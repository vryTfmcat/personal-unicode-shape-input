const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial4#queue=ornamentalPartition');
  await page.waitForSelector('.character');await page.evaluate(()=>document.fonts.ready);
  assert.match(await page.locator('#revision').innerText(),/24(?:字)?装饰、4(?:字)?物品火箭、20(?:字不收入t|排除)/);
  assert.equal(await page.locator('.character').count(),48);
  assert.equal(await page.locator('.character[data-decision=include]').count(),28);
  assert.equal(await page.locator('.character[data-decision=exclude]').count(),20);
  for(let cp=0x1F650;cp<=0x1F67F;cp++){
   const card=page.locator(`.character[data-cp="${cp}"]`);
   const floral=cp<0x1F668,rocket=cp>=0x1F66C&&cp<0x1F670;
   assert.equal(await card.locator('select').inputValue(),floral||rocket?'include':'exclude');
   assert.equal(await card.locator('.category').innerText(),floral?'装饰':rocket?'物品／火箭':'文字标点／抽象纹样');
  }
  await page.locator('[data-queue=decoration]').click();assert.match(await page.locator('#heading').innerText(),/24 字/);
  const output=path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review');
  await page.screenshot({path:path.join(output,'v4-floral-desktop.png'),fullPage:true});
  await page.locator('[data-queue=rockets]').click();assert.equal(await page.locator('.character').count(),4);
  for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1050});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
  await page.screenshot({path:path.join(output,'v4-rockets-mobile.png'),fullPage:true});
  assert.equal(await page.locator('#error').innerText(),'');assert.deepEqual(errors,[]);
  console.log('v4 browser: all 48 character decisions/categories, floral 24, rockets 4, excluded 20 and four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
