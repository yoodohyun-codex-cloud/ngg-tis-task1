#!/usr/bin/env python3
"""Verify an already-generated best1/C1 GUI after a depth-test harness error.

No native arrays are decoded and no prior artifact or frozen source is edited.
"""
from __future__ import annotations
import argparse
import base64
import gzip
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import threading
import time
import task1_best1_pair_run as run

ROOT=run.ROOT
SOURCE=Path('/dev/shm/task1-best1-pair-20261025')
PLAN=ROOT/'docs/single-pair-best1-20261025-context/preregistration.json'
MODES=('raw_1Vpp','skin_contact_only')
MATCHES=('ROI_energy_RMS','centre20_E_RMS')

def selections():
    for mode in MODES:
        for match in MATCHES:
            for plane in ('xy','xz','yz'):
                yield [('mode',mode),('match',match),('plane',plane)]
    # XY depth is intentionally disabled in vertical planes.
    for depth in range(5):yield [('plane','xy'),('depth',str(depth))]

def verify_saved(source,plan):
    originals={p.name:p.read_bytes() for p in source.iterdir() if p.is_file()}
    failure=json.loads(originals['manifest.json'])
    run.require(failure['status']=='failed_preserved' and failure['phase']=='actual_GUI_matrix' and
                '<select disabled id="depth">' in failure['error'] and not failure['surviving_owned_children'],
                'Only the preserved disabled-XY-depth harness failure may be recovered')
    metrics=json.loads(originals['metrics.json']);stats=json.loads(originals['spatial-statistics.json'])
    matched=json.loads(run.MATCHED.read_text())
    run.require(metrics==matched['analysis'],'Current matching metadata must remain exact')
    html=originals['index.html'].decode();encoded=re.search(r'<script id="packed" type="application/octet-stream">(.*?)</script>',html,re.S)
    run.require(encoded is not None,'Bound standalone packed GUI required')
    payload=json.loads(gzip.decompress(base64.b64decode(encoded.group(1),validate=True)))
    run.require(payload['analysis']==metrics and all(payload['spatial'][k]==stats[k] for k in ('regions','shape_comparison','proofs')),
                'GUI must preserve all saved Float64 statistics and proofs')
    proof=stats['proofs'];checks=proof['raw_native_reproduction']
    run.require(len(checks)==52 and all(p['passed'] is True and math.isclose(p['actual'],p['saved'],rel_tol=1e-10,abs_tol=1e-12)
                for p in checks.values()),'52 original native scalar/current/loss comparisons required')
    contact=proof['TIS_contact_regression']
    run.require(contact['passed'] is True and len(contact['checks'])==12 and all(c['passed'] is True for c in contact['checks']),
                'Original TIS contact12 checks required')
    run.require(proof['exact_grid_and_fractional_masks'] is True and proof['inputs_unchanged'] is True and
                proof['C1_NPZ_RMS_used'] is False and proof['C1_only_active_frequency_Hz']==3000 and proof['new_PDE']==0,
                'Pure-sine and common fractional native-grid contracts required')
    return html,dict(native_scalar_current_loss_checks=52,TIS_contact_checks=12,metrics_and_GUI_exact=True,
        source_native_proofs_path=str(source/'spatial-statistics.json'),new_native_array_decode=False),originals

def browser(html,output,guard):
    from playwright.sync_api import sync_playwright
    errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='task1-best1-pair-final-',dir='/dev/shm') as temporary:
        scratch=Path(temporary);(scratch/'tmp').mkdir()
        with sync_playwright() as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'profile'),executable_path='/usr/bin/chromium',headless=True,
                viewport=dict(width=1400,height=1000),env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp')),
                ignore_default_args=['--disable-dev-shm-usage'],args=['--disk-cache-size=0','--media-cache-size=0','--disable-gpu-shader-disk-cache'])
            try:
                page=context.pages[0];page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
                page.on('request',lambda request:requests.append(request.url) if request.url.startswith(('http:','https:')) else None)
                page.set_content(html,wait_until='load',timeout=30000)
                page.wait_for_function("document.querySelectorAll('.case-card').length===2",timeout=30000)
                for actions in selections():
                    guard()
                    for key,value in actions:page.select_option('#'+key,value)
                    for selector in ('.field-map','.contact-map'):
                        values=page.locator(selector).evaluate_all('(nodes)=>nodes.map(n=>n.dataset.vmax)')
                        run.require(len(values)==2 and values[0]==values[1] and values[0] is not None,'Shared two-case map range required')
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS');page.select_option('#plane','xz')
                image=page.screenshot(type='jpeg',quality=35,full_page=False)
                if len(image)>64*1024:image=page.screenshot(type='jpeg',quality=15,full_page=False)
                run.require(len(image)<=64*1024,'Bounded screenshot required');run.put_new(output/'preview.jpg',image,output)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100)
                width=page.evaluate('document.documentElement.scrollWidth')
                run.require(width<=392 and not errors and not requests,'Mobile overflow/JS/external request gate failed')
                return dict(status='passed',actual_data_Chromium=True,mode_match_plane_combinations=12,XY_depth_selections=5,
                    field_maps=2,contact_maps=2,mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,
                    harness_fix='Select XY before operating its depth control; generated GUI and all scientific values unchanged')
            finally:context.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.absolute()
    run.require(output==output.resolve() and output.parent==Path('/dev/shm') and output.name.startswith('task1-best1-pair-') and not output.exists(),'Unique existing-tmpfs validation output required')
    with run.bounded.dual_lock(ROOT/'.task1-loop.lock'),run.bounded.dual_lock(ROOT/'.task1-execution.lock'):
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=run.policy.load_ledger(ledgerpath)
        run.require(run.policy.remaining_seconds(ledger)>=120 and run.shutil.disk_usage(ROOT).free>=2*run.GIB+ledgerpath.stat().st_size+16*1024,'Original120s and atomic ledger headroom required')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=run.bounded.ticks(pid)
        state=dict(owned={pid:ticks},peak_RSS=0);stop=threading.Event();receipt=dict(schema='task1-best1-pair-final-validation-v1',status='failed_preserved',started_utc=run.stamp(),new_PDE=0,new_native_array_decode=False)
        def guard():
            owned=run.bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in owned.items() if run.bounded.live(p,t)}
            rss=sum(run.bounded.rss(p) for p in live);state.update(owned=live,peak_RSS=max(state['peak_RSS'],rss))
            run.require(time.monotonic()-start<120 and rss<3*run.GIB and run.shutil.disk_usage(ROOT).free>=2*run.GIB+ledgerpath.stat().st_size+run.LEDGER_GROWTH,'Original time/RSS/disk guard')
        def interrupt(signum,frame):raise TimeoutError(state.get('failure','Finite final validation stop'))
        def monitor():
            while not stop.wait(1):
                try:guard()
                except BaseException as error:state['failure']=str(error);os.kill(pid,signal.SIGTERM);return
        old={s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for s in old:signal.signal(s,interrupt)
        signal.setitimer(signal.ITIMER_REAL,120);thread=threading.Thread(target=monitor,daemon=True);thread.start();output.mkdir()
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();code={}
            for name in ('tools/task1_best1_pair_verify.py','tests/test_task1_best1_pair_verify.py'):
                path=ROOT/name;run.require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT),'Commit final verifier source first');code[str(path)]=run.sha(path)
            plan=json.loads(PLAN.read_text());pins={**plan['input_sha256'],str(PLAN):run.sha(PLAN)}
            for path,digest in pins.items():guard();run.require(run.sha(path)==digest,'Source/preregistered native drift: '+path)
            html,proof,originals=verify_saved(SOURCE,plan);browserproof=browser(html,output,guard)
            for path,digest in pins.items():guard();run.require(run.sha(path)==digest,'Input changed during final check: '+path)
            for name,raw in originals.items():run.require((SOURCE/name).read_bytes()==raw,'Original failed/exported evidence changed')
            receipt.update(status='GUI_and_saved_native_comparison_verified_unadopted',source_commit=commit,implementation_sha256=code,
                source_run=str(SOURCE),original_artifact_sha256={str(SOURCE/name):run.hashlib.sha256(raw).hexdigest() for name,raw in originals.items()},
                preregistration_SHA256=run.sha(PLAN),source_native_inputs_unchanged=True,native_proof_scope=proof,browser_validation=browserproof,
                output_storage='Existing volatile /dev/shm; immutable remote publication/readback required for persistence',persistent_storage_verified=False,
                same_rounded_two_pad_comparison_computed=False,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
                preview=dict(path=str(output/'preview.jpg'),SHA256=run.sha(output/'preview.jpg')))
        except BaseException as error:receipt.update(error_type=type(error).__name__,error=str(error));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2);survivors=run.stop_owned(pid,ticks,state['owned']);receipt['surviving_owned_children']=survivors
            if survivors:receipt.update(status='failed_preserved',error='Owned child cleanup incomplete')
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='best1_pair_validation_only',status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=run.stamp()))
            data=(json.dumps(ledger,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode();run.require(run.shutil.disk_usage(ROOT).free>=2*run.GIB+len(data),'Exact atomic ledger headroom required');run.bounded.write(ledgerpath,ledger)
            receipt.update(finished_utc=run.stamp(),resources=dict(wall_seconds=elapsed,max_seconds=120,CPU_count=1,peak_aggregate_RSS_bytes=state['peak_RSS']),remaining_approved_seconds=run.policy.remaining_seconds(ledger));run.write_new(output/'final-validation.json',receipt,output,final=True)
            for s,handler in old.items():signal.signal(s,handler)
        print(json.dumps(dict(status=receipt['status'],output=str(output))))
        if receipt['status']!='GUI_and_saved_native_comparison_verified_unadopted':raise SystemExit(1)

if __name__=='__main__':main()
