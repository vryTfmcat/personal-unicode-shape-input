'use strict';
const W=UnicodeWorkspace, DOC_KEY='unicode-touch-drafts-v2';
let doc,baseManifest,metadataProtected=false,mobileAscii=false,mobileMode='block',lastMobileKey=null,importWorkspace=null;
const entry=id=>doc.profile.entries[id]||{favorite:false,chineseName:'',tags:[]};
function draftPayload(){return {format:'unicode-touch-backup-v2',profile:C.clone(doc.profile),layout:C.clone(state)};}
function writeDoc(){if(metadataProtected){toast('旧收藏存档异常，已保护；请导出备份后检查');return false;}try{localStorage.setItem(DOC_KEY,JSON.stringify(doc));return true;}catch(e){toast('草稿保存失败，请立即导出备份');$('saveState').textContent='草稿未保存';return false;}}
window.workspaceChanged=()=>{if(!doc)return;doc.revision++;doc.updatedAt=new Date().toISOString();writeDoc();};
function remember(id){doc.profile.recent=[id,...doc.profile.recent.filter(x=>x!==id)].slice(0,100);writeDoc();}
function download(name,data,type='application/json'){const url=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function saveBackup(){const text=JSON.stringify(draftPayload(),null,2);if(window.AndroidFiles)AndroidFiles.exportLayout(text);else download('Unicode草稿备份.json',text);}
function restore(snapshot){const known=new Set(byId.keys()),p=W.validate(snapshot.profile,known),s=C.validate(snapshot.layout,known);doc.profile=p;state=s;activeTile=null;selected=null;undo=[];redo=[];workspaceChanged();save();renderTray();chooseMode('personal');toast('已恢复到草稿；同文中的输入方案尚未改变');}
function renderPersonalTools(){
 const p=$('personalLookup');p.hidden=mode!=='personal';
}
function reverseLookup(){
 const text=$('reverseInput').value;const target=$('reverseResult');target.replaceChildren();
 for(const ch of Array.from(text).slice(0,80)){
  const c=byId.get('u-'+ch.codePointAt(0).toString(16).padStart(4,'0'));
  const b=document.createElement('button');b.className='reverse-item';b.textContent=c?`${ch} · ${cp(c)} · ${entry(c.id).chineseName||c.name} · ${c.code||'无区块码'}`:`${ch} · U+${ch.codePointAt(0).toString(16).toUpperCase()} · 未收录`;
  if(c)b.onclick=()=>showDetail(c);target.append(b);
 }
}
function renderMobile(){
 $('keyboardScroll').hidden=true;$('mobileKeyboard').hidden=false;
 const key=(name,label,action,cls='')=>{const b=document.createElement('button');b.className='phone-key '+cls;b.textContent=label;b.dataset.phoneKey=name;b.onclick=action;return b;};
 const phone=$('phoneKeys');phone.replaceChildren();
 const row=()=>{const d=document.createElement('div');d.className='phone-row';phone.append(d);return d;};
 let r=row();r.classList.add('phone-toolbar');
 r.append(key('ascii',mobileAscii?'英':'中',()=>{mobileAscii=!mobileAscii;renderMobile();}));
 for(const [id,label]of [['block','区块'],['shape','全形'],['personal','收藏'],['mixed','混合']])r.append(key(id,label,()=>{mobileMode=id;renderMobile();},id===mobileMode?'selected':''));
 const letter=k=>{const binding=doc.profile.mobileKeys[k],c=binding&&byId.get(binding.charId);return key(k,(c?c.char+'\n':'')+k.toUpperCase(),()=>{
  lastMobileKey=k;
  if(trying){$('output').value+=mobileAscii?k:binding?.action==='commit'?c.char:k;if(c)remember(c.id);return;}
  if(selected){doc.profile.mobileKeys[k]={charId:selected,action:$('phoneAction').value};workspaceChanged();renderMobile();toast('已修改 '+k.toUpperCase()+'，导出部署包后用于同文');}else{$('phoneKeyInfo').textContent='已选 '+k.toUpperCase()+' · '+(binding?(binding.action==='commit'?'直接输入符号':'发送字母，显示符号'):'发送字母');}
 },binding?'bound':'');};
 r=row();[...'qwertyuiop'].forEach(k=>r.append(letter(k)));
 r=row();r.classList.add('phone-home');[...'asdfghjkl'].forEach(k=>r.append(letter(k)));
 r=row();r.append(key('cycle','模式⇧',()=>{mobileMode=['block','shape','personal','mixed'][(['block','shape','personal','mixed'].indexOf(mobileMode)+1)%4];renderMobile();},'phone-wide phone-functional'));[...'zxcvbnm'].forEach(k=>r.append(letter(k)));r.append(key('back','⌫',()=>{$('output').value=Array.from($('output').value).slice(0,-1).join('');},'phone-wide phone-functional'));
 r=row();r.append(key('symbols','123',()=>toast('数字与符号页由同文提供'),'phone-functional'));r.append(key('comma',',',()=>{$('output').value+=',';}));r.append(key('space','空格',()=>{$('output').value+=' ';},'phone-space'));r.append(key('dot','.',()=>{$('output').value+='.';}));r.append(key('enter','↵',()=>{$('output').value+='\n';},'phone-functional'));
 $('phoneKeyInfo').textContent=trying?'预览试输；编码候选请在同文中测试':'取用字符后点字母键，设置显示和行为；自由拼图不改变输入码。';
}
function renderManager(){
 $('draftInfo').textContent=`草稿 r${doc.revision} · ${Object.values(doc.profile.entries).filter(e=>e.favorite).length} 个收藏 · ${Object.keys(doc.profile.mobileKeys).length} 个自定义手机键`;
 $('baseInfo').textContent=baseManifest?`Rime 基础码本 ${baseManifest.id}；全形浏览为阶段分桶，部署包使用现有 Rime 全形词典。`:'Rime 部署数据尚未载入';
 $('snapshotList').replaceChildren();for(const s of doc.snapshots){const b=document.createElement('button');b.textContent='恢复 '+s.label;b.onclick=()=>{if(confirm('恢复到此草稿快照？当前内容会先创建恢复点，同文输入法不会自动改变。')){snapshot('恢复前');restore(s.payload);$('releaseDialog').close();}};$('snapshotList').append(b);}
 $('releaseList').replaceChildren();for(const r of doc.releases){const item=document.createElement('div');item.className='release-row';const text=document.createElement('p');text.textContent=`${r.id} · 草稿 r${r.revision} · ${r.status==='exported'?'部署包已导出':r.status==='failed'?'导出失败':'部署包已生成'}${doc.confirmed===r.id?' · 已手动确认部署':''}`;item.append(text);
 const b=document.createElement('button');b.textContent='记录：已在同文部署并测试';b.onclick=()=>{if(confirm('仅在同文完成部署，并实际输入测试成功后确认。本按钮只记录你的验收，不会自动检测或部署。')){doc.confirmed=r.id;doc.confirmedAt=new Date().toISOString();writeDoc();renderManager();}};b.disabled=r.status==='failed';item.append(b);
 const rollback=document.createElement('button');rollback.textContent='恢复此版本为草稿';rollback.onclick=()=>{if(confirm('恢复该版本草稿？恢复后仍须重新导出、导入并部署同文。')){snapshot('恢复前');restore(r.payload);$('releaseDialog').close();}};item.append(rollback);$('releaseList').append(item);}
 $('deploymentState').textContent=doc.confirmed?'最近手动确认的同文版本：'+doc.confirmed:'尚无已确认部署的同文版本';
}
function snapshot(label='手动快照'){doc.snapshots.unshift({label:new Date().toLocaleString('zh-CN')+' · '+label,payload:draftPayload()});doc.snapshots=doc.snapshots.slice(0,5);writeDoc();renderManager();}
async function exportTrime(toDirectory=false){
 if(!baseManifest){toast('Rime 部署数据尚未载入');return;}
 const id='unicode-'+new Date().toISOString().replace(/[^0-9]/g,'').slice(0,17)+'-r'+doc.revision,payload=draftPayload();
 const record={id,revision:doc.revision,baseId:baseManifest.id,status:'generated',createdAt:new Date().toISOString(),payload};doc.releases.unshift(record);doc.releases=doc.releases.slice(0,5);if(!writeDoc())return;
 const files=W.extras(doc.profile,byId,id,baseManifest.fonts||[]);files['unicode-workspace-backup.json']=JSON.stringify(payload);
 if(window.AndroidFiles){if(toDirectory)AndroidFiles.writeTrimeDirectory(JSON.stringify(files),id);else AndroidFiles.exportTrime(JSON.stringify(files),id);}
 else{const button=$('exportTrime');button.disabled=true;try{for(const name of baseManifest.files){const r=await fetch('trime-base/'+name);if(!r.ok)throw Error('基础词典或字体载入失败');files[name]=new Uint8Array(await r.arrayBuffer());}const blob=W.zip(files);const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=id+'.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);toast('部署包已生成；导入同文并部署后再记录确认');}catch(e){record.status='failed';toast(e.message);}finally{button.disabled=false;writeDoc();}}
 renderManager();
}
window.trimeExportFinished=(id,ok)=>{const r=doc.releases.find(r=>r.id===id);if(r)r.status=ok?'exported':'failed';writeDoc();renderManager();toast(ok?'部署包已导出；尚未确认同文部署':'部署包未导出，草稿保留');};
window.trimeDirectorySelected=()=>toast('已记住同文交接目录；更新文件后仍需在同文同步并部署');
document.addEventListener('touch-ready',async()=>{
 const known=new Set(byId.keys());let stored;
 try{stored=localStorage.getItem(DOC_KEY);doc=stored?JSON.parse(stored):{profile:{version:2,entries:C.clone(catalog.personal||{}),mobileKeys:{},recent:[]},revision:1,snapshots:[],releases:[],confirmed:null};doc.profile=W.validate(doc.profile,known);if(!Number.isInteger(doc.revision)||!Array.isArray(doc.snapshots)||!Array.isArray(doc.releases))throw Error();}
 catch(e){metadataProtected=true;doc={profile:{version:2,entries:{},mobileKeys:{},recent:[]},revision:1,snapshots:[],releases:[],confirmed:null};toast('收藏草稿读取失败，旧记录已保护；请导出当前内容后检查');}
 const personal=document.createElement('div');personal.id='personalLookup';personal.hidden=true;personal.innerHTML='<p class="hint">收藏名称和标签保存在个人草稿；收藏不会自动生成输入码。</p><label>粘贴符号反查<input id="reverseInput" placeholder="例如 Ⱝ𓆟á" aria-label="粘贴符号反查"></label><div id="reverseResult"></div>';$('grid').before(personal);$('reverseInput').oninput=reverseLookup;
 $('detailCodes').insertAdjacentHTML('afterend','<div class="personal-fields"><label><input id="favoriteFlag" type="checkbox">加入个人收藏</label><label>中文名称<input id="chineseName" maxlength="120" placeholder="个人命名，不冒充官方译名"></label><label>个人标签<input id="personalTags" placeholder="用逗号分隔，例如 圆形,常用"></label><button id="savePersonal" class="wide">保存收藏资料</button></div>');
 const oldDetail=showDetail;showDetail=c=>{oldDetail(c);const e=entry(c.id);$('favoriteFlag').checked=e.favorite;$('chineseName').value=e.chineseName;$('personalTags').value=e.tags.join(', ');$('detailCodes').textContent+= ' · 收藏码 '+(catalog.aliases?.[c.id]||[]).map(a=>a.code+(a.enabled?'':'（停用）')).join(' / ');};
 $('savePersonal').onclick=()=>{doc.profile.entries[detail.id]={favorite:$('favoriteFlag').checked,chineseName:$('chineseName').value.trim(),tags:[...new Set($('personalTags').value.split(/[,，]/).map(x=>x.trim()).filter(Boolean))]};try{doc.profile=W.validate(doc.profile,known);workspaceChanged();renderGrid();toast('已保存到个人草稿');}catch(e){toast(e.message);}};
 const oldTake=take;take=c=>{remember(c.id);oldTake(c);};const oldAppend=appendOutput;appendOutput=id=>{remember(id);oldAppend(id);};$('copyChar').onclick=()=>{remember(detail.id);copy(detail.char);};
 const oldGroups=renderGroups;renderGroups=()=>{if(mode!=='personal'){oldGroups();return;}$('group').innerHTML='<option value="favorites">个人收藏</option><option value="recent">最近使用</option>';group='favorites';$('heading').textContent='你的符号收藏。';$('browseEyebrow').textContent='03 / PERSONAL';};
 const oldChoose=chooseMode;chooseMode=next=>{oldChoose(next);renderPersonalTools();};
 const oldGrid=renderGrid;renderGrid=()=>{
  if(mode!=='personal'){oldGrid();return;}
  const q=$('search').value.trim().toLowerCase();let list=group==='recent'?doc.profile.recent.map(id=>byId.get(id)):chars.filter(c=>entry(c.id).favorite);
  if(onlyTray)list=list.filter(c=>tray.includes(c.id));
  if(q)list=list.filter(c=>`${c.char} ${cp(c)} ${c.name} ${c.code} ${entry(c.id).chineseName} ${entry(c.id).tags.join(' ')} ${(catalog.aliases?.[c.id]||[]).map(x=>x.code).join(' ')}`.toLowerCase().includes(q));
  $('grid').replaceChildren();for(const c of list.slice(0,limit)){const b=document.createElement('button');b.className='symbol';b.setAttribute('aria-label',`${c.char} ${cp(c)} ${entry(c.id).chineseName||c.name}`);b.innerHTML=`<span class="glyph">${escape(c.char)}</span><code>${escape(entry(c.id).chineseName||cp(c))}</code>`;b.onclick=()=>showDetail(c);$('grid').append(b);}
  if(!list.length)$('grid').textContent='暂无匹配的收藏；在区块或全形中点字符，可添加到收藏。';$('groupInfo').textContent=(group==='recent'?'最近取用／复制／试输':'个人收藏')+' · '+list.length+' 个符号';$('total').textContent='个人草稿';$('more').hidden=limit>=list.length;$('collected').textContent=onlyTray?'查看全部':'只看取用盘';
 };
 const option=document.createElement('option');option.value='mobile';option.textContent='手机 · QWERTY 三模式';$('keyboardLayout').prepend(option);$('keyboardLayout').value='mobile';
 $('keyboardScroll').insertAdjacentHTML('beforebegin','<div id="mobileKeyboard"><label>按键行为<select id="phoneAction"><option value="commit">直接输入取用的符号</option><option value="send">显示取用的符号，发送原字母编码</option></select></label><div id="phoneKeys"></div><p id="phoneKeyInfo" class="hint"></p><button id="resetPhoneKey">还原所选字母键</button></div>');
 $('resetPhoneKey').onclick=()=>{if(!lastMobileKey){toast('先点一个手机字母键');return;}delete doc.profile.mobileKeys[lastMobileKey];workspaceChanged();renderMobile();};
 const oldKeyboard=renderKeyboard;renderKeyboard=()=>{if($('keyboardLayout').value==='mobile'){renderMobile();return;}$('mobileKeyboard').hidden=true;$('keyboardScroll').hidden=false;oldKeyboard();};
 $('keyboardLayout').onchange=renderKeyboard;
 // The desktop physical-key handler only handles KLE geometries.
 $('keyboardLayout').addEventListener('change',()=>{});
 const manager=document.createElement('dialog');manager.id='releaseDialog';manager.innerHTML='<div class="dialog-top"><h2>草稿与发布</h2><button id="closeRelease">×</button></div><p id="draftInfo"></p><p id="baseInfo"></p><p id="deploymentState"></p><button id="snapshotDraft">创建草稿快照</button><button id="backupDraft">导出草稿备份</button><h3>恢复点（最近五份）</h3><div id="snapshotList"></div><h3>同文部署包</h3><p>生成部署包 → 导入同文用户目录 → 部署 → 选方案和主题 → 实际输入测试 → 手动记录确认。已有 default.custom.yaml 时合并启用方案配置，避免覆盖。</p><div id="directoryTools"><button id="pickTrimeDirectory">选择同文交接目录</button><button id="writeTrimeDirectory" class="primary wide">更新交接目录中的部署文件</button><p class="hint">编辑器和同文选择同一个专用目录。文件更新完成后，在同文执行同步、部署；不是实时同步。</p></div><button id="exportTrime" class="primary wide">生成并导出同文部署包 ZIP</button><h3>发布记录（最近五次）</h3><div id="releaseList"></div>';
 document.body.append(manager);$('manage').onclick=()=>{renderManager();manager.showModal();};$('closeRelease').onclick=()=>manager.close();$('snapshotDraft').onclick=()=>snapshot();$('backupDraft').onclick=saveBackup;$('exportTrime').onclick=()=>exportTrime(false);$('export').onclick=saveBackup;
 $('directoryTools').hidden=!window.AndroidFiles;$('pickTrimeDirectory').onclick=()=>AndroidFiles.chooseTrimeDirectory();$('writeTrimeDirectory').onclick=()=>exportTrime(true);
 const oldKeyboardTab=$('keyboardTab').onclick;$('keyboardTab').onclick=()=>{oldKeyboardTab();$('keyboardPanel').scrollIntoView({block:'start',behavior:'smooth'});};
 const originalImport=window.receiveLayout;window.receiveLayout=text=>{try{const p=JSON.parse(text);if(p.format!=='unicode-touch-backup-v2'){originalImport(text);return;}const layout=C.validate(p.layout,known),profile=W.validate(p.profile,known);importWorkspace={layout,profile};$('importSummary').textContent=`草稿备份：${layout.tiles.length} 个空间元素，${Object.keys(profile.entries).length} 份收藏资料，${Object.keys(profile.mobileKeys).length} 个手机按键。将替换草稿并先创建恢复点。`;$('importDialog').showModal();}catch(e){toast('导入失败：'+e.message);}};
 const originalConfirm=$('confirmImport').onclick;$('confirmImport').onclick=()=>{if(!importWorkspace){originalConfirm();return;}snapshot('导入前');restore(importWorkspace);importWorkspace=null;$('importDialog').close();};const originalCancel=$('cancelImport').onclick;$('cancelImport').onclick=()=>{importWorkspace=null;originalCancel();};
 try{const r=await fetch('trime-base/manifest.json');if(!r.ok)throw Error();baseManifest=await r.json();}catch(e){toast('同文基础包尚未生成；收藏编辑仍可使用');}
 writeDoc();$('search').placeholder='搜索符号、名称、码位；收藏支持中文名与标签';renderPersonalTools();
});
