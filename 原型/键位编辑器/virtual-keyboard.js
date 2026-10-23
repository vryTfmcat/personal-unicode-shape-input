(()=>{
  'use strict';
  const C=window.KeyboardPrototypeCore,layouts=window.UNICODE_KEYBOARD_LAYOUTS,$=s=>document.querySelector(s),NS='http://www.w3.org/2000/svg';
  let layout,keys,scheme,selected,undo=[],calibrating=false,pending=null,picked=null;
  const pressed=new Set();
  function status(s){$('#status').textContent=s;}
  function create(tag,attrs={},text){const e=document.createElementNS(NS,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e;}
  function fresh(){return {format:'unicode-keyboard-annotations-v1',layoutId:layout.id,geometryHash:C.signature(layout.kle),annotations:{base:{},shift:{}},bindings:C.defaults(layout.id,keys)};}
  function storageKey(){return 'unicode-virtual-keyboard-v1:'+layout.id;}
  function save(){try{localStorage.setItem(storageKey(),JSON.stringify(scheme));status('草稿已自动保存在此浏览器；可导出独立文件');}catch{status('浏览器保存失败，请导出方案以保留修改');}}
  function snapshot(){undo.push(JSON.stringify(scheme));if(undo.length>40)undo.shift();$('#undo').disabled=false;}
  function cancelCalibration(){calibrating=false;$('#calibrate').textContent='按实体键校准';}
  function load(){
    cancelCalibration();pending=null;$('#importPanel').hidden=true;layout=layouts.find(l=>l.id===$('#layout').value);keys=C.parseKle(layout.kle);scheme=fresh();undo=[];$('#undo').disabled=true;pressed.clear();let recovered=false;
    try{const s=localStorage.getItem(storageKey());if(s){scheme=C.validate(JSON.parse(s),layout,keys);recovered=true;}}catch{status('旧草稿无法读取，已显示原布局；旧数据未覆盖，请先检查或导出。');render();return;}
    selected=keys.find(k=>k.label==='F')?.id||keys[0].id;undo=[];$('#undo').disabled=true;pressed.clear();render();status(recovered?'已恢复此键盘的浏览器草稿':'选择键帽后可添加字符；当前显示原始键帽');
  }
  function render(){
    if(!keys.some(k=>k.id===selected))selected=keys[0].id;
    const svg=$('#keyboard');svg.replaceChildren();
    const minX=Math.min(...keys.map(k=>k.x+Math.min(0,k.x2))),minY=Math.min(...keys.map(k=>k.y+Math.min(0,k.y2))),maxX=Math.max(...keys.map(k=>k.x+Math.max(k.w,k.x2+k.w2))),maxY=Math.max(...keys.map(k=>k.y+Math.max(k.h,k.y2+k.h2)));
    svg.setAttribute('viewBox',`${minX-.15} ${minY-.15} ${maxX-minX+.3} ${maxY-minY+.3}`);
    $('#boardName').textContent=layout.name;$('#keyCount').textContent=`${keys.length} 键 · ${Object.keys(scheme.annotations[$('#layer').value]).length} 个标注`;
    const layer=$('#layer').value;
    keys.forEach(k=>{
      const text=scheme.annotations[layer][k.id],g=create('g',{transform:`translate(${k.x},${k.y})`,'data-key':k.id,role:'button',tabindex:'0','aria-label':`${k.label.replaceAll('\n',' / ')}${text!==undefined?'，标注 '+text:''}`,'aria-pressed':k.id===selected?'true':'false'});
      g.classList.add('key');g.classList.toggle('selected',k.id===selected);g.classList.toggle('annotated',text!==undefined);g.classList.toggle('pressed',pressed.has(scheme.bindings[k.id]));
      g.append(create('path',{d:C.outline(k),class:'cap'}));
      const raw=k.label.split('\n');let display=text!==undefined?text:raw[0];if(/^\p{M}/u.test(display))display='◌'+display;
      const label=create('text',{x:k.w/2,y:k.h/2,class:'main-label'},display);if([...display].length>5)label.style.fontSize='.22px';if([...display].length>12){label.setAttribute('textLength',Math.max(.5,k.w-.18));label.setAttribute('lengthAdjust','spacingAndGlyphs');}g.append(label);
      if($('#original').checked){const corner=text!==undefined?k.label.replaceAll('\n',' / '):raw.slice(1).join(' / ');if(corner)g.append(create('text',{x:.14,y:k.h-.14,class:'original-label'},corner));}
      g.append(create('title',{},`${k.label} · ${scheme.bindings[k.id]||'未绑定'}${text!==undefined?' · '+text:''}`));
      g.addEventListener('click',()=>choose(k.id));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(k.id);}});svg.append(g);
    });inspect();
  }
  function choose(id){selected=id;cancelCalibration();render();}
  function inspect(){const k=keys.find(k=>k.id===selected);$('#selectedName').textContent=k.label.split('\n')[0];$('#position').textContent=`${k.id} · ${k.w} × ${k.h} u`;$('#label').value=scheme.annotations[$('#layer').value][selected]??'';$('#binding').value=scheme.bindings[selected]||'';codepoints();}
  function codepoints(){$('#codepoints').textContent=[...$('#label').value].map(c=>'U+'+c.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')).join(' ');}
  function refreshPressed(){document.querySelectorAll('.key').forEach(g=>g.classList.toggle('pressed',pressed.has(scheme.bindings[g.dataset.key])));}
  function clearPressed(){pressed.clear();refreshPressed();}
  $('#layout').replaceChildren(...layouts.map(l=>{const o=document.createElement('option');o.value=l.id;o.textContent=l.name;return o;}));
  $('#layout').onchange=load;$('#layer').onchange=()=>{cancelCalibration();render();};$('#original').onchange=render;$('#label').oninput=codepoints;
  $('#apply').onclick=()=>{const value=$('#label').value;if(value.length>200){status('标签最多 200 个 UTF-16 单位，请缩短');return;}snapshot();scheme.annotations[$('#layer').value][selected]=value;save();render();};
  $('#restore').onclick=()=>{snapshot();delete scheme.annotations[$('#layer').value][selected];save();render();};
  $('#undo').onclick=()=>{if(undo.length){scheme=JSON.parse(undo.pop());save();render();$('#undo').disabled=!undo.length;}};
  $('#calibrate').onclick=()=>{calibrating=!calibrating;$('#calibrate').textContent=calibrating?'等待按键… Esc 取消':'按实体键校准';status(calibrating?'请按所选实体键；此操作会调整该键的事件绑定':'已取消校准');};
  $('#take').onclick=()=>{if(!picked){status('请从三模式编辑器入口打开本页，并在编辑器中选择一个字符');return;}$('#label').value=picked.char;codepoints();status('已填入当前字符；点击“应用标注”保存到键帽');};
  function acceptPicked(item){if(item&&typeof item.char==='string'&&item.char.length<=200){picked={char:item.char,id:typeof item.id==='string'?item.id:''};$('#pickedInfo').textContent='编辑器当前字符：'+item.char;}}
  window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===window.opener&&e.data?.type==='unicode-keyboard-character')acceptPicked(e.data.item);});
  try{if(window.opener&&window.opener.location.origin===location.origin){acceptPicked(window.opener.keyEditor?.getSelectedItem?.());window.opener.postMessage({type:'unicode-keyboard-ready'},location.origin);}}catch{}
  if(!picked)$('#pickedInfo').textContent='也可直接在上方粘贴任意 Unicode 字符。';
  window.addEventListener('keydown',e=>{
    if(calibrating){if(e.key==='Escape'){cancelCalibration();status('已取消校准');return;}if(!e.code||e.repeat||e.isComposing)return;e.preventDefault();snapshot();for(const [id,code]of Object.entries(scheme.bindings))if(code===e.code&&id!==selected)delete scheme.bindings[id];scheme.bindings[selected]=e.code;cancelCalibration();save();render();status(`已绑定 ${e.code}；同键事件的旧绑定已移除，可撤销`);return;}
    if(e.isComposing||e.target.closest('input,textarea,select,[contenteditable="true"]'))return;
    pressed.add(e.code);refreshPressed();$('#lastKey').textContent=`${e.code||'未知位置'} · ${e.key}`;
  });window.addEventListener('keyup',e=>{pressed.delete(e.code);refreshPressed();});window.addEventListener('blur',clearPressed);document.addEventListener('visibilitychange',()=>{if(document.hidden){clearPressed();cancelCalibration();}});
  $('#export').onclick=()=>{const blob=new Blob([JSON.stringify(scheme,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`unicode-keyboard-${layout.id}-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('已请求下载方案文件，请检查浏览器下载结果');};
  $('#import').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>200000)throw Error('方案文件过大');pending=C.validate(JSON.parse(await f.text()),layout,keys);$('#importSummary').textContent=`${layout.name}：基础层 ${Object.keys(pending.annotations.base).length} 个，Shift 层 ${Object.keys(pending.annotations.shift).length} 个；确认后替换此键盘的全部标注与绑定，可撤销。`;$('#importPanel').hidden=false;$('#importPanel').open=true;status('导入已通过格式检查，等待确认替换');}catch(err){pending=null;$('#importPanel').hidden=true;status('导入失败：'+err.message);}finally{e.target.value='';}};
  $('#confirmImport').onclick=()=>{if(pending){snapshot();scheme=pending;pending=null;save();render();$('#importPanel').hidden=true;}};$('#cancelImport').onclick=()=>{pending=null;$('#importPanel').hidden=true;status('已取消导入');};
  load();
})();
