#!/usr/bin/env python3
"""One finite, preregistered best1/C1 comparison and offline GUI export.

Existing native fields only; no PDE, installation, source mutation or cleanup.
Preparation and execution share both existing locks and the approved ledger.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'
import task1_bounded_continuation as bounded
import task1_resource_policy as policy
import task1_best1_pair_metrics as metrics
import task1_best1_pair_native as native
import task1_best1_pair_dashboard as dashboard

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
OUTPUT_CAP=384*1024
HTML_CAP=240*1024
FINAL_RESERVE=48*1024
LEDGER_GROWTH=8*1024
CONDITION=ROOT/'docs/cloud-rounded-drive-expansion-20261021T214000Z/rounded-expand-f35b23a22166/condition.json'
UNIT_CACHE=ROOT/'docs/cloud-rounded-single-pair-20261021T212000Z/summary.json'
C1_SUMMARY=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-C1pair0-xy80/summary.json'
FEEDBACK=ROOT/'docs/single-pair-best1-20261025-context/feedback-inventory.json'
MATCHED=ROOT/'docs/single-pair-best1-20261025-context/matching-metadata.json'
require=bounded.require

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
    return h.hexdigest()

def encode_json(value):return (json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()

def put_new(path,data,output=None,*,final=False):
    require(not Path(path).exists(),'Preserve existing artifact: '+str(path))
    ledger_bytes=(ROOT/'runtime/task1-budget.json').stat().st_size
    reserve=0 if final else FINAL_RESERVE
    same_device=Path(path).parent.stat().st_dev==ROOT.stat().st_dev
    require(shutil.disk_usage(ROOT).free>=2*GIB+(len(data)+reserve if same_device else 0)+ledger_bytes+LEDGER_GROWTH,'Prospective write must preserve reserve and the single new atomic ledger file')
    if not same_device:require(shutil.disk_usage(Path(path).parent).free>=len(data)+reserve,'Existing tmpfs output headroom required')
    if output is not None:
        used=sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        require(used+len(data)<=OUTPUT_CAP-reserve,'Prospective output bytes exceed preregistered cap')
    with Path(path).open('xb') as stream:stream.write(data)

def write_new(path,value,output=None,*,final=False):put_new(path,encode_json(value),output,final=final)

def stop_owned(pid,ticks,known):
    owned=bounded.owned_descendants(pid,ticks,known)
    children={p:t for p,t in owned.items() if p!=pid and bounded.live(p,t)}
    for p,t in children.items():
        if bounded.live(p,t):
            try:os.kill(p,signal.SIGTERM)
            except ProcessLookupError:pass
    end=time.monotonic()+2
    while time.monotonic()<end and any(bounded.live(p,t) for p,t in children.items()):time.sleep(.05)
    for p,t in children.items():
        if bounded.live(p,t):
            try:os.kill(p,signal.SIGKILL)
            except ProcessLookupError:pass
    end=time.monotonic()+1
    while time.monotonic()<end and any(bounded.live(p,t) for p,t in children.items()):time.sleep(.05)
    return {p:t for p,t in children.items() if bounded.live(p,t)}

def source_pins(commit):
    paths={Path(__file__).resolve()}
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.is_relative_to(ROOT) and path.suffix=='.py':paths.add(path)
    paths.update(ROOT/'tests'/('test_task1_best1_pair_'+name+'.py') for name in ('metrics','native','dashboard','run'))
    pins={}
    for path in sorted(paths):
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
                'Commit exact consumed source and tests before preparation: '+str(path))
        pins[str(path)]=sha(path)
    return pins

def make_plan(output,commit):
    pins=native.required_inputs(ROOT)
    require(isinstance(pins,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in pins.items()),'Explicit native/source SHA map required')
    code=source_pins(commit)
    for path in (CONDITION,UNIT_CACHE,C1_SUMMARY,FEEDBACK,MATCHED):pins[str(path)]=sha(path)
    pins.update(code);pins.update(policy.policy_refs(policy.load_ledger(ROOT/'runtime/task1-budget.json')))
    return dict(schema='task1-best1-pair-run-plan-v1',status='preregistered_not_executed',created_utc=stamp(),
        output_directory=str(output),source_commit=commit,input_sha256=pins,implementation_sha256=code,
        output_storage='Existing volatile /dev/shm; immutable GitHub publication/readback required before claiming persistent result storage' if output.is_relative_to(Path('/dev/shm')) else 'Existing repository filesystem',
        question='Match current f35 carrier E RMS at central r<=5mm/depth15..20 volume or centre20 separately using a true one-output two-square-pad 3000Hz sine; compare required Vpp and local/integrated skin burdens.',
        reference_candidate_id='rounded-expand-f35b23a22166',single_case_id='baseline-square15-C1pair0-xy80',
        modes=['raw_1Vpp','skin_contact_only'],matching=['ROI_energy_RMS','centre20_E_RMS'],
        new_PDE=0,new_native_RHS=0,max_seconds=180,CPU_count=1,aggregate_RSS_limit_bytes=3*GIB,
        minimum_free_disk_bytes=2*GIB,max_output_bytes=OUTPUT_CAP,
        geometry_control='Existing two-square-pad450mm2 comparator; same-rounded two-pad response is unavailable and remains uncomputed.',
        equality_scope='Matching one RMS scalar does not match the entire vector field, waveform, TIS envelope, physiology or safety.',
        unchanged_gates='Saved five native equation gates and original tolerances; no new convergence/experiment adoption.',
        public_source_and_data_only=True,delete_originals=False,paid_resources=False)

def browser_verify(html,output,guard):
    import tempfile
    from playwright.sync_api import sync_playwright
    errors=[];requests=[]
    with tempfile.TemporaryDirectory(prefix='task1-best1-pair-browser-',dir='/dev/shm') as temporary:
        scratch=Path(temporary);(scratch/'tmp').mkdir()
        env=dict(os.environ,TMPDIR=str(scratch/'tmp'),TMP=str(scratch/'tmp'),TEMP=str(scratch/'tmp'))
        with sync_playwright() as engine:
            context=engine.chromium.launch_persistent_context(str(scratch/'profile'),executable_path='/usr/bin/chromium',
                headless=True,viewport=dict(width=1400,height=1000),env=env,ignore_default_args=['--disable-dev-shm-usage'],
                args=['--disk-cache-size=0','--media-cache-size=0','--disable-gpu-shader-disk-cache'])
            try:
                page=context.pages[0]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
                page.on('request',lambda request:requests.append(request.url) if request.url.startswith(('http:','https:')) else None)
                page.set_content(html,wait_until='load',timeout=30000)
                page.wait_for_function("document.querySelectorAll('.case-card').length===2",timeout=30000)
                count=0
                for mode in ('raw_1Vpp','skin_contact_only'):
                    for criterion in ('ROI_energy_RMS','centre20_E_RMS'):
                        for plane in ('xy','xz','yz'):
                            guard()
                            for selector,value in (('#mode',mode),('#match',criterion),('#plane',plane)):
                                page.select_option(selector,value)
                            for selector in ('.field-map','.contact-map'):
                                values=page.locator(selector).evaluate_all('(nodes)=>nodes.map(n=>n.dataset.vmax)')
                                require(len(values)==2 and values[0]==values[1] and values[0] is not None,'Two actual maps require identical saved colour ranges')
                            count+=1
                for depth in range(5):page.select_option('#depth',str(depth));guard()
                page.select_option('#mode','skin_contact_only');page.select_option('#match','ROI_energy_RMS');page.select_option('#plane','xz')
                image=page.screenshot(type='jpeg',quality=35,full_page=False)
                if len(image)>64*1024:image=page.screenshot(type='jpeg',quality=15,full_page=False)
                require(len(image)<=64*1024,'Bounded64KiB GUI screenshot required')
                put_new(output/'preview.jpg',image,output)
                page.set_viewport_size(dict(width=390,height=844));page.wait_for_timeout(100)
                width=page.evaluate('document.documentElement.scrollWidth')
                require(width<=392 and not errors and not requests,'Mobile overflow, JavaScript errors or external requests')
                guard()
                return dict(status='passed',actual_data_Chromium=True,mode_match_plane_combinations=count,depth_selections=5,
                    field_maps=2,contact_maps=2,mobile_width=390,mobile_scroll_width=width,JS_errors=errors,external_requests=requests,
                    browser_profile_and_TMPDIR='owned existing /dev/shm; shared-memory fallback disabled',
                    navigation='Pinned HTML in memory DOM; browser file navigation is unavailable')
            finally:context.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    choice=parser.add_mutually_exclusive_group(required=True);choice.add_argument('--prepare',type=Path);choice.add_argument('--plan',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.absolute()
    require(output==output.resolve() and not output.exists() and (output.is_relative_to(ROOT/'docs') or
            (output.parent==Path('/dev/shm') and output.name.startswith('task1-best1-pair-'))),'New canonical docs or own bounded existing tmpfs output required; no overwrite')
    with ExitStack() as stack:
        stack.enter_context(bounded.dual_lock(ROOT/'.task1-loop.lock'));stack.enter_context(bounded.dual_lock(ROOT/'.task1-execution.lock'))
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledgerpath);cap=45 if args.prepare else 180
        require(policy.remaining_seconds(ledger)>=cap,'Existing approved finite time budget required')
        same_output_device=output.parent.stat().st_dev==ROOT.stat().st_dev
        require(shutil.disk_usage(ROOT).free>=2*GIB+(64*1024 if args.prepare else OUTPUT_CAP if same_output_device else 0)+ledgerpath.stat().st_size+LEDGER_GROWTH,'Original reserve plus prospective outputs and single atomic ledger headroom required')
        if not same_output_device:require(shutil.disk_usage(output.parent).free>=OUTPUT_CAP+64*1024**2,'Existing tmpfs space for bounded GUI and browser scratch required')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();pid=os.getpid();ticks=bounded.ticks(pid)
        state=dict(phase='prepare' if args.prepare else 'verify_plan',owned={pid:ticks},peak_aggregate_RSS_bytes=0,peak_live_processes=0)
        receipt=dict(schema='task1-best1-pair-run-receipt-v1',status='failed_preserved',started_utc=stamp(),pid=pid,proc_start_ticks=ticks,new_PDE=0)
        stop=threading.Event();old={s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        def guard():
            known=bounded.owned_descendants(pid,ticks,state['owned']);live={p:t for p,t in known.items() if bounded.live(p,t)}
            rss=sum(bounded.rss(p) for p in live);state.update(owned=live,peak_aggregate_RSS_bytes=max(state['peak_aggregate_RSS_bytes'],rss),peak_live_processes=max(state['peak_live_processes'],len(live)))
            require(time.monotonic()-start<cap and rss<3*GIB,'Finite time/aggregate3GiB RSS guard')
            require(shutil.disk_usage(ROOT).free>=2*GIB+ledgerpath.stat().st_size+LEDGER_GROWTH,'Preserve2GiB plus the single atomic ledger file')
            if output.exists():require(sum(p.stat().st_size for p in output.iterdir() if p.is_file())<=OUTPUT_CAP-FINAL_RESERVE,'Output cap reserves final48KiB receipt')
        def interrupt(signum,frame):raise TimeoutError(state.get('guard_failure','Controlled finite comparison stop: '+str(signum)))
        def monitor():
            while not stop.wait(1):
                try:guard()
                except BaseException as error:state['guard_failure']=str(error);os.kill(pid,signal.SIGTERM);return
        for s in old:signal.signal(s,interrupt)
        signal.setitimer(signal.ITIMER_REAL,cap);thread=threading.Thread(target=monitor,daemon=True);thread.start()
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            if args.prepare:
                target=args.prepare.absolute();require(target==target.resolve() and target.is_relative_to(ROOT/'docs') and target.parent.is_dir() and not target.exists(),'Unique existing-parent preregistration path required')
                plan=make_plan(output,commit);guard();write_new(target,plan)
                receipt.update(status='preregistered_not_executed',preregistration=str(target),preregistration_SHA256=sha(target))
            else:
                planpath=args.plan.resolve();plan=json.loads(planpath.read_text())
                require(plan['schema']=='task1-best1-pair-run-plan-v1' and plan['status']=='preregistered_not_executed' and plan['output_directory']==str(output) and plan['source_commit']==commit and plan['max_output_bytes']==OUTPUT_CAP,'Exact immutable preregistration and source required')
                require(source_pins(commit)==plan['implementation_sha256'],'Consumed source changed after preregistration')
                for name,digest in plan['input_sha256'].items():guard();require(sha(name)==digest,'Pinned input changed: '+name)
                output.mkdir();state['phase']='reference_metadata_and_four_RMS_matches'
                cached=json.loads(MATCHED.read_text())
                require(cached['status']=='calculated_metadata_matches_native_reproduction_pending' and cached['inputs_unchanged'] is True and
                        all(plan['input_sha256'].get(name)==digest for name,digest in cached['input_sha256'].items()),'Exact new f35 matching metadata must remain bound')
                analysis=cached['analysis']
                require(analysis['reference']['candidate_id']=='rounded-expand-f35b23a22166','Current best1 comparison identity required')
                write_new(output/'checkpoint.json',dict(pid=pid,proc_start_ticks=ticks,updated_utc=stamp(),phase='native_reproduction_and_GUI',preregistration_SHA256=sha(planpath)),output)
                state['phase']='existing_native_field_and_contact_reproduction';spatial=native.export_spatial(analysis,plan['input_sha256'],guard)
                provenance=dict(source_commit=commit,preregistration_path=str(planpath),preregistration_SHA256=sha(planpath),input_sha256=plan['input_sha256'],
                    candidate_id='rounded-expand-f35b23a22166',run_id=output.name,material_contact='Nominal PBS-derived10nm Rs-fit-window500Hz; not validated skin contact',
                    full_convergence_validated=False,experimentally_validated=False,instrument_loading_validated=False,COMSOL_installed_or_executed=False,
                    COMSOL_required_version='5.3a; planned5.3.1.201 unverified',same_rounded_two_pad_comparison_computed=False)
                state['phase']='render_source_bound_GUI';payload=dict(analysis=analysis,spatial=spatial,provenance=provenance);html=dashboard.render(payload)
                require(isinstance(html,str) and len(html.encode())<=HTML_CAP,'Bounded240KiB standalone GUI required')
                put_new(output/'index.html',html.encode(),output)
                write_new(output/'metrics.json',analysis,output);write_new(output/'spatial-statistics.json',{k:spatial[k] for k in ('regions','shape_comparison','proofs')},output)
                state['phase']='actual_GUI_matrix';browser=browser_verify(html,output,guard)
                state['phase']='unchanged_input_verification'
                for name,digest in plan['input_sha256'].items():guard();require(sha(name)==digest,'Source drift during comparison: '+name)
                guard();receipt.update(status='calculated_GUI_verified_unadopted',source_commit=commit,preregistration_SHA256=sha(planpath),input_sha256=plan['input_sha256'],inputs_unchanged=True,
                    native_proofs=spatial['proofs'],browser_validation=browser,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
                    same_rounded_two_pad_comparison_computed=False,artifacts={p.name:dict(SHA256=sha(p),bytes=p.stat().st_size) for p in output.iterdir() if p.is_file()})
        except BaseException as error:
            receipt.update(error_type=type(error).__name__,error=str(error),phase=state['phase'],resource_guard_failure=state.get('guard_failure'));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set();thread.join(timeout=2)
            survivors=stop_owned(pid,ticks,state['owned']);receipt['surviving_owned_children']=survivors
            if survivors:receipt.update(status='failed_preserved',error='Owned child cleanup incomplete')
            elapsed=time.monotonic()-start
            ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='best1_pair_prepare' if args.prepare else 'best1_pair_native_GUI',status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=stamp()))
            ledger_data=(json.dumps(ledger,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
            require(shutil.disk_usage(ROOT).free>=2*GIB+len(ledger_data),'Preserve exact single atomic final ledger write headroom')
            bounded.write(ledgerpath,ledger);receipt.update(finished_utc=stamp(),resources=dict(wall_seconds=elapsed,max_seconds=cap,CPU_count=1,peak_aggregate_RSS_bytes=state['peak_aggregate_RSS_bytes'],peak_live_processes=state['peak_live_processes'],max_output_bytes=OUTPUT_CAP),remaining_approved_seconds=policy.remaining_seconds(ledger))
            target=args.prepare.with_name(args.prepare.name+'.receipt.json') if args.prepare else output/'manifest.json'
            require(not target.exists(),'Preserve original receipt')
            if not target.parent.exists():target.parent.mkdir(parents=True)
            require(len(encode_json(receipt))<=FINAL_RESERVE,'Final receipt must fit48KiB reserved bytes')
            write_new(target,receipt,None if args.prepare else output,final=True)
            for s,handler in old.items():signal.signal(s,handler)
        print(json.dumps(dict(status=receipt['status'],output=str(output),seconds=elapsed)))

if __name__=='__main__':main()
