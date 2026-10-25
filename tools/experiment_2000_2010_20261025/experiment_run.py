#!/usr/bin/env python3
"""One finite owner for one2000/2010Hz sine common-return experiment-model.

No work occurs on import. Preparation, publication, execution and postprocessing
are separate explicit stages. The old numerical sources and all run evidence
remain unchanged. Storage capacity guards are disabled by explicit user instruction. CPU/time budgets remain unchanged; no installation, deletion or main merge.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,base64,hashlib,json,os,re,shutil,signal,subprocess,threading,time
from pathlib import Path
for key in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
os.environ['GODEBUG']='http2client=0'
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-experiment-2000-2010-20261025/source')
RUN=Path('/workspace/task1-experiment-2000-2010-20261025-run')
CASE='baseline-square15-human-sine2000-2010-xy80'
SCHEMA='task1-experiment-sine2000-2010-native-v1'
JAVA_HOME=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
JAVA=JAVA_HOME/'java';JAVAC=JAVA_HOME/'javac'
LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='1a9417879da3cf38abc9ec2a1fd9a6958d4ac148'
PUBLIC_RUN='data-native/cloud-experiment-2000-2010-20261025'
PUBLIC_SOURCE='tools/experiment_2000_2010_20261025'
PUBLIC_REPORT='docs/TASK1_EXPERIMENT_2000_2010_20261025'
GIB=1024**3;MAX_BLOB=64*1024**2;MAX_STDOUT=96*1024**2
STORAGE_POLICY=ROOT/'runtime/task1-storage-policy.json'
CAPS={'prepare':15,'publish-source':35,'execute':60,'postprocess':35,'publish-results':75,'persist':10}
RESERVE={'prepare':230,'publish-source':215,'execute':180,'postprocess':120,'publish-results':85,'persist':10}
NATIVE_GATES={'max_residual':2e-7,'max_power_error':2e-7,'max_current_error':2e-6,'max_area_relative_error':1e-10,'max_interface_normal_current_relative_error':2e-7}
ADJACENCY_PERCENT=dict(target20_modulation_V_m=1,target20_total_E_RMS_V_m=1,
    roi_mean_TIS_V_m=1,roi_p10_TIS_V_m=1,roi_mean_RMS_V_m=1,target_superficial_p95_ratio=1,
    surface_J_RMS_max_A_m2=5,surface_J_RMS_p95_A_m2=5,contact_voltage_RMS_max_V=5,
    SC_power_W=2,contact_power_W=2,source_power_W=2)
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
    files={p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.java','.md','.json','.txt','.csv')}
    files.update(ROOT/'tis-java'/n for n in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'))
    files.update((ROOT/'tis-java').glob('*.py'))
    files.update(ROOT/'tools'/n for n in('task1_bounded_continuation.py','task1_resource_policy.py'))
    return {str(p):sha(p)for p in sorted(files)}
def required_old_inputs():
    import experiment_post as post
    import experiment_inputs as inputs
    refs=post.required_inputs()
    refs[str(inputs.TEMPLATE)]=inputs.TEMPLATE_SHA256;refs[str(inputs.MASK)]=inputs.MASK_SHA256
    require(inputs.MATERIAL_INPUT.is_file(),'Source-verified material-input.json missing; no default human material assignment')
    inputs.verified_materials(inputs.MATERIAL_INPUT.read_bytes());refs[str(inputs.MATERIAL_INPUT)]=sha(inputs.MATERIAL_INPUT)
    publication_path=inputs.COMPARATOR/'result-publication.json';publication=read(publication_path)
    require(publication['status']=='published_readback_verified'and re.fullmatch(r'[0-9a-f]{40}',publication['commit'])is not None and
        publication['files']and all(item['readback_passed']for item in publication['files'].values()),
        'Completed first-result immutable full readback prerequisite before extra check')
    prefix='data-native/cloud-human-tissue-20261025/'
    for path,digest in list(refs.items()):
        p=Path(path)
        if p.is_relative_to(inputs.COMPARATOR):
            target=prefix+p.relative_to(inputs.COMPARATOR).as_posix()
            require(target in publication['files']and publication['files'][target]['SHA256']==digest,
                'Every declared actual SC2 native/post comparator must have verified immutable publication: '+target)
    refs[str(publication_path)]=sha(publication_path)
    refs[str(inputs.RAW_EIS)]=inputs.RAW_EIS_SHA256;refs[str(inputs.FIT)]=sha(inputs.FIT)
    refs[str(ROOT/'tis-java/update_ngg_eis.py')]=sha(ROOT/'tis-java/update_ngg_eis.py')
    evidence=SOURCE/'material_evidence.py'
    if evidence.is_file():
        import material_evidence
        refs.update(material_evidence.required_inputs())
    return refs
def source_guard(pre,guard):
    require(pre['source_sha256']==source_files(),'Preregistered source set or bytes changed')
    for path,digest in {**pre['class_sha256'],**pre['old_input_sha256']}.items():guard();require(sha(path)==digest,'Pinned class/old input changed: '+path)
    require(sha(pre['config_file'])==pre['config_sha256']and sha(pre['mask_file'])==pre['mask_sha256'],'New registered config or mask changed')
    require(sha(RUN/'material-input.json')==pre['material_input_sha256'],'Source-verified material receipt changed')
    require(sha(RUN/'contact-receipt.json')==pre['contact_receipt_sha256'],'Actual carrier contact receipt changed')

def main():
    parser=argparse.ArgumentParser();flags=parser.add_mutually_exclusive_group(required=True)
    for name in CAPS:flags.add_argument('--'+name,action='store_true',dest=name.replace('-','_'))
    parser.add_argument('--output',default=str(RUN));args=parser.parse_args()
    stage=next(name for name in CAPS if getattr(args,name.replace('-','_')))
    require(Path(args.output)==RUN and RUN==RUN.absolute()and RUN.parent==Path('/workspace'),'Exact registered unique run path required')
    require(Path(__file__).resolve()==SOURCE/'experiment_run.py','Exact frozen controller path required')
    require(re.fullmatch(r'[0-9a-f]{40}',PARENT) is not None,'Owner must set the actual expected topic commit before preparation/source freeze')
    storage=read(STORAGE_POLICY);storage_sha256=sha(STORAGE_POLICY)
    require(storage.get('schema')=='task1-user-storage-override-v1'and storage.get('storage_capacity_guards_enabled')is False and storage.get('minimum_root_free_bytes')==0 and storage.get('per_run_output_bytes_limit')is None,'Explicit user storage override required')
    receiptpath=RUN/(stage+'-receipt.json')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);remaining=policy.remaining_seconds(ledger)
        require(remaining>=RESERVE[stage],'Finite first-batch reservation requires '+str(RESERVE[stage])+'s; remaining '+str(remaining))
        require(not receiptpath.exists(),'Immutable stage receipt exists; preserve evidence and review recovery explicitly')
        require(all(p.is_file()and os.access(p,os.X_OK)for p in(JAVA,JAVAC))and shutil.which('setpriv'),'Existing JDK21/setpriv required; no installation')
        if stage=='prepare':
            require(not RUN.exists(),'Preparation needs a genuinely new run; preserve existing attempt')
            RUN.mkdir()
            for name in('configs','masks','bases','classes','logs','tmp','postprocess'):(RUN/name).mkdir()
        else:require(RUN.is_dir()and RUN==RUN.resolve()and not RUN.is_symlink(),'Canonical existing registered tmpfs run')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});pid=os.getpid();ticks=bounded.ticks(pid);start=time.monotonic();deadline=start+CAPS[stage]
        state={'owned':{pid:ticks},'peak_RSS':0,'peak_owned_tmpfs':0,'peak_accounted':0,'phase':stage};stop=threading.Event()
        receipt={'schema':'task1-sine-experiment-finite-stage-v1','stage':stage,'status':'failed_preserved','started_utc':bounded.now(),'pid':pid,'proc_start_ticks':ticks,
            'run_id':RUN.name,'case_id':CASE,'remaining_before_seconds':remaining,'stage_cap_seconds':CAPS[stage],'new_native_conditions_started':0,'new_native_conditions_completed':0,
            'evidence_backed_material_reset':'human_reference_or_declared_surrogate; actual_phantom_calibration_not_performed','scenario':'one explicit2000/2010Hz sine common-return experiment-model; actual hardware unverified','storage_capacity_guards_enabled':False,'storage_policy_sha256':storage_sha256}
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);owned=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));run_bytes=size(RUN)
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],owned),peak_accounted=max(state['peak_accounted'],rss+owned))
            require(time.monotonic()<deadline,'Finite stage deadline exhausted')
            require(rss+owned<=3*GIB,'Original RSS+all-owned-tmpfs3GiB RAM gate; storage capacity guards disabled by user')
            require(sha(STORAGE_POLICY)==storage_sha256,'Explicit storage override bytes changed')
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
        def command(argv,body=None,log=None,allow_nonzero=False):
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
                if allow_nonzero:return dict(returncode=child.returncode,stdout=stdout,stderr=stderr,failure_log=None if failure is None else str(failure))
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
            # Reuse already-full-readback immutable objects from the pinned
            # published human SC2 receipt, chiefly unchanged numerical classes.
            # Every new object still receives a fresh full GET verification.
            prior_path=Path('/dev/shm/task1-human-tissue-20261025-run/result-publication.json')
            prior=read(prior_path);prior_sha256=sha(prior_path)
            require(prior['status']=='published_readback_verified'and all(i['readback_passed']for i in prior['files'].values()),'Pinned prior immutable readback proof')
            cache={i['Git_blob_SHA']:i for i in prior['files'].values()}
            for target,path in files.items():
                guard();p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_BLOB,'Regular bounded64MiB publication file')
                raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                old=cache.get(blob)
                if old is not None and old['SHA256']==h and old['bytes']==len(raw):
                    entries.append(dict(path=target,mode='100644',type='blob',sha=blob))
                    proof[target]=dict(SHA256=h,bytes=len(raw),Git_blob_SHA=blob,readback_passed=True,
                        proof_kind='reused_previous_full_immutable_readback',prior_receipt_sha256=prior_sha256,prior_commit=prior['commit'])
                    del raw
                    continue
                # A deterministic Git identity lets a later explicit recovery
                # distinguish an existing object from a confirmed absence.
                # Unknown mutation failure never triggers another POST.
                record=None;confirmed_missing=False
                for attempt in range(2):
                    reply=command(['gh','api','repos/'+REPO+'/git/blobs/'+blob,'-X','GET'],allow_nonzero=True)
                    if reply['returncode']==0:record=json.loads(reply['stdout']);break
                    try:error=json.loads(reply['stdout'])
                    except(ValueError,UnicodeError):error={}
                    stderr=reply['stderr'].decode(errors='replace')
                    if str(error.get('status'))=='404'and error.get('message')=='Not Found'and re.search(r'HTTP\s+404',stderr):
                        confirmed_missing=True;break
                    if attempt==1:raise RuntimeError('Blob existence unknown; no mutation retry. See '+str(reply['failure_log']))
                    guard()
                existed=record is not None
                if not existed:
                    require(confirmed_missing,'Blob POST requires an explicit404 absence')
                    receipt['pending_blob']=dict(path=target,Git_blob_SHA=blob,SHA256=h,bytes=len(raw),absence_confirmed=True)
                    created=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST')
                    require(created['sha']==blob,'Exact created Gitblob identity')
                    record=api('git/blobs/'+blob)
                require(record['sha']==blob and record.get('encoding')=='base64','Readback must be the exact deterministic Gitblob')
                downloaded=base64.b64decode(record['content']);require(len(downloaded)==len(raw)and hashlib.sha256(downloaded).hexdigest()==h,'Full immutable blob SHA/bytes readback')
                entries.append(dict(path=target,mode='100644',type='blob',sha=blob));proof[target]=dict(SHA256=h,bytes=len(raw),Git_blob_SHA=blob,readback_passed=True,already_present_before_mutation=existed)
                receipt.pop('pending_blob',None);del downloaded,record
                del raw
            tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha']
            commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['created_remote_commit']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent remote advance; immutable objects preserved')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_ref_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Remote ref readback mismatch')
            committed=api('git/commits/'+commit)
            require(committed['tree']['sha']==tree and [p['sha']for p in committed['parents']]==[parent],
                'Commit readback must bind the exact verified immutable blob tree and expected parent')
            return dict(status='published_readback_verified',commit=commit,files=proof)
        def verify_old(refs):
            for p,h in refs.items():guard();require(sha(p)==h,'Declared old input/source mismatch: '+p)
        def controller(status,pre=None):
            obj=dict(status=status,current_case=CASE,pid=pid,proc_start_ticks=ticks,stage=stage,updated_utc=bounded.now())
            if pre is not None:obj.update(preregistration_sha256=sha(RUN/'preregistration.json'),current_config_sha256=pre['config_sha256'])
            mutable_json(RUN/'controller.json',obj)
        try:
            guard();controller('preparing'if stage=='prepare'else'checking')
            import experiment_inputs as inputs
            if stage=='prepare':
                refs=required_old_inputs();verify_old(refs)
                proposal=inputs.derive_config(inputs.TEMPLATE.read_bytes(),inputs.MASK.read_bytes(),inputs.MATERIAL_INPUT.read_bytes(),RUN)
                with Path(proposal['config_file']).open('xb')as f:f.write(proposal['config_bytes'])
                with Path(proposal['mask_file']).open('xb')as f:f.write(proposal['mask_bytes'])
                with(RUN/'material-input.json').open('xb')as f:f.write(proposal['material_bytes'])
                with(RUN/'contact-receipt.json').open('xb')as f:f.write(proposal['contact_bytes'])
                with(RUN/'storage-policy.json').open('xb')as f:f.write(STORAGE_POLICY.read_bytes())
                new_json(RUN/'material-table.json',proposal['material_table']);new_json(RUN/'config-diff.json',proposal['config_diff'])
                old_publication=read(inputs.COMPARATOR/'result-publication.json')
                new_json(RUN/'comparator-publication.json',dict(status='published_readback_verified',commit=old_publication['commit'],
                    public_native_root='data-native/cloud-human-tissue-20261025',
                    publication_receipt_sha256=sha(inputs.COMPARATOR/'result-publication.json'),
                    verified_public_files=len(old_publication['files']),new_PDE_in_this_preparation=0))
                new_json(RUN/'material-evidence.json',dict(status='source_verified_for_declared_scope',material_input_sha256=proposal['material_input_sha256'],rows=proposal['material_table']['rows'],material_calibrated=False,phantom_experimentally_validated=False))
                state['phase']='compile_existing_JDK'
                command(['setpriv','--pdeathsig','KILL',str(JAVAC),'-J-Xmx2g','-J-XX:+UseSerialGC','-J-XX:ActiveProcessorCount=1','-J-XX:-UsePerfData','-J-Djava.io.tmpdir='+str(RUN/'tmp'),'-encoding','UTF-8','-d',str(RUN/'classes'),
                    *[str(ROOT/'tis-java'/name)for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java')],str(SOURCE/'ExperimentSineBasis.java')],log=RUN/'logs/compile.log')
                command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'-cp',str(RUN/'classes'),'ExperimentSineBasis','--selftest'],log=RUN/'logs/selftest.log')
                command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'--version'],log=RUN/'logs/java-version.log')
                state['phase']='source_unit_contracts'
                tests=command([sys.executable,'-B','-c','import sys,unittest; suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern="test_*.py"); result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite); sys.exit(0 if result.wasSuccessful() else 1)',str(SOURCE)])
                with(RUN/'logs/input-and-post-contract-tests.log').open('xb')as f:f.write(tests)
                sources=source_files();classes={str(p):sha(p)for p in sorted((RUN/'classes').glob('*.class'))}
                require(classes and len(classes)<128,'Finite complete class pins')
                pre=dict(schema=SCHEMA,status='prepared',repository_root=str(ROOT),run_directory=str(RUN),case_id=CASE,
                    controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),config_file=proposal['config_file'],mask_file=proposal['mask_file'],config_sha256=proposal['config_sha256'],mask_sha256=proposal['mask_sha256'],
                    source_sha256=sources,class_sha256=classes,old_input_sha256=refs,java=str(JAVA),javac=str(JAVAC),
                    material_input_sha256=proposal['material_input_sha256'],contact_receipt_sha256=proposal['contact_receipt_sha256'],material_table_sha256=sha(RUN/'material-table.json'),material_evidence_sha256=sha(RUN/'material-evidence.json'),config_diff_sha256=sha(RUN/'config-diff.json'),
                    native_gates=NATIVE_GATES,historical_SC_mesh_adjacency_percent=ADJACENCY_PERCENT,
                    adjacency_scope='Historical mesh criteria are not applied to changes caused by different material models; report differences without candidate adoption',
                    independent_interface_accuracy_gate='Predeclared5percent normalized-L2 numerical screening QA flags; non-aborting diagnostics, not a physical accuracy/activation/safety criterion',
                    source_publication_required_before_phantom_PDE=True,maximum_new_conditions=1,maximum_native_RHS=4,frequencies_Hz=list(inputs.FREQUENCIES),
                    mesh=dict(SC_cells=2,XY_mm=.625,bulk_cells=[14,14,40],native_cells=351680),
                    comparators=dict(human3k_template_sha256=inputs.TEMPLATE_SHA256,human3k_run=inputs.COMPARATOR.name,human3k_case=inputs.COMPARATOR_CASE),
                    comparator_publication_receipt_sha256=sha(RUN/'comparator-publication.json'),
                    next_condition_policy='One condition in this finite batch; after actual results, select next scientific step subject to remaining approved budget; no implicit isolated-bipolar assumption',
                    topology_audit=dict(pads=4,independent_outputs=2,pad_nodes={'0':'out0','1':'out1','2':'commonGND','3':'commonGND'},
                        inactive_output_at_other_frequency='0Vthrough50ohm; no open output assumption',actual_equipment_wiring_waveform_verified=False,
                        independent_isolated_bipolar_two_pairs='separate scenario not executed',
                        source_anchors=['tis-java/SelectivityShapeBasis.java:206 e<channels output node else ground',
                            'tis-java/SelectivityShapeBasis.java:209 all output diagonal conductance0.02S',
                            'tis-java/TisSweep.java:73-74 solve(source) RHS0.01A only at selected output; other RHS0',
                            'tis-java/SelectivityShapeBasis.java:259-260 (a==c?0.5:0)-metal divided50ohm']),
                    physics=dict(radius_mm=25,layers_mm=[.1,5,5,15],pads=4,outputs=2,return_topology='commonGND_pads2and3',source_resistance_ohm=50,source_basis_highZ_Vpp=1,phasor='peak,+jomega_t',waveform='sine',carrier_coefficients={'2000':[1,0],'2010':[0,1]},actual_hardware_waveform_and_topology_verified=False),
                    scenario='Explicit2000/2010Hz sine common-return experiment-model; actual hardware waveform/topology unverified; source-material functions retained at actual carriers',material_calibrated=False,
                    limits=dict(CPU=1,simultaneous_PDE_workers=1,java_heap_bytes=2*GIB,RSS_plus_all_owned_tmpfs_bytes=3*GIB,max_native_cells=800000,max_run_bytes=None,minimum_root_free_bytes=0,storage_capacity_guards_enabled=False,stage_caps_seconds=CAPS,first_batch_reserved_seconds=230,GUI_time_reserved_separately=True),
                    policy_refs=policy.policy_refs(ledger),storage_policy_sha256=storage_sha256,proposed_parent_topic_commit=PARENT)
                new_json(RUN/'preregistration.json',pre);controller('prepared',pre);receipt.update(status='prepared_compiled_selftested_no_phantom_PDE',source_input_count=len(refs),compiled_class_count=len(classes))
            else:
                pre=read(RUN/'preregistration.json');source_guard(pre,guard)
                require(pre['schema']==SCHEMA and pre['status']=='prepared'and pre['case_id']==CASE and pre['maximum_new_conditions']==1 and pre['maximum_native_RHS']==4,
                    'Exact immutable one-condition/four-RHS registration')
                if stage=='publish-source':
                    files={PUBLIC_SOURCE+'/'+p.name:p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.java','.md','.json','.txt','.csv')}
                    for name in('preregistration.json','material-table.json','material-evidence.json','config-diff.json','comparator-publication.json','material-input.json','contact-receipt.json','storage-policy.json','prepare-receipt.json'):files[PUBLIC_RUN+'/'+name]=RUN/name
                    for dirname in('configs','masks','classes','logs'):
                        for p in(RUN/dirname).rglob('*'):
                            if p.is_file():files[PUBLIC_RUN+'/'+p.relative_to(RUN).as_posix()]=p
                    for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'):files[PUBLIC_RUN+'/frozen-numerical-sources/'+name]=ROOT/'tis-java'/name
                    result=publish(files,PARENT,'Preregister one2kHz two-carrier sine experiment-model with raw-reconstructed nominal10nm contact')
                    new_json(RUN/'source-publication.json',result);receipt.update(status='source_config_classes_published_readback_verified',source_commit=result['commit'])
                else:
                    publication=read(RUN/'source-publication.json');require(publication['status']=='published_readback_verified'and all(i['readback_passed']for i in publication['files'].values()),'Immutable source/config/classes publication prerequisite')
                    controller('running',pre)
                    basis=RUN/'bases'/CASE
                    if stage=='execute':
                        require(not basis.exists(),'No duplicate native basis/solve')
                        receipt['new_native_conditions_started']=1;state['phase']='actual_two_frequency_two_output_PDE'
                        command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'-cp',str(RUN/'classes'),'ExperimentSineBasis','--execute-parent',str(pid),str(ticks),pre['config_file'],str(basis)],log=RUN/'logs/native-two-frequency.log')
                        require((basis/'BASIS_COMPLETE').is_file(),'Actual native condition completion marker')
                        validation=read(basis/'validation.json');require(validation['new_native_RHS']==4,'Exact4completed actualRHS')
                        for key,limit in NATIVE_GATES.items():require(0<=validation[key]<=limit,'Frozen native gate failed '+key)
                        pins={str(p):sha(p)for p in sorted(basis.iterdir())if p.is_file()};pins[pre['config_file']]=pre['config_sha256'];pins[str(RUN/'material-input.json')]=pre['material_input_sha256'];pins[str(RUN/'contact-receipt.json')]=pre['contact_receipt_sha256']
                        new_json(RUN/'native-sha256.json',dict(schema='task1-sine-experiment-native-raw-pin-v1',case_id=CASE,files=pins,native_conditions_completed=1,native_RHS_completed=4,bytes=sum(p.stat().st_size for p in basis.iterdir()if p.is_file())))
                        source_guard(pre,guard);receipt.update(status='new_native_condition_calculated_five_discrete_gates_passed',new_native_conditions_completed=1,new_native_RHS_completed=4,native_validation=validation,native_file_count=sum(p.is_file()for p in basis.iterdir()))
                    elif stage=='postprocess':
                        require((basis/'BASIS_COMPLETE').is_file()and read(RUN/'execute-receipt.json')['new_native_conditions_completed']==1,'Actual completed new native solve prerequisite')
                        output=RUN/'postprocess';require(not(output/'summary.json').exists()and not(output/'scalars.npz').exists(),'No overwritten postprocess result')
                        manifest=read(RUN/'native-sha256.json');verify_old(manifest['files']);state['phase']='four_layer_native_statistics_and_independent_diagnostics'
                        import experiment_post
                        result=experiment_post.build(RUN,guard,declared_sha256=manifest['files'],deadline_monotonic=deadline-10,include_max_direction=True)
                        guard();new_json(output/'summary.json',result['summary'])
                        import numpy as np
                        with(output/'scalars.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
                        del result;guard();source_guard(pre,guard);verify_old(manifest['files'])
                        new_json(output/'artifact-sha256.json',{p.name:dict(SHA256=sha(p),bytes=p.stat().st_size)for p in output.iterdir()if p.is_file()})
                        receipt.update(status='new_native_postprocessed_sine_experiment_unadopted',new_native_conditions_reused=1,new_PDE_in_postprocess=0,
                            summary_sha256=sha(output/'summary.json'),scalar_archive_sha256=sha(output/'scalars.npz'),full_convergence_validated=False,material_calibrated=False)
                    elif stage=='persist':
                        require(read(RUN/'result-publication.json')['status']=='published_readback_verified','Verified scientific result publication required')
                        verify_old(read(RUN/'native-sha256.json')['files'])
                        for name,entry in read(RUN/'postprocess/artifact-sha256.json').items():require(sha(RUN/'postprocess'/name)==entry['SHA256'],'Final disk artifact identity')
                        receipt.update(status='existing_cloud_disk_dataset_verified_Windows_unverified',new_PDE_in_persistence=0,
                            Windows_storage_verified=False,cloud_run_path=str(RUN),cloud_native_and_post_hashes_verified=True)
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
                        result=publish(files,publication['commit'],'Preserve actual2000/2010sine native fields/contact and limited numerical diagnostics')
                        new_json(RUN/'result-publication.json',result)
                        summary_link=('요약: https://github.com/'+REPO+'/blob/'+result['commit']+'/'+PUBLIC_REPORT+'/summary.json')if(RUN/'postprocess/summary.json').is_file()else'후처리 요약: not_run/실패 보존; 실행 영수증과 실패 로그 참조'
                        completed=executed.get('new_native_conditions_completed',0)==1 and post.get('status')=='new_native_postprocessed_sine_experiment_unadopted'
                        raw_count=sum(1 for name in result['files']if '/bases/'+CASE+'/'in name)
                        body=('GUI 갱신과 별도로 실제 새 계산 조건2000/2010Hz·각출력1Vpp sine·4패드/2출력/commonGND/50ohm를 유한 등록했습니다. '
                            '이는 명시적 실험 모델 시나리오이며 실제 장비 파형·배선 확인을 뜻하지 않습니다. 별도 절연2전극쌍 토폴로지는 계산하지 않았습니다. '
                            '기존50mm/0.1·5·5·15mm 팬텀과SC2/XY0.625mm/bulk14·14·40을 유지하고 HREF-MIX-v1의 이미 게시된2k/2010 물성 행을 사용했습니다.\n\n'
                            '새 PDE: '+str(executed.get('status','not_run'))+' / completed conditions='+str(executed.get('new_native_conditions_completed',0))+
                            ' / RHS='+str(executed.get('new_native_RHS_completed',0))+'. 후처리: '+str(post.get('status','not_run'))+'. '
                            '10nm contact의500은 fit 하한주파수500Hz이며 선택Rs는236.5717747232937ohm입니다. 원본30점·rawSHA를 확인하고 실제2k/2010에서log-f보간 후 Rs한번차감·측정면적1e-4한번곱셈으로 specificZ를 새로 구성했습니다. '
                            '3kcontact값 재사용·재피팅·2로나누기는 없으며 PBS접촉 대체 가정의 한계는 유지합니다.\n\n'
                            '자료: https://github.com/'+REPO+'/tree/'+result['commit']+'/'+PUBLIC_RUN+'\n'+summary_link+'\n\n'
                            '새 원시E/phi/grid/contact/source/loss를 보존하고 J는 E·gamma로 후처리 유도했습니다. SC100um는 고정하며14um와의 specificZ비교는 분석식만 사용했습니다. '
                            '독립 계면 진단의 수치 QA표시는 활성화·안전 기준이 아니며 실패 표시를 유지합니다. 기존3k sine 비교와 동일전력·전류·복합부담제한 비교를 분리했습니다. '
                            'native 파일 '+str(raw_count)+'개와 나머지 자료는 SHA/bytes readback proof를 연결했고, 동일한 기존 불변blob은 이전 검증 영수증을 명시적으로 재사용했습니다. '
                            '저장 용량 가드는 해제했고 기존CPU1/RSS+모든소유tmpfs3GiB/13800초 시간 예산은 유지합니다. Windows실제저장·장비설정은 미확인입니다. '
                            '추가 자동 조건·CPU/시간 예산 확대·설치·삭제·main병합은 하지 않았습니다.')
                        comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='native_and_diagnostics_published_readback_verified'if completed else'partial_or_failed_evidence_published_readback_verified',result_commit=result['commit'],comment_url=comment['html_url'],native_conditions_completed=executed.get('new_native_conditions_completed',0),new_PDE_in_publication=0,public_files_readback_verified=len(result['files']),native_files_readback_verified=raw_count)
                    controller('stage_complete',pre)
        except BaseException as error:
            receipt.update(error_type=type(error).__name__,error=str(error))
            if stage=='execute':
                log=RUN/'logs/native-two-frequency.log'
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
            ledger['runs'].append(dict(run_id=RUN.name,stage='sine_experiment_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
            temporary=LEDGER.with_name('task1-budget-sine-experiment.tmp')
            with temporary.open('xb')as f:f.write(raw)
            os.replace(temporary,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},
                run_bytes=size(RUN),free_root_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            new_json(receiptpath,receipt)
            for sig,handler in previous.items():signal.signal(sig,handler)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
