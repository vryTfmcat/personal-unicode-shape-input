const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial6');
  await page.waitForSelector('.character');await page.evaluate(()=>document.fonts.ready);
  assert.match(await page.locator('#heading').innerText(),/1,258/);
  assert.equal(await page.locator('#queues button').count(),3);
  assert.equal(await page.locator('#followupQueues button').count(),21);
  assert.equal(await page.locator('.second-confirm input:checked').count(),0);
  assert.equal(await page.locator('[data-queue=exclude]').count(),0);
  await page.locator('[data-category="装饰"]').click();
  assert.match(await page.locator('#heading').innerText(),/24 字/);
  assert.equal(await page.locator('.character').count(),24);
  await page.locator('.second-confirm input').first().check();
  const reviewedCP=await page.locator('.character').first().getAttribute('data-cp');
  await page.locator('.category-choice').first().selectOption('植物');
  assert.equal(await page.locator('.character').count(),23);
  await page.reload();await page.waitForSelector('.character');
  await page.locator('[data-category="植物"]').click();
  const modified=page.locator(`.character[data-cp="${reviewedCP}"]`);
  assert.equal(await modified.locator('.second-confirm input').isChecked(),true);
  await modified.locator('details').evaluate(e=>e.open=true);
  await modified.locator('input[placeholder="备注"]').fill('浏览器二审往返测试');
  await modified.locator('input[placeholder="备注"]').press('Tab');
  const saved=page.waitForResponse(r=>r.url().endsWith('/api/pictorial-review/save'));
  await page.locator('#saveProject').click();
  const receipt=await (await saved).json();assert.equal(receipt.saved,true);
  const payload=JSON.parse(fs.readFileSync(receipt.path,'utf8'));
  assert.deepEqual({...payload.decisions.find(d=>d.cp===Number(reviewedCP))},
   {cp:Number(reviewedCP),char:String.fromCodePoint(Number(reviewedCP)),decision:'include',category:'植物',secondReviewed:true,note:'浏览器二审往返测试'});
  // Do not persist simulated human choices in the real project archive.
  fs.unlinkSync(receipt.path);
  await page.locator('[data-queue=admitted]').click();
  await page.locator('#search').fill('U+1F674');await page.locator('#filters button[type=submit]').click();
  assert.equal(await page.locator('.character').count(),0);
  await page.locator('[data-queue=unresolved]').click();
  assert.match(await page.locator('#heading').innerText(),/58 字/);
  await page.locator('[data-queue=boundary]').click();
  assert.match(await page.locator('[data-queue=boundary]').innerText(),/7,303/);
  assert.match(await page.locator('#heading').innerText(),/7,287/);
  assert.equal(await page.locator('.character[data-decision=exclude]').count(),0);
  const backup=await context.request.get('http://127.0.0.1:8766/data/pictorial-intake-archive.zip');
  assert.equal(backup.status(),200);assert.equal((await backup.body()).subarray(0,2).toString(),'PK');
  await page.locator('[data-queue=admitted]').click();
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
   assert(await page.evaluate(()=>[...document.querySelectorAll('.character select')].every(e=>e.getBoundingClientRect().right<=innerWidth)),`select overflow ${width}`);
  }
  await page.setViewportSize({width:1440,height:1050});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v6-desktop.png')});
  assert.deepEqual(errors,[]);
  console.log('v6 browser: categories, independent second confirmation, edits/save/reload, hidden exclusions, preserved boundary and four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
