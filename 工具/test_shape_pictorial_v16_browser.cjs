const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const report=JSON.parse(fs.readFileSync('原型/键位编辑器/data/pictorial-intake-review.json','utf8'));
  await page.addInitScript(({version,hash})=>localStorage.setItem(version+':'+hash,
   JSON.stringify({'10047':{category:'植物',firstKey:'t',note:'原备注保留'},'128704':{secondReviewed:false}})),
   {version:report.predecessorVersion,hash:report.sourceIndexSHA256});
  await page.goto('http://127.0.0.1:8765/pictorial-intake-review.html?v=pictorial16#queue=boundary');
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/4,401 字/);
  assert.equal(await page.locator('.character[data-decision=include]').count(),0);
  assert.equal(await page.locator('[data-queue=tToBBoundary],[data-queue=categoryRepairs13],[data-queue=egyptAnimalParts]').count(),0);
  await page.locator('[data-queue=admittedB]').click();
  await page.locator('#followupQueues [data-category="花"]').click();
  assert.equal(await page.locator('.character').count(),4);
  assert.equal(await page.locator('.character[data-first-key=b][data-decision=include]').count(),4);
  assert.equal(await page.getByLabel('U+273F 备注',{exact:true}).inputValue(),'原备注保留');
  await page.locator('[data-queue=roundFlowers]').click();
  assert.equal(await page.locator('.character').count(),10);
  assert.equal(await page.locator('.character[data-decision=exclude]').count(),3);
  assert.equal(await page.locator('.character[data-decision=pending]').count(),7);
  await page.screenshot({path:'原型/键位编辑器/测试输出/pictorial-intake-review/v16-flower-candidates.png',fullPage:true});
  await page.locator('[data-queue=pictorialUnresolved]').click();
  assert.match(await page.locator('#heading').innerText(),/2,036 字/);
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1100});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  assert.equal(await page.locator('#error').innerText(),'');
  assert.deepEqual(errors,[]);
  console.log('v16 passed: unresolved-only boundary, retired queues, floral b4 + pending7/excluded3, inherited notes, Egyptian merge, four widths');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});

