const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const r=JSON.parse(fs.readFileSync('原型/键位编辑器/data/pictorial-intake-review.json','utf8'));
  await page.addInitScript(({version,hash})=>localStorage.setItem(version+':'+hash,
   JSON.stringify({'9800':{decision:'exclude',note:'原备注保留'},'129678':{decision:'exclude'}})),
   {version:r.predecessorVersion,hash:r.sourceIndexSHA256});
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html?v=pictorial15#queue=admittedB&category='+encodeURIComponent('星座'));
  await page.waitForSelector('.character');
  assert.match(await page.locator('#heading').innerText(),/星座 · 13 字/);
  assert.equal(await page.locator('.character').count(),13);
  assert.equal(await page.locator('.character[data-first-key=b][data-decision=include]').count(),13);
  assert.equal(await page.getByLabel('U+2648 备注',{exact:true}).inputValue(),'原备注保留');
  await page.locator('[data-queue=admittedT]').click();
  assert.match(await page.locator('#heading').innerText(),/3,493 字/);
  await page.locator('#search').fill('U+1FA8E');await page.locator('#filters button[type=submit]').click();
  assert.equal(await page.locator('.character').getAttribute('data-decision'),'include');
  await page.locator('[data-queue=egyptAnimalParts]').click();
  assert.match(await page.locator('#heading').innerText(),/140 字/);
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:1100});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);
  }
  assert.deepEqual(errors,[]);
  console.log('v15: zodiac13, treasure in t, predecessor exclusions revised with notes retained, pending140 and four widths passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
