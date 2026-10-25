"""Finite synthetic_equipotential contact-boundary operator diagnostic, never full phantom."""
import argparse,hashlib,io,json,os,resource,sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1')
sys.path.insert(0,str(ROOT/'tools'))
import task1_execution_policy as ep

def new(p,d):
 with Path(p).open('x')as f:json.dump(d,f,ensure_ascii=False,allow_nan=False,indent=2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--source',required=True);ap.add_argument('--as-limit',type=int,required=True);args=ap.parse_args()
 out=Path(args.output);src=Path(args.source);resource.setrlimit(resource.RLIMIT_AS,(args.as_limit,args.as_limit));limits=ep.resolve_limits();settings=ep.configure_process(limits)
 sys.path.insert(0,str(src));started=time.monotonic();cpu0=time.process_time();rec=dict(schema='task1-contact-edge-Galerkin-worker-v1',status='failed_preserved',new_full_phantom_CEM=0,new_TIS=0,actual_Windows_saved=False,CPU_cap=limits['cpu_limit'])
 try:
  import weighted_dtn_mms as model
  prereg=json.loads((out/'preregistration.json').read_text())
  if sha(out/'spec.json')!=prereg['spec_SHA256']:raise ValueError('Published spec SHA mismatch')
  for name,digest in {**prereg['source_sha256'],**prereg['input_sha256']}.items():
   if sha(name)!=digest:raise ValueError('Frozen synthetic_equipotential source/input SHA mismatch')
  spec=json.loads((out/'spec.json').read_text());deadline=time.monotonic()+100
  def guard():
   if time.monotonic()>deadline:raise TimeoutError('Finite synthetic_equipotential child deadline')
  stream=io.StringIO();suite=unittest.defaultTestLoader.discover(str(src),pattern='test_*.py');tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'tests.log').write_text(stream.getvalue());rec['test_count']=tests.testsRun
  if not tests.wasSuccessful():raise ValueError('Manufactured operator contracts failed')
  result=model.build(spec,guard,deadline_monotonic=deadline,output_dir=out)
  new(out/'summary.json',result['summary'])
  import numpy as np
  with(out/'arrays.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
  try:
   from threadpoolctl import threadpool_info
   new(out/'threadpool-runtime.json',threadpool_info())
  except ImportError:new(out/'threadpool-runtime.json',dict(status='not_available_no_install'))
  rec.update(status='synthetic_equipotential_contact_boundary_diagnostic_computed',summary_SHA256=sha(out/'summary.json'),arrays_SHA256=sha(out/'arrays.npz'),scope='Six separate forced periodic rectangle weighted-DtN Fourier-MMS conditions, no actualcircle/electrode CEM or E/TIS/physiology validation')
 except BaseException as error:
  rec.update(error_type=type(error).__name__,error=str(error));raise
 finally:
  elapsed=time.monotonic()-started;cpu=time.process_time()-cpu0;rec.update(elapsed_seconds=elapsed,process_CPU_seconds=cpu,average_process_CPU_cores=cpu/max(elapsed,1e-30),peak_worker_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024);new(out/'worker-receipt.json',rec)
if __name__=='__main__':main()
