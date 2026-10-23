const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial7#queue=categoryRepairs');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/66 字/);
  for(const [char,category] of [['🐱','动物'],['💋','身体部位'],['🕐','工具与日常物品']]){
   await page.locator('#search').fill(char);await page.locator('#filters button[type=submit]').click();
   assert.equal(await page.locator('.character').count(),1);
   assert.equal(await page.locator('.category').innerText(),category);
  }
  await page.locator('#candidateQueues [data-queue=similarSigns]').click();
  assert.match(await page.locator('#heading').innerText(),/49 字/);
  await page.locator('#search').fill('☢');await page.locator('#filters button[type=submit]').click();
  assert.equal(await page.locator('.character').getAttribute('data-decision'),'pending');
  await page.locator('#candidateQueues [data-queue=egyptFish]').click();
  assert.match(await page.locator('#heading').innerText(),/30 字/);
  await page.locator('#egyptScope').selectOption('原区块');
  assert.match(await page.locator('#heading').innerText(),/9 字/);
  await page.locator('#egyptScope').selectOption('扩展A区块');
  assert.match(await page.locator('#heading').innerText(),/21 字/);
  await page.locator('#egyptScope').selectOption('');
  await page.locator('#search').fill('𓆟');await page.locator('#filters button[type=submit]').click();
  await page.locator('.character details').evaluate(e=>e.open=true);
  assert.match(await page.locator('.character details').innerText(),/fish with a long broad fin/);
  await page.locator('#candidateQueues [data-queue=nearC002]').click();
  assert.match(await page.locator('#heading').innerText(),/60 字/);
  await page.locator('#candidateQueues [data-queue=egyptPeople]').click();
  assert.match(await page.locator('#heading').innerText(),/1,348 字/);
  await page.locator('#candidateQueues [data-queue=egyptAnimals]').click();
  assert.match(await page.locator('#heading').innerText(),/894 字/);
  await page.locator('[data-queue=boundary]').click();
  assert.match(await page.locator('#heading').innerText(),/7,287/);
  await page.locator('#candidateQueues [data-queue=egyptFish]').click();
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v7-fish-desktop.png')});
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  assert.deepEqual(errors,[]);
  console.log('v7 browser: corrected classes, 49 symbol candidates, Egyptian series/official descriptions, unchanged boundaries and four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
