"""Twelve cached single-pair matches for three nominal-SC2 rounded TIS cohorts.

JSON evidence only: no native field/grid/NPZ decode or new PDE. RMS equality is
not modulation, recruitment, activation or safety equality. SC4/contact-scaled
conditions are explicitly outside this comparison.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time
import task1_rotation_coherent_single_pair as old
import task1_rounded_drive_scout as rounded
ROOT=old.ROOT;GIB=old.GIB;RUN=old.RUN;C1=old.C1
require=old.require;read=old.read;sha=old.sha;write_new=old.write_new;core=old.core;policy=old.policy
SCHEMA='task1-rounded-single-pair-preregistration-v1'
REFERENCE_IDS=('original-SC2-square3h','rounded-SC2-square3h','rounded-SC2-opt-e7b3bf639935')
MODES=('raw','skin_contact_only')
OPT_ID='rounded-opt-e7b3bf639935'
OPT_SUMMARY=ROOT/'docs/cloud-rounded-drive-optimization-20261021T203000Z/summary.json'
CONTROL_VOLUME=rounded.CONTROL_VOLUME
C1_CACHE=ROOT/'docs/cloud-rotation-coherent-single-pair-20261021T183500Z/summary.json'
OUTPUT_BOUND_BYTES=64*1024**2
weighted_energy_rms=old.weighted_energy_rms
reference_footprint=old.reference_footprint
target_matches=old.target_matches


def energy_rms_from_statistics(stats):
    mean,std,vol=(stats[k]for k in('mean','std','volume_m3'))
    require(all(type(v)in(int,float)and math.isfinite(v)and v>=0 for v in(mean,std))and
        type(vol)in(int,float)and math.isfinite(vol)and vol>0,'Saved finite volume-weighted mean/std with positive physical ROI volume required')
    result=math.hypot(mean,std);require(result>0,'Positive full-primary energy RMS required')
    return result


def single_signed_power(metrics,scale=1.):
    require(type(scale)in(int,float)and math.isfinite(scale)and scale>0,'Positive finite common C1 amplitude scale required')
    currents={r['frequency_Hz']:r for r in metrics['source_current_spectrum']};metal={r['frequency_Hz']:r for r in metrics['loaded_metal_voltage_spectrum']}
    require(set(currents)==set(metal)and len(currents)==len(metrics['source_current_spectrum'])==len(metrics['loaded_metal_voltage_spectrum']),
        'Unique matching actual C1 current/metal-voltage spectra required')
    rows=[];ps=pr=pm=i2=0.
    for f,c in sorted(currents.items()):
        v=metal[f]
        require(all(len(row[key])==1 and all(type(x)in(int,float)and math.isfinite(x)for x in row[key])for row,keys in
            ((c,('real_A','imaginary_A')),(v,('real_V','imaginary_V')))for key in keys),'Exactly one physical output complex phasor per frequency required')
        current=complex(c['real_A'][0],c['imaginary_A'][0]);loaded=complex(v['real_V'][0],v['imaginary_V'][0]);ideal=loaded+50*current
        p=.5*(ideal*current.conjugate()).real;r=25*abs(current)**2;m=.5*(loaded*current.conjugate()).real
        ps+=p;pr+=r;pm+=m;i2+=abs(current)**2/2
        rows.append(dict(frequency_Hz=f,ideal_source_power_W=p*scale**2,metal_delivered_power_W=m*scale**2,source_resistor_loss_W=r*scale**2))
    require(math.isclose(ps,metrics['source_power_W'],rel_tol=1e-10,abs_tol=1e-14)and
        math.isclose(pr,metrics['source_resistor_power_W'],rel_tol=1e-10,abs_tol=1e-14)and
        len(metrics['source_current_RMS_by_output_mA'])==1 and math.isclose(math.sqrt(i2)*1000,metrics['source_current_RMS_by_output_mA'][0],rel_tol=1e-10,abs_tol=1e-12),
        'C1 signed source/resistor power and output RMS must reproduce saved metrics')
    return dict(physical_outputs=1,source_resistance_ohm=50.,spectrum=rows,amplitude_scale=scale,
        ideal_source_power_W=ps*scale**2,metal_delivered_power_W=pm*scale**2,source_resistor_loss_W=pr*scale**2,
        output_current_RMS_mA=math.sqrt(i2)*1000*scale,negative_frequency_power_preserved=True,hardware_absorption_and_compliance_validated=False)


def validate_sc2_scope(case,meta):
    require(case['circuit']['n_pads']==4 and case['circuit']['n_outputs']==2 and case['circuit']['n_return_nodes']==1 and
        case['circuit']['pad_to_node']=={'0':'out0','1':'out1','2':'GND','3':'GND'}and case['circuit']['source_resistance_ohm']==50 and
        meta['sc_cells']==2 and meta['h_xy_mm']==.625 and meta['bulk_layer_counts']==[14,14,40]and meta['cells']==351680 and
        case.get('source_coating_nm')==10 and case.get('source_Rs_fit_window_Hz')==500 and
        all(math.isclose(a,225e-6,rel_tol=1e-12,abs_tol=1e-16)for a in case['expected_pad_areas_m2'])and len(case['expected_pad_areas_m2'])==4,
        'Only nominalPBS original/rounded four225mm2 SC2 cohorts are compared; no SC4/contact-scaled alias')


def implementation():
    modules=(old,old.old,rounded,old.drive,old.view,core,policy)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_single_pair.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for p in dict.fromkeys(paths):
        require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),'Commit consumed C1 comparison source/tests before use: '+str(p));refs[str(p)]=sha(p)
    return dict(source_commit=commit,implementation_sha256=refs)


def make_preregistration(output,decision_path,feedback_path):
    receipt=implementation();refs=dict(receipt['implementation_sha256'])
    def bind(path,expected=None):
        p=Path(path);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and p.suffix=='.json',
            'Bounded canonical JSON source only; native arrays are never decoded')
        digest=sha(p);require(expected is None or digest==expected,'Source SHA mismatch: '+str(p));refs[str(p)]=digest
        obj=read(p);require(sha(p)==digest,'JSON changed while reading');return obj
    decision=bind(decision_path);feedback=bind(feedback_path);old.old.validate_feedback(feedback)
    require(decision.get('schema')=='task1-rounded-single-pair-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and decision.get('new_PDE')==0 and
        decision.get('reference_ids')==list(REFERENCE_IDS)and decision.get('modes')==list(MODES)and decision.get('single_case_id')==C1 and
        decision.get('single_frequency_Hz')==3000 and isinstance(decision.get('question'),str)and bool(decision['question'].strip()),
        'Exact root-selected nominal SC2 three-cohort C1 comparison decision required')
    required=(OPT_SUMMARY,CONTROL_VOLUME,C1_CACHE,Path(feedback_path))
    require(all(decision.get('input_sha256',{}).get(str(p))==sha(p)for p in required),'Decision must bind exact optimizer/controls/C1 unit cache/current feedback')
    for name,digest in decision['input_sha256'].items():bind(name,digest)
    cache=bind(C1_CACHE);require(cache['status']=='calculated_unadopted'and cache['inputs_unchanged']is True and cache['new_PDE']==0,
        'Completed immutable original C1 unit-response cache required')
    unit=copy.deepcopy(cache['single_stimulation']);require(unit['case_id']==C1 and unit['source_run_id']==RUN and unit['raw_source_Vpp']==1. and
        unit['frequency_Hz']==3000 and unit['circuit']['n_pads']==2 and unit['circuit']['n_outputs']==1,'C1 cache must be genuine one source-return pair at1Vpp')
    c1run=ROOT/'data-native'/RUN;pre=bind(c1run/'preregistration.json');single=next(c for c in pre['cases']if c['id']==C1)
    sp=c1run/'postprocess'/C1/'summary.json';post=bind(sp);record=bind(c1run/'cases'/(C1+'.json'));old.validate_single(single,post['mesh_metadata'])
    c1config=old.properties(single['config_file']);require(sha(single['config_file'])==single['config_sha256']and
        cache['input_sha256'].get(single['config_file'])==single['config_sha256'],'Cached C1 unit response must bind the exact source config')
    refs[single['config_file']]=single['config_sha256']
    require(record['status']==post['status']=='complete'and record['postprocess_sha256']==refs[str(sp)]and pre['gates']==core.GATES and
        all(record['validation'][k]<=v for k,v in core.GATES.items())and cache['input_sha256'].get(str(sp))==refs[str(sp)],'Original native C1 equation gates/cache source binding required')
    sine=next(c for c in post['conditions']if c['waveform']=='sine'and c['actual_fundamental_Hz']==[3000])
    require(all(r['frequency_Hz']==3000 or all(v==0 for k in('real_A','imaginary_A')for v in r[k])for r in sine['metrics']['source_current_spectrum']),
        'Only the actual single3000Hz sine response may be reused')
    require(math.isclose(unit['raw_centre20_E_RMS_V_m'],sine['metrics']['target20_total_E_RMS_V_m'],rel_tol=1e-10,abs_tol=1e-12),'Cached C1 centre RMS differs from original source')
    probe_ref=unit['unloaded_probe_reference'];probes=bind(probe_ref['path'],probe_ref['SHA256'])
    probe=next(c['probe40']for c in probes['conditions']if c['id']==probe_ref['condition_id'])
    require(probe['status']=='complete'and probe['numerical_checks']['all_passed']and len(probe['measurements'])==40,'Existing actual C1 nativephi sine40 probes required')
    # No native inputs are decoded: current/power/field/unit-ROI were already verified by the immutable cached run.
    unit['saved_electrical_metrics']=sine['metrics'];unit['source_summary_path']=str(sp);unit['configuration_sha256']=single['config_sha256'];unit['probe']=probe
    single_signed_power(sine['metrics'])
    controls=bind(CONTROL_VOLUME);optimization=bind(OPT_SUMMARY)
    require(controls['status']=='calculated_unadopted'and controls['inputs_unchanged']is True and optimization['status']=='calculated_unadopted'and
        optimization['inputs_unchanged']is True and optimization['source_geometry']['source_case_id']==rounded.SOURCE_ID,'Completed nominal SC2 controls and selected rounded optimization required')
    refs_list=[];physical_volume=None
    for ident,path in zip(REFERENCE_IDS[:2],(rounded.BASELINE_SUMMARY,rounded.SOURCE_SUMMARY)):
        row=next(c for c in controls['cases']if c['summary_path']==str(path));native=bind(path,controls['inputs_sha256'][str(path)])
        reg=bind(path.parents[2]/'preregistration.json');case=next(c for c in reg['cases']if c['id']==path.parent.name);validate_sc2_scope(case,native['mesh_metadata'])
        config=old.properties(case['config_file']);require(sha(case['config_file'])==case['config_sha256'],'Reference config SHA mismatch')
        keys={k for k in c1config if k.startswith('z.')or k.endswith(('.sigma','.epsilon_r'))}
        require(all(config.get(k)==c1config[k]for k in keys)and config['h_mm']==c1config['h_mm']and
            config['validation.sc_cells']==c1config['validation.sc_cells']=='2'and config['bulk.counts']==c1config['bulk.counts'],
            'Nominal material/specific-contact model and SC2 grid must match the cached C1 unit response')
        refs[case['config_file']]=case['config_sha256']
        square=next(c for c in native['conditions']if c['id']==row['condition_id'])
        refs_list.append(dict(id=ident,condition_id=row['condition_id'],source_run_id=row['run_id'],source_case_id=row['case_id'],source_summary_path=str(path),
            configuration_sha256=case['config_sha256'],source_commit=row['source_commit'],circuit=case['circuit'],waveform='square_3h',frequencies_Hz=[3000,3030,9000,9090],
            electrical_metrics=square['metrics'],normalized_modes={k:row['normalizations']['raw_1Vpp'if k=='raw'else k]for k in MODES},source_intervals_V=[[1.,1.],[1.,1.]],
            footprint=reference_footprint(case['expected_pad_areas_m2'],case['circuit'])))
    entry=next(c for c in optimization['conditions']if c['id']==OPT_ID);ref=entry['artifacts']['condition.json'];condition=bind(ref['path'],ref['SHA256'])
    require(condition['status']=='calculated_unadopted'and condition['source_case_id']==rounded.SOURCE_ID and condition['source_run_id']==rounded.SOURCE_RUN and
        condition['configuration_sha256']==refs_list[1]['configuration_sha256']and condition['candidate_adopted']is False,'Exact selected e7 nominalSC2 rounded condition required')
    refs_list.append(dict(id=REFERENCE_IDS[2],condition_id=OPT_ID,source_run_id=rounded.SOURCE_RUN,source_case_id=rounded.SOURCE_ID,source_summary_path=str(OPT_SUMMARY),
        condition_path=ref['path'],configuration_sha256=condition['configuration_sha256'],source_commit=condition['source_commit'],circuit=condition['source_circuit'],
        waveform=condition['waveform'],frequencies_Hz=[3000,3030],electrical_metrics=condition['electrical_metrics'],source_intervals_V=condition['source_waveform']['source_Vpp_intervals_V'],
        normalized_modes={k:condition['normalizations']['raw_1Vpp'if k=='raw'else k]for k in MODES},footprint=refs_list[1]['footprint']))
    canonical_limits=refs_list[0]['normalized_modes']['skin_contact_only']['baseline_derived_numerical_limits']
    for row in refs_list:
        for mode in MODES:
            data=row['normalized_modes'][mode];stats=data['regions'][rounded.volume.PRIMARY]['RMS'];energy_rms_from_statistics(stats)
            if physical_volume is None:physical_volume=stats['volume_m3']
            require(math.isclose(stats['volume_m3'],physical_volume,rel_tol=1e-12,abs_tol=1e-15),'Identical primary ROI physical volume required across all SC2 cohorts')
            require(mode!='raw'or data['amplitude_scale']==1.,'Raw reference must preserve source1Vpp waveform before50ohm')
            require(data['baseline_derived_numerical_limits']==canonical_limits and data['includes_source_power_cap']is False and
                data['includes_1Vpp_ceiling']is False,'Reference raw/skin8 must retain original SC2 numerical limits without power/voltage ceiling')
    refs.update(policy.policy_refs(policy.load_ledger()))
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),references=refs_list,
        reference_ids=list(REFERENCE_IDS),modes=list(MODES),single_case_id=C1,single_unit=unit,input_sha256=refs,new_PDE=0,max_seconds=120,
        native_array_decode=False,cohort_scope='NominalPBS SC2 only; SC4/contact-scaled cases are not matched',
        cohort_footprints=dict(C1=reference_footprint(unit['represented_pad_contact_areas_m2'],unit['circuit']),TIS_each=refs_list[0]['footprint']),
        root_selection_decision=dict(path=str(decision_path),SHA256=refs[str(decision_path)],question=decision['question']),
        feedback_context=dict(path=str(feedback_path),SHA256=refs[str(feedback_path)],observed_utc=feedback['observed_utc']),
        holds=['C1 is two225mm2 pads including its return,450mm2 total,one output; TIS is four225mm2 pads,900mm2 total,two outputs/commonGND',
            'RMS matching is neither modulation nor physiological activation/safety equivalence; pure C1 sinusoid has zero envelope variation',
            'Centre and ROI energy RMS matches are separate; current,power and skin burden generally do not match simultaneously',
            'All geometry/edge/XY/bulk/contact/PBS-to-skin/experimental and instrument-loading holds remain; no candidate adopted'],**receipt)


def verify_plan(path,output):
    plan=read(path);require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['reference_ids']==list(REFERENCE_IDS)and
        plan['modes']==list(MODES)and plan['single_case_id']==C1 and plan['output_directory']==str(output)and plan['new_PDE']==0 and plan['native_array_decode']is False,
        'Exact nominalSC2 twelve-row C1 cached comparison scope required')
    require(implementation()['implementation_sha256']==plan['implementation_sha256'],'C1 comparison implementation changed')
    for name,d in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and p.suffix in('.json','.py','.md','.properties')and sha(p)==d,'Pinned cached C1/reference evidence changed: '+name)
    return plan


def execute(plan,phase=lambda name:None):
    phase('reuse-cached-unit-response');unit=plan['single_unit'];targets=[]
    for ref in plan['references']:
        point=ref['electrical_metrics']['target20_total_E_RMS_V_m'];raw_roi=energy_rms_from_statistics(ref['normalized_modes']['raw']['regions'][rounded.volume.PRIMARY]['RMS'])
        for mode in MODES:
            data=ref['normalized_modes'][mode];scale=data['amplitude_scale'];roi=energy_rms_from_statistics(data['regions'][rounded.volume.PRIMARY]['RMS'])
            require(math.isclose(roi,raw_roi*scale,rel_tol=1e-10,abs_tol=1e-12),'Saved RMS statistics must preserve common amplitude scaling')
            matches=target_matches(point*scale,roi,unit['raw_centre20_E_RMS_V_m'],unit['raw_ROI_energy_RMS_V_m'],unit['raw_burdens'],unit['probe'])
            for match in matches.values():match['signed_output_power_evidence']=single_signed_power(unit['saved_electrical_metrics'],match['amplitude_scale'])
            targets.append(dict(id=ref['id']+'--'+mode,reference_id=ref['id'],reference_condition_id=ref['condition_id'],reference_source_run_id=ref['source_run_id'],
                reference_source_case_id=ref['source_case_id'],reference_source_commit=ref['source_commit'],reference_configuration_sha256=ref['configuration_sha256'],
                reference_circuit=ref['circuit'],reference_waveform=ref['waveform'],reference_frequencies_Hz=ref['frequencies_Hz'],reference_amplitude_scale=scale,
                reference_source_Vpp_intervals_V=[[x*scale for x in pair]for pair in ref['source_intervals_V']],reference_nine_burdens=data['normalized_burdens'],
                reference_centre20_E_RMS_V_m=point*scale,reference_ROI_energy_RMS_V_m=roi,matches=matches))
    require(len(targets)==6 and sum(len(t['matches'])for t in targets)==12,'Exactly twelve independent C1 RMS comparisons required')
    single={k:v for k,v in unit.items()if k not in('probe','saved_electrical_metrics')}
    return dict(schema='task1-rounded-single-pair-rms-v1',status='calculated_unadopted',targets=targets,reference_ids=list(REFERENCE_IDS),modes=list(MODES),
        single_stimulation=single,cohort_footprints=plan['cohort_footprints'],cohort_scope=plan['cohort_scope'],
        ROI_energy_RMS_definition='sqrt(weighted mean of native E_RMS squared)=sqrt(saved weighted mean(E_RMS)^2+saved weighted population std(E_RMS)^2); not mean(E_RMS)',
        source_Vpp_definition='Actual whole-waveform open/high-Z before50ohm; loaded metal Vpp is a separate actual burden',
        same_field_RMS_implies_same_modulation_or_activation=False,new_PDE=0,new_native_RHS=0,native_array_decode=False,
        candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,instrument_loading_validated=False,
        root_selection_decision=plan['root_selection_decision'],feedback_context=plan['feedback_context'],holds=plan['holds'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path)
    args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new docs output directory required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path);cap=60 if args.prepare else 120
        require(policy.remaining_seconds(ledger)>=cap,'Finite admission budget missing')
        require(shutil.disk_usage(output.parent).free>=2*GIB+OUTPUT_BOUND_BYTES,'Preserve2GiB reserve plus bounded artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+cap
        status='failed_preserved';failure=None;state={};counter=0;mutex=threading.RLock();stop=threading.Event();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
            require(shutil.disk_usage(output.parent).free>=2*GIB,'Existing2GiB disk reserve exhausted')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=OUTPUT_BOUND_BYTES,'New comparison artifacts exceed64MiB bound')
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                guard();counter+=1;state.update(phase=phase,status=status if phase=='complete'else'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                    updated_utc=core.now(),elapsed_seconds=time.monotonic()-started,**extra)
                write_new(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as error:
                    state['resource_guard_failure']=str(error);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(signum,frame):raise TimeoutError('Controlled finite120s/60s-prepare stop signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for signum in previous:signal.signal(signum,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap)
        try:
            if args.prepare:
                require(not args.prepare.exists()and not args.prepare.with_name(args.prepare.name+'.failure.json').exists()and not args.prepare.resolve().is_relative_to(output),
                    'New preregistration must remain outside the untouched actual output directory')
                plan=make_preregistration(output,args.decision.resolve(),args.feedback.resolve());args.prepare.parent.mkdir(parents=True,exist_ok=True)
                write_new(args.prepare,plan);status='preregistered_not_executed'
            else:
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_plan')
                plan_sha=sha(args.preregistration);plan=verify_plan(args.preregistration.resolve(),output)
                result=execute(plan,lambda phase:checkpoint(phase))
                require(sha(args.preregistration)==plan_sha,'Preregistration changed during execution');verify_plan(args.preregistration.resolve(),output);guard()
                result.update(implementation(),preregistration=dict(path=str(args.preregistration.resolve()),SHA256=plan_sha),
                    input_sha256=plan['input_sha256'],inputs_unchanged=True,resources=dict(CPU_count=1,max_batch_seconds=120,
                        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-started,
                        cumulative_budget_limit_seconds=policy.effective_limit(ledger),new_PDE=0))
                write_new(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            if output.exists():write_new(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),
                condition_id=state.get('condition_id'),new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False))
            elif args.prepare:
                failure_path=args.prepare.with_name(args.prepare.name+'.failure.json')
                if not failure_path.exists():write_new(failure_path,dict(status=status,error=failure,new_PDE=0,automatic_retry=False))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='rounded_single_pair_prepare'if args.prepare else'rounded_single_pair',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
