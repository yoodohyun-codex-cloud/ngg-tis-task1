"""Finite cached source-basis audit; no new native PDE."""
import sys,os,json,time,signal,threading,hashlib,shutil,unittest,io
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');SRC=Path('/dev/shm/task1-u19-basis-audit-20261025/source');OUT=Path('/dev/shm/task1-u19-basis-audit-20261025-run');L=ROOT/'runtime/task1-budget.json';sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tis-java'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as policy

def req(x,m):
 if not x:raise ValueError(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,x):
 with Path(p).open('x')as f:json.dump(x,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
with b.dual_lock(ROOT/'.task1-queue-owner.lock'),b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
 req(not OUT.exists(),'Preserve all previous runs');OUT.mkdir();(OUT/'source').mkdir();start=time.monotonic();cpu0=time.process_time();pid=os.getpid();ticks=b.ticks(pid);stop=threading.Event();limits=ep.resolve_limits();settings=ep.configure_process(limits);state=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);receipt=dict(schema='task1-U19-cached-basis-finite-stage-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,finite_seconds=60,cumulative_time_unlimited=True,new_real_native_PDE=0,actual_SC8_native_started=False,resource_limits=limits)
 def guard():
  rss=b.rss(pid);tmp=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));state.update(peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],tmp),peak_accounted=max(state['peak_accounted'],rss+tmp));req(rss+tmp<=limits['total_memory_bytes'],'Approved8e9RSS+ownedtmpfs');req(time.monotonic()-start<60,'Finite60secondestimatorstage')
 def interrupt(s,f):raise TimeoutError('Finite estimator stage or external signal')
 def monitor():
  while not stop.wait(1):
   try:guard()
   except BaseException:os.kill(pid,signal.SIGTERM);return
 handlers={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
 for s in handlers:signal.signal(s,interrupt)
 signal.setitimer(signal.ITIMER_REAL,60);thread=threading.Thread(target=monitor,daemon=True);thread.start()
 try:
  import basis_audit as model
  inputs=model.required_inputs();inputs.update(ep.execution_policy_refs());inputs[str(Path(__file__))]=sha(__file__)
  sources={str(p):sha(p)for p in SRC.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')}
  spec=model.make_spec();new(OUT/'spec.json',spec);new(OUT/'preregistration.json',dict(schema='task1-U19-cached-basis-preregistration-v1',case_id='actualU19-source0-source1-audit-2000',maximum_cached_native_RHS=2,new_PDE=0,source_sha256=sources,input_sha256=inputs,spec_SHA256=sha(OUT/'spec.json'),scope=spec['interpretation'],resource_limits=limits,finite_seconds=60,old_interface_QA_limit_retained=.05,criteria_relaxed=False,prior_native_commit=spec['publication_commit'],root_owner_source_SHA256=sha(__file__)))
  shutil.copyfile(__file__,OUT/'source'/'run_basis_audit.py')
  for p in SRC.iterdir():
   if p.is_file():shutil.copyfile(p,OUT/'source'/p.name)
  stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(SRC),pattern='test_basis_audit.py');tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
  with(OUT/'tests.log').open('x')as f:f.write(stream.getvalue())
  req(tests.wasSuccessful(),'Cachedbasis pure contracts failed');guard();result=model.build(guard,deadline_monotonic=start+50,spec=spec);new(OUT/'summary.json',result['summary'])
  import numpy as np
  with(OUT/'scalars.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
  for p,h in{**sources,**inputs}.items():guard();req(sha(p)==h,'Immutable cachedsource/input changed')
  receipt.update(status='cached_basis_audit_computed',all_conservation_and_source0_checks_passed=result['summary']['all_conservation_and_source0_checks_passed'],test_count=tests.testsRun,cached_native_RHS=2,new_PDE=0,summary_SHA256=sha(OUT/'summary.json'),scalars_SHA256=sha(OUT/'scalars.npz'),source_implementation='cached raw fields; CPU4 allowed cap, measured usage in receipt')
 except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2);elapsed=time.monotonic()-start;cpu=time.process_time()-cpu0;ledger=policy.load_ledger();ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=OUT.name,stage='cached_U19_source_basis_audit',status=receipt['status'],seconds=elapsed));tmp=L.with_name('task1-budget-estimator-finite.tmp')
  with tmp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
  os.replace(tmp,L);receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,CPU_seconds=cpu,observed_average_CPU_cores=cpu/max(elapsed,1e-30),resources=state,remaining_seconds=policy.remaining_seconds(ledger));new(OUT/'computation-receipt.json',receipt)
  print(json.dumps(receipt,ensure_ascii=False))
