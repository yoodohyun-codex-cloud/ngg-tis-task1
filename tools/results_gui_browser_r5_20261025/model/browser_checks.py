"""Actual DOM and canvas checks; not scientific/experimental validation.

The admitted files stream byte-for-byte over a worker-owned read-only loopback
HTTP origin. Actual browser policy/access is checked; no security flag changes.
"""
import hashlib,json,os,re,time
from pathlib import Path
# Both sides are parsed JSON trees: preserve all scalar values, ordered dense
# arrays, and exact own object-keysets, without cloning or serializing payloads.
JSON_SEMANTIC_EQUALITY_JS = r"""
const same=(a,b)=>{
 const ta=typeof a,tb=typeof b;
 if(ta!==tb)return false;
 if(a===null||b===null)return a===b;
 if(ta==='number')return Number.isFinite(a)&&Number.isFinite(b)&&a===b;
 if(ta==='string'||ta==='boolean')return a===b;
 if(ta!=='object')return false;
 const aa=Array.isArray(a),ab=Array.isArray(b);
 if(aa!==ab)return false;
 if(aa){
  if(a.length!==b.length)return false;
  for(let i=0;i<a.length;i++){
   if(!Object.prototype.hasOwnProperty.call(a,i)||!Object.prototype.hasOwnProperty.call(b,i)||!same(a[i],b[i]))return false;
  }
  return true;
 }
 const ak=Object.keys(a),bk=Object.keys(b);
 if(ak.length!==bk.length)return false;
 for(const key of ak){
  if(!Object.prototype.hasOwnProperty.call(b,key)||!same(a[key],b[key]))return false;
 }
 return true;
};
"""
def require(ok,message):
 if not ok:raise ValueError(message)
def new(path,value):
 with Path(path).open('x',encoding='utf-8')as stream:json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
def build(spec,guard,deadline_monotonic,output_dir,transport=None):
 from playwright.sync_api import sync_playwright
 out=Path(output_dir);html=Path(spec['inputs']['index.html']['path']);errors=[];console_errors=[];external=[];failed_requests=[];checks={};started=time.monotonic();browser_version=None
 require(isinstance(transport,dict)and transport.get('bind_address')=='127.0.0.1'and transport.get('read_only')is True and transport.get('extra_processes')==0 and transport.get('chunk_bytes')==65536,'Authenticated worker-owned finite read-only loopback transport')
 origin=transport['origin'];require(re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{0,4}',origin)is not None and set(transport['allowed_urls'])=={origin+'/'+name for name in spec['inputs']}|{origin+'/favicon.ico'},'Exact bound loopback origin and admitted paths only')
 stage_counter=0
 def check():
  guard();require(time.monotonic()<deadline_monotonic,'Finite180s actual-browser watchdog')
 def stage(label,**extra):
  nonlocal stage_counter
  check();stage_counter+=1
  new(out/('browser-stage-'+str(stage_counter).zfill(3)+'.json'),dict(schema='task1-browser-stage-v1',phase=label,worker_pid=os.getpid(),elapsed_seconds=time.monotonic()-started,completed_DOM_checks=len(checks),new_PDE_RHS=0,**extra))
 def digest_js(expression):
  check();return page.evaluate("async()=>{const bytes=new TextEncoder().encode("+expression+");const h=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(h),x=>x.toString(16).padStart(2,'0')).join('')}")
 def control_values():return page.evaluate("Object.fromEntries(['xmin','xmax','ymin','ymax','zmin','zmax','cmin','cmax','bmin','bmax','arrowScale'].map(id=>[id,Number(document.getElementById(id).value)]))")
 def change(ident,value):
  check();page.locator('#'+ident).fill(str(value));page.locator('#'+ident).dispatch_event('change');require(page.locator('#error').inner_text()=='','Valid manual control rejected '+ident)
 def canvas_digest(selector):
  check();return page.locator(selector).first.evaluate("async c=>{const a=c.getContext('2d').getImageData(0,0,c.width,c.height).data;const h=await crypto.subtle.digest('SHA-256',a);return Array.from(new Uint8Array(h),v=>v.toString(16).padStart(2,'0')).join('')}")
 profile=Path('/dev/shm')/('task1-gbr5-'+str(os.getpid()));profile.mkdir(exist_ok=False)
 require(profile==profile.resolve()and not profile.is_symlink(),'Exclusive short canonical browser scratch; preserve any previous path')
 for name in('p','t','c'):(profile/name).mkdir(exist_ok=False)
 socket_bound=str(profile/'t')+'/org.chromium.Chromium.'+('X'*16)+'/SingletonSocket'
 require(len(socket_bound.encode())<90,'Prospective nested Chromium UNIX socket path remains under108 bytes')
 new(out/'browser-scratch.json',dict(schema='task1-browser-short-scratch-v1',path=str(profile),user_data_dir=str(profile/'p'),temporary_dir=str(profile/'t'),config_cache_dir=str(profile/'c'),conservative_singleton_path_bytes=len(socket_bound.encode()),actual_all_task_tmpfs_guard_covers_path=True,original_long_scratch_preserved=True,scratch_will_not_be_deleted_by_controller=True))
 env=dict(os.environ,TMPDIR=str(profile/'t'),TMP=str(profile/'t'),TEMP=str(profile/'t'),XDG_CONFIG_HOME=str(profile/'c'),XDG_CACHE_HOME=str(profile/'c'))
 stage('before_playwright_start',transport='read_only_loopback_streaming',chunk_bytes=65536)
 with sync_playwright()as engine:
  stage('before_chromium_launch')
  context=engine.chromium.launch_persistent_context(str(profile/'p'),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1450,height=1050),env=env,ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0'])
  try:
   stage('chromium_context_started')
   browser_version=context.browser.version if context.browser else 'persistent-context-version-unavailable';page=context.pages[0];page.set_default_timeout(10000);page.set_default_navigation_timeout(20000)
   def route(request):
    if request.request.url in transport['allowed_urls']:request.continue_()
    else:external.append(request.request.url);request.abort()
   context.route('**/*',route);page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:console_errors.append(m.text)if m.type=='error'else None);page.on('requestfailed',lambda r:failed_requests.append(dict(url=r.url,failure=r.failure)))
   stage('before_page_navigation');page.goto(origin+'/index.html',wait_until='load');page.wait_for_function("document.getElementById('cards').children.length>0 && document.getElementById('comparisonTable').querySelectorAll('tbody tr').length===60")
   stage('page_navigation_loaded');require(page.evaluate('window.isSecureContext && !!window.crypto && !!window.crypto.subtle'),'Actual loopback secure-context/WebCrypto availability; no policy override')
   stage('before_published_payload_semantic_comparison')
   require(page.evaluate("async()=>{"+JSON_SEMANTIC_EQUALITY_JS+"const summary=await(await fetch('/summary.json')).json();const views=await(await fetch('/views.json')).json();return same(S,summary)&&same(V,views)}"),'Actual HTML payload differs from admitted published summary/views');checks['published_payload_agreement']=dict(passed=True,whole_summary_and_views_compared=True);stage('published_payload_semantic_comparison_passed')
   stage('before_whole_payload_source_SHA');payload_before=digest_js("JSON.stringify(D)");source_identities_before=digest_js("JSON.stringify(S.candidates.map(c=>({candidate_id:c.candidate_id,provenance:c.provenance,source_scalar_SHA256:c.source_scalar_SHA256,source_mask_SHA256:c.source_mask_SHA256,source_raw_SHA256_by_frequency:c.source_raw_SHA256_by_frequency})))")
   actual_ids=page.evaluate('cs.map(c=>c.candidate_id)');require(actual_ids==spec['native_ids'],'Admitted summary native identity/order differs from actual HTML payload');require(page.evaluate('S.baseline_id')==spec['baseline_id']and page.evaluate('S.mandatory_compare_ids')==spec['mandatory_compare_ids']and page.evaluate('S.provisional_top5')==spec['provisional_top5'],'Published rank/baseline/mandatory IDs agree')
   expected=list(dict.fromkeys([spec['baseline_id']]+spec['mandatory_compare_ids']+spec['provisional_top5']));visible=page.locator('#cards article.candidate > h2').all_text_contents();require(visible==expected,'Default B0/mandatory8/12/16/Top5 card set/order');require(page.locator('#comparisonTable tbody tr').count()==60,'All15×4 separate normalized rows present');checks['mandatory_baseline_top5']=dict(passed=True,default_visible_ids=visible,native_comparison_rows=60)
   local_ids=page.evaluate('localRows.map(c=>c.candidate_id??c.id)');require(local_ids==spec['reported_local_ids']and not(set(local_ids)&set(actual_ids)),'LOCAL report rows must stay outside native ranking');require(page.locator('#localTable tbody tr').count()==len(local_ids),'Separate original LOCAL rows');checks['reported_local_separation']=dict(passed=True,reported_ids=local_ids,native_ranking_separate=True,empty_report_is_not_filled=True)
   # Exact native-mask metadata and actual canvas drawing are both inspected.
   outlines=page.evaluate("cs.map(c=>({id:c.candidate_id,pads:(V.candidates[c.candidate_id].electrodes||c.electrodes).map(p=>({pad:p.pad,contours:p.mask_contours_mm?.length||0,fill:p.mask_fill_rule}))}))")
   require(all(len(row['pads'])>=4 and all(p['contours']>0 for p in row['pads'])for row in outlines),'Actual pixel mask contours available for every physical pad');require(page.locator('#cards canvas').count()==4*len(expected),'Footprint plus XZ/YZ/XY native slice canvases actually created');checks['native_pixel_contours']=dict(passed=True,outline_counts=outlines,canvas_only_not_field_validation=True)
   # Work through all real controls; no hidden setter or direct state mutation.
   initial=control_values();original_canvas=canvas_digest('#cards article.candidate .plotgrid .plot:nth-child(2) canvas')
   for ident,value in dict(xmin=-18,xmax=18,ymin=-17,ymax=17,zmin=1,zmax=24,cmin=0,cmax=max(initial['cmax']*.55,1e-12),bmin=0,bmax=max(initial['bmax']*.6,1e-12),arrowScale=.35).items():change(ident,value)
   manual=control_values();require(all(manual[k]==v for k,v in dict(xmin=-18,xmax=18,ymin=-17,ymax=17,zmin=1,zmax=24,arrowScale=.35).items()),'Actual axis controls applied');require(canvas_digest('#cards article.candidate .plotgrid .plot:nth-child(2) canvas')!=original_canvas,'Changing physical axes/colour range must redraw the actual native canvas');require('clip'in page.locator('#barclip').inner_text()and 'fixed-V native'in page.locator('#cards .clip').nth(1).inner_text(),'Display clipping and native min/max disclosed');checks['manual_axes_colors_bars']=dict(passed=True,original=initial,manual=manual,actual_canvas_redrawn=True);stage('manual_axes_and_color_controls_passed')
   options=page.locator('#normalization option').evaluate_all('(a)=>a.map(o=>o.value)');require(len(options)==4,'Four separate normalization controls')
   for option in options:
    check();page.select_option('#normalization',option);require(control_values()==manual,'Normalization switch reset user ranges');require(page.evaluate('st.normalization')==option,'Actual normalization state switched');require(page.locator('#error').inner_text()=='','Normalization raised UI error')
   checks['normalization_persistence']=dict(passed=True,options=options,axes_color_bars_unchanged=True)
   qoptions=page.locator('#quantity option').evaluate_all('(a)=>a.map(o=>({value:o.value,label:o.textContent}))');require({'AM','carrier_RMS'}.issubset({v['value']for v in qoptions}),'AM and total carrier RMS are distinct actual options')
   axes={k:manual[k]for k in('xmin','xmax','ymin','ymax','zmin','zmax')}
   for q in('carrier_RMS','AM'):
    check();page.select_option('#quantity',q);require(all(control_values()[k]==v for k,v in axes.items()),'Quantity switch reset physical axes');require(q in page.locator('#legendnote').inner_text(),'Actual colour legend quantity label');change('cmin',0);change('cmax',max(initial['cmax']*(.6 if q=='AM'else .7),1e-12))
   changed_AM=control_values()['cmax'];page.select_option('#quantity','carrier_RMS');saved_RMS=control_values()['cmax'];page.select_option('#quantity','AM');require(control_values()['cmax']==changed_AM,'Per-quantity colour limits lost');checks['carrier_vs_modulation']=dict(passed=True,options=qoptions,AM_colour_max=changed_AM,carrier_RMS_colour_max=saved_RMS,independent_ranges=True)
   baroptions=page.locator('#barmetric option').evaluate_all('(a)=>a.map(o=>o.value)');require(len(baroptions)==9,'Nine actual bar metrics')
   for i,value in enumerate(baroptions):
    check();page.select_option('#barmetric',value);change('bmin',0);change('bmax',float(i+1));require(all(control_values()[k]==v for k,v in axes.items()),'Bar metric changed physical axes');require(value==page.evaluate('st.barmetric'),'Actual bar metric not selected')
   page.select_option('#barmetric',baroptions[0]);require(control_values()['bmax']==1.,'Per-bar-metric manual Y range lost');checks['bar_metric_controls']=dict(passed=True,options=baroptions,per_metric_ranges_preserved=True)
   page.locator('#vectors').check();require(page.evaluate('st.vectors')is True and page.evaluate('st.arrowScale')==.35,'Carrier vector overlay controls not applied');page.locator('#vectors').uncheck()
   page.select_option('#displaymode','all_native');require(page.locator('#cards article.candidate').count()==15,'Actual all-native card toggle');page.select_option('#displaymode','mandatory_top5');require(page.locator('#cards article.candidate').count()==len(expected),'Actual mandatory/Top5 toggle');checks['vectors_and_display_mode']=dict(passed=True,all_native_cards=15)
   total=0;probecounts={}
   for cid in actual_ids:
    check();page.select_option('#probeCandidate',cid);n=page.locator('#probeTable tbody tr').count();require(n==40 and cid in page.locator('#probeMeta').inner_text(),'Actual40-probe selection '+cid);probecounts[cid]=n;total+=n
   require(total==600,'All15 native selections provide40 probes');checks['unloaded_native_probes']=dict(passed=True,rows_by_geometry=probecounts,total=total,hardware_loading_validation=False)
   # Display-range profiles: export/import controls. There is no spatial-profile
   # graph in this renderer; do not claim one exists or has been validated.
   state_before=page.evaluate('JSON.parse(JSON.stringify(st))')
   with page.expect_download()as transfer:page.locator('#export').click()
   download=transfer.value;download_path=out/'display-settings-export.json';download.save_as(str(download_path));settings=json.loads(download_path.read_text());require(settings.get('schema')=='task1-manual-display-ranges-v1'and settings.get('settings')==state_before,'Actual exported range profile matches current controls')
   page.locator('#reset').click();require(page.evaluate('st.xmin')==page.evaluate('defaults.xmin'),'Actual shared-range reset');page.locator('#import').set_input_files(str(download_path));page.wait_for_function('(expected)=>JSON.stringify(st)===JSON.stringify(expected)',arg=state_before);require(page.locator('#error').inner_text()=='','Valid settings import failed');checks['range_profile_export_import']=dict(passed=True,actual_download_and_upload=True,spatial_profile_graph_status='not_present_in_renderer_not_claimed');stage('settings_export_import_passed')
   # Import a genuinely invalid display profile and verify the old valid state.
   invalid=dict(settings);invalid['settings']=dict(settings['settings'],xmin=5,xmax=-5);bad=out/'invalid-display-settings-fixture.json';new(bad,invalid);page.locator('#import').set_input_files(str(bad));page.wait_for_function("document.getElementById('error').textContent.length>0");require(page.evaluate('(expected)=>JSON.stringify(st)===JSON.stringify(expected)',state_before),'Invalid import changed last valid display state');checks['invalid_profile_preserves_state']=dict(passed=True)
   # Recover through the real valid file control, then test reload persistence.
   page.locator('#import').set_input_files(str(download_path));page.wait_for_function("document.getElementById('error').textContent===''");page.reload(wait_until='load');page.wait_for_function("document.getElementById('cards').children.length>0");require(page.evaluate('JSON.parse(JSON.stringify(st))')==state_before,'Local display settings did not persist after reload');checks['reload_range_persistence']=dict(passed=True);stage('reload_persistence_passed')
   require(digest_js('JSON.stringify(D)')==payload_before and digest_js("JSON.stringify(S.candidates.map(c=>({candidate_id:c.candidate_id,provenance:c.provenance,source_scalar_SHA256:c.source_scalar_SHA256,source_mask_SHA256:c.source_mask_SHA256,source_raw_SHA256_by_frequency:c.source_raw_SHA256_by_frequency})))")==source_identities_before,'UI scales/clipping/settings mutated scientific payload or source identities');checks['raw_payload_identity']=dict(passed=True,payload_semantic_SHA256=payload_before,source_identity_SHA256=source_identities_before,raw_index_bytes_unchanged_by_controller=True)
   page.locator('#reset').click();page.select_option('#probeCandidate',spec['baseline_id']);page.screenshot(path=str(out/'preview-desktop.jpg'),type='jpeg',quality=72,full_page=False);page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(80);check();mobile_width=page.evaluate('document.documentElement.scrollWidth');require(mobile_width<=392,'Mobile390 document overflows beyond scrollable internal tables');page.screenshot(path=str(out/'preview-mobile.jpg'),type='jpeg',quality=70,full_page=False);checks['responsive_layout']=dict(passed=True,desktop=[1450,1050],mobile=[390,844],mobile_document_width=mobile_width);stage('desktop_and_mobile_checks_passed')
   require(not errors and not console_errors and not external and not failed_requests,'Actual GUI JS/console/external-request failure');check()
   return dict(schema='task1-results-gui-actual-browser-v1',status='passed',browser_validation_performed=True,browser_version=browser_version,browser_executable='/usr/bin/chromium',browser_scratch=str(profile),browser_transport='Worker-owned read-only127.0.0.1 ephemeral HTTPServer with exact admitted paths and64KiB streams; actual browser policy/access checked, no fulfill/base64 body copies or security changes',checks=checks,JS_errors=errors,console_errors=console_errors,external_requests=external,failed_requests=failed_requests,elapsed_seconds=time.monotonic()-started,new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,scientific_validation_performed=False,experimental_validation=False,candidate_adopted=False,Windows_saved_verified=False)
  except BaseException as error:
   new(out/'browser-failure.json',dict(status='failed_preserved',error_type=type(error).__name__,error=str(error),checks=checks,JS_errors=errors,console_errors=console_errors,external_requests=external,failed_requests=failed_requests,HTML_modified=False,new_PDE_RHS=0))
   try:page.screenshot(path=str(out/'failure-preview.jpg'),type='jpeg',quality=65,timeout=3000,full_page=False)
   except BaseException:pass
   raise
  finally:context.close()
