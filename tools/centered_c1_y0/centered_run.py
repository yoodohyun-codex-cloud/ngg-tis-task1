#!/usr/bin/env python3
"""One registered centered-C1 solve and immutable raw-result publication.

New files live in existing tmpfs. The frozen FVM and all old results are kept.
Only the repository's mutable approved time ledger is updated on its disk.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1');SRC=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(SRC))
import task1_bounded_continuation as bounded
import task1_resource_policy as policy
import task1_cloud_batch as core
import centered_inputs
import centered_post
import centered_dashboard

GIB=1024**3
GATES=dict(core.GATES)
REPO='yoodohyun-codex-cloud/ngg-tis-task1'
BRANCH='codex/task1-cloud-restart-20261020'
OLD_REMOTE='ec5b30a9065d9aefd08feeaa51846760fe322a10'
PUBLIC_RUN='data-native/cloud-centered-c1-y0-20261025'
PUBLIC_GUI='docs/TASK1_CENTERED_C1_Y0_20261025'
MAX_NEW=128*1024**2
CASE_ID='centered-square15-C1-y0-xy80-f3000'
require=bounded.require

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
    return h.hexdigest()

def rawsha(raw):return hashlib.sha256(raw).hexdigest()
def gitsha(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def encoded(obj):return (json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
def write_new(path,obj):
    path=Path(path);require(not path.exists(),'Preserve existing evidence: '+str(path))
    with path.open('xb')as stream:stream.write(encoded(obj))

def all_sources():
    files=set(SRC.glob('*.py'))|set(SRC.glob('*.java'))
    # Freeze the complete existing flat research-Python dependency directory,
    # including modules which the postprocessor loads under temporary aliases.
    files.update((ROOT/'tis-java').glob('*.py'))
    files.add(ROOT/'tools/task1_best1_pair_dashboard.py')
    for module in tuple(sys.modules.values()):
        p=getattr(module,'__file__',None)
        if p:
            p=Path(p).resolve()
            if p.is_relative_to(ROOT)and p.suffix=='.py':files.add(p)
    files.update(ROOT/'tis-java'/name for name in ('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'))
    return {str(p):sha(p) for p in sorted(files)}

def browser(payload,run,guard):
    from playwright.sync_api import sync_playwright
    html=centered_dashboard.render(payload);require(len(html.encode())<512*1024,'Bounded standalone GUI required')
    with (run/'results/index.html').open('x')as stream:stream.write(html)
    errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='task1-y0-browser-',dir=run)as temporary:
        tmp=Path(temporary);(tmp/'tmp').mkdir()
        with sync_playwright()as engine:
            context=engine.chromium.launch_persistent_context(str(tmp/'profile'),executable_path='/usr/bin/chromium',headless=True,
                viewport=dict(width=1400,height=1100),env=dict(os.environ,TMPDIR=str(tmp/'tmp'),TMP=str(tmp/'tmp'),TEMP=str(tmp/'tmp')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0'])
            try:
                page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('console',lambda m:errors.append(m.text)if m.type=='error'else None)
                page.on('request',lambda r:requests.append(r.url)if r.url.startswith(('http:','https:'))else None)
                page.set_content(html,wait_until='load',timeout=30000);page.wait_for_function("document.querySelectorAll('.case-card').length===2",timeout=30000)
                count=0
                for mode in ('raw_1Vpp','skin_contact_only'):
                    for criterion in ('ROI_energy_RMS','centre20_E_RMS'):
                        for plane in ('xy','xz','yz'):
                            guard()
                            for key,value in (('mode',mode),('match',criterion),('plane',plane)):page.select_option('#'+key,value)
                            for selector in ('.field-map','.contact-map'):
                                ranges=page.locator(selector).evaluate_all('(a)=>a.map(c=>c.dataset.vmax)')
                                require(len(ranges)==2 and ranges[0]==ranges[1]and ranges[0]is not None,'Two-case shared colour range required')
                            count+=1
                page.select_option('#plane','xy')
                for depth in range(5):page.select_option('#depth',str(depth));guard()
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS');page.select_option('#plane','xz')
                page.evaluate('window.scrollTo(0,850)');page.wait_for_timeout(50)
                image=page.screenshot(type='jpeg',quality=75,full_page=False);require(len(image)<256*1024,'Bounded preview required')
                (run/'results/preview.jpg').write_bytes(image)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100);width=page.evaluate('document.documentElement.scrollWidth')
                require(width<=392 and not errors and not requests,'Actual mobile/JS/offline gate failed')
                return dict(status='passed',actual_data=True,combinations=count,XY_depth_selections=5,mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests)
            finally:context.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    for name in ('prepare','publish-source','execute','publish-results'):group.add_argument('--'+name,action='store_true')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();run=args.output.absolute()
    require(run==run.resolve()and run.parent==Path('/dev/shm')and run.name.startswith('task1-centered-c1-y0-20261025-'),'Own canonical existing-tmpfs run required')
    stage='prepare'if args.prepare else'publish-source'if args.publish_source else'execute'if args.execute else'publish-results'
    cap={'prepare':60,'publish-source':90,'execute':600,'publish-results':300}[stage]
    receiptpath=run/(stage+'-receipt.json');require(not receiptpath.exists(),'One immutable attempt per stage; no retries')
    with bounded.dual_lock(ROOT/'.task1-loop.lock'),bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledgerpath)
        require(policy.remaining_seconds(ledger)>=cap,'Existing remaining authorized time is insufficient')
        require(shutil.disk_usage(ROOT).free>=2*GIB+ledgerpath.stat().st_size+8192,'Original2GiB reserve plus atomic ledger peak required')
        require(shutil.disk_usage('/dev/shm').free>=MAX_NEW+64*1024**2,'Existing tmpfs bound and scratch required')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=bounded.ticks(pid)
        state=dict(status='running',phase=stage,pid=pid,proc_start_ticks=ticks,owned={pid:ticks},peak_RSS=0,peak_tmpfs_bytes=0,peak_accounted_bytes=0)
        receipt=dict(schema='task1-centered-c1-stage-v1',stage=stage,status='failed_preserved',started_utc=bounded.now(),new_PDE=0)
        stop=threading.Event();old={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        def file_bytes(directory):
            value=0
            if directory.exists():
                for path in directory.rglob('*'):
                    try:
                        if path.is_file():value+=path.stat().st_size
                    except FileNotFoundError:pass # Owned browser scratch can disappear normally.
            return value
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items()if bounded.live(p,t)};rss=sum(bounded.rss(p)for p in live)
            used=sum(file_bytes(p) if p.is_dir() else p.stat().st_size for p in Path('/dev/shm').glob('task1-centered-c1-y0-20261025-*'))
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss),peak_tmpfs_bytes=max(state['peak_tmpfs_bytes'],used),peak_accounted_bytes=max(state['peak_accounted_bytes'],rss+used))
            require(time.monotonic()-start<cap and rss+used<3*GIB and used<MAX_NEW,'Finite time/RSS-plus-owned-tmpfs128MiB resource guard')
            require(shutil.disk_usage(ROOT).free>=2*GIB+ledgerpath.stat().st_size+8192,'Preserve original reserve and one atomic ledger file')
            require(not any((run/name).exists()for name in('STOP','needs_attention','needs_physical_validation')),'Run stop marker present')
        def interrupted(sig,frame):raise TimeoutError(state.get('guard_error','Controlled finite stage stop'))
        def monitor():
            last=0
            while not stop.wait(1):
                try:
                    guard()
                    if run.exists()and time.monotonic()-last>=5:
                        public={k:v for k,v in state.items()if k!='owned'};public['updated_utc']=bounded.now();bounded.write(run/'heartbeat.json',public);last=time.monotonic()
                except BaseException as error:state['guard_error']=str(error);os.kill(pid,signal.SIGTERM);return
        for sig in old:signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,input_bytes=None,log=None,native_solve=False):
            guard()
            if native_solve:
                pdeath=shutil.which('setpriv');require(pdeath is not None,'Existing parent-death wrapper required; do not install')
                argv=[pdeath,'--pdeathsig','KILL',*argv]
            child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True,
                env=dict(os.environ,TMPDIR=str(run/'tmp'),TMP=str(run/'tmp'),TEMP=str(run/'tmp')))
            state['owned'][child.pid]=bounded.ticks(child.pid)
            if native_solve:
                receipt.update(new_PDE_started=1,native_RHS_started=1,new_PDE_completed=0)
                state.update(java_pid=child.pid,java_proc_start_ticks=state['owned'][child.pid])
            try:
                output,_=child.communicate(input=input_bytes,timeout=max(.01,cap-(time.monotonic()-start)))
                require(len(output)<=64*1024**2,'Bounded64MiB command response required')
                if log is not None:
                    with Path(log).open('xb')as stream:stream.write(output)
                require(child.returncode==0,'Command failed '+Path(argv[0]).name+' exit'+str(child.returncode));guard();return output
            finally:
                if child.poll()is None:child.kill();child.wait(timeout=3)
        def api(endpoint,obj=None,method='GET'):
            argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
            if obj is not None:argv+=['--input','-']
            return json.loads(command(argv,None if obj is None else json.dumps(obj,separators=(',',':'),ensure_ascii=False).encode()))
        def publish_files(files,parent,message,readback):
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent remote update; preserve results and do not overwrite')
            treebase=api('git/commits/'+parent)['tree']['sha'];entries=[];proof={}
            for target,path in files.items():
                raw=Path(path).read_bytes();require(len(raw)<=32*1024**2,'Native/source file32MiB bound')
                obj=api('git/blobs',dict(content=base64.b64encode(raw).decode(),encoding='base64'),'POST');require(obj['sha']==gitsha(raw),'Exact Git blob differs')
                entries.append(dict(path=target,mode='100644',type='blob',sha=obj['sha']));proof[target]=dict(path=str(path),bytes=len(raw),SHA256=rawsha(raw),Git_blob_SHA=obj['sha'])
            tree=api('git/trees',dict(base_tree=treebase,tree=entries),'POST')['sha'];commit=api('git/commits',dict(message=message,tree=tree,parents=[parent]),'POST')['sha']
            receipt['remote_commit_created']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==parent,'Concurrent remote advance; orphan objects kept')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_ref_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Remote updated commit differs')
            for target in readback:
                item=proof[target];obj=api('git/blobs/'+item['Git_blob_SHA']);raw=base64.b64decode(obj['content'])
                require(len(raw)==item['bytes']and rawsha(raw)==item['SHA256'],'Remote immutable byte/hash restore failed');item['readback_passed']=True
            return dict(commit=commit,files=proof,status='published_readback_verified')
        try:
            if args.prepare:
                require(not run.exists(),'New independent run only');run.mkdir()
                for name in('configs','masks','classes','bases','logs','results','tmp'):(run/name).mkdir()
                state['phase']='prepare_inputs_and_compile'
                case=centered_inputs.build_inputs(run);require(case['id']==CASE_ID,'Exact centered case required')
                historical=core.read(ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/preregistration.json')['java']
                java=historical if Path(historical).is_file() else shutil.which('java')
                candidate=Path(java).with_name('javac') if java else Path('/absent-javac')
                javac=str(candidate) if candidate.is_file() else shutil.which('javac')
                require(javac and java and os.access(javac,os.X_OK) and os.access(java,os.X_OK),'Existing historical Java compiler/runtime required; no installation')
                command([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-J-XX:-UsePerfData','-J-Djava.io.tmpdir='+str(run/'tmp'),'-encoding','UTF-8','-d',str(run/'classes'),
                    *[str(ROOT/'tis-java'/name)for name in('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java')],str(SRC/'CenteredPairBasis.java')],log=run/'logs/compile.log')
                command([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(run/'tmp'),'-cp',str(run/'classes'),'CenteredPairBasis','--selftest'],log=run/'logs/selftest.log')
                command([java,'-XX:-UsePerfData','--version'],log=run/'logs/java-version.log')
                pdeath=shutil.which('setpriv');require(pdeath is not None,'Existing parent-death support required')
                command([pdeath,'--pdeathsig','KILL',shutil.which('true')])
                sources=all_sources();inputs=centered_post.required_inputs()
                prereg=dict(schema='task1-centered-c1-y0-native-v1',status='prepared',repository_root=str(ROOT),run_directory=str(run),case_id=CASE_ID,
                    config_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],controller_path=str(Path(__file__).resolve()),controller_sha256=sha(__file__),
                    source_sha256=sources,class_sha256={str(p):sha(p)for p in(run/'classes').rglob('*.class')},case=case,java=java,
                    old_input_sha256=inputs,gates=GATES,limits=dict(CPU=1,java_heap_bytes=2*GIB,aggregate_RSS_plus_tmpfs_limit_bytes=3*GIB,max_cells=800000,
                        per_condition_seconds=600,minimum_free_repository_bytes=2*GIB,max_owned_tmpfs_bytes=MAX_NEW),
                    physical_question='Translate only the two square-pad centres from y=-10mm to y=0 at x=+-10mm in the same fixed finite D50 phantom. Re-solve the true one-output circuit; never translate old fields.',
                    held='Same-rounded two-pad geometry, full convergence/contact sensitivity, experiment and hardware loading remain unvalidated',new_PDE_planned=1,native_RHS_planned=1,
                    storage='Existing tmpfs; full new raw basis must be published to immutable GitHub blobs and every new native blob restored/hash-checked before a durable-storage claim')
                write_new(run/'preregistration.json',prereg);receipt.update(status='prepared_not_executed',case_id=CASE_ID,preregistration_SHA256=sha(run/'preregistration.json'))
            else:
                pre=core.read(run/'preregistration.json');require(pre['status']=='prepared'and pre['case_id']==CASE_ID,'Exact original prepared plan required')
                case=pre['case'];require(pre['source_sha256']==all_sources(),'Frozen source set changed after preparation')
                for path,digest in {**pre['source_sha256'],**pre['class_sha256'],case['config_file']:pre['config_sha256'],case['mask_file']:pre['mask_sha256']}.items():require(sha(path)==digest,'Prepared input/source/class drift: '+path)
                if args.publish_source:
                    files={}
                    for path in SRC.iterdir():
                        if path.suffix in('.py','.java'):files['tools/centered_c1_y0/'+path.name]=path
                    for path in (run/'preregistration.json',Path(case['config_file']),Path(case['mask_file'])):files[PUBLIC_RUN+'/'+path.relative_to(run).as_posix()]=path
                    result=publish_files(files,OLD_REMOTE,'Register centered y=0 single-pair source and physical inputs before execution',list(files))
                    write_new(run/'source-publication.json',result);receipt.update(status='source_published_not_executed',source_commit=result['commit'])
                elif args.execute:
                    require(not(run/'execution-attempt.json').exists(),'Never rerun an attempted native solve')
                    source=core.read(run/'source-publication.json');require(source['status']=='published_readback_verified','Reviewed source must have immutable readback before execution')
                    for path,digest in pre['old_input_sha256'].items():guard();require(sha(path)==digest,'Old reference drift before solve: '+path)
                    write_new(run/'execution-attempt.json',dict(pid=pid,proc_start_ticks=ticks,source_commit=source['commit'],new_PDE_started=1,native_RHS_started=1,started_utc=bounded.now()))
                    state.update(current_case=CASE_ID,current_config_sha256=pre['config_sha256'],preregistration_sha256=sha(run/'preregistration.json'),source_commit=source['commit'],phase='new_centered_3000Hz_solve')
                    bounded.write(run/'controller.json',{k:v for k,v in state.items()if k!='owned'})
                    command([pre['java'],'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-XX:-UsePerfData','-Djava.io.tmpdir='+str(run/'tmp'),'-cp',str(run/'classes'),'CenteredPairBasis',
                        '--execute-parent',str(pid),str(ticks),case['config_file'],str(run/'bases'/CASE_ID)],log=run/'logs/native-3000Hz.log',native_solve=True)
                    receipt['new_PDE']=1;basis=run/'bases'/CASE_ID;require((basis/'BASIS_COMPLETE').is_file(),'Native complete marker required')
                    validation=core.read(basis/'validation.json')
                    for key,limit in GATES.items():require(isinstance(validation[key],(int,float))and 0<=validation[key]<=limit,'Original native gate failed: '+key)
                    receipt['new_PDE_completed']=1;state['java_pid']=None
                    state['phase']='postprocess_centered_complex_fields';payload=centered_post.postprocess(run,case,guard)
                    require(set(payload)>=set(('analysis','spatial','unit','offcenter_comparison','proofs')),'Complete centered postprocess payload required')
                    payload['provenance']=dict(source_commit=source['commit'],run_id=run.name,case_id=CASE_ID,preregistration_SHA256=sha(run/'preregistration.json'),new_PDE=1,native_RHS=1,
                        output_storage=pre['storage'],persistent_storage_verified=False,previous_GUI=dict(href='https://github.com/'+REPO+'/blob/'+OLD_REMOTE+'/docs/TASK1_BEST1_SINGLE_PAIR_20261025/README.md',commit=OLD_REMOTE))
                    write_new(run/'results/analysis.json',payload['analysis']);write_new(run/'results/statistics.json',{k:payload[k]for k in('offcenter_comparison','proofs','unit')})
                    write_new(run/'results/spatial-statistics.json',{k:payload['spatial'][k]for k in('regions','shape_comparison','proofs')})
                    if 'probe40' in payload:write_new(run/'results/native-phi-probe40.json',payload['probe40'])
                    state['phase']='actual_centered_GUI_validation';browserproof=browser(payload,run,guard)
                    for path,digest in pre['old_input_sha256'].items():guard();require(sha(path)==digest,'Old source changed during new solve: '+path)
                    require(pre['source_sha256']==all_sources(),'Source changed during new execution')
                    write_new(run/'results/validation.json',dict(status='calculated_GUI_verified_unadopted',source_commit=source['commit'],native_gates=validation,
                        browser_validation=browserproof,old_inputs_unchanged=True,new_PDE=1,native_RHS=1,full_convergence_validated=False,experimentally_validated=False,
                        raw_basis_files={p.name:dict(bytes=p.stat().st_size,SHA256=sha(p))for p in basis.iterdir()if p.is_file()}))
                    receipt.update(status='calculated_GUI_verified_unadopted',source_commit=source['commit'],native_gates=validation,browser_validation=browserproof)
                else:
                    source=core.read(run/'source-publication.json');result=core.read(run/'results/validation.json');require(result['status']=='calculated_GUI_verified_unadopted','Completed actual solve and GUI validation required')
                    files={}
                    for path in run.rglob('*'):
                        if path.is_file()and 'tmp'not in path.relative_to(run).parts and path.name not in('controller.json','heartbeat.json')and not path.name.endswith('.partial')and path!=receiptpath:
                            files[PUBLIC_RUN+'/'+path.relative_to(run).as_posix()]=path
                    prior=Path('/dev/shm/task1-centered-c1-y0-20261025-run')
                    for oldpath in prior.rglob('*'):
                        if oldpath.is_file() and 'tmp' not in oldpath.relative_to(prior).parts:files[PUBLIC_RUN+'/prior-prepare-failure/'+oldpath.relative_to(prior).as_posix()]=oldpath
                    for oldpath in Path('/dev/shm/task1-centered-c1-y0-20261025-source').iterdir():
                        if oldpath.suffix in ('.py','.java'):files[PUBLIC_RUN+'/prior-source/'+oldpath.name]=oldpath
                    for name in('index.html','analysis.json','statistics.json','spatial-statistics.json','validation.json','preview.jpg'):
                        files[PUBLIC_GUI+'/'+name]=run/'results'/name
                    result=publish_files(files,source['commit'],'Publish centered y=0 C1 native basis, field comparison and verified GUI',list(files))
                    write_new(run/'immutable-result-publication.json',result)
                    commit=result['commit'];body=f'''사용자의 y=0 배치 지적을 반영해 기존 y=-10mm 단일쌍은 대조군으로 보존하고, 전극 중심(-10,0)/(10,0)mm·15mm사각2패드·1출력·3kHz·50Ω의 새 실제 회로를 재계산했습니다. [새 GUI HTML](https://github.com/{REPO}/raw/{commit}/{PUBLIC_GUI}/index.html) · [배치/전계/접촉 지도](https://github.com/{REPO}/blob/{commit}/{PUBLIC_GUI}/preview.jpg) · [이전위치 대조](https://github.com/{REPO}/blob/{commit}/{PUBLIC_GUI}/statistics.json).

고정 D50/층0.1·5·5·15mm/SC2/XY0.625/bulk14·14·40,기존PBS계면과1Vpp high-Z/50Ω 정의를 유지한1주파수1RHS 새PDE입니다. 기존장을평행이동하지않았습니다. 기존5개native게이트와같은ROI/표시/복소φ팁정의를유지하고원본/실패증거를삭제하지않았습니다. GUI는best1과새중앙C1을같은ROI RMS/중심RMS로각각비교하고,이전y−10대조를별도표시합니다. 수렴/접촉불확실성/실험/장비loading/활성화·안전및후보채택은보류입니다.

sourcecommit `{source['commit']}`, resultcommit `{commit}`. 새raw기저를포함한{len(files)}개공개파일을GitHub불변blob에서RAM으로복원해모든SHA256/bytes를검증했습니다(전체과거native이관완료주장아님). 기존2GiB예약/CPU1/RSS+소유tmpfs3GiB/heap2GiB/원승인시간예산내에수행했고main미변경/force:false입니다.'''
                    comment=api('issues/2/comments',dict(body=body),'POST');receipt.update(status='published_all_native_and_GUI_readback_verified_unadopted',result_commit=commit,source_commit=source['commit'],comment_url=comment['html_url'],all_native_blobs_restored=True)
        except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error),phase=state['phase']);raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            known=bounded.owned_descendants(pid,ticks,state['owned']);children={p:t for p,t in known.items()if p!=pid and bounded.live(p,t)}
            for p,t in children.items():
                if bounded.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            end=time.monotonic()+2
            while any(bounded.live(p,t)for p,t in children.items())and time.monotonic()<end:time.sleep(.05)
            receipt['remaining_owned_children']={p:t for p,t in children.items()if bounded.live(p,t)}
            if receipt['remaining_owned_children']:receipt.update(status='failed_preserved',error='Owned child cleanup incomplete')
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=run.name,stage='centered_C1_'+stage,status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=bounded.now()))
            data=encoded(ledger);require(shutil.disk_usage(ROOT).free>=2*GIB+len(data),'Exact atomic budget-ledger peak must preserve2GiB')
            bounded.write(ledgerpath,ledger);receipt.update(finished_utc=bounded.now(),resources=dict(wall_seconds=elapsed,max_seconds=cap,CPU_count=1,peak_process_RSS_bytes=state['peak_RSS'],peak_owned_tmpfs_bytes=state['peak_tmpfs_bytes'],peak_RSS_plus_owned_tmpfs_bytes=state['peak_accounted_bytes']),remaining_approved_seconds=policy.remaining_seconds(ledger))
            if run.exists()and not receiptpath.exists():write_new(receiptpath,receipt)
            for sig,handler in old.items():signal.signal(sig,handler)
        print(json.dumps({k:receipt.get(k)for k in('stage','status','source_commit','result_commit','comment_url','remaining_approved_seconds')}))
        if receipt['status']=='failed_preserved':raise SystemExit(1)

if __name__=='__main__':main()
