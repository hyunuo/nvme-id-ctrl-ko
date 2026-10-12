/* Browser acceptance checks against the real standalone file URL.
   Usage: node browser_qa.cjs [absolute path to playwright module] */
const {chromium}=require(process.argv[2]||'playwright');
const path=require('path'),fs=require('fs'),{pathToFileURL}=require('url');
(async()=>{
 const root=__dirname, out=path.join(root,'output'),qa=path.join(out,'qa'),data=JSON.parse(fs.readFileSync(path.join(root,'content.json'),'utf8'));
 fs.mkdirSync(qa,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},offline:true});
 const page=await context.newPage(),errors=[],remote=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('request',r=>{if(/^https?:/.test(r.url()))remote.push(r.url());});
 const url=pathToFileURL(path.join(out,'id_ctrl_ko.html')).href;
 const assert=(v,m)=>{if(!v)throw Error(m);};
 await page.goto(url);
 assert(await page.locator('#content h1').innerText().then(t=>t.includes('Identify Controller')),'Home not rendered');
 await page.screenshot({path:path.join(qa,'home.png')});
 const search=page.locator('#search');
 await search.fill('캐시');assert(await page.locator('#navlist [data-id="VWC"]').count()===1,'Korean search');
 await search.fill('Maximum Data Transfer');assert(await page.locator('#navlist [data-id="MDTS"]').count()===1,'English search');
 await search.fill('525');assert(await page.locator('#navlist [data-id="VWC"]').count()===1,'Decimal offset search');
 await search.fill('0x20d');assert(await page.locator('#navlist [data-id="VWC"]').count()===1,'Hex offset search');
 await search.fill('20');assert(await page.locator('#navlist [data-id="SN"]').count()===1,'Interior byte offset search');
 await search.fill('zzzz-not-a-field');assert(await page.locator('#navlist').innerText().then(t=>t.includes('일치하는 항목')),'Empty search');
 await page.locator('#clear').click();
 await page.locator('#navlist [data-id="VWC"]').click();
 await page.waitForFunction(()=>location.hash==='#VWC');
 assert(await page.locator('#content').innerText().then(t=>t.includes('WCE')&&t.includes('Invalid Field in Command')),'VWC core checks');
 await page.locator('#content details').first().locator('summary').click();
 assert(await page.locator('#content details').first().getAttribute('open')!==null,'English expand');
 await page.locator('#content a[href="#base%3A5.1.25.1.4"]').first().click();
 await page.waitForFunction(()=>location.hash.includes('5.1.25.1.4'));
 assert(await page.locator('#content').innerText().then(t=>t.includes('연결된 Identify 필드')&&t.includes('VWC')),'Reference reverse relation');
 await page.goBack();await page.waitForFunction(()=>location.hash==='#VWC');
 await page.goto(url+'#VWC');await page.evaluate(()=>scrollTo(0,0));await page.waitForTimeout(200);await page.screenshot({path:path.join(qa,'vwc.png')});
 await page.locator('#sort').selectOption('topic');assert(await page.locator('.navgroup').count()>0,'Topic grouping');
 await page.locator('#topic').selectOption('전원·열 관리');
 assert(await page.locator('#navlist [data-id="APSTA"]').count()===1,'Topic filter');
 assert(await page.locator('#navlist [data-id="VWC"]').count()===0,'Topic filter exclusion');
 await page.locator('#topic').selectOption('');await page.locator('#reserved').check();
 assert(await page.locator('#navlist [data-id="RESERVED_103"]').count()===1,'Reserved visibility');
 await page.goto(url+'#IOCCSZ');assert(await page.locator('.contextnote').innerText().then(t=>t.includes('PCIe / I/O controller 기준: 예약 필드')),'Memory transport footnote');
 await page.locator('#transport').selectOption('fabrics');assert(await page.locator('.contextnote').innerText().then(t=>t.includes('Fabrics / I/O controller 기준: 필수 필드')),'Message transport footnote');
 await page.locator('#transport').selectOption('pcie');
 let checked=0;
 for(const n of [...data.fields,...data.references]){
  await page.evaluate(id=>location.hash=encodeURIComponent(id),n.id);
  await page.waitForFunction(id=>document.title.startsWith(id+' ·'),n.id);
  assert(await page.locator('#content h1').count()===1,'Missing heading '+n.id);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
  assert(!overflow,'Desktop horizontal overflow '+n.id);checked++;
 }
 for(const id of ['APSTA','MDTS','PSD0']){
  await page.goto(url+'#'+id);await page.evaluate(()=>scrollTo(0,0));await page.waitForTimeout(200);await page.screenshot({path:path.join(qa,id.toLowerCase()+'.png')});
 }
 await page.setViewportSize({width:390,height:844});
 await page.goto(url+'#VWC');await page.evaluate(()=>scrollTo(0,0));await page.waitForTimeout(250);await page.screenshot({path:path.join(qa,'mobile.png')});
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Mobile overflow');
 await page.locator('#menu').click();assert(await page.locator('#menu').getAttribute('aria-expanded')==='true','Mobile menu');
 await search.fill('APSTA');await page.locator('#navlist [data-id="APSTA"]').click();
 await page.waitForFunction(()=>location.hash==='#APSTA');assert(await page.locator('#menu').getAttribute('aria-expanded')==='false','Mobile nav closes');
 await page.goto(url+'#references');assert(await page.locator('.ref-index a').count()===data.references.length,'Reference index');
 await page.goto(url+'#help');assert(await page.locator('#content').innerText().then(t=>t.includes('추가 근거')),'Help');
 await page.setViewportSize({width:1440,height:1000});
 await page.goto(url+'#consistency');
 assert(await page.locator('.field-tile').count()===data.fields.length,'All fields in overview map');
 assert(await page.locator('#overview-body [data-field-id]').count()===data.fields.length,'All fields in overview table');
 assert(await page.locator('#overview-body [data-check-id]').count()===data.consistency_audit.after_checks,'Every check rendered in overview');
 for(const id of ['OAES','FGUID','TNVMCAP','UNVMCAP','SUBNQN'])assert(data.fields.find(f=>f.id===id).rules.length>0,'Previously missing check '+id);
 assert(data.fields.find(f=>f.id==='ONCS').rules.some(r=>r.level==='SHALL'&&r.expected.includes('NVMCSA=1')),'Copy mandatory version condition');
 assert(data.fields.find(f=>f.id==='PSD31').rules.every(r=>r.field_applicability.includes('NPSS≥31')),'Unsupported PSD excluded by applicability');
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Overview desktop overflow');
 await page.screenshot({path:path.join(qa,'consistency.png')});
 await page.locator('#field-map').screenshot({path:path.join(qa,'field_map.png')});
 await page.locator('#overview-expanded').check();
 assert(await page.locator('.remaining-checks:not([open])').count()===0,'Expand every remaining check');
 await page.locator('#overview-search').fill('OAES');
 assert(await page.locator('#overview-body [data-field-id="OAES"]').count()===1,'Overview field search');
 assert(await page.locator('#overview-body').innerText().then(t=>t.includes('활성화하기 전')),'OAES missing requirement restored');
 await page.locator('#overview-reset').click();
 await page.locator('[data-overview-field="FGUID"]').click();
 assert(await page.locator('#overview-field-FGUID').isVisible(),'Field map targets table row');
 await page.locator('#overview-category').selectOption('필드 간 관계');
 assert(await page.locator('#overview-body [data-field-id="FGUID"]').count()===1,'Relationship category');
 await page.locator('#overview-reset').click();
 await page.locator('#overview-status').selectOption('Vendor 정의');
 assert(await page.locator('#overview-body [data-field-id]').count()===1,'Vendor-only filter');
 assert(await page.locator('#overview-body').innerText().then(t=>t.includes('Vendor 문서')),'Vendor is not shown as passed');
 await page.goto(url+'#'+encodeURIComponent('consistency?field=AWUN'));
 assert(await page.locator('#overview-search').inputValue()==='AWUN','Field-to-overview deep link');
 assert(await page.locator('#overview-body [data-field-id]').count()===1,'Selected field overview is exact');
 await page.goto(url+'#audit');
 assert(await page.locator('#content').innerText().then(t=>t.includes('FGUID')&&t.includes('OAES')),'Audit additions');
 await page.setViewportSize({width:390,height:844});await page.goto(url+'#consistency');
 assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),'Mobile overview and header overflow');
 await page.screenshot({path:path.join(qa,'consistency_mobile.png')});
 assert(errors.length===0,'JS errors '+errors.join('\n'));assert(remote.length===0,'Remote requests '+remote.join('\n'));
 const report={status:'passed',offline:true,remote_requests:remote.length,javascript_errors:errors.length,rendered_nodes:checked,
  scenarios:['Korean/English/decimal/hex search','empty search','topic grouping/filter','reserved visibility','English expand',
   'related clause and reverse links','browser back','file URL deep link','transport footnotes','all nodes desktop layout',
   '390px mobile layout and menu','reference index','help','152-field overview map/table','all checks in overview',
   'expand all checks','overview search/category/Vendor filter','overview deep link','audit additions','mobile overview']};
 fs.writeFileSync(path.join(out,'browser_validation.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify(report,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
