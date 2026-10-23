const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
 try{
  const archived=JSON.parse(fs.readFileSync('数据/三模式/规则库/四键实验/键位试验/20261022-pictorial-intake-review-v3/拟物收入全量初稿.json','utf8'));
  await page.route('**/data/pictorial-intake-review.json',route=>route.fulfill({json:archived}));
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial3#queue=exclusionRepairs');
  await page.waitForSelector('.character');await page.evaluate(()=>document.fonts.ready);
  assert.match(await page.locator('#revision').innerText(),/不等于逐字全票通过/);
  assert.match(await page.locator('#heading').innerText(),/26 字/);
  assert.equal(await page.locator('.character[data-decision=exclude]').count(),26);
  assert.equal(await page.locator('#followupQueues button').count(),11);
  const output=path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review');
  await page.screenshot({path:path.join(output,'v3-exclusion-desktop.png'),fullPage:true});
  await page.locator('[data-queue=all]').click();
  const search=async c=>{await page.locator('#search').fill(c);await page.locator('#filters button[type=submit]').click();};
  for(const [char,state,category] of [['🙴','exclude','文字标点／抽象纹样'],['🙶','exclude','文字标点／抽象纹样'],['🙾','exclude','文字标点／抽象纹样'],['🙼','exclude','文字标点／抽象纹样'],['⽉','exclude','中文及汉字构件'],['㊊','exclude','中文及汉字构件'],['𝅒','exclude','乐谱记号'],['𝅓','exclude','乐谱记号'],['🥮','include','食物与饮品'],['𜲢','include','游戏图标'],['𜲣','include','游戏图标']]){
   await search(char);assert.equal(await page.locator('.character select').inputValue(),state);assert.equal(await page.locator('.category').innerText(),category);
  }
  await page.locator('#clear').click();await page.locator('[data-queue=moon]').click();
  assert.match(await page.locator('#heading').innerText(),/18 字/);
  for(const cp of [0x2F49,0x328A,0x1D152,0x1D153,0x1F96E])assert.equal(await page.locator(`.character[data-cp="${cp}"]`).count(),0);
  await page.screenshot({path:path.join(output,'v3-moon-desktop.png'),fullPage:true});
  await page.locator('[data-queue=decoration]').click();assert.match(await page.locator('#heading').innerText(),/28 字/);
  await page.locator('[data-queue=symbolic]').click();
  assert.equal(await page.locator(`.character[data-cp="${0x262E}"] select`).inputValue(),'');
  await page.locator('[data-queue=remainingFirst]').click();assert.match(await page.locator('#heading').innerText(),/58 字/);
  for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1000});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
  await page.screenshot({path:path.join(output,'v3-mobile.png'),fullPage:true});
  assert.equal(await page.locator('#error').innerText(),'');assert.deepEqual(errors,[]);
  console.log('v3 browser: scope approval, 26 exclusions, Chinese/music identity, mooncake food, both game cars, corrected queues and four widths passed');
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
