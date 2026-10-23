const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const data=JSON.parse(fs.readFileSync('数据/三模式/规则库/四键实验/键位试验/20261022-pictorial-intake-review-v2/拟物收入全量初稿.json','utf8'));
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1100}});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
 try{
  await page.route('**/data/pictorial-intake-review.json',route=>route.fulfill({json:data}));
  await page.addInitScript(({version,sha})=>{
   const key=version+':'+sha;
   if(!localStorage.getItem(key))localStorage.setItem(key,JSON.stringify({
    '9773':{decision:'uncertain',note:'原备注不丢失'},
    '117840':{decision:'uncertain'},'128702':{decision:'uncertain'},'9086':{decision:'uncertain'}
   }));
  },{version:data.predecessorVersion,sha:data.sourceIndexSHA256});
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial2#queue=remainingFirst');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#revision').innerText(),/59/);
  assert.match(await page.locator('#heading').innerText(),/59 字/);
  assert.equal(await page.locator('#followupQueues button').count(),10);
  for(const [key,value] of Object.entries(data.reviewQueues)){
   await page.locator(`#followupQueues [data-queue=${key}]`).click();
   assert.match(await page.locator('#heading').innerText(),new RegExp(`${value.cps.length.toLocaleString()} 字`));
  }
  const output=path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review');
  await page.locator('[data-queue=symbolic]').click();await page.evaluate(()=>document.fonts.ready);
  assert.equal(await page.locator('.character').count(),32);
  await page.screenshot({path:path.join(output,'v2-symbols-desktop.png'),fullPage:true});
  await page.locator('[data-queue=all]').click();
  const search=async text=>{await page.locator('#search').fill(text);await page.locator('#filters button[type=submit]').click();};
  await search('☭');assert.equal(await page.locator('.character select').inputValue(),'include');
  assert.equal(await page.locator('.category').innerText(),'象征标志');
  await page.locator('.character details').evaluate(e=>e.open=true);
  assert.equal(await page.locator('.character input').inputValue(),'原备注不丢失');
  for(const [char,state,category] of [['🚾','exclude','字母标识'],['𜱐','include','游戏图标'],['🙙','include','装饰'],['🌒','include','自然物象／月相'],['🨊','include','标识牌'],['⍾','uncertain','象征标志']]){
   await search(char);assert.equal(await page.locator('.character select').inputValue(),state);assert.equal(await page.locator('.category').innerText(),category);
  }
  await search('U+1CCA3');assert.match(await page.locator('.character').innerText(),/几何入口待补建/);
  assert.equal(await page.locator('.character select').inputValue(),'include');
  await page.locator('.character details').evaluate(e=>e.open=true);
  assert.match(await page.locator('.character details').innerText(),/无现成普通主桶或几何细码/);
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  await page.screenshot({path:path.join(output,'v2-dual-mobile.png'),fullPage:true});
  await page.locator('#clear').click();await page.locator('[data-queue=remainingFirst]').click();
  await page.locator('.character select').first().selectOption('include');
  assert.match(await page.locator('#heading').innerText(),/58 字/);
  await page.reload();await page.waitForSelector('.character');assert.match(await page.locator('#heading').innerText(),/58 字/);
  assert.match(await page.locator('#revision').innerText(),/58 项/);
  assert.equal(await page.locator('#error').innerText(),'');assert.deepEqual(errors,[]);
  console.log('v2 browser: ten queues, v1 draft migration, confirmed overrides, preserved note, exception truth, dynamic remaining count and four widths passed');
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
