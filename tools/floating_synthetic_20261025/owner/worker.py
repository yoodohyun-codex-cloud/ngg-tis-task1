"""One killable synthetic-only child. No field admission or dataset API calls."""
import argparse,contextlib,hashlib,io,json,os,re,resource,sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_execution_policy as ep
import task1_bounded_continuation as b
from owner_contracts import SUITES,validate_test_receipt
REMOTE='data-native/floating-synthetic-20261025/'
OWNER=Path('/dev/shm/task1-floating-synthetic-owner-20261025/source')
OUT=Path('/dev/shm/task1-floating-synthetic-20261025-run')

def req(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as stream:
  for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def new(path,value):
 raw=(json.dumps(value,allow_nan=False,indent=2)+'\n').encode()
 with Path(path).open('xb')as stream:stream.write(raw)
def read_pinned(path,expected):
 path=Path(path);req(path.is_file()and not path.is_symlink()and path.stat().st_size<8*1024**2 and sha(path)==expected,'Frozen controller metadata SHA');return json.loads(path.read_text())
def identity(path):
 p=Path(path);req(p.is_file()and not p.is_symlink(),'Frozen regular source');s=p.stat();return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
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
def controller(pid):
 req(Path('/proc',str(pid),'exe').resolve().name.startswith('python'),'Actual Python parent')
 argv=[x.decode()for x in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')if x];i=1
 while i<len(argv)and argv[i].startswith('-'):
  req(argv[i]in('-B','-u','-E','-s','-S','-I','-O','-OO','-q','-R'),'No -c/-m parent spoofing');i+=1
 req(i<len(argv),'Actual parent script');return(Path('/proc',str(pid),'cwd').resolve()/argv[i]).resolve()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
 for key in('registration-sha','preregistration-sha','publication-sha','publication-plan-sha'):parser.add_argument('--'+key,required=True)
 args=parser.parse_args();out=Path(args.output);resource.setrlimit(resource.RLIMIT_AS,(1000000000,1000000000));limits=ep.resolve_limits();configured=ep.configure_process(limits)
 req(limits['cpu_limit']==4 and limits['total_memory_bytes']==8000000000 and limits['max_cells']==800000,'Unchanged CPU/RAM/cell policy')
 start=time.monotonic();cpu0=time.process_time();deadline=start+180;record=dict(status='failed_preserved',kind='synthetic_test_worker',native_RHS=0,field_admission_granted=False,configured=configured);lease=None;pins={};stats={};verification={}
 def guard():
  req(time.monotonic()<deadline and not(out/'STOP').exists(),'Finite180s synthetic child deadline/STOP')
  req(lease is not None,'Authenticated numerical owner required');parent=lease['pid'];req(os.getppid()==parent and b.live(parent,lease['ticks']),'Actual live parent PID/startticks')
  actual=controller(parent);req(actual==OWNER/'guardian.py'and sha(actual)==lease['controller_sha'],'Actual frozen parent script')
  for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):req(owns(parent,ROOT/name),'Actual parent both FLOCK and POSIX '+name)
  for path,expected in lease['metadata'].items():req(sha(path)==expected,'Frozen registration/publication changed')
  for path,expected in pins.items():req(identity(path)==stats[path]and sha(path)==expected,'Frozen synthetic source changed')
 def verify(stage):
  for path,expected in pins.items():guard();req(sha(path)==expected,'Complete before/after synthetic source SHA')
  verification[stage]=dict(passed=True,count=len(pins))
 try:
  req(out==OUT and out==out.resolve()and Path(__file__).resolve()==out/'source/owner/worker.py','Exact unique frozen worker output')
  registration=read_pinned(out/'registration.json',args.registration_sha);prereg=read_pinned(out/'preregistration.json',args.preregistration_sha);publication=read_pinned(out/'source-publication/result-publication.json',args.publication_sha);plan=read_pinned(out/'source-plan.json',args.publication_plan_sha)
  req(publication['status']=='published_readback_verified'and publication['expected_parent']==plan['expected_parent']and publication['remote_branch_head_verified']==publication['commit']and set(publication['files'])==set(plan['files']),'Exact independently-readback source publication')
  for target,item in plan['files'].items():
   proof=publication['files'][target];req(proof['readback_passed']is True and proof['SHA256']==item['SHA256']and proof['bytes']==item['bytes']and sha(item['local_path'])==item['SHA256'],'Full published source/input bytes')
  for name in('registration.json','preregistration.json','test-source-inventory.json'):
   proof=publication['files'][REMOTE+name];req(proof['SHA256']==sha(out/name)and proof['readback_passed']is True,'Actual published controller metadata')
  pins={**prereg['source_sha256'],**prereg['frozen_source_sha256'],**prereg['helper_sha256'],**prereg['execution_policy_refs']};stats={p:identity(p)for p in pins}
  req(registration['source_sha256']==prereg['source_sha256'],'Controller/preregistration source agreement')
  lease=dict(pid=registration['supervisor_pid'],ticks=registration['proc_start_ticks'],controller_sha=registration['controller_sha256'],metadata={str(out/'registration.json'):args.registration_sha,str(out/'preregistration.json'):args.preregistration_sha,str(out/'source-publication/result-publication.json'):args.publication_sha,str(out/'source-plan.json'):args.publication_plan_sha,str(out/'test-source-inventory.json'):prereg['test_inventory_SHA256']})
  guard();verify('before_tests');sys.path.insert(0,str(out/'source/proposal'));sys.path.insert(0,str(out/'source/owner'))
  from unittest.mock import patch
  # Imports only define stdlib-only APIs. Explicitly prohibit all field/input work.
  import p23_inputs,p23_comparison,frozen_coarse_cem,frozen_layer_dtn_backend
  forbidden=[]
  def blocked(name):
   def call(*args,**kwargs):forbidden.append(name);raise AssertionError('Synthetic-only boundary: forbidden field/input API '+name)
   return call
  suite_records=[];all_events=[];total_run=failed=errors=skipped=0
  with contextlib.ExitStack()as stack:
   for module,names in((p23_inputs,('make_spec','required_inputs','source_inventory','read_json','canonical','digest')),(p23_comparison,('make_spec','required_inputs','build','_raw_stage','_raw_frame','_context','_dependencies','_load','_authenticate_alias_files')),(frozen_coarse_cem,('_phase1_metadata','_load_cache','required_inputs','make_spec','build')),(frozen_layer_dtn_backend,('required_inputs','make_spec','build','_graph'))):
    for name in names:
     if hasattr(module,name):stack.enter_context(patch.object(module,name,blocked(module.__name__+'.'+name)))
   class RecordingResult(unittest.TextTestResult):
    def startTest(self,test):guard();super().startTest(test)
    def addSuccess(self,test):all_events.append(dict(test_id=test.id(),outcome='passed'));super().addSuccess(test)
    def addFailure(self,test,err):all_events.append(dict(test_id=test.id(),outcome='failed'));super().addFailure(test,err)
    def addError(self,test,err):all_events.append(dict(test_id=test.id(),outcome='error'));super().addError(test,err)
    def addSkip(self,test,reason):all_events.append(dict(test_id=test.id(),outcome='skipped',reason=reason));super().addSkip(test,reason)
    def stopTest(self,test):super().stopTest(test);guard()
   for module_name in SUITES:
    stream=io.StringIO();suite=unittest.TestLoader().loadTestsFromName(module_name);result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordingResult).run(suite)
    with(out/('tests-'+module_name+'.log')).open('x')as handle:handle.write(stream.getvalue())
    row=dict(suite=module_name,tests_run=result.testsRun,tests_failed=len(result.failures),tests_errors=len(result.errors),tests_skipped=len(result.skipped));suite_records.append(row);total_run+=row['tests_run'];failed+=row['tests_failed'];errors+=row['tests_errors'];skipped+=row['tests_skipped']
   # Owner metadata contracts are separate from the 15 principal MNA tests.
   stream=io.StringIO();owner_result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestLoader().loadTestsFromName('test_owner_contracts'))
   with(out/'tests-owner.log').open('x')as handle:handle.write(stream.getvalue())
  guard();verify('after_tests');owner_ok=owner_result.wasSuccessful()and owner_result.testsRun==prereg['expected_owner_tests']and not owner_result.skipped
  passed=failed==errors==skipped==0 and total_run==prereg['expected_principal_tests']and not forbidden and owner_ok
  receipt=dict(status='passed'if passed else'failed',kind='actual_small_synthetic_matrix_algebra_only',tests_run=total_run,tests_failed=failed,tests_errors=errors,tests_skipped=skipped,suites=list(SUITES),suite_results=suite_records,test_events=all_events,source_sha256=prereg['proposal_source_sha256'],source_publication_commit=publication['commit'],native_RHS=0,native_field_reads=0,native_Q_loaded=False,native_eigen_performed=False,field_admission_granted=False,forbidden_field_calls=forbidden,owner_tests_run=owner_result.testsRun,owner_tests_passed=owner_ok,actual_hardware_wiring_changed=False,meaning='Tiny synthetic MNA/algebra only; no phantom field/GMRES/activation/safety validation')
  new(out/'synthetic-test-receipt.json',receipt);validate_test_receipt(receipt,prereg['expected_principal_tests'],prereg['proposal_source_sha256']);new(out/'input-SHA-verification.json',verification);record.update(status='synthetic_tests_executed',test_receipt_SHA256=sha(out/'synthetic-test-receipt.json'),principal_tests_passed=passed)
 except BaseException as error:record.update(error_type=type(error).__name__,error=str(error));raise
 finally:
  elapsed=time.monotonic()-start;record.update(elapsed_seconds=elapsed,process_CPU_seconds=time.process_time()-cpu0,peak_worker_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,source_verification=verification);new(out/'worker-receipt.json',record)
if __name__=='__main__':main()
