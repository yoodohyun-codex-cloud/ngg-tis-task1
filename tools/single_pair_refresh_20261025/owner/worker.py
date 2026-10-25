"""Finite single-pair child; immutable published P23 TIS is never re-solved."""
import argparse,hashlib,io,json,os,re,resource,sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_execution_policy as ep
import task1_bounded_continuation as b
from owner_contracts import validate_single_pair_summary
REMOTE='data-native/single-pair-refresh-20261025/'
def new(path,value):
 raw=(json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
 return h.hexdigest()
def req(ok,message):
 if not ok:raise ValueError(message)
def read_pinned(path,expected):
 path=Path(path);req(path.is_file()and not path.is_symlink()and path.stat().st_size<2*1024**2,'Canonical bounded controller metadata')
 req(sha(path)==expected,'Expected controller metadata SHA '+str(path));return json.loads(path.read_text())
def identity(path):
 path=Path(path);req(path.is_file()and not path.is_symlink(),'Canonical immutable input '+str(path));s=path.stat()
 return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def virtual_peak_bytes():
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith('VmPeak:'):return int(line.split()[1])*1024
 except OSError:pass
 return None
def owns(pid,path):
 wanted=path.stat();kinds=set()
 for fd in Path('/proc',str(pid),'fd').glob('*'):
  try:
   actual=fd.stat()
   if(actual.st_dev,actual.st_ino)!=(wanted.st_dev,wanted.st_ino):continue
   for line in Path('/proc',str(pid),'fdinfo',fd.name).read_text().splitlines():
    if line.startswith('lock:')and(' '+str(pid)+' ')in line:
     if' FLOCK 'in line:kinds.add('FLOCK')
     if' POSIX 'in line:kinds.add('POSIX')
  except OSError:pass
 return kinds=={'FLOCK','POSIX'}
def actual_controller(pid):
 req(Path('/proc',str(pid),'exe').resolve().name.startswith('python'),'Actual parent must be Python')
 argv=[v.decode()for v in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')if v]
 req(argv and Path(argv[0]).name.startswith('python'),'Actual Python command required');at=1
 while at<len(argv)and argv[at].startswith('-'):
  if argv[at]=='--':at+=1;break
  req(argv[at]in('-B','-u','-E','-s','-S','-I','-O','-OO','-q','-R'),'Actual script required; no -c/-m spoofing');at+=1
 req(at<len(argv),'Actual controller script argument required')
 return(Path('/proc',str(pid),'cwd').resolve()/argv[at]).resolve()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--source',required=True);parser.add_argument('--as-limit',type=int,required=True)
 for name in('registration-sha','preregistration-sha','publication-sha','publication-plan-sha'):parser.add_argument('--'+name,required=True)
 args=parser.parse_args()
 out=Path(args.output);src=Path(args.source)
 if args.as_limit!=1600000000:raise ValueError('Preregistered finite1.6GB address-space cap required; this is not a RAM allocation')
 resource.setrlimit(resource.RLIMIT_AS,(args.as_limit,args.as_limit));limits=ep.resolve_limits();configured=ep.configure_process(limits)
 sys.path.insert(0,str(src));started=time.monotonic();cpu0=time.process_time();deadline=started+1200
 record=dict(schema='task1-memory-separated-single-pair-refresh-worker-v1',status='failed_preserved',maximum_new_driven_RHS=2,connected_sources_per_condition=1,physical_pads_per_condition=2,GUI_generated=False,new_eigen_solves=0,new_native_FVM_RHS=0,candidate_adopted=False,actual_Windows_saved=False,CPU_cap=limits['cpu_limit'],configured=configured)
 proofs={};lease=None;pins={};stats={}
 def guard():
  if time.monotonic()>=deadline:raise TimeoutError('Finite1200s single-pair-refresh calculation deadline')
  if(out/'STOP').exists():raise InterruptedError('Explicit STOP marker')
  req(lease is not None,'Authenticated actual numerical owner required')
  parent=lease['parent_pid'];tick=lease['parent_ticks']
  req(os.getppid()==parent and b.live(parent,tick),'Actual parent PID/startticks changed')
  controller=actual_controller(parent)
  req(controller==Path('/dev/shm/task1-single-pair-refresh-owner-20261025/source/guardian.py')and str(controller)==lease['controller_path']and sha(controller)==lease['controller_sha256'],'Actual frozen parent controller changed')
  for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):req(owns(parent,ROOT/name),'Actual parent must own both FLOCK and POSIX '+name)
  for path,expected in lease['metadata_pins'].items():req(sha(path)==expected,'Registered publication/preregistration metadata changed '+path)
  for path,expected in pins.items():
   ident=identity(path);req(ident==stats[path],'Frozen source/input stat changed '+path)
   if ident[2]<=1024**2:req(sha(path)==expected,'Frozen small source/input SHA changed '+path)
 def verify(pins,stage):
  for path,expected in pins.items():
   guard()
   if sha(path)!=expected:raise ValueError('Frozen source/input SHA mismatch '+path)
  proofs[stage]=dict(passed=True,count=len(pins))
 try:
  req(out==Path('/dev/shm/task1-single-pair-refresh-20261025-run')and out==out.resolve(),'Exact registered design output')
  req(src==out/'source/model'and Path(__file__).resolve()==out/'source/owner/worker.py','Exact frozen worker/model namespaces')
  registration=read_pinned(out/'registration.json',args.registration_sha);prereg=read_pinned(out/'preregistration.json',args.preregistration_sha)
  publication=read_pinned(out/'source-publication/result-publication.json',args.publication_sha);plan=read_pinned(out/'source-plan.json',args.publication_plan_sha)
  parent=registration['supervisor_pid'];tick=registration['proc_start_ticks']
  req(type(parent)is int and type(tick)is int and registration['schema']=='task1-finite-native-continuation-registration-v1','Explicit finite actual-parent identity')
  req(publication['status']=='published_readback_verified'and re.fullmatch('[0-9a-f]{40}',publication['commit'])and publication['remote_branch_head_verified']==publication['commit'],'Verified immutable source-publication required')
  req(publication['expected_parent']==plan['expected_parent']and set(publication['files'])==set(plan['files']),'Exact published source/input file set and expected parent')
  for target,item in plan['files'].items():
   proof=publication['files'][target]
   req(proof['readback_passed']is True and proof['SHA256']==item['SHA256']and proof['bytes']==item['bytes']and sha(item['local_path'])==item['SHA256'],'Exact published source/input readback '+target)
  for name in('registration.json','preregistration.json','spec.json','test-source-inventory.json','root-admission.json'):
   proof=publication['files'][REMOTE+name]
   req(proof['readback_passed']is True and proof['SHA256']==sha(out/name),'Actual published controller/input bytes '+name)
  pins={**prereg['source_sha256'],**prereg['frozen_source_sha256'],**prereg['input_sha256']};stats={path:identity(path)for path in pins}
  req(sha(out/'spec.json')==prereg['spec_SHA256'],'Published spec SHA mismatch')
  req(sha(out/'test-source-inventory.json')==prereg['test_inventory_SHA256'],'Exact preregistered test inventory')
  req(sha(out/'root-admission.json')==prereg['root_admission_SHA256'],'Exact positive single-pair root decision')
  req(prereg['resource_forecast']['fixed_child_RLIMIT_AS_bytes']==args.as_limit,'Unchanged preregistered virtual-address limit')
  numerical=json.loads((out/'numeric-admission.json').read_text());req(numerical['child_RLIMIT_AS_bytes']==args.as_limit and numerical['physical_forecast_bytes']<=numerical['aggregate_cap_bytes']==limits['total_memory_bytes']==8000000000 and limits['cpu_limit']==4 and limits['max_cells']==800000,'Actual unchanged physical budget admission and distinct virtual cap')
  req(registration['source_sha256']==prereg['source_sha256'],'Controller and calculation frozen sources agree')
  lease=dict(parent_pid=parent,parent_ticks=tick,controller_path=registration['controller_path'],controller_sha256=registration['controller_sha256'],
   metadata_pins={str(out/'registration.json'):args.registration_sha,str(out/'preregistration.json'):args.preregistration_sha,str(out/'spec.json'):prereg['spec_SHA256'],str(out/'root-admission.json'):prereg['root_admission_SHA256'],str(out/'test-source-inventory.json'):prereg['test_inventory_SHA256'],str(out/'source-publication/result-publication.json'):args.publication_sha,str(out/'source-plan.json'):args.publication_plan_sha,str(out/'numeric-admission.json'):sha(out/'numeric-admission.json')})
  guard();record['actual_parent_authentication']=dict(parent_pid=parent,parent_start_ticks=tick,three_dual_locks=True,source_publication_commit=publication['commit'],exact_source_input_readback_verified=True)
  verify(pins,'before_tests_and_build')
  import single_pair_refresh as model
  spec=json.loads((out/'spec.json').read_text())
  admission=json.loads((out/'root-admission.json').read_text());req(admission==prereg['root_decision']==spec['admission'],'Published root decision and centred-y0 single-pair specification agree')
  req(spec==model.make_spec(admission),'Exact selected-TIS/body/material/contact/source provenance before numerical work')
  stream=io.StringIO();suite=unittest.TestSuite()
  for directory in(src,out/'source/owner'):suite.addTests(unittest.TestLoader().discover(str(directory),pattern='test_*.py',top_level_dir=str(directory)))
  tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
  with(out/'tests.log').open('x')as handle:handle.write(stream.getvalue())
  record['test_count']=tests.testsRun
  if not tests.wasSuccessful()or tests.testsRun!=prereg['expected_synthetic_tests']:raise ValueError('Actual test count must equal prospectively published source-AST count')
  guard();result=model.build(spec,guard,deadline_monotonic=deadline,output_dir=out)
  summary=result['summary']
  accounting=validate_single_pair_summary(summary)
  for row in summary['Q_release_boundaries']:
   release=json.loads((out/(row['candidate_id']+'-Q-release-boundary.json')).read_text())
   req(release==row and release['raw_frame_returned']is True and release['Q_passed_to_metrics']is False,'Persisted per-case Q release before RMS metrics')
  verify(pins,'after_build');new(out/'input-SHA-verification.json',proofs)
  req((out/'summary.json').is_file()and json.loads((out/'summary.json').read_text())==summary,'Model-written complete summary must exactly match returned result; never overwrite')
  try:
   from threadpoolctl import threadpool_info
   new(out/'threadpool-runtime.json',threadpool_info())
  except ImportError:new(out/'threadpool-runtime.json',dict(status='not_available_no_install'))
  record.update(status='single_pair_comparison_computed',summary_SHA256=sha(out/'summary.json'),single_pair_accounting=accounting,
   scope='Two new centred-y0 single-pair2000Hz physical RHS, one connected source/two physical pads each; centre and targetvolume RMS matches distinct; no modulation/activation equivalence or fullconvergence/hardware/experiment claim; JSON/raw results only')
 except BaseException as error:
  record.update(error_type=type(error).__name__,error=str(error));raise
 finally:
  elapsed=time.monotonic()-started;cpu=time.process_time()-cpu0;record.update(elapsed_seconds=elapsed,process_CPU_seconds=cpu,average_process_CPU_cores=cpu/max(elapsed,1e-30),peak_worker_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,actual_worker_VmPeak_bytes=virtual_peak_bytes(),input_verification=proofs)
  new(out/'worker-receipt.json',record)
if __name__=='__main__':main()
