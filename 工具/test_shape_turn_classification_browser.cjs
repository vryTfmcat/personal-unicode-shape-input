const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const output=path.resolve(__dirname,'../数据/三模式/规则库/四键实验/键位试验/20261024-chvc-turn-classification-v1');
const data=JSON.parse(fs.readFileSync(path.join(output,'分类数据.json'),'utf8'));
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('requestfailed',r=>errors.push(r.url()+' '+r.failure().errorText));
 const base=pathToFileURL(path.join(output,'分类审阅.html')).href;
 async function noOverflow(){assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow');}
 async function reset(){await page.click('#reset');await page.waitForFunction(()=>document.querySelector('#resultCount').textContent.startsWith('1554 /'));}
 try{
  await page.goto(base);await page.waitForFunction(()=>document.querySelectorAll('.card').length===48);
  assert((await page.locator('#summary').textContent()).includes('1554'));
  await noOverflow();
  const ink=await page.locator('.sprite').first().evaluate(async el=>{const img=new Image();img.src=el.style.backgroundImage.slice(5,-2);await img.decode();return img.naturalWidth;});
  assert.equal(ink,1536);
  await page.screenshot({path:path.join(output,'审阅页-桌面.png')});
  await page.fill('#search','U+1C64');assert.equal(await page.locator('.card').count(),1);
  await page.locator('.card').click();await page.waitForSelector('#detail[open]');
  assert((await page.locator('#detailText').textContent()).includes('直3＋曲1＝4段'));
  assert.equal(await page.locator('#variantRows tr').count(),9);
  await page.screenshot({path:path.join(output,'审阅页-1C64详情.png')});
  await page.click('#closeDetail');await page.selectOption('#view','plain');
  assert((await page.locator('.sprite').first().getAttribute('style')).includes('plain.png'));
  await page.reload();assert.equal(await page.locator('.card').count(),1);assert.equal(await page.locator('#search').inputValue(),'U+1C64');
  await reset();await page.click('[data-mode="pending-unstable"]');
  assert((await page.locator('#resultCount').textContent()).startsWith(String(data.statistics.unstableNineVariants)+' /'));
  await page.screenshot({path:path.join(output,'审阅页-不稳定.png')});
  await reset();await page.locator('#groupList button').first().click();
  assert((await page.locator('#resultCount').textContent()).startsWith(String(data.groups[0].count)+' /'));
  await reset();
  const seen=new Set();
  while(true){for(const cp of await page.locator('.card').evaluateAll(xs=>xs.map(x=>Number(x.dataset.cp)))){assert(!seen.has(cp));seen.add(cp);}if(await page.locator('#next').isDisabled())break;await page.click('#next');}
  assert.equal(seen.size,1554);assert.deepEqual([...seen].sort((a,b)=>a-b),data.records.map(r=>r.cp).sort((a,b)=>a-b));
  await reset();await page.selectOption('#facet-corners','1');
  assert((await page.locator('#resultCount').textContent()).startsWith(String(data.records.filter(r=>r.statistics.corners===1).length)+' /'));
  await reset();
  for(const width of [768,390,320]){await page.setViewportSize({width,height:950});await noOverflow();await page.screenshot({path:path.join(output,`审阅页-${width}.png`)});}
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(output,'浏览器验收.json'),JSON.stringify({passed:true,engine:'Edge/Playwright',cohortPagination:1554,viewports:[1440,768,390,320],searchAndDetail:true,rawViewAndRefresh:true,statusAndFeatureFilters:true,groups:true,noHorizontalOverflow:true,pageErrors:errors},null,2));
  console.log('classification browser checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
