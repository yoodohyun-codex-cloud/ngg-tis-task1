#!/usr/bin/env python3
"""One finite locked postprocess/export owner. No PDE, installation, or cleanup."""
import sys
sys.dont_write_bytecode=True
import argparse,base64,gzip,hashlib,json,os,re,shutil,signal,subprocess,tempfile,threading,time
from pathlib import Path
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1')
RUN=Path('/dev/shm/task1-manual-ranges-20261025-r2')
SRC=RUN/'source';OUT=RUN/'results'
REPO='yoodohyun-codex-cloud/ngg-tis-task1';BRANCH='codex/task1-cloud-restart-20261020'
PARENT='a5a78f28a364643feeacf59afe225e49f2b8fe79'
PUBLIC='docs/TASK1_MANUAL_RANGES_20261025';PUBLIC_SRC='tools/manual_ranges_20261025'
BASE=Path('/dev/shm/task1-fixed-scales-20261025-r2/results/index.html')
LEDGER=ROOT/'runtime/task1-budget.json';GIB=1024**3
sys.path[:0]=[str(SRC),str(ROOT/'tools')]
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for block in iter(lambda:f.read(1024**2),b''):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write_new(p,obj):
    with Path(p).open('x',encoding='utf-8')as f:json.dump(obj,f,ensure_ascii=False,allow_nan=False,indent=2)
def source_pins():return {str(p):sha(p)for p in SRC.iterdir()if p.suffix in ('.py','.ps1')}
def total_size(p):return sum(x.stat().st_size for x in Path(p).rglob('*')if x.is_file())

def browser_check(html,guard,state):
    from manual_browser import check
    return check(html,guard,state,OUT)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('prepare','publish-source','build','publish-results','export'));stage=parser.parse_args().stage
    receiptpath=RUN/(stage+'-receipt.json');require(not receiptpath.exists(),'No repeated immutable stage; preserve failure and use reviewed recovery')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledger=policy.load_ledger(LEDGER);cap={'prepare':45,'publish-source':90,'build':240,'publish-results':240,'export':150}[stage]
        require(policy.remaining_seconds(ledger)>=cap,'Finite approved time admission failed')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=bounded.ticks(pid)
        state=dict(owned={pid:ticks},peak_RSS=0,peak_tmpfs=0,peak_accounted=0);stop=threading.Event()
        receipt=dict(schema='task1-field-shape-stage-v1',stage=stage,status='failed_preserved',started_utc=bounded.now(),pid=pid,proc_start_ticks=ticks,new_PDE=0,remaining_before=policy.remaining_seconds(ledger))
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)}
            rss=sum(bounded.rss(p)for p in live);used=total_size(RUN)+total_size('/dev/shm/task1-manual-ranges-20261025')+total_size('/dev/shm/task1-all-layer-sensitivity-20261025')+total_size('/dev/shm/task1-anand-bulk-evidence-20261025')+total_size('/dev/shm/task1-fixed-scales-20261025-r2')+total_size('/dev/shm/task1-fixed-scales-20261025')+total_size('/dev/shm/task1-paper-figure-20261025')+total_size('/dev/shm/task1-field-shape-export-20261025')+sum(total_size(p)if p.is_dir()else p.stat().st_size for p in Path('/dev/shm').glob('task1-centered-c1-y0-20261025-*'))
            if state.get('scratch')is not None and state['scratch'].exists():used+=total_size(state['scratch'])
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_tmpfs=max(state['peak_tmpfs'],used),peak_accounted=max(state['peak_accounted'],rss+used))
            require(time.monotonic()-start<cap and rss+used<3*GIB and total_size(RUN)<128*1024**2,'Finite RSS+tmpfs/time/output gate')
            require(shutil.disk_usage(ROOT).free>=2*GIB+LEDGER.stat().st_size+8192,'Original2GiB plus compact atomic-ledger reserve')
        def interrupt(sig,frame):raise TimeoutError(state.get('failure','Finite field-shape stage interrupted'))
        def monitor():
            last=0
            while not stop.wait(1):
                try:
                    guard()
                    if time.monotonic()-last>5:
                        # Mutable live checkpoint only; immutable receipts remain separate.
                        (RUN/'heartbeat.json').write_text(json.dumps(dict(stage=stage,pid=pid,proc_start_ticks=ticks,updated_utc=bounded.now(),new_PDE=0)))
                        last=time.monotonic()
                except BaseException as e:state['failure']=str(e);os.kill(pid,signal.SIGTERM);return
        old={s:signal.getsignal(s)for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for s in old:signal.signal(s,interrupt)
        signal.setitimer(signal.ITIMER_REAL,cap);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,body=None):
            guard();child=subprocess.Popen(argv,cwd=SRC,stdin=subprocess.PIPE if body is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,
                env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(RUN)))
            state['owned'][child.pid]=bounded.ticks(child.pid)
            try:
                raw,err=child.communicate(input=body,timeout=max(.01,cap-time.monotonic()+start))
                if child.returncode!=0 and argv[0]==sys.executable:(RUN/'subprocess-failure.log').write_bytes(raw+err)
                require(child.returncode==0 and len(raw)<64*1024**2,'Bounded subprocess failed: '+(err+raw[-1600:]).decode(errors='replace')[:1800]);return raw
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
        def api(endpoint,obj=None,method='GET'):
            argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            return json.loads(command(argv,None if obj is None else json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()))
        def publish(files,parent,message):
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent remote update; no overwrite')
            treebase=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,p in files.items():
                raw=Path(p).read_bytes();require(len(raw)<32*1024**2,'32MiB individual publication gate')
                expected=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                item=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');require(item['sha']==expected,'Exact Gitblob identity')
                entries.append(dict(path=target,mode='100644',type='blob',sha=expected));proof[target]=dict(SHA256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),Git_blob_SHA=expected)
            tree=api('git/trees',dict(base_tree=treebase,tree=entries),'POST')['sha']
            commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['remote_commit_created']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Remote advanced; preserve immutable objects')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_ref_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Remotehead mismatch')
            for target,item in proof.items():
                raw=base64.b64decode(api('git/blobs/'+item['Git_blob_SHA'])['content']);require(len(raw)==item['bytes']and hashlib.sha256(raw).hexdigest()==item['SHA256'],'Immutable full readback mismatch');item['readback_passed']=True
            return dict(status='published_readback_verified',commit=commit,files=proof)
        try:
            guard()
            import field_shape_data as data
            if stage=='prepare':
                pins=data.required_inputs();pins[str(BASE)]=sha(BASE)
                tests=command([sys.executable,'-B','-c','import sys,unittest; suite=unittest.defaultTestLoader.discover(sys.argv[1],pattern="test_*.py"); result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite); sys.exit(0 if result.wasSuccessful() else 1)',str(SRC)]).decode()
                (RUN/'prepare-tests.log').write_text(tests)
                write_new(RUN/'preregistration.json',dict(schema='task1-field-shape-preregistration-v1',question='Let the user manually edit every plotted axis and colour range, keep edits across variable changes, expose clipping and settingsJSON; preserve scientific data',
                    new_PDE=0,parent_topic_commit=PARENT,native_source_result_commit='b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe',cached_display_result_commit='b7460d42d63381a53c36daf7d2826286ddb9131b',source_sha256=source_pins(),input_sha256=pins,CPU=1,RSS_plus_owned_tmpfs_bytes=3*GIB,max_new_tmpfs_bytes=128*1024**2,
                    minimum_free_disk_bytes=2*GIB,new_validation='Manual controls on22charts viaactualUI; common andindividualminmax,invalidtransaction,persistence,shiftedtime10-20mswaveforms,settingsroundtrip,clipping,mobileoffline; packedscientificdataunchanged',
                    Windows_destination_connected=False,OneDrive_sync_verified=False,full_convergence_validated=False,fat_new_batch_executed=False))
                receipt['status']='prepared_preregistered_no_PDE'
            else:
                pre=read(RUN/'preregistration.json');require(pre['source_sha256']==source_pins(),'Preregistered source drift')
                for p,digest in pre['input_sha256'].items():guard();require(sha(p)==digest,'Pinned input drift: '+p)
                if stage=='publish-source':
                    files={PUBLIC_SRC+'/'+p.name:p for p in SRC.iterdir()if p.suffix in ('.py','.ps1')}
                    files[PUBLIC+'/preregistration.json']=RUN/'preregistration.json'
                    result=publish(files,PARENT,'Pin user-editable axes/colour controls, persistent settings and bounded waveform resampling sources')
                    write_new(RUN/'source-publication.json',result);receipt.update(status='source_published_readback_verified',source_commit=result['commit'])
                else:
                    source=read(RUN/'source-publication.json');require(source['status']=='published_readback_verified','Source publication prerequisite')
                    if stage=='build':
                        import field_shape_gui as gui
                        payload=data.build(guard,pre['input_sha256']);payload['display_source_commit']=source['commit']
                        require(payload['analysis']==read('/dev/shm/task1-centered-c1-y0-20261025-final-r4/results/analysis.json'),'Frozen statistics changed')
                        write_new(OUT/'field-shape.json',payload)
                        write_new(OUT/'default-range-reference.json',payload['fixed_scale_contract'])
                        write_new(OUT/'manual-range-proof.json',payload['manual_range_proof'])
                        html=gui.render(BASE.read_text(),payload)
                        with (OUT/'index.html').open('x')as f:f.write(html)
                        browser=browser_check(html,guard,state)
                        for p,digest in pre['input_sha256'].items():guard();require(sha(p)==digest,'Pinned input changed after display')
                        write_new(OUT/'validation.json',dict(status='cached_fields_GUI_verified_unadopted',source_commit=source['commit'],native_source_result_commit='b7ef9aaef9dd82ce0c3bfa31f16043080519fbfe',cached_display_result_commit='b7460d42d63381a53c36daf7d2826286ddb9131b',parent_topic_commit=PARENT,new_PDE=0,
                            input_sha256=pre['input_sha256'],proofs=payload['proofs'],paper_proofs=payload['paper_proofs'],paper_reference=payload['paper_reference'],fixed_scale_contract=payload['fixed_scale_contract'],fixed_scale_proof=payload['fixed_scale_proof'],manual_range_proof=payload['manual_range_proof'],browser=browser,Windows_write_verified=False,OneDrive_sync_verified=False,
                            full_convergence_validated=False,fat_new_batch_executed=False,experimentally_validated=False))
                        receipt.update(status='cached_field_shape_GUI_verified',browser=browser)
                    elif stage=='publish-results':
                        require(read(OUT/'validation.json')['status']=='cached_fields_GUI_verified_unadopted','Actual GUI validation prerequisite')
                        files={PUBLIC+'/'+p.name:p for p in OUT.iterdir()if p.is_file()}
                        for name in ('prepare-receipt.json','prepare-tests.log','build-receipt.json'):files[PUBLIC+'/evidence/'+name]=RUN/name
                        result=publish(files,source['commit'],'Publish manual ranges for all22numericalplots, clipping diagnostics and settingsJSON controls')
                        write_new(RUN/'result-publication.json',result);receipt.update(status='GUI_published_readback_verified',result_commit=result['commit'])
                    else:
                        import windows_export
                        oldpub=read('/dev/shm/task1-centered-c1-y0-20261025-final-r4/immutable-result-publication.json');newpub=read(RUN/'result-publication.json')
                        entries=[]
                        for pub in (oldpub,newpub):
                            require(pub['status']=='published_readback_verified','Only fully readback verified results exportable')
                            for path,item in pub['files'].items():
                                require(item['readback_passed'],'Readback prerequisite')
                                entries.append(dict(path=path,commit=pub['commit'],SHA256=item['SHA256'],bytes=item['bytes']))
                        script=windows_export.render(entries)
                        with (OUT/'Save-TIS-Results.ps1').open('x',encoding='ascii')as f:f.write(script)
                        write_new(OUT/'windows-export-manifest.json',dict(schema='task1-windows-export-manifest-v1',files=entries,total_bytes=sum(x['bytes']for x in entries),
                            Windows_files_verified=False,OneDrive_sync_verified=False,private_destination_excluded=True,automatic_sync_configured=False))
                        files={PUBLIC+'/'+name:OUT/name for name in ('Save-TIS-Results.ps1','windows-export-manifest.json')}
                        result=publish(files,newpub['commit'],'Add immutable SHA256-verified Windows download handoff without exposing private destination')
                        write_new(RUN/'export-publication.json',result)
                        body='''GUI의 모든 수치 그래프22개에 공통/개별 수동 눈금 조절을 추가했습니다. 지도와배치도의X/Y좌표,전기장/J색minmax,파형의시간/전기장축,두프로파일축을직접입력하고변수변경후유지합니다. 잘못된입력은적용전거부하며설정JSON저장/불러오기/초기화를지원합니다. 시간축변경시기존복소장에서해당실제시간파형을다시표시하고색범위외개수/빗금을원값hover와구분합니다.

GUI: https://github.com/'''+REPO+'/raw/'+newpub['commit']+'/'+PUBLIC+'''/index.html

Windows SHA256 다운로드: https://github.com/'''+REPO+'/raw/'+result['commit']+'/'+PUBLIC+'''/Save-TIS-Results.ps1

기존자료/Float64통계/실패/수렴보류를보존했고이번GUI작업의새PDE/원시복소장decode는0입니다. 사용자가확대한전층물성재계산은별도감사/민감도신규배치로추적하며이GUI로완료처리하지않습니다. 최신Windows저장대상은비공개runtime설정에변경했지만현재cloud에는C:직접연결이없어실제저장/OneDrive동기화는미확인입니다.'''
                        comment=api('issues/2/comments',dict(body=body),'POST')
                        receipt.update(status='Windows_handoff_published_direct_connection_unavailable',result_commit=result['commit'],comment_url=comment['html_url'],download_files=len(entries),download_bytes=sum(x['bytes']for x in entries))
        except BaseException as e:receipt.update(error_type=type(e).__name__,error=str(e));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=bounded.owned_descendants(pid,ticks,state['owned'])
            for p,t in known.items():
                if p!=pid and bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            elapsed=time.monotonic()-start;ledger=policy.load_ledger(LEDGER)
            ledger['spent_seconds']+=elapsed;ledger.setdefault('runs',[]).append(dict(run_id=RUN.name,stage='field_shape_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            raw=json.dumps(ledger,ensure_ascii=False,separators=(',',':')).encode()
            require(shutil.disk_usage(ROOT).free>=2*GIB+len(raw)+8192,'Exact compact atomic-ledger write admission')
            temporary=LEDGER.with_name('task1-budget-field-shape.tmp')
            with temporary.open('xb')as f:f.write(raw)
            os.replace(temporary,LEDGER)
            receipt.update(finished_utc=bounded.now(),elapsed_seconds=elapsed,remaining_approved_seconds=policy.remaining_seconds(ledger),resources={k:v for k,v in state.items()if k.startswith('peak_')},
                free_workspace_bytes=shutil.disk_usage(ROOT).free,remaining_owned_children={str(p):t for p,t in known.items()if p!=pid and bounded.live(p,t)})
            write_new(receiptpath,receipt)
            for s,h in old.items():signal.signal(s,h)
            print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':main()
