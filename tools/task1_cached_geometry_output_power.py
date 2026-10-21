"""Finite JSON-only signed output-power evidence for five cached geometries.

No E/phi/grid/mask/NPZ/native binary reads. Small configuration text is hashed
as metadata; native validation gates are reported from their saved receipts.
The result verifies saved-phasor algebra, not an independent native PDE solve.
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
import task1_coherent_drive_scout as strong
import task1_output_power_evidence as power
import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_results_view as view

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
FREQUENCIES=(3000,3030,9000,9090)
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
CANONICAL=ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
SOURCES=(
 ('original_square','cloud-mesh-c1-20261019T190000Z','baseline-square15-xy80','cloud-tangential-return-context-20261021T183000Z'),
 ('asymmetric_parent','cloud-asymmetric-20261021T051000Z','asym-cross281p25-return168p75-xy80','cloud-tangential-return-context-20261021T183000Z'),
 ('one_return_rotation','cloud-one-return-rotation-20261021T174000Z','asym-return2-rot90-xy80','cloud-one-return-rotation-context-20261021T174000Z'),
 ('tangential_returns','cloud-tangential-return-20261021T183000Z','asym-return-tangent4p375-xy80','cloud-tangential-return-context-20261021T183000Z'),
 ('perimeter_shell','cloud-perimeter-shell-20261021T185000Z','perimeter-shell225-notch-xy80','cloud-perimeter-shell-context-20261021T185000Z'))
require=strong.require


def _close(a,b):return abs(a-b)<=2e-12*abs(b)+1e-15


def validate_square_condition(condition):
    require(condition.get('waveform')=='square_3h'and condition.get('actual_fundamental_Hz')==[3000,3030]and
        condition.get('phase_deg')==[0.,0.]and condition.get('source_Vpp_per_output')==1.,'Exact exclusive square3h1Vpp phase0/0 condition required')
    metrics=condition['metrics']
    for name in('source_current_spectrum','loaded_metal_voltage_spectrum'):
        rows=metrics[name]
        require(len(rows)==4 and {r['frequency_Hz']for r in rows}==set(FREQUENCIES),'Exact actual four-frequency source/metal spectra required')
    for name,limit in(('driven_max_current_relative_error',2e-6),('driven_max_power_relative_error',2e-7)):
        x=metrics[name];require(type(x)in(int,float)and math.isfinite(x)and 0<=x<=limit,'Saved driven current/power gate failed: '+name)
    evidence=power.output_power_evidence(metrics)
    a1=3/(2*math.sqrt(2));a3=1/(2*math.sqrt(2))
    for row in evidence['outputs']:
        out=row['output_index']
        for tone in row['spectrum']:
            f=tone['frequency_Hz'];active=out==(0 if f in(3000,9000)else 1);expected=-.5j*(a1 if f in(3000,3030)else a3)if active else 0j
            voltage=tone['ideal_voltage_peak_V'];actual=complex(voltage['real'],voltage['imaginary'])
            require(abs(actual-expected)<=1e-12+1e-10*abs(expected),'Saved ideal Thevenin phasors do not match exclusive square3h actual source commands')
    return metrics


def audit_condition(metrics,modes):
    require(set(modes)==set(MODES),'Exactly five saved normalization modes required')
    for name,limit in(('driven_max_current_relative_error',2e-6),('driven_max_power_relative_error',2e-7)):
        value=metrics[name];require(type(value)in(int,float)and math.isfinite(value)and 0<=value<=limit,'Saved driven conservation gate failed: '+name)
    supplied=metrics['source_power_W'];delivered=metrics['tissue_contact_power_W'];resistor=metrics['source_resistor_power_W']
    require(all(type(x)in(int,float)and math.isfinite(x)and x>=0 for x in(supplied,delivered,resistor))and supplied>0,'Finite nonnegative saved aggregate powers required')
    error=abs(delivered+resistor-supplied)/max(abs(supplied),1e-20)
    require(error<=2e-7,'Saved native tissue/contact/resistor group power conservation failed')
    result={}
    for name in MODES:
        mode=modes[name];scale=mode['amplitude_scale']
        require(type(scale)in(int,float)and math.isfinite(scale)and scale>0 and _close(mode['source_Vpp_per_output'],scale)and
            (name!='raw_1Vpp'or scale==1.),'Positive saved common amplitude and actual whole-wave source Vpp scale required')
        evidence=strong.signed_output_powers(metrics,scale)
        if 'normalized_burdens'in mode:
            require(_close(evidence['totals']['ideal_source_power_W'],mode['normalized_burdens']['source_power_W']), 'Saved normalized source power differs from amplitude-square scaling')
        if 'source_output_RMS_by_output_mA'in mode:
            require(len(mode['source_output_RMS_by_output_mA'])==2 and all(_close(r['current_RMS_mA'],saved)for r,saved in
                zip(evidence['outputs'],mode['source_output_RMS_by_output_mA'])),'Saved normalized output current vector differs from linear scaling')
        result[name]=dict(amplitude_scale=scale,source_Vpp_by_output=[scale,scale],source_Vpp_definition='Whole square3h waveform before50ohm; not fundamental-tone Vpp or metal voltage',
            saved_normalization_contract={k:mode[k]for k in('baseline_derived_numerical_limits','active_skin_contact_caps','includes_source_power_cap','includes_1Vpp_ceiling')if k in mode},
            signed_per_output_power_evidence=evidence)
    return dict(normalizations=result,native_saved_conservation=dict(tissue_contact_plus_resistor_vs_source_relative_error=error,
        maximum_allowed_relative_error=2e-7,driven_current_relative_error=metrics['driven_max_current_relative_error'],
        maximum_allowed_current_relative_error=2e-6,driven_power_relative_error=metrics['driven_max_power_relative_error'],
        independent_native_recompute=False))


def implementation():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in(Path(__file__).resolve(),ROOT/'tests/test_task1_cached_geometry_output_power.py',
        *[Path(m.__file__).resolve()for m in(strong,power,core,policy,view)]):
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)==path.read_bytes(),
            'Commit consumed implementation/helper/test before actual audit: '+str(path))
        pins[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def build_report(checkpoint=lambda phase:None):
    receipt=implementation();pins=dict(receipt['implementation_files_sha256']);cases=[];canonical_limits=None
    def bind(path,expected=None,config=False):
        path=Path(path);require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and not path.is_symlink()and
            path.stat().st_size<=(256*1024 if config else 32*1024**2)and(path.suffix=='.json'or config),'Only bounded JSON and small configuration metadata may be read')
        digest=view.sha(path);require(expected is None or digest==expected,'Consumed metadata SHA mismatch: '+str(path));pins[str(path)]=digest
        obj=None if config else view.read(path);require(view.sha(path)==digest,'Metadata changed while reading');return obj
    for label,run_id,ident,volume_dir in SOURCES:
        checkpoint('read-'+label)
        run=ROOT/'data-native'/run_id;sp=run/'postprocess'/ident/'summary.json';post=bind(sp);pre=bind(run/'preregistration.json');record=bind(run/'cases'/(ident+'.json'))
        case=next(c for c in pre['cases']if c['id']==ident)
        require(post['id']==ident and post['status']==record['status']=='complete'and post['source_inputs_unchanged']is True and
            record['postprocess_path']==str(sp)and record['postprocess_sha256']==pins[str(sp)]and
            post['mesh_metadata']['config_sha256']==record['config_sha256']==case['config_sha256'],'Exact completed source-bound geometry receipt required')
        require(pre['gates']==core.GATES and all(type(record['validation'][key])in(int,float)and math.isfinite(record['validation'][key])and
            0<=record['validation'][key]<=limit for key,limit in core.GATES.items()),'Saved five native validation gates failed')
        bind(case['config_file'],case['config_sha256'],config=True)
        circuit=case['circuit'];require(circuit['n_pads']==4 and circuit['n_outputs']==2 and circuit['n_return_nodes']==1 and
            circuit['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}and circuit['source_resistance_ohm']==50 and circuit['source_peak_V']==.5,
            'Fixed four-pad/two-output/commonGND50ohm source topology required')
        conditions=[c for c in post['conditions']if c['waveform']=='square_3h'];require(len(conditions)==1,'One actual square3h waveform condition required')
        condition=conditions[0];metrics=validate_square_condition(condition)
        vp=ROOT/'docs'/volume_dir/'volume.json';volume=bind(vp)
        require(volume['schema']=='task1-volume-selectivity-v1'and volume['status']=='calculated_unadopted'and volume['inputs_unchanged']is True and
            volume['inputs_sha256'].get(str(sp))==pins[str(sp)],'Saved five-normalization volume audit must bind the exact source post')
        rows=[r for r in volume['cases']if r['case_id']==ident and r['run_id']==run_id and r['summary_path']==str(sp)]
        require(len(rows)==1 and rows[0]['condition_id']==condition['id']and rows[0]['baseline_summary']==str(CANONICAL)and
            rows[0]['configuration_sha256']==case['config_sha256']and rows[0]['circuit']==circuit,'Exact same-condition normalization and canonical original-square reference required')
        row=rows[0];modes=row['normalizations'];limits=modes['skin_contact_only']['baseline_derived_numerical_limits']
        if canonical_limits is None:canonical_limits=limits
        require(limits==canonical_limits and all(m['baseline_derived_numerical_limits']==canonical_limits for m in modes.values()),'Canonical numerical comparison limits differ across geometries/modes')
        require(modes['skin_contact_only']['includes_source_power_cap']is False and modes['skin_contact_only']['includes_1Vpp_ceiling']is False,
            'Eight skin/contact caps must remain distinct from source-power/1Vpp constraints')
        cases.append(dict(id=label,case_id=ident,run_id=run_id,condition_id=condition['id'],waveform='square_3h',frequencies_Hz=list(FREQUENCIES),
            source_summary=dict(path=str(sp),SHA256=pins[str(sp)]),source_volume_audit=dict(path=str(vp),SHA256=pins[str(vp)]),
            source_commit=pre['source_commit'],configuration_sha256=case['config_sha256'],mask_SHA256_declared_not_rehashed=case['mask_sha256'],
            original_postprocessor_SHA256_declared=post['postprocessor_sha256'],circuit=circuit,native_validation_saved=record['validation'],
            power_evidence=audit_condition(metrics,modes),candidate_adopted=False))
    for name,digest in pins.items():require(view.sha(name)==digest,'Consumed source changed: '+name)
    require(implementation()==receipt,'Committed implementation changed during audit')
    return dict(schema='task1-cached-geometry-output-power-v1',status='completed_saved_phasor_audit',cases=cases,input_sha256=pins,inputs_unchanged=True,
        **receipt,canonical_reference=str(CANONICAL),canonical_numerical_limits=canonical_limits,
        source_review_not_independent_native_recompute=True,new_PDE=0,new_native_RHS=0,native_array_reads=0,NPZ_reads=0,new_normalization_or_gate_search=False,
        signed_power_scope='Peak/+jwt saved spectra: Videal=Vmetal+50I; passive-frequency negative metal delivery preserved, never clipped',
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
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.stem,stage='cached_geometry_output_power',seconds=elapsed,status=status,error=error,finished_utc=core.now()));core.write(ledger_path,ledger)
            core.write(evidence/'heartbeat.json',dict(state,status=status,error=error,updated_utc=core.now(),elapsed_seconds=elapsed))
            for s,h in previous.items():signal.signal(s,h)
    print(str(output))

if __name__=='__main__':main()
