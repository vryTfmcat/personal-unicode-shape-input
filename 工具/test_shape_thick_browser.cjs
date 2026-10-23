const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const path=require('node:path');
const output=path.resolve(__dirname,'../原型/键位编辑器/测试输出/shape-key-overview');
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'msedge'});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});
  async function settled(n){await page.waitForFunction(n=>document.querySelector('#resultStatus').textContent.startsWith(n+' 个'),n.toLocaleString('zh-CN'));}
  try{
    await page.goto('http://127.0.0.1:8766/shape-key-overview.html?v=thick1#round=3&thickRepair=improved');
    await settled(228);
    assert(await page.locator('#thickPanel').isVisible());
    assert(await page.locator('#thickSummary').textContent().then(t=>t.includes('620 → 762')));
    for(const [kind,n] of Object.entries({newStable:142,stable:762,pending:800,all:1562,improved:228})){
      await page.locator(`#thickResultNav [data-thick="${kind}"]`).click();await settled(n);
    }
    await page.reload();await settled(228);
    await page.fill('#character','T');await page.locator('#search [type="submit"]').click();await settled(1);
    await page.locator('#results .candidate').click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('6/9 → 9/9'));
    assert(await page.locator('#detail').textContent().then(t=>t.includes('chmw')));
    await page.screenshot({path:path.join(output,'thick-repair-desktop.png'),fullPage:true});
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow '+width);
      if(width===390)await page.screenshot({path:path.join(output,'thick-repair-mobile.png'),fullPage:true});
    }
    const raw=await (await page.request.get('http://127.0.0.1:8766/api/shape-overview/query?prefix=chvc&allocation=1')).json();
    assert.equal(raw.total,1562);assert.deepEqual(errors,[]);
    console.log('thick repair browser: five queues, latest T evidence, unchanged lookup and four widths passed');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
