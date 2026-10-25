"""Deferred E13fine display append provenance; inert import, metadata only.
No old-seven native descriptors or payload/index bytes are opened here.
"""
import ast,copy,hashlib,json,math,re
from pathlib import Path
SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025/source')
OUT=Path('/workspace/ngg-tis-task1/runtime/native-GUI-append-E13fine-r5-20261025-run')
GUI=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-20261025-run')
GUI_SOURCE=Path('/workspace/ngg-tis-task1/runtime/native-GUI-lite-r5-owner-20261025/source')
GUI_MODEL=Path('/dev/shm/task1-native-GUI-lite-20261025/source')
POST=Path('/dev/shm/task1-E13-fine-light-post-20261025-run')
FINE=Path('/dev/shm/task1-E13-fineXY-20261025-run')
OLD_FINE=Path('/dev/shm/task1-P23-fineXY-20261025-run')
CID='E13-tangent-P23-centroids-225-XY102-Z97'
PHYSICAL_ID='E13-tangent-P23-centroids-225'
FIELD_VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1'
GUI_PREFIX='data-native/native-GUI-lite-r5-20261025/'
POST_PREFIX='data-native/E13-fine-light-post-20261025/'
FINE_PREFIX='data-native/E13-fineXY-20261025/'
BASE_VERSION='native-GUI-lite-r5-20261025'
BASE_OUTCOME='partial_payload_complete_functional_limit'
PUBLICATION_OUTCOME='readback_recovered_after_original_publication_timeout'
GUI5_RESULT_COMMIT='e16ec548ec8caa5f4557aa70965d26067b70aaf5'
GUI5_RESULT_RECEIPT_SHA='b467b32fd1a1506cd615930b26f7ddee450d54b019ae332744158bcd5f20c748'
ORIGINAL_FAILED_OWNER_SHA256='7951786439f2172536a259302fa978d441c009a9acde0214d040cb6f75e8b3e2'
RECOVERY=Path('/workspace/ngg-tis-task1/runtime/gui5-readback-recovery-20261025-run')
RECOVERY_SOURCE=Path('/workspace/ngg-tis-task1/runtime/gui5-readback-recovery-20261025.py')
RECOVERY_SOURCE_SHA='9ea2922a192b37f4761ab527fb149feb81e033430d7fac0214a8f84446a2ea85'
RECOVERY_RECORDS={'receipt':dict(path=str(RECOVERY/'receipt.json'),SHA256='22ebff67c24de66e822fd79c9e1598e61f9952e1088dfecdef3143073301653b',bytes=899),'preregistration':dict(path=str(RECOVERY/'preregistration.json'),SHA256='6b493dd09a53ef9f769d77da49ccf73c11eafb5199fde64030d78b95a0cbe3d1',bytes=13156),'source':dict(path=str(RECOVERY_SOURCE),SHA256=RECOVERY_SOURCE_SHA,bytes=10739)}
GUI5_SOURCE_COMMIT='23316b1781fc3f092a4091ab06e7b57a77b99075'
GUI5_SOURCE_RECEIPT_SHA='dbd2e800412368210ab6542a737d29ed70f305146804b21248681e16838de3de'
FUNCTIONAL_LIMIT_ERROR='Functional display JSON4.9MB bound exceeded; payload preserved, no automatic science/case omission'
OLD_CASE_IDS=('B0-square15-c10-diagonal-XY102-Z97','P23p5-peripheral-polyomino225-XY102-Z97','E13-tangent-P23-centroids-225','B0-square15-c10-diagonal','MP8-vertical-strips','MP12-vertical-strips','MP16-subpad2x2')
RUNTIME=Path('/workspace/ngg-tis-task1/runtime')
MAX_METADATA=8*1024**2
MAX_NATIVE=80*1024**2
MODES=('same_source_voltage','same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps')
KNOWN={
 'post_S':(POST/'source-publication/result-publication.json','d564f21313a6fddecce37a2ce04342b25ffc8691da3b7b678aaab3acbf22e853','10699c7cc15aba1853a75c679a67fdc0db4be1f0'),
 'post_R':(POST/'result-publication/result-publication.json','1e08a842caed439f02b41ed55d216c626d86e317140dad35811ec0971a529dc0','1be99e442c88bc94b8ddecb4607671c3cf102b9d'),
 'fine_S':(FINE/'source-publication/result-publication.json','e85b52386ccf76452fd7391f8f8a3df756b4b07c6d238bfd19aae1fb52007b8f','50a930fbe1fe08b0b0af2d00d99c79eec3b96fb4'),
 'fine_R':(FINE/'result-publication/result-publication.json','128c64313c836a48f8cd3799ec6b18c0b583ec3a679dbc0f27a93c5f06956135','f394cc9c2570f47a29968bea134a8078b98826d4'),
 'grid_R':(OLD_FINE/'result-publication/result-publication.json','0a9f71adef7439f19c2334ffef96c5f83e271c75c2440af3582615bfb998e075','fd0b0becc1f38d5c8118c929e7c5c4f24cc64c47')}
COPIED_SOURCE_SHA={
 'frozen_gui_build.py':'f802d13334f08fb35611e56afe674f4f21afe030fd77a47aa93bd17013b2e620',
 'gui_inputs.py':'1b5f66e4277c2fadde8290afdb4fa677b1d3971ecb0fdf7fa7e671067fcc3dd7',
 'lite_extract.py':'c796ba656d7e37ac7333a97ca86303052a9508d8e8aa4223f251cc398fcf412e'}

def require(ok,message):
 if not ok:raise ValueError(message)
def fullhex(v,n):return type(v)is str and re.fullmatch('[0-9a-f]{'+str(n)+'}',v)is not None
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for part in iter(lambda:f.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def metadata(path,expected):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.suffix=='.json'and 0<p.stat().st_size<=MAX_METADATA,'Bounded canonical published metadata only')
 raw=p.read_bytes();require(fullhex(expected,64)and hashlib.sha256(raw).hexdigest()==expected,'Full metadata SHA before JSON parse')
 return json.loads(raw)
def source_inventory():
 excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
 paths=sorted(p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md','.log')and p.name not in excluded)
 require(paths and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in paths),'Complete bounded canonical append-source inventory')
 return {str(SOURCE/p.name):digest(SOURCE/p.name)for p in paths}
def publication_witness(d,path=None):
 require(type(d)is dict and type(d.get('path'))is str and fullhex(d.get('SHA256'),64)and fullhex(d.get('commit'),40),'Actual publication receipt path/full SHA/commit witness')
 p=Path(d['path']);require(p.is_absolute()and p==p.resolve()and not p.is_symlink()and(str(p).startswith('/dev/shm/task1-')or p.is_relative_to(RUNTIME))and p.name=='result-publication.json','Canonical task1 publication witness')
 if path is not None:require(p==path,'Exact R5 source/result publication path; no synthetic/other run')
 return d

def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-native-GUI-append-E13fine-root-admission-v4'and a.get('status')=='selected_partial_payload_append_after_GUI5_readback_recovery'and a.get('root_authorized')is True and a.get('safe_boundary_confirmed')is True,'Separate positive root append decision after actual complete R5 publication')
 require(type(a.get('publication_outcome'))is str and a['publication_outcome']==PUBLICATION_OUTCOME and a.get('prior_recovery_terminal_dead_confirmed')is True,'Actual separate readback recovery terminal must be reviewed dead, not old GUI publication success')
 require(type(a.get('base_outcome'))is str and a['base_outcome']==BASE_OUTCOME and a.get('prior_owner_terminal_dead_confirmed')is True,'Only particular completed-payload functional failure after root confirms original terminal is dead')
 require(type(a.get('base_version'))is str and a['base_version']==BASE_VERSION,'Only the explicitly selected actual workspace R5 base; R4 failed before MFG/native')
 require(a.get('candidate_ids')==[CID]and type(a.get('candidate_ids'))is list and all(type(x)is str for x in a['candidate_ids']),'Only one E13fine append candidate')
 for key,value in dict(new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0,old_native_extractions=0,new_native_extractions=1,CPU_limit=4,physical_cap_bytes=8000000000,max_cells=800000).items():require(type(a.get(key))is int and a[key]==value,'Exact append-only scope/resources '+key)
 for key in('candidate_adopted','browser_authorized','old_GUI_pointers_modified'):require(a.get(key)is False,'No unsupported adoption/browser/pointer authorization '+key)
 require(type(a.get('source_sha256'))is dict and type(a.get('decision_basis'))is str and a['decision_basis'].strip(),'Canonical source map and actual decision basis')
 g=a.get('previous_GUI');require(type(g)is dict and type(g.get('publication_outcome'))is str and g['publication_outcome']==PUBLICATION_OUTCOME and type(g.get('base_outcome'))is str and g['base_outcome']==BASE_OUTCOME and type(g.get('base_version'))is str and g['base_version']==BASE_VERSION and g.get('run')==str(GUI),'Exact typed actual workspace R5 base version/run required; no R4 success alias')
 publication_witness(g.get('source_publication'),GUI/'source-publication/result-publication.json');publication_witness(g.get('result_publication'),GUI/'result-publication/result-publication.json')
 require(g['result_publication']['commit']==GUI5_RESULT_COMMIT and g['result_publication']['SHA256']==GUI5_RESULT_RECEIPT_SHA and g.get('readback_recovery')==RECOVERY_RECORDS,'Exact actual fullR and separate recovery receipt/prereg/source descriptors, not old M success')
 require(g['source_publication']['commit']==GUI5_SOURCE_COMMIT and g['source_publication']['SHA256']==GUI5_SOURCE_RECEIPT_SHA,'Exact actual GUI5 source; no other partial/future source admitted')
 t=g.get('terminal_owner');require(type(t)is dict and t.get('path')==str(GUI/'receipt.json')and t.get('SHA256')==ORIGINAL_FAILED_OWNER_SHA256 and type(t.get('bytes'))is int and 0<t['bytes']<MAX_METADATA,'Root-pinned actual failed terminal bytes; no previous M/success witness invented')
 return a

def direct(pub,path,target,expected=None):
 require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual complete readback publication only')
 row=pub.get('files',{}).get(target);require(type(row)is dict and row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<=MAX_NATIVE,'Exact direct SHA/bytes/readback proof '+target)
 require(expected is None or row['SHA256']==expected,'Exact actual published artifact SHA '+target)
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical deferred artifact descriptor; no byte read')
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=pub['commit'],publication_target=target,readback_passed=True,bytes_opened_here=False)

def same_descriptor(a,b):
 return all(a.get(k)==b.get(k)for k in('path','SHA256','bytes','publication_commit','publication_target'))
def validate_zero_work(v,keys):
 require(all(type(v.get(k))is int and v[k]==0 for k in keys),'No hidden solve/Q/eigen/angular/statistic work')
def validate_test_inventory(pre,inventory):
 require(type(inventory)is dict,'Actual published test inventory')
 expected=[]
 for namespace in('model','owner'):
  methods=inventory.get(namespace+'_methods');counts=inventory.get(namespace+'_counts');total=inventory.get(namespace+'_total')
  require(type(methods)is dict and methods and type(counts)is dict and set(counts)==set(methods),'Actual test module/count inventory '+namespace)
  for module,rows in methods.items():
   require(type(module)is str and module.startswith('test_')and type(rows)is list and rows and all(type(v)is str and v for v in rows)and len(set(rows))==len(rows)and type(counts[module])is int and counts[module]==len(rows),'Unique prospective source methods and exact counts '+namespace)
   expected.extend(module+'.'+method for method in rows)
  require(type(total)is int and total==sum(counts.values())and total>0 and type(pre.get('expected_'+namespace+'_tests'))is int and pre['expected_'+namespace+'_tests']==total,'Published preregistration agrees with actual source test count '+namespace)
 require(inventory['model_total']==16,'Byte-exact frozen extractor/renderer sixteen model tests')
 require(type(inventory.get('total'))is int and inventory['total']==inventory['model_total']+inventory['owner_total']==pre.get('expected_synthetic_tests')and len(expected)==len(set(expected))==inventory['total'],'Complete dynamic source inventory, no guessed42 or duplicate event IDs')
 return expected

def validate_partial_GUI_evidence(worker,stage,mfg,terminal,registration,pre,S,R,inventory,missing,caseproofs,cases,statdoc,payload,checkpoints):
 require(S.get('commit')==GUI5_SOURCE_COMMIT,'Only actual particular GUI5 source, not another same-count test run')
 require(worker.get('schema')=='task1-native-GUI-lite-worker-v1'and worker.get('status')=='failed_preserved'and worker.get('error_type')=='ValueError'and worker.get('error')==FUNCTIONAL_LIMIT_ERROR,'Only exact preserved functional display bound failure, not a field/MFG/memory failure')
 require(worker.get('GUI_generated')is False and worker.get('stored_native_phase_started')is True and worker.get('actual_native_bytes_may_have_been_read')is True and worker.get('actual_tests_run')==43,'Actual native phase after43PASS, never completed GUI success')
 boundary=worker.get('MFG_boundary',{});require(boundary.get('manufactured_phase')is False and boundary.get('scientific_API_spy_calls')==[]and boundary.get('native_IO_attempts')==[],'No caught native/MFG violation')
 validate_zero_work(worker,('new_PDE_RHS','new_Q_loads','new_eigen_solves','new_angular_evaluations','new_stat_reductions'))
 require(worker.get('candidate_adopted')is False and worker.get('browser_validation_performed')is False,'No candidate/browser validation')
 verification=worker.get('input_verification',{})
 for name in('before_MFG_metadata_only','after_MFG_before_native_bytes'):require(verification.get(name,{}).get('passed')is True and type(verification[name].get('count'))is int and verification[name]['count']>0 and verification[name].get('native_bytes_opened_by_verifier')is False,'Actual metadata SHA guards around source-bound MFG '+name)
 require(verification['after_MFG_before_native_bytes']['count']==verification['before_MFG_metadata_only']['count']+1,'Actual immutable MFG receipt added before native reads')
 require('after_native_GUI_build_metadata_only'not in verification,'Failed-before-return GUI does not invent an after-build worker proof')
 expected_events=validate_test_inventory(pre,inventory)
 require((inventory['model_total'],inventory['owner_total'],inventory['total'])==(16,27,43),'Actual fixed GUI5 source test inventory is16+27,not a guessed future variant')
 require(mfg.get('schema')=='task1-native-GUI-lite-manufactured-tests-v1'and mfg.get('status')=='passed'and mfg.get('source_publication_commit')==S['commit'],'Actual source-bound43PASS')
 for k,n in dict(model_source_test_count=16,model_tests_run=16,owner_tests_run=27,tests_run=43,expected_total_tests=43,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0).items():require(type(mfg.get(k))is int and mfg[k]==n,'Actual complete43 tests/no native I/O during MFG '+k)
 events=mfg.get('test_events',[]);require(type(events)is list and len(events)==43 and {e.get('test_id')for e in events}==set(expected_events)and all(e.get('outcome')=='passed'for e in events),'Every actual source method succeeded exactly once')
 require(mfg.get('owner_source_sha256')==mfg.get('source_sha256')==pre.get('source_sha256')and mfg.get('model_source_sha256')==pre.get('model_source_sha256')and registration.get('source_sha256')==pre['source_sha256'],'Complete actual GUI5 source/preregistration/MFG inventory identity')
 require(mfg.get('scientific_API_spy_calls')==[]and mfg.get('native_IO_attempts')==[]and mfg.get('field_admission_granted')is False and mfg.get('IO_audit_installed')is True and mfg.get('dependencies_initialized_before_mocks')is True and mfg.get('negative_fixture_counts',{}).get('native_suffix_rejection_before_open')==1,'Actual bounded I/O gate, not test failures or native reads relabelled PASS')
 require(stage.get('status')=='native_GUI_lite_failed_or_partial_preserved'and type(stage.get('worker_exit_code'))is int and stage['worker_exit_code']!=0 and stage.get('source_commit')==S['commit'],'Honest failed original execution stage published after parent metadata SHA loop')
 account=stage.get('accounting',{});require(account.get('passed')is False and account.get('summary_present')is False and account.get('partial_results_preserved')is True,'No missing summary forged to GUI success')
 require(terminal.get('schema')=='task1-native-GUI-lite-owner-v1'and terminal.get('status')=='failed_preserved'and terminal.get('failed_phase')=='result-publication'and terminal.get('error_type')=='ValueError'and terminal.get('error')=='Finite child failed result-publication; preserve log '+str(GUI/'logs/195-result-publication.log')and terminal.get('GUI_generated')is False and terminal.get('source_commit')is None and terminal.get('result_commit')is None,'Original dead publication-failed owner staysfailed; no old terminal success/source/result invented')
 require(type(terminal.get('finished_utc'))is str and terminal['finished_utc']and terminal.get('pid')==registration.get('supervisor_pid')and terminal.get('proc_start_ticks')==registration.get('proc_start_ticks')and registration.get('controller_path')==str(GUI_SOURCE/'guardian.py'),'Actual finished original owner identity')
 require(terminal.get('browser_validation_performed')is not True and terminal.get('candidate_adopted')is False and terminal.get('resources',{}).get('peak_accounted',8000000001)<=8000000000,'No old browser/adoption/8Gpass fabrication; publication failure is separate from worker-only functional error')
 require(missing.get('status')=='actual_outputs_and_absences_preserved'and set(missing.get('missing',[]))=={'index.html','summary.json','gui-build-receipt.json'},'Only original index/summary/GUIreceipt missing, not incomplete native cases')
 require(payload.get('path')==str(GUI/'payload.json')and payload.get('bytes')==5242129 and payload.get('readback_passed')is True and fullhex(payload.get('SHA256'),64),'Exact particular full saved5242129B payload from actual partialR')
 require(type(cases)is list and [r.get('candidate_id')for r in cases]==list(OLD_CASE_IDS)and type(caseproofs)is list and len(caseproofs)==7 and len(checkpoints)==7,'Seven exact source-registered completed cases, not six/duplicates/reordering')
 require(statdoc.get('native_bytes_opened')is False and type(statdoc.get('files'))is dict,'Original pre-MFG native stat guards retained')
 all_native=set()
 for i,(case,proof,cp)in enumerate(zip(cases,caseproofs,checkpoints)):
  cid=case['candidate_id'];require(proof.get('candidate_id')==cid and proof.get('large_native_arrays_released_before_next_case')is True and proof.get('original_statistics_recomputed')is False and proof.get('native_quantitative_metrics_recomputed')is False,'Actual per-case complete/released native display proof '+cid)
  validate_zero_work(proof,('actual_new_PDE_RHS','actual_new_Q_loads','actual_new_angular_evaluations'))
  require(type(proof.get('native_cells'))is int and 0<proof['native_cells']<=800000,'Original case physical count within unchanged cap')
  for kind,key in(('grid','stored_grid_SHA256'),('scalars','stored_scalar_SHA256'),('E2000','stored_E2000_SHA256')):require(proof.get(key)==case[kind]['SHA256'],'Completed proof names actual registered native source '+kind)
  expected=[case[k]for k in('grid','scalars','E2000','probe_arrays','mask','fractional_mask')if k in case]
  if case['geometry']['kind']=='polyomino':expected.append(case['geometry']['mask'])
  identity=lambda d:tuple(d.get(k)for k in('path','SHA256','bytes','publication_commit','publication_target'))
  actual=proof.get('native_file_proofs',[]);require(type(actual)is list and {identity(d)for d in actual}=={identity(d)for d in expected},'Exact native pre/post full-SHA proof coverage for every saved case source')
  for d in actual:
   require(d.get('full_SHA_before_verified')is True and d.get('full_SHA_after_verified')is True and d.get('readback_passed')is True and fullhex(d.get('SHA256'),64),'All native before/after byte identity checks actually recorded')
   st=statdoc['files'].get(d['path']);require(type(st)is list and len(st)==5 and st[2]==d['bytes'],'Every completed native source was stat guarded before MFG')
   all_native.add(d['path'])
  require(cp.get('completed_cases')==i+1 and cp.get('candidate_id')==cid and cp.get('native_arrays_released')is True,'Seven sequential actual case checkpoints')
 require(all_native==set(statdoc['files']),'All26 original guarded native inputs covered by completed case proofs; no old inputs read here')
 return True

def validate_readback_recovery(record,prereg,old_owner,R,result_receipt_SHA256,source_raw):
 require(record.get('schema')=='task1-GUI5-readback-recovery-v1'and record.get('status')=='GUI5_partial_result_readback_recovered'and record.get('source_commit')==GUI5_SOURCE_COMMIT and record.get('result_commit')==GUI5_RESULT_COMMIT,'Separate actual completed readback-only recovery, not old GUI success')
 require(record.get('original_GUI_owner_status')=='failed_preserved'and record.get('original_GUI_owner_receipt_SHA256')==ORIGINAL_FAILED_OWNER_SHA256 and record.get('result_publication_receipt_SHA256')==result_receipt_SHA256==GUI5_RESULT_RECEIPT_SHA,'Actual immutable original failure and recovered fullR receipt identity')
 require(record.get('original_GUI_worker_failure_retained')is True and record.get('old_owner_rewritten')is False and record.get('GUI_generated')is False and record.get('Windows_saved_verified')is False,'Readback recovery never generates GUI or rewrites old failure')
 for k in('new_PDE','new_native_array_decodes','branch_mutations'):require(type(record.get(k))is int and record[k]==0,'No new numerical/native/branch work in recovery '+k)
 require(type(record.get('pid'))is int and record['pid']>0 and type(record.get('proc_start_ticks'))is int and record['proc_start_ticks']>0 and type(record.get('finished_utc'))is str and record['finished_utc']and not any(k in record for k in('error','error_type','monitor_error')),'Actual terminal successful readback owner, not pending/failed state')
 require(type(record.get('files_verified'))is int and record['files_verified']==len(R.get('files',{}))==230 and all(d.get('readback_passed')is True and fullhex(d.get('SHA256'),64)for d in R['files'].values()),'All230 already-pushed blobs independently full-SHA verified')
 require(R.get('commit')==GUI5_RESULT_COMMIT and R.get('expected_parent')==GUI5_SOURCE_COMMIT and R.get('status')=='published_readback_verified'and R.get('transport')=='supported_Git_HTTPS_readback_only_recovery'and R.get('verification_source_SHA256')==RECOVERY_SOURCE_SHA and R.get('original_publisher_attempt_preserved')is True and R.get('no_new_commit_or_push')is True,'Actual standard full readback receipt from separate fresh verifier, not originalfailedattempt rewritten')
 require(prereg.get('schema')=='task1-GUI5-readback-recovery-plan-v1'and prereg.get('fixed_commit')==GUI5_RESULT_COMMIT and prereg.get('expected_parent')==GUI5_SOURCE_COMMIT and prereg.get('original_failed_owner')==old_owner,'Recovery preregistration binds exact fixed commit/parent/original failed owner')
 attempt=prereg.get('original_failed_publisher',{});require(attempt.get('schema')=='task1-Git-only-attempt-v1'and attempt.get('status')=='failed_preserved'and attempt.get('attempt')==1 and attempt.get('push_confirmed')is True and attempt.get('recorded_commit')==GUI5_RESULT_COMMIT,'Original timed-out but confirmed-pushed attempt remains failed')
 require(prereg.get('new_PDE')==0 and prereg.get('branch_mutations')==0 and prereg.get('verifier_source_SHA256')==RECOVERY_SOURCE_SHA and type(prereg.get('verifier_source_UTF8'))is str,'Recovery source/zero-work preregistration')
 raw=prereg['verifier_source_UTF8'].encode();require(raw==source_raw and len(raw)==10739 and hashlib.sha256(raw).hexdigest()==RECOVERY_SOURCE_SHA,'Exact Root executed readback verifier source, no code or transport substitution')
 return True

def validate_post(summary,worker,stage,verification,mfg,spec,S):
 require(summary.get('status')=='E13_fine_cached_highvolume_and40probe_postbatch_computed_unadopted'and summary.get('completed_native_geometries')==1 and summary.get('actual_threshold_subsets')==48 and summary.get('old_case_repeats')==0,'Actual E13fine-only complete postbatch')
 for k,n in dict(requested_probes=40,calculated_probes=40,unavailable_probes=0,strict_same_layer_bracket_available_probes=20,same_layer_extrapolated_probes=20).items():require(type(summary.get(k))is int and summary[k]==n,'Actual published E13fine probe accounting '+k)
 validate_zero_work(summary,('actual_new_PDE_RHS','actual_new_Q_loads','actual_new_eigen_solves','actual_new_angular_evaluations'))
 require(summary.get('candidate_adopted')is False and summary.get('original_results_overwritten')is False and summary.get('original_statistics_recomputed')is False,'No corrected/adopted/recomputed data')
 require(worker.get('status')=='native_light_post_computed'and worker.get('postprocess_accounting',{}).get('passed')is True and stage.get('status')=='native_light_post_computed'and stage.get('worker_exit_code')==0 and stage.get('source_commit')==S['commit'],'Actual post worker/stage completed')
 require(verification.get('before_tests_and_build',{}).get('passed')is True and verification.get('after_build',{}).get('passed')is True and verification['after_build']['count']>verification['before_tests_and_build']['count']and worker.get('input_verification')==verification,'Producing post full pre/post input SHA and added actual MFG receipt')
 require(mfg.get('status')=='passed'and mfg.get('source_publication_commit')==S['commit']and mfg.get('model_source_sha256')==spec['inputs']['source_sha256'],'Actual post source-bound manufactured success')
 for k,n in dict(model_source_test_count=26,model_tests_run=26,owner_tests_run=7,tests_run=33,expected_total_tests=33,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0).items():require(type(mfg.get(k))is int and mfg[k]==n,'Actual33-test post receipt '+k)
 require(mfg.get('native_Q_loaded')is False and mfg.get('scientific_API_spy_calls')==[],'Actual post MFG no native/Q activity')
 require(len(summary.get('candidates',[]))==1 and summary['candidates'][0].get('candidate_id')==CID,'Exactly the full fine E13 case, not old coarse data')
 return True

def validate_geometry(certificate):
 require(certificate.get('schema')=='task1-certified-centroid-ellipse-contact-v1'and certificate.get('passed')is True and certificate.get('area_rescaled')is False and certificate.get('analytic_centres_adjusted')is False and certificate.get('unresolved_potential_positive_support_omitted')is False,'Actual unchanged full positive fine ellipse support certificate')
 require(certificate.get('exact_h_mm')==dict(numerator=25,denominator=51)and certificate.get('injected_graph_node_count')==8184 and certificate.get('physical_pads')==4 and certificate.get('independent_outputs')==2 and certificate.get('physical_area_total_mm2')==900.0,'Actual XY102 fixedD50 fractional contacts, not coarse h0.5 mask')
 pre=certificate.get('preflight',{});require(pre.get('passed')is True and pre.get('no_resize')is True and pre.get('no_centre_adjustment')is True and pre.get('node_mapping')==['out0','out1','GND','GND']and len(pre.get('pads',[]))==4 and len(certificate.get('pads',[]))==4,'Exact physical four-pad/two-output topology')
 signs=((-1,-1),(1,1),(1,-1),(-1,1))
 for i,p in enumerate(pre['pads']):
  require(p.get('physical_pad_id')==i and p.get('analytic_area_mm2')==225.0 and p.get('tangential_semimajor_mm')==13.0 and p.get('analytic_centroid_exact')==[dict(numerator=sgn*5647,denominator=450)for sgn in signs[i]],'Physical a13/225mm2/actual exact P23 centroid, no replacement fit')
 require(all(p.get('physical_pad_id')==i and p.get('omitted_unresolved_area_upper_bound_m2')==0.0 and p.get('minimum_positive_fraction',0)>0 for i,p in enumerate(certificate['pads'])),'All positive fractions retained, no pruning/correction')
 return certificate

def normalization_rows(value):
 require(type(value)is dict and value.get('status')=='complete'and set(value.get('comparisons',{}))==set(MODES),'All four actual original-B0 normalization rows')
 for row in value['comparisons'].values():
  n=row.get('amplitude_scale');require(type(n)in(int,float)and math.isfinite(n)and n>=0,'Actual published finite amplitude scaling')
 return copy.deepcopy(value['comparisons'])

def make_spec(admission=None):
 if admission is None:
  p=SOURCE/'root-admission.json';require(p.is_file(),'Positive root append admission absent');admission=metadata(p,digest(p))
 a=validate_admission(admission);sources=source_inventory();require(a['source_sha256']==sources,'Complete canonical new append source map; no __file__ deployment key')
 pins=dict(sources);pubs={};pubmeta={};documents=[];native=[]
 def addpub(name,witness):
  publication_witness(witness);v=metadata(witness['path'],witness['SHA256']);require(v.get('status')=='published_readback_verified'and v.get('commit')==witness['commit'],'Actual completed publication '+name)
  pins[witness['path']]=witness['SHA256'];pubs[name]=v;pubmeta[name]=copy.deepcopy(witness);return v
 for name,(p,sha,commit)in KNOWN.items():addpub(name,dict(path=str(p),SHA256=sha,commit=commit))
 g=a['previous_GUI'];S=addpub('GUI_S',g['source_publication']);R=addpub('GUI_R',g['result_publication'])
 def read(name,path,target,expected=None):
  d=direct(pubs[name],path,target,expected);pins[d['path']]=d['SHA256'];return metadata(d['path'],d['SHA256']),d
 def gui(name,where='GUI_R'):return read(where,GUI/name,GUI_PREFIX+name)
 worker,wd=gui('worker-receipt.json');stage,staged=gui('execution-stage.json');mfg,mfgd=gui('synthetic-test-receipt.json');pre,pred=gui('preregistration.json','GUI_S');registration,regd=gui('registration.json','GUI_S');inventory,inventoryd=gui('test-source-inventory.json','GUI_S');oldspec,oldspecd=gui('spec.json','GUI_S');statdoc,statd=gui('native-descriptor-stat-registration.json','GUI_S');missing,missingd=gui('missing-output-inventory.json')
 terminal_desc=copy.deepcopy(g['terminal_owner']);terminal=metadata(terminal_desc['path'],terminal_desc['SHA256']);require(Path(terminal_desc['path']).stat().st_size==terminal_desc['bytes'],'Actual local failed-owner bytes match root pin');pins[terminal_desc['path']]=terminal_desc['SHA256']
 recovery_descriptors=copy.deepcopy(g['readback_recovery']);recovery_values={}
 for key,d in recovery_descriptors.items():
  q=Path(d['path']);require(q.is_file()and not q.is_symlink()and q.stat().st_size==d['bytes']and digest(q)==d['SHA256'],'Actual completed recovery receipt/prereg/source bytes');pins[str(q)]=d['SHA256']
  recovery_values[key]=metadata(q,d['SHA256'])if key!='source'else q.read_bytes()
 validate_readback_recovery(recovery_values['receipt'],recovery_values['preregistration'],terminal,R,g['result_publication']['SHA256'],recovery_values['source'])
 payload=direct(R,GUI/'payload.json',GUI_PREFIX+'payload.json');index=None
 absent=[str(GUI/n)for n in('index.html','summary.json','gui-build-receipt.json')]
 require(all(not Path(p).exists()for p in absent)and all(GUI_PREFIX+Path(p).name not in R['files']for p in absent),'Original missing outputs actually absent locally and in partialR; no index/success invented')
 caseproofs=[];case_desc=[];checkpoints=[];checkpoint_desc=[]
 for i,cid in enumerate(OLD_CASE_IDS):
  value,d=gui('case-proofs/'+cid+'.json');caseproofs.append(value);case_desc.append(d)
  value,d=gui('checkpoint-GUI-%02d.json'%(i+1));checkpoints.append(value);checkpoint_desc.append(d)
 cases=oldspec['inputs']['cases'];validate_partial_GUI_evidence(worker,stage,mfg,terminal,registration,pre,S,R,inventory,missing,caseproofs,cases,statdoc,payload,checkpoints)
 require(R.get('expected_parent')==S['commit']and pre['test_inventory_SHA256']==inventoryd['SHA256']and pre['spec_SHA256']==oldspecd['SHA256']and pre['native_descriptor_stats_SHA256']==statd['SHA256'],'Actual source-CAS partial result and exact source/test/stat-guard metadata')
 # Read no old native arrays or payload. Stream-authenticate all original bounded
 # source/metadata pins so published parent post-child SHA stage stays linked.
 original_pins={**pre['source_sha256'],**pre['frozen_source_sha256'],**pre['metadata_input_sha256'],**pre['helper_sha256'],**pre['execution_policy_refs']}
 require(worker['input_verification']['before_MFG_metadata_only']['count']==len(original_pins),'Actual original complete metadata guard coverage')
 for path,sha in original_pins.items():
  q=Path(path);require(q.is_absolute()and q==q.resolve()and q.is_file()and not q.is_symlink()and q.suffix in('.py','.json','.md','.txt','.log')and digest(q)==sha,'Complete original source/metadata guard identity, never native decode')
  pins[str(q)]=sha
 documents.append(payload)
 aliases=[]
 for label,d in [('readback-recovery-receipt',recovery_descriptors['receipt']),('readback-recovery-preregistration',recovery_descriptors['preregistration']),('readback-recovery-source',recovery_descriptors['source']),('failed-owner',terminal_desc),('source-publication',g['source_publication']),('partial-result-publication',g['result_publication']),('failed-worker-and-error',wd),('failed-execution-stage',staged),('passed-43-MFG',mfgd),('preregistration',pred),('registration',regd),('test-inventory',inventoryd),('native-stat-guards',statd),('missing-outputs',missingd)]+[('case-proof-%02d'%i,d)for i,d in enumerate(case_desc)]+[('completed-checkpoint-%02d'%i,d)for i,d in enumerate(checkpoint_desc)]:
  q=Path(d['path']);expected=d['SHA256'];require(q.is_file()and not q.is_symlink()and 0<q.stat().st_size<MAX_METADATA and digest(q)==expected,'Exact bounded prior partial/failure alias bytes')
  aliases.append(dict(label=label,path=str(q),SHA256=expected,bytes=q.stat().st_size,new_source_publication_required=True,original_preserved=True));pins[str(q)]=expected
 source_test_methods={}
 for path,sha in pre['source_sha256'].items():
  original=Path(path);require(original.is_relative_to(GUI_SOURCE)or original.is_relative_to(GUI_MODEL),'Actual R5 canonical owner/model source origin')
  namespace='owner'if original.is_relative_to(GUI_SOURCE)else'model';target='tools/native_GUI_lite_r5_20261025/'+namespace+'/'+original.name
  require(S['files'].get(target,{}).get('readback_passed')is True and S['files'][target]['SHA256']==sha,'Complete R5 source inventory published before tests/build')
  if original.name.startswith('test_')and original.suffix=='.py':
   require(original.is_file()and not original.is_symlink()and original.stat().st_size<MAX_METADATA and digest(original)==sha,'Actual canonical published test source before AST inventory')
   pins[str(original)]=sha;tree=ast.parse(original.read_text(),filename=str(original));source_test_methods[(namespace,original.stem)]=[cls.name+'.'+method.name for cls in tree.body if isinstance(cls,ast.ClassDef)for method in cls.body if isinstance(method,(ast.FunctionDef,ast.AsyncFunctionDef))and method.name.startswith('test_')]
 for namespace in('model','owner'):
  require({module:rows for(ns,module),rows in source_test_methods.items()if ns==namespace}==inventory[namespace+'_methods'],'Actual full published source AST exactly matches prospective test inventory '+namespace)
 for name,sha in COPIED_SOURCE_SHA.items():
  p=SOURCE/name;require(sources.get(str(p))==sha,'Byte-exact authenticated copied source '+name)
  original='gui_build.py'if name=='frozen_gui_build.py'else name;namespace='model'if name=='lite_extract.py'else'owner';target='tools/native_GUI_lite_r5_20261025/'+namespace+'/'+original
  require(S['files'].get(target,{}).get('readback_passed')is True and S['files'][target]['SHA256']==sha,'Copied source direct original R5 S proof '+name)
 post_spec,_=read('post_S',POST/'spec.json',POST_PREFIX+'spec.json');post_sum,postsd=read('post_R',POST/'summary.json',POST_PREFIX+'summary.json');postworker,_=read('post_R',POST/'worker-receipt.json',POST_PREFIX+'worker-receipt.json');poststage,_=read('post_R',POST/'execution-stage.json',POST_PREFIX+'execution-stage.json');postverify,_=read('post_R',POST/'input-SHA-verification.json',POST_PREFIX+'input-SHA-verification.json');postmfg,postmfgd=read('post_R',POST/'synthetic-test-receipt.json',POST_PREFIX+'synthetic-test-receipt.json')
 validate_post(post_sum,postworker,poststage,postverify,postmfg,post_spec,pubs['post_S']);require(postworker['summary_SHA256']==postsd['SHA256']and postworker['manufactured_test_receipt_SHA256']==postmfgd['SHA256'],'Actual post worker names the exact summary/MFG bytes')
 for path,sha in postmfg['model_source_sha256'].items():
  target='tools/E13_fine_light_post_20261025/model/'+Path(path).name;require(pubs['post_S']['files'].get(target,{}).get('SHA256')==sha and pubs['post_S']['files'][target].get('readback_passed')is True,'Full producing post source inventory')
 fine_summary,_=read('fine_R',FINE/'summary.json',FINE_PREFIX+'summary.json');fine_spec,_=read('fine_S',FINE/'spec.json',FINE_PREFIX+'spec.json');raw_manifest,_=read('fine_R',FINE/'raw-manifest.json',FINE_PREFIX+'raw-manifest.json')
 context=post_spec['inputs'];require(len(context.get('datasets',[]))==1 and context['datasets'][0]['candidate_id']==CID,'Actual source-published single E13fine post input')
 dataset=context['datasets'][0];row=next(r for r in fine_summary['candidates']if r['candidate_id']==CID)
 require(row==dataset['record']and row['physical_geometry_id']==PHYSICAL_ID and row['grid_variant']=='XY102-Z97'and row['scalar_archive_kind']=='full_new_fine97'and row['Q_resident_during_metrics']is False,'Full original fine97 row; not coarseSC4/display pixels')
 require(type(fine_spec['inputs']['source_sha256'])is dict and len(fine_spec['inputs']['source_sha256'])==18 and fine_spec['field_estimator_version']==FIELD_VERSION and fine_spec['fine_cells']==793848 and fine_spec['common97_layer_counts']==[4,19,18,56]and raw_manifest['Q_frames_returned']is True and raw_manifest['GC_before_postprocessing']is True,'Actual original fine97 executed field ABI and released Q')
 for path,sha in fine_spec['inputs']['source_sha256'].items():
  target='tools/E13_fineXY_20261025/model/'+Path(path).name;require(pubs['fine_S']['files'].get(target,{}).get('SHA256')==sha and pubs['fine_S']['files'][target].get('readback_passed')is True,'Actual complete producing fine source inventory')
 grid=direct(pubs['grid_R'],dataset['grid']['path'],dataset['grid']['publication_target'],dataset['grid']['SHA256']);scalar=direct(pubs['fine_R'],dataset['scalars']['path'],dataset['scalars']['publication_target'],dataset['scalars']['SHA256']);raw0=raw_manifest['fine']['E13']['2000']['raw'];E2000=direct(pubs['fine_R'],raw0['path'],FINE_PREFIX+'rhs/E13-XY102-2000-raw.npz',raw0['SHA256'])
 require(same_descriptor(grid,dataset['grid'])and same_descriptor(scalar,dataset['scalars'])and E2000['bytes']==raw0['bytes']and E2000['SHA256']==dataset['raw_by_frequency']['2000']['SHA256'],'Exact native grid/scalars/2000 carrier source descriptors')
 certificate,certd=read('fine_R',FINE/'fine-E13-contact-certificate.json',FINE_PREFIX+'fine-E13-contact-certificate.json','6bff68986695fc693d80ccb0c879f4e3cbbc2f992c5e56ad432045bd4057d37e');validate_geometry(certificate)
 postrow=post_sum['candidates'][0];probe_desc=postrow['probe_receipt'];prediction,predproof=read('post_R',probe_desc['path'],POST_PREFIX+'candidates/'+CID+'/native-probe-predictions.json',probe_desc['SHA256']);high_desc=postrow['high_volume_receipt'];high,highproof=read('post_R',high_desc['path'],POST_PREFIX+'candidates/'+CID+'/cached-high-modulation-volumes.json',high_desc['SHA256']);pa=postrow['probe_arrays'];probe_arrays=direct(pubs['post_R'],pa['path'],POST_PREFIX+'candidates/'+CID+'/native-probe-small-arrays.npz',pa['SHA256'])
 require(probe_arrays['bytes']==pa['bytes']and same_descriptor(dict(prediction['small_arrays'],publication_commit=pubs['post_R']['commit'],publication_target=probe_arrays['publication_target']),probe_arrays),'Actual stored small waveforms match actual forty-probe JSON')
 require(prediction['probe_count']==40 and prediction['calculated_probe_count']==40 and prediction['unavailable_probe_count']==0 and prediction['strict_same_layer_bracket_available_probe_count']==20 and prediction['same_layer_extrapolated_probe_count']==20 and len(prediction['probes'])==40 and high['actual_threshold_subsets']==48,'Actual forty complete rows/20strict20extrap/48subsets; no inferred missing fields')
 native=[grid,scalar,E2000,probe_arrays];require(len({d['path']for d in native})==4 and all(Path(d['path']).suffix=='.npz'for d in native),'Exactly four new-case native archives, no old-seven native extraction inputs')
 case=dict(candidate_id=CID,label='E13 fine (unadopted)',physical_geometry_id=PHYSICAL_ID,section='new_native',grid_variant='XY102-Z97',pad_count=4,grid=grid,scalars=scalar,E2000=E2000,probe_arrays=probe_arrays,probe_json=predproof,probe_record=prediction,high_volume=highproof,high_volume_record=high,record=copy.deepcopy(row),normalizations=normalization_rows(row['normalizations_to_original_coarse101_B0']),provenance=copy.deepcopy(dataset['provenance']),geometry=dict(kind='ellipse',record=dict(preflight_and_contact=copy.deepcopy(certificate)),source_certificate=certd))
 require(case['normalizations']==normalization_rows(dataset['normalizations']),'Full original Float64 normalization rows unchanged')
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(metadata(ap,digest(ap))==a,'Exact immutable root append admission');pins[str(ap)]=digest(ap)
 holds=dict(previous_GUI=copy.deepcopy(oldspec['inputs']['holds']),previous_GUI_partial_failure=dict(publication_outcome=PUBLICATION_OUTCOME,readback_recovery_status=recovery_values['receipt']['status'],original_failed_owner_not_rewritten=True,status=terminal['status'],worker_error_type=worker['error_type'],worker_error=worker['error'],completed_case_proofs=7,full_payload_saved=True,index_created=False,previous_GUI_complete_success=False),E13_fine=copy.deepcopy(fine_summary['holds']),E13_fine_adjacent_grid_diagnostics=copy.deepcopy(fine_summary.get('prospective_adjacent_grid_diagnostics')),E13_post=copy.deepcopy(post_sum['inherited_holds']))
 previous=dict(base_version=BASE_VERSION,base_outcome=BASE_OUTCOME,publication_outcome=PUBLICATION_OUTCOME,readback_recovery_descriptors=recovery_descriptors,readback_recovery_status=recovery_values['receipt']['status'],old_owner_failure_preserved_not_relabelled=True,source_publication=pubmeta['GUI_S'],partial_result_publication=pubmeta['GUI_R'],failed_terminal_owner=terminal_desc,failed_worker=wd,failed_execution_stage=staged,model_source_sha256=copy.deepcopy(pre['model_source_sha256']),source_sha256=copy.deepcopy(pre['source_sha256']),actual_MFG_tests=43,actual_MFG_model_tests=16,actual_MFG_owner_tests=27,test_inventory=inventoryd,completed_case_proofs=case_desc,completed_checkpoints=checkpoint_desc,native_stat_guard=statd,all_26_prior_native_files_had_before_after_SHA_proofs=True,metadata_guard_count=len(original_pins),previous_GUI_complete_success=False,previous_index_unavailable=True,partial_R_full_readback=True,old_owner_failure_preserved=True,browser_validation_performed=False,old_cases_reextracted=False)
 return dict(schema='task1-native-GUI-append-E13fine-inputs-v4',base_version=BASE_VERSION,base_outcome=BASE_OUTCOME,publication_outcome=PUBLICATION_OUTCOME,root_admission=copy.deepcopy(a),previous_payload=payload,previous_index=None,previous_index_unavailable=True,previous_index_missing=dict(path=str(GUI/'index.html'),reason='never_created_after_functional_limit'),original_absences=absent,prior_failure_alias_descriptors=aliases,document_input_descriptors=documents,previous_GUI_evidence=previous,new_case=case,metadata_input_sha256=pins,native_input_descriptors=native,source_sha256=sources,model_source_sha256=sources,publication_proofs=pubmeta,current_actual_stats=dict(record=copy.deepcopy(row['metrics']),normalizations=copy.deepcopy(case['normalizations']),probe_rows=copy.deepcopy(prediction['probes']),statistics_recomputed=False),inherited_holds=copy.deepcopy(holds),holds=copy.deepcopy(holds),provenance=dict(publication_outcome=PUBLICATION_OUTCOME,GUI5_readback_recovery=recovery_descriptors,original_GUI5_terminal_failed_preserved=True,new_post_summary=postsd,new_probe_JSON=predproof,new_high_volume_JSON=highproof,fine_contact_certificate=certd,recovered_fine_publication=copy.deepcopy(context['E13_publication_recovery']),field_version=FIELD_VERSION),expected_cases_after_append=8,expected_new_native_cases=4,expected_legacy_reference_cases=4,expected_probes_after_append=160,strict_same_layer_probes_after_append=80,extrapolated_probes_after_append=80,old_native_extractions=0,new_native_extractions=1,preparation_payload_index_or_native_bytes_opened=False,new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0,candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['metadata_input_sha256'])
