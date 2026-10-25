"""One killable manufactured-stage then authenticated native GUI build child."""
import argparse,contextlib,hashlib,io,json,os,re,resource,sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/workspace/ngg-tis-task1');OWNER=Path('/dev/shm/task1-native-GUI-lite-r4-owner-20261025/source');MODEL=Path('/dev/shm/task1-native-GUI-lite-20261025/source');OUT=Path('/dev/shm/task1-native-GUI-lite-r4-20261025-run')
sys.path[:0]=[str(ROOT/'tools'),str(OWNER)]
import task1_bounded_continuation as b,task1_execution_policy as ep
from owner_contracts import validate_admission,validate_MFG,validate_summary
REMOTE='data-native/native-GUI-lite-r4-20261025/'

def req(ok,message):
 if not ok:raise ValueError(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for part in iter(lambda:f.read(1024**2),b''):h.update(part)
 return h.hexdigest()
def new(path,value):
 with Path(path).open('xb')as f:f.write((json.dumps(value,ensure_ascii=False,allow_nan=False,indent=2)+'\n').encode())
def read_pinned(path,digest):
 p=Path(path);req(p.is_file()and p==p.resolve()and not p.is_symlink()and p.stat().st_size<16*1024**2 and sha(p)==digest,'Bounded canonical controller metadata/fullSHA');return json.loads(p.read_bytes())
def identity(path):
 p=Path(path);req(p.is_absolute()and p.is_file()and p==p.resolve()and not p.is_symlink(),'Canonical immutable native/source input');s=p.stat();return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def owns(pid,path):
 wanted=path.stat();kinds=set()
 for fd in Path('/proc',str(pid),'fd').glob('*'):
  try:
   got=fd.stat()
   if(got.st_dev,got.st_ino)!=(wanted.st_dev,wanted.st_ino):continue
   for line in Path('/proc',str(pid),'fdinfo',fd.name).read_text().splitlines():
    if line.startswith('lock:')and(' '+str(pid)+' ')in line:
     if' FLOCK 'in line:kinds.add('FLOCK')
     if' POSIX 'in line:kinds.add('POSIX')
  except OSError:pass
 return kinds=={'FLOCK','POSIX'}
def controller(pid):
 req(Path('/proc',str(pid),'exe').resolve().name.startswith('python'),'Actual Python parent')
 argv=[v.decode()for v in Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')if v];at=1
 while at<len(argv)and argv[at].startswith('-'):
  req(argv[at]in('-B','-u','-E','-s','-S','-I','-O','-OO','-q','-R'),'Actual script parent, no -c/-m');at+=1
 req(at<len(argv),'Parent script argument');return(Path('/proc',str(pid),'cwd').resolve()/argv[at]).resolve()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--source',required=True);parser.add_argument('--as-limit',type=int,required=True)
 for name in('registration-sha','preregistration-sha','publication-sha','publication-plan-sha'):parser.add_argument('--'+name,required=True)
 args=parser.parse_args();out=Path(args.output);src=Path(args.source)
 req(args.as_limit==1200000000,'Preregistered1.2GB virtual address cap, not a RAM allocation');resource.setrlimit(resource.RLIMIT_AS,(args.as_limit,args.as_limit));limits=ep.resolve_limits();configured=ep.configure_process(limits)
 req(limits['cpu_limit']==4 and limits['total_memory_bytes']==8000000000 and limits['max_cells']==800000,'Exact unchanged execution limits')
 start=time.monotonic();deadline=start+1200;cpu0=time.process_time();lease=None;pins={};stats={};native_stats={};proofs={};state=None
 record=dict(schema='task1-native-GUI-lite-worker-v1',status='failed_preserved',new_PDE_RHS=0,new_Q_loads=0,new_eigen_solves=0,new_angular_evaluations=0,new_stat_reductions=0,browser_validation_performed=False,GUI_generated=False,candidate_adopted=False,stored_native_phase_started=False,configured=configured)
 def guard():
  req(time.monotonic()<deadline and not(out/'STOP').exists(),'Finite1200s child deadline/STOP')
  req(lease is not None,'Authenticated parent required');parent=lease['pid'];req(os.getppid()==parent and b.live(parent,lease['ticks']),'Actual parent PID/startticks')
  actual=controller(parent);req(actual==OWNER/'guardian.py'and sha(actual)==lease['controller_sha'],'Actual frozen parent controller')
  for name in('.task1-queue-owner.lock','.task1-loop.lock','.task1-execution.lock'):req(owns(parent,ROOT/name),'Parent owns both FLOCK/POSIX '+name)
  for p,digest in lease['metadata'].items():req(sha(p)==digest,'Frozen controller/publication metadata')
  for p,digest in pins.items():
   req(identity(p)==stats[p],'Frozen metadata/source stat changed')
   if stats[p][2]<=1024**2:req(sha(p)==digest,'Frozen small metadata/source SHA changed')
  for p,stat in native_stats.items():req(identity(p)==stat,'Native descriptor stat changed; no byte read in guard')
 def verify(stage):
  for p,digest in pins.items():guard();req(sha(p)==digest,'Complete before/after metadata/source SHA')
  proofs[stage]=dict(passed=True,count=len(pins),native_bytes_opened_by_verifier=False)
 try:
  req(out==OUT and out==out.resolve()and src==MODEL and Path(__file__).resolve()==out/'source/owner/worker.py','Exact new GUI frozen worker path')
  reg=read_pinned(out/'registration.json',args.registration_sha);pre=read_pinned(out/'preregistration.json',args.preregistration_sha);pub=read_pinned(out/'source-publication/result-publication.json',args.publication_sha);plan=read_pinned(out/'source-plan.json',args.publication_plan_sha)
  req(pub['status']=='published_readback_verified'and re.fullmatch('[0-9a-f]{40}',pub['commit'])and pub['remote_branch_head_verified']==pub['commit']and pub['expected_parent']==plan['expected_parent']and set(pub['files'])==set(plan['files']),'Actual exact source publication/readback before tests')
  for target,item in plan['files'].items():
   proof=pub['files'][target];req(proof['readback_passed']is True and proof['SHA256']==item['SHA256']and proof['bytes']==item['bytes']and sha(item['local_path'])==item['SHA256'],'Every published source/controller byte')
  for name in('registration.json','preregistration.json','spec.json','root-admission.json','test-source-inventory.json','native-descriptor-stat-registration.json','previous-preS-failure-proof.json'):req(pub['files'][REMOTE+name]['SHA256']==sha(out/name),'Exact published GUI metadata '+name)
  req(reg['source_sha256']==pre['source_sha256'],'Canonical source maps agree')
  admission=read_pinned(out/'root-admission.json',pre['root_admission_SHA256']);validate_admission(admission,pre['source_sha256'],pre['model_source_sha256'],pre['expected_owner_tests'])
  spec=read_pinned(out/'spec.json',pre['spec_SHA256']);req(spec['inputs']['root_admission']==admission==pre['root_decision'],'Exact actual-root GUI decision')
  numeric=json.loads((out/'numeric-admission.json').read_bytes());req(numeric['task_temp_accounting_roots']==['/dev/shm/task1-*','/tmp/task1-*']and numeric['task_temp_accounted_bytes']==numeric['task_shm_bytes']+numeric['task_tmp_aux_bytes'],'Both actual task temp roots counted without deletion')
  record['task_temporary_accounting_at_entry']={k:numeric[k]for k in('task_temp_accounting_roots','task_shm_bytes','task_tmp_aux_bytes','task_temp_accounted_bytes')}
  req(numeric['child_RLIMIT_AS_bytes']==args.as_limit and numeric['physical_forecast_bytes']<=numeric['physical_cap_bytes']==8000000000,'Actual whole-task memory forecast and unchanged cap')
  pins={**pre['source_sha256'],**pre['frozen_source_sha256'],**pre['metadata_input_sha256'],**pre['helper_sha256'],**pre['execution_policy_refs']};stats={p:identity(p)for p in pins}
  req(all(Path(p).suffix.lower()in('.py','.md','.json','.txt','.log')for p in pins),'No native archives in pre-MFG byte hash set')
  statdoc=read_pinned(out/'native-descriptor-stat-registration.json',pre['native_descriptor_stats_SHA256']);native_stats={p:tuple(v)for p,v in statdoc['files'].items()}
  lease=dict(pid=reg['supervisor_pid'],ticks=reg['proc_start_ticks'],controller_sha=reg['controller_sha256'],metadata={str(out/'registration.json'):args.registration_sha,str(out/'preregistration.json'):args.preregistration_sha,str(out/'source-publication/result-publication.json'):args.publication_sha,str(out/'source-plan.json'):args.publication_plan_sha,str(out/'spec.json'):pre['spec_SHA256'],str(out/'root-admission.json'):pre['root_admission_SHA256'],str(out/'test-source-inventory.json'):pre['test_inventory_SHA256'],str(out/'native-descriptor-stat-registration.json'):pre['native_descriptor_stats_SHA256'],str(out/'numeric-admission.json'):sha(out/'numeric-admission.json'),str(out/'previous-preS-failure-proof.json'):pre['previous_preS_failure_proof_SHA256']})
  prior=read_pinned(out/'previous-preS-failure-proof.json',pre['previous_preS_failure_proof_SHA256']);req(prior['old_source_publication_available']is False and prior['old_result_publication_available']is False and prior['old_native_phase_reached']is False,'Actual original pre-S failure has no invented old S/R/native outputs')
  guard();verify('before_MFG_metadata_only');record['actual_parent_authentication']=dict(pid=lease['pid'],startticks=lease['ticks'],three_dual_locks=True,source_publication_commit=pub['commit'])
  sys.path[:0]=[str(out/'source/owner'),str(out/'source/model')]
  import gui_build,gui_inputs,mfg_boundary
  req(spec==gui_build.make_spec(admission),'Exact metadata-only spec recreated under frozen modules; no __file__ source alias contamination')
  state=dict(manufactured_phase=True,scientific_API_spy_calls=[],native_IO_attempts=[],array_allocations=[],negative_fixture_counts={},IO_audit_installed=False)
  mfg_boundary.install_io_gate(state,{**pins,**lease['metadata']},out)
  import numpy as np
  import numpy.ma,numpy.fft,numpy.testing
  np.fft.rfft(np.asarray([0.,1.,0.,-1.]));np.testing.assert_allclose(np.asarray([1.]),np.asarray([1.]))
  record['dependencies_initialized_before_mocks']=dict(modules=['numpy.ma','numpy.fft','numpy.testing'],native_inputs_read=False,small_constant_library_initialization_only=True)
  events=[];current=[None];stream=io.StringIO();results={}
  class RecordingResult(unittest.TextTestResult):
   def startTest(self,test):guard();current[0]=test.id();super().startTest(test)
   def addSuccess(self,test):events.append(dict(test_id=test.id(),outcome='passed'));super().addSuccess(test)
   def addFailure(self,test,err):events.append(dict(test_id=test.id(),outcome='failed'));super().addFailure(test,err)
   def addError(self,test,err):events.append(dict(test_id=test.id(),outcome='error'));super().addError(test,err)
   def addSkip(self,test,reason):events.append(dict(test_id=test.id(),outcome='skipped',reason=reason));super().addSkip(test,reason)
   def stopTest(self,test):super().stopTest(test);current[0]=None;guard()
  expected_events=[]
  with contextlib.ExitStack()as stack:
   mfg_boundary.install_spies(stack,np,state,((gui_build,('build','load','verify','digest','_load')),(gui_inputs,('make_spec','required_inputs','metadata','_context','source_inventory'))),current)
   for namespace,directory in(('model',out/'source/model'),('owner',out/'source/owner')):
    modules=pre['test_inventory'][namespace+'_methods']
    for module,methods in modules.items():
     expected_events.extend(module+'.'+method for method in methods)
     suite=unittest.TestLoader().loadTestsFromName(module);result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordingResult).run(suite)
     prior=results.setdefault(namespace,dict(run=0,failures=0,errors=0,skipped=0));prior['run']+=result.testsRun;prior['failures']+=len(result.failures);prior['errors']+=len(result.errors);prior['skipped']+=len(result.skipped)
  with(out/'tests.log').open('x')as f:f.write(stream.getvalue())
  total=sum(v['run']for v in results.values());failed=sum(v['failures']for v in results.values());errors=sum(v['errors']for v in results.values());skipped=sum(v['skipped']for v in results.values());ok=failed==errors==skipped==0 and results['model']['run']==16 and results['owner']['run']==pre['expected_owner_tests']and not state['scientific_API_spy_calls']and not state['native_IO_attempts']
  mfg=dict(schema='task1-native-GUI-lite-manufactured-tests-v1',status='passed'if ok else'failed',source_publication_commit=pub['commit'],model_source_sha256=pre['model_source_sha256'],owner_source_sha256=pre['source_sha256'],source_sha256=pre['source_sha256'],model_source_test_count=16,model_tests_run=results['model']['run'],owner_tests_run=results['owner']['run'],tests_run=total,expected_total_tests=pre['expected_synthetic_tests'],tests_failed=failed,tests_errors=errors,tests_skipped=skipped,test_events=events,per_namespace=results,native_RHS=0,native_Q_loads=0,native_field_reads=0,native_eigen_solves=0,new_angular_evaluations=0,field_admission_granted=False,browser_validation_performed=False,candidate_adopted=False,scientific_API_spy_calls=state['scientific_API_spy_calls'],native_IO_attempts=state['native_IO_attempts'],array_allocations=state['array_allocations'],IO_audit_installed=state['IO_audit_installed'],negative_fixture_counts=state['negative_fixture_counts'],dependencies_initialized_before_mocks=True)
  new(out/'synthetic-test-receipt.json',mfg);record['actual_tests_run']=total;validate_MFG(mfg,pre['model_source_sha256'],pre['expected_owner_tests'],expected_events)
  receipt_path=str(out/'synthetic-test-receipt.json');pins[receipt_path]=sha(receipt_path);stats[receipt_path]=identity(receipt_path);lease['metadata'][receipt_path]=pins[receipt_path]
  state['manufactured_phase']=False;guard();verify('after_MFG_before_native_bytes');record['stored_native_phase_started']=True
  result=gui_build.build(spec,guard,deadline_monotonic=deadline,output_dir=out);summary=result['summary'];accounting=validate_summary(summary)
  req((out/'payload.json').stat().st_size==summary['payload_JSON_bytes']and(out/'index.html').stat().st_size==summary['index_HTML_bytes'],'Actual output sizes match summary')
  verify('after_native_GUI_build_metadata_only');new(out/'input-SHA-verification.json',proofs);new(out/'summary.json',summary)
  record.update(status='native_GUI_lite_built_browser_unverified',GUI_generated=True,build_accounting=accounting,index_HTML_SHA256=sha(out/'index.html'),payload_JSON_SHA256=sha(out/'payload.json'),actual_stored_native_inputs_read=True,browser_validation_performed=False)
 except BaseException as error:
  record.update(error_type=type(error).__name__,error=str(error),MFG_boundary=state,actual_native_bytes_may_have_been_read=record['stored_native_phase_started']);raise
 finally:
  record.update(elapsed_seconds=time.monotonic()-start,process_CPU_seconds=time.process_time()-cpu0,peak_worker_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,input_verification=proofs)
  new(out/'worker-receipt.json',record)
if __name__=='__main__':main()
