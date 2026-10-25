"""Finite metadata-only local assignment handoff; ROOT alone runs this source.

No NumPy/SciPy, Q/cache/raw-field decode or PDE calls. Only small provenance
JSON, two exact geometry masks and canonical scientific JSON are prepared.
Existing raw inputs are addressed by their earlier full readback identities.
"""
import base64,hashlib,json,os,re,signal,subprocess,sys,threading,time
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
OWNER=Path('/dev/shm/task1-local-handoff-owner-20261025/source')
PAIR=Path('/dev/shm/task1-local-design-pair-20261025/source')
PROTOCOL=Path('/dev/shm/task1-local-proposal-20261025/source')
OUT=Path('/dev/shm/task1-local-handoff-20261025-run')
PUB=Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
OLD_MANIFEST=Path('/dev/shm/task1-contact-graded-kernel-20261025-run/auto-transfer/contact-graded-kernel-20261025-transfer-manifest.json')
OLD_MANIFEST_SHA='0f2e7e7b80845e28747b8e329b40a0d7b3cb3a629fc7cd2fcd58ae1adc9d4895'
FIRST8=Path('/dev/shm/task1-design-screen-coarse-20261025-run')
FIRST8_RESULT_COMMIT='4d6207caa60ae16ab7a7e997022ac72653b97ec3'
FIRST8_RESULT_RECEIPT_SHA='d20f3fd6157436c7bcbe626c056377aa5fbc83e4c05fa92acdb1108f86539159'
ORIGINAL_INPUTS=Path('/dev/shm/task1-vs19-uniform-2000-20261025-run')
REPOSITORY='yoodohyun-codex-cloud/ngg-tis-task1'
BRANCH='codex/task1-cloud-restart-20261020'
REGISTRY='docs/TASK1_LOCAL_HANDOFF_20261025/candidate-ownership.json'
DOCS='docs/TASK1_LOCAL_HANDOFF_20261025/'
REMOTE='data-native/local-handoff-20261025/'
PAIR_REMOTE='tools/local_design_pair_20261025/'
OWNER_REMOTE='tools/local_handoff_owner_20261025/'
CAP=900;PUB_CAP=330;MAX_FILE=80*1024**2
sys.path[:0]=[str(ROOT/'tools'),str(PAIR),str(OWNER)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as budget
from frozen_manifest_validation import safe_path,validate_manifest

def req(ok,message):
 if not ok:raise ValueError(message)
def read(path):return json.loads(Path(path).read_text())
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
 return h.hexdigest()
def encoded(value):return(json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
def hash_json(value):return hashlib.sha256(encoded(value)).hexdigest()
def new(path,value):
 with Path(path).open('xb')as stream:stream.write(encoded(value))
def text(path,value):
 with Path(path).open('x',encoding='utf-8')as stream:stream.write(value)
def identity(path):
 p=Path(path);req(p.is_file()and not p.is_symlink(),'Canonical immutable metadata/source '+str(p));s=p.stat()
 return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def size(path):
 try:return path.stat().st_size if path.is_file()else sum(p.stat().st_size for p in path.rglob('*')if p.is_file())
 except FileNotFoundError:return 0
def check_public(value):
 if isinstance(value,str):req('/dev/shm/'not in value and'/workspace/'not in value and not re.search(r'(?<![A-Za-z0-9])[A-Za-z]:[\\/]',value),'Internal/private path in public handoff metadata')
 elif isinstance(value,dict):
  for key,item in value.items():check_public(key);check_public(item)
 elif isinstance(value,list):
  for item in value:check_public(item)
def file_entry(commit,path,bytes_,digest):
 safe_path(path);req(re.fullmatch('[0-9a-f]{40}',commit)is not None and re.fullmatch('[0-9a-f]{64}',digest)is not None,'Full immutable transfer identity')
 suffix=next((suffix for suffix in('.csv.gz','.bin.gz','.tar.gz')if path.endswith(suffix)),Path(path).suffix)
 if suffix not in('', '.json','.py','.md','.txt','.log','.csv','.npz','.f64le','.ps1','.html','.artifact'):suffix='.artifact'
 return dict(fixed_commit=commit,repo_relative_path=path,bytes=bytes_,SHA256=digest,safe_destination_relative_path='objects/'+digest+suffix)
def geometry_key(pads,transform=0):
 """D4 aliases preserve frequency/output labels; common GND pieces may reorder."""
 result=[]
 for p in pads:
  x,y=(float(v)for v in p['center_mm']);w=float(p['width_mm']);h=float(p['height_mm']);rotation=int(p.get('rotation_deg',0))
  req(rotation==0,'This finite handoff only contains axis-aligned rectangles')
  if transform>=4:x=-x
  for _ in range(transform%4):x,y=-y,x;w,h=h,w
  result.append((p['node'],round(x,9),round(y,9),round(w,9),round(h,9)))
 return tuple(sorted(result))
def ensure_no_duplicate(candidate,past):
 key=geometry_key(candidate['pads'])
 return [old['candidate_id']for old in past if any(key==geometry_key(old['pads'],t)for t in range(8))]

def main():
 head=os.environ.get('TASK1_HANDOFF_EXPECTED_PARENT','')
 req(re.fullmatch('[0-9a-f]{40}',head)is not None,'Set TASK1_HANDOFF_EXPECTED_PARENT to actual branch40hex parent')
 with b.dual_lock(ROOT/'.task1-queue-owner.lock'):
  req(not OUT.exists(),'Unique handoff run required; preserve all earlier attempts');OUT.mkdir()
  for name in('logs','source','source-publication','result-publication','prepared','input-layout','public'):(OUT/name).mkdir()
  limits=ep.resolve_limits();configured=ep.configure_process(limits);ledger=budget.load_ledger()
  req(ledger.get('cumulative_time_unlimited')is True,'Actual unlimited cumulative-time approval required');budget.require_time_budget(ledger,CAP)
  pid=os.getpid();ticks=b.ticks(pid);started=time.monotonic();owned={pid:ticks};stop=threading.Event();mutex=threading.RLock()
  state=dict(phase='preparing_metadata_only',peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);counter=0;git_wall=0.
  directories={'pair':PAIR,'protocol':PROTOCOL,'owner':OWNER}
  sources={str(p):sha(p)for directory in directories.values()for p in directory.rglob('*')if p.is_file()and p.suffix in('.py','.json','.md')}
  helpers={str(ROOT/'tools'/name):sha(ROOT/'tools'/name)for name in('task1_bounded_continuation.py','task1_execution_policy.py','task1_resource_policy.py')}
  reg=dict(schema='task1-finite-native-continuation-registration-v1',supervisor_pid=pid,proc_start_ticks=ticks,controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),publisher_path=str(PUB),publisher_sha256=sha(PUB),source_sha256=sources,helper_sha256=helpers,outer_deadline_seconds=CAP,resource_limits=limits,execution_policy_refs=ep.execution_policy_refs(),configured=configured,new_PDE_RHS=0,raw_array_bytes_read=False)
  new(OUT/'registration.json',reg)
  receipt=dict(schema='task1-local-pair-metadata-handoff-owner-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,new_PDE_RHS=0,raw_array_bytes_read=False,local_execution_started=False,Windows_saved_verified=False,OneDrive_sync_verified=False)
  pins={};stats={}
  def bind(refs):
   for path,expected in refs.items():
    ident=identity(path);req(ident[2]<8*1024**2,'Metadata/source-only handoff must never bind/hash raw arrays')
    req(sha(path)==expected,'Metadata/source SHA mismatch '+path)
    with mutex:pins[path]=expected;stats[path]=ident
  bind({**sources,**helpers,**reg['execution_policy_refs'],str(PUB):reg['publisher_sha256'],str(OUT/'registration.json'):sha(OUT/'registration.json')})
  def checkpoint(phase,**extra):
   nonlocal counter
   with mutex:
    counter+=1;row=dict(schema='task1-local-handoff-live-v1',updated_utc=b.now(),queue_pid=pid,queue_start_ticks=ticks,phase=phase,elapsed_seconds=time.monotonic()-started,**extra)
    new(OUT/('checkpoint-'+str(counter).zfill(5)+'.json'),row)
    for target in(OUT/'current.json',ROOT/'runtime/task1-local-handoff-live-20261025.json'):
     temporary=target.with_name(target.name+'.'+str(pid)+'.'+str(counter)+'.tmp');new(temporary,row);os.replace(temporary,target)
    state['phase']=phase
  def guard():
   with mutex:live=b.owned_descendants(pid,ticks,dict(owned));owned.update(live);nowpins=dict(pins);nowstats=dict(stats)
   rss=sum(b.rss(p)for p,t in live.items()if b.live(p,t));tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'))
   with mutex:state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp))
   req(rss+tmp<=limits['total_memory_bytes'],'Actual aggregate ownedRSS+ALLtask1tmpfs cap');req(time.monotonic()-started<CAP,'Finite900s handoff watchdog');req(not(OUT/'STOP').exists(),'Explicit STOP marker')
   for path,expected in nowpins.items():req(identity(path)==nowstats[path]and sha(path)==expected,'Frozen source/metadata changed '+path)
  def interrupt(signum,frame):raise InterruptedError(state.get('error','Finite handoff timeout or external signal'))
  def monitor():
   last=0.
   while not stop.wait(.25):
    try:
     guard()
     if time.monotonic()-last>=5:checkpoint(state['phase'],observed_peak_RSS=state['peak_RSS'],observed_peak_owned_tmpfs=state['peak_owned_tmpfs']);last=time.monotonic()
    except BaseException as error:state['error']=str(error);os.kill(pid,signal.SIGTERM);return
  handlers={sig:signal.getsignal(sig)for sig in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
  for sig in handlers:signal.signal(sig,interrupt)
  signal.setitimer(signal.ITIMER_REAL,CAP);thread=threading.Thread(target=monitor,daemon=True);thread.start()
  def command(argv,label,seconds,is_git=False,capture=False):
   nonlocal git_wall
   guard();checkpoint(label);path=OUT/'logs'/(str(counter)+'-'+label+'.log');before=time.monotonic();rows_before=len(budget.load_ledger()['runs'])
   with path.open('xb')as log:
    child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    with mutex:owned[child.pid]=b.ticks(child.pid)
    checkpoint(label,child_pid=child.pid,child_start_ticks=owned[child.pid],child_timeout_seconds=seconds)
    try:code=child.wait(timeout=max(.01,min(seconds,CAP-(time.monotonic()-started))))
    finally:
     if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
     if is_git:
      run=Path(argv[argv.index('--output')+1]).name
      recorded=sum(row.get('seconds',0.)for row in budget.load_ledger()['runs'][rows_before:]if row.get('run_id')==run)
      git_wall+=min(time.monotonic()-before,recorded)
   req(code==0,'Bounded child failed '+label+'; preserve '+str(path))
   if capture:req(path.stat().st_size<8*1024**2,'Bounded public Git metadata');return read(path)
  def plan(files,parent,message,result,comment=None):
   for target,path in files.items():safe_path(target);req(path.is_file()and not path.is_symlink()and path.stat().st_size<MAX_FILE,'Metadata publication bound')
   return dict(schema='task1-supported-Git-transport-plan-v1',repository=REPOSITORY,branch=BRANCH,expected_parent=parent,message=message,files={target:dict(local_path=str(path),SHA256=sha(path),bytes=path.stat().st_size)for target,path in files.items()},required_result_receipt=str(result),required_receipt_status='published_readback_verified',new_PDE_required=False,comment_body=comment)
  try:
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    # Read Git metadata at exactly the intended parent; never a mutable branch.
    commit_metadata=command(['gh','api','repos/'+REPOSITORY+'/git/commits/'+head],'read-fixed-parent-commit',45,capture=True)
    req(commit_metadata.get('sha')==head and re.fullmatch('[0-9a-f]{40}',commit_metadata['tree']['sha'])is not None,'Exact fixed-parent commit and tree identity required')
    tree_sha=commit_metadata['tree']['sha']
    tree=command(['gh','api','repos/'+REPOSITORY+'/git/trees/'+tree_sha+'?recursive=1'],'read-central-registry-tree',45,capture=True)
    req(tree.get('truncated')is False and tree.get('sha')==tree_sha,'Complete fixed-parent public Git tree required')
    previous_rows=[row for row in tree['tree']if row['path']==REGISTRY];req(len(previous_rows)<=1,'Unique central registry path')
    previous=None
    if previous_rows:
     record=previous_rows[0];req(record['type']=='blob','Central registry must be an ordinary Git blob')
     blob=command(['gh','api','repos/'+REPOSITORY+'/git/blobs/'+record['sha']],'read-central-registry-blob',45,capture=True)
     req(blob.get('encoding')=='base64','Git blob metadata base64 ABI');raw=base64.b64decode(blob['content']);req(len(raw)==blob['size']<2*1024**2,'Bounded previous central registry')
     previous=json.loads(raw);new(OUT/'previous-central-registry.json',previous)
    import portable_pair as pair
    inventory=pair.manifest();catalog=pair.catalog();req(len(inventory['files'])==26 and len(catalog['candidates'])==2,'Exactly26logical inputs and2conditional candidates')
    req(sha(OLD_MANIFEST)==OLD_MANIFEST_SHA,'Original full transfer metadata identity');old=read(OLD_MANIFEST);validate_manifest(old)
    oldrows=old['files']+old.get('logical_file_aliases',[]);oldkeys={(r['fixed_commit'],r['repo_relative_path'],r['bytes'],r['SHA256'])for r in oldrows}
    sourceproof=read(FIRST8/'source-publication/result-publication.json');req(sourceproof['status']=='published_readback_verified'and sourceproof['commit']==inventory['first8_source_commit'],'Actual first8 source readback required')
    proofs=[]
    for row in inventory['files']:
     safe_path(row['local_relative_path']);safe_path(row['repository_relative_path'])
     if row['fixed_commit']is None:
      req(row['logical_artifact']=='portable_native_ROI'and row['repository_relative_path']==PAIR_REMOTE+'portable_native_roi.py'and sha(PAIR/'portable_native_roi.py')==row['SHA256'],'Only new portableROI may await Scommit')
      proofs.append(dict(logical_artifact=row['logical_artifact'],identity_source='new_verified_source_publication_pending'))
     elif row['fixed_commit']==sourceproof['commit']:
      proof=sourceproof['files'][row['repository_relative_path']];req(proof['readback_passed']is True and proof['SHA256']==row['SHA256']and proof['bytes']==row['bytes'],'Existing scientific source readback identity')
      proofs.append(dict(logical_artifact=row['logical_artifact'],identity_source='actual_first8_source_readback'))
     else:
      req((row['fixed_commit'],row['repository_relative_path'],row['bytes'],row['SHA256'])in oldkeys,'Existing original input full-readback manifest identity')
      proofs.append(dict(logical_artifact=row['logical_artifact'],identity_source='previous_full_readback_transfer_manifest'))
    new(OUT/'existing-input-proof.json',dict(metadata_only=True,raw_array_bytes_read=False,logical_inputs=proofs))
    for logical,name in(('material_receipt','material-input.json'),('contact_receipt','contact-receipt.json')):
     row=next(r for r in inventory['files']if r['logical_artifact']==logical);source=ORIGINAL_INPUTS/name
     req(source.stat().st_size==row['bytes']and row['bytes']<30000 and sha(source)==row['SHA256'],'Exact small original material/contact bytes')
     target=OUT/'input-layout'/row['local_relative_path'];target.parent.mkdir(parents=True,exist_ok=True)
     with target.open('xb')as stream:stream.write(source.read_bytes())
     req(sha(target)==row['SHA256'],'Small input-layout readback')
    prepared=pair.prepare_spec(OUT/'input-layout',OUT/'prepared')
    req(prepared['execution_permitted']is False and prepared['lease']is None and prepared['maximum_new_driven_RHS']==4,'Preparation must not authorize local execution')
    frozen={};sourcefiles={}
    for namespace,directory in directories.items():
     destination=OUT/'source'/namespace;destination.mkdir()
     for source in directory.rglob('*'):
      if source.is_file()and source.suffix in('.py','.json','.md'):
       relative=source.relative_to(directory);target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
       with target.open('xb')as stream:stream.write(source.read_bytes())
       req(sha(target)==sources[str(source)],'Complete frozen source identity');frozen[str(target)]=sha(target)
       prefix=PAIR_REMOTE if namespace=='pair'else PAIR_REMOTE+'protocol/'if namespace=='protocol'else OWNER_REMOTE
       sourcefiles[prefix+relative.as_posix()]=target
    result_receipt=FIRST8/'result-publication/result-publication.json'
    req(sha(result_receipt)==FIRST8_RESULT_RECEIPT_SHA,'Pinned actual first8 result-publication receipt')
    cloud_publication=read(result_receipt)
    req(cloud_publication['status']=='published_readback_verified'and cloud_publication['commit']==FIRST8_RESULT_COMMIT and cloud_publication['remote_branch_head_verified']==FIRST8_RESULT_COMMIT,'Actual first8 result full-readback status/commit required')
    summary_proof=cloud_publication['files']['data-native/design-screen-coarse-20261025/summary.json']
    req(summary_proof['readback_passed']is True and summary_proof['SHA256']==sha(FIRST8/'summary.json')and summary_proof['bytes']==(FIRST8/'summary.json').stat().st_size,'Actual cloud8 summary byte-for-byte immutable result readback')
    cloud=read(FIRST8/'summary.json');req(cloud['completed_candidates']==8,'Actual cloud8 metadata required without native arrays')
    past=[]
    for oldcase in cloud['spec']['catalog']['candidates']:
     pads=[dict(node=p['node'],center_mm=p['center_mm'],width_mm=p['width_mm'],height_mm=p['height_mm'],rotation_deg=p.get('rotation_deg',0))for p in oldcase['pads']]
     past.append(dict(candidate_id=oldcase['candidate_id'],pads=pads))
    duplicate_proof=[]
    for candidate in catalog['candidates']:
     aliases=ensure_no_duplicate(candidate,past);req(not aliases,'Local candidate aliases an actual cloud8 assignment')
     duplicate_proof.append(dict(candidate_id=candidate['candidate_id'],cloud_candidates_checked=[c['candidate_id']for c in past],D4_node_preserving_aliases=aliases))
    req(not ensure_no_duplicate(catalog['candidates'][0],[catalog['candidates'][1]]),'The local pair must not be aliases of each other')
    oldentries=[]
    if previous is not None:
     oldentries=previous.get('candidates',previous.get('candidate_entries',[]));req(isinstance(oldentries,list),'Known previous registry entries required')
     for case in prepared['candidates']:
      for oldcase in oldentries:
       req(oldcase.get('candidate_id')!=case['candidate_id']and oldcase.get('run_id')!=case['run_id']and oldcase.get('canonical_config_SHA256')!=case['canonical_config_SHA256'],'Existing central candidate/run/hash collision: preserve and review; never overwrite ownership')
     for candidate in catalog['candidates']:
      for oldcase in oldentries:
       oldpads=oldcase.get('pads')
       req(isinstance(oldpads,list)and oldpads,'Prior central ownership entry lacks inspectable physical-node geometry; preserve and review')
       req(not ensure_no_duplicate(candidate,[dict(candidate_id=oldcase['candidate_id'],pads=oldpads)]),'Existing central physical-node/symmetry alias collision; preserve and review')
    publiccases=[];generatedfiles={};components={}
    for case in prepared['candidates']:
     config=Path(case['canonical_config_path']);mask=Path(case['mask_path']);canonical=read(config)
     req(sha(config)==case['canonical_config_SHA256']and sha(mask)==case['mask_sha256'],'Actual generated canonical configuration and mask SHA');check_public(canonical)
     config_repo=REMOTE+'prepared/'+config.name;mask_repo=REMOTE+'prepared/masks/'+mask.name
     generatedfiles[config_repo]=config;generatedfiles[mask_repo]=mask
     domains=dict(model=dict(adapter=canonical['portable_adapter_SHA256'],scientific_sources=canonical['scientific_source_SHA256'],portable_ROI=canonical['portable_ROI_SHA256'],field=canonical['field_version'],metric=canonical['metric_version']),material=dict(receipt=canonical['material_SHA256'],gamma=canonical['gamma_by_frequency']),contact=dict(receipt=canonical['contact_SHA256'],zA=canonical['z_by_frequency']),geometry=dict(body=canonical['geometry_fixed'],pads=canonical['pads'],mask_SHA256=case['mask_sha256']),circuit=canonical['circuit'],frequency=dict(frequencies_Hz=canonical['frequencies_Hz'],drives=canonical['circuit']['drives']),grid=dict(recipe=canonical['grid'],input_manifest_SHA256=canonical['input_manifest_SHA256'],coarse_realQ_identity=inventory['cache']),reconstruction=dict(field=canonical['field_version'],metric=canonical['metric_version'],modulation=canonical['modulation_definition'],ROI=canonical['ROI']))
     component_hashes={name:hash_json(value)for name,value in domains.items()};components[case['candidate_id']]=dict(canonical_config_SHA256=case['canonical_config_SHA256'],component_SHA256=component_hashes,component_payloads=domains)
     publiccases.append(dict(candidate_id=case['candidate_id'],run_id=case['run_id'],assigned_environment='local_windows_01',assignment_status='assigned_waiting_adapter_and_lease',canonical_config_SHA256=case['canonical_config_SHA256'],component_SHA256=component_hashes,canonical_config_repo_relative_path=config_repo,mask_repo_relative_path=mask_repo,mask_SHA256=case['mask_sha256'],pads=case['pads'],maximum_new_driven_RHS=2,execution_permitted=False,lease=None,actual_owner_PID=None,actual_owner_CreationTime_UTC=None))
    sanitized=dict(schema='task1-portable-local-pair-public-spec-v1',candidates=publiccases,gamma_by_frequency=prepared['gamma_by_frequency'],z_by_frequency=prepared['z_by_frequency'],grid=prepared['grid'],frequencies_Hz=prepared['frequencies_Hz'],maximum_new_driven_RHS=4,execution_permitted=False,lease=None,Windows_owner_adapter_validated=False,baseline_physics_reused=False,first8_source_commit=prepared['first8_source_commit'],input_manifest_repo_relative_path=PAIR_REMOTE+'input-manifest.json',raw_array_bytes_read_by_handoff_owner=False)
    check_public(sanitized);new(OUT/'public/local-pair-spec.json',sanitized);new(OUT/'public/component-hashes.json',components);new(OUT/'public/duplicate-check.json',dict(fixed_parent=head,existing_central_registry_present=previous is not None,checks=duplicate_proof,current_cloud8_preserved=True))
    sourcefiles.update(generatedfiles)
    for name in('local-pair-spec.json','component-hashes.json','duplicate-check.json'):sourcefiles[REMOTE+name]=OUT/'public'/name
    prereg=dict(schema='task1-local-pair-handoff-public-preregistration-v1',new_PDE_RHS=0,raw_array_bytes_read=False,local_execution_started=False,CPU_cap=limits['cpu_limit'],cloud_total_RSS_plus_all_tmpfs_cap_bytes=limits['total_memory_bytes'],finite_owner_timeout_seconds=CAP,source_SHA256={target:sha(path)for target,path in sourcefiles.items()},prepared_candidates=publiccases,local_CPU_physical_cap=8,local_total_Job_memory_cap_bytes=4000000000,Windows_saved_verified=False)
    check_public(prereg);new(OUT/'public/preregistration.json',prereg);sourcefiles[REMOTE+'preregistration.json']=OUT/'public/preregistration.json'
    # These are all small metadata/source artifacts. Q/NPZ locations in
    # prepared['input_pins'] are intentionally NOT dereferenced, copied or bound.
    refs={**frozen,**{str(p):sha(p)for p in sourcefiles.values()},str(OLD_MANIFEST):OLD_MANIFEST_SHA,str(FIRST8/'source-publication/result-publication.json'):sha(FIRST8/'source-publication/result-publication.json'),str(FIRST8/'summary.json'):sha(FIRST8/'summary.json'),str(result_receipt):FIRST8_RESULT_RECEIPT_SHA,str(OUT/'prepared/local-pair-spec.json'):sha(OUT/'prepared/local-pair-spec.json')}
    for name in('material-input.json','contact-receipt.json'):
     refs[str(ORIGINAL_INPUTS/name)]=sha(ORIGINAL_INPUTS/name)
     refs[str(OUT/'input-layout/inputs'/name)]=sha(ORIGINAL_INPUTS/name)
    bind(refs)
   sourceplan=OUT/'source-plan.json';new(sourceplan,plan(sourcefiles,head,'Fix two disjoint local TIS assignments, portable sources and exact scientific configurations',OUT/'source-publication/result-publication.json'))
   command([sys.executable,'-B',str(PUB),'--plan',str(sourceplan),'--output','/dev/shm/task1-git-local-handoff-source-20261025','--queue-registration',str(OUT/'registration.json')],'source-publication',PUB_CAP,True)
   published=read(OUT/'source-publication/result-publication.json');req(published['status']=='published_readback_verified','Actual complete local source readback required');S=published['commit']
   with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
    guard();layout=[];all_entries=[]
    for row in inventory['files']:
     commit=row['fixed_commit']or S;entry=file_entry(commit,row['repository_relative_path'],row['bytes'],row['SHA256']);all_entries.append(entry)
     layout.append(dict(logical_artifact=row['logical_artifact'],safe_download_object_relative_path=entry['safe_destination_relative_path'],desired_layout_relative_path=row['local_relative_path'],SHA256=row['SHA256'],bytes=row['bytes'],fixed_commit=commit,repo_relative_path=row['repository_relative_path']))
    for target,proof in published['files'].items():
     req(proof['readback_passed']is True,'Every new source/config byte read back');entry=file_entry(S,target,proof['bytes'],proof['SHA256']);all_entries.append(entry)
     if target.startswith(PAIR_REMOTE):destination=target[len(PAIR_REMOTE):]
     elif target.startswith(REMOTE+'prepared/'):destination='prepared/'+target[len(REMOTE+'prepared/'):]
     elif target.startswith(OWNER_REMOTE):destination='_cloud_handoff_owner/'+target[len(OWNER_REMOTE):]
     else:destination='_handoff_metadata/'+Path(target).name
     safe_path(destination);layout.append(dict(logical_artifact='new-source:'+target,safe_download_object_relative_path=entry['safe_destination_relative_path'],desired_layout_relative_path=destination,SHA256=proof['SHA256'],bytes=proof['bytes'],fixed_commit=S,repo_relative_path=target))
    # Several source rows intentionally alias identical first8 scientific bytes.
    unique={};aliases=[]
    for entry in all_entries:
     key=entry['safe_destination_relative_path']
     if key in unique:
      req((unique[key]['SHA256'],unique[key]['bytes'])==(entry['SHA256'],entry['bytes']),'Conflicting content addressed identity')
      if entry!=unique[key]:aliases.append(entry)
     else:unique[key]=entry
    manifest=dict(schema='task1-safe-windows-transfer-manifest-v1',status='two_local_assignments_source_inputs_prepared_Windows_receive_unverified',created_UTC=b.now(),repository=REPOSITORY,public_reference_commit=S,Windows_backup_complete=False,OneDrive_sync_verified=False,scope='Two conditionally assigned local designs; unchanged first8 numerical kernel, coarse realQ graph/cache, original per-frequency material/contact and exact prepared configurations. No local PDE or active lease.',files=sorted(unique.values(),key=lambda r:r['safe_destination_relative_path']),logical_file_aliases=aliases,durability_gaps=[],required_local_only_raw_arrays=[],layout_mapping_repo_relative_path=DOCS+'layout-mapping.json',new_PDE_RHS=0,raw_array_bytes_read_by_handoff_owner=False,automatic_extract_or_execute=False)
    result=validate_manifest(manifest);new(OUT/'public/transfer-manifest.json',manifest)
    mapping=dict(schema='task1-safe-transfer-layout-mapping-v1',source_fixed_commit=S,repository=REPOSITORY,download_policy='Use the standard contentaddressed receiver with this manifest; independently verify all bytes. Layout is a separate explicitly reviewed copy step. No automatic extraction, execution, overwriting, install or owner start.',local_root_private_and_not_published=True,files=layout,prepared_path_note='The published prepared spec is sanitized. The validated Windows owner regenerates absolute deployment paths using portable_pair.prepare_spec(local_root, unique_local_preparation_dir) and checks the frozen canonical/mask hashes. Do not call the Linux eight-case build or worker.',Windows_backup_complete=False)
    check_public(mapping);new(OUT/'public/layout-mapping.json',mapping)
    assignments=read(PROTOCOL/'conditional_assignments_v2.json');local_readiness=assignments['local_readiness']
    local_readiness.update(Windows_owner_basic_selftests_user_reported_passed=True,Windows_owner_basic_selftests_scope=['PID and CreationTime identity','Python and Java compatible local locks','stale-token rejection','controller-death child kill and restart'],Windows_owner_engine_integration_verified=False,local_design_execution_started=False)
    registry=dict(schema='task1-central-local-cloud-candidate-ownership-v1',updated_UTC=b.now(),status='two_conditional_assignments_no_active_local_lease_or_execution',registry_repository_relative_path=REGISTRY,source_fixed_commit=S,source_bundle_repo_relative_path=PAIR_REMOTE,source_adapter_SHA256=sha(PAIR/'portable_pair.py'),input_manifest_SHA256=sha(PAIR/'input-manifest.json'),canonical_hash_recipe='SHA256 of UTF8 JSON with sort_keys=true, ensure_ascii=false, allow_nan=false, indent2 and one final newline; portable_pair.encoded',component_hash_recipe='Same JSON canonicalization, over payload domains in component-hashes.json',candidates=oldentries+publiccases,previous_unrelated_entries_preserved=len(oldentries),new_conditional_candidate_count=2,local_readiness=local_readiness,local_limits=dict(max_physical_CPU_cores=8,logical_affinity=[0,2,4,6,8,10,12,13],aggregate_Windows_Job_memory_bytes=4000000000,aggregate_Windows_Job_memory_GiB=4000000000/1024**3,actual_8core_acceleration_verified=False,actual_PDE_executed=False),cloud_limits_unchanged=dict(CPU=4,total_RSS_plus_all_owned_tmpfs_bytes=8000000000,maximum_evaluation_cells=800000,single_cloud_owner=True),prerequisites_before_execution=['Validate and freeze the separate Windows owner/CreationTime/local-lock adapter and its meaningful scientific contracts','Recheck actual available RAM and commit headroom immediately before starting within the fixed4e9 Job cap','Read latest central registry and acquire exact expected-parent nonforce CAS lease with unique run/config/source and actual PID/CreationTime/Job identity','Verify the remote lease bytes and preserve current heartbeat/checkpoints; TTL expiry alone is not process-death proof','Verify every source/input and canonical/mask identity before and after each finite case; original Linux parent/lock guards remain unchanged'],lease_protocol=dict(exclusive_scope='Per canonical scientific candidate and verified symmetry aliases; disjoint local/cloud work may run concurrently',cloud_owner='Unchanged existing Linux owner/dual locks',local_owner='One verified Windows Job owner/local lock',TTL_is_process_death_proof=False,canonical_registry_path_overrides_historical_runtime_template=True),transfer_manifest_repo_relative_path=DOCS+'transfer-manifest.json',layout_mapping_repo_relative_path=DOCS+'layout-mapping.json',source_publication_commit=S,source_publication_readback_verified=True,new_PDE_RHS=0,local_execution_started=False,Windows_backup_complete=False,OneDrive_sync_verified=False)
    check_public(registry);new(OUT/'public/candidate-ownership.json',registry)
    lines=['# Two local TIS assignments — Windows execution remains conditional','',f'Fixed source commit: `{S}`. The cloud calculation owner and its CPU4/8,000,000,000-byte limits remain unchanged.','', '| Candidate | Run ID | Canonical configuration SHA256 |','|---|---|---|']
    for case in publiccases:lines.append('| '+case['candidate_id']+' | '+case['run_id']+' | '+case['canonical_config_SHA256']+' |')
    lines+=['','Both cases use D50mm/layers0.1/5/5/15mm, four top pads/two independent outputs/common return, one50ohm per output,1Vpp high-Z sine drives at2000/2010Hz. Each case requires exactly two NEW driven RHS. This handoff solved no PDE and read no Q/NPZ/raw-field bytes.','', 'Status: `assigned_waiting_adapter_and_lease`; lease/PID/CreationTime remain null and execution is false. The separate Windows owner/Job/local-lock adapter, fresh RAM/commit check and a remotely read-back central CAS lease are required before any local study starts. Runtime/Job tests are not PDE or8-core speedup validation.','', 'Use `transfer-manifest.json` with the existing safe receiver; it downloads SHA-addressed objects. `layout-mapping.json` is a separate reviewed layout-copy plan and never extracts, installs, executes, overwrites or auto-starts anything. The original input manifest’s new ROI source reference is resolved to the fixed source commit by this outer transfer manifest. Prepared public spec contains only safe relative paths; the Windows owner regenerates its private deployment paths and checks canonical/mask hashes.','', 'The registry at `docs/TASK1_LOCAL_HANDOFF_20261025/candidate-ownership.json` is authoritative; historical source-only protocol templates retain their old placeholder runtime path. A stale heartbeat or elapsed TTL alone does not transfer ownership. No Windows save/OneDrive completion, convergence, experimental validation, activation or safety claim is made.','']
    text(OUT/'public/README.md','\n'.join(lines))
    identity_doc=dict(schema='task1-local-handoff-public-identity-v1',source_commit=S,source_adapter_SHA256=sha(PAIR/'portable_pair.py'),input_manifest_SHA256=sha(PAIR/'input-manifest.json'),manifest_SHA256=sha(OUT/'public/transfer-manifest.json'),manifest_bytes=(OUT/'public/transfer-manifest.json').stat().st_size,manifest_validation=result,registry_SHA256=sha(OUT/'public/candidate-ownership.json'),candidate_configurations={case['candidate_id']:case['canonical_config_SHA256']for case in publiccases},local_execution_started=False,Windows_backup_complete=False,OneDrive_sync_verified=False)
    new(OUT/'public/handoff-identity.json',identity_doc)
    for path,expected in list(pins.items()):guard();req(sha(path)==expected,'Complete frozen metadata/source verification after preparation')
   metadatafiles={DOCS+name:OUT/'public'/name for name in('candidate-ownership.json','README.md','transfer-manifest.json','layout-mapping.json','handoff-identity.json')}
   metadatafiles[REMOTE+'existing-input-proof.json']=OUT/'existing-input-proof.json'
   mp=OUT/'result-plan.json';new(mp,plan(metadatafiles,S,'Bind two conditional local TIS owners to fixed sources, exact configs and safe input transfer',OUT/'result-publication/result-publication.json',comment='로컬2개 후보 LOCAL14-c9 / LOCAL16-c8p5를 고유run ID와 실제 canonical설정/분할해시·고정source commit·안전한전송manifest로 조건부배정했습니다. 클라우드배치는 유지하며 로컬PDE/활성lease/PID는 아직0입니다. Windows어댑터검증·실행직전RAM/commit·중앙CAS소유권 readback을 통과한 조건만 실행합니다. 메타데이터준비이며 새PDE0/Q·원시필드읽기0, 설치·원본삭제·예산확대·main병합0입니다. 실제Windows저장/OneDrive동기화는미검증입니다.'))
   command([sys.executable,'-B',str(PUB),'--plan',str(mp),'--output','/dev/shm/task1-git-local-handoff-metadata-20261025','--queue-registration',str(OUT/'registration.json')],'registry-and-transfer-publication',PUB_CAP,True)
   result=read(OUT/'result-publication/result-publication.json');req(result['status']=='published_readback_verified','Actual central registry and manifest immutable full readback required')
   receipt.update(status='local_pair_conditional_assignments_and_transfer_published',source_commit=S,result_commit=result['commit'],registry_repo_relative_path=REGISTRY,manifest_repo_relative_path=DOCS+'transfer-manifest.json',manifest_SHA256=identity_doc['manifest_SHA256'],registry_SHA256=identity_doc['registry_SHA256'],candidate_configurations=identity_doc['candidate_configurations'],active_local_leases=0,actual_local_PDE_RHS=0)
   checkpoint('conditional_assignment_published_local_adapter_and_lease_pending',result_commit=result['commit'])
  except BaseException as error:
   failed=state['phase'];receipt.update(error_type=type(error).__name__,error=str(error),failed_phase=failed);checkpoint('failed_preserved',failed_phase=failed,error=str(error));raise
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
   for child,tick in b.owned_descendants(pid,ticks,dict(owned)).items():
    if child!=pid and b.live(child,tick):
     try:os.kill(child,signal.SIGKILL)
     except ProcessLookupError:pass
   elapsed=time.monotonic()-started;ledger=budget.load_ledger();debit=max(0.,elapsed-git_wall);ledger['spent_seconds']+=debit;ledger['runs'].append(dict(run_id=OUT.name,stage='local_assignment_metadata_and_transfer_supervision',seconds=debit,status=receipt['status'],Git_children_debited_separately=True,new_PDE_RHS=0,raw_array_bytes_read=False))
   temporary=ROOT/'runtime'/('task1-budget-local-handoff-'+str(pid)+'.tmp');new(temporary,ledger);os.replace(temporary,ROOT/'runtime/task1-budget.json')
   receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,nonduplicated_ledger_seconds=debit,remaining_approved_seconds=budget.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')});new(OUT/'receipt.json',receipt)
   for sig,handler in handlers.items():signal.signal(sig,handler)
   print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
