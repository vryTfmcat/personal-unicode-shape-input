const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const query=async text=>{await page.locator('#search').fill(text);await page.locator('#filters button[type=submit]').click();};
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial13#queue=admittedT');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/3,653 字/);
  assert.equal(await page.locator('#followupQueues [data-category="装饰"]').count(),0);
  await page.locator('[data-queue=admittedB]').click();
  assert.match(await page.locator('#heading').innerText(),/174 字/);
  assert.equal(await page.locator('#followupQueues [data-category]').count(),5);
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1100});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  await page.setViewportSize({width:1440,height:1100});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v13-b-bucket.png')});
  await query('U+1CCA3');
  assert.equal(await page.locator('.character').getAttribute('data-first-key'),'b');
  assert.equal(await page.locator('.character').getAttribute('data-decision'),'include');
  await page.locator('[data-queue=tToBBoundary]').click();
  await query('U+2654');
  await page.getByLabel('U+2654 草案主桶',{exact:true}).selectOption('b');
  assert.equal(await page.locator('.character').count(),0);
  assert.match(await page.locator('[data-queue=admittedB]').innerText(),/175/);
  await page.locator('[data-queue=admittedB]').click();await query('U+2654');
  await page.getByLabel('U+2654 草案主桶',{exact:true}).selectOption('auto');
  assert.match(await page.locator('[data-queue=admittedB]').innerText(),/174/);
  await page.reload();await page.waitForSelector('#queues [data-queue=admittedT]');
  await page.locator('[data-queue=admittedT]').click();await query('U+2654');
  assert.equal(await page.getByLabel('U+2654 草案主桶',{exact:true}).getAttribute('aria-label'),'U+2654 草案主桶');
  assert.equal(await page.locator('.character').getAttribute('data-first-key'),'t');
  await page.locator('[data-queue=bBadges]').click();await query('🚾');
  assert.equal(await page.locator('.character').getAttribute('data-decision'),'exclude');
  assert.equal(await page.locator('.character').getAttribute('data-first-key'),'b');
  await page.getByLabel('U+1F6BE 我的判断',{exact:true}).selectOption('include');
  assert.equal(await page.locator('.character').count(),0);
  assert.match(await page.locator('[data-queue=admittedB]').innerText(),/175/);
  await page.goto('http://127.0.0.1:8766/shape-key-overview.html#round=1');
  await page.waitForSelector('#keyboard [data-key=b]');
  await page.locator('#keyboard [data-key=b]').click();
  assert.match(await page.locator('#keyInfo').innerText(),/图案／标识/);
  assert.match(await page.locator('#resultStatus').innerText(),/174/);
  await page.locator('[data-allocation=legacy]').click();
  assert.match(await page.locator('#keyInfo').innerText(),/历史第一位保留/);
  assert.deepEqual(errors,[]);
  console.log('v13: t/b partition, category filters, reversible manual overrides, reload, excluded badge reconsideration, overview and legacy mode, four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
