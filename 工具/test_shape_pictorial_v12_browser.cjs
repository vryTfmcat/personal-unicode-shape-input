const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  const r=JSON.parse(fs.readFileSync('原型/键位编辑器/data/pictorial-intake-review.json','utf8'));
  await page.addInitScript(({version,hash})=>localStorage.setItem(version+':'+hash,
   JSON.stringify({'80744':{decision:'exclude',note:''},'80794':{decision:'exclude',note:''}})),
   {version:r.predecessorVersion,hash:r.sourceIndexSHA256});
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial12#queue=admitted&category=动物部位');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/131 字/);
  assert.match(await page.locator('#progress').innerText(),/3,827 字/);
  assert.match(await page.locator('#revision').innerText(),/不收入 60 字/);
  assert.equal(await page.locator('html').getAttribute('translate'),'no');
  assert.equal(await page.locator('meta[name=google]').getAttribute('content'),'notranslate');
  for(const cp of [80744,80794]){
   await page.locator('#search').fill('U+'+cp.toString(16));
   await page.locator('#filters button[type=submit]').click();
   const card=page.locator(`.character[data-cp="${cp}"]`);
   assert.equal(await card.getAttribute('data-decision'),'include');
   assert.equal(await card.locator('.category').innerText(),'动物部位');
   assert.equal(await card.locator('.glyph').getAttribute('translate'),'no');
  }
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  await page.setViewportSize({width:1440,height:1050});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v12-correction.png')});
  assert.deepEqual(errors,[]);
  console.log('v12: two exclusions overridden after migration, latest counts, translation protection, four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
