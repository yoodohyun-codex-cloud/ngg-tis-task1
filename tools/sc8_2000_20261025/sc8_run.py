#!/usr/bin/env python3
"""One finite owner for one conditional2000Hz SC4-to8 refinement diagnostic.

No work occurs on import. Preparation, publication, execution and postprocessing
are separate explicit stages. The old numerical sources and all run evidence
remain unchanged. Storage capacity guards are disabled by explicit user instruction. CPU/RAM limits remain; cumulative-time limit is explicitly removed, finite stage caps remain; no installation, deletion or main merge.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,base64,gzip,hashlib,io,json,os,re,shutil,signal,subprocess,tarfile,threading,time
from pathlib import Path
# Thread/affinity limits are applied by the SHA-bound helper before NumPy import.
os.environ['GODEBUG']='http2client=0'
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-sc8-2000-20261025/source')
RUN=Path('/dev/shm/task1-sc8-2000-20261025-run')
CASE='baseline-square15-human-sine2000-sc8-bulk18-18-56-xy100'
SCHEMA='task1-sc8-2000-native-v1'
JAVA_HOME=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
JAVA=JAVA_HOME/'java';JAVAC=JAVA_HOME/'javac'
LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='f139de1dcce34600514b55f6e182e15ee058d5fd'
PUBLIC_RUN='data-native/cloud-sc8-2000-20261025'
PUBLIC_SOURCE='tools/sc8_2000_20261025'
PUBLIC_REPORT='docs/TASK1_SC8_2000_20261025'
GIB=1024**3;MAX_BLOB=64*1024**2;MAX_STDOUT=96*1024**2
STORAGE_POLICY=ROOT/'runtime/task1-storage-policy.json'
CAPS={'prepare':30,'publish-source':60,'execute':180,'postprocess':120,'publish-results':240,'persist':30}
RESERVE={'prepare':660,'publish-source':630,'execute':570,'postprocess':390,'publish-results':270,'persist':30}
NATIVE_GATES={'max_residual':2e-7,'max_power_error':2e-7,'max_current_error':2e-6,'max_area_relative_error':1e-10,'max_interface_normal_current_relative_error':2e-7}
ADJACENCY_PERCENT={'target.E_carrier_RMS.mean':1,'target.E_carrier_RMS.p10':1,
    'contact_normal_J_RMS_max_A_m2':5,'contact_normal_J_RMS_P95_A_m2':5,'contact_voltage_RMS_max_V':5,
    'source_power_W':2,'contact_power_W':2,'source_resistor_power_W':2,'SC_power_W':2,'skin_power_W':2,
    'dermis_power_W':2,'fat_power_W':2,'muscle_power_W':2}
sys.path[:0]=[str(SOURCE),str(ROOT/'tools'),str(ROOT/'tis-java')]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy
import task1_execution_policy as execution

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def observe_blas(limits):
    try:
        from threadpoolctl import threadpool_info
    except ImportError:
        return dict(status='runtime_introspection_unavailable',configured_threads=limits['blas_threads'],verified=False)
    libraries=threadpool_info()
    observed=[row for row in libraries if row.get('user_api')in('blas','openmp')]
    require(all(type(row.get('num_threads'))is int and row['num_threads']<=limits['blas_threads']for row in observed),'Observed BLAS/OpenMP thread cap')
    return dict(status='observed_thread_limits'if observed else'no_loaded_BLAS_reported',configured_threads=limits['blas_threads'],
        verified=bool(observed),all_observed_exactly_configured=bool(observed)and all(row['num_threads']==limits['blas_threads']for row in observed),libraries=libraries)
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
    files.update(ROOT/'tools'/n for n in('task1_bounded_continuation.py','task1_resource_policy.py','task1_execution_policy.py'))
    return {str(p):sha(p)for p in sorted(files)}
def required_old_inputs():
    import sc8_post as post
    import sc8_inputs as inputs
    refs=post.required_inputs()
    bulk_result=read(inputs.COMPARATOR/'postprocess/summary.json')
    require(post.conditional_selection_matches(bulk_result),'Conditional SC8 requires actual SC4 scalar stability and unresolved common-two-point screening')
    refs[str(inputs.TEMPLATE)]=inputs.TEMPLATE_SHA256;refs[str(inputs.MASK)]=inputs.MASK_SHA256
    require(inputs.MATERIAL_INPUT.is_file(),'Source-verified material-input.json missing; no default human material assignment')
    inputs.verified_materials(inputs.MATERIAL_INPUT.read_bytes());refs[str(inputs.MATERIAL_INPUT)]=sha(inputs.MATERIAL_INPUT)
    publication_path=inputs.COMPARATOR/'result-publication.json';publication=read(publication_path)
    require(publication['status']=='published_readback_verified'and re.fullmatch(r'[0-9a-f]{40}',publication['commit'])is not None and
        publication['files']and all(item['readback_passed']for item in publication['files'].values()),
        'Completed first-result immutable full readback prerequisite before extra check')
    prefix='data-native/cloud-sc4-2000-20261025/'
    from verified_publication import verified_archive_member
    source_publication_path=inputs.COMPARATOR/'source-publication.json'
    source_publication=read(source_publication_path)
    require(source_publication['status']=='published_readback_verified'and all(v['readback_passed']for v in source_publication['files'].values()),'Verified original source publication receipt')
    archive_path=inputs.COMPARATOR/'publication-evidence/evidence.tar.gz'
    archive_target=prefix+'evidence.tar.gz'
    archive_proof=publication['files'].get(archive_target)
    member_proofs={}
    for path,digest in list(refs.items()):
        file=Path(path)
        if file.is_relative_to(inputs.COMPARATOR):
            member=file.relative_to(inputs.COMPARATOR).as_posix();target=prefix+member
            direct=next((pub for pub in(publication,source_publication)if target in pub['files']and pub['files'][target]['SHA256']==digest and pub['files'][target]['readback_passed']),None)
            if direct is not None:
                member_proofs[member]=dict(kind='direct_immutable_full_readback',commit=direct['commit'],SHA256=digest)
            else:
                require(not member.startswith('bases/')and archive_proof is not None,'Raw native data must have direct individual immutable proof: '+target)
                verified_archive_member(archive_path,archive_proof,member,digest)
                member_proofs[member]=dict(kind='exact_member_of_full_readback_archive',commit=publication['commit'],archive_repository_path=archive_target,archive_SHA256=archive_proof['SHA256'],member=member,member_SHA256=digest)
                refs[str(archive_path)]=archive_proof['SHA256']
    refs[str(source_publication_path)]=sha(source_publication_path)
    new_json(RUN/'comparator-member-proof.json',dict(schema='task1-comparator-direct-or-archive-proof-v1',members=member_proofs,raw_native_requires_individual_proof=True))
    refs[str(publication_path)]=sha(publication_path)
    refs[str(inputs.CONTACT_INPUT)]=inputs.CONTACT_SHA256
    manufactured_path=Path('/workspace/task1-interface-fourier-20261025-run-r2/computation-receipt.json')
    manufactured=read(manufactured_path)
    require(manufactured['status']=='manufactured_cases_computed'and manufactured['analytic_contracts']['passed']is True and manufactured['new_real_phantom_PDE']==0,
        'Completed manufactured analytical contracts required before bulk admission; not physical phantom validation')
    refs[str(manufactured_path)]=sha(manufactured_path)
    manufactured_summary=manufactured_path.with_name('summary.json')
    refs[str(manufactured_summary)]=sha(manufactured_summary)
    with(RUN/'manufactured-computation-receipt.json').open('xb')as stream:stream.write(manufactured_path.read_bytes())
    new_json(RUN/'manufactured-admission.json',dict(receipt_sha256=sha(manufactured_path),summary_sha256=sha(manufactured_summary),
        status='analytic_contracts_passed_bulk_diagnostic_admitted',
        scientific_question='Does SC4-to8 native refinement change actual target/skin metrics and common-two-point diagnostics after stable SC4 metrics, using fixed-order common2 and nearest3 fits on both meshes?',
        scope='Code/manufactured-case context only; manufactured bias does not clear actual phantom5percent flags or validate tissue/physiology'))
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
    require(sha(RUN/'comparator-member-proof.json')==pre['comparator_member_proof_sha256'],'Comparator archive-member proof changed')
    require(sha(RUN/'execution-limits.json')==pre['execution_limits_sha256'],'Registered execution limits changed')
    require(sha(RUN/'blas-runtime.json')==pre['blas_runtime_sha256'],'Registered BLAS observation changed')
    require(sha(RUN/'manufactured-admission.json')==pre['manufactured_admission_sha256']and sha(RUN/'manufactured-computation-receipt.json')==pre['manufactured_receipt_sha256'],'Registered manufactured admission context changed')

def pack_evidence(guard):
    """Snapshot small immutable evidence; large native/post files stay direct."""
    directory=RUN/'publication-evidence';directory.mkdir(exist_ok=True)
    archive=directory/'evidence.tar.gz';manifest=directory/'manifest.json'
    require(not archive.exists()and not manifest.exists(),'Preserve existing evidence archive; explicit recovery required')
    selected=[];large={}
    for path in sorted(RUN.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(RUN)
        if relative.parts[0]in('bases','postprocess','tmp','publication-evidence'):continue
        if path.name in('controller.json','heartbeat.json','controller.json.new','heartbeat.json.new','publish-results-receipt.json'):continue
        guard();require(not path.is_symlink(),'Canonical regular evidence')
        if path.stat().st_size>4*1024**2:large[PUBLIC_RUN+'/failure-evidence/large/'+relative.as_posix()]=path
        else:selected.append((path,relative.as_posix(),sha(path),path.stat().st_size))
    record=dict(schema='task1-small-evidence-archive-v1',snapshot_utc=bounded.now(),
        scope='Configs/classes/logs/failures/checkpoints/metadata existing before result publication; native/post direct; later publication logs remain local evidence',
        files={name:dict(SHA256=h,bytes=n)for _,name,h,n in selected})
    new_json(manifest,record)
    with archive.open('xb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0)as compressed:
            with tarfile.open(fileobj=compressed,mode='w|')as tar:
                for path,name,digest,n in selected:
                    guard();data=path.read_bytes();require(len(data)==n and hashlib.sha256(data).hexdigest()==digest,'Evidence changed while archiving')
                    info=tarfile.TarInfo(name);info.size=n;info.mode=0o644;info.mtime=0
                    tar.addfile(info,io.BytesIO(data))
                data=manifest.read_bytes();info=tarfile.TarInfo('archive-manifest.json');info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data))
    require(archive.stat().st_size<=MAX_BLOB,'Evidence archive must fit provider transport limit')
    return archive,manifest,large

def main():
    parser=argparse.ArgumentParser();flags=parser.add_mutually_exclusive_group(required=True)
    for name in CAPS:flags.add_argument('--'+name,action='store_true',dest=name.replace('-','_'))
    parser.add_argument('--output',default=str(RUN));args=parser.parse_args()
    stage=next(name for name in CAPS if getattr(args,name.replace('-','_')))
    require(Path(args.output)==RUN and RUN==RUN.absolute()and RUN.parent==Path('/dev/shm'),'Exact registered unique tmpfs diagnostic run path required')
    require(Path(__file__).resolve()==SOURCE/'sc8_run.py','Exact frozen controller path required')
    require(re.fullmatch(r'[0-9a-f]{40}',PARENT) is not None,'Owner must set the actual expected topic commit before preparation/source freeze')
    storage=read(STORAGE_POLICY);storage_sha256=sha(STORAGE_POLICY)
    require(storage.get('schema')=='task1-user-storage-override-v1'and storage.get('storage_capacity_guards_enabled')is False and storage.get('minimum_root_free_bytes')==0 and storage.get('per_run_output_bytes_limit')is None,'Explicit user storage override required')
    active_execution=execution.load_active_policy();execution_limits=execution.resolve_limits(active_execution)
    execution_configured=execution.configure_process(execution_limits)
    execution_refs=execution.execution_policy_refs(active_execution)
    receiptpath=RUN/(stage+'-receipt.json')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);remaining=policy.remaining_seconds(ledger)
        policy.require_time_budget(ledger,RESERVE[stage])
        require(ledger.get('cumulative_time_unlimited')is True and remaining is None,'Explicit validated null cumulative-time override required; finite stage caps remain')
        require(not receiptpath.exists(),'Immutable stage receipt exists; preserve evidence and review recovery explicitly')
        require(all(p.is_file()and os.access(p,os.X_OK)for p in(JAVA,JAVAC))and shutil.which('setpriv'),'Existing JDK21/setpriv required; no installation')
        if stage=='prepare':
            require(not RUN.exists(),'Preparation needs a genuinely new run; preserve existing attempt')
            RUN.mkdir()
            for name in('configs','masks','bases','classes','logs','tmp','postprocess'):(RUN/name).mkdir()
        else:require(RUN.is_dir()and RUN==RUN.resolve()and not RUN.is_symlink(),'Canonical existing registered tmpfs run')
        pid=os.getpid();ticks=bounded.ticks(pid);start=time.monotonic();deadline=start+CAPS[stage]
        parent_cpu_start=time.process_time();child_cpu_start=os.times().children_user+os.times().children_system
        state={'owned':{pid:ticks},'peak_RSS':0,'peak_owned_tmpfs':0,'peak_accounted':0,'phase':stage};stop=threading.Event()
        receipt={'schema':'task1-XY-onecarrier-finite-stage-v1','stage':stage,'status':'failed_preserved','started_utc':bounded.now(),'pid':pid,'proc_start_ticks':ticks,
            'run_id':RUN.name,'case_id':CASE,'remaining_before_seconds':remaining,'cumulative_time_unlimited':True,'stage_cap_seconds':CAPS[stage],'new_native_conditions_started':0,'new_native_conditions_completed':0,
            'evidence_backed_material_reset':'human_reference_or_declared_surrogate; actual_phantom_calibration_not_performed','scenario':'one2000Hz2RHS SC4to8 diagnostic at unchangedXY0.5/bulk18/18/56; no TIS modulation claim','storage_capacity_guards_enabled':False,'storage_policy_sha256':storage_sha256,
            'execution_limits':execution_limits,'execution_configured':execution_configured,'actual_solver_serial':True,'independent_concurrent_solves':1}
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);owned=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));run_bytes=size(RUN)
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],owned),peak_accounted=max(state['peak_accounted'],rss+owned))
            require(time.monotonic()<deadline,'Finite stage deadline exhausted')
            require(rss+owned<=execution_limits['total_memory_bytes'],'Approved aggregate processRSS plus alltask1tmpfs byte cap')
            for path,digest in execution_refs.items():require(sha(path)==digest,'SHA-bound execution policy changed')
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
            large=[(target,Path(path))for target,path in files.items()if Path(path).stat().st_size>32*1024**2]
            if large:
                plan=RUN/'external-git-publication-plan.json'
                new_json(plan,dict(schema='task1-supported-Git-transport-plan-v1',status='requires_supported_Git_transport',
                    expected_parent=parent,repository=REPO,branch=BRANCH,message=message,
                    reason='GitHub REST create-blob input bound observed; use supported normal Git pack transport, no POST retry or service-limit bypass',
                    files={target:dict(local_path=str(path),SHA256=sha(path),bytes=Path(path).stat().st_size)for target,path in files.items()},
                    required_result_receipt=str(RUN/'result-publication.json'),required_receipt_status='published_readback_verified',
                    full_per_file_SHA_bytes_readback_required=True,single_root_owner_required=True,new_PDE_required=False))
                receipt.update(status='requires_supported_Git_transport',transport_plan_sha256=sha(plan),new_PDE_in_transport=0)
                raise RuntimeError('requires_supported_Git_transport; immutable plan preserved; no REST blob POST attempted')
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Remote advanced; no overwrite or force update')
            base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            # Reuse already-full-readback immutable objects from the pinned
            # published human SC2 receipt, chiefly unchanged numerical classes.
            # Every new object still receives a fresh full GET verification.
            cache={}
            for prior_path in(Path('/dev/shm/task1-sc4-2000-20261025-run/result-publication.json'),RUN/'source-publication.json'):
                if not prior_path.is_file():continue
                prior=read(prior_path);prior_sha256=sha(prior_path)
                require(prior['status']=='published_readback_verified'and all(i['readback_passed']for i in prior['files'].values()),'Prior immutable readback proof')
                for item in prior['files'].values():cache[item['Git_blob_SHA']]=dict(item,prior_receipt_sha256=prior_sha256,prior_commit=prior['commit'])
            checkpoints=RUN/'publication-checkpoints';checkpoints.mkdir(exist_ok=True)
            def checkpoint(target,item):
                name=stage+'-'+item['Git_blob_SHA']+'-'+hashlib.sha256(target.encode()).hexdigest()[:16]+'.json'
                path=checkpoints/name
                data=dict(schema='task1-immutable-blob-readback-checkpoint-v1',stage=stage,target=target,proof=item)
                if path.exists():require(read(path)==data,'Immutable blob checkpoint differs')
                else:new_json(path,data)
            for target,path in files.items():
                guard();p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_BLOB,'Regular bounded64MiB publication file')
                raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                old=cache.get(blob)
                if old is not None and old['SHA256']==h and old['bytes']==len(raw):
                    entries.append(dict(path=target,mode='100644',type='blob',sha=blob))
                    proof[target]=dict(SHA256=h,bytes=len(raw),Git_blob_SHA=blob,readback_passed=True,
                        proof_kind='reused_previous_full_immutable_readback',prior_receipt_sha256=old['prior_receipt_sha256'],prior_commit=old['prior_commit'])
                    checkpoint(target,proof[target])
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
                checkpoint(target,proof[target])
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
            import sc8_inputs as inputs
            if stage=='prepare':
                refs=required_old_inputs();refs.update(execution_refs);verify_old(refs)
                new_json(RUN/'execution-limits.json',execution_limits);new_json(RUN/'execution-configured.json',execution_configured)
                new_json(RUN/'blas-runtime.json',observe_blas(execution_limits))
                proposal=inputs.derive_config(inputs.TEMPLATE.read_bytes(),inputs.MASK.read_bytes(),inputs.MATERIAL_INPUT.read_bytes(),RUN)
                with Path(proposal['config_file']).open('xb')as f:f.write(proposal['config_bytes'])
                with Path(proposal['mask_file']).open('xb')as f:f.write(proposal['mask_bytes'])
                with(RUN/'material-input.json').open('xb')as f:f.write(proposal['material_bytes'])
                with(RUN/'contact-receipt.json').open('xb')as f:f.write(proposal['contact_bytes'])
                with(RUN/'storage-policy.json').open('xb')as f:f.write(STORAGE_POLICY.read_bytes())
                new_json(RUN/'material-table.json',proposal['material_table']);new_json(RUN/'config-diff.json',proposal['config_diff'])
                old_publication=read(inputs.COMPARATOR/'result-publication.json')
                new_json(RUN/'comparator-publication.json',dict(status='published_readback_verified',commit=old_publication['commit'],
                    public_native_root='data-native/cloud-sc4-2000-20261025',
                    publication_receipt_sha256=sha(inputs.COMPARATOR/'result-publication.json'),
                    verified_public_files=len(old_publication['files']),new_PDE_in_this_preparation=0))
                new_json(RUN/'material-evidence.json',dict(status='source_verified_for_declared_scope',material_input_sha256=proposal['material_input_sha256'],rows=proposal['material_table']['rows'],material_calibrated=False,phantom_experimentally_validated=False))
                state['phase']='compile_existing_JDK'
                command(['setpriv','--pdeathsig','KILL',str(JAVAC),'-J-Xmx2g','-J-XX:+UseSerialGC','-J-XX:ActiveProcessorCount='+str(execution_limits['java_active_processor_count']),'-J-XX:-UsePerfData','-J-Djava.io.tmpdir='+str(RUN/'tmp'),'-encoding','UTF-8','-d',str(RUN/'classes'),
                    *[str(ROOT/'tis-java'/name)for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java')],str(SOURCE/'SC8SingleCarrierBasis.java')],log=RUN/'logs/compile.log')
                command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount='+str(execution_limits['java_active_processor_count']),'-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'-cp',str(RUN/'classes'),'SC8SingleCarrierBasis','--selftest'],log=RUN/'logs/selftest.log')
                command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount='+str(execution_limits['java_active_processor_count']),'-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'--version'],log=RUN/'logs/java-version.log')
                state['phase']='source_unit_contracts'
                tests=command([sys.executable,'-B','-c','import sys,unittest; suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern="test_*.py"); result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite); sys.exit(0 if result.wasSuccessful() else 1)',str(SOURCE)])
                with(RUN/'logs/input-and-post-contract-tests.log').open('xb')as f:f.write(tests)
                sources=source_files();classes={str(p):sha(p)for p in sorted((RUN/'classes').glob('*.class'))}
                require(classes and len(classes)<128,'Finite complete class pins')
                pre=dict(schema=SCHEMA,status='prepared',repository_root=str(ROOT),run_directory=str(RUN),case_id=CASE,
                    controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),config_file=proposal['config_file'],mask_file=proposal['mask_file'],config_sha256=proposal['config_sha256'],mask_sha256=proposal['mask_sha256'],
                    source_sha256=sources,class_sha256=classes,old_input_sha256=refs,java=str(JAVA),javac=str(JAVAC),
                    material_input_sha256=proposal['material_input_sha256'],contact_receipt_sha256=proposal['contact_receipt_sha256'],material_table_sha256=sha(RUN/'material-table.json'),material_evidence_sha256=sha(RUN/'material-evidence.json'),config_diff_sha256=sha(RUN/'config-diff.json'),
                    native_gates=NATIVE_GATES,single_carrier_SC_adjacent_percent=ADJACENCY_PERCENT,
                    adjacency_scope='Only applicable single-carrier RMS/current/voltage/power metrics across the same2000Hz material/operator XY pair; TIS modulation metrics unavailable',
                    independent_interface_accuracy_gate='Predeclared5percent normalized-L2 numerical screening QA flags; non-aborting diagnostics, not a physical accuracy/activation/safety criterion',
                    source_publication_required_before_phantom_PDE=True,maximum_new_conditions=1,maximum_native_RHS=2,frequencies_Hz=list(inputs.FREQUENCIES),
                    mesh=dict(SC_cells=8,XY_mm=.5,bulk_cells=[18,18,56],native_cells=proposal['native_cells'],XY_columns=proposal['native_XY_columns']),
                    comparator=dict(coarse2000_template_sha256=inputs.TEMPLATE_SHA256,coarse2000_run=inputs.COMPARATOR.name,coarse2000_case=inputs.COMPARATOR_CASE),
                    comparator_publication_receipt_sha256=sha(RUN/'comparator-publication.json'),comparator_member_proof_sha256=sha(RUN/'comparator-member-proof.json'),
                    next_condition_policy='One condition in this finite batch; after actual results, select next scientific step subject to remaining approved budget; no implicit isolated-bipolar assumption',
                    topology_audit=dict(pads=4,independent_outputs=2,pad_nodes={'0':'out0','1':'out1','2':'commonGND','3':'commonGND'},
                        inactive_output_at_other_frequency='0Vthrough50ohm; no open output assumption',actual_equipment_wiring_waveform_verified=False,
                        independent_isolated_bipolar_two_pairs='separate scenario not executed',
                        source_anchors=['tis-java/SelectivityShapeBasis.java:206 e<channels output node else ground',
                            'tis-java/SelectivityShapeBasis.java:209 all output diagonal conductance0.02S',
                            'tis-java/TisSweep.java:73-74 solve(source) RHS0.01A only at selected output; other RHS0',
                            'tis-java/SelectivityShapeBasis.java:259-260 (a==c?0.5:0)-metal divided50ohm']),
                    physics=dict(radius_mm=25,layers_mm=[.1,5,5,15],pads=4,outputs=2,return_topology='commonGND_pads2and3',source_resistance_ohm=50,source_basis_highZ_Vpp=1,phasor='peak,+jomega_t',waveform='sine',carrier_coefficients={'2000':[1,0]},single_frequency_modulation='not_defined_no_TIS_claim',actual_hardware_waveform_and_topology_verified=False),
                    scenario='SC4to8 onecarrier2000Hz diagnostic; unchangedXY0.5/bulk18/18/56/material/contact/pads; actual equipment unverified',material_calibrated=False,
                    limits=dict(CPU=execution_limits['cpu_limit'],simultaneous_PDE_workers=1,java_heap_bytes=execution_limits['java_heap_bytes'],RSS_plus_all_owned_tmpfs_bytes=execution_limits['total_memory_bytes'],blas_threads=execution_limits['blas_threads'],actual_solver_serial=True,max_native_cells=800000,max_run_bytes=None,minimum_root_free_bytes=0,storage_capacity_guards_enabled=False,stage_caps_seconds=CAPS,finite_batch_maximum_seconds=660,cumulative_time_limit_seconds=None,cumulative_time_unlimited=True),
                    policy_refs=policy.policy_refs(ledger),execution_policy_refs=execution_refs,execution_limits_sha256=sha(RUN/'execution-limits.json'),blas_runtime_sha256=sha(RUN/'blas-runtime.json'),
                    manufactured_receipt_sha256=sha(RUN/'manufactured-computation-receipt.json'),manufactured_admission_sha256=sha(RUN/'manufactured-admission.json'),
                    scientific_question='SC4to8 at fixedXY0.5/bulk18/18/56 after actualstableSC4/scalarchecks and common2screeninghold; retain common2point and comparable nearest3point fits on both SC4/SC8 meshes without changing gates',
                    storage_policy_sha256=storage_sha256,proposed_parent_topic_commit=PARENT)
                new_json(RUN/'preregistration.json',pre);controller('prepared',pre);receipt.update(status='prepared_compiled_selftested_no_phantom_PDE',source_input_count=len(refs),compiled_class_count=len(classes))
            else:
                pre=read(RUN/'preregistration.json');source_guard(pre,guard)
                require(pre['schema']==SCHEMA and pre['status']=='prepared'and pre['case_id']==CASE and pre['maximum_new_conditions']==1 and pre['maximum_native_RHS']==2,
                    'Exact immutable one-condition/two-RHS registration')
                if stage=='publish-source':
                    files={PUBLIC_SOURCE+'/'+p.name:p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.java','.md','.json','.txt','.csv')}
                    for name in('preregistration.json','material-table.json','material-evidence.json','config-diff.json','comparator-publication.json','comparator-member-proof.json','material-input.json','contact-receipt.json','storage-policy.json','execution-limits.json','execution-configured.json','blas-runtime.json','manufactured-computation-receipt.json','manufactured-admission.json','prepare-receipt.json'):files[PUBLIC_RUN+'/'+name]=RUN/name
                    for dirname in('configs','masks','classes','logs'):
                        for p in(RUN/dirname).rglob('*'):
                            if p.is_file():files[PUBLIC_RUN+'/'+p.relative_to(RUN).as_posix()]=p
                    for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'):files[PUBLIC_RUN+'/frozen-numerical-sources/'+name]=ROOT/'tis-java'/name
                    result=publish(files,PARENT,'Preregister conditional one2000Hz SC4-to8 diagnostic with unchanged XY, bulk, material and contact')
                    new_json(RUN/'source-publication.json',result);receipt.update(status='source_config_classes_published_readback_verified',source_commit=result['commit'])
                else:
                    publication=read(RUN/'source-publication.json');require(publication['status']=='published_readback_verified'and all(i['readback_passed']for i in publication['files'].values()),'Immutable source/config/classes publication prerequisite')
                    controller('running',pre)
                    basis=RUN/'bases'/CASE
                    if stage=='execute':
                        require(not basis.exists(),'No duplicate native basis/solve')
                        receipt['new_native_conditions_started']=1;state['phase']='actual_one_frequency_two_RHS_PDE'
                        command(['setpriv','--pdeathsig','KILL',str(JAVA),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount='+str(execution_limits['java_active_processor_count']),'-XX:-UsePerfData','-Djava.io.tmpdir='+str(RUN/'tmp'),'-cp',str(RUN/'classes'),'SC8SingleCarrierBasis','--execute-parent',str(pid),str(ticks),pre['config_file'],str(basis)],log=RUN/'logs/native-one-frequency.log')
                        require((basis/'BASIS_COMPLETE').is_file(),'Actual native condition completion marker')
                        validation=read(basis/'validation.json');require(validation['new_native_RHS']==2,'Exact2completed actualRHS')
                        for key,limit in NATIVE_GATES.items():require(0<=validation[key]<=limit,'Frozen native gate failed '+key)
                        pins={str(p):sha(p)for p in sorted(basis.iterdir())if p.is_file()};pins[pre['config_file']]=pre['config_sha256'];pins[str(RUN/'material-input.json')]=pre['material_input_sha256'];pins[str(RUN/'contact-receipt.json')]=pre['contact_receipt_sha256']
                        new_json(RUN/'native-sha256.json',dict(schema='task1-XY-onecarrier-native-raw-pin-v1',case_id=CASE,files=pins,native_conditions_completed=1,native_RHS_completed=2,bytes=sum(p.stat().st_size for p in basis.iterdir()if p.is_file())))
                        source_guard(pre,guard);receipt.update(status='new_native_condition_calculated_five_discrete_gates_passed',new_native_conditions_completed=1,new_native_RHS_completed=2,native_validation=validation,native_file_count=sum(p.is_file()for p in basis.iterdir()))
                    elif stage=='postprocess':
                        require((basis/'BASIS_COMPLETE').is_file()and read(RUN/'execute-receipt.json')['new_native_conditions_completed']==1,'Actual completed new native solve prerequisite')
                        output=RUN/'postprocess';require(not(output/'summary.json').exists()and not(output/'scalars.npz').exists(),'No overwritten postprocess result')
                        manifest=read(RUN/'native-sha256.json');verify_old(manifest['files']);state['phase']='four_layer_native_statistics_and_independent_diagnostics'
                        import sc8_post
                        result=sc8_post.build(RUN,guard,declared_sha256=manifest['files'],deadline_monotonic=deadline-10,include_max_direction=True)
                        guard();new_json(output/'summary.json',result['summary'])
                        import numpy as np
                        with(output/'scalars.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
                        del result;guard();source_guard(pre,guard);verify_old(manifest['files'])
                        new_json(output/'artifact-sha256.json',{p.name:dict(SHA256=sha(p),bytes=p.stat().st_size)for p in output.iterdir()if p.is_file()})
                        receipt.update(status='new_native_postprocessed_SC8_onecarrier_unadopted',new_native_conditions_reused=1,new_PDE_in_postprocess=0,
                            summary_sha256=sha(output/'summary.json'),scalar_archive_sha256=sha(output/'scalars.npz'),full_convergence_validated=False,material_calibrated=False)
                    elif stage=='persist':
                        require(read(RUN/'result-publication.json')['status']=='published_readback_verified','Verified scientific result publication required')
                        verify_old(read(RUN/'native-sha256.json')['files'])
                        for name,entry in read(RUN/'postprocess/artifact-sha256.json').items():require(sha(RUN/'postprocess'/name)==entry['SHA256'],'Final disk artifact identity')
                        receipt.update(status='remote_publication_and_local_tmpfs_dataset_verified_Windows_unverified',new_PDE_in_persistence=0,
                            Windows_storage_verified=False,local_tmpfs_path=str(RUN),local_storage_kind='tmpfs_not_durable_across_environment_shutdown',
                            remote_result_commit=read(RUN/'result-publication.json')['commit'],local_native_and_post_hashes_verified=True)
                    else:
                        state['phase']='immutable_raw_and_diagnostic_publication'
                        executed=read(RUN/'execute-receipt.json')if(RUN/'execute-receipt.json').is_file()else{}
                        post=read(RUN/'postprocess-receipt.json')if(RUN/'postprocess-receipt.json').is_file()else{}
                        new_json(RUN/'publication-controller-snapshot.json',read(RUN/'controller.json'))
                        archive,archive_manifest,large=pack_evidence(guard)
                        files=dict(large)
                        files[PUBLIC_RUN+'/evidence.tar.gz']=archive;files[PUBLIC_RUN+'/evidence-manifest.json']=archive_manifest
                        for directory in(basis,RUN/'postprocess'):
                            if directory.is_dir():
                                for p in directory.iterdir():
                                    if p.is_file():files[PUBLIC_RUN+'/'+p.relative_to(RUN).as_posix()]=p
                        for name in('preregistration.json','native-sha256.json','prepare-receipt.json','execute-receipt.json','postprocess-receipt.json','source-publication.json','publication-controller-snapshot.json'):
                            if(RUN/name).is_file():files[PUBLIC_RUN+'/'+name]=RUN/name
                        if(RUN/'postprocess/summary.json').is_file():files[PUBLIC_REPORT+'/summary.json']=RUN/'postprocess/summary.json'
                        files[PUBLIC_REPORT+'/material-table.json']=RUN/'material-table.json';files[PUBLIC_REPORT+'/material-evidence.json']=RUN/'material-evidence.json';files[PUBLIC_REPORT+'/config-diff.json']=RUN/'config-diff.json'
                        result=publish(files,publication['commit'],'Preserve actual onecarrier SC8 data and paired SC4/SC8 native diagnostics')
                        new_json(RUN/'result-publication.json',result)
                        summary_link=('요약: https://github.com/'+REPO+'/blob/'+result['commit']+'/'+PUBLIC_REPORT+'/summary.json')if(RUN/'postprocess/summary.json').is_file()else'후처리 요약: not_run/실패 보존; 실행 영수증과 실패 로그 참조'
                        completed=executed.get('new_native_conditions_completed',0)==1 and post.get('status')=='new_native_postprocessed_SC8_onecarrier_unadopted'
                        raw_count=sum(1 for name in result['files']if '/bases/'+CASE+'/'in name)
                        body=('실제 SC4 결과의13개 scalar 인접지표가 안정적이고 common2 계면 screening hold가 남은 조건에서만, 별도 유한 배치로SC4→8 진단을 등록했습니다. '
                            '50mm 팬텀과0.1/5/5/15mm 층,XY0.5mm/bulk18·18·56,4개의225mm2 top pad,2출력/commonGND/50ohm,2000Hz·물성·접촉은 동일합니다. '
                            '실제 SC두께를 변경하지 않으며800kcells 제한을 넘는 SC16은 등록하지 않습니다.\n\n'
                            '새 PDE: '+str(executed.get('status','not_run'))+' / completed conditions='+str(executed.get('new_native_conditions_completed',0))+
                            ' / RHS='+str(executed.get('new_native_RHS_completed',0))+'. 후처리: '+str(post.get('status','not_run'))+'. '
                            '단일 carrier이므로 TIS 변조를 계산했다고 표시하지 않습니다. 각 실제Z격자의 물리적 ROI를 독립 계산하며13개1/5/2% 지표와5%normalized-L2 screening은 그대로 유지합니다. '
                            'Common2는 양쪽격자·양쪽계면면 모두2점이며 nearest3도 SC4상부3점과SC8상부3점으로 차수가 같습니다. 두 방법·모든 영역·실패를 함께 보고하며 전체 수렴·물리적 정확도·생리적검증을 주장하지 않습니다.\n\n'
                            '자료: https://github.com/'+REPO+'/tree/'+result['commit']+'/'+PUBLIC_RUN+'\n'+summary_link+'\n\n'
                            '물성·접촉 receipt와 물리 패드마스크를 byte그대로 보존하며 재피팅·물성 재평가는 없습니다. E/phi/grid/contact/source/loss를 보존하고 J는gammaE/sigmaE로 유도합니다. '
                            'native파일 '+str(raw_count)+'개와 기타자료의 SHA/bytes 검증 증거를 연결합니다. CPU최대4·aggregateRSS+모든task1tmpfs8,000,000,000bytes·heap2GiB·800kcells·단일소유잠금을 유지합니다. '
                            'CG/RHS는serial이며 관측CPU/wall비율과 BLAS설정을 기록합니다. 각 배치는 유한시간이며 localtmpfs 환경종료뒤 영속성을 주장하지 않습니다. '
                            '실제장비·Windows동기화·생리적검증은 미확인이고 설치·삭제·보안변경·서비스제한우회·main병합은 하지 않았습니다.')
                        comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='native_and_diagnostics_published_readback_verified'if completed else'partial_or_failed_evidence_published_readback_verified',result_commit=result['commit'],comment_url=comment['html_url'],native_conditions_completed=executed.get('new_native_conditions_completed',0),new_PDE_in_publication=0,public_files_readback_verified=len(result['files']),native_files_readback_verified=raw_count)
                    controller('stage_complete',pre)
        except BaseException as error:
            receipt.update(error_type=type(error).__name__,error=str(error))
            if stage=='execute':
                log=RUN/'logs/native-one-frequency.log'
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
            elapsed=time.monotonic()-start;parent_cpu=time.process_time()-parent_cpu_start;child_cpu=os.times().children_user+os.times().children_system-child_cpu_start;ledger=policy.load_ledger(LEDGER);ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=RUN.name,stage='SC8_onecarrier_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
            temporary=LEDGER.with_name('task1-budget-XY-onecarrier.tmp')
            with temporary.open('xb')as f:f.write(raw)
            os.replace(temporary,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,parent_CPU_seconds=parent_cpu,child_CPU_seconds=child_cpu,total_CPU_seconds=parent_cpu+child_cpu,observed_CPU_seconds_per_wall_second=(parent_cpu+child_cpu)/max(elapsed,1e-12),remaining_approved_seconds=policy.remaining_seconds(ledger),cumulative_time_unlimited=True,resources={k:v for k,v in state.items()if k.startswith('peak_')},
                run_bytes=size(RUN),free_root_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            new_json(receiptpath,receipt)
            for sig,handler in previous.items():signal.signal(sig,handler)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
