const {chromium}=require(process.argv[2]||'playwright');
const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
(async()=>{
  const root=__dirname,base=pathToFileURL(path.join(root,'output/id_ctrl_ko.html')).href;
  const data=JSON.parse(fs.readFileSync(path.join(root,'content.json'),'utf8'));
  const cid=data.fields.find(f=>f.id==='SSVID').rules[0].id;
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const context=await browser.newContext({offline:true,viewport:{width:1440,height:1000}});
  const p=await context.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
  let dismiss=false;p.on('dialog',d=>dismiss?d.dismiss():d.accept());
  const assert=(x,m)=>{if(!x)throw Error(m);};
  const nav=async hash=>{await p.goto(base+'#'+encodeURIComponent(hash));await p.waitForFunction(()=>lastRenderedHash===location.hash);};
  await nav('project');
  await p.locator('#project-import').setInputFiles(path.join(root,'output/qa/project-roundtrip.json'));
  await p.waitForFunction(()=>activeProject?.metadata.product==='QA SSD');
  assert(await p.locator('[data-meta=firmware]').getAttribute('readonly')!==null,'Recorded firmware protected');
  for(const controller of ['controller-A','controller-B']){
    await nav('condition/'+cid+'?'+new URLSearchParams({controller,target:'NSID 1'}));
    await p.locator('[name=status]').selectOption('조건 만족');
    await p.locator('#review-form button').click();
    assert((await p.locator('#review-message').innerText()).includes('관측값이 필요'),'No data cannot become satisfied');
    await p.locator('[name=value]').fill('SSVID=0x1234; PCI Header=0x1234');
    await p.locator('[name=reviewer]').fill('');await p.locator('#review-form button').click();
    assert((await p.locator('#review-message').innerText()).includes('검토자를 입력'),'Reviewer required');
    await p.locator('[name=reviewer]').fill('QA reviewer');
    assert(await p.locator('[name=state]').inputValue()==='미확인','Observation state not inferred');
    assert(await p.locator('[name=observedAt]').inputValue()==='미확인','Observation time not inferred');
    await p.locator('#review-form button').click();
  }
  const records=await p.evaluate(()=>Object.values(activeProject.reviews).filter(r=>r.target==='NSID 1'));
  assert(records.length===2&&new Set(records.map(r=>r.controller)).size===2,'Same namespace on different controllers stays separate');
  await p.locator('[name=reason]').fill('반영하지 않은 메모');dismiss=true;
  await p.locator('.app-nav a[href="#project"]').click();
  assert(await p.locator('[name=reason]').inputValue()==='반영하지 않은 메모','Cancelled navigation retains form');
  dismiss=false;await p.locator('.app-nav a[href="#project"]').click();
  await p.waitForFunction(()=>lastRenderedHash==='#project');
  assert((await p.evaluate(()=>Object.values(activeProject.reviews).filter(r=>r.target==='NSID 1').map(r=>r.reason))).every(r=>!r.includes('반영하지 않은')),'Uncommitted form not recorded');
  // OCP configuration changes must not invalidate NVMe-only conditions.
  await p.locator('.context-settings summary').click();await p.locator('#scope-ocp').selectOption('yes');
  assert(await p.evaluate(()=>Object.values(activeProject.reviews).every(r=>{const live=caseMap.get(r.conditionId);return contextKey(r.snapshot.context,live.standard)===contextKey(activeProject.context,live.standard);})), 'Unrelated profile setting does not invalidate NVMe result');
  await p.locator('#controller').selectOption('admin');

  assert((await p.locator('#content').innerText()).includes('적용 설정 변경 · 재확인 필요'),'Controller applicability change requires recheck');
  await nav('workflows');await p.locator('details summary').filter({hasText:'단위 환산'}).click();
  await p.locator('#calc-mdts').fill('');await p.locator('#calc-run').click();
  assert((await p.locator('#calc-result').innerText()).includes('빈 값은 0이 아닙니다'),'Blank is not zero');
  await p.locator('#calc-mdts').fill('6');await p.locator('#calc-run').click();
  assert((await p.locator('#calc-result').innerText()).includes('262144 bytes = 256 KiB'),'MDTS byte conversion');
  await nav('workflow/identity');await p.emulateMedia({media:'print'});
  assert(await p.locator('aside').evaluate(e=>getComputedStyle(e).display)==='none','Print hides navigation');
  await p.emulateMedia({media:'screen'});
  for(let i=1;i<=4;i++){
    const stage=await context.newPage();await stage.goto(pathToFileURL(path.join(root,`output/stages/stage${i}.html`)).href);
    assert(await stage.locator('#content h1').count()>0,'Stage entrypoint '+i);await stage.close();
  }
  assert(!errors.length,'JS errors '+errors.join(';'));
  const report={checked_at:new Date().toISOString(),html_sha256:require('crypto').createHash('sha256').update(fs.readFileSync(path.join(root,'output/id_ctrl_ko.html'))).digest('hex'),status:'passed',offline:true,controller_namespace_isolation:true,uncommitted_navigation_cancel:true,firmware_identity_protected:true,missing_value_and_reviewer_blocked:true,observation_unknown_preserved:true,context_recheck:true,unit_conversion:true,print_navigation_hidden:true,stage_entrypoints:4};
  fs.writeFileSync(path.join(root,'output/project_validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
