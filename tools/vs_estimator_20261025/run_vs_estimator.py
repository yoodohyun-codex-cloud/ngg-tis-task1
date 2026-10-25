"""Finite15-case VS-spacing manufactured diagnostic; no new real native PDE."""
import sys,os,json,time,signal,threading,hashlib,shutil,unittest,io
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');SRC=Path('/dev/shm/task1-vs-estimator-20261025/source');OUT=Path('/dev/shm/task1-vs-estimator-20261025-run');L=ROOT/'runtime/task1-budget.json';sys.path[:0]=[str(ROOT/'tools'),str(SRC)]
import task1_bounded_continuation as b,task1_execution_policy as ep,task1_resource_policy as policy

def req(x,m):
 if not x:raise ValueError(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def new(p,x):
 with Path(p).open('x')as f:json.dump(x,f,ensure_ascii=False,allow_nan=False,indent=2)
def size(p):return p.stat().st_size if p.is_file()else sum(q.stat().st_size for q in p.rglob('*')if q.is_file())
with b.dual_lock(ROOT/'.task1-queue-owner.lock'),b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
 req(not OUT.exists(),'Preserve all previous runs');OUT.mkdir();(OUT/'source').mkdir();start=time.monotonic();cpu0=time.process_time();pid=os.getpid();ticks=b.ticks(pid);stop=threading.Event();limits=ep.resolve_limits();settings=ep.configure_process(limits);state=dict(peak_RSS=0,peak_owned_tmpfs=0,peak_accounted=0);receipt=dict(schema='task1-VS-spacing-estimator-finite-stage-v1',status='failed_preserved',started_utc=b.now(),pid=pid,proc_start_ticks=ticks,finite_seconds=60,cumulative_time_unlimited=True,new_real_native_PDE=0,actual_SC8_native_started=False,resource_limits=limits)
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
  import vs_estimator as model
  inputs=model.required_inputs();inputs.update(ep.execution_policy_refs());inputs[str(Path(__file__))]=sha(__file__);inputs[str(model.SC8/'result-publication.json')]=sha(model.SC8/'result-publication.json');inputs[str(model.SC8/'persist-receipt.json')]=sha(model.SC8/'persist-receipt.json');publication=json.loads((model.SC8/'result-publication.json').read_text());req(publication['status']=='published_readback_verified'and all(x['readback_passed']for x in publication['files'].values()),'ActualSC8fullpublication prerequisite');sources={str(p):sha(p)for p in SRC.iterdir()if p.is_file()and p.suffix in('.py','.json','.md')}
  coarse=model.f.COARSE;config=coarse/'configs'/(model.f.COARSE_CASE+'.properties');spec=model.make_spec((coarse/'material-input.json').read_bytes(),config.read_bytes());new(OUT/'spec.json',spec);new(OUT/'preregistration.json',dict(schema='task1-VS-estimator-preregistration-v1',case_id='SC8-VS18-U19-G18-manufactured-2000',max_cases=15,new_real_native_PDE=0,source_sha256=sources,input_sha256=inputs,spec_SHA256=sha(OUT/'spec.json'),scope=spec['comparison'],resource_limits=limits,finite_seconds=60,real_QA_limit_retained=.05,criteria_relaxation=False,real_bias_subtraction=False,prior_real_SC8_commit=publication['commit'],root_owner_source_SHA256=sha(__file__),native_candidate_admission='separateRootDecisionAfterPublishedManufacturedResultsOnly'))
  shutil.copyfile(__file__,OUT/'source'/'run_vs_estimator.py')
  for p in SRC.iterdir():
   if p.is_file():shutil.copyfile(p,OUT/'source'/p.name)
  stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(SRC),pattern='test_vs_estimator.py');tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
  with(OUT/'tests.log').open('x')as f:f.write(stream.getvalue())
  req(tests.wasSuccessful(),'Manufactured estimator contracts failed');guard();result=model.build(spec,guard,deadline_monotonic=start+30);new(OUT/'summary.json',result['summary']);new(OUT/'profiles.json',result['arrays'])
  for p,h in{**sources,**inputs}.items():guard();req(sha(p)==h,'Immutable source/input changed')
  receipt.update(status='VS_spacing_manufactured_diagnostic_computed',manufactured_cases=len(result['summary']['rows']),test_count=tests.testsRun,analytic_contracts=result['summary']['analytic_contracts'],summary_SHA256=sha(OUT/'summary.json'),profiles_SHA256=sha(OUT/'profiles.json'),source_implementation='stdlib complex serial; CPU4 is an allowed cap, not a claim of4coreuse')
 except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2);elapsed=time.monotonic()-start;cpu=time.process_time()-cpu0;ledger=policy.load_ledger();ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=OUT.name,stage='VS_spacing_manufactured_estimator_diagnostic',status=receipt['status'],seconds=elapsed));tmp=L.with_name('task1-budget-estimator-finite.tmp')
  with tmp.open('x')as f:json.dump(ledger,f,ensure_ascii=False,separators=(',',':'),allow_nan=False)
  os.replace(tmp,L);receipt.update(finished_utc=b.now(),elapsed_seconds=elapsed,CPU_seconds=cpu,observed_average_CPU_cores=cpu/max(elapsed,1e-30),resources=state,remaining_seconds=policy.remaining_seconds(ledger));new(OUT/'computation-receipt.json',receipt)
  print(json.dumps(receipt,ensure_ascii=False))
