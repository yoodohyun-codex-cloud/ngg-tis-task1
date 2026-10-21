"""Finite deterministic bounded two-port drive search on one cached geometry.

Proxy ranking uses the exact frozen2074 target-direction metric and a guarded
three-lambda spectral off-target upper bound. Full-volume2074 validation remains separate.
Only up to four novel improving genes receive actual full2074/40phi validation.
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
import task1_direction_bounds_audit as direction_audit
ROOT=base.ROOT
GIB=base.GIB
FREQUENCIES=base.FREQUENCIES
PAIR=base.PAIR
SOURCE_RUN=base.SOURCE_RUN
SOURCE_ID=base.SOURCE_ID
SOURCE_SUMMARY=base.SOURCE_SUMMARY
BASELINE_SUMMARY=base.BASELINE_SUMMARY
CONTROL_VOLUME=base.CONTROL_VOLUME
SCHEMA='task1-rounded-drive-optimization-preregistration-v1'
GENES=('z0_real','z0_imag','z1_real','z1_imag','rho')
BOUNDS=((-.075,.075),)*4+((.95,1.05),)
STEPS=(.02,.01,.005)
SEEDS=((0.,0.,0.,0.,1.),(.01,0.,.01,0.,1.),(0.,.01,0.,.01,1.),(0.,-.01,0.,-.01,1.))
SEARCH_CONTRACT=dict(gene_names=list(GENES),bounds=[list(v)for v in BOUNDS],steps=list(STEPS),seeds=[list(v)for v in SEEDS],
    maximum_proxy_evaluations=124,proxy_seconds=300,maximum_final_candidates=4,total_seconds=600)
PROXY_DEFINITION=dict(target='Exact maximum over the actual frozen2074 sampled real directions on full positive-weight primary ROI; volume-weighted mean/P10',
    off_target='Minimum of guarded largest eigenvalues at lambda0,0.5,1 on Qa/Qb; continuous-direction upper bound used only for ranking',
    lambdas=[0.,.5,1.],skin='Exact full native8 skin/contact burdens; source power and1Vpp ceiling excluded',
    gates='Original square eight screens/cutoffs; target sampled2074 exact, off-target spectral UB remains surrogate ranking only',
    whole_source_Vpp_normalized=False,raw_1Vpp_claimed=False,ranked_only_not_full2074_validation=True,
    target2074_is_continuous_maximum=False)
OLD_SUMMARY=ROOT/'docs/cloud-rounded-drive-20261021T202000Z/summary.json'
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


class ProxyDeadline(TimeoutError):pass


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


def _fields(a,b):
    a,b=np.asarray(a,complex),np.asarray(b,complex)
    require(a.ndim==b.ndim==2 and a.shape==b.shape and a.shape[1]==3 and len(a)>0 and
        np.isfinite(a).all()and np.isfinite(b).all(),'Finite equal Nx3 complex carrier fields required')
    return a,b


def spectral_upper(e0,e1,chunk_cells=256,deadline=None):
    """Three fixed spectral dual bounds; no old nine-lambda audit is changed."""
    a,b=_fields(e0,e1);require(type(chunk_cells)is int and 1<=chunk_cells<=4096,'Bounded chunk size1..4096 required')
    result=np.empty(len(a),float);eps=np.finfo(float).eps
    for start in range(0,len(a),chunk_cells):
        if deadline is not None and time.monotonic()>=deadline:raise ProxyDeadline('Proxy spectral-bound deadline')
        aa=a[start:start+chunk_cells];bb=b[start:start+chunk_cells]
        qa=aa.real[:,:,None]*aa.real[:,None,:]+aa.imag[:,:,None]*aa.imag[:,None,:]
        qb=bb.real[:,:,None]*bb.real[:,None,:]+bb.imag[:,:,None]*bb.imag[:,None,:]
        norm=np.maximum(np.linalg.norm(qa,axis=(1,2)),np.linalg.norm(qb,axis=(1,2)))
        require(np.isfinite(norm).all(),'Proxy PSD outer products overflowed')
        best=np.full(len(aa),np.inf)
        for lam in(0.,.5,1.):
            matrix=lam*qa+(1-lam)*qb
            largest=np.linalg.eigvalsh((matrix+matrix.transpose(0,2,1))*.5)[:,-1]
            best=np.minimum(best,largest)
        guard=64*eps*norm+1e-24
        require(np.isfinite(best).all()and np.all(best>=-guard),'Nonfinite/materially negative largest PSD eigenvalue')
        bound=np.nextafter(2*np.sqrt(np.maximum(0.,best+guard)),np.inf)
        bound[np.all(aa==0,axis=1)|np.all(bb==0,axis=1)]=0.
        result[start:start+chunk_cells]=bound
    require(np.isfinite(result).all(),'Proxy spectral upper bound overflow')
    return result


def _directions(dirs):
    require(not np.iscomplexobj(dirs),'Target directions must be real')
    dirs=np.asarray(dirs,float)
    require(dirs.shape==(2074,3)and np.isfinite(dirs).all()and
        np.allclose(np.linalg.norm(dirs,axis=1),1.,rtol=0,atol=1e-12),'Actual2074 finite real-unit target directions required')
    return dirs


def frozen_direction_set(post,scalar):
    """No replacement direction generator: require both SHA-pinned frozen modules to agree byte-for-byte."""
    raw_a=np.asarray(post._DIRECTIONS);raw_b=np.asarray(scalar.directions(2048))
    require(raw_a.dtype==raw_b.dtype==np.dtype('float64'),'Frozen2074 matrix dtype must remain float64')
    a=_directions(raw_a);b=_directions(raw_b)
    require(a.dtype==b.dtype==np.dtype('float64')and a.tobytes(order='C')==b.tobytes(order='C'),
        'Frozen point and volume2074 direction order/bytes differ')
    out=a.copy();out.flags.writeable=False;return out


def sampled_target(e0,e1,dirs,chunk_cells=256,deadline=None):
    """Same2074 sampled metric and chunk algebra as frozen selectivity_volume.evaluate_volume."""
    a,b=_fields(e0,e1);dirs=_directions(dirs)
    require(type(chunk_cells)is int and 1<=chunk_cells<=4096,'Bounded target chunk size1..4096 required')
    result=np.empty(len(a),float)
    for start in range(0,len(a),chunk_cells):
        if deadline is not None and time.monotonic()>=deadline:raise ProxyDeadline('Proxy target2074 deadline')
        pa=abs(a[start:start+chunk_cells]@dirs.T);pb=abs(b[start:start+chunk_cells]@dirs.T)
        np.minimum(pa,pb,out=pa);result[start:start+chunk_cells]=2*np.max(pa,axis=1)
    require(np.isfinite(result).all(),'Target sampled2074 projection overflow');return result


def validate_seed_regression(targetstats,actualscale,savedcondition):
    mode=savedcondition['normalizations']['skin_contact_only'];expected=mode['regions'][volume.PRIMARY]['maxTIS']
    require(type(actualscale)in(int,float)and math.isfinite(actualscale)and actualscale>0 and
        math.isclose(actualscale,mode['amplitude_scale'],rel_tol=1e-10,abs_tol=1e-14),
        'Pure seed exact8skin amplitude scale must match saved completed rounded sine control')
    errors={}
    for name in('mean','p10'):
        v,b=targetstats[name],expected[name]
        require(type(v)in(int,float)and type(b)in(int,float)and math.isfinite(v)and math.isfinite(b)and v>=0 and b>=0 and
            math.isclose(v,b,rel_tol=1e-10,abs_tol=1e-12),'Pure seed sampled2074 primary '+name+' differs from completed rounded sine')
        errors[name]=abs(v-b)
    return dict(passed=True,metric='sampled2074',matching_skin8_amplitude_scale=actualscale,absolute_errors_V_m=errors,
        relative_tolerance=1e-10,absolute_tolerance_V_m=1e-12,scope='Full primary ROI with identical frozen2074 directions/weights; not a continuous maximum or convergence claim')


def _proxy_gate_values(targetstats,offstats):
    values={f'primary_maxTIS_{stat}':float(targetstats[stat])for stat in('mean','p10')}
    for region in('surface_0_5','primary_complement'):
        values[region+'_maxTIS_p95']=float(offstats[region]['p95'])
        for stat in('mean','p10'):values[region+'_high_volume_at_'+volume.PRIMARY+'_'+stat]=float(offstats[region]['high_volume_'+stat+'_m3'])
    return values


def proxy_objective(targetstats,offstats,baseline):
    actual=_proxy_gate_values(targetstats,offstats);reference=_proxy_gate_values(baseline['target'],baseline)
    violations=[]
    for definition in screen.GATE_DEFINITIONS:
        name=definition['name'];v,b=actual[name],reference[name]
        require(math.isfinite(v)and v>=0 and math.isfinite(b)and b>0,'Finite nonnegative proxy and positive original baseline gates required')
        delta=(b-v)if definition['required_direction']=='greater'else(v-b)
        violations.append(max(0.,(delta-screen.tolerance(b,definition['unit']))/b))
    return(max(violations),sum(violations),-float(targetstats['p10']))


def bounded_pattern_search(evaluator,*,deadline,max_evaluations=124,clock=time.monotonic,source_identity='synthetic',metric_identity='synthetic'):
    require(type(max_evaluations)is int and 1<=max_evaluations<=128,'Finite evaluation cap1..128 required')
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
        global_optimum_claimed=False,all124_evaluations_promised=False)


def context_metadata(decision_path,feedback_path,pins):
    require(decision_path is not None and feedback_path is not None,'Explicit root decision and actual feedback GET context required')
    def bound(path):
        path=Path(path)
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and
            not path.is_symlink()and path.stat().st_size<=25*1024**2,'Canonical local public JSON context required')
        digest=view.sha(path);value=view.read(path);require(view.sha(path)==digest,'Context changed while reading')
        pins[str(path)]=digest;return value,dict(path=str(path),SHA256=digest)
    decision,dref=bound(decision_path);feedback,fref=bound(feedback_path)
    require(decision.get('schema')=='task1-rounded-drive-optimization-root-decision-v1'and decision.get('status')=='selected_not_executed'and
        decision.get('root_selected')is True and decision.get('peer_endorsed')is False and
        decision.get('new_PDE')==0 and decision.get('source_run_id')==SOURCE_RUN and decision.get('source_case_id')==SOURCE_ID and
        decision.get('search_contract')==SEARCH_CONTRACT,'Exact root-selected bounded five-gene search required; peer endorsement must not be inferred')
    refs=decision.get('input_sha256');require(isinstance(refs,dict)and bool(refs),'Root decision must bind completed scientific evidence')
    require(all(refs.get(str(p))==view.sha(p)for p in(OLD_SUMMARY,base.CONTROL_VOLUME,base.CONTROL_SCREEN)),
        'Root decision must bind actual completed rounded signed6/control volume/screen')
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
        source_drive='Exclusive sine control'if declared['waveform']=='sine'else'Both actual fundamentals coherent on both outputs')
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
        require(time.monotonic()<deadline,'Per-condition60s full-metrics deadline exceeded')
    checks=screen.screen_checks(dict(normalizations=modes),base_screen)
    result=dict(schema='task1-rounded-drive-optimization-condition-v1',status='calculated_unadopted',**declared,
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
    modules=(base,direction_audit,drive,volume,waveform,carrier,frequency,power,screen,core,policy,view,ranking,routing,strong)
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_rounded_drive_optimization.py',*[Path(m.__file__).resolve()for m in modules]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for path in dict.fromkeys(paths):
        require(path.read_bytes()==subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Consumed implementation/test must match committed HEAD: '+str(path))
        refs[str(path)]=view.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def old_validation_aliases(refs):
    summary=view.read(OLD_SUMMARY);refs[str(OLD_SUMMARY)]=view.sha(OLD_SUMMARY)
    require(summary.get('schema')=='task1-rounded-drive-scout-v1'and summary.get('status')=='calculated_unadopted'and
        summary.get('inputs_unchanged')is True and summary.get('new_PDE')==0 and
        not any(c.get('canonical_screen_all_passed')is True for c in summary['conditions'])and
        [c['id']for c in summary['conditions']]==[c['id']for c in base.CONDITIONS],'Completed unchanged six-condition source-bound validation required')
    aliases=[]
    for declared,entry in zip(base.CONDITIONS,summary['conditions']):
        gain=declared.get('cross_gain',0.);gene=[gain,0.,gain,0.,1.]if gain else list(SEEDS[0])
        ref=entry['artifacts']['condition.json'];path=Path(ref['path'])
        require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT/'docs')and path.suffix=='.json'and view.sha(path)==ref['SHA256'],
            'Existing exact validation JSON identity differs')
        row=view.read(path);refs[str(path)]=ref['SHA256']
        require(row['source_run_id']==SOURCE_RUN and row['source_case_id']==SOURCE_ID and row['status']=='calculated_unadopted',
            'Existing validation must belong to this fixed rounded geometry')
        coeff={int(f):np.asarray(v['real'])+1j*np.asarray(v['imaginary'])for f,v in row['coefficient_vectors'].items()}
        free_family_evidence(coeff,gene)
        aliases.append(dict(genes=gene,condition_id=declared['id'],condition_json=ref,
            full2074_validation_reused=True,proxy2074_three_lambda_spectral_cache_available=False,
            meaning='Existing final result alias only; the new off-target spectral surrogate still needs its own one-time seed evaluation'))
    return aliases


def make_preregistration(baseline_summary,output,*,decision_path,feedback_path):
    require(Path(baseline_summary).resolve()==BASELINE_SUMMARY,'Only original square canonical caps/cutoffs are allowed')
    plan=drive.make_preregistration(baseline_summary,output);canonical=drive.baseline_item(baseline_summary)
    selection=context_metadata(decision_path,feedback_path,plan['input_sha256'])
    source=base.source_metadata(canonical,plan['input_sha256']);old=old_validation_aliases(plan['input_sha256'])
    source_identity=_hash_json({k:source[k]for k in('summary_path','configuration_sha256','mask_sha256','native_input_sha256')})
    metric_identity=_hash_json(dict(proxy=PROXY_DEFINITION,canonical_summary_SHA256=view.sha(BASELINE_SUMMARY),
        source_scalar_archive_SHA256=plan['input_sha256'][str(SOURCE_SUMMARY.parent/'volume.npz')]))
    plan.update(schema=SCHEMA,conditions=[],search_contract=copy.deepcopy(SEARCH_CONTRACT),proxy_definition=copy.deepcopy(PROXY_DEFINITION),
        source_geometry=source,root_selection_context=selection,old_full_validation_aliases=old,
        source_identity=source_identity,metric_identity=metric_identity,direction_count=2074,eight_gate_definitions=screen.GATE_DEFINITIONS,
        new_PDE_conditions=0,scope='Fixed rounded geometry narrow5gene pattern search; exact target2074 and off-target spectral proxy then up to4 novel full validations',
        resource_limits=dict(CPU_count=1,total_seconds=600,source_load_seconds=30,proxy_seconds=300,per_condition_seconds=60,
            finalization_seconds=30,maximum_proxy_evaluations=124,maximum_final_candidates=4,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,
            max_added_bytes=2*GIB,cumulative_budget_seconds=policy.effective_limit(policy.load_ledger())),
        selection_rule='Up to4 completed novel genes strictly lexicographically better than the best completed seed; exact old six final genes alias only; zero allowed',
        source_Vpp_policy='No waveform normalization or raw1Vpp claim in proxy: common amplitude cancels under8skin caps. Final uses ONE global actual full-wave Vpp upper normalization',
        canonical_reference='Originalsquare only8caps/cutoffs; original and rounded square controls and existing6final signed drives preserved')
    plan['holds']+=['Proxy target uses the exact sampled2074 metric; off-target three-lambda spectral UB is ranked_only_not_full2074_validation and a worse UB is not a failure proof',
        'No promise of all124 completed evaluations, global optimum, physiological activation or unrestricted physical drive feasibility',
        'Proxy all8burdens are exact for cached native discrete model; rounded full-face staircase/field/edge/SC/XY/bulk/contact holds remain',
        'Source2port/rho-positive phase gauge is scoped to amplitude-phase-invariant8skin objective; raw waveforms/hardware remain separately checked',
        'Only completed evaluations can enter selection; reserve240s final validation+30sfinalization before stopping proxy',
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
        plan['eight_gate_definitions']==screen.GATE_DEFINITIONS,'Exact fixed bounded optimization source/ROI/caps/metric contract required')
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
    old_keys={gene_key(row['genes'],source_identity,metric_identity)for row in old_aliases}
    rows=[r for r in search['evaluations']if r['key']not in old_keys and tuple(r['objective'])<best_seed]
    return sorted(rows,key=lambda row:(tuple(row['objective']),row['key']))[:4]


def execute(plan,output,deadline,checkpoint):
    source_deadline=deadline-570;require(source_deadline>time.monotonic(),'Initial30s source admission exhausted')
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
    pure=next(row for row in plan['old_full_validation_aliases']if row['condition_id']==base.CONDITIONS[0]['id'])
    saved_pure=view.read(pure['condition_json']['path'])
    burden,currents=volume.burdens(canonical,baseline['condition'])
    cutoffs={metric:{region+'_'+stat:volume.weighted_statistics(baseline['arrays'][metric],baseline['regions'][region])[stat]
        for region in(volume.PRIMARY,volume.SLAB)for stat in('mean','p10')}for metric in volume.METRICS}
    base_screen=dict(normalizations={'skin_contact_only':dict(regions=volume.summarize_regions(baseline['arrays'],baseline['regions'],basis['grid'],1.,cutoffs))})
    reference=_baseline_proxy_reference(base_screen)
    proxy_deadline=min(time.monotonic()+300,deadline-270);require(proxy_deadline>time.monotonic(),'No proxy budget after preserving final reserve')
    signal.setitimer(signal.ITIMER_REAL,max(.001,proxy_deadline-time.monotonic()));partial=[]
    checkpoint('proxy_search',completed_evaluations=0)
    def evaluate(g):
        try:
            result=evaluate_proxy(g,basis,geometry,cached,post,dirs,burden,reference,proxy_deadline)
            if tuple(g)==SEEDS[0]:result['cached_pure_seed_regression']=validate_seed_regression(result['target2074'],result['skin8_amplitude_scale'],saved_pure)
        except TimeoutError as error:
            if isinstance(error,ProxyDeadline)or time.monotonic()>=proxy_deadline:raise ProxyDeadline(str(error))from error
            raise
        completed=dict(genes=list(g),key=gene_key(g,plan['source_identity'],plan['metric_identity']),record=result)
        drive.write_json(output/f'proxy-evaluation-{len(partial):03d}.json',completed)
        partial.append(completed)
        core.write(output/'completed-proxy-evaluations.json',dict(status='partial_proxy_checkpoint',completed=partial))
        checkpoint('proxy_search',completed_evaluations=len(partial));return result
    search=bounded_pattern_search(evaluate,deadline=proxy_deadline,max_evaluations=124,
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
        if deadline-time.monotonic()<90:
            held.append(dict(genes=row['genes'],reason='Insufficient remaining60s validation+30s finalization reserve'));continue
        declared=dict(id='rounded-opt-'+row['key'][:12],waveform='optimized_two_tone_sine',genes=row['genes'],proxy_evaluation_index=row['evaluation_index'])
        folder=output/declared['id'];folder.mkdir();per=min(deadline-30,time.monotonic()+60)
        signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()));checkpoint('final_validation_start',condition_id=declared['id'])
        results.append(final_derive(basis,geometry,volume_meta,cached,declared,post,scalar,probe,folder,per,burden,currents,cutoffs,base_screen,checkpoint))
        checkpoint('final_validation_complete',condition_id=declared['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-rounded-drive-optimization-v1',status='calculated_unadopted',new_PDE=0,
        actual_target_direction_set=direction_receipt,cached_pure_seed_regression=seed_regression,
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
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path);cap=60 if args.prepare else 600
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
                drive.write_json(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as error:
                    state['resource_guard_failure']=str(error);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(signum,frame):
            if signum==signal.SIGALRM and state.get('phase')=='proxy_search':raise ProxyDeadline('proxy_wall_deadline')
            raise TimeoutError('Controlled600s/30s-source/60s-condition stop signal '+str(signum))
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
                    input_sha256=plan['input_sha256'],inputs_unchanged=True,resources=dict(CPU_count=1,max_batch_seconds=600,max_proxy_seconds=300,max_condition_seconds=60,
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
            ledger['runs'].append(dict(run_id=output.name,stage='rounded_drive_optimization_prepare'if args.prepare else'rounded_drive_optimization',
                seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
