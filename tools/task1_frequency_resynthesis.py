#!/usr/bin/env python3
"""Finite actual-frequency pure-sine re-synthesis; no PDE or source mutation.

The9000/9090Hz transfer basis remains9000/9090Hz. Both carrier and beat change
relative to3000/3030Hz; electrical comparisons imply no physiological equivalence.
Frozen research modules are imported only inside the caller's execution lock.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import importlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import threading
import time
import shutil

for _key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='1'
import numpy as np
import task1_drive_ratio_audit as drive
import task1_volume_selectivity as volume
import task1_waveform_check as waveform
import task1_carrier_balance_audit as carrier
import task1_results_view as view
import task1_cloud_batch as core

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
SCHEMA='task1-frequency-resynthesis-preregistration-v1'
PAIRS=((3000,3030),(9000,9090))
CONDITIONS=({'id':'sine-3000-3030-beat30','actual_fundamental_Hz':[3000,3030],'beat_frequency_Hz':30},
    {'id':'sine-9000-9090-beat90','actual_fundamental_Hz':[9000,9090],'beat_frequency_Hz':90})


def require(ok,message):
    if not ok:raise ValueError(message)


def sine_coefficients(pair):
    require(isinstance(pair,(tuple,list))and len(pair)==2 and all(type(f)is int for f in pair)
        and tuple(pair)in PAIRS,'Explicit actual3000/3030Hz or9000/9090Hz ordered pair required')
    return {pair[0]:np.array([-1j,0j]),pair[1]:np.array([0j,-1j])}


def electrical_for_pair(basis,coefficients,geometry,pair,post,deadline):
    """Explicit frequency-general adapter; no mutation/monkeypatch of frozen code."""
    expected=sine_coefficients(pair)
    require(set(coefficients)==set(pair)and all(np.array_equal(coefficients[f],expected[f])for f in pair),
        'Actual pure-sine unit coefficients required; square third-harmonic factors are excluded')
    post._deadline(deadline,'frequency_specific_electrical')
    sampler=post.LayeredPotentialSampler(basis['grid'],geometry)
    contacts=basis['f'][pair[0]]['contacts'];area=contacts['area_m2'];pads=contacts['pad'].astype(int)
    j2,polar2,current2,loss=np.zeros(len(area)),np.zeros(len(area)),np.zeros(2),np.zeros(6)
    source_power=0.;centres={};current_spectra=[];metal_spectra=[];current_errors=[];power_errors=[]
    for frequency in pair:
        post._deadline(deadline,'electrical_frequency:'+str(frequency))
        row=basis['f'][frequency];c=coefficients[frequency]
        require(np.array_equal(row['contacts'],contacts),'Actual frequency contact identities differ')
        density=c@row['density'];current=row['source']@c
        losses=np.einsum('i,kij,j->k',c.conj(),row['loss'],c).real
        supplied=float(.25*np.vdot(c,current).real)
        signals=np.array([np.sum(density[pads==i]*area[pads==i])for i in range(2)])
        error=float(np.max(abs(signals-current))/max(float(np.max(abs(current))),1e-30))
        balance=float(abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)),1e-30))
        p_error=float(abs(losses.sum()-supplied)/max(abs(supplied),1e-20))
        require(max(error,balance)<=2e-6 and p_error<=2e-7,'Existing driven-current/power conservation gate failed at actual frequency')
        current_errors.append(max(error,balance));power_errors.append(p_error)
        stencil=sampler.stencil([0,0,20],geometry['gamma_S_m'][frequency])
        target=np.einsum('p,cpk->ck',stencil['weights'],row['field'][:,stencil['indices'],:])
        centres[frequency]=c@target
        za=complex(float(basis['config'][f'z.{frequency}.re']),float(basis['config'][f'z.{frequency}.im']))
        j2+=abs(density)**2/2;polar2+=abs(density*za)**2/2;current2+=abs(current)**2/2
        loss+=losses;source_power+=supplied
        current_spectra.append(dict(frequency_Hz=frequency,real_A=current.real.tolist(),imaginary_A=current.imag.tolist()))
        metal=.5*c-50*current
        metal_spectra.append(dict(frequency_Hz=frequency,real_V=metal.real.tolist(),imaginary_V=metal.imag.tolist()))
    jrms=np.sqrt(j2);order=np.argsort(jrms,kind='stable');cdf=np.cumsum(area[order])
    p95=float(jrms[order[min(int(np.searchsorted(cdf,.95*cdf[-1],side='left')),len(order)-1)]])
    modulation=float(2*np.minimum(abs(post._DIRECTIONS@centres[pair[0]]),abs(post._DIRECTIONS@centres[pair[1]])).max())
    return dict(actual_fundamental_Hz=list(pair),beat_frequency_Hz=pair[1]-pair[0],
        target20_modulation_V_m=modulation,target20_total_E_RMS_V_m=float(np.sqrt(sum(np.vdot(v,v).real for v in centres.values())/2)),
        surface_J_RMS_max_A_m2=float(jrms.max()),surface_J_RMS_p95_A_m2=p95,contact_voltage_RMS_max_V=float(np.sqrt(polar2.max())),
        max_source_current_RMS_mA=float(np.sqrt(current2.max())*1000),source_current_RMS_by_output_mA=(np.sqrt(current2)*1000).tolist(),
        SC_power_W=float(loss[0]),contact_power_W=float(loss[4]),skin_power_W=float(loss[0]+loss[4]),
        tissue_contact_power_W=float(sum(loss[:5])),source_power_W=source_power,source_resistor_power_W=float(loss[5]),
        source_current_spectrum=current_spectra,loaded_metal_voltage_spectrum=metal_spectra,
        centre_field_spectrum=[dict(frequency_Hz=f,real_V_m=v.real.tolist(),imaginary_V_m=v.imag.tolist())for f,v in centres.items()],
        driven_max_current_relative_error=max(current_errors),driven_max_power_relative_error=max(power_errors),sampled_direction_count=len(post._DIRECTIONS))


def policy_module():
    return importlib.import_module('task1_resource_policy')


def implementation_receipt():
    modules=(drive,volume,waveform,carrier,view,core,policy_module())
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_frequency_resynthesis.py',*[Path(module.__file__).resolve()for module in modules]]
    # volume imports the JSON-only ranking helper; pin that dependency as well.
    paths.append(ROOT/'tools/task1_candidate_ranking.py')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in paths:
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)==path.read_bytes(),
            'All implementation/helpers/tests must match committed HEAD: '+str(path))
        pins[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def make_preregistration(baseline_summary,output):
    """Metadata-only adapter of the frozen baseline inventory; no basis compute."""
    plan=drive.make_preregistration(baseline_summary,output)
    policy=policy_module();ledger=policy.load_ledger(ROOT/'runtime/task1-budget.json')
    plan.update(schema=SCHEMA,conditions=[dict(row)for row in CONDITIONS],waveform='sine',
        feedback_id='T1-F010-frequency-GH6312627319',parent_feedback_id='T1-F010',
        source_feedback_id='T1-F010-frequency-GH6312627319',source_comment_id=6312627319,
        source_comment_url='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6312627319',
        source_Vpp_by_output=[1.,1.],
        resource_limits=dict(CPU_count=1,per_condition_seconds=180,total_seconds=480,preparation_seconds=60,finalization_seconds=60,
            RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,cumulative_budget_seconds=policy.effective_limit(ledger)),
        cohorts=['cached_original_square_3000_3030_caps','fresh_sine_3000_3030_caps'],
        cutoff_contract='Original cached square3000/3030 primary+supplemental mean/P10 fixed for every new condition/cohort/mode',
        scope='Exactly two actual-frequency pure-sine re-syntheses of one existing four-pad/two-output native basis; no new PDE',
        frequency_warning='Carrier pair AND beat change3000/3030,30Hz to9000/9090,90Hz; not a carrier-only contrast or physiological equivalence')
    plan.update(implementation_receipt());plan['input_sha256'].update(plan['implementation_files_sha256'])
    plan['resource_policy_refs']=policy.policy_refs(ledger)
    plan['input_sha256'].update(plan['resource_policy_refs'])
    plan['holds']+=['No pure-carrier causal interpretation because beat also changes30to90Hz',
        'New-frequency C1/probe-loaded/experimental/physiological validation not established']
    return plan


def verify_plan(path,baseline_summary,output,expected=None):
    path=Path(path).resolve();digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Preregistration changed during execution')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['new_PDE_conditions']==0
        and plan['conditions']==[dict(row)for row in CONDITIONS]and plan['waveform']=='sine'
        and plan['baseline_summary']==str(Path(baseline_summary).resolve())and plan['output_directory']==str(output),
        'Exact two actual-frequency pure-sine conditions/source/output required')
    for name,digest0 in plan['input_sha256'].items():
        source=Path(name);require(source.is_absolute()and source==source.resolve()and source.is_relative_to(ROOT)
            and source.is_file()and not source.is_symlink()and view.sha(source)==digest0,'Pinned source changed: '+name)
    require(view.read(baseline_summary)['input_sha256']==plan['native_input_sha256'],'Native source manifest differs')
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Implementation changed')
    return plan,digest


def candidate_burdens(electrical,skin,losses):
    j=skin['regions']['skin_SC_plus_dermis']['total']
    result={key:float(electrical[key])for key in view.CAPS}
    result.update(bulk_skin_J_vector_RMS_max_A_m2=j['J_vector_RMS_max_A_m2'],
        bulk_skin_J_vector_RMS_p95_A_m2=j['J_vector_RMS_p95_A_m2'],skin_SC_plus_dermis_power_W=losses['metrics']['skin_SC_plus_dermis_power_W'])
    return result


def derive(basis,geometry,volume_meta,cached,base_coeffs,declared,post,scalar,probe,output,deadline,references,cutoffs,checkpoint):
    pair=declared['actual_fundamental_Hz'];coeff=sine_coefficients(pair)
    spectra={f:np.einsum('c,cnk->nk',coeff[f],basis['f'][f]['field'])for f in pair}
    electrical=electrical_for_pair(basis,coeff,geometry,pair,post,deadline)
    if tuple(pair)==PAIRS[0]:
        old=next(c for c in cached['item']['summary']['conditions']if c['waveform']=='sine')
        for key in ('target20_modulation_V_m','target20_total_E_RMS_V_m',*view.CAPS):
            require(abs(electrical[key]-old['metrics'][key])<=1e-12+1e-10*abs(old['metrics'][key]),'Existing same-waveform sine electrical readback differs: '+key)
    checkpoint('volume_direction_projection',condition_id=declared['id'],actual_fundamental_Hz=pair)
    weights={name:cached['arrays']['region_'+name+'_m3']for name in ('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    native=scalar.evaluate_volume(spectra,basis['grid'],volume_meta,fundamental_frequencies_Hz=pair,
        region_weights=weights,fibonacci_count=2048,chunk_cells=256,deadline_monotonic=deadline)
    arrays={key:native['scalars'][key]for key in (*volume.METRICS,'maxTIS_direction_index')}
    arrays.update({'region_'+key+'_m3':value for key,value in native['region_weights_m3'].items()})
    np.savez_compressed(output/'volume.npz',**arrays);drive.write_json(output/'native-volume-metrics.json',native['metrics'])
    regions=volume.region_weights(arrays,basis['grid'],basis['metadata'])
    balance=carrier.carrier_metrics(spectra[pair[0]],spectra[pair[1]],native['scalars']['maxTIS_direction_index'],native['scalars']['maxTIS'],native['scalars']['fixedTIS'])
    skin=waveform.bulk_skin_current_density(spectra,basis['grid'],geometry['gamma_S_m'])
    losses=waveform.layer_losses_from_matrices({f:basis['f'][f]['loss']for f in pair},
        {f:basis['f'][f]['source']for f in pair},coeff,electrical)
    burdens=candidate_burdens(electrical,skin,losses);currents=electrical['source_current_RMS_by_output_mA']
    own_reference=dict(id=declared['id'],burdens=burdens,currents=currents,waveform='sine',actual_fundamental_Hz=pair)
    if tuple(pair)==PAIRS[0]:references['fresh_sine_3000_3030_caps']=own_reference
    provenance=dict(source_run_id=cached['item']['run'].name,source_condition_id=cached['item']['case']['id'],
        source_candidate_id=declared['id'],input_sha256=post._digest(basis['hashes']),code_sha256=view.sha(__file__),result_sha256=post._digest(basis['validation']))
    checkpoint('native_phi_probe40',condition_id=declared['id'])
    probes=probe.evaluate_layered_probe(basis['grid'],{f:basis['f'][f]['potential']for f in pair},
        {f:basis['f'][f]['field']for f in pair},geometry,coeff,provenance=provenance,fundamental_frequencies_Hz=pair,
        tip_gap_mm=5.,plus_pitch_mm=5.,depths_mm=(5.,10.,15.,20.))
    probes.update(actual_source_Vpp_by_output=[1.,1.],actual_fundamental_Hz=pair,beat_frequency_Hz=declared['beat_frequency_Hz'],waveform='sine')
    for row in probes['measurements']:row.pop('time_plot',None)
    drive.write_json(output/'probes.json',probes)
    require(probes['status']=='complete'and probes['numerical_checks']['all_passed'],'Actual-frequency phi/E40-probe validation incomplete')
    probe_audit=waveform.probe_check(dict(id=declared['id'],probe40=probes))
    field_audit=waveform.field_check(dict(id=declared['id'],waveform='sine',actual_fundamental_Hz=pair,metrics=electrical))
    cohorts={}
    for name,reference in references.items():
        modes=volume.normalization_modes(burdens,reference['burdens'],sum(currents),sum(reference['currents']))
        modes['raw_sine_1Vpp']=modes.pop('raw_1Vpp')
        for mode in modes.values():
            scale=mode['amplitude_scale'];mode.pop('source_Vpp_per_output',None);mode['source_Vpp_by_output']=[scale,scale]
            mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
            mode['regions']=volume.summarize_regions(native['scalars'],regions,basis['grid'],scale,cutoffs)
            mode['carrier_and_balance_regions']={region:{key:carrier.weighted(value if key.endswith('_balance')else value*scale,w,basis['grid'])
                for key,value in balance.items()if key in ('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
                for region,w in regions.items()}
            mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
            require(time.monotonic()<deadline,'Per-condition normalized statistics deadline exceeded')
        cohorts[name]=dict(reference_id=reference['id'],reference_waveform=reference['waveform'],
            reference_actual_fundamental_Hz=reference['actual_fundamental_Hz'],normalizations=modes,
            cutoff_reference='cached original square3000/3030; same frozen numerical values in every cohort')
    result=dict(schema='task1-frequency-resynthesis-condition-v1',status='calculated_unadopted',**declared,
        source_provenance=dict(run_id=cached['item']['run'].name,case_id=cached['item']['case']['id'],
            source_commit=cached['item']['registration']['source_commit'],source_summary=str(cached['item']['path']),
            configuration_sha256=basis['metadata']['config_sha256'],circuit=cached['item']['circuit']),
        waveform='sine',source_Vpp_by_output=[1.,1.],coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coeff.items()},
        electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,native_volume_metrics=native['metrics'],
        cohorts=cohorts,field_waveform_audit=field_audit,probe_waveform_audit=probe_audit,
        output_power_evidence=carrier.output_power_evidence(electrical),
        shared_square_baseline_cutoffs_V_m=cutoffs,new_PDE=0,candidate_adopted=False,numerical_validation_promoted=False,
        source_normalization='Original independent0.5Vpeak per-frequency basis; each active sine coefficient is-j1, including9000/9090Hz',
        frequency_warning='Carrier AND beat differ;30Hz versus90Hz. No physiological equivalence or carrier-only interpretation.',
        balance_definition='min/max fundamental projections,0/0 assigned0; no all-harmonic or activation interpretation',
        C1_status='No newly frequency-matched true electrode-pair control calculated',instrument_loading_validated=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],actual_fundamental_Hz=pair,beat_frequency_Hz=declared['beat_frequency_Hz'],status=result['status'],
        artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))for name in ('condition.json','probes.json','volume.npz','native-volume-metrics.json')})


def execute(plan,baseline_summary,output,deadline,checkpoint):
    item=drive.baseline_item(baseline_summary);cached=volume.load_native(item)
    post,scalar,probe=drive.import_frozen(item['run'],plan)
    basis=post._load_basis(item['run']/'bases'/item['case']['id'],item['case'],min(deadline,time.monotonic()+60))
    require(basis['hashes']==plan['native_input_sha256'],'Loaded native basis digest differs')
    geometry,volume_meta=post._geometry(basis,item['case']);require(np.array_equal(basis['grid'],cached['grid']),'Scalar/native grid mismatch')
    square_burden,square_current=volume.burdens(item,cached['condition'])
    refs={'cached_original_square_3000_3030_caps':dict(id=cached['condition']['id'],burdens=square_burden,currents=square_current,
        waveform='square_3h',actual_fundamental_Hz=[3000,3030])}
    cutoffs={metric:{region+'_'+stat:volume.weighted_statistics(cached['arrays'][metric],cached['regions'][region])[stat]
        for region in (volume.PRIMARY,volume.SLAB)for stat in ('mean','p10')}for metric in volume.METRICS}
    results=[]
    for declared in plan['conditions']:
        current_deadline=min(deadline,time.monotonic()+180);signal.setitimer(signal.ITIMER_REAL,max(.001,current_deadline-time.monotonic()))
        folder=output/declared['id'];folder.mkdir();checkpoint('condition_start',condition_id=declared['id'])
        results.append(derive(basis,geometry,volume_meta,cached,None,declared,post,scalar,probe,folder,current_deadline,refs,cutoffs,checkpoint))
        checkpoint('condition_complete',condition_id=declared['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-frequency-resynthesis-audit-v1',status='calculated_unadopted',conditions=results,new_PDE=0,
        actual_frequency_pairs=[list(pair)for pair in PAIRS],actual_beat_frequencies_Hz=[30,90],waveform='sine',
        comparison_cohorts=plan['cohorts'],holds=plan['holds'],candidate_adopted=False,numerical_validation_promoted=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline-summary',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs')and output.relative_to(ROOT/'docs').parts[0].startswith('cloud-next'), 'New docs/cloud-next... output required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not output.exists(),'Never overwrite attempted frequency resynthesis')
        policy=policy_module();ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path)
        require(policy.remaining_seconds(ledger)>=480,'Admission requires finite480s within authorized cumulative policy')
        require(shutil.disk_usage(output.parent).free>=2*GIB+256*1024**2,'Keep2GiB reserve plus256MiB bounded artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});output.mkdir();start=time.monotonic();deadline=start+480
        status='failed_preserved';failure=None;mutex=threading.RLock();stop=threading.Event();state={};counter=0
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
                require(shutil.disk_usage(output).free>=2*GIB,'Existing2GiB reserve exhausted')
                counter+=1;state.update(phase=phase,status=status if phase=='complete'else'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                    updated_utc=core.now(),elapsed_seconds=time.monotonic()-start,**extra)
                drive.write_json(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5.):
                with mutex:core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-start))
        def timeout(signum,frame):raise TimeoutError('180s condition/480s frequency batch deadline exceeded')
        def interrupted(signum,frame):raise RuntimeError('Controlled frequency batch signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60);thread=threading.Thread(target=heartbeat,daemon=True)
        try:
            thread.start();checkpoint('verify_plan');plan,plan_sha=verify_plan(args.plan.resolve(),args.baseline_summary,output)
            result=execute(plan,args.baseline_summary,output,deadline,checkpoint)
            verify_plan(args.plan.resolve(),args.baseline_summary,output,expected=plan_sha)
            result.update(implementation_receipt(),preregistration=dict(path=str(args.plan.resolve()),SHA256=plan_sha),
                input_sha256=plan['input_sha256'],inputs_unchanged=True,wall_seconds=time.monotonic()-start,
                resources=dict(CPU_count=1,authorized_cumulative_seconds=policy.effective_limit(ledger),max_batch_seconds=480,
                    max_condition_seconds=180,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
            drive.write_json(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            drive.write_json(output/'failure.json',dict(status=status,error=failure,new_PDE=0,partial_artifacts_preserved=True));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread.ident is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='actual_frequency_resynthesis',seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            with mutex:core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
