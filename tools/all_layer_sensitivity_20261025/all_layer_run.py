#!/usr/bin/env python3
"""One finite owner for a preregistered four-layer assumption sensitivity.

No work occurs on import. Preparation, publication, execution and postprocessing
are separate explicit stages. The old numerical sources and all run evidence
remain unchanged. No installation, deletion, budget expansion or main merge.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,base64,hashlib,json,os,re,shutil,signal,subprocess,threading,time
from pathlib import Path
for key in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-all-layer-sensitivity-20261025/source')
RUN=Path('/dev/shm/task1-all-layer-sensitivity-20261025-run')
CASE='baseline-square15-sc-eps1100-xy80'
SCHEMA='task1-whole-layer-sensitivity-native-v1'
JAVA_HOME=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
JAVA=JAVA_HOME/'java';JAVAC=JAVA_HOME/'javac'
LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='9cde5e1bfb95afa5c8383eb87cb4efd1e5bd4f75'
PUBLIC_RUN='data-native/cloud-all-layer-sc-epsilon-sensitivity-20261025'
PUBLIC_SOURCE='tools/all_layer_sensitivity_20261025'
PUBLIC_REPORT='docs/TASK1_ALL_LAYER_SENSITIVITY_20261025'
GIB=1024**3;MAX_RUN=768*1024**2;MAX_BLOB=64*1024**2;MAX_STDOUT=96*1024**2
CAPS={'prepare':90,'publish-source':120,'execute':600,'postprocess':600,'publish-results':360}
RESERVE={'prepare':1770,'publish-source':1680,'execute':1560,'postprocess':960,'publish-results':360}
NATIVE_GATES={'max_residual':2e-7,'max_power_error':2e-7,'max_current_error':2e-6,'max_area_relative_error':1e-10,'max_interface_normal_current_relative_error':2e-7}
sys.path[:0]=[str(SOURCE),str(ROOT/'tools'),str(ROOT/'tis-java')]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def new_json(path,obj):
    with Path(path).open('x',encoding='utf-8')as stream:json.dump(obj,stream,ensure_ascii=False,allow_nan=False,indent=2)
def mutable_json(path,obj):
    # Operational checkpoint only. Immutable source/registration/results use x.
    path=Path(path);temp=path.with_name(path.name+'.new')
    with temp.open('x',encoding='utf-8')as stream:json.dump(obj,stream,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    os.replace(temp,path)
def size(path):
    p=Path(path)
    if not p.exists():return 0
    if p.is_file():return p.stat().st_size
    total=0
    for item in p.rglob('*'):
        try:
            if item.is_file():total+=item.stat().st_size
        except FileNotFoundError:pass
    return total
def source_files():
    files={p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.java','.md','.json')}
    files.update(ROOT/'tis-java'/n for n in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'))
    files.update((ROOT/'tis-java').glob('*.py'))
    files.update(ROOT/'tools'/n for n in('task1_bounded_continuation.py','task1_resource_policy.py'))
    return {str(p):sha(p)for p in sorted(files)}
def required_old_inputs():
    import whole_layer_post as post
    import all_layer_inputs as inputs
    refs=post.required_inputs()
    refs[str(inputs.TEMPLATE)]=inputs.TEMPLATE_SHA256;refs[str(inputs.MASK)]=inputs.MASK_SHA256
    evidence=SOURCE/'material_evidence.py'
    if evidence.is_file():
        import material_evidence
        refs.update(material_evidence.required_inputs())
    return refs
def source_guard(pre,guard):
    require(pre['source_sha256']==source_files(),'Preregistered source set or bytes changed')
    for path,digest in {**pre['class_sha256'],**pre['old_input_sha256']}.items():guard();require(sha(path)==digest,'Pinned class/old input changed: '+path)
    require(sha(pre['config_file'])==pre['config_sha256']and sha(pre['mask_file'])==pre['mask_sha256'],'New registered config or mask changed')

def main():
    parser=argparse.ArgumentParser();flags=parser.add_mutually_exclusive_group(required=True)
    for name in CAPS:flags.add_argument('--'+name,action='store_true',dest=name.replace('-','_'))
    parser.add_argument('--output',default=str(RUN));args=parser.parse_args()
    stage=next(name for name in CAPS if getattr(args,name.replace('-','_')))
    require(Path(args.output)==RUN and RUN==RUN.absolute()and RUN.parent==Path('/dev/shm'),'Exact registered unique run path required')
    require(Path(__file__).resolve()==SOURCE/'all_layer_run.py','Exact frozen controller path required')
    receiptpath=RUN/(stage+'-receipt.json')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);remaining=policy.remaining_seconds(ledger)
        require(remaining>=RESERVE[stage],'Finite first-batch reservation requires '+str(RESERVE[stage])+'s; remaining '+str(remaining))
        require(not receiptpath.exists(),'Immutable stage receipt exists; preserve evidence and review recovery explicitly')
        require(all(p.is_file()and os.access(p,os.X_OK)for p in(JAVA,JAVAC))and shutil.which('setpriv'),'Existing JDK21/setpriv required; no installation')
        if stage=='prepare':
            require(not RUN.exists(),'Preparation needs a genuinely new run; preserve existing attempt')
            require(shutil.disk_usage('/dev/shm').free>=MAX_RUN+256*1024**2,'tmpfs new-run plus bounded scratch admission')
            RUN.mkdir()
            for name in('configs','masks','bases','classes','logs','tmp','postprocess'):(RUN/name).mkdir()
        else:require(RUN.is_dir()and RUN==RUN.resolve()and not RUN.is_symlink(),'Canonical existing registered tmpfs run')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});pid=os.getpid();ticks=bounded.ticks(pid);start=time.monotonic();deadline=start+CAPS[stage]
        state={'owned':{pid:ticks},'peak_RSS':0,'peak_owned_tmpfs':0,'peak_accounted':0,'phase':stage};stop=threading.Event()
        receipt={'schema':'task1-all-layer-finite-stage-v1','stage':stage,'status':'failed_preserved','started_utc':bounded.now(),'pid':pid,'proc_start_ticks':ticks,
            'run_id':RUN.name,'case_id':CASE,'remaining_before_seconds':remaining,'stage_cap_seconds':CAPS[stage],'new_native_conditions_started':0,'new_native_conditions_completed':0,
            'evidence_backed_material_reset':'deferred_missing_independent_skin_and_carrier_material_data','scenario':'explicit uncalibrated four-layer SC-permittivity sensitivity'}
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);owned=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));run_bytes=size(RUN)
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],owned),peak_accounted=max(state['peak_accounted'],rss+owned))
            require(time.monotonic()<deadline,'Finite stage deadline exhausted')
            require(rss+owned<=3*GIB and run_bytes<=MAX_RUN,'Original RSS+all-owned-tmpfs3GiB / registered run768MiB gate')
            require(shutil.disk_usage(ROOT).free>=2*GIB+LEDGER.stat().st_size+8192,'Original2GiB plus compact atomic-ledger reserve')
            for marker in('STOP','needs_attention','needs_physical_validation'):require(not(RUN/marker).exists(),'Run blocked by '+marker)
        def interrupt(sig,frame):raise TimeoutError(state.get('failure','Finite stage interrupted'))
        def monitor():
            last=0.
            while not stop.wait(1):
                try:
                    guard()
                    if time.monotonic()-last>5:
                        mutable_json(RUN/'heartbeat.json',dict(stage=stage,phase=state['phase'],pid=pid,proc_start_ticks=ticks,updated_utc=bounded.now(),elapsed_seconds=time.monotonic()-start))
                        last=time.monotonic()
                except BaseException as error:state['failure']=str(error);os.kill(pid,signal.SIGTERM);return
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in previous:signal.signal(sig,interrupt)
        signal.setitimer(signal.ITIMER_REAL,CAPS[stage]);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,body=None,log=None):
            guard();stream=None
            failure=None
            if log is not None:stream=Path(log).open('xb')
            child=subprocess.Popen([str(a)for a in argv],cwd=ROOT,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,
                stdout=stream if stream is not None else subprocess.PIPE,stderr=subprocess.STDOUT if stream is not None else subprocess.PIPE,start_new_session=True,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(RUN/'tmp'),TMP=str(RUN/'tmp'),TEMP=str(RUN/'tmp')))
            state['owned'][child.pid]=bounded.ticks(child.pid)
            if str(JAVA)in [str(a)for a in argv]:state['java_pid']=child.pid;state['java_startticks']=state['owned'][child.pid]
            try:
                stdout,stderr=child.communicate(input=body,timeout=max(.01,deadline-time.monotonic()))
                stdout=stdout or b'';stderr=stderr or b''
                require(len(stdout)<=MAX_STDOUT and len(stderr)<=4*1024**2,'Bounded subprocess output')
                if child.returncode!=0 and log is None:
                    failure=RUN/'logs'/('failed-'+stage+'-'+str(child.pid)+'.log')
                    with failure.open('xb')as f:f.write(stdout+stderr)
                require(child.returncode==0,'Command exit '+str(child.returncode)+'; see preserved '+str(log or failure or 'subprocess output'))
                return stdout
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
                if stream is not None:stream.close()
                state.pop('java_pid',None);state.pop('java_startticks',None)
        def api(endpoint,obj=None,method='GET'):
            argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            data=None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()
            try:return json.loads(command(argv,data))
            except Exception:
                # One readonly retry; mutation errors are never retried blindly.
                if method!='GET':raise
                guard();return json.loads(command(argv,data))
        def publish(files,parent,message):
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Remote advanced; no overwrite or force update')
            base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,path in files.items():
                guard();p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_BLOB,'Regular bounded64MiB publication file')
                raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                record=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');require(record['sha']==blob,'Exact Gitblob identity')
                entries.append(dict(path=target,mode='100644',type='blob',sha=blob));proof[target]=dict(SHA256=h,bytes=len(raw),Git_blob_SHA=blob)
                del raw
            tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha']
            commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['created_remote_commit']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent remote advance; immutable objects preserved')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_ref_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Remote ref readback mismatch')
            for target,item in proof.items():
                guard();raw=base64.b64decode(api('git/blobs/'+item['Git_blob_SHA'])['content']);require(len(raw)==item['bytes']and hashlib.sha256(raw).hexdigest()==item['SHA256'],'Full immutable file readback failed');item['readback_passed']=True;del raw
            return dict(status='published_readback_verified',commit=commit,files=proof)
        def verify_old(refs):
            for p,h in refs.items():guard();require(sha(p)==h,'Declared old input/source mismatch: '+p)
        def controller(status,pre=None):
            obj=dict(status=status,current_case=CASE,pid=pid,proc_start_ticks=ticks,stage=stage,updated_utc=bounded.now())
            if pre is not None:obj.update(preregistration_sha256=sha(RUN/'preregistration.json'),current_config_sha256=pre['config_sha256'])
            mutable_json(RUN/'controller.json',obj)
        try:
            guard();controller('preparing'if stage=='prepare'else'checking')
            import all_layer_inputs as inputs
            if stage=='prepare':
                refs=required_old_inputs();verify_old(refs)
                proposal=inputs.derive_config(inputs.TEMPLATE.read_bytes(),inputs.MASK.read_bytes(),RUN)
                with Path(proposal['config_file']).open('xb')as f:f.write(proposal['config_bytes'])
                with Path(proposal['mask_file']).open('xb')as f:f.write(proposal['mask_bytes'])
                new_json(RUN/'material-table.json',proposal['material_table']);new_json(RUN/'config-diff.json',proposal['config_diff'])
                if(SOURCE/'material_evidence.py').is_file():
                    import material_evidence
                    new_json(RUN/'material-evidence.json',material_evidence.build())
                else:new_json(RUN/'material-evidence.json',dict(status='missing_external_audit',material_calibration=False,unverified=True))
                state['phase']='compile_existing_JDK'
                command(['setpriv','--pdeathsig','KILL',str(JAVAC),'-J-Xmx2g','-J-XX:+UseSerialGC','-J-XX:ActiveProcessorCount=1','-J-XX:-UsePerfData','-J-Djava.io.tmpdir='+str(RUN/'tmp'),'-encoding','UTF-8','-d',str(RUN/'classes'),
                    *[str(ROOT/'tis-java'/name)for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java')],str(SOURCE/'WholeLayerSensitivityBasis.java')],log=RUN/'logs/compile.log')
                command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'-cp',str(RUN/'classes'),'WholeLayerSensitivityBasis','--selftest'],log=RUN/'logs/selftest.log')
                command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'--version'],log=RUN/'logs/java-version.log')
                state['phase']='source_unit_contracts'
                tests=command([sys.executable,'-B','-c','import sys,unittest; suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern="test_*.py"); result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite); sys.exit(0 if result.wasSuccessful() else 1)',str(SOURCE)])
                with(RUN/'logs/input-and-post-contract-tests.log').open('xb')as f:f.write(tests)
                sources=source_files();classes={str(p):sha(p)for p in sorted((RUN/'classes').glob('*.class'))}
                require(classes and len(classes)<128,'Finite complete class pins')
                pre=dict(schema=SCHEMA,status='prepared',repository_root=str(ROOT),run_directory=str(RUN),case_id=CASE,
                    controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),config_file=proposal['config_file'],mask_file=proposal['mask_file'],config_sha256=proposal['config_sha256'],mask_sha256=proposal['mask_sha256'],
                    source_sha256=sources,class_sha256=classes,old_input_sha256=refs,java=str(JAVA),javac=str(JAVAC),
                    material_table_sha256=sha(RUN/'material-table.json'),material_evidence_sha256=sha(RUN/'material-evidence.json'),config_diff_sha256=sha(RUN/'config-diff.json'),
                    native_gates=NATIVE_GATES,source_publication_required_before_phantom_PDE=True,maximum_new_conditions=1,maximum_native_RHS=8,frequencies_Hz=list(inputs.FREQUENCIES),
                    physics=dict(radius_mm=25,layers_mm=[.1,5,5,15],pads=4,outputs=2,return_topology='commonGND_pads2and3',source_resistance_ohm=50,source_basis_highZ_Vpp=1,phasor='peak,+jomega_t'),
                    scenario='only SCepsilon110000to1100; all four layer values explicitly uncalibrated assumptions',material_calibrated=False,
                    limits=dict(CPU=1,simultaneous_PDE_workers=1,java_heap_bytes=2*GIB,RSS_plus_all_owned_tmpfs_bytes=3*GIB,max_native_cells=800000,max_run_bytes=MAX_RUN,minimum_root_free_bytes=2*GIB,stage_caps_seconds=CAPS,first_batch_reserved_seconds=1770),
                    policy_refs=policy.policy_refs(ledger),proposed_parent_topic_commit=PARENT)
                new_json(RUN/'preregistration.json',pre);controller('prepared',pre);receipt.update(status='prepared_compiled_selftested_no_phantom_PDE',source_input_count=len(refs),compiled_class_count=len(classes))
            else:
                pre=read(RUN/'preregistration.json');source_guard(pre,guard)
                require(pre['schema']==SCHEMA and pre['status']=='prepared'and pre['case_id']==CASE and pre['maximum_new_conditions']==1 and pre['maximum_native_RHS']==8,
                    'Exact immutable one-condition/eight-RHS registration')
                if stage=='publish-source':
                    files={PUBLIC_SOURCE+'/'+p.name:p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.java','.md','.json')}
                    for name in('preregistration.json','material-table.json','material-evidence.json','config-diff.json','prepare-receipt.json'):files[PUBLIC_RUN+'/'+name]=RUN/name
                    for dirname in('configs','masks','classes','logs'):
                        for p in(RUN/dirname).rglob('*'):
                            if p.is_file():files[PUBLIC_RUN+'/'+p.relative_to(RUN).as_posix()]=p
                    for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'):files[PUBLIC_RUN+'/frozen-numerical-sources/'+name]=ROOT/'tis-java'/name
                    result=publish(files,PARENT,'Preregister one four-layer SC-permittivity assumption sensitivity with pinned native source/classes')
                    new_json(RUN/'source-publication.json',result);receipt.update(status='source_config_classes_published_readback_verified',source_commit=result['commit'])
                else:
                    publication=read(RUN/'source-publication.json');require(publication['status']=='published_readback_verified'and all(i['readback_passed']for i in publication['files'].values()),'Immutable source/config/classes publication prerequisite')
                    controller('running',pre)
                    basis=RUN/'bases'/CASE
                    if stage=='execute':
                        require(not basis.exists(),'No duplicate native basis/solve')
                        receipt['new_native_conditions_started']=1;state['phase']='actual_four_frequency_two_output_PDE'
                        command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'-cp',str(RUN/'classes'),'WholeLayerSensitivityBasis','--execute-parent',str(pid),str(ticks),pre['config_file'],str(basis)],log=RUN/'logs/native-four-frequency.log')
                        require((basis/'BASIS_COMPLETE').is_file(),'Actual native condition completion marker')
                        validation=read(basis/'validation.json');require(validation['new_native_RHS']==8,'Exact8completed actualRHS')
                        for key,limit in NATIVE_GATES.items():require(0<=validation[key]<=limit,'Frozen native gate failed '+key)
                        pins={str(p):sha(p)for p in sorted(basis.iterdir())if p.is_file()};pins[pre['config_file']]=pre['config_sha256']
                        new_json(RUN/'native-sha256.json',dict(schema='task1-native-raw-pin-v1',case_id=CASE,files=pins,native_conditions_completed=1,native_RHS_completed=8,bytes=sum(p.stat().st_size for p in basis.iterdir()if p.is_file())))
                        source_guard(pre,guard);receipt.update(status='new_native_condition_calculated_five_discrete_gates_passed',new_native_conditions_completed=1,new_native_RHS_completed=8,native_validation=validation,native_file_count=len(pins)-1)
                    elif stage=='postprocess':
                        require((basis/'BASIS_COMPLETE').is_file()and read(RUN/'execute-receipt.json')['new_native_conditions_completed']==1,'Actual completed new native solve prerequisite')
                        output=RUN/'postprocess';require(not(output/'summary.json').exists()and not(output/'scalars.npz').exists(),'No overwritten postprocess result')
                        manifest=read(RUN/'native-sha256.json');verify_old(manifest['files']);state['phase']='four_layer_native_statistics_and_independent_diagnostics'
                        import whole_layer_post
                        result=whole_layer_post.build(RUN,guard,declared_sha256=manifest['files'],deadline_monotonic=deadline-10,include_max_direction=True)
                        guard();new_json(output/'summary.json',result['summary'])
                        import numpy as np
                        with(output/'scalars.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
                        del result;guard();source_guard(pre,guard);verify_old(manifest['files'])
                        new_json(output/'artifact-sha256.json',{p.name:dict(SHA256=sha(p),bytes=p.stat().st_size)for p in output.iterdir()if p.is_file()})
                        receipt.update(status='new_native_postprocessed_sensitivity_unadopted',new_native_conditions_reused=1,new_PDE_in_postprocess=0,
                            summary_sha256=sha(output/'summary.json'),scalar_archive_sha256=sha(output/'scalars.npz'),full_convergence_validated=False,material_calibrated=False)
                    else:
                        state['phase']='immutable_raw_and_diagnostic_publication'
                        executed=read(RUN/'execute-receipt.json')if(RUN/'execute-receipt.json').is_file()else{}
                        post=read(RUN/'postprocess-receipt.json')if(RUN/'postprocess-receipt.json').is_file()else{}
                        new_json(RUN/'publication-controller-snapshot.json',read(RUN/'controller.json'))
                        files={}
                        for p in RUN.rglob('*'):
                            if not p.is_file()or 'tmp'in p.relative_to(RUN).parts or p.name in('heartbeat.json','controller.json')or p==receiptpath:continue
                            relative=p.relative_to(RUN).as_posix()
                            target=PUBLIC_RUN+('/failure-evidence/unfinished/'if p.name.endswith('.new')else'/')+relative
                            files[target]=p
                        if(RUN/'postprocess/summary.json').is_file():files[PUBLIC_REPORT+'/summary.json']=RUN/'postprocess/summary.json'
                        files[PUBLIC_REPORT+'/material-table.json']=RUN/'material-table.json';files[PUBLIC_REPORT+'/material-evidence.json']=RUN/'material-evidence.json';files[PUBLIC_REPORT+'/config-diff.json']=RUN/'config-diff.json'
                        result=publish(files,publication['commit'],'Preserve actual four-layer SC-permittivity sensitivity native fields, losses and validation evidence')
                        new_json(RUN/'result-publication.json',result)
                        summary_link=('요약: https://github.com/'+REPO+'/blob/'+result['commit']+'/'+PUBLIC_REPORT+'/summary.json')if(RUN/'postprocess/summary.json').is_file()else'후처리 요약: not_run/실패 보존; 실행 영수증과 실패 로그 참조'
                        completed=executed.get('new_native_conditions_completed',0)==1 and post.get('status')=='new_native_postprocessed_sensitivity_unadopted'
                        raw_count=sum(1 for name in result['files']if '/bases/'+CASE+'/'in name)
                        body='''전 층 확대 지시를 수신·검토했고, 개별 SC/dermis3kHz bulk 물성과 Anand carrier 원자료 미확보를 먼저 보고했습니다. 논문 물성 교정·재현은 보류입니다. 이번 새 조건은 네 층의 기존 가정을 명시한 SCepsilon110000→1100 단일 인자 민감도이며 원하는 그라데이션에 맞춘 조정이 아닙니다.\n\n새 PDE 상태: '''+str(executed.get('status','not_run'))+''' / actual completed conditions='''+str(executed.get('new_native_conditions_completed',0))+''' / RHS='''+str(executed.get('new_native_RHS_completed',0))+'''. 후처리: '''+str(post.get('status','not_run'))+'''. 잔차·전력·전류·면적·shared-flux 보존 gate와 독립 potential-gradient 진단/전체 수렴을 분리합니다. 기존 XY 실패와 전체 수렴·실험·접촉 검증 보류는 유지합니다.\n\n자료: https://github.com/'''+REPO+'/tree/'+result['commit']+'/'+PUBLIC_RUN+'\n'+summary_link+'''\n\n원본/실패/이전 GUI를 보존했습니다. 게시된 실제 native 파일 '''+str(raw_count)+'''개와 나머지 자료 모두를 불변 Gitblob에서 SHA/bytes로 readback 검증했습니다. 완료·부분·실패 상태는 위 영수증과 별개로 바꾸지 않습니다. Jtotal/Jconduction은 같은 저장E에서 유도한 값이며 독립 검증이 아닙니다. 기존CPU1/heap2GiB/RSS+소유tmpfs3GiB/800k/2GiBreserve/13800초 범위의 유한 단일 소유 실행입니다. 실제 Windows 저장·OneDrive 동기화는 직접 연결이 없어 미확인입니다. main 병합·삭제·설치·예산 확대는 하지 않았습니다.'''
                        comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='native_and_diagnostics_published_readback_verified'if completed else'partial_or_failed_evidence_published_readback_verified',result_commit=result['commit'],comment_url=comment['html_url'],native_conditions_completed=executed.get('new_native_conditions_completed',0),new_PDE_in_publication=0,public_files_readback_verified=len(result['files']),native_files_readback_verified=raw_count)
                    controller('stage_complete',pre)
        except BaseException as error:
            receipt.update(error_type=type(error).__name__,error=str(error))
            if stage=='execute':
                log=RUN/'logs/native-four-frequency.log'
                text=log.read_text(errors='replace')if log.is_file()else''
                values=[int(v)for v in re.findall(r'completed_RHS=(\d+)',text)]
                receipt['native_RHS_completed_lower_bound_from_log']=max(values,default=0)
            try:controller('failed_preserved')
            except BaseException:pass
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=bounded.owned_descendants(pid,ticks,state['owned'])
            for p,t in known.items():
                if p!=pid and bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=RUN.name,stage='all_layer_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
            require(shutil.disk_usage(ROOT).free>=2*GIB+len(raw)+8192,'Exact compact atomic ledger admission; preserve budget/history')
            temporary=LEDGER.with_name('task1-budget-all-layer.tmp')
            with temporary.open('xb')as f:f.write(raw)
            os.replace(temporary,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},
                run_bytes=size(RUN),free_root_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            new_json(receiptpath,receipt)
            for sig,handler in previous.items():signal.signal(sig,handler)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
