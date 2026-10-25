"""One killable numerical child; parent owns all locks, resource/time watchdogs."""
import sys,os,json,time,hashlib,resource,unittest,io,argparse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');SRC=Path('/dev/shm/task1-layer-dtn-20261025/source');sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b

def req(x,m):
 if not x:raise ValueError(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,j):
 with Path(p).open('x')as f:json.dump(j,f,ensure_ascii=False,allow_nan=False,indent=2)
def owns(pid,path):
 inode=path.stat().st_ino;types=set()
 for fd in Path('/proc',str(pid),'fd').glob('*'):
  try:
   if fd.stat().st_ino!=inode:continue
   for line in Path('/proc',str(pid),'fdinfo',fd.name).read_text().splitlines():
    if line.startswith('lock:')and (' '+str(pid)+' ')in line:
     if ' FLOCK 'in line:types.add('FLOCK')
     if ' POSIX 'in line:types.add('POSIX')
  except OSError:pass
 return types=={'FLOCK','POSIX'}
a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--as-limit',type=int,required=True);args=a.parse_args();OUT=Path(args.output);reg=json.loads((OUT/'registration.json').read_text());pre=json.loads((OUT/'preregistration.json').read_text());regsha=sha(OUT/'registration.json');pid=reg['supervisor_pid'];ticks=reg['proc_start_ticks'];publication=json.loads((OUT/'source-publication/result-publication.json').read_text());pubsha=sha(OUT/'source-publication/result-publication.json');req(publication['status']=='published_readback_verified','Verified source publication beforeheavy');req(publication['files']['data-native/cloud-layer-dtn-phase1-20261025/preregistration.json']['SHA256']==sha(OUT/'preregistration.json'),'Published exact preregistration bytes')
req(OUT==Path('/dev/shm/task1-layer-dtn-20261025-run')and OUT==OUT.resolve(),'Exact new output');req(1_000_000_000<=args.as_limit<=4_200_000_000,'Conservative address-space bound');resource.setrlimit(resource.RLIMIT_AS,(args.as_limit,args.as_limit))
start=time.monotonic();cpu=time.process_time();receipt=dict(schema='task1-layer-dtn-phase1-worker-v1',status='failed_preserved',started_utc=b.now(),pid=os.getpid(),proc_start_ticks=b.ticks(os.getpid()),parent_pid=pid,parent_start_ticks=ticks,finite_parent_watchdog_seconds=600,RLIMIT_AS_bytes=args.as_limit,new_CEM_RHS=0,new_native_FVM_RHS=0)
def guard():
 req(os.getppid()==pid and b.live(pid,ticks),'Actual parent PID/startticks changed');req(sha(OUT/'registration.json')==regsha,'Parent registration changed')
 req(str(Path('/proc',str(pid),'cwd').resolve()/reg['controller_path'])==reg['controller_path'],'Canonical parent controller')
 req(reg['controller_path'].encode()in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')and sha(reg['controller_path'])==reg['controller_sha256'],'Actual registered parent source')
 for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):req(owns(pid,ROOT/name),'Parent dual lock missing '+name)
 req(time.monotonic()-start<600,'Finite child bound')
 for p,h in{**pre['source_sha256'],**pre['input_sha256']}.items():req(sha(p)==h,'Frozen source/input changed '+p)
 req(sha(OUT/'spec.json')==pre['spec_sha256'],'Exact preregistered specification')
 req(sha(OUT/'source-publication/result-publication.json')==pubsha,'Source-publication receipt changed')
try:
 guard();import layer_dtn_backend as model
 stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(SRC),pattern='test_layer_dtn_backend.py');tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 with(OUT/'tests.log').open('x')as f:f.write(stream.getvalue())
 req(tests.wasSuccessful(),'Phase1 analytic pure contracts failed');spec=json.loads((OUT/'spec.json').read_text());result=model.build(spec,guard,deadline_monotonic=start+590)
 import numpy as np
 from threadpoolctl import threadpool_info
 pools=threadpool_info();req(all(p.get('num_threads',0)<=4 for p in pools if p.get('user_api')in('blas','openmp')),'BLAS/OpenMP thread cap')
 with(OUT/'arrays.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
 new(OUT/'summary.json',result['summary']);new(OUT/'threadpool-runtime.json',dict(actual_affinity=sorted(os.sched_getaffinity(0)),libraries=pools,scope='Configured<=4threads each and<=4CPUaffinity; actualCPUuse separatelymeasured'))
 guard();receipt.update(status='phase1_graph_eigen_MMS_calculated',test_count=tests.testsRun,summary_sha256=sha(OUT/'summary.json'),arrays_sha256=sha(OUT/'arrays.npz'),actual_eigen_wall_seconds=result['summary']['eigen']['eigen_wall_seconds'],new_CEM_RHS=0,local_cache_manifest_sha256=sha(OUT/'eigen-cache/manifest.json'),cache_remote_verified=False)
except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
finally:
 elapsed=time.monotonic()-start;receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,CPU_seconds=time.process_time()-cpu,observed_CPU_cores=(time.process_time()-cpu)/max(elapsed,1e-30));new(OUT/'worker-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
