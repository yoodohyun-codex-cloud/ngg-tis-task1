"""Deferred R5 input proof: ONLY the newly published binding-fixed native GUI.

Import performs no reads/server/browser/science. Missing actual native-GUI R
and positive root decision block before browser use. Old known-bad HTML is not
an allowed fallback. Original scientific S/V remain authenticated byte aliases.
"""
import hashlib,json,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-results-gui-browser-r5-20261025/source')
NATIVE=Path('/dev/shm/task1-native-gui-r2-20261025-run')
ORIGINAL=Path('/dev/shm/task1-results-consolidation-20261025-run')
PREFIX='data-native/native-gui-r2-20261025/'
BAD_INDEX_SHA='b16ad8955bc3a17e7c0dc07dbb439eb3df4298562c18f37c9dd14b793dbfeb57'
RENDERER_SHA='72a4c9252f20ed24f4f6d6951a043b5bb533aa0866972d4bfaca112664d75c5e'
S_V={'summary.json':('3abc2508eeb954c469436e972b24112ce3707ad9e3780851424df0d3d2a1d36f',6201176),'views.json':('760ed5da8f41493b723dff22b78f0bd73de488c7ef587afb2fd3a703270ab2b4',20072607)}
ORIGINAL_R='89c8d2c71fd30d1a4b421346f09b48107e1301b2'

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def read(path,expected=None,maximum=8*1024**2):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<maximum,'Canonical bounded native GUI metadata')
 raw=p.read_bytes();require(expected is None or hashlib.sha256(raw).hexdigest()==expected,'Exact native metadata SHA');return json.loads(raw)
def fullhex(value,n):return isinstance(value,str)and re.fullmatch('[0-9a-f]{'+str(n)+'}',value)is not None

def make_spec(admission=None):
 if admission is None:admission=read(SOURCE/'root-admission.json',maximum=1024**2)
 require(admission.get('schema')=='task1-results-gui-browser-root-admission-v1'and admission.get('status')=='selected_finite_browser_validation'and admission.get('root_selected')is True,'Positive root R5 admission AFTER actual nativeGUI-R2 R')
 require(admission.get('native_GUI_run')==str(NATIVE)and admission.get('new_PDE_RHS')==0 and admission.get('new_angular_evaluations')==0 and admission.get('candidate_adopted')is False,'Only new nativeGUI-R2 presentation validation; no scientific recomputation')
 require(isinstance(admission.get('decision_basis'),str)and admission['decision_basis'].strip(),'Actual binding-fix result rationale required')
 commit=admission.get('native_GUI_result_commit');receipt_SHA=admission.get('native_GUI_result_publication_sha256');receipt_path=Path(admission.get('native_GUI_result_publication_path',''))
 require(fullhex(commit,40)and fullhex(receipt_SHA,64)and receipt_path==NATIVE/'result-publication/result-publication.json','Actual nativeGUI-R2 immutable R identity, never prepared/assumed completion')
 pub=read(receipt_path,receipt_SHA);require(pub.get('status')=='published_readback_verified'and pub.get('commit')==commit and pub.get('remote_branch_head_verified')==commit,'Full new nativeGUI-R2 R readback')
 pins={str(receipt_path):receipt_SHA}
 def actual(name,path,expected=None,size=None):
  row=pub['files'][PREFIX+name];require(row.get('readback_passed')is True and fullhex(row.get('SHA256'),64)and type(row.get('bytes'))is int and 0<row['bytes']<80*1024**2,'Direct complete nativeGUI R file proof '+name)
  require(expected is None or row['SHA256']==expected,'Unchanged original alias SHA '+name);require(size is None or row['bytes']==size,'Unchanged original alias size '+name)
  p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and p.stat().st_size==row['bytes']and sha(p)==row['SHA256'],'Actual exact nativeGUI file '+name);pins[str(p)]=row['SHA256']
  return dict(path=str(p),SHA256=row['SHA256'],bytes=row['bytes'],publication_commit=commit,published_target=PREFIX+name,readback_passed=True)
 render_desc=actual('render-receipt.json',NATIVE/'render-receipt.json');render=read(render_desc['path'],render_desc['SHA256'])
 require(render.get('status')=='minimal_JS_binding_rendered_payload_EXACT_browser_unverified'and render.get('renderer_SHA256')==RENDERER_SHA and render.get('original_result_commit')==ORIGINAL_R and render.get('browser_validation_performed')is False and render.get('new_PDE_RHS')==0 and render.get('new_angular_evaluations')==0 and render.get('originals_overwritten')is False,'Actual completed minimal renderer fix with reviewed source, no browser/PDE claim')
 proof=render['payload_identity_proof'];require(all(proof.get(k)is True for k in('EXACT_payload_bytes_equal','EXACT_binding_only_HTML_equal','supplied_summary_views_JSON_semantic_equal','after_write_EXACT_payload_bytes_equal'))and proof['old_index_SHA256']==BAD_INDEX_SHA and proof['renderer_SHA256']==RENDERER_SHA,'All exact original payload/binding-only/write checks from actual render')
 proof_desc=actual('payload-after-write-proof.json',NATIVE/'payload-after-write-proof.json');require(read(proof_desc['path'],proof_desc['SHA256'])==proof,'Original and separately published exact payload proof agree')
 alias_desc=actual('original-summary-views-aliases.json',NATIVE/'original-summary-views-aliases.json');aliases=read(alias_desc['path'],alias_desc['SHA256']);require(set(aliases)==set(S_V),'Exactly original S/V read-only aliases')
 descriptors={'index.html':actual('index.html',NATIVE/'index.html',render['new_index_SHA256'],render['new_index_bytes'])};require(descriptors['index.html']['SHA256']!=BAD_INDEX_SHA and descriptors['index.html']['bytes']==23390867,'NEVER retry old known-bad HTML; six-reference binding-only byte delta')
 for name,(expected,size)in S_V.items():
  alias=aliases[name];require(Path(alias['path'])==ORIGINAL/name and alias['SHA256']==expected and alias['bytes']==size and alias['publication_commit']==ORIGINAL_R and alias.get('originals_overwritten')is False,'Actual original local byte-alias descriptor')
  descriptors[name]=actual(name,alias['path'],expected,size)
 source_desc=actual('source-publication-receipt.json',NATIVE/'source-publication/result-publication.json');source=read(source_desc['path'],source_desc['SHA256']);require(source.get('status')=='published_readback_verified'and fullhex(source.get('commit'),40),'Actual new renderer source publication')
 row=source['files']['tools/native_gui_r2_20261025/consolidated_gui.py'];require(row.get('readback_passed')is True and row.get('SHA256')==RENDERER_SHA and row.get('bytes')==45728,'Reviewed renderer exact source readback')
 summary=read(descriptors['summary.json']['path'],descriptors['summary.json']['SHA256']);require(summary.get('status')=='fifteen_native_geometries_cached_gui_probe_analysis_complete'and summary.get('canonical_native_geometries')==15 and summary.get('new_PDE_RHS')==0 and summary.get('actual_new_angular_evaluations')==0,'Same actual native scientific dataset')
 rows=summary['candidates'];require(len(rows)==15 and len({row['candidate_id']for row in rows})==15 and all(row['probe_prediction']['probe_count']==40 and len(row['probe_prediction']['probes'])==40 for row in rows),'Same15 native geometries and600 actual unloaded probes')
 chain=(('prior-browser-launch-failure-evidence.json','347ddd8cca8accefa5fd4924458648cbaba011834f865de2af753ae0461562e9'),('prior-browser-r2-memory-failure-evidence.json','905d7a5b009309fa4ce196a3901c13c831ef8d83e63f7468d23c7b1b7f98289d'),('prior-browser-r3-memory-failure-evidence.json','ebdbf83889646feb707b12392d583baa55044baf6b3a43d12634147110a07e70'),('r4-JS-failure-evidence.json','323aeb3611bf56863e581e45e776911e3f74a8b254fe021526c73477b921b9ee'))
 for name,expected in chain:
  history=read(SOURCE/name,expected);pins[str(SOURCE/name)]=expected
  for item in history['evidence'].values():
   q=Path(item['path']);require(q.is_absolute()and q==q.resolve()and q.is_file()and not q.is_symlink()and q.stat().st_size==item['bytes']and sha(q)==item['SHA256'],'All prior launch/memory/JS failure originals preserved');pins[str(q)]=item['SHA256']
  for item in history.get('missing_artifacts',[]):require(not Path(item['path']).exists(),'Prior missing receipt state changed; root review required')
 for name in('browser_inputs.py','browser_checks.py','guardian.py','worker.py','loopback_transport.py','resource_scope.py'):pins[str(SOURCE/name)]=sha(SOURCE/name)
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(read(ap)==admission,'Root admission unchanged');pins[str(ap)]=sha(ap)
 return dict(schema='task1-results-gui-browser-spec-v1',root_admission=admission,input_sha256=pins,source_sha256={str(SOURCE/name):pins[str(SOURCE/name)]for name in('browser_inputs.py','browser_checks.py','guardian.py','worker.py','loopback_transport.py','resource_scope.py')},inputs=descriptors,baseline_id=summary['baseline_id'],mandatory_compare_ids=summary['mandatory_compare_ids'],provisional_top5=summary['provisional_top5'],native_ids=[r['candidate_id']for r in rows],reported_local_ids=[r.get('candidate_id',r.get('id'))for r in summary.get('reported_local_candidates',[])],consolidation_result_commit=ORIGINAL_R,native_GUI_recovery_result_commit=commit,native_GUI_renderer_source_commit=source['commit'],renderer_SHA256=RENDERER_SHA,exact_payload_proof=proof,expected_native_geometries=15,expected_unloaded_probes=600,body_dimensions_unchanged=True,new_PDE_RHS=0,new_angular_evaluations=0,Q_loaded=False,candidate_adopted=False,browser_cap_seconds=180)
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
