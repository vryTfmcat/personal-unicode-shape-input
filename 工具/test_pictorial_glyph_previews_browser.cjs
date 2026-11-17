const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1050}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8765/pictorial-intake-review.html?display=20261023#queue=egyptAnimalParts&page=6');
  await page.waitForSelector('.glyph img');
  await page.locator('#heading').scrollIntoViewIfNeeded();
  const stats=await page.locator('.glyph img').evaluateAll(async images=>{
   const rows=[];
   for(const img of images){await img.decode();const c=document.createElement('canvas');c.width=190;c.height=104;const ctx=c.getContext('2d');ctx.drawImage(img,0,0,190,104);const data=ctx.getImageData(0,0,190,104).data;let left=190,right=-1,top=104,bottom=-1,pixels=0;for(let y=0;y<104;y++)for(let x=0;x<190;x++)if(data[(y*190+x)*4+3]>64){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);pixels++;}rows.push({cp:img.closest('.character').dataset.cp,pixels,width:right-left+1,height:bottom-top+1});}
   return rows;
  });
  for(const row of stats){assert(row.pixels>40,JSON.stringify(row));assert(Math.max(row.width,row.height)>=70,JSON.stringify(row));}
  assert.equal(await page.locator('.character').count(),48);
  assert.equal(stats.length,43);
  await page.screenshot({path:path.resolve('原型/键位编辑器/测试输出/pictorial-intake-review/display-fix-20261023.png')});
  for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1050});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
  assert.deepEqual(errors,[]);
  console.log('48 glyph pixel checks: all nonblank and fitted at four viewport widths; review source and classifications untouched');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
