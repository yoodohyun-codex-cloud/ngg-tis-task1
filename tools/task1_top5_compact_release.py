#!/usr/bin/env python3
"""Release the already-exported GUI without another native read or HTML copy.

Original failed artifacts remain untouched. Only display pixels are quantized
to Float16 and gzip-packed; all original Float64 catalog/statistical proofs and
shared colour limits remain exact. The mobile source-code wrapping is repaired.
"""
from __future__ import annotations
import argparse
import base64
import copy
from contextlib import ExitStack
from datetime import datetime,timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
import numpy as np
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
MAX_OUTPUT=2200*1024
RELATIVE=.0005
ABSOLUTE=3.1e-8
CODEC="""function f16(b){const s=b&32768?-1:1,e=(b>>10)&31,f=b&1023;return e===0?s*Math.pow(2,-14)*f/1024:e===31?(f?NaN:s*Infinity):s*Math.pow(2,e-15)*(1+f/1024);}
function decode(s,kind){const key=kind+s;if(cache.has(key))return cache.get(key);const raw=atob(s),a=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)a[i]=raw.charCodeAt(i);const v=new DataView(a.buffer),n=raw.length/2,out=kind==='h'?new Int16Array(n):new Float32Array(n);for(let i=0;i<n;i++)out[i]=kind==='h'?v.getInt16(i*2,true):f16(v.getUint16(i*2,true));cache.set(key,out);return out;}
"""


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for chunk in iter(lambda:stream.read(1024**2),b''):h.update(chunk)
    return h.hexdigest()


def stamp():return datetime.now(timezone.utc).isoformat()


def quantize_display(payload):
    output=copy.deepcopy(payload);proof=dict(values=0,max_relative_error_for_abs_over_1e_4=0.,max_absolute_error=0.,relative_bound=RELATIVE,absolute_bound=ABSOLUTE,all_checks_passed=True)
    def one(encoded):
        a=np.frombuffer(base64.b64decode(encoded,validate=True),dtype='<f4');b=a.astype('<f2');use=np.isfinite(a);restored=b.astype(float)
        require(not np.isinf(a).any() and not np.isinf(b).any(),'Finite display values must fit Float16')
        error=abs(restored[use]-a[use]);require(np.all(error<=ABSOLUTE+RELATIVE*abs(a[use])),'Display rounding exceeded the explicit bound')
        nonzero=use&(abs(a)>1e-4)
        if np.any(nonzero):proof['max_relative_error_for_abs_over_1e_4']=max(proof['max_relative_error_for_abs_over_1e_4'],float(np.max(abs(restored[nonzero]-a[nonzero])/abs(a[nonzero]))))
        proof['max_absolute_error']=max(proof['max_absolute_error'],float(np.max(error))if len(error)else 0.);proof['values']+=a.size
        return base64.b64encode(b.tobytes()).decode()
    for case in output['display']['cases']:
        for planes in case['planes'].values():
            planes['xy']=[one(s)for s in planes['xy']];planes['xz']=one(planes['xz']);planes['yz']=one(planes['yz'])
        case['contact_J_RMS']['values_b64']=one(case['contact_J_RMS']['values_b64'])
    output['display']['display_precision']='Float16LE display approximation only: absolute error <=3.1e-8 +0.0005*abs(originalFloat32); all Float64 scientific statistics and colour limits unchanged'
    require(output['catalog']==payload['catalog'],'Scientific catalog must not change')
    require(output['display']['color_limits']==payload['display']['color_limits']and output['display']['contact_color_limits']==payload['display']['contact_color_limits'],'Exact common ranges must not change')
    return output,proof


def transform(original):
    match=re.search(r'<script id="data" type="application/json">(.*?)</script>',original,re.S);require(match is not None,'Bound offline JSON payload required')
    source=json.loads(match.group(1));payload,proof=quantize_display(source)
    active=re.search(r'<script>(.*?)</script>\s*</body>',original,re.S);require(active is not None,'One original active script required')
    script=active.group(1);begin=script.index('function decode(');end=script.index('function color(',begin);script=script[:begin]+CODEC+script[end:]
    script=script.replace('Float32 표시값','Float16 근사 표시값; 원통계 Float64').replace("fmt(v,7)+' '","fmt(v,4)+' '")
    encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode();packed=base64.b64encode(gzip.compress(encoded,mtime=0,compresslevel=9)).decode()
    bootstrap="""(async()=>{'use strict';if(!window.DecompressionStream)throw Error('이 오프라인 GUI는 gzip DecompressionStream을 지원하는 최신 브라우저가 필요합니다.');const t=document.getElementById('packed').textContent,b=Uint8Array.from(atob(t),c=>c.charCodeAt(0));const text=await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text();const e=document.createElement('script');e.id='data';e.type='application/json';e.textContent=text;document.body.append(e);
"""+script+"\n})().catch(e=>{console.error(e);document.body.insertAdjacentText('afterbegin','GUI 로드 오류: '+e.message);});"
    head=original[:match.start()].replace('</style>','code{overflow-wrap:anywhere;word-break:break-all}</style>')
    head=head.replace('지도는 Float32LE native cell 표시값이며 보간하지 않습니다.','지도는 native 셀의 Float16 표시 근사(상대 0.05% + 절대 3.1e−8 이내)이며 보간하지 않습니다. 원래 Float64 정량 통계와 색상 범위는 그대로입니다.')
    script_hash=base64.b64encode(hashlib.sha256(bootstrap.encode()).digest()).decode();head=re.sub(r"script-src 'sha256-[^']+'","script-src 'sha256-"+script_hash+"'",head)
    html=head+'<script id="packed" type="application/octet-stream">'+packed+'</script><script>'+bootstrap+'</script></body></html>'
    return html,source,payload,proof


def browser_verify(html,output):
    from playwright.sync_api import sync_playwright
    errors=[];requests=[];tests=0
    with sync_playwright()as engine:
        # Existing tmpfs keeps browser scratch away from preserved native disk.
        context=engine.chromium.launch_persistent_context('/dev/shm/task1-top5-'+str(os.getpid()),executable_path='/usr/bin/chromium',headless=True,viewport=dict(width=1540,height=1100),args=['--disable-dev-shm-usage','--disk-cache-size=0','--disable-gpu-shader-disk-cache'])
        try:
            page=context.pages[0];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url)if r.url.startswith(('http:','https:'))else None)
            page.set_content(html,wait_until='load',timeout=30000);page.wait_for_function("document.querySelectorAll('.case-card').length===6",timeout=30000)
            require(page.locator('.field-map').count()==page.locator('.contact-map').count()==6,'Six actual field/contact panels required')
            for mode in ('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin'):
                for metric in ('maxTIS','fixedTIS','RMS'):
                    for plane in ('xy','xz','yz'):
                        page.select_option('#mode',mode);page.select_option('#metric',metric);page.select_option('#plane',plane)
                        ranges=page.locator('.field-map').evaluate_all('(a)=>a.map(c=>c.dataset.vmax)');require(len(set(ranges))==1,'Every panel must share one exact colour range');tests+=1
            page.select_option('#mode','skin_contact_only');page.select_option('#metric','maxTIS');page.select_option('#plane','xz');page.wait_for_timeout(50)
            page.screenshot(path=str(output/'preview.png'),full_page=False)
            page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100);width=page.evaluate('document.documentElement.scrollWidth');require(width<=392,'Mobile page overflow remains')
            require(not errors and not requests,'Offline UI emitted errors or external requests')
            return dict(status='passed',actual_data_Chromium=True,combinations=tests,cards=6,contact_maps=6,field_maps=6,mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,source='Bound standalone artifact in memory DOM; browser file navigation is unavailable')
        finally:context.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new release directory required')
    source=ROOT/'docs/TASK1_TOP5_20261022_v2/index.html';planpath=ROOT/'docs/task1-top5-context-20261022/preregistration-v2.json';diagnostic=ROOT/'docs/task1-top5-context-20261022/mobile-overflow-diagnostic.json'
    with ExitStack()as stack:
        stack.enter_context(bounded.dual_lock(ROOT/'.task1-loop.lock'));stack.enter_context(bounded.dual_lock(ROOT/'.task1-execution.lock'));ledger=policy.load_ledger(ROOT/'runtime/task1-budget.json');require(policy.remaining_seconds(ledger)>=180,'Existing finite budget required');require(shutil.disk_usage(ROOT).free>=2*GIB+MAX_OUTPUT,'Preserve2GiB plus compact release maximum')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();status='failed_preserved';error=None;output.mkdir();receipt={};signal.signal(signal.SIGALRM,lambda s,f:(_ for _ in()).throw(TimeoutError('Finite180s compact display stop')));signal.alarm(180)
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();code={}
            for name in('tools/task1_top5_compact_release.py','tests/test_task1_top5_compact_release.py'):
                p=ROOT/name;require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT),'Commit compact release source/tests first');code[str(p)]=sha(p)
            require(sha(source)==json.loads(diagnostic.read_text())['source_HTML_SHA256'],'Original actual GUI changed')
            original_sha=sha(source);plan=json.loads(planpath.read_text())
            for path,digest in plan['input_sha256'].items():require(sha(path)==digest,'Prior exported native input changed: '+path)
            html,original,payload,precision=transform(source.read_text());require(len(html.encode())<MAX_OUTPUT,'Compact GUI exceeds2.15MiB bound')
            with(output/'index.html').open('x')as stream:stream.write(html)
            require(shutil.disk_usage(ROOT).free>=2*GIB,'Original free reserve exhausted');browser=browser_verify(html,output)
            require(sha(source)==original_sha,'Original failed GUI must remain unchanged')
            for path,digest in plan['input_sha256'].items():require(sha(path)==digest,'Native source drift during release')
            require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<3*GIB and shutil.disk_usage(ROOT).free>=2*GIB,'Original RSS/disk caps required')
            cases=payload['display']['cases'];status='compact_dashboard_complete_unadopted';receipt=dict(schema='task1-top5-compact-release-v1',status=status,source_commit=commit,implementation_sha256=code,source_HTML=dict(path=str(source),SHA256=original_sha),source_plan=dict(path=str(planpath),SHA256=sha(planpath)),native_input_SHA_count=len(plan['input_sha256']),native_inputs_unchanged=True,scientific_catalog_unchanged=True,shared_colour_limits_unchanged=True,display_precision=precision,browser_validation=browser,contact_regression={c['id']:c['contact_J_RMS']['regression']for c in cases},native_scalar_primary_proofs={c['id']:c['native_stats_proofs']for c in cases},selected_cases=[r['source_case_id']for r in payload['catalog']['selected_layouts']],catalog_counts=payload['catalog']['counts'],new_PDE=0,new_E_phi_decode=False,new_contact_decode=False,full_convergence_validated=False,experimentally_validated=False,candidate_adopted=False,old_originals_and_failures_preserved=True,artifacts={p.name:dict(SHA256=sha(p),bytes=p.stat().st_size)for p in output.iterdir()if p.is_file()})
        except BaseException as exc:error=type(exc).__name__+': '+str(exc);receipt.update(status='failed_preserved',error=error);status='failed_preserved';raise
        finally:
            signal.alarm(0);elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='compact_GUI_release_no_native_recompute',status=status,seconds=elapsed,error=error,finished_utc=stamp()));bounded.write(ROOT/'runtime/task1-budget.json',ledger);receipt.update(finished_utc=stamp(),resources=dict(wall_seconds=elapsed,max_seconds=180,CPU_count=1,peak_process_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),remaining_approved_seconds=policy.remaining_seconds(ledger));bounded.write(output/'manifest.json',receipt)
        print(json.dumps(dict(status=status,output=str(output),seconds=elapsed)))


if __name__=='__main__':main()
