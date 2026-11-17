const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial11#queue=admitted');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/3,629/);
  assert.match(await page.locator('#progress').innerText(),/初审待讨论 0 字/);
  assert.equal(await page.locator('#followupQueues [data-category="标识分类"]').count(),0);
  assert.equal(await page.locator('#followupQueues [data-category="标识"]').innerText(),'标识 · 6');
  for(const [topic,count] of [['omittedObjects',267],['omittedSigns',49],['omittedVariants',84]]){
   await page.locator(`#candidateQueues [data-queue=${topic}]`).click();
   assert.match(await page.locator('#heading').innerText(),new RegExp(`${count} 字`));
   assert.equal(await page.locator('.character[data-decision=include]').count(),0);
   assert.match(await page.locator('.character .suggestion').first().innerText(),/尚未收入/);
  }
  await page.locator('#candidateQueues [data-queue=omittedObjects]').click();
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  await page.setViewportSize({width:1440,height:1050});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v11-omissions.png')});
  assert.deepEqual(errors,[]);
  console.log('v11: latest decisions, corrected label, three candidate queues, four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
