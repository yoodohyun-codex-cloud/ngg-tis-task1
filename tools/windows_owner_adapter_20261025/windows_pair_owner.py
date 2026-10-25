"""Windows pair dispatcher. Fail closed until a remote central lease is verified.
No Git writes, installation, shell invocation or numerical source modification.
"""
import ctypes as C, ctypes.wintypes as W, datetime, hashlib, json, msvcrt, os, pathlib, sys, time, urllib.request
import windows_guard as wg
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE/'handoff-fe212445'/'layout'
REG='docs/TASK1_LOCAL_HANDOFF_20261025/candidate-ownership.json'
REPO='https://raw.githubusercontent.com/yoodohyun-codex-cloud/ngg-tis-task1/'
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def new(p,obj):
    with pathlib.Path(p).open('x',encoding='utf8') as f:json.dump(obj,f,indent=2)
def safe_tree():
    for p in [ROOT,*ROOT.parents,*ROOT.rglob('*')]:
        need(not p.is_symlink() and not p.is_junction(),'Unexpected reparse path')
def start_time():
    k=C.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=W.HANDLE
    k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4
    a=[W.FILETIME() for _ in range(4)];need(k.GetProcessTimes(k.GetCurrentProcess(),*[C.byref(x) for x in a]),'Creation time')
    ticks=(a[0].dwHighDateTime<<32)|a[0].dwLowDateTime
    return datetime.datetime.fromtimestamp((ticks-116444736000000000)/1e7,datetime.timezone.utc).isoformat()
def job_check():
    k=C.WinDLL('kernel32',use_last_error=True);k.OpenJobObjectW.argtypes=[W.DWORD,W.BOOL,W.LPCWSTR];k.OpenJobObjectW.restype=W.HANDLE
    k.GetCurrentProcess.restype=W.HANDLE;k.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,C.POINTER(W.BOOL)]
    name=os.environ.get('TIS_WINDOWS_JOB','');need(name=='Local\\TIS-'+pathlib.Path.cwd().name,'Exact named Job identity')
    handle=wg.check(k.OpenJobObjectW(4,False,name));limit=wg.LIMIT()
    try:
        inside=W.BOOL();wg.check(k.IsProcessInJob(k.GetCurrentProcess(),handle,C.byref(inside)));need(inside.value,'Owner is not in intended Job')
        wg.check(wg.queryjob(handle,9,C.byref(limit),C.sizeof(limit),None))
    finally:wg.close(handle)
    need(limit.job_memory==3999997952 and limit.basic.affinity==13653 and limit.basic.flags&0x2000,'Exact current Job limits/kill-on-close')
    need(wg.rss(os.getpid())<=4_000_000_000,'Owner RSS cap')
    return {'commit_bytes':int(limit.job_memory),'affinity':int(limit.basic.affinity),'flags':int(limit.basic.flags)}
class Owner:
    def __init__(self,deadline):
        self.deadline=deadline;self.creation=start_time();self.last_remote=0;self.registry=None;self.expected={}
        self.lock=open('pair-owner.lock','x+b');self.lock.write(b'0');self.lock.flush();self.lock.seek(0);msvcrt.locking(self.lock.fileno(),msvcrt.LK_NBLCK,1)
        self.identity={'PID':os.getpid(),'CreationTime_UTC':self.creation,'WindowsJob_identity':pathlib.Path.cwd().name,'frozen_owner_source_SHA256':wg.sha(__file__)}
        self.guard_hash=wg.sha(wg.__file__);self.hash_checked=0
    def local(self):
        need(time.monotonic()<self.deadline,'Finite batch timeout');need(start_time()==self.creation,'Process creation changed');job_check()
        need(not pathlib.Path('STOP').exists(),'Stop marker')
        if time.monotonic()-self.hash_checked>10:
            need(wg.sha(__file__)==self.identity['frozen_owner_source_SHA256'] and wg.sha(wg.__file__)==self.guard_hash,'Frozen owner/guard changed')
            self.hash_checked=time.monotonic()
    def accept(self,admission):
        need(isinstance(admission,dict),'Admission object')
        self.admission=admission;self.last_remote=0
        self.fetch()
    def fetch(self):
        a=self.admission;commit=a['registry_commit'];need(len(commit)==40 and all(x in '0123456789abcdef' for x in commit),'Pinned registry commit')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*a,**k):raise RuntimeError('Redirect refused')
        op=urllib.request.build_opener(NoRedirect)
        with op.open(REPO+commit+'/'+REG,timeout=15) as r:raw=r.read(2_000_001)
        need(len(raw)<=2_000_000 and hashlib.sha256(raw).hexdigest()==a['registry_SHA256'],'Remote registry bytes')
        registry=json.loads(raw)
        # Branch read prevents a newer revocation/transfer from being hidden by a pinned historical lease.
        with op.open(REPO+'refs/heads/codex/task1-cloud-restart-20261020/'+REG,timeout=15) as r:latest=json.loads(r.read(2_000_001))
        for cid in self.expected:
            row=next(x for x in registry['candidates'] if x['candidate_id']==cid)
            current=next(x for x in latest['candidates'] if x['candidate_id']==cid)
            need(row==current,'Registry candidate changed; revalidate lease')
            self.validate_row(row,cid)
        self.registry=registry;self.last_remote=time.monotonic()
    def validate_row(self,row,cid):
        need(row['canonical_config_SHA256']==self.expected[cid] and row['assigned_environment']=='local_windows_01','Canonical owner assignment')
        need(row['execution_permitted'] is True and row['lease'] is not None,'Central execution admission/lease missing')
        lease=row['lease'];need(lease['OS_process_identity']==self.identity,'Exact live owner/Job/source lease identity')
        need(lease['lease_id']==self.admission['leases'][cid] and int(lease['lease_epoch'])>0,'Lease fencing identity')
    def assert_active(self,config):
        self.local();need(config in self.expected.values(),'Unassigned configuration')
        if time.monotonic()-self.last_remote>10:self.fetch()
        need(self.registry is not None,'Remote registry not admitted')
        cid=next(k for k,v in self.expected.items() if v==config)
        self.validate_row(next(x for x in self.registry['candidates'] if x['candidate_id']==cid),cid)
        if not hasattr(self,'heartbeat_at') or time.monotonic()-self.heartbeat_at>10:
            new('heartbeat-'+str(time.time_ns())+'.json',dict(identity=self.identity,candidate_id=cid,updated_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase='guard_checkpoint'))
            self.heartbeat_at=time.monotonic()
def main():
    safe_tree();job=job_check();owner=Owner(time.monotonic()+1800)
    # Full layout pin validation occurs before importing any downloaded module.
    mapping=json.loads((ROOT.parent/'layout-mapping.json').read_text())
    for row in mapping['files']:
        p=ROOT/row['desired_layout_relative_path'];need(p.stat().st_size==row['bytes'] and wg.sha(p)==row['SHA256'],'Layout pin mismatch')
    sys.path.insert(0,str(ROOT));import portable_pair as pair
    prep=pathlib.Path('prepared');prep.mkdir();spec=pair.prepare_spec(ROOT,prep)
    central=json.loads((ROOT.parent/'candidate-ownership.json').read_text())
    for case in spec['candidates']:
        expected=next(x for x in central['candidates'] if x['candidate_id']==case['candidate_id'])
        need(case['canonical_config_SHA256']==expected['canonical_config_SHA256'] and case['mask_sha256']==expected['mask_SHA256'],'Generated config/mask identity')
        owner.expected[case['candidate_id']]=case['canonical_config_SHA256']
    import numpy as np,scipy
    kernel=pair.scientific_kernel(ROOT);import frozen_fourier_v1 as fourier, frozen_coarse_cem as cem
    tests={'analytic':fourier.analytic_contracts(owner.local)}
    ij=np.array([[0,0],[1,0],[2,0]]);e=kernel['field'].lateral_field(np,np.array([0.,-1.,-2.]),ij,1.,owner.local)
    need(np.allclose(e[:,0],[.5,1.,.5]) and np.all(e[:,1]==0),'Half-face field contract')
    s,metal,q=cem.contact_equations([0j]*4,[0j]*4,[1+0j,0j],[0,1,2,3],[0,1,2,3],[2.]*4,2+0j)
    need(q==[-1+0j,0j,0j,0j] and abs(metal[0]-1.02)<1e-14,'Signed contact/50ohm/inactive output contract')
    stats=kernel['metrics'].weighted_stats(np,np.array([1.,3.]),np.array([1.,3.]),np.zeros((2,5)))
    need(stats['mean']==2.5 and stats['p10']==1 and stats['p95']==3,'Weighted metric contract')
    tests.update(field_half_faces=True,circuit=True,weighted_metrics=True,canonical_config_and_masks=True)
    for cid in owner.expected:
        try:owner.validate_row(next(x for x in central['candidates'] if x['candidate_id']==cid),cid)
        except RuntimeError as e:need('admission/lease' in str(e),'Expected inactive lease refusal')
        else:raise RuntimeError('Inactive lease accepted')
    tests['inactive_lease_rejected']=True
    # Synthetic lease fixtures test admission predicates only, never remote CAS.
    import copy
    cid=next(iter(owner.expected));fixture=copy.deepcopy(next(x for x in central['candidates'] if x['candidate_id']==cid))
    owner.admission={'leases':{cid:'synthetic-test-only'}}
    fixture.update(execution_permitted=True,lease={'OS_process_identity':owner.identity.copy(),'lease_id':'synthetic-test-only','lease_epoch':1})
    owner.validate_row(fixture,cid)
    for name in ('PID','CreationTime_UTC','WindowsJob_identity','frozen_owner_source_SHA256'):
        bad=copy.deepcopy(fixture);bad['lease']['OS_process_identity'][name]='wrong-test-identity'
        try:owner.validate_row(bad,cid)
        except RuntimeError:pass
        else:raise RuntimeError('Mismatched lease identity accepted: '+name)
    bad=copy.deepcopy(fixture);bad['canonical_config_SHA256']='0'*64
    try:owner.validate_row(bad,cid)
    except RuntimeError:pass
    else:raise RuntimeError('Wrong scientific configuration accepted')
    del owner.admission
    tests['synthetic_lease_identity_and_config_rejections']=True
    new('adapter-contracts.json',dict(tests=tests,identity=owner.identity,job=job,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,new_research_PDE=False))
    if '--selftest' in sys.argv:return
    new('waiting-for-central-lease.json',dict(identity=owner.identity,configs=owner.expected,job=job,source_commit='6694e1a2931c149d0cb62ba5098e858464d75318',status='waiting_no_PDE',required_admission_fields=['registry_commit','registry_SHA256','leases']))
    while not pathlib.Path('admission.json').exists():owner.local();time.sleep(1)
    owner.accept(json.loads(pathlib.Path('admission.json').read_text()))
    mem=wg.memory();need(mem['available']>1_800_000_000 and mem['commit_available']>2_100_000_000,'Fresh workload memory/commit admission')
    new('research-started.json',dict(identity=owner.identity,memory=mem,UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),lease_registry_commit=owner.admission['registry_commit'],status='admitted_before_cache_loading'))
    pair.verify_inputs(ROOT,owner.local)
    guard=lambda:owner.assert_active(spec['candidates'][0]['canonical_config_SHA256'])
    shared=pair.load_graph_and_Q(ROOT,np,guard);grid=pair.prepare_grid(ROOT,np,shared,guard,owner.deadline)
    np.savez_compressed('grid-weights.npz',grid=grid['grid'],**grid['weights']);new('ROI-receipt.json',grid['ROI_receipt'])
    for case in spec['candidates']:
        owner.assert_active(case['canonical_config_SHA256']);out=pathlib.Path(case['run_id']);out.mkdir()
        pair.build_local_case(np,ROOT,case,spec,shared,grid['grid'],grid['weights'],owner,out,owner.deadline)
    new('pair-complete.json',{'new_driven_RHS':4,'candidate_adopted':False,'identity':owner.identity})
if __name__=='__main__':
    try:main()
    except BaseException as e:
        new('owner-failure-'+str(time.time_ns())+'.json',{'error':repr(e),'research_completion_not_asserted':True});raise
