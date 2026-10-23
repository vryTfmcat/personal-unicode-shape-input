const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
 try{
  await page.goto('http://127.0.0.1:8766/pictorial-intake-review.html');
  await page.waitForSelector('.character');await page.evaluate(()=>document.fonts.ready);
  assert.match(await page.locator('#scope').innerText(),/159,345/);
  assert.equal(await page.locator('#cards .character').count(),48);
  assert.match(await page.locator('#heading').innerText(),/建议收入/);
  assert.equal(await page.locator('#error').innerText(),'');
  const output=path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review');fs.mkdirSync(output,{recursive:true});
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  for(const q of ['confirmed','boundary','exclude','all','propose']){
   await page.locator(`[data-queue=${q}]`).click();await page.waitForSelector('.character');
   assert.equal(await page.locator(`[data-queue=${q}]`).getAttribute('aria-pressed'),'true');
  }
  await page.locator('[data-queue=all]').click();
  await page.locator('#search').fill('𓆟');await page.locator('#filters button[type=submit]').click();
  assert.equal(await page.locator('.character').count(),1);assert.match(await page.locator('.cp').innerText(),/1319F/);
  assert.match(await page.locator('.suggestion').innerText(),/原例已确认/);
  await page.locator('#search').fill('U+1F41F');await page.locator('#filters button[type=submit]').click();
  await page.locator('.character select').selectOption('include');
  await page.reload();await page.waitForSelector('.character');
  assert.equal(await page.locator('.character select').inputValue(),'include');
  const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;
  const data=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  assert.equal(data.decisions.find(r=>r.cp===0x1F41F).decision,'include');
  await page.locator('.character select').selectOption('exclude');
  await page.locator('#import').setInputFiles({name:'review.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
  await page.waitForFunction(()=>document.querySelector('.character select').value==='include');
  await page.locator('#import').setInputFiles({name:'wrong.json',mimeType:'application/json',buffer:Buffer.from('{}')});
  await page.waitForFunction(()=>document.querySelector('#error').textContent.includes('不匹配'));
  assert.equal(await page.locator('.character select').inputValue(),'include');
  await page.reload();await page.waitForSelector('.character');assert.equal(await page.locator('#error').innerText(),'');
  await page.locator('#clear').click();await page.locator('[data-queue=boundary]').click();
  await page.locator('#category').selectOption('象形·鱼类');await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:path.join(output,'hieroglyphs.png'),fullPage:true});
  await page.locator('#clear').click();await page.locator('[data-queue=propose]').click();
  await page.locator('#next').click();assert.match(await page.locator('#page').innerText(),/49/);
  await page.reload();await page.waitForSelector('.character');assert.match(await page.locator('#page').innerText(),/49/);
  await page.locator('#prev').click();await page.locator('#bulk').selectOption('uncertain');page.once('dialog',d=>d.accept());await page.locator('#applyBulk').click();
  assert.equal(await page.locator('.character[data-decision=uncertain]').count(),48);
  for(const width of [1440,768,390,320]){
   await page.setViewportSize({width,height:950});await page.evaluate(()=>document.fonts.ready);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
  }
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  const raw=await (await page.request.get('http://127.0.0.1:8766/api/shape-overview/query?prefix=chvc')).json();
  assert.equal(raw.total,1562);
  await page.goto('http://127.0.0.1:8766/shape-key-overview.html?v=pictorial1#round=1');
  await page.locator('[data-key=t]').click();assert.match(await page.locator('#keyInfo').innerText(),/拟物.*收入待审/);
  assert.match(await page.locator('#keyInfo').innerText(),/尚未迁移/);
  assert.equal(await page.locator('#keyInfo a[href="pictorial-intake-review.html"]').count(),1);
  assert.deepEqual(errors,[]);
  console.log('pictorial browser: all queues, filters, persistence, export/import, invalid import, pagination, bulk review, four widths and unchanged chvc passed');
 }finally{await context.close();await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
