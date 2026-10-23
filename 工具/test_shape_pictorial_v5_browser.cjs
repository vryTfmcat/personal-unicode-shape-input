const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial5#queue=games&q=U%2B1CCA3');
  await page.waitForSelector('.character');await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('.character').count(),1);
  assert.equal(await page.locator('.category').innerText(),'游戏图标');
  assert.match(await page.locator('.character').innerText(),/仅保留t入口/);
  assert.equal(await page.locator('.character select').inputValue(),'include');
  assert.equal(await page.locator('[data-queue=dual]').count(),0);
  assert.doesNotMatch(await page.locator('#revision').innerText(),/几何入口待补建/);
  await page.locator('.character details').evaluate(e=>e.open=true);
  assert.match(await page.locator('.character details').innerText(),/不保留、不补建t外几何入口/);
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v5-t-only-desktop.png'),fullPage:true});
  for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1050});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
  await page.goto('http://127.0.0.1:8766/shape-key-overview.html?v=pictorial5#round=1');
  await page.locator('[data-key=t]').click();
  assert.match(await page.locator('#keyInfo').innerText(),/不设双入口个例/);
  assert.doesNotMatch(await page.locator('#keyInfo').innerText(),/几何入口待补建/);
  assert.deepEqual(errors,[]);
  console.log('v5 browser: t-only game entry, removed exception queue, updated overview and four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
