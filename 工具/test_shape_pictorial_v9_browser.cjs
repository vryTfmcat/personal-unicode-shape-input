const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial9#queue=admitted');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/3,620/);
  assert.equal(await page.locator('#followupQueues [data-category="象形·形象待辨"]').count(),0);
  for(const [category,count] of [['人物与动作',904],['人物与神形',513],['动物',666],['鸟类',334],['鱼类',30],['昆虫',35],['动物部位',48]]){
   await page.locator(`#followupQueues [data-category="${category}"]`).click();
   assert.match(await page.locator('#heading').innerText(),new RegExp(`${count} 字`));
  }
  assert.equal(await page.locator('#candidateQueues button:visible').count(),2);
  await page.locator('#candidateQueues [data-queue=egyptAnimalParts]').click();
  assert.match(await page.locator('#heading').innerText(),/241 字/);
  assert.equal(await page.locator('.character[data-decision=include]').count(),0);
  await page.locator('[data-queue=admitted]').click();
  for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1050});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
  await page.setViewportSize({width:1440,height:1050});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v9-categories.png')});
  assert.deepEqual(errors,[]);
  console.log('v9: all admitted characters in concrete categories, no admitted-unknown bucket, unresolved queues only, four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
