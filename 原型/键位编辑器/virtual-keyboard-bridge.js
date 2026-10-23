(()=>{
  let keyboardWindow=null;
  const send=()=>{if(keyboardWindow&&!keyboardWindow.closed)keyboardWindow.postMessage({type:'unicode-keyboard-character',item:window.keyEditor?.getSelectedItem?.()||null},location.origin);};
  const anchor=document.createElement('a');anchor.href='virtual-keyboard.html';anchor.className='button quiet';anchor.textContent='键盘标注 ↗';anchor.target='unicode-keyboard';
  anchor.addEventListener('click',e=>{e.preventDefault();keyboardWindow=window.open(anchor.href,'unicode-keyboard');if(!keyboardWindow)location.href=anchor.href;else send();});
  const host=document.querySelector('.topbar .brand');if(host)host.after(anchor);
  document.addEventListener('unicode-character-selected',send);
  window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===keyboardWindow&&e.data?.type==='unicode-keyboard-ready')send();});
})();
