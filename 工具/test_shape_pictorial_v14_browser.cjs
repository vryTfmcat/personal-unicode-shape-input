const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const r=JSON.parse(fs.readFileSync('原型/键位编辑器/data/pictorial-intake-review.json','utf8'));
  await page.addInitScript(({version,hash})=>localStorage.setItem(version+':'+hash,JSON.stringify({
   '128702':{decision:'exclude',note:'保留的备注',firstKey:'t',category:'字母标识'}})),
   {version:r.predecessorVersion,hash:r.sourceIndexSHA256});
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial14#queue=admittedB');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/599 字/);
  for(const c of ['自然物象','人脸与表情','棋牌符号','字符标识'])assert.equal(await page.locator(`#followupQueues [data-category="${c}"]`).count(),1);
  assert.equal(await page.locator('#candidateQueues [data-queue=bBadges]:visible').count(),0);
  await page.locator('#search').fill('🚾');await page.locator('#filters button[type=submit]').click();
  assert.equal(await page.locator('.character').getAttribute('data-first-key'),'b');
  assert.equal(await page.locator('.character').getAttribute('data-decision'),'include');
  assert.equal(await page.locator('.character .category').innerText(),'字符标识');
  assert.equal(await page.getByLabel('U+1F6BE 备注',{exact:true}).inputValue(),'保留的备注');
  await page.locator('[data-queue=admittedT]').click();
  assert.match(await page.locator('#heading').innerText(),/3,279 字/);
  for(const c of ['自然物象','人脸与表情','棋牌符号'])assert.equal(await page.locator(`#followupQueues [data-category="${c}"]`).count(),0);
  await page.locator('[data-queue=egyptAnimalParts]').click();
  assert.match(await page.locator('#heading').innerText(),/148 字/);
  assert.match(await page.locator('#queueDescription').innerText(),/不是现代写实部位图/);
  assert.match(await page.locator('.character[data-cp="78126"] .egyptian-explanation').innerText(),/牛肋骨/);
  assert.match(await page.locator('.character[data-cp="78130"] .egyptian-explanation').innerText(),/肠.*右下/);
  assert.equal(await page.locator('.character[data-decision=include]').count(),0);
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1100});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  await page.setViewportSize({width:1440,height:1100});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v14-parts-explained.png')});
  assert.deepEqual(errors,[]);
  console.log('v14: approved categories in b, all 43 badges admitted, old exclusion override with note retained, 148 parts explained but unadmitted, four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
