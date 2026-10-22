#!/usr/bin/env python3
"""Finite fundamental carrier/balance readback of three fixed completed cases.

Only3000/3030Hz native E is read. No phi, density,9kHz E, direction search,
producer mutation or PDE. Source-selected maximum directions are read back,
not independently optimized. NumPy/research data are not loaded on import.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import threading
import time
import shutil

import task1_cloud_batch as core
import task1_results_view as view
from task1_output_power_evidence import output_power_evidence

ROOT=Path(__file__).resolve().parents[1]
GIB=1024**3
SCHEMA='task1-carrier-balance-preregistration-v1'
REL,ABS=1e-10,1e-12
CASE_IDS=('baseline-square15-xy80','asym-cross281p25-return168p75-xy80','return-cross281p25-signal168p75-xy80')
RUN_IDS=('cloud-mesh-c1-20261019T190000Z','cloud-asymmetric-20261021T051000Z','cloud-return-role-20261021T090200Z')
REPORTS=(ROOT/'docs/cloud-continuation-20261021/volume-asymmetric.json',
    ROOT/'docs/cloud-next-20261021T085200Z/return-role-volume.json')
MODES=('raw_1Vpp','skin_contact_only')


def require(ok,message):
    if not ok:raise ValueError(message)


def np_module():
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
    import numpy as np
    return np


def directions():
    """Exact26 Cartesian plus2048 Fibonacci source ordering, without imports."""
    np=np_module()
    result=[np.array(v)/np.linalg.norm(v)for v in itertools.product((-1,0,1),repeat=3)if any(v)]
    for i in range(2048):
        z=1-2*(i+.5)/2048;p=i*np.pi*(3-np.sqrt(5));r=np.sqrt(1-z*z)
        result.append([r*np.cos(p),r*np.sin(p),z])
    return np.array(result)


def read_active_field(path,n_cells,active_channel):
    np=np_module();path=Path(path)
    require(type(n_cells)is int and 0<n_cells<=800000 and active_channel in (0,1),'Bounded native cell count and explicit basis channel required')
    size=2*n_cells*3*16;opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb')as stream:data=stream.read(size+1)
    require(len(data)==size,'Exact little-endian complex128(2,N,3) decoded byte count required')
    array=np.frombuffer(data,dtype='<c16').reshape(2,n_cells,3)
    require(np.isfinite(array).all(),'Every native E basis element must be finite')
    return array[active_channel].copy()


def carrier_metrics(first,second,winner_indices,saved_max,saved_fixed):
    np=np_module();a,b=np.asarray(first,complex),np.asarray(second,complex);idx=np.asarray(winner_indices)
    require(a.ndim==2 and a.shape==b.shape and a.shape[1:]==(3,)and len(a)>0 and
        np.isfinite(a).all()and np.isfinite(b).all()and idx.shape==(len(a),)and
        np.issubdtype(idx.dtype,np.integer)and np.all((idx>=0)&(idx<2074)), 'Finite matching complex(N,3) carriers and integer saved direction indices required')
    selected=directions()[idx];fixed=np.array([1/math.sqrt(2),1/math.sqrt(2),0.])
    pa,pb=np.abs(np.einsum('ij,ij->i',a,selected)),np.abs(np.einsum('ij,ij->i',b,selected))
    fa,fb=np.abs(a@fixed),np.abs(b@fixed)
    result=dict(carrier0_RMS_V_m=np.sqrt(np.sum(np.abs(a)**2,axis=1)/2),
        carrier1_RMS_V_m=np.sqrt(np.sum(np.abs(b)**2,axis=1)/2),
        combined_fundamental_RMS_V_m=np.sqrt((np.sum(np.abs(a)**2,axis=1)+np.sum(np.abs(b)**2,axis=1))/2),
        max_direction_balance=np.divide(np.minimum(pa,pb),np.maximum(pa,pb),out=np.zeros(len(a)),where=np.maximum(pa,pb)>0),
        fixed_direction_balance=np.divide(np.minimum(fa,fb),np.maximum(fa,fb),out=np.zeros(len(a)),where=np.maximum(fa,fb)>0),
        maxTIS_reconstructed_V_m=2*np.minimum(pa,pb),fixedTIS_reconstructed_V_m=2*np.minimum(fa,fb),
        max_direction_zero_zero=(pa==0)&(pb==0),fixed_direction_zero_zero=(fa==0)&(fb==0))
    for key,saved in (('maxTIS_reconstructed_V_m',saved_max),('fixedTIS_reconstructed_V_m',saved_fixed)):
        saved=np.asarray(saved,float);actual=result[key]
        require(saved.shape==(len(a),)and np.isfinite(saved).all()and np.all(saved>=0),'Finite complete saved scalar required')
        bad=np.abs(actual-saved)>ABS+REL*np.abs(saved)
        require(not np.any(bad),f'Saved native scalar reconstruction failed: {key}; failed_cells={int(np.count_nonzero(bad))}')
    require(all(np.isfinite(v).all()for v in result.values()),'Reconstructed carrier magnitude overflow')
    return result


def source_coefficients(metrics):
    evidence=output_power_evidence(metrics)
    result={}
    for frequency,active in ((3000,0),(3030,1)):
        rows=[next(row for row in output['spectrum']if row['frequency_Hz']==frequency)for output in evidence['outputs']]
        ideal=[complex(row['ideal_voltage_peak_V']['real'],row['ideal_voltage_peak_V']['imaginary'])for row in rows]
        require(abs(ideal[active])>0 and abs(ideal[1-active])<=ABS+REL*abs(ideal[active]),'One active output and passive other-frequency termination required')
        result[frequency]=2*ideal[active]
    return result,evidence


def implementation_receipt():
    paths=[Path(__file__).resolve(),ROOT/'tests/test_task1_carrier_balance_audit.py',ROOT/'tools/task1_cloud_batch.py',
        ROOT/'tools/task1_results_view.py',ROOT/'tools/task1_output_power_evidence.py']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for path in paths:
        require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT)==path.read_bytes(),
            'Code/helpers/tests must match committed HEAD: '+str(path))
        pins[str(path)]=core.sha(path)
    return dict(implementation_git_commit=commit,implementation_files_sha256=pins)


def allowed_input(path):
    path=Path(path)
    require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)and path.is_file()and not path.is_symlink(), 'Canonical repository input required')
    name=path.name
    require(not name.startswith(('potential-','density-','contacts-','source-','loss-'))and
        (not name.startswith('field-')or name in ('field-3000.bin','field-3000.bin.gz','field-3030.bin','field-3030.bin.gz'))and
        (path.suffix!='.npz'or name=='volume.npz'),'Only fundamental E/grid/scalar/metadata reads permitted')
    require(path.stat().st_size<=96*1024**2,'Individual input exceeds finite96MiB bound')
    return path


def output_ok(path):
    relative=path.relative_to(ROOT/'docs')
    return bool(relative.parts)and relative.parts[0].startswith('cloud-next')


def make_preregistration(output):
    output=Path(output)
    require(output.is_absolute()and output==output.resolve()and output_ok(output)and not output.exists(),'Unique new docs/cloud-next... output directory required')
    implementation=implementation_receipt()
    plan=dict(schema=SCHEMA,status='preregistered_not_executed',created_utc=core.now(),output_directory=str(output),
        new_PDE_conditions=0,source_feedback_id='T1-F010-S3-GH6309148063',source_comment_id=6309148063,
        cases=[],input_sha256={},modes=list(MODES),
        tolerance=dict(relative=REL,absolute=ABS),direction_count=2074,direction_search=False,
        resource_limits=dict(CPU_count=1,wall_seconds=180,RSS_bytes=3*GIB,disk_reserve_bytes=2*GIB,cumulative_budget_seconds=6600),
        **implementation)
    def add(path,expected=None):
        path=allowed_input(path);digest=core.sha(path)
        require(expected is None or digest==expected,'Input SHA differs from completed source: '+str(path))
        plan['input_sha256'][str(path)]=digest;return path
    reports=[core.read(add(path))for path in REPORTS]
    for report in reports:require(report['status']=='calculated_unadopted'and report['inputs_unchanged']is True,'Completed source-bound volume report required')
    for ident,run_id in zip(CASE_IDS,RUN_IDS):
        run=ROOT/'data-native'/run_id;summary_path=run/'postprocess'/ident/'summary.json'
        summary=core.read(add(summary_path));registration=core.read(add(run/'preregistration.json'))
        case=next(c for c in registration['cases']if c['id']==ident)
        add(run/'cases'/(ident+'.json'))
        if(run/'reference-comparison.json').is_file():add(run/'reference-comparison.json')
        require(view.case_eligibility(summary_path,summary)['eligible'],'Only genuinely completed eligible source cases required')
        add(Path(case['config_file']),case['config_sha256'])
        add(Path(case['mask_file']),case['mask_sha256'])
        require(case['circuit']['n_pads']==4 and case['circuit']['n_outputs']==2,'Physical4pad/2output topology required')
        native=summary['input_sha256'];consumed={}
        for names,key in (({'mesh-metadata.json'},'metadata'),({'grid.csv','grid.csv.gz'},'grid'),
            ({'field-3000.bin','field-3000.bin.gz'},'field3000'),({'field-3030.bin','field-3030.bin.gz'},'field3030')):
            paths=[Path(p)for p in native if Path(p).name in names];require(len(paths)==1,'One exact native input required: '+key)
            consumed[key]=str(add(paths[0],native[str(paths[0])]))
        archive=add(summary_path.parent/'volume.npz',summary['artifacts']['files']['volume.npz']['SHA256'])
        report_index=1 if ident==CASE_IDS[2]else 0
        rows=[row for row in reports[report_index]['cases']if row['case_id']==ident and row['summary_path']==str(summary_path)]
        require(len(rows)==1 and reports[report_index]['inputs_sha256'].get(str(summary_path))==core.sha(summary_path), 'Normalization report is not bound to this completed summary')
        c=[row for row in summary['conditions']if row['waveform']=='square_3h']
        require(len(c)==1 and c[0]['actual_fundamental_Hz']==[3000,3030]and c[0]['phase_deg']==[0.,0.], 'Explicit later square_3h condition required')
        meta=summary['mesh_metadata'];require(meta['h_xy_mm']==.625 and meta['sc_cells']==2 and meta['bulk_layer_counts']==[14,14,40]and meta['cells']==351680
            and meta['radius_mm']==25 and meta['total_depth_mm']==25.1 and meta['tissue_boundaries_mm']==[0,.1,5.1,10.1,25.1]
            and meta['source_peak_V']==.5 and meta['source_resistance_ohm']==50 and meta['channels']==2
            and meta['phasor_convention']=='peak,+jomega_t','Exact fixed same-grid coarse/source normalization required')
        plan['cases'].append(dict(case_id=ident,run_id=run_id,summary=str(summary_path),volume_npz=str(archive),
            normalization_report=str(REPORTS[report_index]),condition_id=c[0]['id'],
            source_commit=registration['source_commit'],config_sha256=case['config_sha256'],mask_sha256=case['mask_sha256'],circuit=case['circuit'],
            comparison_signature=view.comparison_signature(summary,view.properties(case['config_file'])),**consumed))
    require(len({c['comparison_signature']for c in plan['cases']})==1,'Source mesh/material/contact/ROI signatures differ')
    plan['input_sha256'].update(implementation['implementation_files_sha256'])
    return plan


def verify_plan(path,output,expected=None):
    path=allowed_input(path);digest=core.sha(path);plan=core.read(path)
    require(expected is None or digest==expected,'Plan changed during audit')
    require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['output_directory']==str(output)
        and plan['new_PDE_conditions']==0 and [c['case_id']for c in plan['cases']]==list(CASE_IDS)and plan['modes']==list(MODES)
        and [c['run_id']for c in plan['cases']]==list(RUN_IDS)
        and [c['summary']for c in plan['cases']]==[str(ROOT/'data-native'/run/'postprocess'/ident/'summary.json')for ident,run in zip(CASE_IDS,RUN_IDS)]
        and plan['tolerance']==dict(relative=REL,absolute=ABS)and plan['direction_count']==2074 and plan['direction_search']is False,'Exact fixed three-case plan required')
    for path,digest0 in plan['input_sha256'].items():require(core.sha(allowed_input(path))==digest0,'Pinned input changed: '+path)
    require(implementation_receipt()['implementation_files_sha256']==plan['implementation_files_sha256'],'Implementation changed')
    return plan,digest


def weighted(values,weights,grid):
    np=np_module();v,w=np.asarray(values,float),np.asarray(weights,float);use=w>0
    require(v.shape==w.shape and np.isfinite(v).all()and np.isfinite(w).all()and np.all(w>=0)and np.any(use),'Finite weighted region required')
    vv,ww=v[use],w[use];order=np.argsort(vv,kind='stable');cdf=np.cumsum(ww[order]);index=int(np.flatnonzero(use)[np.argmax(vv)])
    result=dict(mean=float(vv@ww/ww.sum()),min=float(vv.min()),max=float(vv.max()),volume_m3=float(ww.sum()),
        maximum_native_index=index,maximum_native_center_xyz_mm=[float(grid[k][index])for k in ('x_mm','y_mm','z_mm')],
        maximum_native_layer_index=int(grid['layer'][index]))
    for key,fraction in (('p10',.1),('p50',.5),('p95',.95)):result[key]=float(vv[order[min(int(np.searchsorted(cdf,fraction*cdf[-1],side='left')),len(vv)-1)]])
    return result


def analyze_case(declared,checkpoint):
    np=np_module();summary=core.read(declared['summary']);meta=core.read(declared['metadata'])
    require(meta==summary['mesh_metadata'],'Native/source metadata differ')
    path=Path(declared['grid']);opener=gzip.open if path.suffix=='.gz'else open
    with opener(path,'rt')as stream:grid=np.atleast_1d(np.genfromtxt(stream,delimiter=',',names=True))
    n=meta['cells'];require(len(grid)==n and 0<n<=800000,'Native grid size mismatch')
    with np.load(declared['volume_npz'],allow_pickle=False)as archive:
        saved={key:archive[key]for key in ('maxTIS','fixedTIS','RMS','maxTIS_direction_index','region_total_m3','region_target_m3','region_surface_0_5_m3')}
    require(all(a.shape==(n,)and np.isfinite(a).all()for a in saved.values()),'Complete finite scalar/cache arrays required')
    require(np.all(saved['region_total_m3']>0)and np.all(saved['region_target_m3']>=0)and
        np.all(saved['region_target_m3']<=saved['region_total_m3'])and np.all(saved['region_surface_0_5_m3']>=0)and
        np.all(saved['region_surface_0_5_m3']<=saved['region_total_m3']),'Native fractional weights invalid')
    condition=next(c for c in summary['conditions']if c['id']==declared['condition_id'])
    coefficient,power_evidence=source_coefficients(condition['metrics'])
    checkpoint('load_fundamental_E',case_id=declared['case_id'])
    first=read_active_field(declared['field3000'],n,0)*coefficient[3000]
    second=read_active_field(declared['field3030'],n,1)*coefficient[3030]
    checkpoint('validate_saved_TIS',case_id=declared['case_id'])
    metrics=carrier_metrics(first,second,saved['maxTIS_direction_index'],saved['maxTIS'],saved['fixedTIS'])
    del first,second
    require(np.all(metrics['combined_fundamental_RMS_V_m']<=saved['RMS']+ABS+REL*np.abs(saved['RMS'])),
        'Combined fundamental RMS exceeds cached all-four-frequency RMS beyond frozen arithmetic tolerance')
    metrics['cached_all_frequency_RMS_V_m']=saved['RMS']
    regions={'primary_r5_depth15_20':saved['region_target_m3'],'surface_0_5':saved['region_surface_0_5_m3'],
        'primary_complement':saved['region_total_m3']-saved['region_target_m3']}
    report=core.read(declared['normalization_report']);row=next(row for row in report['cases']if row['case_id']==declared['case_id'])
    depths,inverse=np.unique(grid['z_mm'],return_inverse=True);modes={}
    for mode in MODES:
        scale=row['normalizations'][mode]['amplitude_scale'];require(math.isfinite(scale)and scale>0,'Positive source-bound scale required')
        entries={}
        for region,w in regions.items():
            result={};sums=np.bincount(inverse,weights=w,minlength=len(depths));used=sums>0
            for key,value in metrics.items():
                if key.endswith('zero_zero'):continue
                is_balance=key.endswith('_balance');actual=value if is_balance else value*scale
                stats=weighted(actual,w,grid)
                if is_balance:
                    zero=metrics[key.replace('_balance','_zero_zero')]
                    stats['zero_over_zero_assigned_zero_volume_fraction']=float(w[zero].sum()/w.sum())
                means=np.bincount(inverse,weights=actual*w,minlength=len(depths))[used]/sums[used]
                stats['native_depth_means']=[dict(depth_center_mm=float(z),mean=float(mean),represented_volume_m3=float(vol))for z,mean,vol in zip(depths[used],means,sums[used])]
                result[key]=stats
            entries[region]=result
        modes[mode]=dict(amplitude_scale=scale,regions=entries)
        checkpoint('normalization_complete',case_id=declared['case_id'],normalization=mode)
    grid_hash=hashlib.sha256(np.column_stack([grid[k]for k in grid.dtype.names]).astype('<f8').tobytes()).hexdigest()
    weight_hash={name:hashlib.sha256(w.astype('<f8').tobytes()).hexdigest()for name,w in regions.items()}
    return dict(case_id=declared['case_id'],condition_id=declared['condition_id'],source_summary=declared['summary'],
        source_commit=declared['source_commit'],config_sha256=declared['config_sha256'],mask_sha256=declared['mask_sha256'],circuit=declared['circuit'],
        comparison_signature=declared['comparison_signature'],grid_value_sha256=grid_hash,region_weights_value_sha256=weight_hash,
        coefficient_by_frequency={str(f):dict(real=c.real,imaginary=c.imag,amplitude=abs(c))for f,c in coefficient.items()},
        saved_TIS_reconstruction=dict(all_cells_passed=True,cells=n,relative_tolerance=REL,absolute_tolerance=ABS),
        fundamental_vs_cached_all_frequency_RMS_consistency=dict(all_cells_passed=True,relative_tolerance=REL,absolute_tolerance=ABS,
            scope='Arithmetic consistency of a nonnegative frequency-energy subset; not an additional convergence or safety gate'),
        output_power_evidence=power_evidence,modes=modes)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();output=args.output.resolve()
    require(args.output.absolute()==output and output_ok(output),'Canonical docs/cloud-next output required')
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not output.exists(),'Never overwrite attempted evidence')
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=core.read(ledger_path)
        require(ledger['limit_seconds']==6600 and ledger['spent_seconds']<6600,'Existing budget exhausted')
        require(shutil.disk_usage(output.parent).free>=2*GIB+32*1024**2,'Preserve2GiB disk reserve plus32MiB artifacts')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});output.mkdir();start=time.monotonic();status='failed_preserved';failure=None
        seconds=min(180.,6600-ledger['spent_seconds']);mutex=threading.RLock();stop=threading.Event();state={};counter=0
        def checkpoint(phase,**extra):
            nonlocal counter
            with mutex:
                require(core.rss(os.getpid())<3*GIB,'Existing3GiB RSS limit exceeded')
                require(shutil.disk_usage(output).free>=2*GIB,'Existing2GiB disk reserve exhausted')
                counter+=1;state.update(phase=phase,status=status if phase in('complete','failure')else'running',
                    pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-start,**extra)
                with(output/f'checkpoint-{counter:03d}-{phase}.json').open('x')as stream:json.dump(state,stream,indent=2)
                core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5.):
                with mutex:core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-start))
        def interrupted(signum,frame):raise RuntimeError('Controlled carrier-audit signal '+str(signum))
        def timeout(signum,frame):raise TimeoutError('Finite180s/remaining6600s carrier audit expired')
        previous={s:signal.getsignal(s)for s in(signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
        signal.setitimer(signal.ITIMER_REAL,seconds);thread=threading.Thread(target=heartbeat,daemon=True)
        try:
            thread.start();checkpoint('verify_plan');plan,plan_sha=verify_plan(args.plan.resolve(),output);results=[]
            for declared in plan['cases']:
                checkpoint('case_start',case_id=declared['case_id']);result=analyze_case(declared,checkpoint)
                if results:require(result['grid_value_sha256']==results[0]['grid_value_sha256']and result['region_weights_value_sha256']==results[0]['region_weights_value_sha256'],'Paired grid/ROI values differ')
                with(output/(declared['case_id']+'.json')).open('x')as stream:json.dump(result,stream,indent=2,allow_nan=False)
                results.append(result);checkpoint('case_complete',case_id=declared['case_id'])
            verify_plan(args.plan.resolve(),output,expected=plan_sha)
            checkpoint('all_inputs_reverified')
            final=dict(schema='task1-carrier-balance-audit-v1',status='complete_diagnostic_only',new_PDE=0,
                cases=[dict(case_id=r['case_id'],artifact=str(output/(r['case_id']+'.json')),SHA256=core.sha(output/(r['case_id']+'.json')))for r in results],
                preregistration=dict(path=str(args.plan.resolve()),SHA256=plan_sha),inputs_sha256=plan['input_sha256'],inputs_unchanged=True,
                definitions=dict(carrier_RMS='||complex E_f||/sqrt(2); separate3000/3030Hz',combined_fundamental_RMS='sqrt((||E3000||^2+||E3030||^2)/2)',
                    balance='min(abs(n.E3000),abs(n.E3030))/max;0/0 assigned0 with undefined-volume fraction reported',
                    envelope_variation='2min(abs(n.E3000),abs(n.E3030)); fundamental projection only, no activation or all-harmonic envelope',
                    max_direction='Original saved2074-direction winner at each cell; reconstructed, no new direction search; winners can differ across cases',
                    fixed_direction='(1/sqrt(2),1/sqrt(2),0); common across all cases',
                    cached_all_frequency_RMS='Existing four-frequency vector RMS, separately labeled;9kHz E not read',
                    coordinates='mm; z=0 top surface,positivez depth; native center of positively overlapping fractional ROI cell'),
                limitations=['Spatial association and carrier balance are descriptive, not a causal proof',
                    'No additive attribution of nonlinear TIS across physical pads or frequencies',
                    'No phi/density/9kHz field reads, waveform/probe update or PDE',
                    'All prior SC/XY/bulk/contact, instrument-loading, experimental and physiological holds remain'],
                direction_search=False,candidate_adopted=False,numerical_validation_promoted=False,experimental_validation=False,
                wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,**implementation_receipt())
            with(output/'result.json').open('x')as stream:json.dump(final,stream,indent=2,allow_nan=False)
            status=final['status'];checkpoint('complete')
        except BaseException as error:
            failure=type(error).__name__+': '+str(error)
            with(output/'failure.json').open('x')as stream:json.dump(dict(status=status,error=failure,new_PDE=0,partial_artifacts_preserved=True),stream,indent=2)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            stop.set()
            if thread.ident is not None:thread.join(timeout=1)
            elapsed=time.monotonic()-start;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='carrier_balance_audit',status=status,seconds=elapsed,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            with mutex:core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for signum,handler in previous.items():signal.signal(signum,handler)
        print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__=='__main__':main()
