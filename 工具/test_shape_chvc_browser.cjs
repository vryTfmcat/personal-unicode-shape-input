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
    await page.goto('http://127.0.0.1:8766/shape-key-overview.html#round=3&chvcTrial=preferred');
    await settled(418);
    assert(await page.locator('#chvcSummary').textContent().then(s=>s.includes('101')));
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('草案已将下方首选'));
    await page.screenshot({path:path.join(output,'chvc-priority-desktop.png'),fullPage:true});
    const groups={all:1562,positive:620,pending:942,fallback:1144,holes:107,attachments:19,parts:113,bars:26,centre:101,residual:861,largest:1188};
    for(const [kind,n] of Object.entries(groups)){
      await page.locator(`#chvcResultNav [data-chvc="${kind}"]`).click();await settled(n);
      assert(await page.locator(`#chvcResultNav [data-chvc="${kind}"]`).getAttribute('aria-pressed')==='true');
    }
    await page.reload();await settled(1188);
    await page.locator('#chvcResultNav [data-chvc="centre"]').click();await settled(101);
    await page.locator('#next').click();
    await page.waitForFunction(()=>document.querySelector('#page').textContent.startsWith('61'));
    for(const width of [1440,768,390,320]){
      await page.setViewportSize({width,height:900});
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow '+width);
      if(width===390)await page.screenshot({path:path.join(output,'chvc-centre-mobile.png'),fullPage:true});
    }
    await page.setViewportSize({width:1440,height:1000});
    await page.locator('[data-allocation="legacy"]').click();
    await page.locator('[data-round="3"]').click();await settled(1562);
    assert.equal(await page.locator('#error').textContent(),'');
    assert.deepEqual(errors,[]);console.log('chvc browser: groups, navigation, detail, history, compatibility and four widths passed');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
