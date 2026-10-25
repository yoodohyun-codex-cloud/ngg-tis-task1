"""Deferred metadata-only E13 fine-XY comparison prerequisites; import inert."""
import copy,hashlib,json,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-E13-fineXY-20261025/source')
NATIVE=Path('/dev/shm/task1-streamed-Q-native-restore-20261025-run')
MFG=Path('/dev/shm/task1-streamed-Q-MFG-20261025-run')
FINE=Path('/dev/shm/task1-P23-fineXY-20261025-run')
COARSE=Path('/dev/shm/task1-centroid-ellipse-20261025-run')
FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
FINE_GRAPH=Path('/dev/shm/task1-layer-dtn-xy102-20261025-run')
COARSE_GRAPH=Path('/dev/shm/task1-layer-dtn-20261025-run')
E13='E13-tangent-P23-centroids-225';B0='B0-square15-c10-diagonal'
FIELD_VERSION='native-lateral-half-face-v1+analytic-z-DtN-v1';MAX_METADATA=8*1024**2
REMOTE_Q_COMMIT='d725ee29ee568ef26a4b7579e9dfc55d23e0681a'
NORMALIZED_Q=Path('/dev/shm/task1-transfer-20261025/cache-publication-normalized.json')
NORMALIZED_Q_SHA='f05f5eb7f37aabdba649ca1c445217aed82663c3bbf875b7193afd7031e35a4f'
ORIGINAL_Q_RECEIPT=Path('/dev/shm/task1-cache-retention-20261025-run/public-receipt.json')
ORIGINAL_Q_RECEIPT_SHA='589dad62a301761c930e03f7a74fd33d53caf550e3e5613fbcd10143c4dfd634'
OPERATOR_SHA='4a4276096f6eeb7d0e085bc7f9f3f0f0c97eb1a39c1c2de899b77b28668dcf0e'
MFG_MODEL_SHA={'/dev/shm/task1-streamed-Q-20261025/source/streamed_real_q.py':OPERATOR_SHA,'/dev/shm/task1-streamed-Q-20261025/source/test_streamed_real_q.py':'8230fdc374d70942d46dd648ef01cf6da17c5d117f2a0072b70f2831fcfe46b9','/dev/shm/task1-streamed-Q-20261025/source/OPERATOR_CONTRACT.md':'1c82247c211e9c65b00079feef58d69798a927803a42d10e58de5571489e896c'}
FIXED_PUBLICATIONS={
 'fine_R':(FINE/'result-publication/result-publication.json','0a9f71adef7439f19c2334ffef96c5f83e271c75c2440af3582615bfb998e075','fd0b0becc1f38d5c8118c929e7c5c4f24cc64c47'),
 'E13_R':(COARSE/'result-publication/result-publication.json','bb22a13b9542cd8fdd0afff05f89d0a6fab80755b7d5d9039be251c8bfac00c2','a6ee5d2b7c3438d9060a6fd8202b390be0ad9069'),
 'E13_S':(COARSE/'source-publication/result-publication.json','029b21c7458caf30652f4a84b487384a550802429e788fbdfd64d2e38a7ea5f9','b5b5dad73184ada8daf16350e059d6b17067c02c'),
 'first8_R':(FIRST8/'result-publication/result-publication.json','d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159','4d6207caa60ae16ab7a7e997022ac72653b97ec3'),
 'first8_S':(FIRST8/'source-publication/result-publication.json','cb8939fdd21b3c4d7103eeb26c3591037402553d4369aa195888e30930b1eb49','c8e5f2f9d4fbba5646944772d526533ecedbbab1'),
 'coarse_graph_R':(COARSE_GRAPH/'result-publication/result-publication.json','41e21c0eb3551b628083aa8e32c5f4ddcb4a8407cfa0202f9e46ddfd064eba1f','815327e978ec5e3976ba9a462510d6faac6f318a'),
 'old47_R':(Path('/dev/shm/task1-P23-fineXY-synthetic-r2-20261025-run/result-publication/result-publication.json'),'60c01ccc60cd6478ba285035f1d98993013d76cda09af0e8ba5b057f3fafd6b6','fef95229d10023caffe733047b5ae59492132bd8')}

def require(ok,message):
 if not ok:raise ValueError(message)
def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def metadata(path,expected):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink()and p.is_file()and 0<p.stat().st_size<MAX_METADATA,'Canonical bounded source/metadata only')
 require(fullhex(expected,64),'Full expected metadata SHA required');raw=p.read_bytes();require(hashlib.sha256(raw).hexdigest()==expected,'Exact metadata bytes before parse');return json.loads(raw)
def source_inventory():
 excluded={'root-admission.json','synthetic-test-receipt.json','tests-receipt.json'}
 files=sorted(p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')and p.name not in excluded)
 require(any(p.name=='e13_inputs.py'for p in files)and all(not p.is_symlink()and p.stat().st_size<MAX_METADATA for p in files),'Complete canonical bounded source inventory')
 return{str(SOURCE/p.name):digest(SOURCE/p.name)for p in files}
def direct(pub,path,target,expected=None):
 require(pub.get('status')=='published_readback_verified'and fullhex(pub.get('commit'),40),'Actual immutable full readback, not pending/failure plan')
 p=Path(path);require(p.is_absolute()and p==p.resolve()and not p.is_symlink(),'Canonical deferred artifact descriptor')
 row=pub['files'][target];require(row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<=80*1024**2,'Direct original full SHA/byte/readback proof')
 require(expected is None or row['SHA256']==expected,'Unchanged original artifact identity')
 return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_target=target,publication_commit=pub['commit'],readback_passed=True,decoded_here=False)
def validate_admission(a):
 require(type(a)is dict and a.get('schema')=='task1-E13-fineXY-root-admission-v1'and a.get('status')=='admitted_after_published_native_streamed_B0_PASS'and a.get('root_review_positive')is True and a.get('sole_NUM_owner')is True,'Separate root decision after actual native B0 full PASS')
 fixed=dict(new_fine_driven_RHS=2,new_coarse_driven_RHS=0,cached_coarse_SC4_responses=2,new_eigen_solves=0,new_fine_full_angular_evaluations=1,new_coarse_SC4_angular_evaluations=1,repeated_original93_bulk_angular_evaluations=0,fine_B0_PDE_or_angular_repeats=0,physical_pads=4,independent_outputs=2,frequencies_Hz=[2000,2010],fine_evaluation_cells=793848,coarse_common97_cells=762420,max_physical_evaluation_cells=800000,CPU_limit=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,candidate_adopted=False)
 for key,value in fixed.items():require(key in a and type(a[key])is type(value)and a[key]==value,'Exact prospective E13 geometry/work scope '+key)
 require(type(a.get('source_sha256'))is dict and type(a.get('decision_basis'))is str and a['decision_basis'].strip(),'Frozen source inventory and explicit root rationale')
 r=a.get('native_restore_review');require(type(r)is dict and r.get('run')==str(NATIVE)and r.get('publication_path')==str(NATIVE/'result-publication/result-publication.json')and r.get('root_reviewed')is True,'Only exact actual native restore run/publication can admit this candidate')
 require(fullhex(r.get('publication_SHA256'),64)and fullhex(r.get('publication_commit'),40)and type(r.get('decision_basis'))is str and r['decision_basis'].strip(),'Actual future native restore R identity/review; no pending/failed substitutes')
 t=r.get('terminal_owner_receipt');require(type(t)is dict and t.get('path')==str(NATIVE/'receipt.json')and fullhex(t.get('SHA256'),64)and type(t.get('bytes'))is int and 0<t['bytes']<MAX_METADATA,'Separate exact root-pinned completed owner receipt written after native R')
 return a


def validate_mfg(value,model_sources,source_commit):
 require(type(value)is dict and value.get('status')=='passed'and value.get('kind')=='actual_tiny_streamed_real_Q_operator_fixtures_only','Actual passed manufactured operator fixture receipt required')
 require(value.get('source_publication_commit')==source_commit and value.get('model_source_sha256')==model_sources and value.get('source_sha256')==model_sources,'Actual MFG source bindings')
 for key,num in dict(model_source_test_count=12,tests_run=20,expected_total_tests=20,model_tests_run=12,owner_tests_run=8,tests_failed=0,tests_errors=0,tests_skipped=0,native_RHS=0,native_field_reads=0,native_file_reads=0,native_eigen_solves=0,native_full_field_exports=0,native_field_angular_work=0).items():
  require(type(value.get(key))is int and value[key]==num,'Actual frozen12+8 MFG accounting '+key)
 for key in('native_Q_loaded','native_eigen_performed','native_restore_performed','field_admission_granted','candidate_adopted'):require(value.get(key)is False,'MFG never grants native work '+key)
 require(value.get('forbidden_field_calls')==[]and value.get('native_IO_attempts')==[]and value.get('IO_audit_installed')is True and value.get('synthetic_metadata_proofs_are_fixture_values')is True,'No actual native data or caught scope violations in manufactured PASS')
 events=value.get('test_events');require(type(events)is list and len(events)==20 and len({r['test_id']for r in events})==20 and all(r.get('outcome')=='passed'for r in events),'Every actual frozen synthetic method passed, no invented aggregate')
 for key in('operator_constructors','metadata_validation_calls','forward_attempts','transpose_attempts','slice_attempts','chunk_visits_started','chunk_visits_completed','operator_receipts'):
  require(type(value.get('manufactured_work_counts',{}).get(key))is int and value['manufactured_work_counts'][key]>0,'Actual synthetic operator calls '+key)
 return True


def validate_chunk_receipts(manifest, normalized, original, *, n, grid_name):
    """Pure proof-chain validation; never overwrites historical manifest flags."""
    require(normalized.get('status') == 'published_readback_verified'
            and normalized.get('commit') == REMOTE_Q_COMMIT
            and normalized.get('original_public_receipt_SHA256') == ORIGINAL_Q_RECEIPT_SHA,
            'Actual standard retained-Q publication receipt')
    require(original.get('schema') == 'task1-retained-cache-public-readback-receipt-v1'
            and original.get('commit') == REMOTE_Q_COMMIT and isinstance(original.get('files'), list),
            'Original retained-Q receipt list and fixed commit')
    require(manifest['shape'] == [n, n] and manifest['dtype'] == '<f8'
            and manifest['order'] == 'F', 'Exact original real-Q matrix ABI')
    original_files = {row['repo_relative_path']: row for row in original['files']}
    require(len(original_files) == len(original['files']), 'Unique original remote file proofs')
    at, total, proofs = 0, 0, []
    for chunk in manifest['chunks']:
        require(chunk['row_start'] == 0 and chunk['row_stop'] == n
                and chunk['column_start'] == at and at < chunk['column_stop'] <= n
                and chunk['dtype'] == '<f8' and chunk['order'] == 'F'
                and chunk['bytes'] == n * (chunk['column_stop'] - at) * 8,
                'Ordered disjoint complete original Q chunk ABI')
        target = 'data-native/retained-eigen-cache-20261025/' + grid_name + '/' + Path(chunk['path']).name
        require(target in normalized['files'] and target in original_files, 'Every actual Q chunk needs direct remote proof')
        a, b = normalized['files'][target], original_files[target]
        require(a['readback_passed'] is True and b['readback_passed'] is True
                and b['commit'] == REMOTE_Q_COMMIT
                and a['SHA256'] == b['SHA256'] == chunk['SHA256']
                and a['bytes'] == b['bytes'] == chunk['bytes']
                and a['Git_blob_SHA'] == b['Git_blob_SHA'], 'Exact remote Q full SHA/bytes/Git blob readback')
        proofs.append(dict(path=chunk['path'], SHA256=chunk['SHA256'], bytes=chunk['bytes'],
                           publication_target=target, publication_commit=REMOTE_Q_COMMIT,
                           Git_blob_SHA=a['Git_blob_SHA'], readback_passed=True))
        total += chunk['bytes']
        at = chunk['column_stop']
    require(at == n and total == n * n * 8, 'All Q columns/bytes authenticated without decoding')
    return proofs


def validate_cached_gates(p):
 require(p.get('passed')is True and p.get('passivity_passed')is True and p.get('physical_gates',{}).get('passed')is True,'Fresh unchanged five circuit/power/passivity gates before E reconstruction')
 limits=dict(relative_algebraic_residual=2e-7,relative_loaded_current_residual=2e-7,relative_all_pad_KCL=2e-6,relative_output_pad_current=2e-6,relative_complex_power_error=2e-7)
 metrics=p['physical_gates'].get('metrics',{});require(set(metrics)==set(limits),'All five original numerical metrics retained')
 for key,limit in limits.items():require(metrics[key].get('passed')is True and metrics[key].get('limit')==limit,'Original circuit gate not relaxed '+key)
 require(p.get('actual_new_RHS')==0 and p.get('iterations')==0 and p.get('matvec_count')==0 and p.get('new_Krylov_calls')==0 and p.get('reused_published_baseline_surface')is True,'Cached response only; no solve/Krylov fallback')
 require(p.get('modal_restore_passed')is True and 0<=p.get('modal_restore_relative_error',-1)<=2e-7 and p.get('modal_restore_limit')==2e-7 and p.get('stored_source_current_restore_passed')is True and p.get('stored_power_restore_comparison',{}).get('passed')is True,'Modal/current/signed-power restore gates before field comparison')
 return dict(passed=True,new_PDE_RHS=0,new_Krylov_calls=0)


def validate_summary(s):
 require(s.get('status')=='two_cached_native_carriers_streamed_Q_restore_computed_unadopted','Exact completed cached-native restore status')
 for key,num in dict(completed_cached_native_responses=2,actual_native_E_reconstructions=2,actual_native_field_comparisons=2,actual_new_PDE_RHS=0,actual_new_Krylov_calls=0,actual_new_eigen_solves=0,actual_new_angular_evaluations=0,new_native_phi_or_E_archives=0,new_Q_archives=0).items():require(type(s.get(key))is int and s[key]==num,'Exact finite restored-work/no-new-solve count '+key)
 require(s.get('frequencies_Hz')==[2000,2010]and s.get('actual_native_Q_read')is True and all(s.get(key)is False for key in('whole_Q_loaded','full_Q_materialized','complex_Q_materialized')),'Actual streamed real nativeQ; no full/complexQ')
 rows=s.get('responses',[]);require(len(rows)==2 and [(r.get('frequency_Hz'),r.get('active_output'))for r in rows]==[(2000,0),(2010,1)],'Exactly original two cached carrier/output responses')
 for r in rows:
  require(r.get('native_Q_read')is True and r.get('whole_Q_loaded')is False and r.get('Q_closed_and_profiles_released_before_error_reduction')is True and r.get('field_reconstruction_saved')is False,'Operator/profile lifetime ended before RAM-only original-field comparison')
  for key in('new_PDE_RHS','new_Krylov_calls','new_eigen_solves','new_angular_evaluations'):require(type(r.get(key))is int and r[key]==0,'No hidden per-carrier solve/search '+key)
  require(type(r.get('field_error',{}).get('passed'))is bool and r.get('candidate_adopted')is False,'Honest retained field-error diagnostic; no adoption')
 expected=all(r['field_error']['passed']for r in rows);require(s.get('native_restore_verification_passed')is expected,'Field-equivalence gate failures remain failed computed results')
 for key in('phase_fit','gauge_fit','original_results_overwritten','full_mesh_convergence','experimental_validation','physiological_activation_or_safety_claim','candidate_adopted','Windows_saved_verified'):require(s.get(key)is False,'No fitted equivalence or unsupported validation/storage/adoption '+key)
 require(s.get('same_physical_coordinates_and_grid_verified')is True and s.get('inherited_holds',{}).get('old_independent_5percent_interface_failures_preserved')is True,'Same physical grid/old failed diagnostics retained')
 return dict(passed=True,completed_cached_native_responses=2,new_PDE_RHS=0,new_Krylov_calls=0,E_reconstructions=2,new_angular_evaluations=0,native_Q_read=True,full_Q_materialized=False,native_field_equivalence_passed=expected,candidate_adopted=False)

def require_native_PASS(summary):
 accounting=validate_summary(summary)
 require(summary.get('native_restore_verification_passed')is True and accounting['native_field_equivalence_passed']is True,'Computed native restore with failed field gate cannot admit new PDE')
 require(all(row['field_error'].get('passed')is True and row['field_error'].get('pointwise_passed')is True and row['field_error'].get('component_passed')is True and row['field_error'].get('vector_passed')is True for row in summary['responses']),'Every actual native component/vector/pointwise field gate passed')
 return accounting

def validate_native_completion(worker,stage,verification,terminal,*,summary_SHA256,source_commit,result_commit,local_MFG_receipt_SHA256):
 require(worker.get('status')=='streamed_Q_cached_native_restore_computed'and worker.get('summary_SHA256')==summary_SHA256,'Actual native worker completed after build/source verification')
 require(stage.get('status')=='streamed_Q_native_restore_computed'and type(stage.get('worker_exit_code'))is int and stage['worker_exit_code']==0 and stage.get('source_commit')==source_commit,'Actual native owner execution stage completed with worker exit0')
 require(worker.get('native_restore_accounting',{}).get('native_field_equivalence_passed')is True and stage.get('accounting')==worker['native_restore_accounting'],'Actual worker/owner agree native field equivalence passed')
 require(worker.get('input_verification')==verification,'Actual worker source verification agrees with published artifact')
 for key in('before_tests_and_build','after_build'):
  row=verification.get(key,{});require(row.get('passed')is True and type(row.get('count'))is int and row['count']>0,'Full before/after native source/input SHA evidence '+key)
 require(verification['after_build']['count']==verification['before_tests_and_build']['count']+1,'Exact extra actual local-MFG receipt pin added after successful tests before build')
 require(fullhex(local_MFG_receipt_SHA256,64)and worker.get('manufactured_test_receipt_SHA256')==local_MFG_receipt_SHA256,'Actual local-MFG receipt is the extra source-verified input')
 require(terminal.get('status')=='streamed_Q_native_restore_computed_published'and terminal.get('source_commit')==source_commit and terminal.get('result_commit')==result_commit and terminal.get('postprocess_accounting')==stage['accounting']and type(terminal.get('finished_utc'))is str and terminal['finished_utc'],'Actual terminal owner success must match exact published native S/R')
 for record in(worker,stage,terminal):require(not any(key in record for key in('error_type','error','failed_phase','failed_stage')),'A post-build/publication failure cannot admit new PDE')
 return True

def make_spec(admission=None):
 if admission is None:
  p=SOURCE/'root-admission.json';require(p.is_file(),'New E13fine decision absent; no input or data work authorized');admission=metadata(p,digest(p))
 a=validate_admission(admission);sources=source_inventory();require(a['source_sha256']==sources and sources.get(str(SOURCE/'streamed_real_q.py'))==OPERATOR_SHA,'Exact canonical E13fine source inventory/operator')
 refs=dict(sources);pubs={};pubmeta={};artifacts={}
 def register(name,path,expected,commit):
  value=metadata(path,expected);require(value.get('status')=='published_readback_verified'and value.get('commit')==commit and fullhex(commit,40),'Actual complete publication '+name);pubs[name]=value;pubmeta[name]=dict(path=str(path),SHA256=expected,commit=commit);refs[str(path)]=expected;return value
 def item(name,path,target,expected=None,parse=False):
  desc=direct(pubs[name],path,target,expected);refs[desc['path']]=desc['SHA256'];artifacts[desc['path']]=desc;return metadata(desc['path'],desc['SHA256'])if parse else desc
 def source_receipt(result_name,source_name,run,prefix,expected_commit=None):
  row=pubs[result_name]['files'][prefix+'source-publication-receipt.json'];require(row.get('readback_passed')is True and fullhex(row.get('SHA256'),64),'Actual source receipt direct proof')
  p=run/'source-publication/result-publication.json';value=metadata(p,row['SHA256']);require(expected_commit is None or value['commit']==expected_commit,'Exact known actual source commit');return register(source_name,p,row['SHA256'],value['commit'])
 def auth(desc,parse=False):
  if 'publication_proof'in desc:
   p=desc['publication_proof'];register('embedded:'+p['path'],Path(p['path']),p['SHA256'],p['commit'])
  names=[name for name,p in pubs.items()if p['commit']==desc['publication_commit']and desc['publication_target']in p['files']]
  require(names,'Original descriptor has authenticated owning publication')
  d=item(names[0],Path(desc['path']),desc['publication_target'],desc['SHA256']);require(d['bytes']==desc['bytes'],'Original descriptor byte identity')
  return metadata(d['path'],d['SHA256'])if parse else d
 for name,args in FIXED_PUBLICATIONS.items():register(name,*args)
 review=a['native_restore_review'];register('native_R',Path(review['publication_path']),review['publication_SHA256'],review['publication_commit']);nprefix='data-native/streamed-Q-native-restore-20261025/'
 nativeS=source_receipt('native_R','native_S',NATIVE,nprefix)
 native_spec=item('native_S',NATIVE/'spec.json',nprefix+'spec.json',parse=True);rctx=native_spec['inputs']
 native_summary=item('native_R',NATIVE/'native-restore-result.json',nprefix+'native-restore-result.json',parse=True);accounting=require_native_PASS(native_summary)
 require(item('native_R',NATIVE/'summary.json',nprefix+'summary.json',parse=True)==native_summary,'Actual native model result and owner summary byte-semantics agree')
 require(native_summary['source_sha256']==rctx['source_sha256'],'Actual native summary and source-published specification share model source map')
 for path,expected in rctx['source_sha256'].items():
  require(Path(path).parent==Path('/dev/shm/task1-streamed-Q-native-restore-20261025/source'),'Canonical original native model source keys')
  item('native_S',Path(path),'tools/streamed_Q_native_restore_20261025/model/'+Path(path).name,expected)
 native_worker=item('native_R',NATIVE/'worker-receipt.json',nprefix+'worker-receipt.json',parse=True);native_stage=item('native_R',NATIVE/'execution-stage.json',nprefix+'execution-stage.json',parse=True);native_verification=item('native_R',NATIVE/'input-SHA-verification.json',nprefix+'input-SHA-verification.json',parse=True)
 native_prereg=item('native_S',NATIVE/'preregistration.json',nprefix+'preregistration.json',parse=True);native_local_MFG_desc=item('native_R',NATIVE/'synthetic-test-receipt.json',nprefix+'synthetic-test-receipt.json');native_local_MFG=metadata(native_local_MFG_desc['path'],native_local_MFG_desc['SHA256'])
 validate_MFG(native_local_MFG,rctx['source_sha256'],native_prereg['expected_model_tests'],native_prereg['expected_owner_tests']);require(native_local_MFG['source_publication_commit']==nativeS['commit']and native_local_MFG['expected_total_tests']==native_prereg['expected_synthetic_tests'],'Actual source-bound native-local MFG counts from published preregistration, not guessed')
 terminal_desc=copy.deepcopy(review['terminal_owner_receipt']);terminal=metadata(terminal_desc['path'],terminal_desc['SHA256']);require(Path(terminal_desc['path']).stat().st_size==terminal_desc['bytes'],'Exact actual root-pinned terminal owner receipt byte count');refs[terminal_desc['path']]=terminal_desc['SHA256']
 validate_native_completion(native_worker,native_stage,native_verification,terminal,summary_SHA256=artifacts[str(NATIVE/'summary.json')]['SHA256'],source_commit=nativeS['commit'],result_commit=pubs['native_R']['commit'],local_MFG_receipt_SHA256=native_local_MFG_desc['SHA256'])
 for name,desc in rctx['publication_metadata'].items():register('native-input:'+name,Path(desc['path']),desc['SHA256'],desc['commit'])
 native_evidence=[]
 for row in native_summary['responses']:
  frequency=row['frequency_Hz'];gate_desc=auth(dict(row['cached_gate_receipt'],publication_target=nprefix+Path(row['cached_gate_receipt']['path']).name,publication_commit=pubs['native_R']['commit']));gates=metadata(gate_desc['path'],gate_desc['SHA256']);validate_cached_gates(gates)
  require(gates['frequency_Hz']==frequency and gates['driven_output']==row['active_output']and gates['native_Q_read']is True and gates['whole_Q_loaded']is False,'Actual carrier/output fresh5/modal/power gate proof')
  opdesc=auth(dict(row['streamed_Q_receipt'],publication_target=nprefix+Path(row['streamed_Q_receipt']['path']).name,publication_commit=pubs['native_R']['commit']));op=metadata(opdesc['path'],opdesc['SHA256'])
  require(op['closed']is True and op['whole_Q_loaded']is False and op['complex_Q_materialized']is False and op['all_loaded_chunks_before_after_verified']is True and op['audit']['loaded_chunk_visits']>0,'Actual closed bounded native Q visits, not a fabricated no-read receipt')
  record=item('native_R',NATIVE/('B0-'+str(frequency)+'-native-field-error.json'),nprefix+'B0-'+str(frequency)+'-native-field-error.json',parse=True);require(record==row,'Exact actual same-grid field-error record')
  native_evidence.append(dict(response=copy.deepcopy(row),fresh_gate_descriptor=gate_desc,fresh_gates=gates,operator_descriptor=opdesc,operator_receipt=op))
 # Native synthetic test PASS is not enough: the previous block required the
 # actual computed field/5-gate native result. Recheck its separate20-MFG chain.
 me=rctx['MFG_evidence'];mp=me['publications'];require(mp['R']['path']==str(MFG/'result-publication/result-publication.json')and mp['S']['path']==str(MFG/'source-publication/result-publication.json'),'Exact actual operator-MFG publication paths, not another fixture run');register('Q_MFG_R',Path(mp['R']['path']),mp['R']['SHA256'],mp['R']['commit']);register('Q_MFG_S',Path(mp['S']['path']),mp['S']['SHA256'],mp['S']['commit'])
 mr=auth(me['receipt_descriptor'],True);validate_mfg(mr,MFG_MODEL_SHA,mp['S']['commit']);require(mr==me['receipt'],'Actual operator20-MFG metadata agrees with native-run input')
 fineS=source_receipt('fine_R','fine_S',FINE,'data-native/P23-fineXY-20261025/','83a61fb55bd42a8ef778a8653c8aa31bbdf647e0')
 fprefix='data-native/P23-fineXY-20261025/';cprefix='data-native/centroid-ellipse-20261025/'
 fine_spec=item('fine_S',FINE/'spec.json',fprefix+'spec.json','ef39c4d106fbb33ce23a58793faf10a35a067f5c7e1eb0506ebf95225d92c4aa',True);old=fine_spec['inputs'];catalog=copy.deepcopy(rctx['catalog'])
 require(fine_spec==rctx['fine_spec']and fine_spec['field_estimator_version']==FIELD_VERSION,'Native PASS and actual fine batch have identical reference specification')
 fine_summary=item('fine_R',FINE/'summary.json',fprefix+'summary.json','fa3239f8a56d2c26558d40bb2afd834adabea3a24d4292ec5632dd7586d4c22f',True)
 fine_B0=next(row for row in fine_summary['candidates']if row['candidate_id']==B0+'-XY102-Z97');require(fine_B0['scalar_archive_kind']=='full_new_fine97'and fine_B0['candidate_adopted']is False,'Actual whole fine B0 alias, not patch/recalculation')
 fine_B0_scalar=item('fine_R',Path(fine_B0['scalar_arrays']['path']),fprefix+Path(fine_B0['scalar_arrays']['path']).relative_to(FINE).as_posix(),fine_B0['scalar_arrays']['SHA256'])
 fine_B0_raw={key:auth(desc)for key,desc in rctx['B0_raw_by_frequency'].items()}
 coarse_summary=item('E13_R',COARSE/'summary.json',cprefix+'summary.json','8fcc2e475699d1c5240158955e8892360862b1a4a43e5e24ec773334a71c1efe',True)
 require(coarse_summary['status']=='single_centroid_area_matched_ellipse_screen_computed_unadopted'and coarse_summary['actual_new_driven_RHS']==2 and coarse_summary['actual_new_angular_metric_evaluations']==1 and coarse_summary['candidate_adopted']is False,'Actual old E13 computed result only')
 csp=item('E13_S',COARSE/'spec.json',cprefix+'spec.json',parse=True);require(csp==coarse_summary['spec']and csp['field_version']==FIELD_VERSION,'Actual coarse E13 source/result specification')
 ectx=csp['inputs'];require(ectx['catalog']==catalog==old['first8catalog'],'Unchanged material/contact/carriers/drives/commonROI/circuit, not a new proxy')
 coarse_E13=next(row for row in coarse_summary['candidates']if row['candidate_id']==E13);require(coarse_E13['control_alias']is False and coarse_E13['candidate_adopted']is False and coarse_E13['scalar_saved_names']==['AM_max2074','carrier_RMS','Jtotal_vector_RMS','AM_direction_index'],'Only four actual stored coarse scalar fields; do not invent other raw scalars')
 geom=coarse_E13['geometry'];require(geom['definition']['semimajor_mm']==13. and geom['definition']['semiminor_mm_formula']=='225/(pi*13)'and geom['definition']['area_mm2_each']==225. and geom['physical_pad_count']==4 and geom['independent_outputs']==2 and geom['body_changed']is False,'Exactly same physical four225mm2 tangent ellipses')
 centres=item('E13_R',COARSE/'actual-P23-centroid-proof.json',cprefix+'actual-P23-centroid-proof.json',parse=True);require(centres==geom['centroid_source']and centres['passed']is True,'Actual authenticated exact rational physical centroid proof')
 exact=[(-5647,-5647),(5647,5647),(5647,-5647),(-5647,5647)]
 require([row['pad']for row in centres['rows']]==[0,1,2,3]and all(row['exact_centroid_mm']==[dict(numerator=x,denominator=450),dict(numerator=y,denominator=450)]for row,(x,y)in zip(centres['rows'],exact)),'Published exact analytic centres, never reconstructed from floats')
 curve_desc=item('E13_R',COARSE/'ellipse-contact-quadrature-receipt.json',cprefix+'ellipse-contact-quadrature-receipt.json');curve=metadata(curve_desc['path'],curve_desc['SHA256']);require(curve==geom['preflight_and_contact']and curve['passed']is True and curve['area_rescaled']is False and curve['unresolved_potential_positive_support_omitted']is False,'Actual coarse positive-support/area certificate; no prune/correction')
 coarse_raw={};coarse_proofs={}
 for f,out in((2000,0),(2010,1)):
  entry=coarse_E13['raw_by_frequency'][str(f)];desc=entry['raw'];coarse_raw[str(f)]=item('E13_R',Path(desc['path']),cprefix+Path(desc['path']).relative_to(COARSE).as_posix(),desc['SHA256'])
  proof=item('E13_R',COARSE/'rhs'/(E13+'-'+str(f)+'-solve-proof.json'),cprefix+'rhs/'+E13+'-'+str(f)+'-solve-proof.json',parse=True);require(proof==entry['proof']and proof['passed']is True and proof['physical_gates']['passed']is True and proof['frequency_Hz']==f and proof['driven_output']==out,'Actual old E13 carrier/modal/source proof')
  coarse_proofs[str(f)]=proof
 sd=coarse_E13['scalar_arrays'];coarse_scalar=item('E13_R',Path(sd['path']),cprefix+Path(sd['path']).relative_to(COARSE).as_posix(),sd['SHA256'])
 first=item('first8_R',FIRST8/'summary.json','data-native/design-screen-coarse-20261025/summary.json','1a05816b0358ecf1f6f31590c90ffb3bc7552c3b60c7a9828b1a999bf5337422',True);coarse_B0=next(row for row in first['candidates']if row['candidate_id']==B0)
 require(coarse_B0==ectx['controls']['B0']['record']==old['coarse_B0_record'],'Actual original coarse101B0 primary caps, unchanged')
 original_grid=auth(ectx['common_grid_ROI']);geometry={'fine':auth(rctx['grid_ROI'])}
 raw_manifest=item('fine_R',FINE/'raw-manifest.json',fprefix+'raw-manifest.json','88d36157b7574ff2337072a572d434a1f6f2c3aeb90a67c2d22c59d95a33b78e',True)
 gd=raw_manifest['geometry']['coarse'];geometry['coarse']=item('fine_R',Path(gd['path']),fprefix+Path(gd['path']).relative_to(FINE).as_posix(),gd['SHA256'])
 bulk_binding=item('fine_R',FINE/'coarse-common97-original93-bulk-binding.json',fprefix+'coarse-common97-original93-bulk-binding.json',parse=True);require(bulk_binding['passed']is True and bulk_binding['XY_row_order_identical']is True and bulk_binding['bulk_z_layer_volume_and_faces_identical']is True,'Actual old physical93bulk same-coordinate binding; runtime E13 arrays still checked')
 ROI_receipts={which:item('fine_R',FINE/(which+'-ROI-receipt.json'),fprefix+which+'-ROI-receipt.json',parse=True)for which in('fine','coarse')}
 faces=auth(rctx['eval_face_receipt']);faces_value=metadata(faces['path'],faces['SHA256']);require(faces_value==rctx['eval_face_receipt_value']==old['eval_face_receipts']['fine']and faces_value['layer_counts']==[4,19,18,56],'Actual shared97depth faces, no geometry regeneration')
 normalized=metadata(NORMALIZED_Q,NORMALIZED_Q_SHA);original=metadata(ORIGINAL_Q_RECEIPT,ORIGINAL_Q_RECEIPT_SHA);refs[str(NORMALIZED_Q)]=NORMALIZED_Q_SHA;refs[str(ORIGINAL_Q_RECEIPT)]=ORIGINAL_Q_RECEIPT_SHA
 graphs={};graph_summaries={};manifests={};remote={};manifest_desc={}
 for name,n,context in(('fine',8184,rctx),('coarse',7860,ectx)):
  graphs[name]=auth(context['graph_arrays']);graph_summaries[name]=auth(context['graph_summary_descriptor'],True);manifest_desc[name]=auth(context['Q_manifest_descriptor']);manifests[name]=metadata(manifest_desc[name]['path'],manifest_desc[name]['SHA256'])
  require(manifests[name]==context['Q_manifest']==graph_summaries[name]['eigen']['cache']and graph_summaries[name]['analytic']['passed']is True,'Actual original graph/Q manifest, no new eigen')
  remote[name]=validate_chunk_receipts(manifests[name],normalized,original,n=n,grid_name='xy102'if name=='fine'else'xy100');require(remote[name]==context['remote_Q_chunk_proofs'],'Actual complete fine/coarse remote proof identity')
  for row in remote[name]:refs[row['path']]=row['SHA256']
 fine_sources={}
 for name in('fine_solver.py','fine_fields.py','frozen_layer_dtn_backend.py','provisional_field.py','frozen_fourier_v1.py','screen_metrics.py','physical_projector.py'):
  matches=[(key,row)for key,row in fineS['files'].items()if key.endswith('/'+name)];require(len(matches)==1,'Unique actual fine source '+name);key,row=matches[0];require(sources.get(str(SOURCE/name))==row['SHA256'],'Byte-exact mathematical source reuse '+name)
  fine_sources[name]=dict(path=str(SOURCE/name),SHA256=row['SHA256'],original_source=item('fine_S',FINE/'source/model'/name,key,row['SHA256']),byte_exact_copy=True)
 # Actual old47 PASS applies only to byte-exact reused components; new E13
 # adapters/curve integration require their own prospective manufactured gate.
 old47root=Path('/dev/shm/task1-P23-fineXY-synthetic-r2-20261025-run');o47prefix='data-native/P23-fineXY-synthetic-r2-20261025/';old47S=source_receipt('old47_R','old47_S',old47root,o47prefix,'b06d9ef597324f8ed2f71c7021701a1a227f9148')
 old47=item('old47_R',old47root/'synthetic-test-receipt.json',o47prefix+'synthetic-test-receipt.json','c3228b9b8a05203f12ab59a40ddf45200f58adc9c5d3390950c116fb37419af4',True)
 require(old47['status']=='passed'and old47['model_tests_run']==47 and old47['owner_tests_run']==6 and old47['tests_run']==53 and old47['tests_failed']==old47['tests_errors']==old47['tests_skipped']==0 and old47['native_RHS']==0 and old47['native_Q_loaded']is False,'Actual historical47+6 synthetic PASS, not native restore substitute')
 old47_components={Path(path).name:sha for path,sha in old47['model_source_sha256'].items()if sources.get(str(SOURCE/Path(path).name))==sha}
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(metadata(ap,digest(ap))==a,'Immutable E13 fine root decision');refs[str(ap)]=digest(ap)
 return dict(schema='task1-E13-fineXY-inputs-v1',root_admission=copy.deepcopy(a),source_sha256=sources,input_sha256=refs,publication_metadata=pubmeta,publication_file_proofs=artifacts,
  native_restore_evidence=dict(accounting=accounting,summary=native_summary,summary_publication=pubmeta['native_R'],source_publication=pubmeta['native_S'],worker=native_worker,execution_stage=native_stage,source_verification=native_verification,local_MFG_receipt=native_local_MFG,local_MFG_receipt_descriptor=native_local_MFG_desc,terminal_owner_receipt=terminal_desc,terminal_owner_receipt_value=terminal,terminal_receipt_requires_readonly_alias_in_new_source_publication=True,responses=native_evidence,root_review_basis=review['decision_basis']),actual_operator_MFG=copy.deepcopy(me),
  catalog=catalog,gamma_by_frequency=copy.deepcopy(catalog['gamma_by_frequency']),z_by_frequency=copy.deepcopy(catalog['z_by_frequency']),material=auth(rctx['material']),contact=auth(rctx['contact']),material_value=copy.deepcopy(rctx['material_value']),contact_value=copy.deepcopy(rctx['contact_value']),
  coarse_raw={'E13':coarse_raw},coarse_proofs={'E13':coarse_proofs},coarse_scalars={'E13':coarse_scalar},coarse_E13_record=copy.deepcopy(coarse_E13),coarse_B0_record=copy.deepcopy(coarse_B0),common_grid_original=original_grid,
  fine_B0_record=copy.deepcopy(fine_B0),fine_B0_raw_by_frequency=fine_B0_raw,fine_B0_scalar=fine_B0_scalar,fine_B0_provenance=dict(source_commit=fineS['commit'],result_commit=pubs['fine_R']['commit'],full_original_metric_raw_scalar_alias=True,new_PDE_or_angular_repeats=0,normalization_role='Secondary fineB0 caps; originalcoarse101B0 primary'),
  E13_physical_definition=copy.deepcopy(geom['definition']),E13_exact_centroid_proof=centres,E13_centroid_proof_value=centres,E13_exact_centroid_rows=copy.deepcopy(centres['rows']),coarse_curve_receipt=curve,coarse_curve_receipt_descriptor=curve_desc,original_minimum_fraction_diagnostics=copy.deepcopy(coarse_E13['fractional_contact_diagnostics']),
  geometry=geometry,ROI_receipts=ROI_receipts,eval_face_receipt=faces,eval_face_receipt_value=faces_value,eval_faces_m=copy.deepcopy(faces_value['z_faces_m']),coarse97_original93_bulk_binding=bulk_binding,
  graph_arrays=graphs,graph_summaries=graph_summaries,Q_manifest=manifests,Q_manifest_descriptor=manifest_desc,cache_manifests=manifests,remote_Q_chunk_proofs=remote,fine_sources=fine_sources,
  old47_evidence=dict(receipt=old47,publication=pubmeta['old47_R'],byte_exact_component_source_SHA256=old47_components,applies_to_modified_new_adapter=False,actual47_tests_repeated=False),
  field_version=FIELD_VERSION,inherited_holds=dict(native=native_summary['inherited_holds'],coarse_E13=coarse_summary['holds'],fine=fine_summary['holds']),old_minimum_fraction_not_pruned=True,geometry_or_material_correction=False,
  new_fine_driven_RHS=2,new_coarse_driven_RHS=0,new_eigen_solves=0,new_fine_full_angular_evaluations=1,new_coarse_SC4_angular_evaluations=1,repeated_original93_bulk_angular_evaluations=0,fine_B0_PDE_or_angular_repeats=0,candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])


def validate_MFG(r,sources,model_count,owner_count):
 require(type(model_count)is int and model_count>0 and type(owner_count)is int and owner_count>0,'Positive prospective source-AST counts')
 require(r.get('status')=='passed'and r.get('model_source_sha256')==sources and r.get('model_source_test_count')==model_count,'Actual successful source-bound local manufactured tests')
 for key,num in dict(model_tests_run=model_count,owner_tests_run=owner_count,tests_run=model_count+owner_count,expected_total_tests=model_count+owner_count,tests_failed=0,tests_errors=0,tests_skipped=0).items():require(type(r.get(key))is int and r[key]==num,'Exact actual successful MFG count '+key)
 require(r.get('native_RHS')==0 and r.get('native_Q_loaded')is False and r.get('native_field_reads')==0 and r.get('field_admission_granted')is False and r.get('scientific_API_spy_calls')==[],'Small controlled fixtures only, no native/cache/field/solve data in local tests')
 return dict(passed=True,model_tests=model_count,owner_tests=owner_count)
