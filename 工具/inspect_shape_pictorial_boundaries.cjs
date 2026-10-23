const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const report=JSON.parse(fs.readFileSync('原型/键位编辑器/data/pictorial-intake-review.json','utf8'));
 const chars=[...'☭⍾🔗🕨⛍🨊⯟𜱐𜱓𜲣𜷴🌒🙐🙘🚾',String.fromCodePoint(0x1CEBC)];
 const rows=chars.map(c=>report.records.find(r=>r.char===c));
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1200,height:1040}});
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html');
  await page.setContent('<html lang="zh-CN"><head><link rel="stylesheet" href="http://127.0.0.1:8766/fonts/editor-fonts.css"><style>body{font-family:system-ui;background:#f5f7f7;color:#222;margin:20px}h1{font-size:20px}main{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}article{border:1px solid #bbc9c5;background:#fff;padding:12px;min-width:0}.glyph{font-family:"Unicode Editor";font-size:78px;height:120px;display:flex;align-items:center;justify-content:center;color:#000}p{font-size:12px;overflow-wrap:anywhere;line-height:1.5;margin:5px 0}.cp{text-align:center;font-size:14px}</style></head><body><h1>拟物边界讨论 · 编辑器实际本地字形 · 尚未改审核结论</h1><main>'+rows.map(r=>`<article><div class="glyph">${r.char}</div><p class="cp">U+${r.cp.toString(16).toUpperCase()}</p><p>${r.name}</p><p>${r.block}</p></article>`).join('')+'</main></body></html>');
  await page.evaluate(()=>document.fonts.ready);
  const output=path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/boundary-discussion.png');
  await page.screenshot({path:output,fullPage:true});console.log(output);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
