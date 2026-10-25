"""Local Windows batch guard. No network, installers, cloud control or source execution at import."""
import argparse, ctypes as C, hashlib, json, msvcrt, os, pathlib, subprocess, sys, time
from ctypes import wintypes as W

K=C.WinDLL('kernel32',use_last_error=True); P=C.WinDLL('psapi',use_last_error=True)
SIZE=C.c_size_t; U64=C.c_ulonglong
def api(name, args, ret=W.BOOL, lib=K):
    f=getattr(lib,name); f.argtypes=args; f.restype=ret; return f
def check(value):
    if not value: raise C.WinError(C.get_last_error())
    return value
class BASIC(C.Structure):
    _fields_=[('user',C.c_longlong),('job',C.c_longlong),('flags',W.DWORD),('minws',SIZE),('maxws',SIZE),('active',W.DWORD),('affinity',SIZE),('priority',W.DWORD),('scheduling',W.DWORD)]
class IO(C.Structure): _fields_=[(n,U64) for n in ('r','w','o','rb','wb','ob')]
class LIMIT(C.Structure): _fields_=[('basic',BASIC),('io',IO),('process_memory',SIZE),('job_memory',SIZE),('peak_process',SIZE),('peak_job',SIZE)]
class MEM(C.Structure): _fields_=[('length',W.DWORD),('load',W.DWORD)]+[(n,U64) for n in ('total','available','page_total','page_available','virtual_total','virtual_available','extended')]
class SI(C.Structure):
    _fields_=[('cb',W.DWORD),('reserved',W.LPWSTR),('desktop',W.LPWSTR),('title',W.LPWSTR)]+[(n,W.DWORD) for n in ('x','y','xs','ys','xc','yc','fill','flags')]+[('show',W.WORD),('reserved2size',W.WORD),('reserved2',C.c_void_p),('stdin',W.HANDLE),('stdout',W.HANDLE),('stderr',W.HANDLE)]
class PI(C.Structure): _fields_=[('process',W.HANDLE),('thread',W.HANDLE),('pid',W.DWORD),('tid',W.DWORD)]
class PMC(C.Structure): _fields_=[('cb',W.DWORD),('faults',W.DWORD)]+[(n,SIZE) for n in ('peakws','ws','peakpaged','paged','peaknonpaged','nonpaged','page','peakpage','private')]
class ACCOUNT(C.Structure):
    _fields_=[(n,C.c_longlong) for n in ('user','kernel','period_user','period_kernel')]+[(n,W.DWORD) for n in ('faults','total_processes','active_processes','terminated_processes')]
close=api('CloseHandle',[W.HANDLE]); createjob=api('CreateJobObjectW',[C.c_void_p,W.LPCWSTR],W.HANDLE)
setjob=api('SetInformationJobObject',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD]); queryjob=api('QueryInformationJobObject',[W.HANDLE,C.c_int,C.c_void_p,W.DWORD,C.c_void_p])
assign=api('AssignProcessToJobObject',[W.HANDLE,W.HANDLE]); terminate=api('TerminateJobObject',[W.HANDLE,W.UINT])
createprocess=api('CreateProcessW',[W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,W.DWORD,C.c_void_p,W.LPCWSTR,C.POINTER(SI),C.POINTER(PI)])
resume=api('ResumeThread',[W.HANDLE],W.DWORD); exitcode=api('GetExitCodeProcess',[W.HANDLE,C.POINTER(W.DWORD)])
killprocess=api('TerminateProcess',[W.HANDLE,W.UINT])
openprocess=api('OpenProcess',[W.DWORD,W.BOOL,W.DWORD],W.HANDLE)
getmem=api('GetProcessMemoryInfo',[W.HANDLE,C.POINTER(PMC),W.DWORD],lib=P)
affinity=api('GetProcessAffinityMask',[W.HANDLE,C.POINTER(SIZE),C.POINTER(SIZE)])
globalmem=api('GlobalMemoryStatusEx',[C.POINTER(MEM)])
cpus=api('GetSystemCpuSetInformation',[C.c_void_p,W.DWORD,C.POINTER(W.DWORD),W.HANDLE,W.DWORD])
def memory():
    m=MEM(); m.length=C.sizeof(m); check(globalmem(C.byref(m))); return {'total':m.total,'available':m.available,'commit_limit':m.page_total,'commit_available':m.page_available}
def topology():
    n=W.DWORD(); cpus(None,0,C.byref(n),None,0); buf=C.create_string_buffer(n.value); check(cpus(buf,n,C.byref(n),None,0))
    rows=[]; off=0
    while off<n.value:
        size=C.c_uint32.from_buffer(buf,off).value; kind=C.c_uint32.from_buffer(buf,off+4).value
        if size<8: raise RuntimeError('Invalid CPU topology record')
        if kind==0:
            raw=buf.raw[off:off+size]
            rows.append(dict(group=int.from_bytes(raw[12:14],'little'),logical=raw[14],core=raw[15],efficiency=raw[18]))
        off+=size
    return rows
def mask_for_eight():
    allowed=SIZE(); system=SIZE(); check(affinity(K.GetCurrentProcess(),C.byref(allowed),C.byref(system)))
    selected=[]; seen=set()
    for r in sorted(topology(),key=lambda r:(-r['efficiency'],r['core'],r['logical'])):
        if r['group']==0 and (allowed.value>>r['logical'])&1 and r['core'] not in seen:
            selected.append(r); seen.add(r['core'])
            if len(selected)==8: break
    if len(selected)!=8: raise RuntimeError('Eight distinct accessible physical cores unavailable')
    return sum(1<<r['logical'] for r in selected),selected
def rss(pid):
    h=openprocess(0x410,False,pid)
    if not h: return 0
    try:
        m=PMC(); m.cb=C.sizeof(m); return m.ws if getmem(h,C.byref(m),m.cb) else 0
    finally: close(h)
def job_pids(job):
    buf=C.create_string_buffer(8+8*1024); check(queryjob(job,3,buf,len(buf),None)); count=C.c_uint32.from_buffer(buf,4).value
    if count>1024: raise RuntimeError('Process count exceeded monitor capacity')
    return [SIZE.from_buffer(buf,8+i*8).value for i in range(count)]
def write_new(path, value):
    with open(path,'x',encoding='utf8') as f: json.dump(value,f,indent=2)
def sha(path):
    with open(path,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def run(config):
    base=pathlib.Path(__file__).resolve().parent; spec=json.loads(pathlib.Path(config).read_text(encoding='utf-8-sig'))
    run_id=spec['run_id']
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in run_id): raise ValueError('Unsafe run ID')
    mode=spec.get('mode'); cap=int(spec['memory_bytes']); pressure_floor=128_000_000
    if mode=='selftest':
        if not 64_000_000<=cap<=4_000_000_000: raise ValueError('Selftest cap out of range')
    elif mode in ('research','lease_wait'):
        if cap!=4_000_000_000: raise ValueError('Research cap must be exactly 4,000,000,000 bytes')
        if (mode=='research' and not spec.get('owner_confirmation')) or int(spec['evaluation_cells'])>800000: raise ValueError('Missing owner confirmation or cell limit')
        if mode=='lease_wait' and (pathlib.Path(spec['argv'][2]).name!='windows_pair_owner.py' or '--selftest' in spec['argv']): raise ValueError('Lease wait requires the verified pair dispatcher')
    else: raise ValueError('Mode must be explicit')
    timeout=float(spec['timeout_seconds'])
    if not 0<timeout<=3600: raise ValueError('Finite batch timeout required')
    for p,h in spec['source_sha256'].items():
        if sha(p)!=h: raise ValueError('Source digest mismatch')
    argv=spec['argv']; exe=pathlib.Path(argv[0]).resolve()
    if not exe.is_file() or not exe.is_relative_to(base): raise ValueError('Executable must be the isolated local runtime')
    mask,selected=mask_for_eight(); mem=memory()
    expected_rss=int(spec['estimated_peak_rss_bytes']) if mode in ('research','lease_wait') else min(cap,256_000_000)
    expected_commit=int(spec['estimated_peak_commit_bytes']) if mode in ('research','lease_wait') else min(cap,750_000_000)
    if not (0<expected_rss<=cap and 0<expected_commit<=cap): raise ValueError('Bounded working-set and commit estimates required')
    if mem['available']<expected_rss+pressure_floor or mem['commit_available']<expected_commit+pressure_floor:
        raise RuntimeError(f'Batch-size admission blocked: memory={mem}, estimated RSS={expected_rss}, estimated commit={expected_commit}; reduce the finite batch')
    runs=base/'runs'; runs.mkdir(exist_ok=True); dest=runs/run_id; dest.mkdir()
    lock=open(base/'owner.lock','a+b'); lock.seek(0)
    if lock.read(1)==b'': lock.write(b'0'); lock.flush()
    lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    job=None; streams=[]; pi=PI(); began=time.monotonic(); pressure_since=None
    record=dict(run_id=run_id,mode=mode,admission_memory=mem,memory_cap_bytes=cap,severe_pressure_floor_bytes=pressure_floor,estimated_peak_rss_bytes=expected_rss,estimated_peak_commit_bytes=expected_commit,selected_physical_cores=selected,affinity_mask=mask,peak_tree_rss=0,peak_job_commit=0,new_research_PDE=mode=='research',status='starting')
    try:
        job_name='Local\\TIS-'+run_id
        write_new(dest/'spec.json',spec); job=check(createjob(None,job_name)); limits=LIMIT()
        limits.basic.flags=0x2000|0x200|0x10|0x8 # kill-on-close, job commit, affinity, active count
        limits.basic.active=32; limits.basic.affinity=mask; limits.job_memory=(cap//4096)*4096
        check(setjob(job,9,C.byref(limits),C.sizeof(limits))); actual=LIMIT(); check(queryjob(job,9,C.byref(actual),C.sizeof(actual),None))
        if actual.job_memory!=limits.job_memory or actual.basic.affinity!=mask: raise RuntimeError('Job limit readback mismatch')
        record['job_limit_readback']={'flags':actual.basic.flags,'commit_bytes':actual.job_memory,'affinity':actual.basic.affinity}
        env=dict(os.environ); env.update(OPENBLAS_NUM_THREADS='8',OMP_NUM_THREADS='8',MKL_NUM_THREADS='8',NUMEXPR_NUM_THREADS='8',PYTHONDONTWRITEBYTECODE='1',TIS_WINDOWS_JOB=job_name)
        envbuf=C.create_unicode_buffer('\0'.join(f'{k}={v}' for k,v in sorted(env.items()))+'\0\0')
        si=SI(); si.cb=C.sizeof(si)
        streams=[open(os.devnull,'rb'),open(dest/'stdout.log','xb'),open(dest/'stderr.log','xb')]
        handles=[msvcrt.get_osfhandle(f.fileno()) for f in streams]
        for h in handles: os.set_handle_inheritable(h,True)
        si.flags=0x100; si.stdin,si.stdout,si.stderr=handles
        cmd=C.create_unicode_buffer(subprocess.list2cmdline(argv))
        check(createprocess(str(exe),cmd,None,None,True,0x4|0x400|0x8000000,envbuf,str(dest),C.byref(si),C.byref(pi)))
        for h in handles: os.set_handle_inheritable(h,False)
        check(assign(job,pi.process)); actualmask=SIZE(); sysmask=SIZE(); check(affinity(pi.process,C.byref(actualmask),C.byref(sysmask)))
        if actualmask.value!=mask: raise RuntimeError('Child affinity readback mismatch')
        record['child_affinity']=actualmask.value; record['pid']=pi.pid
        write_new(dest/'started.json',record)
        if resume(pi.thread)==0xffffffff: raise C.WinError(C.get_last_error())
        record['status']='running'
        while True:
            ids=job_pids(job); total=sum(rss(pid) for pid in ids)+rss(os.getpid()); record['peak_tree_rss']=max(record['peak_tree_rss'],total)
            actual=LIMIT(); check(queryjob(job,9,C.byref(actual),C.sizeof(actual),None)); record['peak_job_commit']=max(record['peak_job_commit'],actual.peak_job)
            if not ids: break
            now=time.monotonic(); current=memory(); low=current['available']<pressure_floor or current['commit_available']<pressure_floor
            if low and pressure_since is None:
                pressure_since=now; write_new(dest/('checkpoint-request-'+str(time.time_ns())+'.json'),dict(reason='severe_memory_pressure',memory=current))
                record['checkpoint_requested']=True
            elif not low: pressure_since=None
            reason='timeout' if now-began>timeout else ('rss_cap' if total>cap else ('severe_memory_pressure' if pressure_since is not None and now-pressure_since>=2 else None))
            if reason: check(terminate(job,124)); record['status']=reason; break
            time.sleep(.1)
        code=W.DWORD(); check(exitcode(pi.process,C.byref(code))); record['exit_code']=code.value
        if record['status']=='running': record['status']='completed' if code.value==0 else 'child_failed'
    except BaseException as e:
        record['status']='failed'; record['error']=repr(e)
        if pi.process: killprocess(pi.process,125)
        raise
    finally:
        if mode=='lease_wait':
            proofs=list(dest.glob('task1-local-*/*-solve-proof.json'))
            record['new_research_PDE']=bool(proofs)
            record['PDE_completion_proofs']=len(proofs)
        record['elapsed_seconds']=time.monotonic()-began
        if job:
            accounting=ACCOUNT()
            if queryjob(job,1,C.byref(accounting),C.sizeof(accounting),None):
                record['job_cpu_seconds']=(accounting.user+accounting.kernel)/1e7
                record['average_logical_cpu_usage']=record['job_cpu_seconds']/max(record['elapsed_seconds'],.001)
                record['total_job_processes']=accounting.total_processes
            close(job)
        if pi.thread: close(pi.thread)
        if pi.process: close(pi.process)
        for f in streams: f.close()
        write_new(dest/'receipt.json',record); lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1); lock.close()
        print(json.dumps(record))
    return 0 if record['status']=='completed' else 1
if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--inspect',action='store_true'); a.add_argument('--config'); ns=a.parse_args()
    if ns.inspect:
        mask,selected=mask_for_eight(); print(json.dumps(dict(memory=memory(),topology=topology(),selected=selected,mask=mask),indent=2))
    else: sys.exit(run(ns.config))
