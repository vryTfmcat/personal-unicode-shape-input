(function(root) {
  "use strict";
  function model(data) {
    if(data.format!=="unicode-shape-experiment-v1" || data.active!==false) throw Error("不是隔离实验数据");
    const byCp=new Map(), index=new Map();
    function add(code,cp) {if(!index.has(code))index.set(code,new Set());index.get(code).add(cp);}
    for(const row of data.records) {
      if(byCp.has(row.cp))throw Error("重复字符身份");
      byCp.set(row.cp,row);
      if(!/^[a-w]$/.test(row.bucket))throw Error("主桶超出a–w");
      add(row.bucket,row.cp);
      for(const route of row.familyRoutes) {
        if(!data.familyBuckets[route.familyKey]?.includes(route.bucket) || data.definitions.families[route.familyKey]?.id!==route.familyId)throw Error("形族映射不一致");
        add(route.bucket,row.cp);add(route.bucket+route.familyKey,row.cp);
      }
      const codes=new Set(), objects=new Map((row.objects||[]).map(o=>[o.id,o]));
      if(data.indexOnly)for(const code of row.codes) {
        if(!/^[a-w][a-z]{2,3}$/.test(code)||codes.has(code)||(code.length===4&&!data.definitions.fourth[code[3]]))throw Error("索引路径无效");
        if(!row.familyRoutes.some(r=>r.bucket===code[0]&&r.familyKey===code[1]))throw Error("路径缺少形族入口");
        codes.add(code);for(let n=1;n<=code.length;n++)add(code.slice(0,n),row.cp);
      }
      for(const path of row.paths||[]) {
        if(!/^[a-w][a-z]{2,3}$/.test(path.code) || codes.has(path.code) || !path.evidence.length)throw Error("路径格式或依据无效");
        codes.add(path.code);
        if(path.code.length===4 && !data.definitions.fourth[path.code[3]])throw Error("第四位未定义");
        for(const e of path.evidence) {
          if(!objects.has(e.objectId)||e.objectId!==e.fourthObjectId||e.third!==path.code[2]||data.definitions.third[e.third]?.function!==e.rule)throw Error("路径对象或规则不一致");
          if(!row.familyRoutes.some(r=>r.bucket===path.code[0]&&r.familyKey===path.code[1]&&r.target===e.familyTarget))throw Error("缺少形族观察依据");
        }
        for(let n=1;n<=path.code.length;n++)add(path.code.slice(0,n),row.cp);
      }
    }
    function query(code) {
      if(!/^[a-w][a-z]{0,3}$/.test(code))return [];
      return [...(index.get(code)||[])].map(cp=>byCp.get(cp));
    }
    function characters(text) {
      const raw=text.trim();const match=/^U\+([0-9a-f]{1,6})$/i.exec(raw);
      const cps=match?[parseInt(match[1],16)]:[...raw].map(c=>c.codePointAt(0));
      return [...new Set(cps)].map(cp=>byCp.get(cp)).filter(Boolean);
    }
    return {byCp,index,query,characters};
  }
  const api={model};if(typeof module!=="undefined"&&module.exports)module.exports=api;else root.ShapeExperiment=api;
})(typeof window!=="undefined"?window:globalThis);
