#!/usr/bin/env python3
"""Complete postprocessing of the successful centered solve, without another PDE.

The sole correction is the explicit frozen research-module search path. All
previous source, failed attempts, raw fields and validation evidence are kept.
"""
import argparse,base64,hashlib,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
for key in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1');RAW=Path('/dev/shm/task1-centered-c1-y0-20261025-run-r2')
SRC=Path('/dev/shm/task1-centered-c1-y0-20261025-source-r2');OUT=Path('/dev/shm/task1-centered-c1-y0-20261025-post-r3')
sys.path[:0]=[str(SRC),str(ROOT/'tis-java'),str(ROOT/'tools')]
import centered_run as r
require=r.require
PARENT='2339c6b4d638294cb615d1eafa7d806b9a838f74'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('publish-source','postprocess','publish-results'));stage=parser.parse_args().stage
    receiptpath=OUT/(stage+'-receipt.json');require(not receiptpath.exists(),'One new immutable recovery stage, no repeat')
    with r.bounded.dual_lock(ROOT/'.task1-loop.lock'),r.bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=r.policy.load_ledger(ledgerpath);cap=90 if stage=='publish-source' else 180 if stage=='postprocess' else 300
        require(r.policy.remaining_seconds(ledger)>=cap,'Existing authorized finite time budget required')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=r.bounded.ticks(pid)
        state=dict(owned={pid:ticks},peak_RSS=0,peak_tmpfs=0,peak_accounted=0);stop=threading.Event()
        receipt=dict(schema='task1-centered-post-recovery-v1',stage=stage,status='failed_preserved',started_utc=r.bounded.now(),new_PDE=0,existing_native_PDE_reused=1)
        def size(path):
            if not path.is_dir():return path.stat().st_size
            total=0
            for item in path.rglob('*'):
                try:
                    if item.is_file():total+=item.stat().st_size
                except FileNotFoundError:pass
            return total
        def guard():
            live=r.bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in live.items()if r.bounded.live(p,t)}
            rss=sum(r.bounded.rss(p)for p in live);used=sum(size(p)for p in Path('/dev/shm').glob('task1-centered-c1-y0-20261025-*'))
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_tmpfs=max(state['peak_tmpfs'],used),peak_accounted=max(state['peak_accounted'],rss+used))
            require(time.monotonic()-start<cap and rss+used<3*r.GIB and used<r.MAX_NEW,'Original finite RSS-plus-tmpfs resource limits')
            require(r.shutil.disk_usage(ROOT).free>=2*r.GIB+ledgerpath.stat().st_size+8192,'Original2GiB plus atomic ledger reserve')
        def interrupted(sig,frame):raise TimeoutError(state.get('failure','Finite postprocess recovery stopped'))
        def monitor():
            last=0
            while not stop.wait(1):
                try:
                    guard()
                    if OUT.exists()and time.monotonic()-last>5:r.bounded.write(OUT/'heartbeat.json',dict(pid=pid,proc_start_ticks=ticks,stage=stage,updated_utc=r.bounded.now(),elapsed_seconds=time.monotonic()-start));last=time.monotonic()
                except BaseException as error:state['failure']=str(error);os.kill(pid,signal.SIGTERM);return
        old={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in old:signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,data=None):
            guard();child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
            state['owned'][child.pid]=r.bounded.ticks(child.pid)
            try:
                raw,_=child.communicate(input=data,timeout=max(.01,cap-time.monotonic()+start));require(child.returncode==0 and len(raw)<=64*1024**2,'Bounded command failed');return raw
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
        def api(endpoint,obj=None,method='GET'):
            argv=['gh','api','repos/'+r.REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            return json.loads(command(argv,None if obj is None else json.dumps(obj,separators=(',',':'),ensure_ascii=False).encode()))
        def publish(files,parent,message):
            require(api('git/ref/heads/'+r.BRANCH)['object']['sha']==parent,'Concurrent remote advance; do not overwrite')
            base=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,path in files.items():
                raw=Path(path).read_bytes();require(len(raw)<=32*1024**2,'Native32MiB individual bound')
                blob=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');require(blob['sha']==r.gitsha(raw),'Exact Git blob identity failed')
                entries.append(dict(path=target,mode='100644',type='blob',sha=blob['sha']));proof[target]=dict(path=str(path),SHA256=r.rawsha(raw),bytes=len(raw),Git_blob_SHA=blob['sha'])
            tree=api('git/trees',dict(base_tree=base,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha'];receipt['created_remote_commit']=commit
            require(api('git/ref/heads/'+r.BRANCH)['object']['sha']==parent,'Concurrent remote update; preserve orphan objects')
            api('git/refs/heads/'+r.BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_updated']=True
            require(api('git/ref/heads/'+r.BRANCH)['object']['sha']==commit,'Updated remote commit differs')
            for target,item in proof.items():
                raw=base64.b64decode(api('git/blobs/'+item['Git_blob_SHA'])['content']);require(len(raw)==item['bytes']and r.rawsha(raw)==item['SHA256'],'Native/source full immutable restore failed');item['readback_passed']=True
            return dict(status='published_readback_verified',commit=commit,files=proof)
        try:
            guard()
            if stage=='publish-source':
                require(not OUT.exists(),'Unique recovery directory only');OUT.mkdir();(OUT/'results').mkdir()
                result=publish({'tools/centered_c1_y0/centered_post_recovery.py':Path(__file__)},PARENT,'Pin postprocess path recovery for already-completed centered C1 solve; no new PDE')
                r.write_new(OUT/'source-publication.json',result);receipt.update(status='recovery_source_published',source_commit=result['commit'])
            else:
                publication=r.core.read(OUT/'source-publication.json');require(publication['status']=='published_readback_verified','Recovery source readback required')
                pre=r.core.read(RAW/'preregistration.json');require(pre['source_sha256']==r.all_sources(),'Original scientific source set drift')
                for path,digest in{**pre['source_sha256'],**pre['class_sha256'],**pre['old_input_sha256']}.items():guard();require(r.sha(path)==digest,'Original source/input/class changed')
                basis=RAW/'bases'/r.CASE_ID;require((basis/'BASIS_COMPLETE').is_file(),'Successful existing native solve required')
                validation=r.core.read(basis/'validation.json')
                for key,limit in r.GATES.items():require(0<=validation[key]<=limit,'Original five native gates required')
                nativepins={str(p):r.sha(p)for p in basis.iterdir()if p.is_file()}
                if stage=='postprocess':
                    require(not(OUT/'results/index.html').exists(),'Do not overwrite derived results')
                    payload=r.centered_post.postprocess(RAW,pre['case'],guard)
                    payload['provenance']=dict(source_commit=PARENT,postprocess_adapter_source_commit=publication['commit'],run_id=OUT.name,native_run_id=RAW.name,case_id=r.CASE_ID,
                        new_PDE=1,native_RHS=1,new_PDE_in_recovery=0,preregistration_SHA256=r.sha(RAW/'preregistration.json'),
                        persistent_storage_verified=False,storage='Existing tmpfs until entire new raw basis is restored from immutable GitHub blobs',
                        previous_GUI=dict(href='https://github.com/'+r.REPO+'/blob/'+r.OLD_REMOTE+'/docs/TASK1_BEST1_SINGLE_PAIR_20261025/README.md',commit=r.OLD_REMOTE))
                    for name,key in(('analysis.json','analysis'),('statistics.json',None),('native-phi-probe40.json','probe40')):
                        obj=payload[key]if key else{k:payload[k]for k in('offcenter_comparison','proofs','unit')};r.write_new(OUT/'results'/name,obj)
                    r.write_new(OUT/'results/spatial-statistics.json',{k:payload['spatial'][k]for k in('regions','shape_comparison','proofs')})
                    browser=r.browser(payload,OUT,guard)
                    for path,digest in nativepins.items():require(r.sha(path)==digest,'Existing native changed during postprocess')
                    for path,digest in pre['old_input_sha256'].items():guard();require(r.sha(path)==digest,'Old reference source changed')
                    require(pre['source_sha256']==r.all_sources(),'Original scientific sources changed after postprocess')
                    r.write_new(OUT/'results/validation.json',dict(status='calculated_GUI_verified_unadopted',source_commit=PARENT,postprocess_adapter_source_commit=publication['commit'],
                        native_gates=validation,native_files_sha256=nativepins,browser_validation=browser,new_native_PDE=1,new_PDE_in_postprocess=0,
                        full_convergence_validated=False,experimentally_validated=False,inputs_unchanged=True))
                    receipt.update(status='postprocess_GUI_verified_unadopted',source_commit=publication['commit'],native_PDE_source_commit=PARENT,browser_validation=browser)
                else:
                    require(r.core.read(OUT/'results/validation.json')['status']=='calculated_GUI_verified_unadopted','Actual postprocess and GUI pass required')
                    files={}
                    for directory,prefix in((RAW,r.PUBLIC_RUN),(OUT,r.PUBLIC_RUN+'/postprocess-recovery'),(Path('/dev/shm/task1-centered-c1-y0-20261025-run'),r.PUBLIC_RUN+'/prior-prepare-failure')):
                        for path in directory.rglob('*'):
                            if path.is_file()and 'tmp'not in path.relative_to(directory).parts and path.name not in('heartbeat.json','controller.json')and not path.name.endswith('.partial')and path!=receiptpath:
                                files[prefix+'/'+path.relative_to(directory).as_posix()]=path
                    for path in Path('/dev/shm/task1-centered-c1-y0-20261025-source').iterdir():
                        if path.suffix in('.py','.java'):files[r.PUBLIC_RUN+'/prior-source/'+path.name]=path
                    for path in(OUT/'results').iterdir():
                        if path.is_file():files[r.PUBLIC_GUI+'/'+path.name]=path
                    result=publish(files,publication['commit'],'Publish centered y=0 C1 native fields, corrected comparison GUI and all failure evidence')
                    r.write_new(OUT/'immutable-result-publication.json',result)
                    commit=result['commit'];body=f'''y=0 중앙배치 수정의 실제 새1주파수·1RHS 계산과 GUI를 완료했습니다. [GUI HTML](https://github.com/{r.REPO}/raw/{commit}/{r.PUBLIC_GUI}/index.html) · [새 배치/전기장/접촉 지도](https://github.com/{r.REPO}/blob/{commit}/{r.PUBLIC_GUI}/preview.jpg) · [y−10 대 y0 정량대조](https://github.com/{r.REPO}/blob/{commit}/{r.PUBLIC_GUI}/statistics.json).

전극중심(-10,0)/(10,0)mm,15mm사각2패드,1출력/귀환포함/3kHz/50Ω입니다. 기존y−10단일쌍과best1 f35는대조군으로보존했고기존장을이동하거나재계산하지않았습니다. 고정D50/층0.1·5·5·15mm,SC2/XY0.625/bulk14·14·40,기존PBS접촉을유지한새FVM해입니다. 기존5native게이트·동일fractional ROI·nativeφ40프로브와GUI12조합/깊이5개/390px 검증을연결했습니다. fullconvergence/실험/장비부하/안전·활성화/후보채택은보류입니다.

새native source `{PARENT}`, 경로의존성후처리복구source `{publication['commit']}`, 결과 `{commit}`. 새PDE는전체1회뿐이고복구에서는0회입니다. 준비PATH실패와후처리import실패는source/receipt와함께보존했습니다. 원시E/φ/grid/density/source/loss및모든신규연구파일{len(files)}개를GitHub불변blob에서RAM으로복원해전부SHA256/bytes검증했습니다. 이는과거전체native이관완료주장이아닙니다. 기존2GiB예약/CPU1/heap2GiB/RSS+소유tmpfs3GiB/승인시간예산을유지했고main미변경/force:false입니다.'''
                    comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='all_native_and_GUI_immutable_readback_verified_unadopted',source_commit=publication['commit'],result_commit=commit,comment_url=comment['html_url'],native_files_restored=len(nativepins),public_files_restored=len(files))
        except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=r.bounded.owned_descendants(pid,ticks,state['owned']);children={p:t for p,t in known.items()if p!=pid and r.bounded.live(p,t)}
            for p,t in children.items():
                if r.bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            end=time.monotonic()+2
            while any(r.bounded.live(p,t)for p,t in children.items())and time.monotonic()<end:time.sleep(.05)
            receipt['remaining_owned_children']={p:t for p,t in children.items()if r.bounded.live(p,t)}
            if receipt['remaining_owned_children']:receipt.update(status='failed_preserved',error='Owned child cleanup incomplete')
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=OUT.name,stage='centered_C1_recovery_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=r.bounded.now()))
            require(r.shutil.disk_usage(ROOT).free>=2*r.GIB+len(r.encoded(ledger)),'Exact atomic ledger peak preserves2GiB');r.bounded.write(ledgerpath,ledger)
            receipt.update(finished_utc=r.bounded.now(),resources=dict(wall_seconds=elapsed,max_seconds=cap,CPU_count=1,peak_RSS_bytes=state['peak_RSS'],peak_owned_tmpfs_bytes=state['peak_tmpfs'],peak_accounted_memory_bytes=state['peak_accounted']),remaining_approved_seconds=r.policy.remaining_seconds(ledger))
            if OUT.exists()and not receiptpath.exists():r.write_new(receiptpath,receipt)
            for sig,handler in old.items():signal.signal(sig,handler)
        print(json.dumps({key:receipt.get(key)for key in('stage','status','source_commit','result_commit','comment_url','remaining_approved_seconds')}))
        if receipt['status']=='failed_preserved':raise SystemExit(1)

if __name__=='__main__':main()
