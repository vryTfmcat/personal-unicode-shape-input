const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require('playwright');
const output=path.resolve(__dirname,'../原型/键位编辑器/测试输出/shape-key-overview');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  try {
    await page.goto('http://127.0.0.1:8766/shape-key-overview.html#round=1');
    await page.waitForFunction(()=>document.querySelector('#resultStatus').textContent.includes('个去重字符'));
    for(const width of [1440,390,320]) {
      await page.setViewportSize({width,height:900});
      for(const [kind,count] of [['pending','396'],['allocated','47'],['recovered','138'],['reviewed','10'],['all','443']]) {
        await page.locator(`#cleanupQueues [data-cleanup="${kind}"]`).click();
        await page.waitForFunction(t=>document.querySelector('#resultStatus').textContent.startsWith(t+' 个去重字符'),count);
        const geometry=await page.evaluate(()=>({headingTop:document.querySelector('#resultHeading').getBoundingClientRect().top,
          resultsTop:document.querySelector('#results').getBoundingClientRect().top,height:innerHeight,scrollY,
          overflow:document.documentElement.scrollWidth>innerWidth}));
        console.log(JSON.stringify({width,kind,count,...geometry}));
        assert(geometry.headingTop>=0&&geometry.headingTop<geometry.height-100,'点击后结果标题仍在屏外');
        assert(geometry.resultsTop<geometry.height-60,'点击后首行候选仍在屏外');
        assert(!geometry.overflow,'页面横向溢出');
        assert.equal(await page.locator(`#cleanupQueues [data-cleanup="${kind}"]`).getAttribute('aria-pressed'),'true');
        if(kind==='pending')await page.screenshot({path:path.join(output,`cleanup-navigation-${width}.png`)});
      }
      await page.locator('#cleanupResultNav [data-cleanup="pending"]').click();
      await page.waitForFunction(()=>document.querySelector('#resultStatus').textContent.startsWith('396 '));
      assert(await page.locator('#resultHeading').evaluate(el=>document.activeElement===el));
    }
    assert.deepEqual(errors,[]);
    await page.setViewportSize({width:1440,height:900});
    await page.locator('[data-position="1"]').click();await page.locator('[data-key="u"]').click();
    await page.waitForFunction(()=>document.querySelector('#resultStatus').textContent.startsWith('42 '));
    await page.locator('#keyInfo [data-uexpansion="six"]').click();
    for(const [kind,count] of [['six',22],['three',8],['two',4],['stable',131],['unstable',22],['broad',28],['new',181]]) {
      await page.locator(`#uExpansionNav [data-uexpansion="${kind}"]`).click();
      await page.waitForFunction(n=>document.querySelector('#resultStatus').textContent.startsWith(n+' '),count);
      assert(await page.locator('#resultHeading').evaluate(el=>el.getBoundingClientRect().top<innerHeight));
      assert.equal(await page.locator(`#uExpansionNav [data-uexpansion="${kind}"]`).getAttribute('aria-pressed'),'true');
    }
    await page.locator('#uExpansionNav [data-uexpansion="stable"]').click();
    await page.waitForFunction(()=>document.querySelector('#resultStatus').textContent.startsWith('131 '));
    await page.locator('#next').click();
    await page.waitForFunction(()=>document.querySelector('#page').textContent.startsWith('61'));
    await page.locator('#uExpansionNav [data-uexpansion="unstable"]').click();
    await page.waitForFunction(()=>document.querySelector('#resultStatus').textContent.startsWith('22 '));
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('6/9种通过'));
    for(const width of [1440,390,320]) {
      await page.setViewportSize({width,height:900});
      await page.locator('#uExpansionNav [data-uexpansion="six"]').click();
      await page.waitForFunction(()=>document.querySelector('#resultStatus').textContent.startsWith('22 '));
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
      assert(await page.locator('#results').evaluate(el=>el.getBoundingClientRect().top<innerHeight-60));
      await page.screenshot({path:path.join(output,`u-expansion-${width}.png`)});
    }
    const unchanged=await page.request.get('http://127.0.0.1:8766/api/shape-overview/query?prefix=u&allocation=1');
    assert.equal((await unchanged.json()).total,42);
    assert.deepEqual(errors,[]);
    console.log('cleanup navigation checks passed');
  } catch(error) {
    await page.screenshot({path:path.join(output,'cleanup-navigation-failure.png')});
    throw error;
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
