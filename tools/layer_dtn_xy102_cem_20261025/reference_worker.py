"""One killable numerical child; parent owns all locks, resource/time watchdogs."""
import sys,os,json,time,hashlib,resource,unittest,io,argparse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');SRC=Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025/source');sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tis-java'),str(SRC)]
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
a=argparse.ArgumentParser();a.add_argument('--output',required=True);a.add_argument('--as-limit',type=int,required=True);args=a.parse_args();OUT=Path(args.output);reg=json.loads((OUT/'registration.json').read_text());pre=json.loads((OUT/'preregistration.json').read_text());regsha=sha(OUT/'registration.json');pid=reg['supervisor_pid'];ticks=reg['proc_start_ticks'];publication=json.loads((OUT/'source-publication/result-publication.json').read_text());pubsha=sha(OUT/'source-publication/result-publication.json');req(publication['status']=='published_readback_verified','Verified source publication beforeheavy');req(publication['files']['data-native/cloud-layer-dtn-xy102-cem-20261025/preregistration.json']['SHA256']==sha(OUT/'preregistration.json'),'Published exact preregistration bytes')
req(OUT==Path('/dev/shm/task1-layer-dtn-xy102-cem-20261025-run')and OUT==OUT.resolve(),'Exact new output');req(1_000_000_000<=args.as_limit<=4_200_000_000,'Conservative address-space bound');resource.setrlimit(resource.RLIMIT_AS,(args.as_limit,args.as_limit))
input_stats={p:(Path(p).stat().st_size,Path(p).stat().st_ino,Path(p).stat().st_mtime_ns)for p in pre['input_sha256']}
integrity_start=time.monotonic()
for p,h in pre['input_sha256'].items():req(sha(p)==h,'Full input/cache SHA before actualnewCEM '+p)
integrity_before_seconds=time.monotonic()-integrity_start
start=time.monotonic();cpu=time.process_time();receipt=dict(schema='task1-layer-dtn-CEM-reference-worker-v1',status='failed_preserved',started_utc=b.now(),pid=os.getpid(),proc_start_ticks=b.ticks(os.getpid()),parent_pid=pid,parent_start_ticks=ticks,finite_parent_watchdog_seconds=600,initial_full_input_integrity_seconds=integrity_before_seconds,RLIMIT_AS_bytes=args.as_limit,new_CEM_RHS_started_maximum=2,new_native_FVM_RHS=0)
def guard():
 req(os.getppid()==pid and b.live(pid,ticks),'Actual parent PID/startticks changed');req(sha(OUT/'registration.json')==regsha,'Parent registration changed')
 req(str(Path('/proc',str(pid),'cwd').resolve()/reg['controller_path'])==reg['controller_path'],'Canonical parent controller')
 req(reg['controller_path'].encode()in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')and sha(reg['controller_path'])==reg['controller_sha256'],'Actual registered parent source')
 for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):req(owns(pid,ROOT/name),'Parent dual lock missing '+name)
 req(time.monotonic()-start<600,'Finite child bound')
 for p,h in pre['source_sha256'].items():req(sha(p)==h,'Frozen source changed '+p)
 for p,h in pre['input_sha256'].items():
  f=Path(p);req((f.stat().st_size,f.stat().st_ino,f.stat().st_mtime_ns)==input_stats[p],'Immutable input/cache stat changed '+p)
  if f.stat().st_size<=1024**2:req(sha(p)==h,'Small immutable input SHA changed '+p)
 req(sha(OUT/'spec.json')==pre['spec_sha256'],'Exact preregistered specification')
 req(sha(OUT/'source-publication/result-publication.json')==pubsha,'Source-publication receipt changed')
try:
 guard();import layer_dtn_cem as model
 stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(SRC),pattern='test_*.py');tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 with(OUT/'tests.log').open('x')as f:f.write(stream.getvalue())
 req(tests.wasSuccessful(),'Reference analytic/fit pure contracts failed');spec=json.loads((OUT/'spec.json').read_text())
 new(OUT/'reference-execution-start.json',dict(started_utc=b.now(),new_CEM_conditions_started=1,maximum_new_CEM_RHS=2,frequency_Hz=2000,PID=os.getpid(),old_FVM_reference_unchanged=True))
 result=model.build(spec,guard,deadline_monotonic=start+540)
 import numpy as np
 new(OUT/'reference-summary.json',result['summary'])
 with(OUT/'reference-arrays.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
 # A completed reference remains preserved if subsequent cached comparison fails.
 receipt.update(new_CEM_conditions_completed=result['summary']['actual_new_CEM_conditions'],new_CEM_RHS_completed=result['summary']['actual_new_CEM_RHS'],reference_summary_sha256=sha(OUT/'reference-summary.json'),reference_arrays_sha256=sha(OUT/'reference-arrays.npz'))
 import cem_compare
 comparison=cem_compare.build(result,spec,guard,deadline_monotonic=start+590)
 new(OUT/'comparison-summary.json',comparison['summary'])
 if comparison.get('arrays'):
  with(OUT/'comparison-arrays.npz').open('xb')as f:np.savez_compressed(f,**comparison['arrays'])
 from threadpoolctl import threadpool_info
 pools=threadpool_info();req(all(p.get('num_threads',0)<=4 for p in pools if p.get('user_api')in('blas','openmp')),'BLAS/OpenMP thread cap')
 new(OUT/'threadpool-runtime.json',dict(actual_affinity=sorted(os.sched_getaffinity(0)),libraries=pools,scope='Configured<=4threads each and<=4CPUaffinity; actualCPUuse separatelymeasured'))
 for p,h in pre['input_sha256'].items():req(sha(p)==h,'Full input/cache SHA after actualreference '+p)
 guard();receipt.update(status='continuous_z_CEM_reference_and_comparison_calculated',test_count=tests.testsRun,reference_wall_seconds=result['summary']['wall_seconds'],comparison_summary_sha256=sha(OUT/'comparison-summary.json'),old_5percent_flags_preserved=True,cache_remote_verified=False)
except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
finally:
 elapsed=time.monotonic()-start;receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,CPU_seconds=time.process_time()-cpu,observed_CPU_cores=(time.process_time()-cpu)/max(elapsed,1e-30));new(OUT/'worker-receipt.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
