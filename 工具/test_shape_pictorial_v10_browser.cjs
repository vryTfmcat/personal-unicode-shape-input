const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial10#queue=admitted');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/3,620/);
  for(const old of ['安全标识','标识牌','自然物象／月相','人物与场景'])
   assert.equal(await page.locator(`#followupQueues [data-category="${old}"]`).count(),0);
  for(const [category,count] of [['人物与动作',907],['建筑与场所',42],['自然物象',71],['棋牌符号',204],['标识分类',6]]){
   await page.locator(`#followupQueues [data-category="${category}"]`).click();
   assert.match(await page.locator('#heading').innerText(),new RegExp(`${count} 字`));
  }
  await page.locator('[data-queue=admitted]').click();
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1050});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  await page.setViewportSize({width:1440,height:1050});
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/v10-categories.png')});
  assert.deepEqual(errors,[]);
  console.log('v10: five category counts, old labels removed, four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
