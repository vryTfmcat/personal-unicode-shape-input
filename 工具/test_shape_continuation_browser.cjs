const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');const {chromium}=require('playwright');
const output=path.resolve(__dirname,'../数据/三模式/规则库/四键实验/键位试验/20261024-stroke-continuation-trial-v1');
const data=JSON.parse(fs.readFileSync(path.join(output,'分类数据.json'),'utf8'));
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>errors.push(r.url()));
 const url=pathToFileURL(path.join(output,'分类审阅.html')).href;
 async function reset(){await page.click('#reset');assert((await page.locator('#resultCount').textContent()).startsWith('1554 /'));}
 try{
  await page.goto(url);await page.waitForSelector('.card');
  assert.equal(await page.locator('#facet-loops').count(),1);assert.equal(await page.locator('#facet-strokeCount').count(),1);
  await page.screenshot({path:path.join(output,'连续笔审阅-桌面.png')});
  for(const [cp,text] of [['0054','连续笔 2'],['A4EC','连续笔 3'],['A694','直0／曲2'],['0034','环 1']]){
   await page.fill('#search','U+'+cp);assert.equal(await page.locator('.card').count(),1);
   await page.locator('.card').click();await page.waitForSelector('#detail[open]');
   assert((await page.locator('#detailText').textContent()).includes(text));assert.equal(await page.locator('#variantRows tr').count(),9);
   await page.screenshot({path:path.join(output,`连续笔审阅-${cp}.png`)});await page.click('#closeDetail');
  }
  await page.selectOption('#view','plain');
  const width=await page.locator('.sprite').first().evaluate(async el=>{const im=new Image();im.src=el.style.backgroundImage.slice(5,-2);await im.decode();return im.naturalWidth;});assert.equal(width,1536);
  await reset();await page.selectOption('#facet-loops','1');assert((await page.locator('#resultCount').textContent()).startsWith(data.records.filter(r=>r.statistics.loops===1).length+' /'));
  await page.reload();assert.equal(await page.locator('#facet-loops').inputValue(),'1');
  await reset();const seen=new Set();while(true){for(const cp of await page.locator('.card').evaluateAll(xs=>xs.map(x=>Number(x.dataset.cp)))){assert(!seen.has(cp));seen.add(cp);}if(await page.locator('#next').isDisabled())break;await page.click('#next');}assert.equal(seen.size,1554);
  await reset();await page.click('[data-mode="pending-unstable"]');assert((await page.locator('#resultCount').textContent()).startsWith(data.statistics.unstableNineVariants+' /'));await reset();
  for(const width of [768,390,320]){await page.setViewportSize({width,height:1000});await page.evaluate(()=>scrollTo(0,0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(output,`连续笔审阅-${width}.png`)});}
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(output,'浏览器验收.json'),JSON.stringify({passed:true,viewports:[1440,768,390,320],samples:['T','ꓬ','Ꚕ','4'],fullPagination:1554,ringAndStrokeFilters:true,rawView:true,refresh:true,errors},null,2));console.log('continuation browser checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
