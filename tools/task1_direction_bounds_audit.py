#!/usr/bin/env python3
"""Finite native XYZ/continuous-direction bounds; preserve every old2074 screen.

Reads selected fundamental E, native grid and saved scalar weights only. No PDE,
phi, harmonic E, waveform/probe recalculation, candidate adoption or safety claim.
"""
from __future__ import annotations
import argparse
import copy
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import shutil
import subprocess
import threading
import time
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_name]='1'
import numpy as np
import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_return_position_volume_registration as native
import task1_adjacent_source_volume_registration as probes
import task1_volume_selectivity as volume
import task1_candidate_screen as screen

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
LAMBDAS=tuple(i/8 for i in range(9))
PAIR=(3000,3030)
BASE_RUN='cloud-mesh-c1-20261019T190000Z';BASE_ID='baseline-square15-xy80'
SHELL_RUN='cloud-perimeter-shell-20261021T185000Z';SHELL_ID='perimeter-shell225-notch-xy80'
SOURCE_SUMMARY=ROOT/'docs/cloud-perimeter-antiphase-20261021T190500Z/summary.json'
CONTROL_VOLUME=ROOT/'docs/cloud-perimeter-shell-context-20261021T185000Z/volume.json'
SCHEMA='task1-direction-bounds-preregistration-v1'
FP_FACTOR=64
FP_EIGEN_ABSOLUTE=1e-24
METRICS=('X_TIS','Y_TIS','Z_TIS','old2074_maxTIS_LB','continuous_direction_UB')
require=native.require


def _deadline(deadline):
    require(deadline is None or time.monotonic()<deadline,'Finite direction-bounds deadline exhausted')


def field_bounds(e0,e1,*,chunk_cells=256,deadline=None):
    a,b=np.asarray(e0),np.asarray(e1)
    require(a.ndim==2 and a.shape==b.shape and a.shape[1]==3 and 0<len(a)<=800000 and
        np.iscomplexobj(a)and np.iscomplexobj(b)and np.isfinite(a).all()and np.isfinite(b).all(),
        'Finite complete complex peak E pairs with shape(N,3) required')
    require(type(chunk_cells)is int and 1<=chunk_cells<=256,'Bounded cell chunks1..256 required')
    result={name:2*np.minimum(abs(a[:,i]),abs(b[:,i]))for i,name in enumerate(('X_TIS','Y_TIS','Z_TIS'))}
    raw=np.empty(len(a));guarded=np.empty(len(a))
    for start in range(0,len(a),chunk_cells):
        _deadline(deadline);stop=min(start+chunk_cells,len(a));x,y=a[start:stop],b[start:stop]
        aa=np.einsum('ni,nj->nij',x.real,x.real)+np.einsum('ni,nj->nij',x.imag,x.imag)
        bb=np.einsum('ni,nj->nij',y.real,y.real)+np.einsum('ni,nj->nij',y.imag,y.imag)
        norm=np.maximum(np.linalg.norm(aa,axis=(1,2)),np.linalg.norm(bb,axis=(1,2)))
        require(np.isfinite(norm).all(),'PSD outer products overflowed')
        smallest=np.full(stop-start,np.inf)
        for weight in LAMBDAS:
            matrix=weight*aa+(1-weight)*bb
            eigen=np.linalg.eigvalsh((matrix+matrix.transpose(0,2,1))*.5)[:,-1]
            smallest=np.minimum(smallest,eigen)
        error=FP_FACTOR*np.finfo(float).eps*norm+FP_EIGEN_ABSOLUTE
        require(np.isfinite(smallest).all()and np.all(smallest>=-error),'Nonfinite/materially negative PSD largest eigenvalue')
        raw[start:stop]=2*np.sqrt(np.maximum(smallest,0.))
        guarded[start:stop]=np.nextafter(2*np.sqrt(np.maximum(smallest+error,0.)),np.inf)
        zero=np.all(x==0,axis=1)|np.all(y==0,axis=1)
        raw[start:stop][zero]=0.;guarded[start:stop][zero]=0.
    result.update(continuous_direction_UB_raw_V_m=raw,continuous_direction_UB_V_m=guarded)
    return result


def validate_lower_bound(lb,ub):
    low,high=np.asarray(lb,float),np.asarray(ub,float)
    require(low.ndim==1 and low.shape==high.shape and len(low)>0 and np.isfinite(low).all()and
        np.isfinite(high).all()and np.all(low>=0)and np.all(high>=0),'Finite nonnegative common-shape LB/UB required')
    defect=low-high;tol=1e-12+1e-10*np.maximum(low,high)
    require(np.all(defect<=tol),'Saved2074 lower bound exceeds guarded continuous-direction upper bound')
    return dict(passed=True,maximum_LB_minus_UB_V_m=float(np.max(defect)),relative_tolerance=1e-10,absolute_tolerance_V_m=1e-12,
        numeric_scope='Outward floating diagnostic; not formal IEEE, solver-error or continuum certification')


def weighted_volume_interval(lb,ub,weights,cutoff,scale=1.):
    low,high,w=np.asarray(lb,float),np.asarray(ub,float),np.asarray(weights,float)
    validate_lower_bound(low,high)
    # Inclusive thresholds are discontinuous even for a tolerated rounding
    # inversion. Enlarge only the upper side; never change the saved lower.
    high=np.maximum(high,low)
    require(w.shape==low.shape and np.isfinite(w).all()and np.all(w>=0)and w.sum()>0 and
        type(cutoff)in(int,float)and math.isfinite(cutoff)and cutoff>=0 and
        type(scale)in(int,float)and math.isfinite(scale)and scale>0,'Positive fixed native weights/scale and finite cutoff required')
    return dict(lower_volume_m3=float(w[low*scale>=cutoff].sum()),upper_volume_m3=float(w[high*scale>=cutoff].sum()),
        cutoff_V_m=cutoff,amplitude_scale=scale,comparison='>=',cutoff_scope='Frozen original2074 raw maxTIS baseline cutoff; not redefined from this UB',
        interpretation='Represented high-modulation volume interval; no biological activation or safety threshold',
        tolerated_roundoff_inversion_handling='Upper side enlarged to savedLB after fixed consistency gate; lower unchanged')


def robust_failure(candidate_lower,candidate_upper,baseline_lower,baseline_upper,*,direction,unit='V/m'):
    vals=(candidate_lower,candidate_upper,baseline_lower,baseline_upper)
    require(all(type(v)in(int,float)and math.isfinite(v)and v>=0 for v in vals)and
        candidate_lower<=candidate_upper and baseline_lower<=baseline_upper and direction in('greater','less'),
        'Ordered finite nonnegative scalar intervals and fixed gate direction required')
    b=baseline_lower if direction=='greater'else baseline_upper
    eps=screen.tolerance(b,unit);outward=(1e-18 if unit=='m3'else 1e-12)+1e-10*max(vals)
    failed=candidate_upper+outward<baseline_lower-eps if direction=='greater'else candidate_lower-outward>baseline_upper+eps
    return dict(status='conditional_direction_robust_failure'if failed else'inconclusive',required_direction=direction,
        candidate_interval=[candidate_lower,candidate_upper],baseline_interval=[baseline_lower,baseline_upper],unit=unit,
        frozen_gate_arithmetic_tolerance=eps,extra_outward_comparison_guard=outward,
        meaning='Necessary old-gate comparison under the stored discrete field model; no old screen or adoption status changed')


def _local(path):
    return native._regular(Path(path),ROOT)


def _json(path,refs,expected=None):
    p=_local(path);require(p.suffix=='.json'and p.stat().st_size<=25*1024**2,'Only bounded local JSON context required')
    digest=native._pin(p,refs,ROOT,expected);obj=native.read(p)
    require(native.sha(p)==digest,'Consumed JSON changed while reading');return obj


def _implementation():
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_direction_bounds_audit.py',
        *[Path(m.__file__).resolve()for m in(core,policy,native,probes,volume,screen)]]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();refs={}
    for p in dict.fromkeys(paths):
        require(p.read_bytes()==subprocess.check_output(['git','show',commit+':'+p.relative_to(ROOT).as_posix()],cwd=ROOT),
            'Commit implementation/helpers/tests before registration: '+str(p));refs[str(p)]=native.sha(p)
    return dict(implementation_git_commit=commit,implementation_files_sha256=refs)


def _selected_files(item,refs):
    expected=item['native_expected_input_sha256'];out={}
    for key,names in [('grid',('grid.csv','grid.csv.gz')),('metadata',('mesh-metadata.json',)),
        ('3000',('field-3000.bin','field-3000.bin.gz')),('3030',('field-3030.bin','field-3030.bin.gz'))]:
        found=[Path(p)for p in expected if Path(p).name in names];require(len(found)==1,'Exactly one selected native file required: '+key)
        p=_local(found[0]);refs[str(p)]=expected[str(p)];out[key]=dict(path=str(p),SHA256=expected[str(p)])
        require(p.parent==Path(item['basis_folder']),'Selected native arrays must belong to the registered physical basis')
    out['volume']=dict(path=item['volume_npz'],SHA256=item['volume_npz_sha256'])
    return out


def source_bundle(refs):
    source=_json(SOURCE_SUMMARY,refs)
    require(source.get('schema')=='task1-perimeter-antiphase-scout-v1'and source.get('status')=='calculated_unadopted'and
        source.get('inputs_unchanged')is True and source.get('new_PDE')==0 and len(source['conditions'])==6,'Exact completed unchanged antiphase6 evidence required')
    control=_json(CONTROL_VOLUME,refs,source['cached_control_volume']['SHA256'])
    require(source['cached_control_volume']['path']==str(CONTROL_VOLUME)and control['status']=='calculated_unadopted'and control['inputs_unchanged']is True,
        'Source-bound unchanged canonical/perimeter square controls required')
    cases=[];bases={}
    for run,ident in((BASE_RUN,BASE_ID),(SHELL_RUN,SHELL_ID)):
        item,pre=native._case(ROOT,run,ident,refs);probes._validate_probe40(item,refs,ROOT)
        require(pre.get('gates')==core.GATES,'Original five native numerical gate limits must remain fixed')
        case=next(c for c in pre['cases']if c['id']==ident);meta=native.read(Path(item['summary']))['mesh_metadata']
        require(meta.get('source_peak_V')==.5 and meta.get('source_resistance_ohm')==50 and
            meta.get('phasor_convention')=='peak,+jomega_t'and meta.get('field_reconstruction')=='half_face_flux; top contact term averaged over full cell face h^2',
            'Frozen peak-field reconstruction/0.5V/50ohm basis required')
        if ident==SHELL_ID:require(case.get('geometry_kind')=='fixed_native_face_union'and case.get('native_full_face_contact')is True,'Exact physical shell source required')
        base=dict(case=item,files=_selected_files(item,refs),metadata=meta,physical_geometry=case.get('design'),physical_geometry_kind=case.get('geometry_kind','four_square'))
        bases[ident]=base
        rows=[r for r in control['cases']if r['summary_path']==item['summary']]
        require(len(rows)==1 and control['inputs_sha256'].get(item['summary'])==item['summary_sha256'],'Control summary binding mismatch')
        row=rows[0];a1=3/(2*math.sqrt(2));coeff={3000:dict(real=[0.,0.],imaginary=[-a1,0.]),3030:dict(real=[0.,0.],imaginary=[0.,-a1])}
        cases.append(dict(id=ident+'-square_3h',basis_id=ident,coefficients=coeff,volume_file=base['files']['volume'],
            normalizations=copy.deepcopy(row['normalizations']),
            saved_raw_XYZ_primary_statistics=copy.deepcopy(next(c for c in native.read(Path(item['summary']))['conditions']if c['id']==ident+'-square_3h')['volume_metrics']['regions']['target']['statistics']),
            old_screen_source=dict(path=str(CONTROL_VOLUME),old_screens_replaced=False)))
    require(bases[BASE_ID]['case']['comparison_signature']==bases[SHELL_ID]['case']['comparison_signature'],'Same physical/grid/ROI cohort required')
    for row in source['conditions']:
        artifact=row['artifacts']['condition.json'];c=_json(artifact['path'],refs,artifact['SHA256'])
        require(c['schema']=='task1-perimeter-antiphase-condition-v1'and c['status']=='calculated_unadopted'and c['id']==row['id']and
            c['source_case_id']==SHELL_ID and c['source_run_id']==SHELL_RUN and
            c['configuration_sha256']==bases[SHELL_ID]['case']['config_sha256']and c['actual_fundamental_Hz']==list(PAIR)and
            c['source_geometry_unchanged']is True and c['new_PDE']==0,'Actual completed antiphase source/coefficient identity required')
        coeff={f:c['coefficient_vectors'][str(f)]for f in PAIR}
        for f in PAIR:
            require(len(coeff[f]['real'])==len(coeff[f]['imaginary'])==2 and all(math.isfinite(v)for v in coeff[f]['real']+coeff[f]['imaginary']),
                'Finite actual two-source coefficients required')
        archive=row['artifacts']['volume.npz'];_local(archive['path']);refs[archive['path']]=archive['SHA256']
        cases.append(dict(id=c['id'],basis_id=SHELL_ID,coefficients=coeff,volume_file=archive,
            normalizations=copy.deepcopy(c['normalizations']),old_screen_source=dict(path=artifact['path'],SHA256=artifact['SHA256'],
                old_screen=copy.deepcopy(c['canonical_skin_cap_screen']),old_screens_replaced=False),
            saved_raw_XYZ_primary_statistics=copy.deepcopy(c['native_volume_metrics']['regions']['target']['statistics'])))
    require(len(cases)==8 and len({c['id']for c in cases})==8,'Exactly eight distinct source conditions required')
    return dict(cases=cases,bases=bases,source_summary_SHA256=refs[str(SOURCE_SUMMARY)])


def make_preregistration(output,decision_path,feedback_path):
    refs={};d=_json(decision_path,refs);f=_json(feedback_path,refs)
    require(d.get('schema')=='task1-direction-bounds-root-decision-v1'and d.get('status')=='selected_not_executed'and
        d.get('root_selected')is True and d.get('peer_endorsed')is False and d.get('new_PDE')==0 and
        d.get('candidate_adopted')is False and isinstance(d.get('question'),str)and d['question'].strip(), 'Root-selected supplemental direction-bound question required')
    require(d.get('source_summary')==dict(path=str(SOURCE_SUMMARY),SHA256=native.sha(SOURCE_SUMMARY))and
        d.get('feedback')==dict(path=str(feedback_path),SHA256=refs[str(feedback_path)]),'Exact completed source and fresh feedback pins required')
    require(f.get('schema')=='task1-queue-feedback-v1'and f.get('status')=='read_only_feedback_checked'and f.get('error')is None and
        f.get('public_GitHub_only')is True and f.get('messages_sent')==0 and f.get('new_PDE')==0,'Actual read-only public feedback receipt required')
    for p,digest in d.get('input_sha256',{}).items():_json(p,refs,digest)
    bundle=source_bundle(refs);implementation=_implementation();refs.update(implementation['implementation_files_sha256'])
    ledger=policy.load_ledger();refs.update(policy.policy_refs(ledger))
    return dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),
        lambdas=list(LAMBDAS),case_order=[c['id']for c in bundle['cases']],sources=bundle,input_sha256=refs,
        root_selection=dict(decision=dict(path=str(decision_path),SHA256=refs[str(decision_path)]),feedback=dict(path=str(feedback_path),SHA256=refs[str(feedback_path)]),peer_endorsed=False),
        numerical_contract=dict(matrix='Re(E)Re(E)^T+Im(E)Im(E)^T; actual peak fundE after coherent source composition',
            XYZ_TIS='2min(abs(E3000axis),abs(E3030axis)); fundamental pair only, distinct from RMS and full harmonic waveform envelope',
            upper='2sqrt(min_fixed_lambda eigmax(lambda*A0+(1-lambda)*A1))',lower='Existing2074 sampled-direction maximum, unchanged',
            angular_scope='Independent real unit direction at each native cell; not a single continuous axon path',
            outward_guard_eigenvalue_units_E_squared=dict(relative_factor_eps=FP_FACTOR,absolute=FP_EIGEN_ABSOLUTE),
            exact_zero_carrier_upper=0.,not_formal_IEEE_certificate=True,mesh_or_solver_convergence_claimed=False,
            tolerated_roundoff_inversion_handling='Only widen upper to unchanged savedLB after fixed1e-10/1e-12 consistency validation',
            fixed_cutoff_scope='Original2074 raw maxTIS primary/slab mean/P10; fixed numerical comparison thresholds, not physiology'),
        resources=dict(CPU_count=1,total_seconds=600,per_condition_seconds=60,source_load_seconds=60,RSS_bytes=3*GIB,
            minimum_free_disk_bytes=2*GIB,max_added_bytes=2*GIB,cumulative_seconds=policy.effective_limit(ledger)),
        new_PDE=0,phi_or_harmonic_field_reads=False,new_probes=False,old_screens_replaced=False,**implementation)


def verify_plan(path,output,expected=None,*,hash_arrays):
    p=_local(path);digest=native.sha(p);plan=native.read(p)
    require(expected is None or digest==expected,'Preregistration changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['output_directory']==str(output)and
        plan['lambdas']==list(LAMBDAS)and len(plan['case_order'])==8 and plan['new_PDE']==0 and plan['old_screens_replaced']is False,
        'Exact eight-condition supplemental bound registration required')
    for name,d in plan['input_sha256'].items():
        f=_local(name)
        if hash_arrays or f.suffix not in('.npz','.gz','.bin'):require(native.sha(f)==d,'Pinned input changed: '+name)
    require(_implementation()['implementation_files_sha256']==plan['implementation_files_sha256'],'Committed implementation changed')
    require(json.loads(json.dumps(source_bundle({})))==plan['sources'],
        'Saved source coefficients, normalizations, case order or physical provenance differ from immutable evidence')
    return plan,digest


def _array(path,shape):
    path=Path(path);count=math.prod(shape);opener=gzip.open if path.suffix=='.gz'else open
    with opener(path,'rb')as stream:
        data=stream.read(count*16+1)
    require(len(data)==count*16,'Exact native complex field dimensions required')
    a=np.frombuffer(data,dtype='<c16').reshape(shape)
    require(np.isfinite(a).all(),'Native complex field contains nonfinite values');return a


def _load_base(base):
    paths=base['files'];p=Path(paths['grid']['path']);opener=gzip.open if p.suffix=='.gz'else open
    with opener(p,'rt')as stream:grid=np.atleast_1d(np.genfromtxt(stream,delimiter=',',names=True))
    meta=base['metadata'];require(len(grid)==meta['cells']==351680,'Actual grid cell count mismatch')
    return dict(grid=grid,metadata=meta,field={f:_array(paths[str(f)]['path'],(2,len(grid),3))for f in PAIR})


def _load_scalars(case,base):
    with np.load(case['volume_file']['path'],allow_pickle=False)as z:arrays={k:z[k]for k in z.files}
    regions=volume.region_weights(arrays,base['grid'],base['metadata'])
    return arrays,regions


def _summaries(fields,lb,regions,grid,scale,cutoffs):
    out={}
    maps={name:fields[name]for name in('X_TIS','Y_TIS','Z_TIS')};maps.update(old2074_maxTIS_LB=lb,continuous_direction_UB=fields['continuous_direction_UB_V_m'])
    for region,weights in regions.items():
        out[region]={name:volume.weighted_statistics(values*scale,weights)for name,values in maps.items()}
        for name,values in maps.items():
            out[region][name]['hotspot']=volume.hotspot(values*scale,weights,grid)
            out[region][name]['hotspot_scope']='UB maximizer need not be actual continuous-direction maximizer'if name=='continuous_direction_UB'else'native scalar represented-cell maximum'
            out[region][name]['fixed_original_maxTIS_cutoff_volume_m3']={key:float(weights[values*scale>=c].sum())for key,c in cutoffs.items()}
        out[region]['continuous_direction_fixed_cutoff_volume_intervals']={key:weighted_volume_interval(lb,fields['continuous_direction_UB_V_m'],weights,c,scale)for key,c in cutoffs.items()}
    return out


def execute(plan,output,deadline,checkpoint):
    loaded={};start=time.monotonic()
    for ident,base in plan['sources']['bases'].items():
        loaded[ident]=_load_base(base);_deadline(min(deadline,start+60));checkpoint('fundamental_fields_loaded',basis_id=ident)
    require(np.array_equal(loaded[BASE_ID]['grid'],loaded[SHELL_ID]['grid']),'Original/shell grid order must be identical')
    results=[];baseline=None;cutoffs=None
    for case in plan['sources']['cases']:
        per=min(deadline,time.monotonic()+60);signal.setitimer(signal.ITIMER_REAL,max(.001,per-time.monotonic()))
        checkpoint('condition_start',condition_id=case['id']);base=loaded[case['basis_id']];arrays,regions=_load_scalars(case,base);lb=arrays['maxTIS']
        if cutoffs is None:cutoffs={r+'_'+s:volume.weighted_statistics(lb,regions[r])[s]for r in(volume.PRIMARY,volume.SLAB)for s in('mean','p10')}
        spectra={}
        for f in PAIR:
            row=case['coefficients'][str(f)]if str(f)in case['coefficients']else case['coefficients'][f]
            coeff=np.asarray(row['real'])+1j*np.asarray(row['imaginary']);spectra[f]=np.einsum('c,cnk->nk',coeff,base['field'][f])
        fields=field_bounds(spectra[3000],spectra[3030],deadline=per);validation=validate_lower_bound(lb,fields['continuous_direction_UB_V_m'])
        validation['upper_enlarged_to_unchanged_saved_LB_cells']=int(np.count_nonzero(lb>fields['continuous_direction_UB_V_m']))
        fields['continuous_direction_UB_eigen_guard_only_V_m']=fields['continuous_direction_UB_V_m'].copy()
        fields['continuous_direction_UB_V_m']=np.maximum(fields['continuous_direction_UB_V_m'],lb)
        for name in('X_TIS','Y_TIS','Z_TIS'):require(np.all(fields[name]<=lb+1e-12+1e-10*lb),'Saved2074 set must include physicalXYZ axes')
        validation['XYZ_primary_mean_P10_regression']={}
        for name in('X_TIS','Y_TIS','Z_TIS'):
            stats=volume.weighted_statistics(fields[name],regions[volume.PRIMARY]);saved=case['saved_raw_XYZ_primary_statistics'][name]
            require(all(math.isclose(stats[k],saved[k],rel_tol=1e-12,abs_tol=1e-14)for k in('mean','p10')),
                'Native source-bound XYZ primary statistics disagree: '+name)
            validation['XYZ_primary_mean_P10_regression'][name]=dict(passed=True,actual={k:stats[k]for k in('mean','p10')},saved={k:saved[k]for k in('mean','p10')})
        modes={};folder=output/case['id'];folder.mkdir()
        np.savez_compressed(folder/'direction-bounds.npz',**fields,old2074_maxTIS_LB=lb)
        for name,saved in case['normalizations'].items():
            scale=saved['amplitude_scale'];old=volume.weighted_statistics(lb*scale,regions[volume.PRIMARY]);expected=saved['regions'][volume.PRIMARY]['maxTIS']
            require(all(math.isclose(old[k],expected[k],rel_tol=1e-12,abs_tol=1e-14)for k in('mean','p10')),'Saved source-bound primarymean/P10 regression differs')
            metadata=copy.deepcopy({k:v for k,v in saved.items()if k not in('regions','probe40_unloaded')})
            metadata['regions']=_summaries(fields,lb,regions,base['grid'],scale,cutoffs);metadata['normalization_recomputed']=False;modes[name]=metadata;_deadline(per)
        robust={}
        if baseline is not None:
            for name,mode in modes.items():
                checks=[];reference=baseline['normalizations'][name]
                for region,stat,direction in((volume.PRIMARY,'mean','greater'),(volume.PRIMARY,'p10','greater'),('surface_0_5','p95','less'),('primary_complement','p95','less')):
                    a=mode['regions'][region];b=reference['regions'][region]
                    checks.append(dict(region=region,statistic=stat,**robust_failure(a['old2074_maxTIS_LB'][stat],a['continuous_direction_UB'][stat],b['old2074_maxTIS_LB'][stat],b['continuous_direction_UB'][stat],direction=direction)))
                robust[name]=dict(comparisons=checks,any_conditional_direction_robust_failure=any(c['status']=='conditional_direction_robust_failure'for c in checks))
        result=dict(id=case['id'],basis_id=case['basis_id'],status='calculated_supplemental_unadopted',normalizations=modes,
            lower_upper_validation=validation,direction_robust_necessary_gate_comparisons=robust,source=case,
            archive=dict(path=str(folder/'direction-bounds.npz'),SHA256=native.sha(folder/'direction-bounds.npz')),
            fixed_original_cutoffs_V_m=cutoffs,old_screens_replaced=False,new_PDE=0,new_probes=False)
        core.write(folder/'summary.json',result);results.append(result)
        if baseline is None:baseline=result
        checkpoint('condition_complete',condition_id=case['id'])
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
    return dict(schema='task1-direction-bounds-audit-v1',status='calculated_supplemental_unadopted',conditions=results,
        numerical_contract=plan['numerical_contract'],new_PDE=0,old_screens_replaced=False,new_probes=False,
        phi_or_harmonic_field_reads=False,normalization_changed=False,candidate_adopted=False,full_convergence_validated=False,
        root_selection=plan['root_selection'],input_sha256=plan['input_sha256'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',type=Path);g.add_argument('--preregistration',type=Path)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output
    require(output.is_absolute()and output==output.resolve()and output.is_relative_to(ROOT/'docs')and output.parent.is_dir()and not output.exists(),'New canonical docs output required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledgerpath=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledgerpath);cap=60 if args.prepare else 600
        require(policy.remaining_seconds(ledger)>=cap and shutil.disk_usage(output.parent).free>=2*GIB+256*1024**2,'Finite budget/reserve admission failed')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic();deadline=start+cap;status='failed_preserved';failure=None;state={};counter=0;stop=threading.Event();mutex=threading.RLock();thread=None
        def guard():
            require(core.rss(os.getpid())<3*GIB and shutil.disk_usage(output.parent).free>=2*GIB,'RSS3GiB/disk2GiB reserve exceeded')
            if output.exists():require(sum(p.stat().st_size for p in output.rglob('*')if p.is_file())<=2*GIB,'Added artifacts exceed2GiB')
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                guard();counter+=1;state.update(phase=phase,status=status if phase=='complete'else'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-start,**extra)
                core.write(output/f'checkpoint-{counter:03d}-{phase}.json',dict(state));core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex:guard();core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-start))
                except BaseException as e:state['resource_guard_failure']=str(e);os.kill(os.getpid(),signal.SIGTERM);return
        def interrupted(sig,frame):raise TimeoutError('Finite direction-bounds stop '+str(sig))
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in previous:signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60)
        try:
            if args.prepare:
                require(args.prepare.is_absolute()and args.prepare==args.prepare.resolve()and args.prepare.is_relative_to(ROOT/'docs')and not args.prepare.exists()and not args.prepare.with_name(args.prepare.name+'.failure.json').exists()and not args.prepare.is_relative_to(output),'New external canonical preregistration required')
                plan=make_preregistration(output,args.decision,args.feedback);args.prepare.parent.mkdir(parents=True,exist_ok=True)
                with args.prepare.open('x')as stream:json.dump(plan,stream,indent=2,allow_nan=False);stream.write('\n')
                status='preregistered_not_executed'
            else:
                require(args.decision is None and args.feedback is None,'Frozen selection context only at execution')
                output.mkdir();thread=threading.Thread(target=heartbeat,daemon=True);thread.start();checkpoint('verify_inputs')
                plan,digest=verify_plan(args.preregistration,output,hash_arrays=True)
                result=execute(plan,output,deadline,checkpoint);verify_plan(args.preregistration,output,digest,hash_arrays=True);guard()
                result.update(_implementation(),preregistration=dict(path=str(args.preregistration),SHA256=digest),inputs_unchanged=True,
                    resources=dict(CPU_count=1,max_seconds=600,max_condition_seconds=60,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,wall_seconds=time.monotonic()-start,cumulative_limit_seconds=policy.effective_limit(ledger)))
                core.write(output/'summary.json',result);status=result['status'];checkpoint('complete')
        except BaseException as e:
            failure=type(e).__name__+': '+str(e)
            dest=output/'failure.json'if output.exists()else args.prepare.with_name(args.prepare.name+'.failure.json')if args.prepare else None
            if dest is not None and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);core.write(dest,dict(status=status,error=failure,phase=state.get('phase'),condition_id=state.get('condition_id'),partial_artifacts_preserved=True,automatic_retry=False,new_PDE=0))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);stop.set()
            if thread is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='direction_bounds_prepare'if args.prepare else'direction_bounds_audit',seconds=elapsed,status=status,error=failure,finished_utc=core.now()));core.write(ledgerpath,ledger)
            if output.exists():core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for sig,handler in previous.items():signal.signal(sig,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
