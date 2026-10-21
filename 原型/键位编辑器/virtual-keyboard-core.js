(function(root){
  'use strict';
  function parseKle(rows){
    if(!Array.isArray(rows))throw Error('KLE 必须为行数组');
    const keys=[];let y=0,c='#293a2f',t='#edf6ef';
    rows.forEach((row,r)=>{if(!Array.isArray(row))return;let x=0,p={};let n=0;
      for(const item of row){
        if(typeof item==='object'&&item){
          if(item.r||item.rx||item.ry)throw Error('第一版暂不支持旋转键盘');
          x+=item.x||0;y+=item.y||0;c=item.c||c;t=item.t||t;Object.assign(p,item);continue;
        }
        if(typeof item!=='string')throw Error('KLE 键帽格式错误');
        const w=p.w??1,h=p.h??1;
        keys.push({id:`r${r}-k${n++}`,x,y,w,h,label:item,c,t,x2:p.x2??0,y2:p.y2??0,w2:p.w2??w,h2:p.h2??h});
        x+=w;p={};
      }y+=1;
    });return keys;
  }
  // Outline the union of the primary and secondary KLE rectangles, including ISO Enter.
  function outline(k,gap=.05){
    const rs=[[0,0,k.w,k.h],[k.x2,k.y2,k.x2+k.w2,k.y2+k.h2]];
    const xs=[...new Set(rs.flatMap(r=>[r[0],r[2]]))].sort((a,b)=>a-b),ys=[...new Set(rs.flatMap(r=>[r[1],r[3]]))].sort((a,b)=>a-b);
    const filled=(i,j)=>i>=0&&j>=0&&i<xs.length-1&&j<ys.length-1&&rs.some(r=>(xs[i]+xs[i+1])/2>r[0]&&(xs[i]+xs[i+1])/2<r[2]&&(ys[j]+ys[j+1])/2>r[1]&&(ys[j]+ys[j+1])/2<r[3]);
    const edges=[];for(let i=0;i<xs.length-1;i++)for(let j=0;j<ys.length-1;j++)if(filled(i,j)){
      const a=[xs[i],ys[j]],b=[xs[i+1],ys[j]],c=[xs[i+1],ys[j+1]],d=[xs[i],ys[j+1]];
      if(!filled(i,j-1))edges.push([a,b]);if(!filled(i+1,j))edges.push([b,c]);if(!filled(i,j+1))edges.push([c,d]);if(!filled(i-1,j))edges.push([d,a]);
    }
    const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
    const pt=p=>`${p[0]===maxX?p[0]-gap:p[0]===minX?p[0]+gap:p[0]},${p[1]===maxY?p[1]-gap:p[1]===minY?p[1]+gap:p[1]}`;
    let result='';while(edges.length){let [start,end]=edges.shift();result+='M'+pt(start)+'L'+pt(end);let guard=0;while((end[0]!==start[0]||end[1]!==start[1])&&guard++<30){let i=edges.findIndex(e=>e[0][0]===end[0]&&e[0][1]===end[1]);if(i<0)break;end=edges.splice(i,1)[0][1];result+='L'+pt(end);}result+='Z';}return result;
  }
  function defaults(layout,keys){
    const result={};const simple={Tab:'Tab',Backspace:'Backspace',Enter:'Enter',Space:'Space',Ins:'Insert',Del:'Delete',PgUp:'PageUp',PgDn:'PageDown',Home:'Home',End:'End','↑':'ArrowUp','↓':'ArrowDown','←':'ArrowLeft','→':'ArrowRight',Esc:'Escape',Menu:'ContextMenu','Caps Lock':'CapsLock','Caps':'CapsLock','Num':'NumLock','Prt Sc':'PrintScreen','Scr Lk':'ScrollLock',Pause:'Pause'};
    const top=['KeyQ','KeyW','KeyE','KeyR','KeyT','KeyY','KeyU','KeyI','KeyO','KeyP','BracketLeft','BracketRight'];
    const home=['KeyA','KeyS','KeyD','KeyF','KeyG','KeyH','KeyJ','KeyK','KeyL','Semicolon','Quote'];
    const bottom=['KeyZ','KeyX','KeyC','KeyV','KeyB','KeyN','KeyM','Comma','Period','Slash'];
    const bindAfter=(r,label,codes)=>{const row=keys.filter(k=>k.id.startsWith(`r${r}-`));let ix=row.findIndex(k=>k.label.split('\n')[0]===label);if(ix>=0)codes.forEach((code,n)=>{if(row[ix+1+n])result[row[ix+1+n].id]=code;});};
    keys.forEach(k=>{const s=k.label.split('\n')[0];if(simple[s])result[k.id]=simple[s];if(/^F\d{1,2}$/.test(s))result[k.id]=s;});
    bindAfter(layout==='mk68'?1:2,'Tab',top);bindAfter(layout==='mk68'?2:3,layout==='mk68'?'Caps Lock':'Caps',home);
    const br=keys.filter(k=>k.id.startsWith(`r${layout==='mk68'?3:4}-`));const z=br.findIndex(k=>k.label==='Z');bottom.forEach((code,i)=>{if(br[z+i])result[br[z+i].id]=code;});
    let shifts=0,ctrls=0,alts=0;keys.forEach(k=>{let s=k.label.split('\n')[0];if(s==='Shift')result[k.id]=shifts++?'ShiftRight':'ShiftLeft';if(s==='Ctrl')result[k.id]=ctrls++?'ControlRight':'ControlLeft';if(s==='Alt'||s==='Alt Gr')result[k.id]=alts++?'AltRight':'AltLeft';if(s==='Win')result[k.id]='MetaLeft';});
    const nr=keys.filter(k=>k.id.startsWith(`r${layout==='mk68'?0:1}-`));const one=nr.findIndex(k=>k.label.startsWith('1'));for(let i=0;i<10;i++)if(nr[one+i])result[nr[one+i].id]='Digit'+((i+1)%10);if(nr[one-1])result[nr[one-1].id]=layout==='mk68'?'Escape':'Backquote';if(nr[one+10])result[nr[one+10].id]='Minus';if(nr[one+11])result[nr[one+11].id]='Equal';
    if(layout==='mk68'){const slash=keys.find(k=>k.id.startsWith('r1-')&&k.label.startsWith('\\'));if(slash)result[slash.id]='Backslash';}else{
      const extra=keys.find(k=>k.id.startsWith('r3-')&&k.label.startsWith('#'));if(extra)result[extra.id]='Backslash';if(z>0)result[br[z-1].id]='IntlBackslash';
      const num=keys.find(k=>k.label==='Num\nLock');
      if(num)keys.forEach(k=>{if(k.y>=num.y&&k.x>=num.x){const s=k.label.split('\n')[0];const map={'/':'NumpadDivide','*':'NumpadMultiply','-':'NumpadSubtract','+':'NumpadAdd','Enter':'NumpadEnter','.':'NumpadDecimal','Num':'NumLock'};if(map[s])result[k.id]=map[s];else if(/^\d$/.test(s))result[k.id]='Numpad'+s;}});
      keys.forEach(k=>{if(k.label==='Page\nUp')result[k.id]='PageUp';if(k.label==='Page\nDown')result[k.id]='PageDown';});
    }
    return result;
  }
  function signature(kle){const str=JSON.stringify(kle);let h=2166136261;for(let i=0;i<str.length;i++)h=Math.imul(h^str.charCodeAt(i),16777619);return(h>>>0).toString(16);}
  function validate(data,layout,keys){
    if(!data||data.format!=='unicode-keyboard-annotations-v1'||data.layoutId!==layout.id||data.geometryHash!==signature(layout.kle))throw Error('方案格式、键盘或外形版本不匹配');
    const ids=new Set(keys.map(k=>k.id));const annotations={base:{},shift:{}},bindings={};
    if(!data.annotations||!data.bindings||typeof data.bindings!=='object')throw Error('方案缺少标注或绑定');
    for(const layer of ['base','shift']){if(!data.annotations[layer]||typeof data.annotations[layer]!=='object'||Array.isArray(data.annotations[layer]))throw Error('标注层格式错误');for(const [id,value]of Object.entries(data.annotations[layer])){if(!ids.has(id)||typeof value!=='string'||value.length>200)throw Error('未知键或标签格式错误');annotations[layer][id]=value;}}
    for(const [id,value]of Object.entries(data.bindings)){if(!ids.has(id)||typeof value!=='string'||!/^[A-Za-z][A-Za-z0-9]{0,39}$/.test(value))throw Error('实体键绑定格式错误');bindings[id]=value;}
    return {format:data.format,layoutId:data.layoutId,geometryHash:data.geometryHash,annotations,bindings};
  }
  const api={parseKle,outline,defaults,signature,validate};root.KeyboardPrototypeCore=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
