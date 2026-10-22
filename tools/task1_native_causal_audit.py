#!/usr/bin/env python3
"""Finite saved-scalar spatial association; no source-causal decomposition.

The fixed baseline/asymmetric pair reuses the completed physical-pad report.
No E, phi, contact density, solver, waveform reconstruction or research module
is imported. NumPy is loaded lazily for the explicitly invoked cached audit.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
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

import task1_cloud_batch as core

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
SCHEMA='task1-native-spatial-association-plan-v1'
BASE_ID='baseline-square15-xy80'
ASYM_ID='asym-cross281p25-return168p75-xy80'
VOLUME=ROOT/'docs/cloud-continuation-20261021/volume-asymmetric.json'
PADS=ROOT/'docs/cloud-continuation-20261021/physical-pad-burdens.json'
SOURCES=(ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess'/BASE_ID/'summary.json',
         ROOT/'data-native/cloud-asymmetric-20261021T051000Z/postprocess'/ASYM_ID/'summary.json')
REGIONS={'surface_0_5':'surface_0_5','primary_r5_depth15_20':'target','primary_complement':None}
MODES=('raw_1Vpp','skin_contact_only')
REL=1e-10
ABS=1e-14


def require(ok,message):
    if not ok:raise ValueError(message)


def np_module():
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
    import numpy as np
    return np


def close_metric(actual,expected):
    return math.isfinite(float(actual)) and math.isfinite(float(expected)) and abs(actual-expected)<=ABS+REL*abs(expected)


def weighted_statistics(values,weights):
    np=np_module();v,w=np.asarray(values,float),np.asarray(weights,float)
    require(v.ndim==1 and v.shape==w.shape and len(v)>0 and np.isfinite(v).all() and
        np.isfinite(w).all() and np.all(w>=0) and np.any(w>0),'Finite matching scalar/positive volume arrays required')
    use=w>0;v,w=v[use],w[use];order=np.argsort(v,kind='stable');cdf=np.cumsum(w[order])
    out=dict(mean=float(v@w/w.sum()),volume_m3=float(w.sum()),min=float(v.min()),max=float(v.max()))
    for name,fraction in (('p10',.1),('p95',.95)):
        out[name]=float(v[order[min(int(np.searchsorted(cdf,fraction*cdf[-1],side='left')),len(v)-1)]])
    return out


def nearest_pad_labels(xy,centres):
    np=np_module();xy=np.asarray(xy,float);centres=np.asarray(centres,float)
    require(xy.ndim==2 and xy.shape[1]==2 and centres.shape==(4,2) and
        np.isfinite(xy).all() and np.isfinite(centres).all(),'Finite XY points/four physical-pad centres required')
    return np.argmin(np.sum((xy[:,None,:]-centres[None,:,:])**2,axis=2),axis=1)


def delta_statistics(before,after,weights,grid,cutoffs):
    np=np_module();a,b,w=np.asarray(before,float),np.asarray(after,float),np.asarray(weights,float)
    require(a.ndim==1 and a.shape==b.shape==w.shape and len(grid)==len(a) and len(a)>0 and
        np.isfinite(a).all() and np.isfinite(b).all() and np.all(a>=0) and np.all(b>=0) and
        np.isfinite(w).all() and np.all(w>=0) and np.any(w>0),'Finite nonnegative paired scalars/positive region required')
    require(bool(cutoffs) and all(math.isfinite(float(x)) and x>=0 for x in cutoffs.values()),'Fixed finite baseline cutoffs required')
    use=np.flatnonzero(w>0);delta=b-a;volume=float(w.sum())
    def hotspot(positive):
        ids=use[delta[use]>0] if positive else use[delta[use]<0]
        if not len(ids):return None
        i=int(ids[np.argmax(delta[ids]) if positive else np.argmin(delta[ids])])
        return dict(native_index=i,xyz_mm=[float(grid[k][i])for k in ('x_mm','y_mm','z_mm')],delta_V_m=float(delta[i]))
    am,bm=float(a@w/volume),float(b@w/volume)
    pos,neg=float(np.maximum(delta,0)@w/volume),float(np.minimum(delta,0)@w/volume)
    require(close_metric(pos+neg,bm-am),'Positive+negative weighted contributions must reproduce signed mean change')
    cuts={}
    for name,cutoff in cutoffs.items():
        av,bv=float(w[a>=cutoff].sum()),float(w[b>=cutoff].sum())
        cuts[name]=dict(cutoff_V_m=float(cutoff),before_high_volume_m3=av,after_high_volume_m3=bv,
            before_fraction=av/volume,after_fraction=bv/volume,comparison='value>=fixed raw same-grid baseline cutoff; not activation')
    return dict(total_volume_m3=volume,before_mean_V_m=am,after_mean_V_m=bm,signed_mean_change_V_m=bm-am,
        signed_delta_integral_V_m_times_m3=float(delta@w),positive_delta_mean_contribution_V_m=pos,
        negative_delta_mean_contribution_V_m=neg,positive_delta_volume_m3=float(w[delta>0].sum()),
        negative_delta_volume_m3=float(w[delta<0].sum()),zero_delta_volume_m3=float(w[delta==0].sum()),
        positive_hotspot=hotspot(True),negative_hotspot=hotspot(False),fixed_baseline_cutoffs=cuts,
        before_statistics=weighted_statistics(a,w),after_statistics=weighted_statistics(b,w))


def implementation_receipt():
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_native_causal_audit.py',ROOT/'tools/task1_cloud_batch.py',
        ROOT/'tools/task1_contact_patch_audit.py',ROOT/'tools/task1_contact_edge_audit.py',ROOT/'tools/task1_results_view.py']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in paths:
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)==path.read_bytes(),
            'All audit/controller/helper/test sources must match committed HEAD: '+str(path))
        pins[str(path)]=core.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def input_path(path):
    path=Path(path)
    require(path.is_absolute() and path==path.resolve() and path.is_relative_to(ROOT) and path.is_file() and
        not path.is_symlink() and path.stat().st_size<=64*1024**2,'Bounded regular canonical repository input required: '+str(path))
    require(not path.name.startswith(('field-','potential-','density-','source-','loss-','contacts-')),
            'Raw E/phi/contact/circuit reads are excluded; reuse completed pad report')
    return path


def make_preregistration(output):
    """Metadata/hash-only; root saves returned JSON to a new plan with open('x')."""
    output=Path(output)
    require(output.is_absolute() and output==output.resolve() and output.is_relative_to(ROOT/'docs/cloud-continuation-20261021')
        and not output.exists(),'Unique future output directory under continuation evidence required')
    volume,pads=core.read(VOLUME),core.read(PADS)
    require(volume['status']=='calculated_unadopted' and volume['inputs_unchanged'] is True and
        pads['status']=='complete_diagnostic_only' and pads['inputs_unchanged'] is True,
        'Completed source-bound volume and physical-pad reports required; no duplicate contact reconstruction')
    plan=dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),new_PDE_conditions=0,
        source_feedback_id='T1-F010-S3-GH6309148063',source_comment_id=6309148063,output_directory=str(output),
        source_volume_report=str(VOLUME),source_physical_pad_report=str(PADS),cases=[],input_sha256={},
        normalization_modes=list(MODES),regions=list(REGIONS),metric='fundamental sampled-direction maxTIS',
        regression_tolerance=dict(relative=REL,absolute=ABS),nearest_pad_tie='lowest physical pad index; XY centre distance only',
        cutoff_source='Raw baseline PRIMARY r<=5mm/depth15to20mm mean andP10, fixed across all regions/modes',
        resource_limits=dict(CPU_count=1,wall_seconds=180,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,cumulative_budget_seconds=6600),
        scope='Saved scalar spatial association plus reused contact burdens; not causal source superposition')
    def add(path,expected=None):
        p=input_path(path);digest=core.sha(p);require(expected is None or expected==digest,'Pinned metadata/artifact differs: '+str(p))
        plan['input_sha256'][str(p)]=digest;return p
    add(VOLUME);add(PADS)
    for summary_path,ident in zip(SOURCES,(BASE_ID,ASYM_ID)):
        post=core.read(add(summary_path));run=summary_path.parents[2]
        pre_path=add(run/'preregistration.json');pre=core.read(pre_path)
        case=next(c for c in pre['cases'] if c['id']==ident);record=core.read(add(run/'cases'/(ident+'.json')))
        require(post['status']==record['status']=='complete' and record['postprocess_sha256']==core.sha(summary_path),'Completed fixed native case required')
        rows=[r for r in volume['cases'] if r['case_id']==ident and r['summary_path']==str(summary_path)]
        contact=[r for r in pads['cases'] if r['case_id']==ident and r['summary_path']==str(summary_path)]
        require(len(rows)==len(contact)==1 and contact[0]['summary_sha256']==core.sha(summary_path) and
            contact[0]['case_eligibility']['eligible'] is True and all(v['passed'] for v in contact[0]['summary_metric_verification'].values()),
            'Completed eligible physical-pad result must already contain both cases')
        for key in ('config','mask'):add(Path(case[key+'_file']),case[key+'_sha256'])
        meta=post['mesh_metadata'];require(meta['h_xy_mm']==.625 and meta['sc_cells']==2 and
            meta['bulk_layer_counts']==[14,14,40] and meta['cells']==351680 and case['channels']==2 and
            case['circuit']['n_pads']==4 and case['circuit']['n_outputs']==2,'Fixed same-grid4pad/2output source required')
        native=post['input_sha256']
        def one(names):
            matches=[Path(p) for p in native if Path(p).name in names];require(len(matches)==1,'Unique native input required: '+str(names))
            return add(matches[0],native[str(matches[0])])
        grid=one({'grid.csv','grid.csv.gz'});metadata=one({'mesh-metadata.json'})
        archive=add(summary_path.parent/'volume.npz',post['artifacts']['files']['volume.npz']['SHA256'])
        centres=[p['center_mm'] for p in case['design']['pads']]
        require(centres==[[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]],'Same physical-pad XY centres required')
        # Preserve existing cached depth/spatial report provenance without parsing native E.
        associated=[]
        for name,digest in volume['inputs_sha256'].items():
            if str(run)+'/' in name and '/audit/' in name and Path(name).suffix in ('.json','.csv'):
                add(Path(name),digest);associated.append(name)
        plan['cases'].append(dict(case_id=ident,run_id=run.name,summary=str(summary_path),registration=str(pre_path),
            grid=str(grid),metadata=str(metadata),volume_npz=str(archive),pad_centres_xy_mm=centres,
            config_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],cached_spatial_depth_reports=associated,
            contact_report_reused=True,contact_density_reopened=False))
    implementation=implementation_receipt();plan.update(implementation);plan['input_sha256'].update(implementation['implementation_files_sha256'])
    return plan


def verify_plan(path,output,expected=None):
    path=input_path(path);digest=core.sha(path);plan=core.read(path)
    require(expected is None or digest==expected,'Audit plan changed')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed' and plan['new_PDE_conditions']==0 and
        plan['output_directory']==str(output) and [c['case_id']for c in plan['cases']]==[BASE_ID,ASYM_ID] and
        [c['summary']for c in plan['cases']]==list(map(str,SOURCES)) and
        plan['normalization_modes']==list(MODES) and plan['regions']==list(REGIONS), 'Exact fixed paired audit plan required')
    require(plan['regression_tolerance']==dict(relative=REL,absolute=ABS),'No numerical guard relaxation')
    require(plan['cutoff_source']=='Raw baseline PRIMARY r<=5mm/depth15to20mm mean andP10, fixed across all regions/modes',
            'Use identical raw primary-ROI baseline cutoffs for every region/mode')
    for name,pin in plan['input_sha256'].items():require(core.sha(input_path(name))==pin,'Audit input changed: '+name)
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'], 'Audit/helper implementation changed')
    return plan,digest


def load_scalar_case(declared):
    np=np_module();meta=core.read(declared['metadata']);dtype=[('x_mm','f8'),('y_mm','f8'),('z_mm','f8'),('layer','i4'),('volume_m3','f8')]
    path=Path(declared['grid']);opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rt') as stream:
        require(stream.readline().strip()=='x_mm,y_mm,z_mm,layer,volume_m3','Native grid column contract differs')
        grid=np.loadtxt(stream,delimiter=',',dtype=dtype)
    with np.load(declared['volume_npz'],allow_pickle=False) as archive:
        data={key:np.array(archive[key],dtype=float,copy=True) for key in
            ('maxTIS','RMS','region_total_m3','region_target_m3','region_surface_0_5_m3')}
    n=meta['cells'];require(n<=800000 and len(grid)==n and all(v.shape==(n,) and np.isfinite(v).all() and np.all(v>=0)for v in data.values()),
        'Complete bounded nonnegative saved scalar/volume arrays required')
    require(meta['radius_mm']==25 and meta['total_depth_mm']==25.1 and meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1]
        and np.isfinite(grid['x_mm']).all() and np.isfinite(grid['y_mm']).all() and np.isfinite(grid['z_mm']).all() and
        np.all(grid['x_mm']**2+grid['y_mm']**2<625),'FixedD50 native geometry required')
    total,target,surface=(data['region_'+key+'_m3']for key in ('total','target','surface_0_5'))
    require(np.all(total>0) and np.all(target<=total) and np.all(surface<=total) and
        np.allclose(total,grid['volume_m3'],rtol=REL,atol=1e-25),'Saved fractional volume/grid mismatch')
    weights={'surface_0_5':surface,'primary_r5_depth15_20':target,'primary_complement':np.maximum(0.,total-target)}
    return dict(grid=grid,meta=meta,scalar=data['maxTIS'],RMS=data['RMS'],weights=weights)


def association_groups(before,after,weights,grid,meta,labels,cutoffs):
    np=np_module();volume=float(weights.sum());faces=np.asarray(meta['z_faces_mm']);depth=np.searchsorted(faces,grid['z_mm'],side='right')-1
    rows=[]
    def add(kind,index,selected,extra):
        local=np.where(selected,weights,0.)
        if not np.any(local>0):return
        result=delta_statistics(before,after,local,grid,cutoffs)
        result.update(group_kind=kind,group_index=index,**extra,
            region_mean_delta_contribution_V_m=result['signed_delta_integral_V_m_times_m3']/volume)
        rows.append(result)
    for layer in range(4):add('layer',layer,grid['layer']==layer,dict(layer_index=layer))
    for pad in range(4):add('nearest_pad_XY',pad,labels==pad,dict(physical_pad=pad))
    for d in np.unique(depth):
        selected=depth==d;extent=dict(depth_faces_mm=[float(faces[d]),float(faces[d+1])])
        add('native_depth',int(d),selected,extent)
        for pad in range(4):add('native_depth_nearest_pad_XY',f'{int(d)}:{pad}',selected&(labels==pad),dict(**extent,physical_pad=pad))
    expected=delta_statistics(before,after,weights,grid,cutoffs)['signed_mean_change_V_m']
    for kind in ('layer','nearest_pad_XY','native_depth','native_depth_nearest_pad_XY'):
        require(close_metric(sum(r['region_mean_delta_contribution_V_m']for r in rows if r['group_kind']==kind),expected),
                'Spatial partition does not reproduce whole-region signed mean delta')
    return rows


def scaled_saved_pad_report(row,scale):
    """Scale already validated spectra coherently; never reread density files."""
    pads=[]
    for p in row['pads']:
        pads.append(dict(pad=p['pad'],physical_contact_area_mm2=p['physical_contact_area_mm2'],
            contact_power_W=p['contact_power_W']*scale**2,physical_pad_current_RMS_A=p['physical_pad_current_RMS_A']*scale))
    require(close_metric(sum(p['contact_power_W']for p in pads),row['contact_power_W']*scale**2),'Saved physical-pad contact powers must sum')
    spectra=copy.deepcopy(row['physical_pad_current_spectrum'])
    for f in spectra:
        for key in ('real_A_by_pad','imaginary_A_by_pad'):f[key]=[v*scale for v in f[key]]
        for key in ('common_GND_return_real_A','common_GND_return_imaginary_A','KCL_absolute_residual_A','KCL_denominator_A'):f[key]*=scale
        # Nested source comparison is left as explicitly raw provenance, not relabelled scaled.
        f.pop('source_output_comparison',None)
    return dict(pads=pads,contact_power_W=row['contact_power_W']*scale**2,physical_pad_current_spectrum=spectra,
        common_GND_return_current_RMS_A=row['common_GND_return_current_RMS_A']*scale,
        common_GND_return_definition=row['common_GND_return_definition'],
        reconstruction='Reused completed physical-pad report; complex spectra scaled before interpretation; no density/circuit re-read')


def build_audit(plan,checkpoint=lambda phase,**kwargs:None):
    np=np_module();volume,pad_report=core.read(plan['source_volume_report']),core.read(plan['source_physical_pad_report'])
    datasets=[]
    for declared in plan['cases']:
        checkpoint('load_saved_scalar',case_id=declared['case_id']);datasets.append(load_scalar_case(declared))
        checkpoint('saved_case_loaded',case_id=declared['case_id'])
    base,candidate=datasets
    require(np.array_equal(base['grid'],candidate['grid']) and all(np.array_equal(base['weights'][r],candidate['weights'][r])for r in REGIONS),
            'Only identical native mesh/order/fractional ROI weights can be paired')
    for key in ('h_xy_mm','z_faces_mm','tissue_boundaries_mm','source_peak_V','source_resistance_ohm','channels','field_reconstruction'):
        require(base['meta'][key]==candidate['meta'][key],'Paired mesh/normalization differs: '+key)
    rows=[next(c for c in volume['cases']if c['case_id']==case['case_id'])for case in plan['cases']]
    require(rows[0]['comparison_signature']==rows[1]['comparison_signature'],'Same-grid material/contact/ROI signature required')
    labels=nearest_pad_labels(np.column_stack((base['grid']['x_mm'],base['grid']['y_mm'])),plan['cases'][0]['pad_centres_xy_mm'])
    fixed=weighted_statistics(base['scalar'],base['weights']['primary_r5_depth15_20'])
    cutoffs=dict(baseline_mean=fixed['mean'],baseline_p10=fixed['p10'])
    results=[]
    for mode in MODES:
        scales=[r['normalizations'][mode]['amplitude_scale']for r in rows]
        require(all(math.isfinite(s) and s>0 for s in scales),'Actual saved positive normalization scales required')
        a,b=base['scalar']*scales[0],candidate['scalar']*scales[1];regions={}
        for region in REGIONS:
            checkpoint('paired_spatial_region',normalization=mode,region=region)
            w=base['weights'][region]
            result=delta_statistics(a,b,w,base['grid'],cutoffs)
            for index,values in enumerate((a,b)):
                actual=weighted_statistics(values,w);saved=rows[index]['normalizations'][mode]['regions'][region]['maxTIS']
                require(all(close_metric(actual[k],saved[k])for k in ('mean','p10','p95','min','max')),
                        'Saved fundamental TIS region metrics do not reproduce at frozen tolerance')
            result['spatial_associations']=association_groups(a,b,w,base['grid'],base['meta'],labels,cutoffs)
            rms=[weighted_statistics(d['RMS']*s,w)for d,s in zip(datasets,scales)]
            for index,actual in enumerate(rms):
                saved=rows[index]['normalizations'][mode]['regions'][region]['RMS']
                require(all(close_metric(actual[k],saved[k])for k in ('mean','p10','p95','min','max')),'Saved all-carrier RMS metric differs')
            result['all_carrier_E_RMS_statistics']=dict(before=rms[0],after=rms[1],definition='Total vector RMS of all4saved spectral lines, not modulation')
            regions[region]=result
        burdens=[]
        for declared,scale in zip(plan['cases'],scales):
            p=next(p for p in pad_report['cases']if p['case_id']==declared['case_id'])
            burdens.append(dict(case_id=declared['case_id'],amplitude_scale=scale,**scaled_saved_pad_report(p,scale)))
        results.append(dict(normalization=mode,amplitude_scales=scales,regions=regions,reused_physical_pad_burdens=burdens))
        checkpoint('normalization_complete',normalization=mode)
    return dict(schema='task1-native-spatial-association-audit-v1',status='complete_diagnostic_only',new_PDE=0,
        cases=plan['cases'],comparisons=results,source_feedback_id=plan['source_feedback_id'],
        source_reports=dict(volume=plan['source_volume_report'],physical_pad=plan['source_physical_pad_report']),
        native_E_phi_density_circuit_reopened=False,contact_report_reused=True,
        definitions=dict(TIS='fundamental3000/3030 sampled2074-direction maximum; nonlinear scalar, not additive by source',
            normalization='Actual saved raw1Vpp/skin_contact_only scales; not simultaneously equal power/current',
            attribution='Descriptive spatial association by native-depth/layer/nearest physical-pad XY centre; no source-causal assignment',
            nearest_pad='Geometric Voronoi label only; first physical pad index wins exact ties; commonGND returns remain coherent',
            signed_delta='after-before; positive/negative mean contributions divided by whole region volume',
            cutoff='Raw baseline PRIMARY r<=5mm/depth15to20mm mean/P10, identical across all regions and modes; no physiological threshold'),
        unavailable_fields=['Per-carrier vector E and balance decomposition not computed in this audit',
            'No proof that both carriers amplify at a hotspot', 'No causal source superposition of nonlinear maxTIS',
            'No loaded probe prediction, skin contact experiment, activation threshold or independent solver validation'],
        decision_scope='Use contact redistribution and spatial associations to propose a separate bounded rewiring test; no automatic nomination',
        existing_XY_SC_bulk_edge_contact_holds_preserved=True,candidate_adopted=False,numerical_validation_promoted=False,
        experimental_validation=False,safety_validation=False,regression_tolerance=dict(relative=REL,absolute=ABS))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.resolve()
    require(args.output.absolute()==output and output.is_relative_to(ROOT/'docs/cloud-continuation-20261021'),'Canonical continuation output required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # This check is intentionally inside both locks, immediately before mkdir.
        require(not output.exists(),'Never overwrite an attempted/complete native association audit')
        budget_path=ROOT/'runtime/task1-budget.json';ledger=core.read(budget_path)
        require(ledger['limit_seconds']==6600 and ledger['spent_seconds']<6600,'Existing cumulative budget exhausted')
        require(shutil.disk_usage(output.parent).free>=2*GIB+64*1024**2,'Keep2GiB reserve plus64MiB output allowance')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});output.mkdir();started=time.monotonic();status='failed_preserved';failure=None
        seconds=min(180.,6600-ledger['spent_seconds']);state_lock=threading.RLock();state={};counter=0;stop=threading.Event()
        def checkpoint(phase,**extra):
            nonlocal counter
            with state_lock:
                if phase!='failure':
                    require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS limit exceeded at phase: '+phase)
                    require(shutil.disk_usage(output).free>=2*GIB,'Existing2GiB disk reserve exhausted at phase: '+phase)
                phase_status=status if phase in ('complete','failure') else 'running'
                counter+=1;state.update(phase=phase,status=phase_status,pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),
                    updated_utc=core.now(),elapsed_seconds=time.monotonic()-started,**extra)
                with (output/f'checkpoint-{counter:03d}-{phase}.json').open('x')as stream:json.dump(state,stream,ensure_ascii=False,indent=2)
                core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5.):
                with state_lock:core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
        def expired(signum,frame):raise TimeoutError('180s/remaining6600s cached association audit deadline exceeded')
        def interrupted(signum,frame):raise RuntimeError('Controlled cached audit interruption by signal '+str(signum))
        previous={signum:signal.getsignal(signum)for signum in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        signal.signal(signal.SIGALRM,expired)
        signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        signal.setitimer(signal.ITIMER_REAL,seconds)
        thread=threading.Thread(target=heartbeat,daemon=True)
        try:
            thread.start();checkpoint('before_start')
            checkpoint('verify_plan');plan,plan_sha=verify_plan(args.plan.resolve(),output)
            checkpoint('start');result=build_audit(plan,checkpoint)
            verify_plan(args.plan.resolve(),output,expected=plan_sha)
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            require(peak<3*GIB,'Existing3GiB RSS limit exceeded')
            require(shutil.disk_usage(output).free>=2*GIB,'Existing2GiB reserve exhausted')
            result.update(implementation_receipt(),preregistration=dict(path=str(args.plan.resolve()),SHA256=plan_sha),
                inputs_sha256={**plan['input_sha256'],str(args.plan.resolve()):plan_sha},inputs_unchanged=True,wall_seconds=time.monotonic()-started,
                resources=dict(CPU_count=1,wall_limit_seconds=seconds,peak_RSS_bytes=peak,RSS_limit_bytes=3*GIB,disk_reserve_bytes=2*GIB))
            with (output/'result.json').open('x')as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
            status=result['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            with (output/'failure.json').open('x')as stream:json.dump(dict(status=status,error=failure,new_PDE=0,failed_evidence_preserved=True),stream,indent=2)
            checkpoint('failure',error=failure);raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            for signum,handler in previous.items():signal.signal(signum,handler)
            stop.set()
            if thread.ident is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='native_spatial_association_audit',status=status,seconds=elapsed,error=failure,finished_utc=core.now()))
            core.write(budget_path,ledger)
            with state_lock:core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
