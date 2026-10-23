const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium}=require('playwright');
const output=path.resolve(__dirname,'../原型/键位编辑器/测试输出/shape-key-overview');
fs.mkdirSync(output,{recursive:true});
(async()=>{
  const browser=await chromium.launch({headless:true,channel:'msedge'});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400)errors.push(r.status()+' '+r.url());});
  async function settled(n){await page.waitForFunction(n=>document.querySelector('#resultStatus').textContent.startsWith(n+' 个'),n.toLocaleString('zh-CN'));}
  try{
    await page.goto('http://127.0.0.1:8766/shape-key-overview.html#round=3&centre=stable');
    const boot=await (await page.request.get('http://127.0.0.1:8766/api/shape-overview/bootstrap')).json();
    const c=boot.centreTrial;assert(c,'centre report absent');await settled(c.stableCharacters);
    assert(await page.locator('#centrePanel').isVisible());
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('o中心'));
    const frozen=await (await page.request.get('http://127.0.0.1:8766/api/shape-overview/query?centre=frozen&allocation=1')).json();
    const groups={preferred:c.newPreferredCharacters,gap:101,unstable:c.unstableCharacters,all:c.baseCentreCharacters,frozen:frozen.total,stable:c.stableCharacters};
    for(const [kind,n] of Object.entries(groups)){
      await page.locator(`#centreResultNav [data-centre="${kind}"]`).click();await settled(n);
    }
    await page.reload();await settled(c.stableCharacters);
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('o中心'));
    assert(await page.locator('#results .candidate').first().textContent().then(t=>t.includes('中心：')));
    await page.screenshot({path:path.join(output,'centre-desktop.png')});
    for(const [code,n] of Object.entries(c.codeCounts)){
      await page.locator(`#centreSummary [data-prefix="${code}"]`).click();await settled(n);
    }
    await page.locator('[data-round="1"]').click();
    await page.locator('[data-position="4"]').click();await page.locator('[data-key="o"]').click();
    await settled(c.stableCharacters);assert(await page.locator('#keyInfo').textContent().then(t=>t.includes('中心')));
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow '+width);
      if(width===390)await page.screenshot({path:path.join(output,'centre-mobile.png'),fullPage:true});
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('[data-allocation="legacy"]').click();await settled(0);
    assert(await page.locator('#centrePanel').isHidden());
    await page.locator('[data-allocation="draft"]').click();await settled(c.stableCharacters);
    assert.deepEqual(errors,[]);console.log('centre browser: new codes, fourth key, six queues, legacy isolation and four widths passed');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
