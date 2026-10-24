#!/usr/bin/env python3
"""Finite publication of a verified cached-field comparison, with no local blob copies."""
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import time
import shutil
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
ROOT=Path('/workspace/ngg-tis-task1');sys.path.insert(0,str(ROOT/'tools'))
import task1_bounded_continuation as b
import task1_resource_policy as policy
import task1_top5_remote_publish as previous

REPO='yoodohyun-codex-cloud/ngg-tis-task1'
BRANCH='codex/task1-cloud-restart-20261020'
SOURCE_BRANCH='codex/task1-best1-pair-source-20261025'
EXPECTED_REMOTE='f0749c17b99a4d4096b9b0fdbd070a3518190651'
BASE_LOCAL='317cd38af623d02a902d6b713d6433fb8f8800fc'
SOURCE=Path('/dev/shm/task1-best1-pair-20261025')
VALIDATION=Path('/dev/shm/task1-best1-pair-20261025-validation')
OUTPUT=Path('/dev/shm/task1-best1-pair-publication-20261025')
DEST='docs/TASK1_BEST1_SINGLE_PAIR_20261025'
GIB=1024**3
require=b.require
def sha(data):return hashlib.sha256(data).hexdigest()
def blobsha(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def jsonbytes(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()

def main():
    require(not OUTPUT.exists(),'Preserve all previous publication attempts')
    with b.dual_lock(ROOT/'.task1-loop.lock'),b.dual_lock(ROOT/'.task1-execution.lock'):
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledgerpath)
        require(policy.remaining_seconds(ledger)>=180 and shutil.disk_usage('/dev/shm').free>=64*1024**2,'Existing finite budget/tmpfs required')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=b.ticks(pid)
        state=dict(owned={pid:ticks},peak_RSS=0);stop=threading.Event()
        receipt=dict(schema='task1-best1-pair-publication-v1',status='failed_preserved',started_utc=b.now(),new_PDE=0,remote_updated=False)
        def guard():
            owned=b.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in owned.items() if b.live(p,t)};rss=sum(b.rss(p) for p in live)
            state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss))
            require(time.monotonic()-start<180 and rss<3*GIB and shutil.disk_usage(ROOT).free>=2*GIB+ledgerpath.stat().st_size+8192,'Original time/RSS/disk/atomic-ledger caps')
        def interrupted(sig,frame):raise TimeoutError(state.get('failure','Finite publication stopped'))
        def monitor():
            while not stop.wait(1):
                try:guard()
                except BaseException as error:state['failure']=str(error);os.kill(pid,signal.SIGTERM);return
        old={s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for s in old:signal.signal(s,interrupted)
        signal.setitimer(signal.ITIMER_REAL,180);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        def command(argv,body=None):guard();return previous.guarded_command(argv,root=ROOT,deadline=start+180,input_bytes=body)
        def git(*args):return command(['git','-c','gc.auto=0','-c','pack.threads=1',*args]).strip()
        def api(endpoint,body=None,method='GET'):
            argv=['gh','api','repos/'+REPO+'/'+endpoint,'-X',method]
            if body is not None:argv+=['--input','-']
            return json.loads(command(argv,None if body is None else json.dumps(body,separators=(',',':'),ensure_ascii=False).encode()))
        try:
            guard();OUTPUT.mkdir();local=git('rev-parse','HEAD')
            validation=json.loads((VALIDATION/'final-validation.json').read_text())
            require(local==validation['source_commit'],'Reviewed source commit changed')
            require(validation['status']=='GUI_and_saved_native_comparison_verified_unadopted' and not validation['surviving_owned_children'],'Passed actual GUI and native-result evidence required')
            for path,digest in validation['original_artifact_sha256'].items():require(sha(Path(path).read_bytes())==digest,'Preserved source artifact drift')
            require(sha((VALIDATION/'preview.jpg').read_bytes())==validation['preview']['SHA256'],'Validated screenshot drift')
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==EXPECTED_REMOTE,'Concurrent original topic update; no automatic retry')
            changes=git('diff','--name-status',BASE_LOCAL,local).splitlines();source_files={}
            for line in changes:
                kind,path=line.split('\t');require(kind=='A' and (path.startswith('tools/task1_best1_pair_') or path.startswith('tests/test_task1_best1_pair_') or path.startswith('docs/single-pair-best1-20261025-context/')),'Only reviewed new Task1 files are authorized')
                data=(ROOT/path).read_bytes();require(data==command(['git','show',local+':'+path]).encode(),'Only committed exact research source may be published')
                previous.publication.scan(ROOT/path);source_files[path]=data
            # This source-only branch makes every scientific source commit reviewable.
            require(not git('ls-remote','--heads','origin','refs/heads/'+SOURCE_BRANCH),'Unique source branch required')
            git('push','origin',local+':refs/heads/'+SOURCE_BRANCH)
            require(api('git/ref/heads/'+SOURCE_BRANCH)['object']['sha']==local,'Source branch readback differs')
            # A second view shows the actual field and contact maps, beyond the header.
            from playwright.sync_api import sync_playwright
            with tempfile.TemporaryDirectory(prefix='task1-pair-field-preview-',dir='/dev/shm') as temporary:
                scratch=Path(temporary);(scratch/'tmp').mkdir()
                with sync_playwright() as engine:
                    context=engine.chromium.launch_persistent_context(str(scratch/'profile'),executable_path='/usr/bin/chromium',headless=True,
                        viewport=dict(width=1400,height=1100),env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp')),
                        ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0'])
                    try:
                        page=context.pages[0];page.set_content((SOURCE/'index.html').read_text(),wait_until='load',timeout=30000)
                        page.wait_for_function("document.querySelectorAll('.case-card').length===2",timeout=30000)
                        page.evaluate('window.scrollTo(0,800)');page.wait_for_timeout(50)
                        image=page.screenshot(type='jpeg',quality=70,full_page=False);require(len(image)<256*1024,'Bounded field preview required')
                        (OUTPUT/'fields-preview.jpg').write_bytes(image)
                    finally:context.close()
            readme='''# 현재 best1과 실제 1출력·2전극 비교

[GUI HTML](index.html)을 내려받아 최신 브라우저에서 열면 조작할 수 있습니다. [전기장·접촉 지도 미리보기](fields-preview.jpg), [정량 결과](metrics.json), [공간 통계·원결과 대조](spatial-statistics.json), [최종 화면 검증](validation.json)을 함께 제공합니다.

현재 best1은 rounded-expand-f35b23a22166, 4패드·2출력·공통GND·50Ω·3000/3030Hz입니다. 비교 C1은 실제 귀환을 포함한 15×15mm 사각패드2개,1출력·3000Hz sine·50Ω입니다. 각패드225mm²이나 총면적은900 대450mm²입니다. 같은 rounded 형상의2패드 기저는 없으며 이 계산으로 대체 검증했다고 표시하지 않습니다.

기본 skin8 TIS 기준 목표 r≤5mm·표면에서깊이15–20mm의 체적 에너지 RMS=2.198173 V/m를 맞추면 C1 source1.567712Vpp가 필요합니다. TIS 출력0약1.092516Vpp/출력1약1.105108Vpp 대비 큰출력기준41.86% 증가입니다. 이는 목표장 자체가42% 더 커진다는 뜻이 아닙니다. 전압은 모두50Ω앞 high-Z 전체파형Vpp이며 C1 metal전압은1.365143Vpp입니다. 중심20mm만 맞춘 결과1.564942Vpp는 별도 선택입니다.

ROI RMS 일치에서 C1 RMS전류1.467383mA, 접촉normal Jmax23.471879/J9517.088115A/m²입니다. TIS대비 각각30.51%/40.98% 증가하며 피부SC+dermis bulk벡터 Jmax는23.87%,J95는0.85% 증가합니다. 반면 SC+dermis 총손실은19.92%,source전력은23.11% 감소합니다. 국소최대/면적P95/전체손실은 서로다른부담입니다. 이 한 사각패드쌍의 결과를 모든 단일채널 설계의 최솟값이나 인체안전/활성화 판단으로 확대하지 않습니다.

같은 ROI 에너지 RMS여도 scalar RMS 공간차이의 가중RMS는0.159686V/m(목표RMS대비7.2645%)입니다. 목표체적81.908%가TIS국소RMS의±10%내에 있고 이10%는수치비교폭입니다. 벡터·방향·시간파형은 같지 않습니다. C1단일sine의envelope변조0을 E=0 또는TIS와생리동등성으로 취급하지 않습니다. mean/P10·표층/비표적 분포·동일색상 단면과 전류지도를 GUI에서 함께 봅니다.

새PDE는0입니다. 기존 복소3kHz C1전기장과 density/source/loss를 읽어 순수sine응답을 재구성하고52개scalar/전류/손실값 및TIS접촉12검사를 대조했습니다. C1의기존square3h NPZ는영역마스크에만사용했습니다. 실제화면12조합·깊이5개·모바일390px·JS오류/외부요청0을검증했습니다. 최초표시검사실패(export-attempt.json)는수직단면에서비활성화된XYdepthselector를검사한하네스오류이고원본GUI/계산값은수정하지않았습니다. validation.json은추가native재계산없이동일결과를검증한별도실행입니다.

정량표는Float64,지도는Float16표시근사입니다. 원픽셀|오차|≤3.1e−8+0.0005|원값|이고 진폭A후절대항도|A|배입니다. PBS계면접촉의피부적용·SC/XY/bulk/edge/contact수렴·실험·ETA5001실제부하와장비구동가능성은미검증입니다. 후보채택/활성화/안전검증은없습니다.

작업공간2GiBreserve와원자료를보존하기위해새GUI만기존/dev/shm에서생성했습니다. 이휘발성작업사본자체를영속백업이라고표시하지않습니다. 공개GitHub불변commit의readback검증은게시영수증/PR댓글로별도연결하며전체native기저이관·백업을대신하지않습니다. 기존Top5와원결과는보존하며main은변경하지않습니다.
'''
            (OUTPUT/'README.md').write_text(readme)
            artifacts={DEST+'/index.html':(SOURCE/'index.html').read_bytes(),DEST+'/metrics.json':(SOURCE/'metrics.json').read_bytes(),
                DEST+'/spatial-statistics.json':(SOURCE/'spatial-statistics.json').read_bytes(),DEST+'/export-attempt.json':(SOURCE/'manifest.json').read_bytes(),
                DEST+'/validation.json':(VALIDATION/'final-validation.json').read_bytes(),DEST+'/preview.jpg':(VALIDATION/'preview.jpg').read_bytes(),
                DEST+'/fields-preview.jpg':image,DEST+'/README.md':readme.encode()}
            release=dict(schema='task1-best1-pair-release-v1',status='validated_unadopted_payload',scientific_source_commit=local,
                scientific_calculation_source_commit='ef72425',reference_candidate_id='rounded-expand-f35b23a22166',new_PDE=0,
                same_rounded_two_pad_comparison_computed=False,full_convergence_validated=False,experimentally_validated=False,
                storage='Immutable GitHub commit payload; remote publication/readback evidence delivered separately',
                files={path:dict(SHA256=sha(data),Git_blob_SHA=blobsha(data),bytes=len(data)) for path,data in artifacts.items()})
            (OUTPUT/'manifest.json').write_bytes(jsonbytes(release));artifacts[DEST+'/manifest.json']=jsonbytes(release)
            source_files['tools/task1_best1_pair_publish.py']=Path(__file__).read_bytes()
            files={**source_files,**artifacts};require(sum(map(len,files.values()))<2*1024**2,'Bounded2MiB approved research publication')
            for data in files.values():require(previous.publication.SECRET.search(data) is None,'Public secret-signature scan rejected payload')
            receipt.update(local_source_HEAD=local,old_remote_HEAD=EXPECTED_REMOTE,source_branch=SOURCE_BRANCH,
                files={path:dict(SHA256=sha(data),Git_blob_SHA=blobsha(data),bytes=len(data)) for path,data in files.items()})
            parent=api('git/commits/'+EXPECTED_REMOTE);entries=[]
            for path,data in files.items():
                guard();obj=api('git/blobs',dict(content=base64.b64encode(data).decode(),encoding='base64'),'POST')
                require(obj['sha']==blobsha(data),'Exact remote blob readback differs');entries.append(dict(path=path,mode='100644',type='blob',sha=obj['sha']))
            tree=api('git/trees',dict(base_tree=parent['tree']['sha'],tree=entries),'POST')['sha']
            commit=api('git/commits',dict(message='Compare current best1 TIS and a true single electrode pair at matched target RMS',tree=tree,parents=[EXPECTED_REMOTE,local]),'POST')['sha']
            receipt['created_remote_commit']=commit
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==EXPECTED_REMOTE,'Concurrent advance; orphan objects preserved, no ref overwrite')
            api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH');receipt['remote_updated']=True
            require(api('git/ref/heads/'+BRANCH)['object']['sha']==commit,'Updated ref differs')
            observed=api('git/commits/'+commit)
            require(observed['tree']['sha']==tree and [p['sha'] for p in observed['parents']]==[EXPECTED_REMOTE,local],'Topic integration parents/tree differ')
            readback={}
            for path,data in artifacts.items():
                stored=api('git/blobs/'+blobsha(data));restored=base64.b64decode(stored['content'])
                require(restored==data and sha(restored)==sha(data),'Remote immutable artifact restore differs')
                readback[path]=dict(SHA256=sha(restored),bytes=len(restored),passed=True)
            receipt.update(status='published_and_readback_verified_unadopted',published_commit=commit,remote_artifact_readback=readback,
                local_intentionally_one_topic_merge_child_behind=True,main_merged=False,originals_deleted=False,large_blobs_fetched_to_local_Git=False)
            body=f'''현재 best1 **f35**를 실제 **1출력·2전극**과 같은 목표 RMS에서 비교한 GUI를 추가했습니다. [GUI HTML 내려받기](https://github.com/{REPO}/raw/{commit}/{DEST}/index.html) · [전기장/접촉 지도](https://github.com/{REPO}/blob/{commit}/{DEST}/fields-preview.jpg) · [정의·제한·결과](https://github.com/{REPO}/blob/{commit}/{DEST}/README.md).

기본 skin8 TIS의 r≤5mm/깊이15–20mm ROI 에너지 RMS2.198173V/m를 맞추면 C1은1.567712Vpp(50Ω앞),큰TIS출력1.105108Vpp 대비+41.86%입니다. 접촉Jmax+30.51%/J95+40.98%,피부bulkJmax+23.87%/J95+0.85%이지만 SC+dermis손실−19.92%/source전력−23.11%입니다. 국소부담과적분손실의상충을분리했습니다. 중심20mm만맞춘1.564942Vpp도별도선택입니다.

C1은실제15mm사각2패드450mm², TIS는rounded4패드900mm²로형상이달라TIS방식만의인과효과/모든C1설계최저전압을주장하지않습니다. 동일rounded2패드기저는없고미계산입니다. scalar RMS공간차이7.2645%,목표체적81.908%만국소±10%내이며그10%는수치비교폭입니다. 단일sine변조0과TIS변조·활성화·안전을동일시하지않습니다.

기존복소native재사용,새PDE0;52scalar/전류/손실+TIS접촉12대조,실제GUI12조합/XY깊이5개/모바일390px/JS·외부요청0을검증했습니다. 최초depth검사하네스실패를보존하고기존GUI/원장값수정없이검증만완료했습니다. 전체수렴·실험·PBS피부접촉·장비loading/구동검증·후보채택은보류입니다.

공개commit `{commit}`, 과학source `{local}`; sourcebranch `{SOURCE_BRANCH}`. 기존PR2tree를보존하고reviewedsource를topic에서만통합했으며main미변경/force:false입니다. 모든새공개GUIartifact9개를GitblobAPI로RAM에readback해SHA/bytes를대조했습니다. 기존2GiBreserve/CPU1/RSS3GiB/13800초승인예산을유지했고GUI만기존tmpfs에서생성했습니다. 전체native백업을검증했다고확대하지않습니다. 현재새PDEworker는없고동일rounded2pad등새field계산은영속저장peak+2GiBreserve확보전까지보류입니다. 로컬sourceHEAD는새remote의부모로남아큰blobfetch/forcepush는하지않습니다.'''
            comment=api('issues/2/comments',dict(body=body),'POST');receipt['comment_url']=comment['html_url']
        except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            owned=b.owned_descendants(pid,ticks,state['owned']);survivors={p:t for p,t in owned.items() if p!=pid and b.live(p,t)}
            for p,t in survivors.items():
                if b.live(p,t):
                    try:os.kill(p,signal.SIGKILL)
                    except ProcessLookupError:pass
            receipt['remaining_owned_children']={p:t for p,t in survivors.items() if b.live(p,t)}
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=OUTPUT.name,stage='best1_pair_remote_publication',status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=b.now()))
            data=jsonbytes(ledger);require(shutil.disk_usage(ROOT).free>=2*GIB+len(data),'Exact final atomic ledger peak required');b.write(ledgerpath,ledger)
            receipt.update(finished_utc=b.now(),resources=dict(wall_seconds=elapsed,max_seconds=180,CPU_count=1,peak_aggregate_RSS_bytes=state['peak_RSS']),remaining_approved_seconds=policy.remaining_seconds(ledger),free_workspace_bytes=shutil.disk_usage(ROOT).free)
            if OUTPUT.exists():(OUTPUT/'publication.json').write_bytes(jsonbytes(receipt))
            for s,handler in old.items():signal.signal(s,handler)
        print(json.dumps({k:receipt.get(k) for k in ('status','published_commit','comment_url','remaining_approved_seconds')}))
        if receipt['status']!='published_and_readback_verified_unadopted':raise SystemExit(1)

if __name__=='__main__':main()
