'use strict';
const $=id=>document.getElementById(id), C=TouchSpace, K=KeyboardPrototypeCore;
const STORE='unicode-touch-workspace-v1';
let catalog,chars=[],byId,blocks,mode='block',group='block-25a0',selected=null,detail=null,onlyTray=false,limit=120,trying=false,keyboardMode=false,pendingImport=null;
let state={format:C.FORMAT,tiles:[],bindings:{}},tray=[],undo=[],redo=[],activeTile=null;
let view={x:0,y:0,scale:1},step=64,saveFailed=false,storageProtected=false;
const pointers=new Map();let gesture=null;
function toast(s){$('toast').textContent=s;$('toast').classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').classList.remove('show'),3000);}
function save(){
  if(storageProtected){$('saveState').textContent='旧存档异常，已保护；请导出当前布局';return;}
  try{localStorage.setItem(STORE,JSON.stringify({layout:state,tray,view}));$('saveState').textContent='已保存在此设备';saveFailed=false;}
  catch(e){saveFailed=true;$('saveState').textContent='保存失败，请立即导出布局';toast('设备存储不可用或空间不足，请导出布局');}
}
function commit(next){undo.push(C.clone(state));if(undo.length>80)undo.shift();redo=[];state=next;save();if(window.workspaceChanged)workspaceChanged();renderSpace();}
function history(back){const from=back?undo:redo,to=back?redo:undo;if(!from.length)return;to.push(C.clone(state));state=from.pop();activeTile=null;save();renderSpace();}
function escape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function cp(c){return 'U+'+c.char.codePointAt(0).toString(16).toUpperCase().padStart(4,'0');}
function chooseMode(next){mode=next;onlyTray=false;limit=120;$('browse').hidden=next==='space';$('space').hidden=next!=='space';document.querySelectorAll('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===mode));if(next!=='space'){group=next==='block'?'block-25a0':'i';renderGroups();renderGrid();}else{requestAnimationFrame(renderSpace);}window.scrollTo(0,0);}
function renderGroups(){
  const list=mode==='block'?blocks.map(b=>[b.id,`P${b.plane} · ${b.name}`]):[...'abcdefghijklmnopqrstuvwxyz'].map(k=>[k,`${k} · ${'xyz'.includes(k)?({x:'组合与附加标记',y:'排除文字收纳',z:'中文与汉字构件'})[k]:'图形桶'}`]).concat([['unclassified','未分类 · 待补字形']]);
  $('group').innerHTML=list.map(([id,label])=>`<option value="${id}">${escape(label)}</option>`).join('');$('group').value=group;
  $('heading').textContent=mode==='block'?'从区块开始。':'循着形状寻找。';$('browseEyebrow').textContent=mode==='block'?'01 / BLOCKS':'02 / SHAPES';
}
function renderGrid(){
  const q=$('search').value.trim().toLowerCase();
  const list=chars.filter(c=>{
    if(onlyTray&&!tray.includes(c.id))return false;
    if(q)return `${c.char} ${c.id} ${cp(c)} ${c.name} ${c.code} ${c.bucket||''}`.toLowerCase().includes(q);
    return onlyTray|| (mode==='block'?c.block===group:group==='unclassified'?!c.bucket:c.bucket===group);
  });
  if(mode==='shape'&&!q&&!onlyTray)list.sort((a,b)=>a.rank-b.rank);
  $('groupInfo').textContent=(q?'全库搜索':onlyTray?'已取用符号':mode==='shape'?'阶段分桶 · 分类待核对':'Unicode '+catalog.unicodeVersion)+' · '+list.length.toLocaleString()+' 个符号';
  $('total').textContent=mode==='shape'?'沿用阶段分桶':blocks.length+' 个区块';
  const frag=document.createDocumentFragment();
  list.slice(0,limit).forEach(c=>{const b=document.createElement('button');b.className='symbol';b.setAttribute('aria-label',`${c.char} ${cp(c)} ${c.name}`);b.innerHTML=`<span class="glyph">${escape(c.char)}</span><code>${cp(c)}</code>${tray.includes(c.id)?'<span class="mark">●</span>':''}`;b.onclick=()=>showDetail(c);frag.append(b);});
  $('grid').replaceChildren(frag);if(!list.length)$('grid').textContent='没有匹配的符号';$('more').hidden=limit>=list.length;$('collected').textContent=onlyTray?'查看全部':'只看取用盘';
}
function showDetail(c){detail=c;$('detailGlyph').textContent=c.char;$('detailName').textContent=c.name;$('detailMeta').textContent=cp(c)+' · '+(blocks.find(b=>b.id===c.block)?.name||c.block);$('detailCodes').textContent=`区块码 ${c.code||'无'} · 全形桶 ${c.bucket||'待分类'}（阶段分桶）`;$('detail').showModal();}
function take(c){if(!tray.includes(c.id))tray.push(c.id);selected=c.id;activeTile=null;trying=false;save();renderTray();$('detail').close();chooseMode('space');toast('已取用 '+c.char+'，点空格放置或点键帽标注');}
function renderTray(){
  $('trayCount').textContent=tray.length;$('trayItems').replaceChildren();
  tray.forEach(id=>{const c=byId.get(id),b=document.createElement('button');b.textContent=c.char;b.className='glyph'+(id===selected?' selected':'');b.title=cp(c)+' · 长按可移出取用盘';b.setAttribute('aria-label','取用 '+c.char+' '+cp(c));b.onclick=()=>{selected=id;activeTile=null;trying=false;renderTray();chooseMode('space');};
    let timer; b.onpointerdown=()=>timer=setTimeout(()=>{tray=tray.filter(t=>t!==id);if(selected===id)selected=null;save();renderTray();renderSpace();toast('已从取用盘移除；空间元素保留');},900);for(const e of ['pointerup','pointercancel','pointerleave'])b.addEventListener(e,()=>clearTimeout(timer));$('trayItems').append(b);
  });
  $('trayHelp').textContent=selected?'已取用 '+byId.get(selected).char+' · 点空格放置':'点符号查看与取用';
}
function appendOutput(id){const c=byId.get(id);if(c){$('output').value+=c.char;$('output').scrollTop=$('output').scrollHeight;}}
function point(e){const r=$('viewport').getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
function cell(p){return{x:Math.floor((p.x-view.x)/(step*view.scale)),y:Math.floor((p.y-view.y)/(step*view.scale))};}
function center(){const vp=$('viewport');const ts=state.tiles;const x=ts.length?ts.reduce((n,t)=>n+t.x,0)/ts.length:256,y=ts.length?ts.reduce((n,t)=>n+t.y,0)/ts.length:256;view.x=vp.clientWidth/2-(x+.5)*step*view.scale;view.y=vp.clientHeight/2-(y+.5)*step*view.scale;save();renderCanvas();}
function zoom(factor,p={x:$('viewport').clientWidth/2,y:$('viewport').clientHeight/2}){const old=view.scale,n=Math.max(.3,Math.min(2.5,old*factor));view.x=p.x-(p.x-view.x)*n/old;view.y=p.y-(p.y-view.y)*n/old;view.scale=n;renderCanvas();}
function renderCanvas(){
  const vp=$('viewport'),s=step*view.scale;$('position').textContent=`512 × 512 · ${Math.round(view.scale*100)}%`;
  vp.style.backgroundSize=`${s}px ${s}px`;vp.style.backgroundPosition=`${view.x}px ${view.y}px`;
  const fragment=document.createDocumentFragment();
  state.tiles.forEach(t=>{const x=t.x*s+view.x,y=t.y*s+view.y;if(x < -s||y < -s||x>vp.clientWidth||y>vp.clientHeight)return;const c=byId.get(t.charId),b=document.createElement('button');b.className='tile'+(t.id===activeTile?' selected':'');b.dataset.id=t.id;b.style.cssText=`left:${x+3}px;top:${y+3}px;width:${s-6}px;height:${s-6}px;font-size:${32*view.scale}px`;b.setAttribute('aria-label',`${c.char} 位置 ${t.x},${t.y}`);b.innerHTML=`${escape(c.char)}<span class="cell">${t.x},${t.y}</span>`;
    b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();if(trying)appendOutput(t.charId);else{activeTile=t.id;selected=null;renderSpace();}}};fragment.append(b);});$('tiles').replaceChildren(fragment);
}
function renderKeyboard(){
  const layout=UNICODE_KEYBOARD_LAYOUTS.find(l=>l.id===$('keyboardLayout').value),keys=K.parseKle(layout.kle),svg=$('keyboard');
  const maxX=Math.max(...keys.map(k=>k.x+k.w)),maxY=Math.max(...keys.map(k=>k.y+k.h));svg.setAttribute('viewBox',`-.1 -.1 ${maxX+.2} ${maxY+.2}`);svg.style.height=(780*maxY/maxX)+'px';svg.replaceChildren();
  keys.forEach(k=>{const ns='http://www.w3.org/2000/svg',g=document.createElementNS(ns,'g'),path=document.createElementNS(ns,'path'),text=document.createElementNS(ns,'text');const bound=state.bindings[layout.id]?.[k.id],c=byId.get(bound);g.setAttribute('transform',`translate(${k.x} ${k.y})`);g.setAttribute('role','button');g.setAttribute('tabindex','0');g.setAttribute('aria-label',`${k.label.split('\n')[0]}${c?' '+c.char:''}`);if(c)g.classList.add('bound');path.setAttribute('d',K.outline(k));text.setAttribute('x',k.w/2);text.setAttribute('y',k.h/2+.12);text.setAttribute('text-anchor','middle');text.setAttribute('font-size',c?'.5':'.24');text.textContent=c?.char||k.label.split('\n')[0];g.append(path,text);
    if(c){const sub=document.createElementNS(ns,'text');sub.setAttribute('x','.12');sub.setAttribute('y','.25');sub.setAttribute('class','key-original');sub.textContent=k.label.split('\n')[0];g.append(sub);}
    g.dataset.keyId=k.id;
    const act=()=>{if(trying){if(c)appendOutput(c.id);return;}if(!selected){toast('先在区块或全形中取用符号');return;}const next=C.clone(state);next.bindings[layout.id]||={};next.bindings[layout.id][k.id]=selected;commit(next);};g.onclick=act;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();act();}};svg.append(g);
  });
}
function renderSpace(){
  $('tileCount').textContent=state.tiles.length+' 个元素';$('undo').disabled=!undo.length;$('redo').disabled=!redo.length;$('try').setAttribute('aria-pressed',trying);$('try').classList.toggle('selected',trying);
  $('canvasTab').setAttribute('aria-pressed',!keyboardMode);$('keyboardTab').setAttribute('aria-pressed',keyboardMode);$('canvasPanel').hidden=keyboardMode;$('keyboardPanel').hidden=!keyboardMode;
  const tile=state.tiles.find(t=>t.id===activeTile);$('remove').disabled=!tile;$('selectionText').textContent=trying?'试输中 · 点元素输出原始字符':tile?'已选 '+byId.get(tile.charId).char+' · 拖动或点空格移动':selected?'待放置 '+byId.get(selected).char+' · 可重复放置':'选择符号，再点空格放置';
  if(keyboardMode)renderKeyboard();else renderCanvas();
}
function addAt(p){const pos=cell(p);try{const old=state.tiles.find(t=>t.id===activeTile);if(!old&&!selected)return;const tile=old||{id:crypto.randomUUID?crypto.randomUUID():'tile-'+Date.now()+'-'+Math.random(),charId:selected};const next=C.clone(state);next.tiles=C.place(next.tiles,tile,pos.x,pos.y);commit(next);}catch(e){toast(e.message);}}
function setupPointer(){
  const vp=$('viewport');
  vp.onpointerdown=e=>{if(e.button&&e.button!==0)return;vp.setPointerCapture(e.pointerId);pointers.set(e.pointerId,point(e));const tile=state.tiles.find(t=>t.id===e.target.closest('.tile')?.dataset.id);
    if(pointers.size===1){gesture={start:point(e),last:point(e),view:{...view},tile,moved:false};}
    else if(pointers.size===2){const [a,b]=[...pointers.values()];gesture={pinch:true,distance:Math.hypot(a.x-b.x,a.y-b.y),mid:{x:(a.x+b.x)/2,y:(a.y+b.y)/2},moved:true};}
  };
  vp.onpointermove=e=>{if(!pointers.has(e.pointerId)||!gesture)return;const p=point(e);pointers.set(e.pointerId,p);
    if(pointers.size===2&&gesture.pinch){const[a,b]=[...pointers.values()],d=Math.hypot(a.x-b.x,a.y-b.y),mid={x:(a.x+b.x)/2,y:(a.y+b.y)/2};if(gesture.distance>0)zoom(d/gesture.distance,gesture.mid);view.x+=mid.x-gesture.mid.x;view.y+=mid.y-gesture.mid.y;gesture.distance=d;gesture.mid=mid;renderCanvas();return;}
    if(gesture.pinch)return;const dx=p.x-gesture.start.x,dy=p.y-gesture.start.y;if(Math.hypot(dx,dy)>6)gesture.moved=true;
    if(gesture.moved&&!gesture.tile){view.x=gesture.view.x+dx;view.y=gesture.view.y+dy;renderCanvas();}
    if(gesture.moved&&gesture.tile&&!trying){const b=$('tiles').querySelector(`[data-id="${CSS.escape(gesture.tile.id)}"]`);if(b){b.style.left=(gesture.tile.x*step*view.scale+view.x+dx+3)+'px';b.style.top=(gesture.tile.y*step*view.scale+view.y+dy+3)+'px';}}
    gesture.last=p;
  };
  vp.onpointerup=e=>{if(!pointers.has(e.pointerId))return;const g=gesture,p=point(e);pointers.delete(e.pointerId);if(g&&!g.pinch){if(g.tile){if(trying&&!g.moved)appendOutput(g.tile.charId);else if(!trying){activeTile=g.tile.id;selected=null;if(g.moved)addAt(p);renderTray();renderSpace();}}else if(!g.moved&&!trying){addAt(p);}}if(!pointers.size){gesture=null;save();}else gesture={pinch:true,moved:true};};
  vp.onpointercancel=e=>{pointers.delete(e.pointerId);gesture=null;renderCanvas();};
  vp.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?1.1:1/1.1,point(e));clearTimeout(zoom.timer);zoom.timer=setTimeout(save,300);},{passive:false});
}
function exportLayout(){const data=JSON.stringify(state,null,2);if(window.AndroidFiles){AndroidFiles.exportLayout(data);return;}const a=document.createElement('a'),url=URL.createObjectURL(new Blob([data],{type:'application/json'}));a.href=url;a.download='Unicode键位空间.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
window.receiveLayout=text=>{try{pendingImport=C.validate(JSON.parse(text),new Set(byId.keys()));for(const [layout,map]of Object.entries(pendingImport.bindings)){const keys=new Set(K.parseKle(UNICODE_KEYBOARD_LAYOUTS.find(l=>l.id===layout).kle).map(k=>k.id));if(Object.keys(map).some(k=>!keys.has(k)))throw Error('包含不存在的实体键位');}$('importSummary').textContent=`${pendingImport.tiles.length} 个空间元素，${Object.values(pendingImport.bindings).reduce((n,m)=>n+Object.keys(m).length,0)} 个键帽标注`;$('importDialog').showModal();}catch(e){pendingImport=null;toast('导入失败：'+e.message);}};
async function copy(text){try{if(window.AndroidFiles)AndroidFiles.copyText(text);else await navigator.clipboard.writeText(text);toast('已复制');}catch(e){toast('复制失败，可在文本框中手动选择复制');}}
async function init(){
  const response=await fetch('catalog.json');if(!response.ok)throw Error('字符快照载入失败');catalog=await response.json();chars=catalog.characters.map(r=>({id:r[0],char:r[1],name:r[2],block:r[3],code:r[4],bucket:r[5],rank:r[6]}));byId=new Map(chars.map(c=>[c.id,c]));blocks=catalog.blocks.map(r=>({id:r[0],name:r[1],plane:r[2]}));
  try{const raw=localStorage.getItem(STORE);if(raw){const saved=JSON.parse(raw);state=C.validate(saved.layout,new Set(byId.keys()));tray=Array.isArray(saved.tray)?[...new Set(saved.tray)].filter(id=>byId.has(id)):[];if(saved.view&&Number.isFinite(saved.view.x)&&Number.isFinite(saved.view.y)&&saved.view.scale>=.3&&saved.view.scale<=2.5)view=saved.view;}}catch(e){storageProtected=true;toast('旧存档无法读取，已保护；请导出当前布局后检查');}
  document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>chooseMode(b.dataset.mode));$('search').oninput=()=>{clearTimeout(init.timer);init.timer=setTimeout(()=>{limit=120;renderGrid();},180);};$('group').onchange=e=>{group=e.target.value;limit=120;$('search').value='';renderGrid();};$('more').onclick=()=>{limit+=120;renderGrid();};$('collected').onclick=()=>{onlyTray=!onlyTray;limit=120;renderGrid();};
  $('closeDetail').onclick=()=>$('detail').close();$('take').onclick=()=>take(detail);$('copyChar').onclick=()=>copy(detail.char);$('undo').onclick=()=>history(true);$('redo').onclick=()=>history(false);$('try').onclick=()=>{trying=!trying;activeTile=null;renderSpace();};$('canvasTab').onclick=()=>{keyboardMode=false;renderSpace();};$('keyboardTab').onclick=()=>{keyboardMode=true;renderSpace();};$('keyboardLayout').onchange=renderKeyboard;
  $('minus').onclick=()=>{zoom(1/1.2);save();};$('plus').onclick=()=>{zoom(1.2);save();};$('home').onclick=center;
  $('cancelSelection').onclick=()=>{selected=null;activeTile=null;renderTray();renderSpace();};$('remove').onclick=()=>{if(!activeTile)return;const next=C.clone(state);next.tiles=next.tiles.filter(t=>t.id!==activeTile);activeTile=null;commit(next);};$('copyOutput').onclick=()=>copy($('output').value);
  $('export').onclick=exportLayout;$('import').onclick=()=>window.AndroidFiles?AndroidFiles.importLayout():$('file').click();$('file').onchange=async e=>{const f=e.target.files[0];if(f){if(f.size>8000000)toast('文件过大，最多 8 MB');else receiveLayout(await f.text());}e.target.value='';};$('cancelImport').onclick=()=>{$('importDialog').close();pendingImport=null;};$('confirmImport').onclick=()=>{if(!pendingImport)return;commit(pendingImport);pendingImport=null;activeTile=null;$('importDialog').close();chooseMode('space');center();toast('布局已导入，可撤销');};
  setupPointer();
  window.addEventListener('keydown',e=>{
    if(mode!=='space'||!keyboardMode||$('keyboardLayout').value==='mobile'||e.ctrlKey||e.altKey||e.metaKey||e.target.closest('input,textarea,select,dialog'))return;
    const layout=UNICODE_KEYBOARD_LAYOUTS.find(l=>l.id===$('keyboardLayout').value),map=K.defaults(layout.id,K.parseKle(layout.kle));
    const key=Object.keys(map).find(id=>map[id]===e.code);if(!key)return;
    $('keyboard').querySelector(`[data-key-id="${key}"]`)?.classList.add('pressed');
    const id=state.bindings[layout.id]?.[key];if(trying&&id&&!e.repeat){e.preventDefault();appendOutput(id);}
  });
  const release=()=>document.querySelectorAll('#keyboard .pressed').forEach(el=>el.classList.remove('pressed'));
  window.addEventListener('keyup',release);window.addEventListener('blur',release);
  window.addEventListener('resize',()=>{if(mode==='space')renderSpace();});window.addEventListener('beforeunload',()=>{if(!saveFailed)save();});renderTray();chooseMode('block');if(!localStorage.getItem(STORE)){view.x=0;view.y=0;}save();
  // Delay centering until the canvas has measurable dimensions on its first visit.
  const oldChoose=chooseMode;let centered=false;chooseMode=next=>{oldChoose(next);if(next==='space'&&!centered){centered=true;center();}};
  document.dispatchEvent(new Event('touch-ready'));
}
init().catch(e=>{$('saveState').textContent='载入失败';$('grid').textContent=e.message+'。请重新生成触屏数据后启动。';});
