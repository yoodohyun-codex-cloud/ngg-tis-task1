"""Deferred exact-publication inventory for one renderer-only GUI recovery.

Import is stdlib/inert. Root alone authenticates metadata and later renders.
No native field, NPZ, Q, PDE, angular computation or browser is used here.
"""
import hashlib,json,re
from pathlib import Path
SOURCE=Path('/dev/shm/task1-native-gui-r2-20261025/source')
ORIGINAL=Path('/dev/shm/task1-results-consolidation-20261025-run')
OLD_RENDERER=Path('/dev/shm/task1-results-consolidation-20261025/source/consolidated_gui.py')
RESULT_COMMIT='89c8d2c71fd30d1a4b421346f09b48107e1301b2'
RESULT_RECEIPT_SHA='965122fda9670950f97fea5cccbe69ed8176b747602884089276276009335fdd'
SOURCE_COMMIT='753b317f48bff8bc584dcfaebc67eac2080fa62d'
SOURCE_RECEIPT_SHA='6acc5c3884d8e7da6d1859134e2b53e0827bf680b2f1cee63f1b978be14f508a'
OLD_RENDERER_SHA='04d7f3986ecff163dc3dafb3323702839038eefcb6c51dad7e70beb24bfa4150'
NEW_RENDERER_SHA='72a4c9252f20ed24f4f6d6951a043b5bb533aa0866972d4bfaca112664d75c5e'
FILES={'index.html':('b16ad8955bc3a17e7c0dc07dbb439eb3df4298562c18f37c9dd14b793dbfeb57',23390831),'summary.json':('3abc2508eeb954c469436e972b24112ce3707ad9e3780851424df0d3d2a1d36f',6201176),'views.json':('760ed5da8f41493b723dff22b78f0bd73de488c7ef587afb2fd3a703270ab2b4',20072607)}
MAX_FILE=80*1024**2

def require(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def regular(path,maximum=MAX_FILE):
 p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_file()and not p.is_symlink()and 0<p.stat().st_size<maximum,'Canonical bounded regular input '+str(p));return p
def read(path,expected=None):
 p=regular(path,8*1024**2);raw=p.read_bytes();require(expected is None or hashlib.sha256(raw).hexdigest()==expected,'Exact metadata SHA before parse');return json.loads(raw)
def actual_file(path,expected,size):
 p=regular(path);require(p.stat().st_size==size and sha(p)==expected,'Exact published file bytes/SHA');return dict(path=str(p),SHA256=expected,bytes=size)
def published(pub,target,expected,size):
 row=pub['files'][target];require(row.get('readback_passed')is True and row.get('SHA256')==expected and row.get('bytes')==size,'Direct original full publication readback '+target)
def make_spec(admission=None):
 if admission is None:admission=read(SOURCE/'root-admission.json')
 require(admission.get('schema')=='task1-native-gui-render-root-admission-v1'and admission.get('status')=='selected_native_GUI_JS_binding_recovery'and admission.get('root_selected')is True,'Positive root renderer-only selection after actual R4 JS failure')
 require(admission.get('new_PDE_RHS')==0 and admission.get('new_angular_evaluations')==0 and admission.get('native_arrays_loaded')is False and admission.get('candidate_adopted')is False,'Renderer-only scope, no scientific work or adoption')
 require(isinstance(admission.get('decision_basis'),str)and admission['decision_basis'].strip(),'Actual presentation-failure rationale required')
 rp=ORIGINAL/'result-publication/result-publication.json';sp=ORIGINAL/'source-publication/result-publication.json';pub=read(rp,RESULT_RECEIPT_SHA);srcpub=read(sp,SOURCE_RECEIPT_SHA)
 require(pub.get('status')=='published_readback_verified'and pub.get('commit')==RESULT_COMMIT and srcpub.get('status')=='published_readback_verified'and srcpub.get('commit')==SOURCE_COMMIT,'Actual original native consolidated S/R, never a browser PASS assumption')
 pins={str(rp):RESULT_RECEIPT_SHA,str(sp):SOURCE_RECEIPT_SHA};descriptors={}
 for name,(expected,size)in FILES.items():
  target='data-native/results-consolidation-20261025/'+name;published(pub,target,expected,size);row=actual_file(ORIGINAL/name,expected,size);row.update(publication_commit=RESULT_COMMIT,publication_target=target,read_only_original_alias=True);descriptors[name]=row;pins[row['path']]=expected
 target='tools/results_consolidation_20261025/model/consolidated_gui.py';published(srcpub,target,OLD_RENDERER_SHA,45692);old=actual_file(OLD_RENDERER,OLD_RENDERER_SHA,45692);pins[old['path']]=old['SHA256']
 new=regular(SOURCE/'consolidated_gui.py');require(sha(new)==NEW_RENDERER_SHA,'Only reviewed new renderer source');pins[str(new)]=NEW_RENDERER_SHA
 delta=read(SOURCE/'renderer-delta.json');require(delta['original_renderer_SHA256']==OLD_RENDERER_SHA and delta['new_renderer_SHA256']==NEW_RENDERER_SHA and delta['binding_and_use_token_replacements']==6,'Exact six-token renderer source delta')
 failure=read(SOURCE/'r4-JS-failure-evidence.json');require(failure.get('actual_error')=="Identifier 'top' has already been declared"and failure.get('browser_PASS')is False and failure.get('previous_source_publication_commit')=='106bad54ec879973fffd03a8ef3cc0f7d13650df'and failure.get('completed_DOM_checks')=={},'Actual R4 early JS failure preserved')
 for item in failure['evidence'].values():
  q=Path(item['path']);require(q.is_absolute()and q==q.resolve()and q.is_file()and not q.is_symlink()and q.stat().st_size==item['bytes']and sha(q)==item['SHA256'],'Exact original R4 failure/scope/log/source-publication evidence');pins[str(q)]=item['SHA256']
  if item['format']=='JSON':require(read(q,item['SHA256'])==item['record'],'Embedded original failure record agrees')
 for name,expected in(('prior-browser-launch-failure-evidence.json','347ddd8cca8accefa5fd4924458648cbaba011834f865de2af753ae0461562e9'),('prior-browser-r2-memory-failure-evidence.json','905d7a5b009309fa4ce196a3901c13c831ef8d83e63f7468d23c7b1b7f98289d'),('prior-browser-r3-memory-failure-evidence.json','ebdbf83889646feb707b12392d583baa55044baf6b3a43d12634147110a07e70')):
  require(sha(regular(SOURCE/name))==expected,'Prior R1/R2/R3 failure chain byte identity');pins[str(SOURCE/name)]=expected
 for q in SOURCE.iterdir():
  if q.is_file()and q.suffix in('.py','.json','.md'):pins[str(q)]=sha(q)
 ap=SOURCE/'root-admission.json'
 if ap.exists():require(read(ap)==admission,'Root decision unchanged')
 return dict(schema='task1-native-gui-render-recovery-spec-v1',root_admission=admission,input_sha256=pins,inputs=descriptors,original_renderer=old,new_renderer=dict(path=str(new),SHA256=NEW_RENDERER_SHA),renderer_delta=delta,original_result_commit=RESULT_COMMIT,original_source_commit=SOURCE_COMMIT,original_R4_error=failure['actual_error'],expected_new_GUI_files=1,summary_and_views_policy='Read-only original byte aliases at new publication prefix; no physical duplicate or original overwrite',payload_identity_required='EXACT old/new embedded payload bytes before and after exclusive render write, plus supplied summary/views exact JSON semantic equality',browser_validation_performed=False,new_PDE_RHS=0,new_angular_evaluations=0,native_arrays_loaded=False,Q_loaded=False,candidate_adopted=False)
def required_inputs(admission=None):return dict(make_spec(admission)['input_sha256'])
