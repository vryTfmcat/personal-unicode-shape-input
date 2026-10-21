(function(root){
  'use strict';
  const SIZE=512, FORMAT='unicode-touch-space-v1';
  const clone=x=>JSON.parse(JSON.stringify(x));
  function validate(value,known){
    if(!value||value.format!==FORMAT||!Array.isArray(value.tiles)||value.tiles.length>20000)throw Error('不是有效的触屏键位空间（最多 20000 个元素）');
    const ids=new Set(),cells=new Set();
    const tiles=value.tiles.map(t=>{
      if(!t||typeof t.id!=='string'||ids.has(t.id)||!known.has(t.charId)||!Number.isInteger(t.x)||!Number.isInteger(t.y)||t.x<0||t.y<0||t.x>=SIZE||t.y>=SIZE||cells.has(`${t.x},${t.y}`))throw Error('布局含未知字符、重复位置或越界元素');
      ids.add(t.id);cells.add(`${t.x},${t.y}`);return {id:t.id,charId:t.charId,x:t.x,y:t.y};
    });
    const bindings={};
    for(const [layout,map] of Object.entries(value.bindings||{})){
      if(!['mk68','razer'].includes(layout)||!map||typeof map!=='object')throw Error('键盘布局无效');
      bindings[layout]={};for(const [key,id] of Object.entries(map)){if(!/^r\d+-k\d+$/.test(key)||!known.has(id))throw Error('键帽标注无效');bindings[layout][key]=id;}
    }
    return {format:FORMAT,tiles,bindings};
  }
  function place(tiles,tile,x,y){
    x=Math.round(x);y=Math.round(y);
    if(x<0||y<0||x>=SIZE||y>=SIZE)throw Error('位置超出 512 × 512 键位空间');
    if(tiles.some(t=>t.id!==tile.id&&t.x===x&&t.y===y))throw Error('这个格子已有元素，请选择空格');
    return [...tiles.filter(t=>t.id!==tile.id),{...tile,x,y}];
  }
  const api={SIZE,FORMAT,clone,validate,place};
  if(typeof module!=='undefined')module.exports=api;else root.TouchSpace=api;
})(globalThis);
