#!/usr/bin/env python3
"""Postprocess and publish one already-completed SC4 basis under the storage override.

No work occurs on import. Only postprocessing and result publication are exposed. No PDE or
preparation/compile/source-publication stage is reachable. The old numerical sources and all run evidence
remain unchanged. The user authorized removal of storage-capacity limits;
CPU/time budgets stay unchanged. No installation, deletion or main merge.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse,base64,hashlib,json,os,re,shutil,signal,subprocess,threading,time
from pathlib import Path
for key in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1')
SOURCE=Path('/dev/shm/task1-all-layer-sc4-check-20261025/source')
RUN=Path('/dev/shm/task1-all-layer-sc4-check-20261025-run')
CASE='baseline-square15-sc-eps1100-sc4-xy80'
SCHEMA='task1-whole-layer-sc4-check-native-v1'
JAVA_HOME=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
JAVA=JAVA_HOME/'java';JAVAC=JAVA_HOME/'javac'
LEDGER=ROOT/'runtime/task1-budget.json'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='ebbad61a7da19d13af17031ae53ab5047c3f71a8'
PUBLIC_RUN='data-native/cloud-all-layer-sc4-check-20261025'
PUBLIC_SOURCE='tools/all_layer_sc4_check_20261025'
PUBLIC_REPORT='docs/TASK1_ALL_LAYER_SC4_CHECK_20261025'
GIB=1024**3;MAX_BLOB=64*1024**2;MAX_STDOUT=96*1024**2
CONTINUATION=Path('/dev/shm/task1-all-layer-storage-unlimited-20261025/continue.py')
STORAGE_POLICY=ROOT/'runtime/task1-storage-policy.json'
ARCHIVED_STORAGE_POLICY=CONTINUATION.with_name('storage-policy.json')
CAPS={'postprocess':300,'publish-results':360}
RESERVE={'postprocess':660,'publish-results':360}
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
    files={p for p in SOURCE.iterdir()if p.is_file()and p.suffix in('.py','.java','.md','.json','.txt')}
    files.update(ROOT/'tis-java'/n for n in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'))
    files.update((ROOT/'tis-java').glob('*.py'))
    files.update(ROOT/'tools'/n for n in('task1_bounded_continuation.py','task1_resource_policy.py'))
    return {str(p):sha(p)for p in sorted(files)}
def required_old_inputs():
    import sc4_post as post
    import all_layer_inputs as inputs
    refs=post.required_inputs()
    refs[str(inputs.TEMPLATE)]=inputs.TEMPLATE_SHA256;refs[str(inputs.MASK)]=inputs.MASK_SHA256
    publication_path=inputs.COMPARATOR/'result-publication.json';publication=read(publication_path)
    require(publication['status']=='published_readback_verified'and re.fullmatch(r'[0-9a-f]{40}',publication['commit'])is not None and
        publication['files']and all(item['readback_passed']for item in publication['files'].values()),
        'Completed first-result immutable full readback prerequisite before extra check')
    prefix='data-native/cloud-all-layer-sc-epsilon-sensitivity-20261025/'
    for path,digest in list(refs.items()):
        p=Path(path)
        if p.is_relative_to(inputs.COMPARATOR):
            target=prefix+p.relative_to(inputs.COMPARATOR).as_posix()
            require(target in publication['files']and publication['files'][target]['SHA256']==digest,
                'Every declared actual SC2 native/post comparator must have verified immutable publication: '+target)
    refs[str(publication_path)]=sha(publication_path)
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
    require(Path(__file__).resolve()==CONTINUATION,'Exact non-PDE continuation source path required')
    storage_policy=read(STORAGE_POLICY);storage_policy_sha256=sha(STORAGE_POLICY);continuation_sha256=sha(CONTINUATION)
    require(storage_policy.get('schema')=='task1-user-storage-override-v1'and storage_policy.get('storage_capacity_guards_enabled')is False and
        storage_policy.get('minimum_root_free_bytes')==0 and storage_policy.get('per_run_output_bytes_limit')is None and
        storage_policy.get('minimum_destination_free_bytes')==0,'Explicit current user storage override required')
    require(sha(ARCHIVED_STORAGE_POLICY)==storage_policy_sha256,'Archived storage-policy byte identity')
    require(re.fullmatch(r'[0-9a-f]{40}',PARENT) is not None,'Owner must set the actual expected topic commit before preparation/source freeze')
    receiptpath=RUN/(stage+'-receipt.json')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);remaining=policy.remaining_seconds(ledger)
        require(remaining>=RESERVE[stage],'Finite first-batch reservation requires '+str(RESERVE[stage])+'s; remaining '+str(remaining))
        require(not receiptpath.exists(),'Immutable stage receipt exists; preserve evidence and review recovery explicitly')
        require(RUN.is_dir()and RUN==RUN.resolve()and not RUN.is_symlink(),'Canonical existing completed SC4 tmpfs run')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});pid=os.getpid();ticks=bounded.ticks(pid);start=time.monotonic();deadline=start+CAPS[stage]
        state={'owned':{pid:ticks},'peak_RSS':0,'peak_owned_tmpfs':0,'peak_accounted':0,'phase':stage};stop=threading.Event()
        receipt={'schema':'task1-all-layer-storage-override-continuation-v1','stage':stage,'status':'failed_preserved','started_utc':bounded.now(),'pid':pid,'proc_start_ticks':ticks,
            'run_id':RUN.name,'case_id':CASE,'remaining_before_seconds':remaining,'stage_cap_seconds':CAPS[stage],'new_native_conditions_started':0,'new_native_conditions_completed':0,
            'evidence_backed_material_reset':'deferred_missing_independent_skin_and_carrier_material_data','scenario':'non-PDE continuation of already-completed SC4 under explicit storage override',
            'continuation_source_sha256':continuation_sha256,'storage_policy_sha256':storage_policy_sha256,
            'storage_override_authorized_utc':storage_policy['authorized_utc'],
            'storage_capacity_guards_enabled':False,'minimum_root_free_bytes':0,'per_run_output_bytes_limit':None,
            'minimum_destination_free_bytes':0,'historical_preregistration_storage_gates':'preserved unchanged; overridden for this continuation',
            'user_reported_destination_capacity_bytes_lower_bound':1000000000000,'destination_capacity_verified':False,
            'Windows_destination_accessible_from_cloud':False,'new_PDE_in_this_continuation':0}
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);owned=sum(size(p)for p in Path('/dev/shm').glob('task1-*'));run_bytes=size(RUN)
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_owned_tmpfs=max(state['peak_owned_tmpfs'],owned),peak_accounted=max(state['peak_accounted'],rss+owned))
            require(time.monotonic()<deadline,'Finite stage deadline exhausted')
            require(rss+owned<=3*GIB,'Original RSS plus all owned tmpfs3GiB RAM gate, not a storage-capacity stop')
            require(sha(CONTINUATION)==continuation_sha256 and sha(STORAGE_POLICY)==storage_policy_sha256 and sha(ARCHIVED_STORAGE_POLICY)==storage_policy_sha256,'Continuation source or explicit storage-policy bytes changed')
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
            for target,path in files.items():
                guard();p=Path(path);require(p.is_file()and not p.is_symlink()and p.stat().st_size<=MAX_BLOB,'Regular bounded64MiB publication file')
                raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
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
            guard();controller('checking')
            override_path=RUN/'storage-override-continuation.json'
            if stage=='postprocess':
                new_json(override_path,dict(schema='task1-non-PDE-storage-override-continuation-v1',
                    authorized_utc=storage_policy['authorized_utc'],continuation_source_sha256=continuation_sha256,
                    storage_policy_sha256=storage_policy_sha256,storage_capacity_guards_enabled=False,
                    minimum_root_free_bytes=0,minimum_destination_free_bytes=0,per_run_output_bytes_limit=None,
                    authorized_storage_budget_expansion=True,CPU_and_time_budget_expanded=False,
                    user_reported_Windows_destination_capacity_bytes_at_least=1000000000000,
                    destination_capacity_independently_verified=False,Windows_destination_accessible_from_cloud=False,
                    historical_native_preregistration_preserved_unchanged=True,new_PDE_in_this_continuation=0))
            else:
                override=read(override_path)
                require(override['continuation_source_sha256']==continuation_sha256 and override['storage_policy_sha256']==storage_policy_sha256,
                    'Postprocessing and publication must use the same frozen continuation and explicit storage override')
            pre=read(RUN/'preregistration.json');source_guard(pre,guard)
            require(pre['schema']==SCHEMA and pre['status']=='prepared'and pre['case_id']==CASE and pre['maximum_new_conditions']==1 and pre['maximum_native_RHS']==8,
                'Exact immutable completed one-check/eight-RHS registration')
            publication=read(RUN/'source-publication.json')
            require(publication['status']=='published_readback_verified'and all(i['readback_passed']for i in publication['files'].values()),'Original frozen source/classes publication prerequisite')
            basis=RUN/'bases'/CASE
            executed=read(RUN/'execute-receipt.json')
            require((basis/'BASIS_COMPLETE').is_file()and executed['new_native_conditions_completed']==1 and executed['new_native_RHS_completed']==8,'Already-completed native SC4 condition required; no PDE entry point')
            controller('running',pre)
            if stage=='postprocess':
                require((basis/'BASIS_COMPLETE').is_file()and read(RUN/'execute-receipt.json')['new_native_conditions_completed']==1,'Actual completed new native solve prerequisite')
                output=RUN/'postprocess';require(not(output/'summary.json').exists()and not(output/'scalars.npz').exists(),'No overwritten postprocess result')
                manifest=read(RUN/'native-sha256.json');verify_old(manifest['files']);state['phase']='four_layer_native_statistics_and_independent_diagnostics'
                import sc4_post
                result=sc4_post.build(RUN,guard,declared_sha256=manifest['files'],deadline_monotonic=deadline-10,include_max_direction=True)
                guard();new_json(output/'summary.json',result['summary'])
                import numpy as np
                with(output/'scalars.npz').open('xb')as f:np.savez_compressed(f,**result['arrays'])
                del result;guard();source_guard(pre,guard);verify_old(manifest['files'])
                new_json(output/'artifact-sha256.json',{p.name:dict(SHA256=sha(p),bytes=p.stat().st_size)for p in output.iterdir()if p.is_file()})
                receipt.update(status='new_native_postprocessed_SC4_adjacency_unadopted',new_native_conditions_reused=1,new_PDE_in_postprocess=0,
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
                files[PUBLIC_SOURCE+'/storage-unlimited-continuation.py']=CONTINUATION
                files[PUBLIC_SOURCE+'/storage-policy.json']=ARCHIVED_STORAGE_POLICY
                result=publish(files,publication['commit'],'Preserve one actual SC4 native check and SC2 adjacency and independent interface diagnostics')
                new_json(RUN/'result-publication.json',result)
                summary_link=('요약: https://github.com/'+REPO+'/blob/'+result['commit']+'/'+PUBLIC_REPORT+'/summary.json')if(RUN/'postprocess/summary.json').is_file()else'후처리 요약: not_run/실패 보존; 실행 영수증과 실패 로그 참조'
                completed=executed.get('new_native_conditions_completed',0)==1 and post.get('status')=='new_native_postprocessed_SC4_adjacency_unadopted'
                raw_count=sum(1 for name in result['files']if '/bases/'+CASE+'/'in name)
                body=('지시 수신·전 층 출처 점검과 첫 SC2 계산·독립 계면 진단을 마친 뒤, 추가 조건은 SC2→SC4 한 번만 선택했습니다. '
                    '네 층 물성·회로·마스크·4개 주파수·파형은 동일하며 SC 두께 방향 셀 수와 명시적 마스크 경로만 달라집니다. '
                    '이는 동일한 미교정 물성 가정의 인접 격자 비교이며 문헌 물성 교정·재현 또는 후보 채택이 아닙니다.\n\n'
                    '새 PDE 상태: '+str(executed.get('status','not_run'))+' / actual completed conditions='+str(executed.get('new_native_conditions_completed',0))+
                    ' / RHS='+str(executed.get('new_native_RHS_completed',0))+'. 후처리: '+str(post.get('status','not_run'))+'. '
                    '기존1% ROI/5% J·접촉V/2% 전력 인접 변화 기준을 유지하며 독립 potential-gradient 진단은 별도 ungated 항목입니다. '
                    '동일2점 SC 계면 fit을 두 격자에 적용하고 SC4 quadratic 진단을 구분합니다. 기존 XY 실패와 전체 수렴·실험·접촉·물성 검증 보류를 유지합니다.\n\n'
                    '자료: https://github.com/'+REPO+'/tree/'+result['commit']+'/'+PUBLIC_RUN+'\n'+summary_link+'\n\n'
                    '실제 게시된 native 파일 '+str(raw_count)+'개와 나머지 자료는 불변 Gitblob SHA/bytes readback으로 확인했습니다. '
                    '기존 SC2 원시 결과·실패·GUI는 보존했습니다. Jtotal/Jconduction은 같은 저장E의 유도량이며 독립 검증이 아닙니다. '
                    '계산 완료·인접 변화 판정·전체 수렴·게시·Windows 저장 상태를 분리합니다. Windows 저장·OneDrive 동기화는 직접 연결이 없어 미확인입니다. '
                    '원래 native 계산의 용량 가드는 역사 자료로 보존하며, 현재 후처리·게시의 용량 가드는 사용자 지시로 해제했습니다. '
                    'CPU1/RSS+모든소유tmpfs3GiB/13800초 시간 예산은 유지하는 단일 소유 유한 실행입니다. '
                    '사용자 저장공간 가드 해제 지시에 따라 최소 여유0/출력 용량 제한 없음 정책을 적용했으며 기존 등록의 용량 가드는 역사 자료로 보존했습니다. '
                    'CPU·RAM·시간·파일 형식·서비스 업로드 제한은 유지합니다. 보고된 Windows1TB 이상 용량과 실제 저장은 cloud에서 검증되지 않았습니다. '
                    '저장 용량 예산 확대는 사용자 지시로 승인되었으며, 이 연속 실행은 추가 PDE 없이 후처리·게시만 합니다. '
                    'CPU·시간 예산 확대·main 병합·설치·삭제는 하지 않았습니다.')
                comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='native_and_diagnostics_published_readback_verified'if completed else'partial_or_failed_evidence_published_readback_verified',result_commit=result['commit'],comment_url=comment['html_url'],native_conditions_completed=executed.get('new_native_conditions_completed',0),new_PDE_in_publication=0,public_files_readback_verified=len(result['files']),native_files_readback_verified=raw_count)
            controller('stage_complete',pre)
        except BaseException as error:
            receipt.update(error_type=type(error).__name__,error=str(error))
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
            ledger['runs'].append(dict(run_id=RUN.name,stage='storage_override_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
            temporary=LEDGER.with_name('task1-budget-storage-override.tmp')
            with temporary.open('xb')as f:f.write(raw)
            os.replace(temporary,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},
                run_bytes=size(RUN),free_root_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            new_json(receiptpath,receipt)
            for sig,handler in previous.items():signal.signal(sig,handler)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
