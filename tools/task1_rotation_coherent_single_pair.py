"""Finite cached C1 RMS matches for three fixed rotated-return references.

No PDE, new reference resynthesis, source mutation or physiological equivalence.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import fcntl
import gzip
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
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
import numpy as np
import task1_coherent_single_pair as old
import task1_drive_ratio_audit as drive
import task1_results_view as view
import task1_cloud_batch as core
import task1_resource_policy as policy

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
RUN=old.RUN
C1=old.C1
SCHEMA='task1-rotation-coherent-single-pair-preregistration-v1'
SOURCE_SUMMARY=ROOT/'docs/cloud-rotation-coherent-20261021T182000Z/summary.json'
ROTATION_SUMMARY=ROOT/'data-native/cloud-one-return-rotation-20261021T174000Z/postprocess/asym-return2-rot90-xy80/summary.json'
REFERENCE_IDS=('rotation-square-control','rotation-sine-control','rotation-coherent-r1-p090')
MODES=('raw','skin_contact_only')
require=old.require
read=old.read
sha=old.sha
write_new=old.write_new
properties=old.properties
validate_single=old.validate_single
weighted_energy_rms=old.weighted_energy_rms
weighted_p95=old.weighted_p95
sample_native=old.sample_native
scale_burdens=old.scale_burdens
matched_single=old.matched_single
scaled_probe_rows=drive.scaled_probe_rows


def reference_footprint(expected_pad_areas_m2,circuit):
    a=np.asarray(expected_pad_areas_m2,float)
    require(a.shape==(circuit['n_pads'],)and np.isfinite(a).all()and np.all(a>0),'Positive physical-pad footprint array matching circuit required')
    return dict(physical_pads=circuit['n_pads'],independent_outputs=circuit['n_outputs'],common_return_nodes=circuit['n_return_nodes'],
        per_pad_area_mm2=(a*1e6).tolist(),total_contact_area_mm2=float(a.sum()*1e6),
        interpretation='Contact footprint differs between C1 and TIS cohorts; RMS matching does not equalize footprint')


def target_matches(target_centre,target_roi,single_centre,single_roi,burdens,probe):
    require(all(math.isfinite(x)and x>0 for x in(target_centre,target_roi,single_centre,single_roi)), 'Positive finite target/control RMS values required')
    matches=matched_single(target_centre,target_roi,single_centre,single_roi,burdens)
    for row in matches.values():
        scale=row['amplitude_scale'];row['actual_source_Vpp']=scale;row['source_peak_V']=.5*scale
        row['unloaded_probe40']=scaled_probe_rows(probe,scale)
        row['single_frequency_modulation_definition']='One pure sinusoid has zero temporal envelope variation; field RMS equality does not imply equal activation'
    return matches


def implementation():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in(Path(__file__).resolve(),ROOT/'tests/test_task1_rotation_coherent_single_pair.py',
        *[Path(m.__file__).resolve()for m in(old,drive,view,core,policy)]):
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)==path.read_bytes(),
            'Commit implementation/helper/test before research execution: '+str(path))
        pins[str(path)]=sha(path)
    return dict(source_commit=commit,implementation_sha256=pins)


def validate_decision(decision,source_sha):
    require(decision.get('schema')=='task1-rotation-coherent-single-pair-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('reference_ids')==list(REFERENCE_IDS)and decision.get('modes')==list(MODES)and decision.get('single_case_id')==C1 and
        decision.get('single_frequency_Hz')==3000 and decision.get('new_PDE')==0 and decision.get('candidate_adopted')is False and
        decision.get('source_summary_path')==str(SOURCE_SUMMARY)and decision.get('source_summary_sha256')==source_sha and
        isinstance(decision.get('question'),str)and bool(decision['question'].strip()),'Exact root-selected three-reference twelve C1 RMS matches required')


def make_preregistration(output,decision_path,feedback_path):
    receipt=implementation();refs=dict(receipt['implementation_sha256'])
    def bind(path,expected=None):
        path=Path(path);require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and not path.is_symlink(),'Canonical local source required')
        digest=sha(path);require(expected is None or digest==expected,'Source SHA mismatch: '+str(path));refs[str(path)]=digest;value=read(path)
        require(sha(path)==digest,'Source changed while reading');return value
    source=ROOT/'data-native'/RUN;pre=bind(source/'preregistration.json')
    single=next(c for c in pre['cases']if c['id']==C1);summary_path=source/'postprocess'/C1/'summary.json';summary=bind(summary_path)
    record=bind(source/'cases'/(C1+'.json'))
    require(summary['status']==record['status']=='complete'and record['postprocess_path']==str(summary_path)and record['postprocess_sha256']==refs[str(summary_path)],'Completed original C1 receipt required')
    validate_single(single,summary['mesh_metadata'])
    gates=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
    require(pre['gates']==gates and all(math.isfinite(record['validation'][k])and 0<=record['validation'][k]<=v for k,v in gates.items()),'Original five C1 native gates required')
    config=properties(single['config_file'])
    for p,(x,y)in enumerate(((-10.,-10.),(10.,-10.))):
        require(float(config[f'pad.{p}.x_mm'])==x and float(config[f'pad.{p}.y_mm'])==y and
            float(config[f'pad.{p}.width_mm'])==float(config[f'pad.{p}.height_mm'])==15.,'Original C1 source/return geometry required')
    sine=next(c for c in summary['conditions']if c['waveform']=='sine'and c['actual_fundamental_Hz']==[3000])
    primary=next(c for c in summary['conditions']if c['waveform']=='square_3h'and c['actual_fundamental_Hz']==[3000])
    scout=bind(SOURCE_SUMMARY)
    require(scout['schema']=='task1-rotation-coherent-scout-v1'and scout['status']=='calculated_unadopted'and scout['inputs_unchanged']is True and
        scout['candidate_adopted']is False,'Completed source-bound rotated coherent scout required')
    rotation=bind(ROTATION_SUMMARY);rotation_record_path=ROTATION_SUMMARY.parents[2]/'cases'/'asym-return2-rot90-xy80.json';rotation_record=bind(rotation_record_path)
    require(rotation_record['status']==rotation['status']=='complete'and rotation_record['postprocess_sha256']==refs[str(ROTATION_SUMMARY)],'Completed rotated geometry source required')
    control_volume=bind(scout['cached_control_volume']['path'],scout['cached_control_volume']['SHA256'])
    require(control_volume['status']=='calculated_unadopted'and control_volume['inputs_unchanged']is True,'Completed unchanged cached square volume audit required')
    square_control=scout['cached_controls']['rotation_equal_drive']
    require(square_control['summary_path']==str(ROTATION_SUMMARY)and square_control['condition_id']=='asym-return2-rot90-xy80-square_3h'and
        control_volume['inputs_sha256'][str(ROTATION_SUMMARY)]==refs[str(ROTATION_SUMMARY)]and
        any(c==square_control for c in control_volume['cases']),'Cached rotated square control must remain source-bound')
    square=next(c for c in rotation['conditions']if c['id']==square_control['condition_id'])
    references=[dict(id=REFERENCE_IDS[0],kind='cached_square3h',summary_path=str(ROTATION_SUMMARY),condition_id=square['id'],
        native_npz=str(ROTATION_SUMMARY.parent/'volume.npz'),electrical_metrics=square['metrics'],source_commit=square_control['source_commit'],
        configuration_sha256=rotation['mesh_metadata']['config_sha256'],circuit=square_control['circuit'],
        normalized_modes={k:square_control['normalizations']['raw_1Vpp'if k=='raw'else k]for k in MODES},
        source_intervals_V=[[1.,1.],[1.,1.]],waveform='square_3h',frequencies_Hz=[3000,3030,9000,9090],probe_reference=square_control['raw_probe_artifact_reference'])]
    refs[references[0]['native_npz']]=rotation['artifacts']['files']['volume.npz']['SHA256']
    rotation_probe=ROTATION_SUMMARY.parent/rotation['artifacts']['probes_json']
    refs[str(rotation_probe)]=rotation['artifacts']['files'][rotation_probe.name]['SHA256']
    for ident in REFERENCE_IDS[1:]:
        row=next(c for c in scout['conditions']if c['id']==ident);art=row['artifacts'];condition=bind(art['condition.json']['path'],art['condition.json']['SHA256'])
        require(condition['id']==ident and condition['status']=='calculated_unadopted'and condition['source_case_id']=='asym-return2-rot90-xy80'and
            condition['configuration_sha256']==rotation['mesh_metadata']['config_sha256']and condition['candidate_adopted']is False and
            condition['actual_fundamental_Hz']==[3000,3030]and not condition['harmonics_active'],'Exact fixed rotated two-carrier source required')
        for name in('volume.npz','probes.json'):refs[art[name]['path']]=art[name]['SHA256']
        references.append(dict(id=ident,kind='fresh_sine'if ident==REFERENCE_IDS[1]else'coherent_sine',summary_path=str(SOURCE_SUMMARY),
            condition_path=art['condition.json']['path'],condition_id=ident,native_npz=art['volume.npz']['path'],
            electrical_metrics=condition['electrical_metrics'],source_commit=condition['source_commit'],configuration_sha256=condition['configuration_sha256'],
            circuit=condition['source_circuit'],normalized_modes={k:condition['normalizations']['raw_1Vpp'if k=='raw'else k]for k in MODES},
            source_intervals_V=condition['source_waveform']['source_Vpp_intervals_V'],waveform=condition['waveform'],frequencies_Hz=[3000,3030],probe_reference=art['probes.json']))
    decision=bind(decision_path);validate_decision(decision,refs[str(SOURCE_SUMMARY)]);feedback=bind(feedback_path);old.validate_feedback(feedback)
    require(isinstance(decision.get('input_sha256'),dict)and decision['input_sha256'].get(str(feedback_path))==refs[str(feedback_path)],'Root decision must bind the same actual feedback receipt')
    for name,digest in decision['input_sha256'].items():bind(name,digest)
    paths=dict(single_summary=str(summary_path),single_npz=str(source/'postprocess'/C1/primary['native_volume_archive']),case_config=single['config_file'],case_mask=single['mask_file'])
    refs[paths['single_npz']]=summary['artifacts']['files'][primary['native_volume_archive']]['SHA256']
    for key in('case_config','case_mask'):refs[paths[key]]=single[key.removeprefix('case_')+'_sha256']
    selected={p:d for p,d in summary['input_sha256'].items()if Path(p).name in('grid.csv.gz','grid.csv','mesh-metadata.json','validation.json','BASIS_COMPLETE',
        'field-3000.bin.gz','potential-3000.bin.gz','density-3000.bin','source-3000.bin','loss-3000.bin','contacts-3000.csv')}
    require(len(selected)==10,'Exact ten complete cached3k C1 field/potential/current/loss inputs required');refs.update(selected)
    probe=source/'postprocess'/C1/summary['artifacts']['probes_json'];refs[str(probe)]=summary['artifacts']['files'][probe.name]['SHA256'];paths['single_unloaded_probes']=str(probe)
    refs.update(policy.policy_refs(policy.load_ledger()))
    area=rotation['contact_area_validation']['3000']['expected_pad_area_m2'];c1area=single.get('expected_pad_areas_m2',[225e-6,225e-6])
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),reference_ids=list(REFERENCE_IDS),modes=list(MODES),
        references=references,paths=paths,single_case=single,single_sine_condition_id=sine['id'],single_case_id=C1,
        native_input_sha256=selected,input_sha256=refs,new_PDE=0,max_seconds=120,**receipt,
        root_selection_decision=dict(path=str(decision_path),SHA256=refs[str(decision_path)],question=decision['question']),
        feedback_context=dict(path=str(feedback_path),SHA256=refs[str(feedback_path)],observed_utc=feedback['observed_utc']),
        cohort_footprints=dict(C1=reference_footprint(c1area,single['circuit']),rotated_TIS=reference_footprint(area,references[0]['circuit'])),
        matching_definitions=['centre20 native E trilinear RMS','sqrt(sum(fractional_ROI_volume * native_E_RMS_squared)/sum(fractional_ROI_volume))'],
        holds=['All reference candidates remain unadopted; canonical original square eight-skin caps define skin8 reference normalization',
            'RMS matching is not modulation or physiological equivalence; C1 is one actual source-return electrode pair',
            'Source pad area/footprint differs between C1 and TIS; no equal-footprint claim',
            'Native numerical checks do not establish mesh/contact/sphere convergence or experimental validation',
            'Unloaded phi-derived probe predictions; instrument loading/calibration remains unvalidated'])


def verify_plan(path,output):
    plan=read(path);require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['reference_ids']==list(REFERENCE_IDS)and
        plan['modes']==list(MODES)and plan['single_case_id']==C1 and plan['output_directory']==str(output)and plan['max_seconds']==120 and plan['new_PDE']==0,
        'Exact bounded three-reference twelve RMS matches plan required')
    require(implementation()['implementation_sha256']==plan['implementation_sha256'],'Implementation changed')
    for name,digest in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and sha(p)==digest,'Pinned input changed: '+name)
    return plan

def load_single(plan,phase=lambda name:None):
    phase('read-native')
    paths=plan['paths'];summary=read(paths['single_summary'])
    sine=next(c for c in summary['conditions']if c['id']==plan['single_sine_condition_id']);meta=summary['mesh_metadata'];validate_single(plan['single_case'],meta)
    def native(name):return Path(next(p for p in plan['native_input_sha256']if Path(p).name in (name,name+'.gz')))
    def complex_array(name,shape):
        p=native(name);opener=gzip.open if p.suffix=='.gz'else open
        with opener(p,'rb')as stream:raw=stream.read()
        a=np.frombuffer(raw,dtype='<c16');require(a.size==math.prod(shape)and np.isfinite(a).all(),'Exact finite complex native dimensions required');return a.reshape(shape)
    gp=native('grid.csv');opener=gzip.open if gp.suffix=='.gz'else open
    with opener(gp,'rt')as stream:grid=np.genfromtxt(stream,delimiter=',',names=True)
    n=meta['cells'];require(len(grid)==n,'Native grid cell count mismatch')
    with np.load(paths['single_npz'],allow_pickle=False)as a:weights=a['region_target_m3'];total=a['region_total_m3']
    field=-1j*complex_array('field-3000.bin',(1,n,3))[0];phi=-1j*complex_array('potential-3000.bin',(1,n))[0]
    erms=np.sqrt(np.sum(abs(field)**2,axis=1)/2);single_roi=weighted_energy_rms(erms,weights)
    centre_field=sample_native(field,grid);single_centre=float(np.sqrt(np.vdot(centre_field,centre_field).real/2))
    require(math.isclose(single_centre,sine['metrics']['target20_total_E_RMS_V_m'],rel_tol=1e-10,abs_tol=1e-12),'Stored native centre RMS reproduction failed')
    cp=native('contacts-3000.csv');contacts=np.genfromtxt(cp,delimiter=',',names=True);area=contacts['area_m2'];pads=contacts['pad'].astype(int)
    require(set(pads)=={0,1}and np.all(area>0),'Exactly source/return physical contact IDs required')
    density=-1j*complex_array('density-3000.bin',(1,len(area)))[0];transfer=complex_array('source-3000.bin',(1,1))[0,0];loss=complex_array('loss-3000.bin',(6,1,1))[:,0,0]
    actual_areas=[float(area[pads==p].sum())for p in range(2)]
    require(np.allclose(np.asarray(actual_areas)*1e6,plan['cohort_footprints']['C1']['per_pad_area_mm2'],rtol=1e-10,atol=1e-12),
        'Native C1 represented contact areas differ from fixed physical footprint')
    require(np.max(abs(loss.imag))<1e-12 and np.all(loss.real>=-1e-12),'Finite passive six-compartment loss evidence required')
    current=-1j*transfer;balance=abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)),1e-30)
    require(balance<=2e-6 and abs(np.sum(density[pads==0]*area[pads==0])-current)<=2e-6*abs(current),'Single-pair current conservation failed')
    require(abs(loss.real.sum()-.25*transfer.real)<=2e-7*abs(.25*transfer.real),'Single-pair power conservation failed')
    config=properties(paths['case_config']);za=complex(float(config['z.3000.re']),float(config['z.3000.im']));jrms=abs(density)/np.sqrt(2)
    layer=grid['layer'].astype(int);gamma=np.asarray([complex(float(config[k+'.sigma']),2*np.pi*3000*8.8541878128e-12*float(config[k+'.epsilon_r']))for k in ('sc','dermis','fat','muscle')])
    skin=layer<=1;jskin=abs(gamma[layer])*erms
    burdens=dict(source_current_RMS_mA=float(abs(current)/np.sqrt(2)*1000),source_current_peak_mA=float(abs(current)*1000),
        contact_J_RMS_max_A_m2=float(jrms.max()),contact_J_RMS_p95_A_m2=weighted_p95(jrms,area),
        contact_voltage_RMS_max_V=float((abs(density*za)/np.sqrt(2)).max()),
        bulk_skin_J_RMS_max_A_m2=float(jskin[skin].max()),bulk_skin_J_RMS_p95_A_m2=weighted_p95(jskin[skin],total[skin]),
        SC_power_W=float(loss[0].real),dermis_power_W=float(loss[1].real),skin_SC_plus_dermis_power_W=float(loss[0].real+loss[1].real),
        fat_power_W=float(loss[2].real),muscle_power_W=float(loss[3].real),contact_power_W=float(loss[4].real),
        tissue_contact_power_W=float(loss[:5].real.sum()),source_resistor_power_W=float(loss[5].real),source_power_W=float(.25*transfer.real),
        loaded_metal_Vpp=float(2*abs(-.5j-50*current)))
    for key,stored in [('contact_J_RMS_max_A_m2','surface_J_RMS_max_A_m2'),('contact_J_RMS_p95_A_m2','surface_J_RMS_p95_A_m2'),('source_power_W','source_power_W')]:
        require(math.isclose(burdens[key],sine['metrics'][stored],rel_tol=1e-10,abs_tol=1e-12),'Stored sine burden reproduction failed: '+key)
    probe_summary=read(paths['single_unloaded_probes'])
    row=next(c for c in probe_summary['conditions']if c['id']==sine['id']and c['waveform']=='sine');probe=row['probe40']
    require(probe_summary['status']=='complete'and probe['status']=='complete'and probe['numerical_checks']['all_passed']and len(probe['measurements'])==40,
        'Completed source-bound nativephi C1 sine forty probes required')
    scaled_probe_rows(probe,1.)
    return dict(grid=grid,weights=weights,total=total,centre=single_centre,roi=single_roi,burdens=burdens,probe=probe,sine=sine,
        represented_pad_contact_areas_m2=actual_areas)


def execute(plan,phase=lambda name:None):
    single=load_single(plan,phase);phase('match-twelve-targets');targets=[]
    for ref in plan['references']:
        with np.load(ref['native_npz'],allow_pickle=False)as z:
            require(np.array_equal(single['weights'],z['region_target_m3'])and np.array_equal(single['total'],z['region_total_m3']),
                'Reference/C1 full-precision fractional ROI and native volumes differ')
            energy=weighted_energy_rms(z['RMS'],single['weights'])
        point=ref['electrical_metrics']['target20_total_E_RMS_V_m']
        require(math.isfinite(point)and point>0,'Positive finite source-bound reference centre RMS required')
        for mode in MODES:
            data=ref['normalized_modes'][mode];scale=data['amplitude_scale']
            require(math.isfinite(scale)and scale>0 and(mode!='raw'or scale==1.),'Explicit raw1 or positive skin8 common amplitude required')
            targets.append(dict(id=ref['id']+'--'+mode,reference_id=ref['id'],reference_waveform=ref['waveform'],reference_frequencies_Hz=ref['frequencies_Hz'],
                reference_summary_path=ref['summary_path'],reference_condition_id=ref['condition_id'],reference_source_commit=ref['source_commit'],
                reference_configuration_sha256=ref['configuration_sha256'],reference_circuit=ref['circuit'],
                reference_amplitude_scale=scale,reference_source_Vpp_intervals_V=(np.asarray(ref['source_intervals_V'])*scale).tolist(),
                reference_centre20_E_RMS_V_m=point*scale,reference_ROI_energy_RMS_V_m=energy*scale,
                reference_nine_burdens=data['normalized_burdens'],reference_source_output_RMS_by_output_mA=data['source_output_RMS_by_output_mA'],
                reference_probe_artifact=ref['probe_reference'],canonical_skin8_limits=data['baseline_derived_numerical_limits'],
                matches=target_matches(point*scale,energy*scale,single['centre'],single['roi'],single['burdens'],single['probe'])))
    require(len(targets)==6 and sum(len(t['matches'])for t in targets)==12,'Exactly twelve independent C1 RMS matches required')
    return dict(schema='task1-rotation-coherent-single-pair-rms-v1',status='calculated_unadopted',targets=targets,reference_ids=list(REFERENCE_IDS),modes=list(MODES),
        source_summary_path=str(SOURCE_SUMMARY),source_summary_sha256=plan['input_sha256'][str(SOURCE_SUMMARY)],cohort_footprints=plan['cohort_footprints'],
        single_stimulation=dict(case_id=C1,source_run_id=RUN,circuit=plan['single_case']['circuit'],physical_pad_centres_mm=[[-10,-10],[10,-10]],waveform='pure sine',
            frequency_Hz=3000,raw_source_Vpp=1.,raw_centre20_E_RMS_V_m=single['centre'],raw_ROI_energy_RMS_V_m=single['roi'],raw_burdens=single['burdens'],
            represented_pad_contact_areas_m2=single['represented_pad_contact_areas_m2'],
            unloaded_probe_reference=dict(path=plan['paths']['single_unloaded_probes'],SHA256=plan['input_sha256'][plan['paths']['single_unloaded_probes']],
                condition_id=single['sine']['id'],probe_count=40,tip_gap_mm=5.,coordinate_system=single['probe']['coordinate_system'],
                scaling='Saved source-bound nativephi sine waveforms/spectra and scalar statistics share each exact positive matching amplitude_scale')),
        point_definition='Native complex E trilinear interpolation at(0,0,20)mm, sqrt(sum_f dot(E*,E)/2)',
        ROI_definition='Central r<=5mm, depth15..20; full-precision fractional volume; sqrt(weighted mean native E_RMS squared), NOT mean(E_RMS)',
        new_PDE=0,new_native_RHS=0,new_reference_recomposition=0,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,
        instrument_loading_validated=False,root_selection_decision=plan['root_selection_decision'],feedback_context=plan['feedback_context'],holds=plan['holds'])

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
        require(shutil.disk_usage(output.parent).free>=2*GIB+256*1024**2,'Preserve2GiB reserve plus bounded artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+cap
        status='failed_preserved';failure=None;state={};counter=0;mutex=threading.RLock();stop=threading.Event();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
            require(shutil.disk_usage(output.parent).free>=2*GIB,'Existing2GiB disk reserve exhausted')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=2*GIB,'New artifacts exceed2GiB cap')
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
                require(not args.prepare.exists()and not args.prepare.resolve().is_relative_to(output),
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
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='rotation_coherent_single_pair_prepare'if args.prepare else'rotation_coherent_single_pair',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
