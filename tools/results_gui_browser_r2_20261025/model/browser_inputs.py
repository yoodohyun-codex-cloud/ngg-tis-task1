"""Deferred metadata authentication for a single published consolidated GUI.

No browser, scientific imports, arrays, native fields or process launch on import.
The sole root owner supplies a positive admission after result/M/T completion.
"""
import hashlib,json,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-results-gui-browser-r2-20261025/source')
INPUT=Path('/dev/shm/task1-results-consolidation-20261025-run')
def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def read(path,expected=None,maximum=80*1024**2):
 p=Path(path);require(p.is_file()and not p.is_symlink()and p==p.resolve()and 0<p.stat().st_size<maximum,'Canonical bounded published input '+str(p))
 if expected is not None:require(sha(p)==expected,'Actual immutable input SHA '+str(p))
 return json.loads(p.read_bytes())
def make_spec(admission=None):
 if admission is None:admission=read(SOURCE/'root-admission.json',maximum=1024**2)
 require(admission.get('schema')=='task1-results-gui-browser-root-admission-v1'and admission.get('status')=='selected_finite_browser_validation'and admission.get('root_selected')is True,'Positive root browser-validation selection required')
 require(admission.get('consolidation_run')==str(INPUT)and admission.get('new_PDE_RHS')==0 and admission.get('new_angular_evaluations')==0 and admission.get('candidate_adopted')is False,'Published consolidated GUI only; no scientific recomputation/adoption')
 commit=admission.get('consolidation_result_commit','');expected=admission.get('consolidation_result_publication_sha256','');publication_path=Path(admission.get('consolidation_result_publication_path',''))
 require(re.fullmatch('[0-9a-f]{40}',commit)is not None and re.fullmatch('[0-9a-f]{64}',expected)is not None and publication_path==INPUT/'result-publication/result-publication.json','Exact actual consolidated result receipt/commit')
 require(isinstance(admission.get('decision_basis'),str)and admission['decision_basis'].strip(),'Explicit root rationale required')
 pub=read(publication_path,expected);require(pub.get('status')=='published_readback_verified'and pub.get('commit')==commit and pub.get('remote_branch_head_verified')==commit,'Complete consolidated R readback required')
 pins={str(publication_path):expected};descriptors={}
 failure_path=SOURCE/'prior-browser-launch-failure-evidence.json';failure=read(failure_path,maximum=2*1024**2)
 require(failure.get('schema')=='task1-prior-browser-launch-failure-evidence-v1'and failure.get('previous_run')=='/dev/shm/task1-results-gui-browser-20261025-run'and failure.get('previous_source_publication_commit')=='9299f993e5e655ee6dcb2710a4bbee17af5f5e76','Exact preserved first browser launch failure')
 pins[str(failure_path)]=sha(failure_path)
 for item in failure['evidence'].values():
  original=Path(item['path']);require(original.is_file()and not original.is_symlink()and original==original.resolve()and original.stat().st_size==item['bytes']and sha(original)==item['SHA256'],'Preserved original failure bytes unchanged '+str(original));pins[str(original)]=item['SHA256']

 for name in('index.html','summary.json','views.json'):
  relative='data-native/results-consolidation-20261025/'+name;require(relative in pub['files'],'Direct actual input publication proof '+name);proof=pub['files'][relative];path=INPUT/name
  require(proof.get('readback_passed')is True and type(proof.get('bytes'))is int and 0<proof['bytes']<80*1024**2 and re.fullmatch('[0-9a-f]{64}',proof.get('SHA256',''))is not None,'Full bounded readback proof '+name)
  require(path.is_file()and not path.is_symlink()and path==path.resolve()and path.stat().st_size==proof['bytes']and sha(path)==proof['SHA256'],'Exact admitted GUI input bytes '+name)
  descriptors[name]=dict(path=str(path),SHA256=proof['SHA256'],bytes=proof['bytes'],publication_commit=commit,published_target=relative,readback_passed=True);pins[str(path)]=proof['SHA256']
 summary=read(descriptors['summary.json']['path'],descriptors['summary.json']['SHA256']);require(summary.get('status')=='fifteen_native_geometries_cached_gui_probe_analysis_complete'and summary.get('canonical_native_geometries')==15 and summary.get('new_PDE_RHS')==0 and summary.get('actual_new_angular_evaluations')==0,'Actual complete cached analysis, not renderer-only acknowledgment')
 rows=summary['candidates'];require(len(rows)==15 and len({row['candidate_id']for row in rows})==15 and all(row['probe_prediction']['probe_count']==40 and len(row['probe_prediction']['probes'])==40 for row in rows),'Fifteen native geometries and six hundred actual unloaded probe predictions')
 source_pins={str(SOURCE/name):sha(SOURCE/name)for name in('browser_inputs.py','browser_checks.py','guardian.py','worker.py')}
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(read(ap,maximum=1024**2)==admission,'Root decision bytes unchanged');pins[str(ap)]=sha(ap)
 return dict(schema='task1-results-gui-browser-spec-v1',root_admission=admission,input_sha256=pins,source_sha256=source_pins,inputs=descriptors,prior_browser_launch_failure_SHA256=sha(failure_path),baseline_id=summary['baseline_id'],mandatory_compare_ids=summary['mandatory_compare_ids'],provisional_top5=summary['provisional_top5'],native_ids=[r['candidate_id']for r in rows],reported_local_ids=[r.get('candidate_id',r.get('id'))for r in summary.get('reported_local_candidates',[])],consolidation_result_commit=commit,expected_native_geometries=15,expected_unloaded_probes=600,body_dimensions_unchanged=True,new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,candidate_adopted=False,browser_cap_seconds=180)
def required_inputs(admission=None):
 spec=make_spec(admission);return dict(spec['input_sha256'])
