"""Finite JSON-only signed-power supplement for the fixed inward cohort.

Reads saved JSON only; no configuration, mask, E/phi/grid/NPZ/native binary
reads or independent native recalculation. Source-code bytes are pinned.
"""
from __future__ import annotations
import argparse
import fcntl
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time
for _name in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
import task1_cached_geometry_output_power as frozen
ROOT=frozen.ROOT
GIB=frozen.GIB
core=frozen.core
policy=frozen.policy
view=frozen.view
strong=frozen.strong
require=frozen.require
MODES=frozen.MODES
CANONICAL=frozen.CANONICAL
VOLUME=ROOT/'docs/cloud-perimeter-inward-context-20261021T194000Z/volume.json'
IDS=('baseline-square15-xy80','perimeter-shell225-notch-xy80','perimeter-shell225-inward0p625-xy80')
RUNS=('cloud-mesh-c1-20261019T190000Z','cloud-perimeter-shell-20261021T185000Z','cloud-perimeter-inward-20261021T194000Z')
audit_condition=frozen.audit_condition
validate_square_condition=frozen.validate_square_condition


def validate_volume(volume):
    require(volume.get('schema')=='task1-volume-selectivity-v1'and volume.get('status')=='calculated_unadopted'and
        volume.get('inputs_unchanged')is True and volume.get('selected_for_adoption')==[],'Completed unchanged unadopted inward volume report required')
    rows=volume.get('cases',[])
    require(tuple(r.get('case_id')for r in rows)==IDS and tuple(r.get('run_id')for r in rows)==RUNS and
        all(r.get('adopted')is False and r.get('calculation_status')=='cached_native_scalar_audit_complete'and
            r.get('baseline_summary')==str(CANONICAL)and set(r.get('normalizations',{}))==set(MODES)for r in rows),
        'Exact original-square/perimeter/inward rows, five fixed modes and original sole baseline required')
    return rows


def validate_source_binding(row,post,pre,record,summary_path,summary_sha):
    ident=row['case_id'];cases=[c for c in pre['cases']if c['id']==ident]
    require(len(cases)==1,'One registered exact native source case required');case=cases[0]
    require(post['id']==ident and post['status']==record['status']=='complete'and post['source_inputs_unchanged']is True and
        record['id']==ident and record['postprocess_path']==str(summary_path)and record['postprocess_sha256']==summary_sha and
        row['summary_path']==str(summary_path)and post['mesh_metadata']['config_sha256']==record['config_sha256']==case['config_sha256']==row['configuration_sha256']and
        post['input_sha256'].get(case['config_file'])==case['config_sha256'],'Completed source/config JSON receipts disagree')
    require(pre['gates']==core.GATES and all(type(record['validation'][k])in(int,float)and math.isfinite(record['validation'][k])and
        0<=record['validation'][k]<=limit for k,limit in core.GATES.items()),'Saved native numerical gates failed')
    c=case['circuit'];require(row['circuit']==c and c['n_pads']==4 and c['n_outputs']==2 and c['n_return_nodes']==1 and
        c['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}and c['source_resistance_ohm']==50 and c['source_peak_V']==.5,
        'Four pads/two outputs/commonGND50ohm source topology required')
    require(isinstance(case.get('mask_sha256'),str)and len(case['mask_sha256'])==64,'Saved declared contact-mask SHA required')
    return case


def implementation():
    receipt=frozen.implementation();commit=receipt['implementation_git_commit'];pins=dict(receipt['implementation_files_sha256'])
    for path in(Path(__file__).resolve(),ROOT/'tests/test_task1_inward_geometry_output_power.py'):
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)==path.read_bytes(),
            'Commit inward wrapper/test before actual execution: '+str(path));pins[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def build_report(checkpoint=lambda phase:None):
    receipt=implementation();pins=dict(receipt['implementation_files_sha256'])
    def bind(path,expected=None):
        path=Path(path);require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.suffix=='.json'and path.stat().st_size<=32*1024**2,'Only bounded canonical saved JSON inputs permitted')
        digest=view.sha(path);require(expected is None or digest==expected,'Consumed JSON SHA mismatch: '+str(path));pins[str(path)]=digest
        value=view.read(path);require(view.sha(path)==digest,'Consumed JSON changed while reading');return value
    volume=bind(VOLUME);rows=validate_volume(volume);cases=[];canonical_limits=None
    for row in rows:
        checkpoint('read-'+row['case_id']);sp=ROOT/'data-native'/row['run_id']/'postprocess'/row['case_id']/'summary.json'
        require(row['summary_path']==str(sp),'Fixed inward row/source path differs')
        post=bind(sp,volume['inputs_sha256'][str(sp)]);run=sp.parents[2];pre=bind(run/'preregistration.json');record=bind(run/'cases'/(row['case_id']+'.json'))
        case=validate_source_binding(row,post,pre,record,sp,pins[str(sp)])
        selected=[c for c in post['conditions']if c['waveform']=='square_3h'];require(len(selected)==1 and selected[0]['id']==row['condition_id'],'Exact saved square condition reference required')
        metrics=validate_square_condition(selected[0]);modes=row['normalizations'];limits=modes['skin_contact_only']['baseline_derived_numerical_limits']
        if canonical_limits is None:canonical_limits=limits
        require(limits==canonical_limits and all(m['baseline_derived_numerical_limits']==canonical_limits for m in modes.values())and
            modes['skin_contact_only']['includes_source_power_cap']is False and modes['skin_contact_only']['includes_1Vpp_ceiling']is False,
            'Original sole eight-skin caps and five saved normalization meanings must remain fixed')
        cases.append(dict(case_id=row['case_id'],run_id=row['run_id'],condition_id=selected[0]['id'],waveform='square_3h',frequencies_Hz=list(frozen.FREQUENCIES),
            source_summary=dict(path=str(sp),SHA256=pins[str(sp)]),source_volume_audit=dict(path=str(VOLUME),SHA256=pins[str(VOLUME)]),source_commit=pre['source_commit'],
            configuration_sha256=case['config_sha256'],configuration_sha256_scope='Matched saved preregistration/case/post/volume JSON; configuration bytes not read/rehashed',
            mask_SHA256_declared_not_rehashed=case['mask_sha256'],original_postprocessor_SHA256_declared=post['postprocessor_sha256'],
            circuit=case['circuit'],native_validation_saved=record['validation'],power_evidence=audit_condition(metrics,modes),candidate_adopted=False))
    for name,digest in pins.items():require(view.sha(name)==digest,'Consumed JSON/implementation changed: '+name)
    require(implementation()==receipt,'Committed implementation changed')
    return dict(schema='task1-inward-geometry-output-power-v1',status='completed_saved_phasor_audit',cases=cases,input_sha256=pins,inputs_unchanged=True,**receipt,
        canonical_reference=str(CANONICAL),canonical_numerical_limits=canonical_limits,source_review_not_independent_native_recompute=True,
        new_PDE=0,new_native_RHS=0,native_array_reads=0,configuration_file_reads=0,contact_mask_reads=0,NPZ_reads=0,new_normalization_or_gate_search=False,
        signed_power_scope='Peak/+jwt saved spectra: Videal=Vmetal+50I; passive-frequency negative metal delivery preserved without clipping',
        hardware_power_absorption_compliance_validated=False,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.resolve()
    evidence=output.with_suffix('.evidence');require(output.is_relative_to(ROOT/'docs')and output.suffix=='.json'and not output.exists()and not evidence.exists(),'Unique new docs JSON and sidecar evidence directory required')
    with(ROOT/'.task1-loop.lock').open('a+')as loop,(ROOT/'.task1-execution.lock').open('a+')as execution:
        for lock in(loop,execution):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path);require(policy.remaining_seconds(ledger)>=60,'Need60s finite remaining authorization')
        require(shutil.disk_usage(output.parent).free>=2*GIB+16*1024**2,'Preserve2GiB reserve plus finite output allowance')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();status='failed_preserved';error=None;counter=0;stop=threading.Event();mutex=threading.RLock();state={}
        evidence.mkdir();thread=None
        def guard():require(core.rss(os.getpid())<3*GIB and shutil.disk_usage(output.parent).free>=2*GIB,'Finite3GiB RSS/2GiB disk reserve guard failed')
        def checkpoint(phase):
            nonlocal counter
            with mutex:
                guard();counter+=1;state.update(status='running',phase=phase,pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-started)
                strong.drive.write_json(evidence/f'checkpoint-{counter:03d}.json',dict(state));core.write(evidence/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(evidence/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException:os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(signum,frame):raise TimeoutError('Finite60s saved-phasor audit stopped by signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for s in previous:signal.signal(s,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60)
        try:
            thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('start')
            result=build_report(checkpoint);guard();result['resources']=dict(CPU_count=1,max_seconds=60,wall_seconds=time.monotonic()-started,
                peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,cumulative_budget_limit_seconds=policy.effective_limit(ledger))
            strong.drive.write_json(output,result);status=result['status'];checkpoint('complete')
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc);strong.drive.write_json(evidence/'failure.json',dict(status=status,error=error,partial_evidence_preserved=True,automatic_retry=False,new_PDE=0));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.stem,stage='inward_geometry_output_power',seconds=elapsed,status=status,error=error,finished_utc=core.now()));core.write(ledger_path,ledger)
            core.write(evidence/'heartbeat.json',dict(state,status=status,error=error,updated_utc=core.now(),elapsed_seconds=elapsed))
            for s,h in previous.items():signal.signal(s,h)
    print(str(output))

if __name__=='__main__':main()
