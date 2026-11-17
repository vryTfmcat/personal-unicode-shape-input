const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url'),{chromium}=require('playwright');
const output=path.resolve(__dirname,'../数据/三模式/规则库/四键实验/键位试验/20261024-other-large-collisions-v1');
const D=JSON.parse(fs.readFileSync(path.join(output,'其他大组分析.json'),'utf8'));
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>errors.push(r.url()));
 const url=pathToFileURL(path.join(output,'大组结构审阅.html')).href;
 async function reset(){await page.click('#reset');}
 try{
  await page.goto(url,{timeout:60000});await page.waitForSelector('.card');
  assert.equal(await page.locator('#comparison tbody tr').count(),D.groups.length);
  const first=D.groups[0];assert((await page.locator('#resultCount').textContent()).startsWith(first.count+' /'));
  await page.screenshot({path:path.join(output,'其他大组-桌面.png')});
  const alias=D.groups.find(g=>g.identicalMembershipCodes.length>1);
  await page.selectOption('#code',alias.code);const a=await page.locator('.card').evaluateAll(xs=>xs.map(x=>x.dataset.cp));
  await page.selectOption('#code',alias.identicalMembershipCodes.find(c=>c!==alias.code));assert.deepEqual(await page.locator('.card').evaluateAll(xs=>xs.map(x=>x.dataset.cp)),a);
  await page.selectOption('#code','all');await reset();assert((await page.locator('#resultCount').textContent()).startsWith(D.statistics.uniqueCharacters+' /'));
  await page.fill('#search','U+0034');assert.equal(await page.locator('.card').count(),1);await page.locator('.card').click();await page.waitForSelector('#detail[open]');assert.equal(await page.locator('#variants tr').count(),9);
  await page.screenshot({path:path.join(output,'其他大组-详情.png')});await page.click('#close');await page.selectOption('#view','plain');
  assert.equal(await page.locator('.sprite').first().evaluate(async el=>{const im=new Image();im.src=el.style.backgroundImage.slice(5,-2);await im.decode();return im.naturalWidth}),1280);
  await reset();await page.selectOption('#status','filled-face');assert((await page.locator('#resultCount').textContent()).startsWith((D.statistics.statusCounts['filled-face']||0)+' /'));
  await page.screenshot({path:path.join(output,'其他大组-实心面.png')});await reset();await page.selectOption('#facet-loops','1');assert((await page.locator('#resultCount').textContent()).startsWith(D.records.filter(r=>r.statistics&&r.statistics.loops===1).length+' /'));
  await page.reload();assert.equal(await page.locator('#facet-loops').inputValue(),'1');await reset();
  const seen=new Set();for(let i=0;i<3;i++){for(const cp of await page.locator('.card').evaluateAll(xs=>xs.map(x=>x.dataset.cp))){assert(!seen.has(cp));seen.add(cp);}await page.click('#next');}
  await page.goto(url+'#code=all&status=all&page=999999&view=annotated');await page.waitForSelector('.card');assert(await page.locator('#next').isDisabled());assert.equal(await page.locator('.card').count(),D.statistics.uniqueCharacters%48||48);
  await page.goto(url+'#code=mdez&status=all&page=0&view=annotated');await page.waitForSelector('.card');await page.screenshot({path:path.join(output,'其他大组-mdez.png')});
  for(const width of [768,390,320]){await page.setViewportSize({width,height:1000});await page.evaluate(()=>scrollTo(0,0));assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(output,`其他大组-${width}.png`)});}
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(output,'浏览器验收.json'),JSON.stringify({passed:true,codeGroups:D.groups.length,uniqueCharacters:D.statistics.uniqueCharacters,aliases:true,nineVariants:true,rawSprites:true,scopeFilters:true,refresh:true,firstAndLastPages:true,viewports:[1440,768,390,320],errors},null,2));console.log('other groups browser checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
