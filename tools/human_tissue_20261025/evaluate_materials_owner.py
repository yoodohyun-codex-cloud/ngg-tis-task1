import os,sys,json,time,hashlib,signal,csv,resource
from pathlib import Path
ROOT=Path('/workspace/ngg-tis-task1');SOURCE=Path('/dev/shm/task1-human-tissue-20261025/source');OUT=SOURCE.parent
sys.path[:0]=[str(ROOT/'tools'),str(SOURCE)]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,o):
 with p.open('x')as f:json.dump(o,f,ensure_ascii=False,allow_nan=False,indent=2)
with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
 start=time.monotonic();ledgerpath=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledgerpath);assert policy.remaining_seconds(ledger)>=855
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});signal.signal(signal.SIGALRM,lambda a,b:(_ for _ in()).throw(TimeoutError('finite material30s')));signal.setitimer(signal.ITIMER_REAL,30)
 refs={str(p):sha(p)for p in SOURCE.glob('evidence-*.json')};refs[str(SOURCE/'material_eval.py')]=sha(SOURCE/'material_eval.py')
 save(OUT/'material-evaluation-preregistration.json',dict(schema='task1-human-material-evaluation-v1',source_SHA256=refs,source_script_SHA256=sha(Path(__file__)),cap_seconds=30,new_PDE=0,scope='Source-verified declared substitutes only; no region-specific human material claim',CPU=1,storage_capacity_guards_enabled=False))
 status='failed_preserved';error=None
 try:
  import material_eval
  result=material_eval.build(read(SOURCE/'evidence-skin.json'),read(SOURCE/'evidence-kangasmaa.json'),read(SOURCE/'evidence-gabriel.json'))
  save(SOURCE/'material-input.json',result['receipt']);save(SOURCE/'material-function-audit.json',result['audit'])
  with (SOURCE/'material-input-table.csv').open('x',newline='')as f:
   writer=csv.DictWriter(f,fieldnames=['layer','frequency_Hz','sigma_S_m','epsilon_r','gamma_real_S_m','gamma_imag_S_m','assignment_type','source_id','source_location','temperature_C','numerical_uncertainty_interval','limitation']);writer.writeheader()
   for row in result['audit']['rows']:writer.writerow({k:row[k]for k in writer.fieldnames})
  assert all(sha(Path(p))==h for p,h in refs.items())
  status='source_functions_evaluated_declared_surrogate_inputs_fixed'
  display=[dict(layer=r['layer'],frequency_Hz=r['frequency_Hz'],sigma_S_m=r['sigma_S_m'],epsilon_r=r['epsilon_r'],gamma_imag_S_m=r['gamma_imag_S_m'])for r in result['receipt']['rows']]
  print(json.dumps(display))
 except BaseException as exc:error=str(exc);raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-start;ledger=policy.load_ledger(ledgerpath);ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id='task1-human-tissue-20261025',stage='source_material_function_evaluation',status=status,seconds=elapsed,error=error,finished_utc=bounded.now()))
  raw=json.dumps(ledger,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();temp=ledgerpath.with_name('task1-budget-human-material.tmp')
  with temp.open('xb')as f:f.write(raw)
  os.replace(temp,ledgerpath)
  save(OUT/'material-evaluation-receipt.json',dict(status=status,elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),error=error,new_PDE=0,input_material_SHA256=sha(SOURCE/'material-input.json')if(SOURCE/'material-input.json').exists()else None,RSS_peak_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,storage_capacity_guards_enabled=False))
