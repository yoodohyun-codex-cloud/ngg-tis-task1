"""Finite cached original-square two-output complex-drive analysis.

Proxy ranking uses the exact frozen2074 target-direction metric and a guarded
three-lambda spectral off-target upper bound. Full-volume2074 validation remains separate.
Only up to one novel improving gene receive actual full2074/40phi validation.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import hashlib
import itertools
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
for _thread_var in('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_thread_var]='1'
import numpy as np
import task1_rounded_drive_scout as base
import task1_rounded_drive_optimization as frozen
import task1_direction_bounds_audit as direction_audit
ROOT=base.ROOT
GIB=base.GIB
FREQUENCIES=base.FREQUENCIES
PAIR=base.PAIR
SOURCE_RUN='cloud-mesh-c1-20261019T190000Z'
SOURCE_ID='baseline-square15-xy80'
SOURCE_SUMMARY=ROOT/'data-native'/SOURCE_RUN/'postprocess'/SOURCE_ID/'summary.json'
BASELINE_SUMMARY=base.BASELINE_SUMMARY
CONTROL_VOLUME=ROOT/'docs/cloud-adjacent-cross-20261021T164000Z/volume.json'
SCHEMA='task1-original-cached-drive-preregistration-v1'
GENES=('z0_real','z0_imag','z1_real','z1_imag','rho')
BOUNDS=((-.15,.15),)*4+((.9,1.1),)
STEPS=(.03,.015,.005)
# Third seed is the exact actual weak-r.05-p090 command after its historical
# independent output normalization, divided by its common -j primary amplitude.
# Tiny phase terms and rho drift are retained; no rounding to [0,.05,0,.05,1].
SEEDS=((0.,0.,0.,0.,1.),(-.03,0.,-.03,0.,1.),
    (-3.0616341296444263e-18,.050000279783135114,3.061616997868383e-18,.05,1.000005595662702))
SEARCH_CONTRACT=dict(gene_names=list(GENES),bounds=[list(v)for v in BOUNDS],steps=list(STEPS),seeds=[list(v)for v in SEEDS],
    maximum_proxy_evaluations=72,proxy_seconds=180,maximum_final_candidates=1,total_seconds=360,
    per_condition_seconds=120,output_bound_bytes=32*1024**2,command_gauge='sine: c3000=-j[1,z0],c3030=-j[z1,rho],peak0.5V,+jwt')
OUTPUT_BOUND_BYTES=32*1024**2
PROXY_DEFINITION=dict(target='Exact maximum over the actual frozen2074 sampled real directions on full positive-weight primary ROI; volume-weighted mean/P10',
    off_target='Minimum of guarded largest eigenvalues at lambda0,0.5,1 on Qa/Qb; continuous-direction upper bound used only for ranking',
    lambdas=[0.,.5,1.],skin='Exact full native8 skin/contact burdens; source power and1Vpp ceiling excluded',
    gates='Original square eight screens/cutoffs; target sampled2074 exact, off-target spectral UB remains surrogate ranking only',
    whole_source_Vpp_normalized=False,raw_1Vpp_claimed=False,ranked_only_not_full2074_validation=True,
    target2074_is_continuous_maximum=False)
OLD_STRONG_SUMMARY=ROOT/'docs/cloud-next-coherent-drive-20261021T165000Z/summary.json'
OLD_WEAK_SUMMARY=ROOT/'docs/cloud-next-coherent-weak-20261021T170000Z/summary.json'
PURE_SUMMARY=ROOT/'docs/cloud-next-frequency-20261021T104000Z/summary.json'
PURE_ID='sine-3000-3030-beat30'
require=base.require
drive=base.drive
volume=base.volume
waveform=base.waveform
carrier=base.carrier
frequency=base.frequency
power=base.power
screen=base.screen
core=base.core
policy=base.policy
view=base.view
ranking=base.ranking
routing=base.routing
strong=base.strong


def valid_gene(g):
    return isinstance(g,(list,tuple))and len(g)==5 and all(type(v)in(int,float)and math.isfinite(v)and lo<=v<=hi for v,(lo,hi)in zip(g,BOUNDS))


def gene_key(g,source_identity='synthetic',metric_identity='synthetic'):
    require(valid_gene(g),'Finite five genes inside registered bounds required; no clipping')
    values=[float(v).hex()for v in g]
    return hashlib.sha256(json.dumps([source_identity,metric_identity,values],separators=(',',':')).encode()).hexdigest()


def gene_coefficients(g):
    require(valid_gene(g),'Finite bounded five-gene source command required')
    z0=complex(g[0],g[1]);z1=complex(g[2],g[3])
    return{3000:-1j*np.array([1.,z0],complex),3030:-1j*np.array([z1,g[4]],complex),9000:np.zeros(2,complex),9090:np.zeros(2,complex)}


ProxyDeadline=frozen.ProxyDeadline
spectral_upper=frozen.spectral_upper
sampled_target=frozen.sampled_target
frozen_direction_set=frozen.frozen_direction_set
proxy_objective=frozen.proxy_objective


def bounded_pattern_search(evaluator,*,deadline,max_evaluations=72,clock=time.monotonic,source_identity='synthetic',metric_identity='synthetic'):
    require(type(max_evaluations)is int and 1<=max_evaluations<=72,'Finite evaluation cap1..72 required')
    cache={};rows=[];aliases=[];skipped=[];levels=[];attempts=0;stop_reason=None
    def evaluate(g,origin):
        nonlocal attempts,stop_reason
        if not valid_gene(g):skipped.append(dict(genes=list(g),origin=origin,reason='out_of_bounds_no_clipping'));return None
        key=gene_key(g,source_identity,metric_identity)
        if key in cache:aliases.append(dict(genes=list(g),origin=origin,key=key,alias_of=cache[key]['evaluation_index']));return cache[key]
        if attempts>=max_evaluations or clock()>=deadline:stop_reason='evaluation_cap'if attempts>=max_evaluations else'proxy_wall_deadline';return None
        attempts+=1
        try:record=evaluator(tuple(map(float,g)))
        except ProxyDeadline as error:stop_reason=str(error)or'proxy_wall_deadline';return None
        objective=tuple(record['objective'])
        require(len(objective)==3 and all(type(v)in(int,float)and math.isfinite(v)for v in objective),'Finite lexicographic proxy objective required')
        row=dict(evaluation_index=len(rows),genes=list(map(float,g)),key=key,origin=origin,objective=list(objective),record=record)
        rows.append(row);cache[key]=row;return row
    incumbents=[];seed_records=[]
    try:
        for index,g in enumerate(SEEDS):
            row=evaluate(g,dict(seed=index,phase='seed'));incumbents.append(row);seed_records.append(row)
            if stop_reason:break
        if stop_reason is None:
            for step in STEPS:
                for index in range(len(SEEDS)):
                    anchor=incumbents[index];neighbors=[];evaluated=0
                    for dim in range(5):
                        for sign in(-1,1):
                            g=list(anchor['genes']);g[dim]+=sign*step
                            row=evaluate(g,dict(seed=index,step=step,dimension=dim,sign=sign,phase='neighbor'))
                            if row is not None:neighbors.append(row);evaluated+=1
                            if stop_reason:break
                        if stop_reason:break
                    complete=stop_reason is None
                    chosen=min([anchor,*neighbors],key=lambda row:(tuple(row['objective']),row['key']))if complete else anchor
                    incumbents[index]=chosen
                    levels.append(dict(seed=index,step=step,anchor_genes=anchor['genes'],completed=complete,
                        returned_neighbor_records=evaluated,next_anchor_genes=chosen['genes'],anchor_updated_once=complete))
                    if stop_reason:break
                if stop_reason:break
    except ProxyDeadline as error:
        stop_reason=str(error)or'proxy_wall_deadline'
    return dict(status='proxy_budget_exhausted_partial'if stop_reason else'proxy_search_complete_ranked_only',
        ranked_only_not_full2074_validation=True,evaluations=rows,aliases=aliases,skipped=skipped,levels=levels,
        evaluation_attempts=attempts,completed_evaluations=len(rows),stop_reason=stop_reason,
        seed_evaluation_indices=[row['evaluation_index']for row in seed_records if row is not None],
        incumbent_evaluation_indices=[row['evaluation_index']for row in incumbents if row is not None],
        global_optimum_claimed=False,all72_evaluations_promised=False)


def context_metadata(decision_path,feedback_path,pins):
    require(decision_path is not None and feedback_path is not None,'Explicit root decision and actual feedback GET context required')
    def bound(path):
        path=Path(path)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.stat().st_size<=25*1024**2,'Canonical local public JSON context required')
        digest=view.sha(path);value=view.read(path);require(view.sha(path)==digest,'Context changed while reading')
        pins[str(path)]=digest;return value,dict(path=str(path),SHA256=digest)
    decision,dref=bound(decision_path);feedback,fref=bound(feedback_path)
    require(decision.get('schema')=='task1-original-cached-drive-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('new_PDE')==0 and decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        decision.get('search_contract')==SEARCH_CONTRACT,'Exact root-selected bounded five-gene search required; peer endorsement must not be inferred')
    refs=decision.get('input_sha256');require(isinstance(refs,dict)and bool(refs),'Root decision must bind completed scientific evidence')
    require(all(refs.get(str(p))==view.sha(p)for p in(OLD_STRONG_SUMMARY,OLD_WEAK_SUMMARY,PURE_SUMMARY,CONTROL_VOLUME)),
        'Root decision must bind completed strong/weak/pure original drives and original-square volume control')
    require(refs.get(str(Path(feedback_path)))==fref['SHA256'],'Root decision must bind the same actual feedback GET receipt')
    for name,digest in refs.items():
        path=Path(name)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.suffix=='.json'and path.stat().st_size<=25*1024**2 and view.sha(path)==digest,
            'Root selected evidence changed: '+name)
        pins[str(path)]=digest
    require(feedback.get('schema')=='task1-queue-feedback-v1'and feedback.get('status')=='read_only_feedback_checked'and
        feedback.get('error')is None and feedback.get('public_GitHub_only')is True and feedback.get('messages_sent')==0 and
        feedback.get('new_PDE')==0 and feedback.get('peer_agreement_inferred')is False and
        feedback.get('new_feedback_automatically_adopted')is False,'Actual read-only public GitHub GET context required')
    bodies=[]
    for receipt in feedback.get('receipts',[]):
        if receipt.get('kind')!='comments':continue
        for row in receipt.get('evidence',[]):
            require(isinstance(row.get('body'),str)and hashlib.sha256(row['body'].encode()).hexdigest()==row.get('body_sha256'),
                'Actual feedback comment body SHA mismatch')
            bodies.append({key:row[key]for key in('id','author','updated_at','body_sha256','html_url')})
    require(bool(bodies),'Actual public comment body evidence required')
    return dict(root_selected=True,peer_endorsed=False,decision=dref,actual_feedback=fref,
        feedback_observed_utc=feedback['observed_utc'],feedback_comment_evidence=bodies,
        meaning='Root chose this bounded scientific question under existing user authorization; GET is not peer agreement')



def final_derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,output,deadline,baseline_burdens,baseline_currents,cutoffs,base_screen,checkpoint):
    seed=gene_coefficients(declared['genes'])
    try:
        coefficients,sourceproof=routing.normalize_source(seed,probe.waveform_statistics,probe.SamplingLimits)
    except ValueError as error:
        if hasattr(error,'source_waveform_evidence'):drive.write_json(output/'source-waveform-failure.json',error.source_waveform_evidence)
        raise
    familyproof=free_family_evidence(coefficients,declared['genes'])
    checkpoint('normalized_source',condition_id=declared['id'])
    spectra=post._spectra(basis,coefficients);active={f:spectra[f]for f in PAIR}
    electrical=post._electrical(basis,coefficients,geometry,deadline)
    padcurrents=base.physical_pad_currents(basis,coefficients);returnlocal=base.return_local_current_evidence(basis,coefficients)
    regression=None
    losses=waveform.layer_losses_from_matrices({f:r['loss']for f,r in basis['f'].items()},
        {f:r['source']for f,r in basis['f'].items()},coefficients,electrical)
    skin=waveform.bulk_skin_current_density(active,basis['grid'],geometry['gamma_S_m'])
    burdens=frequency.candidate_burdens(electrical,skin,losses);currents=electrical['source_current_RMS_by_output_mA']
    checkpoint('volume_projection',condition_id=declared['id'])
    weights={r:cached['arrays']['region_'+r+'_m3']for r in('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    native=scalar.evaluate_volume(active,basis['grid'],volume_meta,fundamental_frequencies_Hz=list(PAIR),region_weights=weights,
        fibonacci_count=2048,chunk_cells=256,deadline_monotonic=deadline)
    arrays={k:native['scalars'][k]for k in(*volume.METRICS,'maxTIS_direction_index')}
    arrays.update({'region_'+k+'_m3':v for k,v in native['region_weights_m3'].items()})
    regions=volume.region_weights(arrays,basis['grid'],basis['metadata'])
    np.savez_compressed(output/'volume.npz',**arrays);drive.write_json(output/'native-volume-metrics.json',native['metrics'])
    balance=carrier.carrier_metrics(active[3000],active[3030],arrays['maxTIS_direction_index'],arrays['maxTIS'],arrays['fixedTIS'])
    provenance=dict(source_run_id=cached['item']['run'].name,source_condition_id=cached['condition']['id'],
        source_candidate_id=declared['id'],input_sha256=post._digest(basis['hashes']),code_sha256=view.sha(__file__),result_sha256=post._digest(basis['validation']))
    probes=probe.evaluate_layered_probe(basis['grid'],{f:basis['f'][f]['potential']for f in PAIR},
        {f:basis['f'][f]['field']for f in PAIR},geometry,{f:coefficients[f]for f in PAIR},provenance=provenance,
        fundamental_frequencies_Hz=list(PAIR),plus_pitch_mm=5.,tip_gap_mm=5.,depths_mm=(5.,10.,15.,20.))
    require(probes['status']=='complete'and probes['numerical_checks']['all_passed']and len(probes['measurements'])==40,
        'All40 actual coherent nativephi/E probes required')
    for row in probes['measurements']:row.pop('time_plot',None)
    probes.update(actual_source_Vpp_intervals_V=sourceproof['source_Vpp_intervals_V'],actual_fundamental_Hz=list(PAIR),
        source_drive='Sine (-j) gauge two-frequency command; actual output activity is explicit in coefficient vectors')
    drive.write_json(output/'probes.json',probes)
    probecheck=waveform.probe_check(dict(id=declared['id'],probe40=probes))
    fieldcheck=waveform.field_check(dict(id=declared['id'],waveform=declared['waveform'],actual_fundamental_Hz=list(PAIR),metrics=electrical))
    modes=routing.normalization_modes(burdens,baseline_burdens,sum(currents),sum(baseline_currents),sourceproof['source_Vpp_intervals_V'])
    for mode in modes.values():
        mode['source_Vpp_definition']='Actual full source waveform max-minus-min before50ohm; analytic control or coherent bounds, not per-tone Vpp'
        mode['unitary_after_Vpp_normalization']=sourceproof['unitary_after_Vpp_normalization']
    for name,mode in modes.items():
        scale=mode['amplitude_scale'];mode['regions']=volume.summarize_regions(arrays,regions,basis['grid'],scale,cutoffs)
        mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
        mode['signed_per_output_power_evidence']=base.signed_output_powers(electrical,scale)
        mode['physical_pad_current_RMS_mA']=[v*scale for v in padcurrents['physical_pad_current_RMS_mA']]
        mode['return_net_and_local_current_evidence']=base.scaled_return_local_evidence(returnlocal,scale)
        mode['probe40_unloaded']=drive.scaled_probe_rows(probes,scale)
        require(time.monotonic()<deadline,'Per-condition120s full-metrics deadline exceeded')
    checks=screen.screen_checks(dict(normalizations=modes),base_screen)
    result=dict(schema='task1-original-cached-drive-condition-v1',status='calculated_unadopted',**declared,
        source_case_id=cached['item']['case']['id'],source_run_id=cached['item']['run'].name,
        source_commit=cached['item']['registration']['source_commit'],configuration_sha256=basis['metadata']['config_sha256'],
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
            return_topology='all_return_pads_ideal_common_GND',source_resistance_ohm=50,
            active_frequencies_by_output_Hz={str(o):[f for f in PAIR if coefficients[f][o]!=0]for o in range(2)},uncommanded_frequency_termination='0V through50ohm',
            hardware_multitone_phase_sync_power_sink_compliance='unverified; not experimental-ready'),
        actual_fundamental_Hz=list(PAIR),beat_frequency_Hz=30,active_frequencies_Hz=list(PAIR),harmonics_active=False,
        cached_sine_electrical_regression=regression,
        seed_coefficients={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in seed.items()},
        coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()},
        source_waveform=sourceproof,electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,
        physical_pad_current_evidence=padcurrents,output_power_evidence=base.signed_output_powers(electrical),
        coefficient_family_proof=familyproof,return_net_and_local_current_evidence=returnlocal,
        centre20_directional_E_TIS=dict(point_mm=[0.,0.,20.],unit='V/m',
            scope='Layered interpolated electric field at central20mm point; directional fundamental envelope widths, not ROI metrics or probe voltage',
            axes={axis:float(2*min(abs(complex(row['real_V_m'][index],row['imaginary_V_m'][index]))
                for row in electrical['centre_field_spectrum']if row['frequency_Hz']in PAIR))for index,axis in enumerate(('X','Y','Z'))}),
        native_volume_XYZ_directional_scalar_archives='not produced in this bounded scout; fixed diagonal and2074maximum volume arrays are supplied',
        native_volume_metrics=native['metrics'],normalizations=modes,raw_mode='raw_1Vpp',
        source_geometry_unchanged=True,shared_original_square_cutoffs_V_m=cutoffs,
        raw_carrier_balance_regions={region:{key:carrier.weighted(value,w,basis['grid'])for key,value in balance.items()
            if key in('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
            for region,w in regions.items()},probe_waveform_audit=probecheck,field_waveform_audit=fieldcheck,
        canonical_skin_cap_screen=dict(checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            failed_checks=[c['name']for c in checks if not c['passed']],normalization='skin_contact_only'),
        new_PDE=0,candidate_adopted=False,instrument_loading_validated=False,full_convergence_validated=False,experimentally_validated=False)
    drive.write_json(output/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],waveform=declared['waveform'],source_Vpp_intervals_V=sourceproof['source_Vpp_intervals_V'],
        canonical_screen_all_passed=all(c['passed']for c in checks),artifacts={name:dict(path=str(output/name),SHA256=view.sha(output/name))
            for name in('condition.json','probes.json','volume.npz','native-volume-metrics.json')})



def _hash_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def implementation_receipt():
    modules=(frozen,base,direction_audit,drive,volume,waveform,carrier,frequency,power,screen,core,policy,view,ranking,routing,strong)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_original_cached_drive.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for path in dict.fromkeys(paths):
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Consumed implementation/test must match committed HEAD: '+str(path))
        refs[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def validate_original_config(config,canonical_config):
    require(config==canonical_config,'Original source is exactly canonical; no physical configuration difference admitted')
    expected=[[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]]
    for i,xy in enumerate(expected):
        key='pad.'+str(i)+'.'
        require(config[key+'shape']=='rectangle'and float(config[key+'width_mm'])==15. and
            float(config[key+'height_mm'])==15. and float(config[key+'rotation_deg'])==0. and
            float(config[key+'analytic_area_mm2'])==225. and
            math.isclose(float(config[key+'represented_area_m2']),.000225,rel_tol=0,abs_tol=1e-18)and
            [float(config[key+'x_mm']),float(config[key+'y_mm'])]==xy,
            'Exact original four unrotated15x15mm squares with opposite source0/1 required')
    return dict(changed_properties=[],self_same_canonical_source=True,physical_pad_centres_mm=expected,
        same_tissue_contact_grid_source_properties=True,area_mm2_per_pad=225.,new_physics_validation_claimed=False)


def source_metadata(canonical,refs):
    item=view.load_case(SOURCE_SUMMARY);case=item['case'];circuit=item['circuit'];config=view.properties(case['config_file'])
    require(item['path']==canonical['path']==SOURCE_SUMMARY and item['case']==canonical['case']and
        item['signature']==canonical['signature'],'Exact original canonical cached basis required')
    require(case.get('source_coating_nm')==10 and case.get('source_Rs_fit_window_Hz')==500,
        'Exact nominal PBS10nm/Rs fit-window500Hz required; not500ohm')
    require(circuit.get('n_pads')==4 and circuit.get('n_outputs')==2 and circuit.get('n_return_nodes')==1 and
        circuit.get('pad_to_node')=={'0':'out0','1':'out1','2':'GND','3':'GND'}and circuit.get('source_resistance_ohm')==50 and
        circuit.get('source_peak_V')==.5 and circuit.get('source_Vpp_each')==1. and
        circuit.get('return_topology')=='all_return_pads_ideal_common_GND'and circuit.get('carrier_assignment_Hz')==list(PAIR)and
        circuit.get('inactive_source_at_other_frequencies','').replace(' ','')=='0Vthrough50ohm',
        'Exact highZ1Vpp/50ohm/twooutput/commonGND source and passive-frequency termination required')
    proof=validate_original_config(config,view.properties(canonical['case']['config_file']))
    refs.update(ranking.input_refs(item));refs.update(item['summary']['input_sha256'])
    refs[str(Path(case['mask_file']))]=case['mask_sha256']
    refs[str(SOURCE_SUMMARY.parent/'volume.npz')]=item['summary']['artifacts']['files']['volume.npz']['SHA256']
    refs[str(item['run']/'frozen-source-manifest.json')]=view.sha(item['run']/'frozen-source-manifest.json')
    for name in('selectivity_postprocess.py','selectivity_volume.py','layered_probe_analysis.py','explore_tis.py','explore_inputs.py'):
        actual=item['run']/'frozen-source/tis-java'/name;refs[str(actual)]=view.sha(actual)
    report=view.read(CONTROL_VOLUME);refs[str(CONTROL_VOLUME)]=view.sha(CONTROL_VOLUME)
    require(report.get('schema')=='task1-volume-selectivity-v1'and report.get('status')=='calculated_unadopted'and
        report.get('inputs_unchanged')is True and report.get('selected_for_adoption')==[],
        'Completed unchanged volume with original four-square control required')
    rows=[r for r in report['cases']if r['summary_path']==str(SOURCE_SUMMARY)]
    require(len(rows)==1 and report['inputs_sha256'].get(str(SOURCE_SUMMARY))==view.sha(SOURCE_SUMMARY)and
        rows[0]['condition_id']==SOURCE_ID+'-square_3h'and rows[0]['baseline_summary']==str(BASELINE_SUMMARY)and
        rows[0]['normalizations']['raw_1Vpp']['amplitude_scale']==1.,
        'Unchanged original square3h1/1 comparator retained; do not relabel as sine')
    return dict(source_case_id=SOURCE_ID,source_run_id=SOURCE_RUN,summary_path=str(SOURCE_SUMMARY),
        source_commit=item['registration']['source_commit'],configuration_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],
        native_input_sha256=item['summary']['input_sha256'],circuit=circuit,comparison_signature=item['signature'],
        config_contrast_proof=proof,cached_controls=dict(canonical_original_square=rows[0]),
        cached_control_volume=dict(path=str(CONTROL_VOLUME),SHA256=refs[str(CONTROL_VOLUME)]),
        physical_geometry=dict(shape='square',side_mm=15.,area_mm2_per_pad=225.,total_area_mm2=900.,
            physical_pad_centres_mm=proof['physical_pad_centres_mm'],placement='top-only',changed_from_canonical=[],
            edge_or_mesh_convergence_claimed=False))


def decode_existing_commands(coefficients):
    require(set(coefficients)==set(FREQUENCIES),'Four explicit actual carrier/harmonic coefficient vectors required')
    c={f:np.asarray(v,complex)for f,v in coefficients.items()}
    require(all(v.shape==(2,)and np.isfinite(v).all()for v in c.values())and
        np.array_equal(c[9000],np.zeros(2))and np.array_equal(c[9090],np.zeros(2)),
        'Finite two-output sine coefficient vectors and zero harmonics required')
    primary=complex(c[3000][0]);require(primary.real==0 and primary.imag<0,'Actual3000Hz primary must be negative imaginary')
    scale=-primary.imag
    z0=complex(c[3000][1])/primary;z1=complex(c[3030][0])/primary;rho=complex(c[3030][1])/primary
    require(abs(rho.imag)<=1e-14 and rho.real>0,'Historical3030Hz primary must have the same -j phase and positive amplitude')
    genes=[float(z0.real),float(z0.imag),float(z1.real),float(z1.imag),float(rho.real)]
    genes=[0. if v==0 else v for v in genes]
    reconstructed={3000:-1j*np.array([1,z0])*scale,3030:-1j*np.array([z1,rho.real])*scale,
        9000:np.zeros(2,complex),9090:np.zeros(2,complex)}
    require(all(np.allclose(c[f],reconstructed[f],rtol=1e-12,atol=1e-15)for f in FREQUENCIES),
        'Actual producer commands fail ONE common scale reconstruction')
    return dict(genes=genes,actual_primary_global_scale=scale,within_registered_domain=valid_gene(genes),
        coefficient_reconstruction_passed=True,coefficient_reconstruction_relative_tolerance=1e-12,
        coefficient_reconstruction_absolute_tolerance=1e-15,
        meaning='Ratios extracted from saved ACTUAL normalized commands, preserving historical outputwise normalization and tiny phase terms; no unitary-seed/rho1 substitution')


def validate_pure_seed_regression(targetstats,actualscale,savedcondition):
    require(savedcondition['id']==PURE_ID and savedcondition['source_provenance']['source_summary']==str(SOURCE_SUMMARY),
        'Exact saved pure sine source required')
    mode=savedcondition['cohorts']['cached_original_square_3000_3030_caps']['normalizations']['skin_contact_only']
    # The producer did not have a top-level normalizations field. This adapter
    # selects its explicit ORIGINAL-square cap cohort without changing old JSON.
    result=frozen.validate_seed_regression(targetstats,actualscale,dict(normalizations={'skin_contact_only':mode}))
    result.update(condition_id=PURE_ID,producer_schema=savedcondition['schema'],
        selected_cap_cohort='cached_original_square_3000_3030_caps',actual_source_primary_global_scale=1.,
        old_JSON_mutated=False,phase_gauge='same exact -j unit-primary sine')
    return result


def validate_existing_source_identity(row,source_commit,configuration_sha256,*,pure=False):
    source=row['source_provenance'] if pure else row
    run_key='run_id' if pure else 'source_run_id';case_key='case_id' if pure else 'source_case_id'
    require(source[run_key]==SOURCE_RUN and source[case_key]==SOURCE_ID and
        source['source_commit']==source_commit and source['configuration_sha256']==configuration_sha256,
        'Historical full condition must bind exact canonical source commit/configuration/run/case identity')
    if pure:require(source['source_summary']==str(SOURCE_SUMMARY),'Exact canonical pure source summary required')
    return dict(source_commit=source_commit,configuration_sha256=configuration_sha256,source_run_id=SOURCE_RUN,
        source_case_id=SOURCE_ID,passed=True)


def old_validation_aliases(refs):
    aliases=[];source=view.load_case(SOURCE_SUMMARY)
    expected_commit=source['registration']['source_commit'];expected_config=source['case']['config_sha256']
    decode=lambda values:{int(f):np.asarray(v['real'])+1j*np.asarray(v['imaginary'])for f,v in values.items()}
    for summary_path,schema,count in((OLD_STRONG_SUMMARY,'task1-coherent-drive-scout-v1',8),
        (OLD_WEAK_SUMMARY,'task1-coherent-drive-weak-scout-v1',6)):
        summary=view.read(summary_path);refs[str(summary_path)]=view.sha(summary_path)
        require(summary.get('schema')==schema and summary.get('status')=='calculated_unadopted'and
            summary.get('inputs_unchanged')is True and summary.get('new_PDE')==0 and len(summary['conditions'])==count,
            'Completed unchanged strong8/weak6 source-bound results required')
        for entry in summary['conditions']:
            ref=entry['artifacts']['condition.json'];path=Path(ref['path'])
            require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT/'docs')and
                path.suffix=='.json'and view.sha(path)==ref['SHA256'],'Old condition SHA identity differs')
            row=view.read(path);refs[str(path)]=ref['SHA256']
            require(row['source_run_id']==SOURCE_RUN and row['source_case_id']==SOURCE_ID and row['status']=='calculated_unadopted'and
                row['candidate_adopted']is False and row['actual_fundamental_Hz']==list(PAIR)and row['harmonics_active']is False,
                'Old full condition must belong to exact canonical original-square source')
            identity=validate_existing_source_identity(row,expected_commit,expected_config)
            proof=decode_existing_commands(decode(row['coefficient_vectors']))
            require(len(row['source_waveform']['column_scales'])==2 and row['source_waveform']['unitary_after_Vpp_normalization']is False,
                'Historical independent output-normalization evidence must be preserved explicitly')
            for artifact in entry['artifacts'].values():
                ap=Path(artifact['path']);require(ap.is_absolute()and ap==ap.resolve()and ap.is_relative_to(ROOT/'docs')and
                    view.sha(ap)==artifact['SHA256'],'Old full artifact SHA differs');refs[str(ap)]=artifact['SHA256']
            aliases.append(dict(**proof,condition_id=entry['id'],condition_json=ref,artifacts=entry['artifacts'],
                full2074_validation_reused=True,source_identity_check=identity,producer_source_waveform=row['source_waveform'],
                proxy2074_three_lambda_spectral_cache_available=False,
                reused_scope='Immutable saved ACTUAL normalized commands/results only. New ONE-global raw normalization is not substituted into old raw source Vpp/probes.',
                new_full_validation_excluded=proof['within_registered_domain']))
    pure=strong.control_metadata(refs)
    summary=view.read(PURE_SUMMARY);entry=next(c for c in summary['conditions']if c['id']==PURE_ID)
    row=view.read(entry['artifacts']['condition.json']['path'])
    pure_identity=validate_existing_source_identity(row,expected_commit,expected_config,pure=True)
    vectors=decode(row['coefficient_vectors'])
    vectors.update({f:np.zeros(2,complex)for f in(9000,9090)if f not in vectors})
    proof=decode_existing_commands(vectors)
    require(proof['genes']==list(SEEDS[0])and proof['actual_primary_global_scale']==1.,'Exact unit pure sine control required')
    for artifact in entry['artifacts'].values():
        ap=Path(artifact['path']);require(view.sha(ap)==artifact['SHA256'],'Old pure artifact SHA differs');refs[str(ap)]=artifact['SHA256']
    aliases.append(dict(**proof,condition_id=PURE_ID,condition_json=entry['artifacts']['condition.json'],artifacts=entry['artifacts'],
        full2074_validation_reused=True,source_identity_check=pure_identity,proxy2074_three_lambda_spectral_cache_available=False,new_full_validation_excluded=True,
        reused_scope='Exact -j unit pure-sine full result; original-square cap cohort, not fresh-sine caps. No new pure full projection.'))
    reference=next(a for a in aliases if a['condition_id']=='coherent-weak-r0p05-p090')
    require(reference['genes']==list(SEEDS[2]),'Third registered seed must preserve EXACT actual saved weak genes, including rho drift')
    return aliases


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Only original square canonical caps/cutoffs are allowed')
    plan=drive.make_preregistration(baseline_summary,output);canonical=drive.baseline_item(baseline_summary)
    selection=context_metadata(decision_path,feedback_path,plan['input_sha256'])
    source=source_metadata(canonical,plan['input_sha256']);old=old_validation_aliases(plan['input_sha256'])
    source_identity=_hash_json({k:source[k]for k in('summary_path','configuration_sha256','mask_sha256','native_input_sha256')})
    metric_identity=_hash_json(dict(proxy=PROXY_DEFINITION,canonical_summary_SHA256=view.sha(BASELINE_SUMMARY),
        source_scalar_archive_SHA256=plan['input_sha256'][str(SOURCE_SUMMARY.parent/'volume.npz')]))
    plan.update(schema=SCHEMA,conditions=[],search_contract=copy.deepcopy(SEARCH_CONTRACT),proxy_definition=copy.deepcopy(PROXY_DEFINITION),
        source_geometry=source,root_selection_context=selection,old_full_validation_aliases=old,
        source_identity=source_identity,metric_identity=metric_identity,direction_count=2074,eight_gate_definitions=screen.GATE_DEFINITIONS,
        new_PDE_conditions=0,scope='Original-square sine5gene pattern search; exact target2074 and off-target spectral proxy then up to1 novel full validation',
        resource_limits=dict(CPU_count=1,total_seconds=360,source_load_seconds=30,proxy_seconds=180,per_condition_seconds=120,
            finalization_seconds=30,maximum_proxy_evaluations=72,maximum_final_candidates=1,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,
            max_added_bytes=OUTPUT_BOUND_BYTES,cumulative_budget_seconds=policy.effective_limit(policy.load_ledger())),
        selection_rule='Up to1 completed novel gene strictly lexicographically better than the best completed seed; existing in-domain actual old14 plus pure full genes excluded; zero allowed',
        source_Vpp_policy='No waveform normalization or raw1Vpp claim in proxy: common amplitude cancels under8skin caps. Final uses ONE global actual full-wave Vpp upper normalization',
        canonical_reference='Originalsquare only8caps/cutoffs; unchanged canonical4square3h and old14 coherent plus pure-sine results preserved')
    plan['holds']+=['Proxy target uses the exact sampled2074 metric; off-target three-lambda spectral UB is ranked_only_not_full2074_validation and a worse UB is not a failure proof',
        'No promise of all72 completed evaluations, global optimum, physiological activation or unrestricted physical drive feasibility',
        'Proxy all8burdens are exact for cached native discrete model; original-square field/edge/SC/XY/bulk/contact holds remain',
        'Source2port/rho-positive phase gauge is scoped to amplitude-phase-invariant8skin objective; raw waveforms/hardware remain separately checked',
        'Only completed evaluations can enter selection; reserve120s final validation+30sfinalization before stopping proxy',
        'Existing final2074 results are not relabelled as this spectral proxy cache; evaluate each surrogate seed once and regress pure-target2074/8skin against its saved final result']
    plan.update(implementation_receipt());plan['input_sha256'].update(plan['implementation_files_sha256'])
    plan['resource_policy_refs']=policy.policy_refs(policy.load_ledger());plan['input_sha256'].update(plan['resource_policy_refs'])
    return plan


def verify_plan(path,output,expected=None):
    digest=view.sha(path);plan=view.read(path)
    require(expected is None or digest==expected,'Optimization preregistration mutated')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['new_PDE_conditions']==0 and
        plan['search_contract']==SEARCH_CONTRACT and plan['proxy_definition']==PROXY_DEFINITION and plan['conditions']==[]and
        plan['baseline_summary']==str(BASELINE_SUMMARY)and plan['output_directory']==str(output)and
        plan['source_geometry']['summary_path']==str(SOURCE_SUMMARY)and plan['direction_count']==2074 and
        plan['eight_gate_definitions']==screen.GATE_DEFINITIONS,'Exact fixed bounded original-square optimization source/ROI/caps/metric contract required')
    for name,expected_sha in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink()and
            view.sha(p)==expected_sha,'Pinned optimization source changed: '+name)
    require(view.read(BASELINE_SUMMARY)['input_sha256']==plan['native_input_sha256'],'Original native manifest changed')
    selection=plan['root_selection_context']
    require(context_metadata(Path(selection['decision']['path']),Path(selection['actual_feedback']['path']),{})==selection,'Root selection/feedback changed')
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Committed optimization implementation changed')
    return plan,digest


def free_family_evidence(coefficients,g):
    seed=gene_coefficients(g);require(set(coefficients)==set(FREQUENCIES),'All four explicit available frequency vectors required')
    scale=float(abs(coefficients[3000][0]));require(math.isfinite(scale)and scale>0,'Positive global source scale required')
    require(all(np.asarray(coefficients[f]).shape==(2,)and np.isfinite(coefficients[f]).all()and
        np.allclose(coefficients[f],seed[f]*scale,rtol=1e-12,atol=1e-15)for f in FREQUENCIES),
        'One common positive normalization must preserve exact free source coefficient ratios')
    return dict(genes=list(g),gene_names=list(GENES),global_scale=scale,independent_physical_outputs=2,
        source_peak_basis_V=.5,source_resistance_ohm=50.,common_GND_nodes=1,global_optimum_claimed=False,
        net_GND_zero_claimed=False,local_GND_J_zero_claimed=False)


def _baseline_proxy_reference(base_screen):
    regions=base_screen['normalizations']['skin_contact_only']['regions'];target=regions[volume.PRIMARY]['maxTIS']
    result=dict(target={k:target[k]for k in('mean','p10')})
    for region in('surface_0_5','primary_complement'):
        stats=regions[region]['maxTIS']
        result[region]=dict(p95=stats['p95'],**{'high_volume_'+s+'_m3':stats['fixed_baseline_threshold_volume'][volume.PRIMARY+'_'+s]['volume_m3']for s in('mean','p10')})
    return result


def evaluate_proxy(g,basis,geometry,cached,post,dirs,baseline_burdens,baseline_reference,deadline):
    if time.monotonic()>=deadline:raise ProxyDeadline('Proxy deadline before field assembly')
    coeff=gene_coefficients(g)
    active={f:np.einsum('c,cnk->nk',coeff[f],basis['f'][f]['field'])for f in PAIR}
    electrical=post._electrical(basis,coeff,geometry,deadline)
    losses=waveform.layer_losses_from_matrices({f:v['loss']for f,v in basis['f'].items()},
        {f:v['source']for f,v in basis['f'].items()},coeff,electrical)
    skin=waveform.bulk_skin_current_density(active,basis['grid'],geometry['gamma_S_m'])
    burdens=frequency.candidate_burdens(electrical,skin,losses)
    scales={key:(baseline_burdens[key]/burdens[key])**(1/degree)if burdens[key]else math.inf for key,degree in screen.CAP_DEGREES.items()}
    scale=min(scales.values());require(math.isfinite(scale)and scale>0,'Positive finite exact8skin normalization required')
    if time.monotonic()>=deadline:raise ProxyDeadline('Proxy deadline after exact8burdens')
    weights=cached['regions'];targetweights=weights[volume.PRIMARY];mask=targetweights>0
    target_values=sampled_target(active[3000][mask],active[3030][mask],dirs,chunk_cells=256,deadline=deadline)*scale
    target=volume.weighted_statistics(target_values,targetweights[mask])
    upper=spectral_upper(active[3000],active[3030],chunk_cells=4096,deadline=deadline)*scale
    direction_audit.validate_lower_bound(target_values,upper[mask]);targetupper=volume.weighted_statistics(upper[mask],targetweights[mask])
    off={}
    for region in('surface_0_5','primary_complement'):
        w=weights[region];stats=volume.weighted_statistics(upper,w)
        off[region]=dict(p95=stats['p95'],**{'high_volume_'+s+'_m3':float(w[upper>=baseline_reference['target'][s]].sum())for s in('mean','p10')})
    score=proxy_objective(target,off,baseline_reference)
    return dict(objective=list(score),status='ranked_only_not_full2074_validation',target2074=target,target_spectral_upper=targetupper,
        off_target_spectral_upper=off,skin8_amplitude_scale=scale,skin8_active_caps=[k for k,v in scales.items()if math.isclose(v,scale,rel_tol=1e-12,abs_tol=1e-15)],
        raw_unnormalized_source_burdens=burdens,normalized_skin8_burdens={k:burdens[k]*scale**d for k,d in screen.CAP_DEGREES.items()},
        proxy_whole_source_Vpp_normalized=False,raw_1Vpp_claimed=False,target_direction_count=2074,target_is_continuous_maximum=False,
        target_bound_mean_gap_V_m=targetupper['mean']-target['mean'],target_bound_p10_gap_V_m=targetupper['p10']-target['p10'])


def select_final_candidates(search,old_aliases,source_identity,metric_identity):
    seed_rows=[r for r in search['evaluations']if r['evaluation_index']in search['seed_evaluation_indices']]
    if not seed_rows:return[]
    best_seed=min(tuple(r['objective'])for r in seed_rows)
    old_keys={gene_key(row['genes'],source_identity,metric_identity)for row in old_aliases if row['within_registered_domain']}
    rows=[r for r in search['evaluations']if r['key']not in old_keys and tuple(r['objective'])<best_seed]
    return sorted(rows,key=lambda row:(tuple(row['objective']),row['key']))[:1]


def execute(plan,output,deadline,checkpoint):
    source_deadline=deadline-330;require(source_deadline>time.monotonic(),'Initial30s source admission exhausted')
    signal.setitimer(signal.ITIMER_REAL,max(.001,source_deadline-time.monotonic()))
    canonical=drive.baseline_item(BASELINE_SUMMARY);baseline=volume.load_native(canonical)
    item=view.load_case(SOURCE_SUMMARY);cached=volume.load_native(item)
    require(item['signature']==canonical['signature']and np.array_equal(cached['grid'],baseline['grid']),'Source/canonical physical grid/contact signature differs')
    post,scalar,probe=drive.import_frozen(canonical['run'],plan)
    basis=post._load_basis(item['run']/'bases'/item['case']['id'],item['case'],source_deadline)
    require(basis['hashes']==plan['source_geometry']['native_input_sha256']and np.array_equal(basis['grid'],cached['grid']),'Actual cached source native identity differs')
    geometry,volume_meta=post._geometry(basis,item['case']);dirs=frozen_direction_set(post,scalar)
    direction_receipt=dict(count=2074,dtype=str(dirs.dtype),SHA256=hashlib.sha256(dirs.tobytes(order='C')).hexdigest(),
        source='Actual SHA-pinned post._DIRECTIONS and scalar.directions(2048), byte-identical ordered matrices',continuous_maximum=False)
    pure=next(row for row in plan['old_full_validation_aliases']if row['condition_id']==PURE_ID)
    saved_pure=view.read(pure['condition_json']['path'])
    burden,currents=volume.burdens(canonical,baseline['condition'])
    cutoffs={metric:{region+'_'+stat:volume.weighted_statistics(baseline['arrays'][metric],baseline['regions'][region])[stat]
        for region in(volume.PRIMARY,volume.SLAB)for stat in('mean','p10')}for metric in volume.METRICS}
    base_screen=dict(normalizations={'skin_contact_only':dict(regions=volume.summarize_regions(baseline['arrays'],baseline['regions'],basis['grid'],1.,cutoffs))})
    reference=_baseline_proxy_reference(base_screen)
    proxy_deadline=min(time.monotonic()+180,deadline-150);require(proxy_deadline>time.monotonic(),'No proxy budget after preserving final reserve')
    signal.setitimer(signal.ITIMER_REAL,max(.001,proxy_deadline-time.monotonic()));partial=[]
    checkpoint('proxy_search',completed_evaluations=0)
    def evaluate(g):
        try:
            result=evaluate_proxy(g,basis,geometry,cached,post,dirs,burden,reference,proxy_deadline)
            if tuple(g)==SEEDS[0]:result['cached_pure_seed_regression']=validate_pure_seed_regression(result['target2074'],result['skin8_amplitude_scale'],saved_pure)
        except TimeoutError as error:
            if isinstance(error,ProxyDeadline)or time.monotonic()>=proxy_deadline:raise ProxyDeadline(str(error))from error
            raise
        completed=dict(genes=list(g),key=gene_key(g,plan['source_identity'],plan['metric_identity']),record=result)
        drive.write_json(output/f'proxy-evaluation-{len(partial):03d}.json',completed)
        partial.append(completed)
        core.write(output/'completed-proxy-evaluations.json',dict(status='partial_proxy_checkpoint',completed=partial))
        checkpoint('proxy_search',completed_evaluations=len(partial));return result
    search=bounded_pattern_search(evaluate,deadline=proxy_deadline,max_evaluations=72,
        source_identity=plan['source_identity'],metric_identity=plan['metric_identity'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    seed_regression=next((row['record']['cached_pure_seed_regression']for row in search['evaluations']
        if 'cached_pure_seed_regression'in row['record']),dict(passed=None,status='not_completed_before_proxy_deadline'))
    chosen=select_final_candidates(search,plan['old_full_validation_aliases'],plan['source_identity'],plan['metric_identity'])
    search.update(source_identity=plan['source_identity'],metric_identity=plan['metric_identity'],proxy_definition=PROXY_DEFINITION,actual_target_direction_set=direction_receipt,
        selected_for_final_validation=[dict(genes=row['genes'],key=row['key'],proxy_evaluation_index=row['evaluation_index'],objective=row['objective'])for row in chosen],
        old_full_validation_aliases=plan['old_full_validation_aliases'],baseline_proxy_reference=reference,
        remaining_resume_condition='Root may preregister a new bounded continuation after reviewing completed search; no automatic retry or unbounded worker')
    drive.write_json(output/'proxy-search.json',search);checkpoint('proxy_search_complete',completed_evaluations=search['completed_evaluations'])
    results=[];held=[]
    for row in chosen:
        if deadline-time.monotonic()<150:
            held.append(dict(genes=row['genes'],reason='Insufficient remaining120s validation+30s finalization reserve'));continue
        declared=dict(id='original-drive-'+row['key'][:12],waveform='optimized_two_tone_sine',genes=row['genes'],proxy_evaluation_index=row['evaluation_index'])
        folder=output/declared['id'];folder.mkdir();per=min(deadline-30,time.monotonic()+120)
        signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()));checkpoint('final_validation_start',condition_id=declared['id'])
        results.append(final_derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,folder,per,burden,currents,cutoffs,base_screen,checkpoint))
        checkpoint('final_validation_complete',condition_id=declared['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-original-cached-drive-v1',status='calculated_unadopted',new_PDE=0,
        actual_target_direction_set=direction_receipt,cached_pure_seed_regression=seed_regression,
        no_novel_final_reason=None if chosen else 'No completed novel genes strictly improve the best completed seed proxy objective after excluding immutable eligible old full aliases',
        proxy_search_status=search['status'],proxy_completed_evaluations=search['completed_evaluations'],proxy_search_artifact=dict(path=str(output/'proxy-search.json'),SHA256=view.sha(output/'proxy-search.json')),
        conditions=results,held_final_candidates=held,selected_final_candidates=len(chosen),completed_new_full_validations=len(results),
        cached_controls=plan['source_geometry']['cached_controls'],old_full_validation_aliases=plan['old_full_validation_aliases'],source_geometry=plan['source_geometry'],
        canonical_square_reference=dict(condition_id=baseline['condition']['id'],summary_path=str(BASELINE_SUMMARY),burdens=burden,
            source_current_RMS_by_output_mA=currents,screen_baseline=base_screen),
        actual_fundamental_Hz=list(PAIR),all_active_frequencies_Hz=list(PAIR),beat_frequency_Hz=30,search_contract=SEARCH_CONTRACT,proxy_definition=PROXY_DEFINITION,
        candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,global_optimum_claimed=False,
        holds=plan['holds'],root_selection_context=plan['root_selection_context'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--baseline-summary',type=Path,default=BASELINE_SUMMARY)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path)
    args=parser.parse_args();output=args.output.resolve()
    require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new docs output directory required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path);cap=60 if args.prepare else 360
        require(policy.remaining_seconds(ledger)>=cap,'Finite admission budget missing')
        require(shutil.disk_usage(output.parent).free>=2*GIB+OUTPUT_BOUND_BYTES,'Preserve2GiB reserve plus32MiB bounded artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();deadline=started+cap
        status='failed_preserved';failure=None;state={};counter=0;mutex=threading.RLock();stop=threading.Event();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS cap exceeded')
            require(shutil.disk_usage(output.parent).free>=2*GIB,'Existing2GiB disk reserve exhausted')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=OUTPUT_BOUND_BYTES,'New artifacts exceed32MiB cap')
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                guard();counter+=1;state.update(phase=phase,status=status if phase=='complete'else'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                    updated_utc=core.now(),elapsed_seconds=time.monotonic()-started,**extra)
                drive.write_json(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as error:
                    state['resource_guard_failure']=str(error);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(signum,frame):
            if signum==signal.SIGALRM and state.get('phase')=='proxy_search':raise ProxyDeadline('proxy_wall_deadline')
            raise TimeoutError('Controlled360s/30s-source/120s-condition stop signal '+str(signum))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for signum in previous:signal.signal(signum,interrupted)
        signal.setitimer(signal.ITIMER_REAL,cap if args.prepare else 30)
        try:
            if args.prepare:
                require(not args.prepare.exists()and not args.prepare.with_name(args.prepare.name+'.failure.json').exists()and
                    not args.prepare.resolve().is_relative_to(output),
                    'New preregistration must remain outside the untouched actual output directory')
                plan=make_preregistration(args.baseline_summary,output,decision_path=args.decision,feedback_path=args.feedback);args.prepare.parent.mkdir(parents=True,exist_ok=True)
                drive.write_json(args.prepare,plan);status='preregistered_not_executed'
            else:
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_plan')
                plan,plan_sha=verify_plan(args.preregistration.resolve(),output)
                result=execute(plan,output,deadline,checkpoint)
                verify_plan(args.preregistration.resolve(),output,expected=plan_sha);guard()
                result.update(implementation_receipt(),preregistration=dict(path=str(args.preregistration.resolve()),SHA256=plan_sha),
                    input_sha256=plan['input_sha256'],inputs_unchanged=True,resources=dict(CPU_count=1,max_batch_seconds=360,max_proxy_seconds=180,max_condition_seconds=120,
                        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-started,
                        cumulative_budget_limit_seconds=policy.effective_limit(ledger),new_PDE=0))
                drive.write_json(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            if output.exists():drive.write_json(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),
                condition_id=state.get('condition_id'),new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False,
                resume_condition='Root reviews preserved completed checkpoints and remaining existing budget before a new preregistered bounded run'))
            elif args.prepare:
                failure_path=args.prepare.with_name(args.prepare.name+'.failure.json')
                if not failure_path.exists():
                    failure_path.parent.mkdir(parents=True,exist_ok=True)
                    drive.write_json(failure_path,dict(status=status,error=failure,new_PDE=0,partial_artifacts_preserved=True,automatic_retry=False))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='original_cached_drive_prepare'if args.prepare else'original_cached_drive',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
