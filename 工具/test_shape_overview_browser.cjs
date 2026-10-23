const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const output = path.join(root, '原型/键位编辑器/测试输出/shape-key-overview');
const url = process.env.OVERVIEW_URL || 'http://127.0.0.1:8766/shape-key-overview.html';
fs.mkdirSync(output, {recursive:true});

(async () => {
  const browser = await chromium.launch({headless:true, channel:'msedge'});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if(r.status()>=400) errors.push(`${r.status()} ${r.url()}`); });
  async function settled(expected) {
    await page.waitForFunction(text => document.querySelector('#resultStatus').textContent.includes(text), expected);
    assert.equal(await page.locator('#error').textContent(), '');
  }
  async function noOverflow() {
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'page overflow');
    assert.deepEqual(await page.locator('#keyboard .key').evaluateAll(nodes => nodes.filter(n => n.scrollHeight > n.clientHeight+2).map(n=>n.textContent)), [], 'key text overflow');
  }
  try {
    await page.goto(url);
    await page.waitForFunction(() => document.querySelector('#version').textContent.includes('v14'), {timeout:60000});
    if(await page.locator('[data-allocation="legacy"]').isVisible())await page.click('[data-allocation="legacy"]');
    await settled('个去重字符');
    assert.equal(await page.locator('#keyboard .key').count(),26);
    for(const p of [1,2,3,4]) {
      await page.click(`[data-position="${p}"]`);
      await settled('个去重字符');
      assert.equal(await page.locator('#keyboard .key').count(),26);
      await noOverflow();
    }
    await page.click('[data-position="3"]');
    await page.click('[data-key="z"]');
    await page.waitForFunction(()=>document.querySelector('#keyInfo').textContent.includes('连接横笔组'));
    await page.screenshot({path:path.join(output,'desktop-keys.png')});
    await page.click('[data-round="2"]');
    await page.click('[data-sample="EF"]');
    await settled('2 个去重字符');
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('chzt'));
    await page.locator('#proofImage').evaluate(img => img.decode());
    assert(await page.locator('#proofImage').evaluate(img=>img.naturalWidth>0));
    const ink = await page.locator('#results .glyph').first().evaluate(async glyph => {
      const img = new Image(); img.src = glyph.style.backgroundImage.slice(5,-2); await img.decode();
      const [x,y] = glyph.style.backgroundPosition.split(' ').map(v=>-parseFloat(v));
      const c=document.createElement('canvas'); c.width=64;c.height=64;
      const ctx=c.getContext('2d');ctx.drawImage(img,x,y,64,64,0,0,64,64);
      const data=ctx.getImageData(0,0,64,64).data;
      let dark=0; for(let i=0;i<data.length;i+=4) if(data[i]<128&&data[i+3]>0)dark++;
      return dark;
    });
    assert(ink>20&&ink<4000,'locked-font sprite is blank');
    await page.screenshot({path:path.join(output,'desktop-objects.png'),fullPage:true});
    await page.click('[data-round="3"]');
    await settled('1,562 个去重字符');
    assert.equal(await page.locator('#results .candidate').count(),60);
    await page.click('#next');
    await page.waitForFunction(()=>document.querySelector('#page').textContent.startsWith('61'));
    await page.click('[data-prefix="chzb"]');
    await settled('17 个去重字符');
    await page.selectOption('#length','3');
    await page.waitForFunction(()=>document.querySelector('#collisions button span').textContent.length===3);
    await page.fill('#collisionFilter','ch');
    assert(await page.locator('#collisions button').count()>0);
    await page.click('[data-round="4"]');
    await settled('6,716 个去重字符');
    await page.click('[data-queue="affected"]');
    await settled('3 个去重字符');
    for(const label of ['𐏓','𒌋','𐎓']) assert(await page.locator('#results').innerHTML().then(s=>s.includes(label)));
    await page.click('[data-queue="unclassified"]');
    await settled('5,220 个去重字符');
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('全局未分类'));
    await page.fill('#prefix','ioym');await page.fill('#character','Q');await page.click('#search [type="submit"]');
    await settled('1 个去重字符');
    await page.locator('#results .candidate').click();
    await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('iose'));
    for(const width of [1440,768,390,320]) {
      await page.setViewportSize({width,height:900});
      await noOverflow();
      await page.click('[data-round="1"]');
      for(const p of [1,2,3,4]) { await page.click(`[data-position="${p}"]`);await noOverflow(); }
      await page.screenshot({path:path.join(output,`keys-${width}.png`)});
      await page.click('[data-round="2"]');await page.click('[data-sample="QO"]');
      await settled('2 个去重字符');
      await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('iose'));
      await noOverflow();
      if(width===390)await page.screenshot({path:path.join(output,'mobile-objects.png'),fullPage:true});
      await page.click('[data-round="3"]');await settled('1,562 个去重字符');await noOverflow();
      await page.click('[data-round="4"]');await settled('6,716 个去重字符');await noOverflow();
    }
    assert.deepEqual(errors,[]);
    await page.setViewportSize({width:1440,height:1000});
    await page.goto(url+'#round=1&pilot=u');
    await settled('42 个去重字符');
    assert(await page.locator('#historicalPanel').evaluate(el=>el.open));
    await page.locator('#historicalImage').evaluate(img=>img.decode());
    await page.locator('#historicalPanel').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'historical-u-desktop.png')});
    await page.click('[data-trial="existing"]');
    await settled('4 个去重字符');
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail .pilot-detail')?.textContent.includes('九扰动通过 9/9'));
    assert((await page.locator('#detail').textContent()).includes('全部路径 · 0 条'));
    await page.click('[data-trial="v"]');await settled('1 个去重字符');
    await page.locator('#results .candidate').click();
    await page.waitForFunction(()=>document.querySelector('#detail .pilot-detail')?.textContent.includes('块面新用途试验'));
    await page.click('[data-pilotcategory="新用途扰动不稳定"]');await settled('7 个去重字符');
    await page.locator('#results .candidate').first().click();
    await page.waitForFunction(()=>document.querySelector('#detail .pilot-detail')?.textContent.includes('不纳入稳定候选'));
    await page.click('[data-trial="history"][data-oldkey="j"]');await settled('5 个去重字符');
    await page.click('[data-trial="reviewed"]');await settled('10 个去重字符');
    const unchanged=await page.request.get(new URL('/api/shape-overview/query?prefix=u',url).href);
    assert.equal((await unchanged.json()).total,73);
    for(const width of [390,320]) {
      await page.setViewportSize({width,height:1000});
      await page.click('[data-trial="u"]');await settled('42 个去重字符');
      await noOverflow();
      await page.locator('#historicalPanel').scrollIntoViewIfNeeded();
      if(width===390)await page.screenshot({path:path.join(output,'historical-u-mobile.png')});
    }
    assert.deepEqual(errors,[]);
    if(await page.locator('[data-allocation="draft"]').isVisible()) {
      await page.setViewportSize({width:1440,height:1000});
      await page.click('[data-allocation="draft"]');
      await page.click('[data-round="1"]');await page.click('[data-position="1"]');
      for(const key of ['b','g','j','t']) {
        await page.click(`[data-key="${key}"]`);await settled('0 个去重字符');
        assert((await page.locator('#keyInfo').textContent()).includes('空键'));
      }
      await page.click('[data-key="u"]');await settled('42 个去重字符');
      assert((await page.locator('#keyInfo').textContent()).includes('线群／层列'));
      await page.screenshot({path:path.join(output,'cleanup-desktop.png')});
      await page.click('[data-key="v"]');await settled('1 个去重字符');
      await page.click('[data-cleanup="pending"]');await settled('396 个去重字符');
      await page.locator('#results .candidate').first().click();
      await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('主桶待定'));
      await page.click('[data-cleanup="reviewed"]');await settled('10 个去重字符');
      await page.locator('#results .candidate').first().click();
      await page.waitForFunction(()=>document.querySelector('#detail').textContent.includes('原确认记录未迁移'));
      await page.click('[data-cleanup="recovered"]');await settled('138 个去重字符');
      await page.click('[data-round="4"]');await settled('6,578 个去重字符');
      for(const width of [390,320]) {
        await page.setViewportSize({width,height:1000});await page.click('[data-round="1"]');
        await noOverflow();
        if(width===390)await page.screenshot({path:path.join(output,'cleanup-mobile.png')});
      }
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify({passed:true,url,widths:[1440,768,390,320],glyphInkPixels:ink,errors},null,2));
    console.log(JSON.stringify({passed:true,output,glyphInkPixels:ink,errors}));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
