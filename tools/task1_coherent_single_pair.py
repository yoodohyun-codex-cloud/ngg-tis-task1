"""Bounded cached single-pair RMS matching. Import never reads research data."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
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
import time

for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[_name]='1'
import numpy as np
try:
    import task1_resource_policy as policy
except ModuleNotFoundError:
    from tools import task1_resource_policy as policy

ROOT=Path(__file__).resolve().parents[1]
RUN='cloud-mesh-c1-20261019T190000Z'
C1='baseline-square15-C1pair0-xy80'
BASE='baseline-square15-xy80'
COHERENT='docs/cloud-next-coherent-drive-20261021T165000Z'
CANDIDATE='coherent-r1-p090'
GIB=1024**3
SCHEMA='task1-coherent-single-pair-preregistration-v1'

def require(ok,message):
    if not ok:raise ValueError(message)

def read(path):return json.loads(Path(path).read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(4*1024**2),b''):h.update(block)
    return h.hexdigest()

def write_new(path,obj):
    with Path(path).open('x')as stream:json.dump(obj,stream,indent=2,allow_nan=False);stream.write('\n')

def utc():return datetime.now(timezone.utc).isoformat()

def checkpoint(output,phase,started,started_utc,status='running'):
    obj=dict(status=status,phase=phase,pid=os.getpid(),proc_start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
        started_utc=started_utc,updated_utc=utc(),elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_PDE=0)
    write_new(output/('checkpoint-'+phase+'.json'),obj)
    temporary=output/'heartbeat.json.partial';temporary.write_text(json.dumps(obj,indent=2)+'\n');temporary.replace(output/'heartbeat.json')

def properties(path):
    return {k.strip():v.strip()for line in Path(path).read_text().splitlines()
        if line.strip()and not line.lstrip().startswith('#')for k,v in[line.split('=',1)]}

def implementation():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();pins={}
    for name in ('tools/task1_coherent_single_pair.py','tests/test_task1_coherent_single_pair.py','tools/task1_resource_policy.py'):
        path=ROOT/name
        require(subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)==path.read_bytes(),'Commit implementation before research execution: '+name)
        pins[str(path)]=sha(path)
    return dict(source_commit=commit,implementation_sha256=pins)

def validate_single(case,meta):
    circuit=case['circuit']
    require(circuit.get('n_pads')==2 and circuit.get('n_outputs')==1 and circuit.get('n_return_nodes')==1
        and circuit.get('pad_to_node')=={'0':'out0','1':'GND'} and circuit.get('source_peak_V')==.5
        and circuit.get('source_resistance_ohm')==50 and meta.get('channels')==1,
        'C1 must be one actual source/return pair, not four pads with a disabled output')
    require(meta.get('h_xy_mm')==.625 and meta.get('sc_cells')==2 and meta.get('bulk_layer_counts')==[14,14,40]
        and meta.get('cells')==351680 and meta.get('phasor_convention')=='peak,+jomega_t','Exact fixed C1 mesh/phasor convention required')

def validate_decision(decision,condition_path,condition_sha):
    require(decision.get('schema')=='task1-coherent-single-pair-decision-v1'and decision.get('status')=='selected_not_executed'
        and decision.get('candidate_id')==CANDIDATE and decision.get('single_case_id')==C1
        and decision.get('single_frequency_Hz')==3000 and decision.get('new_PDE')==0 and decision.get('candidate_adopted')is False
        and decision.get('source_condition_path')==str(condition_path)and decision.get('source_condition_sha256')==condition_sha
        and isinstance(decision.get('question'),str)and bool(decision['question'].strip()),'Explicit root single-pair selection/source binding required')

def validate_feedback(feedback):
    require(feedback.get('schema')=='task1-queue-feedback-v1'and feedback.get('status')=='read_only_feedback_checked'
        and feedback.get('public_GitHub_only')is True and feedback.get('messages_sent')==0
        and feedback.get('new_PDE')==0 and feedback.get('error')is None and feedback.get('observed_utc'),
        'Successful explicit read-only public feedback snapshot required')

def make_preregistration(output,decision_path,feedback_path):
    receipt=implementation();refs=dict(receipt['implementation_sha256'])
    def bind(path,expected=None):
        path=Path(path);require(path.is_absolute()and path==path.resolve()and path.is_relative_to(ROOT)
            and path.is_file()and not path.is_symlink(),'Canonical local source required')
        digest=sha(path);require(expected is None or digest==expected,'Source SHA mismatch: '+str(path));refs[str(path)]=digest;return read(path)
    source=ROOT/'data-native'/RUN;pre=bind(source/'preregistration.json')
    single=next(c for c in pre['cases']if c['id']==C1);summary=bind(source/'postprocess'/C1/'summary.json')
    record=bind(source/'cases'/(C1+'.json'))
    require(summary['status']==record['status']=='complete'and record['postprocess_sha256']==refs[str(source/'postprocess'/C1/'summary.json')], 'Completed original C1 receipt required')
    validate_single(single,summary['mesh_metadata'])
    gates=dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
    require(pre['gates']==gates and all(math.isfinite(record['validation'][k])and 0<=record['validation'][k]<=v for k,v in gates.items()),'Original five C1 native gates required')
    config=properties(single['config_file'])
    for p,(x,y)in enumerate(((-10.,-10.),(10.,-10.))):
        require(float(config[f'pad.{p}.x_mm'])==x and float(config[f'pad.{p}.y_mm'])==y
            and float(config[f'pad.{p}.width_mm'])==float(config[f'pad.{p}.height_mm'])==15.,'Original indexed source/return geometry required')
    sine=next(c for c in summary['conditions']if c['waveform']=='sine'and c['actual_fundamental_Hz']==[3000])
    primary=next(c for c in summary['conditions']if c['waveform']=='square_3h'and c['actual_fundamental_Hz']==[3000])
    coherent_summary=bind(ROOT/COHERENT/'summary.json')
    require(coherent_summary['status']=='calculated_unadopted'and coherent_summary['inputs_unchanged']is True,'Completed unchanged coherent scout required')
    row=next(c for c in coherent_summary['conditions']if c['id']==CANDIDATE)
    coherent=bind(Path(row['artifacts']['condition.json']['path']),row['artifacts']['condition.json']['SHA256'])
    require(coherent['id']==CANDIDATE and coherent['configuration_sha256']==next(c for c in pre['cases']if c['id']==BASE)['config_sha256']
        and coherent['candidate_adopted']is False and coherent['active_frequencies_Hz']==[3000,3030],'Exact latest unadopted coherent condition required')
    decision=bind(decision_path);validate_decision(decision,Path(row['artifacts']['condition.json']['path']),row['artifacts']['condition.json']['SHA256'])
    feedback=bind(feedback_path);validate_feedback(feedback)
    paths=dict(single_summary=str(source/'postprocess'/C1/'summary.json'),coherent_condition=str(ROOT/COHERENT/CANDIDATE/'condition.json'),
        coherent_npz=row['artifacts']['volume.npz']['path'],single_npz=str(source/'postprocess'/C1/primary['native_volume_archive']),
        baseline_summary=str(source/'postprocess'/BASE/'summary.json'),case_config=single['config_file'],case_mask=single['mask_file'])
    refs[paths['coherent_npz']]=row['artifacts']['volume.npz']['SHA256']
    refs[paths['single_npz']]=summary['artifacts']['files'][primary['native_volume_archive']]['SHA256']
    for key in ('case_config','case_mask'):refs[paths[key]]=single[key.removeprefix('case_')+'_sha256']
    selected={p:d for p,d in summary['input_sha256'].items()if Path(p).name in
        ('grid.csv.gz','grid.csv','mesh-metadata.json','validation.json','BASIS_COMPLETE','field-3000.bin.gz','potential-3000.bin.gz','density-3000.bin','source-3000.bin','loss-3000.bin','contacts-3000.csv')}
    require(len(selected)==10,'Exact complete cached 3k C1 field/potential/current/loss files required')
    refs.update(selected)
    baseline=bind(paths['baseline_summary']);baseline_record=bind(source/'cases'/(BASE+'.json'))
    require(baseline_record['status']=='complete'and baseline_record['postprocess_sha256']==refs[paths['baseline_summary']],'Completed canonical baseline required')
    paths['baseline_npz']=str(source/'postprocess'/BASE/'volume.npz');refs[paths['baseline_npz']]=baseline['artifacts']['files']['volume.npz']['SHA256']
    probe=source/'postprocess'/C1/summary['artifacts']['probes_json'];refs[str(probe)]=summary['artifacts']['files'][probe.name]['SHA256'];paths['single_unloaded_probes']=str(probe)
    refs.update(policy.policy_refs(policy.load_ledger()))
    return dict(schema=SCHEMA,status='preregistered_not_executed',candidate_id=CANDIDATE,source_run_id=RUN,single_case_id=C1,
        output_directory=str(output),paths=paths,single_case=single,single_sine_condition_id=sine['id'],
        baseline_circuit=next(c for c in pre['cases']if c['id']==BASE)['circuit'],
        root_selection_decision=dict(path=str(decision_path),SHA256=refs[str(decision_path)],question=decision['question']),
        feedback_context=dict(path=str(feedback_path),SHA256=refs[str(feedback_path)],observed_utc=feedback['observed_utc'],
            scope='Public read-only feedback context; root selection is not peer endorsement or adoption'),
        native_input_sha256=selected,input_sha256=refs,new_PDE=0,max_seconds=120,**receipt,
        matching_definitions=['centre20 native E trilinear RMS','sqrt(sum(fractional_ROI_volume * native_E_RMS_squared)/sum(fractional_ROI_volume))'],
        targets=['latest_coherent_raw_1Vpp','latest_coherent_original_skin8','canonical_four_line_square_1Vpp'],
        holds=['Unadopted coherent candidate fails off-target screens','RMS matching is not modulation/physiological equivalence',
            'PBS interface and all mesh/contact convergence holds remain','Unloaded phi/probe predictions only; no instrument loading validation'])

def verify_plan(path,output):
    plan=read(path);require(plan['schema']==SCHEMA and plan['status']=='preregistered_not_executed'and plan['candidate_id']==CANDIDATE
        and plan['output_directory']==str(output)and plan['max_seconds']==120 and plan['new_PDE']==0,'Exact bounded RMS matching plan required')
    require(implementation()['implementation_sha256']==plan['implementation_sha256'],'Implementation changed')
    for name,digest in plan['input_sha256'].items():
        p=Path(name);require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and not p.is_symlink()and sha(p)==digest,'Pinned input changed: '+name)
    return plan

def weighted_energy_rms(values,weights):
    values,weights=np.asarray(values,float),np.asarray(weights,float)
    require(values.ndim==1 and values.shape==weights.shape and np.isfinite(values).all()and np.isfinite(weights).all()
        and np.all(values>=0)and np.all(weights>=0)and weights.sum()>0,'Finite native RMS and fractional volumes required')
    return float(np.sqrt(np.dot(values*values,weights)/weights.sum()))

def weighted_p95(values,weights):
    order=np.argsort(values,kind='stable');index=min(int(np.searchsorted(np.cumsum(weights[order]),.95*weights.sum())),len(order)-1)
    return float(values[order[index]])

def sample_native(values,grid,point=(0.,0.,20.)):
    coordinates=[np.unique(grid[k])for k in ('x_mm','y_mm','z_mm')];pairs=[]
    for axis,x in zip(coordinates,point):
        j=int(np.searchsorted(axis,x));require(0<j<len(axis),'Interior interpolation point required')
        t=(x-axis[j-1])/(axis[j]-axis[j-1]);pairs.append(((axis[j-1],1-t),(axis[j],t)))
    result=np.zeros(values.shape[1:],complex)
    for x,wx in pairs[0]:
        for y,wy in pairs[1]:
            for z,wz in pairs[2]:
                indices=np.flatnonzero((grid['x_mm']==x)&(grid['y_mm']==y)&(grid['z_mm']==z))
                require(len(indices)==1,'Unique complete interior native stencil required');result+=values[indices[0]]*wx*wy*wz
    return result

def scale_burdens(raw,scale):
    require(math.isfinite(scale)and scale>0,'Positive finite matching scale required')
    return {k:v*scale**(2 if k.endswith('_W')else 1)for k,v in raw.items()}

def matched_single(target_centre,target_roi,single_centre,single_roi,burdens):
    require(min(target_centre,target_roi,single_centre,single_roi)>0,'Positive point and ROI RMS required')
    return {name:dict(required_source_Vpp=scale,amplitude_scale=scale,burdens=scale_burdens(burdens,scale),
        achieved_centre20_E_RMS_V_m=single_centre*scale,achieved_ROI_energy_RMS_V_m=single_roi*scale)
        for name,scale in [('centre20_E_RMS',target_centre/single_centre),('ROI_energy_RMS',target_roi/single_roi)]}

def execute(plan,phase=lambda name:None):
    phase('read-native')
    paths=plan['paths'];summary=read(paths['single_summary']);coherent=read(paths['coherent_condition']);base=read(paths['baseline_summary'])
    sine=next(c for c in summary['conditions']if c['id']==plan['single_sine_condition_id']);meta=summary['mesh_metadata'];validate_single(plan['single_case'],meta)
    def native(name):return Path(next(p for p in plan['native_input_sha256']if Path(p).name in (name,name+'.gz')))
    def complex_array(name,shape):
        p=native(name);opener=gzip.open if p.suffix=='.gz'else open
        with opener(p,'rb')as stream:raw=stream.read()
        a=np.frombuffer(raw,dtype='<c16');require(a.size==math.prod(shape)and np.isfinite(a).all(),'Exact finite complex native dimensions required');return a.reshape(shape)
    gp=native('grid.csv');opener=gzip.open if gp.suffix=='.gz'else open
    with opener(gp,'rt')as stream:grid=np.genfromtxt(stream,delimiter=',',names=True)
    n=meta['cells'];require(len(grid)==n,'Native grid cell count mismatch')
    with np.load(paths['coherent_npz'],allow_pickle=False)as a:crms=a['RMS'];weights=a['region_target_m3'];total=a['region_total_m3']
    with np.load(paths['single_npz'],allow_pickle=False)as a:require(np.array_equal(weights,a['region_target_m3'])and np.array_equal(total,a['region_total_m3']),'C1/coherent fractional volumes differ')
    field=-1j*complex_array('field-3000.bin',(1,n,3))[0];phi=-1j*complex_array('potential-3000.bin',(1,n))[0]
    erms=np.sqrt(np.sum(abs(field)**2,axis=1)/2);single_roi=weighted_energy_rms(erms,weights)
    centre_field=sample_native(field,grid);single_centre=float(np.sqrt(np.vdot(centre_field,centre_field).real/2))
    require(math.isclose(single_centre,sine['metrics']['target20_total_E_RMS_V_m'],rel_tol=1e-10,abs_tol=1e-12),'Stored native centre RMS reproduction failed')
    cp=native('contacts-3000.csv');contacts=np.genfromtxt(cp,delimiter=',',names=True);area=contacts['area_m2'];pads=contacts['pad'].astype(int)
    require(set(pads)=={0,1}and np.all(area>0),'Exactly source/return physical contact IDs required')
    density=-1j*complex_array('density-3000.bin',(1,len(area)))[0];transfer=complex_array('source-3000.bin',(1,1))[0,0];loss=complex_array('loss-3000.bin',(6,1,1))[:,0,0]
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
    coherent_roi=weighted_energy_rms(crms,weights);sc=float(coherent['normalizations']['skin_contact_only']['amplitude_scale'])
    phase('match-point-and-ROI')
    with np.load(paths['baseline_npz'],allow_pickle=False)as a:
        require(np.array_equal(weights,a['region_target_m3']),'Canonical baseline ROI weights differ');base_roi=weighted_energy_rms(a['RMS'],weights)
    baseline=next(c for c in base['conditions']if c['waveform']=='square_3h')
    targets=[('latest_coherent_raw_1Vpp',coherent['electrical_metrics']['target20_total_E_RMS_V_m'],coherent_roi,1.),
        ('latest_coherent_original_skin8',coherent['electrical_metrics']['target20_total_E_RMS_V_m']*sc,coherent_roi*sc,sc),
        ('canonical_four_line_square_1Vpp',baseline['metrics']['target20_total_E_RMS_V_m'],base_roi,1.)]
    phi_e=[]
    for axis,delta in enumerate((.1,.1,.01)):
        plus=np.array([0.,0.,20.]);minus=plus.copy();plus[axis]+=delta;minus[axis]-=delta
        phi_e.append(-(sample_native(phi,grid,plus)-sample_native(phi,grid,minus))/(2*delta/1000))
    def reference_metrics(ident,scale):
        metrics=baseline['metrics']if ident.startswith('canonical')else coherent['electrical_metrics']
        keys=('surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V',
            'max_source_current_RMS_mA','SC_power_W','contact_power_W','source_power_W','source_resistor_power_W','tissue_contact_power_W')
        return dict(**{k:metrics[k]*scale**(2 if k.endswith('_W')else 1)for k in keys},
            source_current_RMS_by_output_mA=[x*scale for x in metrics['source_current_RMS_by_output_mA']])
    return dict(schema='task1-coherent-single-pair-rms-v1',status='calculated_unadopted',candidate_id=CANDIDATE,
        candidate_source_condition=paths['coherent_condition'],candidate_source_commit=coherent['source_commit'],
        targets=[dict(id=ident,target_centre20_E_RMS_V_m=point,target_ROI_energy_RMS_V_m=roi,candidate_amplitude_scale=scale,
            reference_electrical_metrics=reference_metrics(ident,scale),
            reference_circuit=plan['baseline_circuit']if ident.startswith('canonical')else coherent['source_circuit'],
            reference_source_Vpp_intervals_V=[[1.,1.],[1.,1.]]if ident.startswith('canonical')else
                coherent['normalizations']['skin_contact_only'if ident.endswith('skin8')else'raw_1Vpp']['actual_source_Vpp_intervals_V'],
            matches=matched_single(point,roi,single_centre,single_roi,burdens))for ident,point,roi,scale in targets],
        single_stimulation=dict(case_id=C1,source_run_id=RUN,circuit=plan['single_case']['circuit'],physical_pad_centres_mm=[[-10,-10],[10,-10]],
            waveform='pure sine',frequency_Hz=3000,raw_source_Vpp=1.,raw_centre20_E_RMS_V_m=single_centre,raw_ROI_energy_RMS_V_m=single_roi,
            raw_burdens=burdens,unloaded_probe_reference=dict(path=paths['single_unloaded_probes'],condition_id=sine['id'],
                scaling='Existing sine phi-derived Vpp/RMS multiply by each matching amplitude_scale; instrument loading not established')),
        point_definition='Native complex E trilinear interpolation at(0,0,20)mm, sqrt(sum_f dot(E*,E)/2); same original electrical metric',
        ROI_definition='Central r<=5mm, depth15..20; full-precision fractional volume; sqrt(weighted mean of native E_RMS squared), NOT mean(E_RMS)',
        separate_unloaded_phi_gradient_centre_RMS_V_m=float(np.sqrt(np.vdot(phi_e,phi_e).real/2)),phi_gradient_used_for_matching=False,
        new_PDE=0,new_native_RHS=0,candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False,holds=plan['holds'])

def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',type=Path);group.add_argument('--preregistration',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--decision',type=Path);parser.add_argument('--feedback',type=Path)
    args=parser.parse_args();output=args.output.resolve();require(output.is_relative_to(ROOT/'docs')and not output.exists(),'Unique new docs output directory required')
    with policy.execution_lock(ROOT/'runtime/task1-budget.json'):
        ledger=policy.load_ledger();require(policy.remaining_seconds(ledger)>=120,'Reserve120s authorized audit time')
        require(shutil.disk_usage(output.parent).free>=2*GIB+64*1024**2,'Preserve2GiB disk reserve plus finite output allowance')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        soft,hard=resource.getrlimit(resource.RLIMIT_AS)
        address_limit=min([3*GIB]+[x for x in (soft,hard)if x!=resource.RLIM_INFINITY])
        resource.setrlimit(resource.RLIMIT_AS,(address_limit,hard))
        start=time.monotonic();started_utc=utc();status='failed_preserved';error=None
        def timeout(signum,frame):raise TimeoutError('Finite120s cached RMS matching deadline')
        prior=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,120)
        try:
            if args.prepare:
                require(not args.prepare.exists()and not args.prepare.resolve().is_relative_to(output),'New independent preregistration required')
                require(args.decision is not None and args.feedback is not None,'Explicit root decision and fresh feedback paths required')
                plan=make_preregistration(output,args.decision.resolve(),args.feedback.resolve());write_new(args.prepare,plan);status=plan['status']
            else:
                output.mkdir();checkpoint(output,'verify-plan',start,started_utc)
                plan=verify_plan(args.preregistration,output)
                result=execute(plan,lambda name:checkpoint(output,name,start,started_utc));verify_plan(args.preregistration,output)
                require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<3*GIB,'Existing3GiB RSS limit exceeded')
                require(shutil.disk_usage(output).free>=2*GIB,'Preserve2GiB disk reserve')
                result.update(preregistration=dict(path=str(args.preregistration.resolve()),SHA256=sha(args.preregistration)),
                    source_commit=plan['source_commit'],input_sha256=plan['input_sha256'],inputs_unchanged=True,
                    resources=dict(max_seconds=120,CPU_count=1,wall_seconds=time.monotonic()-start,cumulative_limit_seconds=policy.effective_limit(ledger),
                        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,address_space_limit_bytes=address_limit,
                        started_utc=started_utc,finished_utc=utc(),budget_spent_before_seconds=ledger['spent_seconds'],
                        budget_remaining_after_wall_seconds=policy.remaining_seconds(ledger)-(time.monotonic()-start)))
                write_new(output/'summary.json',result);status=result['status']
                checkpoint(output,'complete',start,started_utc,status)
        except BaseException as exc:
            error=type(exc).__name__+': '+str(exc)
            if output.exists():
                write_new(output/'failure.json',dict(status=status,error=error,new_PDE=0,partial_evidence_preserved=True,finished_utc=utc()))
                checkpoint(output,'failed',start,started_utc,status)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,prior);elapsed=time.monotonic()-start
            ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.name,stage='coherent_single_pair_prepare'if args.prepare else'coherent_single_pair_rms',seconds=elapsed,status=status,error=error))
            partial=ROOT/'runtime/task1-budget.json.partial';partial.write_text(json.dumps(ledger,indent=2,allow_nan=False)+'\n');partial.replace(ROOT/'runtime/task1-budget.json')
    print(json.dumps(dict(status=status,output=str(output),new_PDE=0)))

if __name__=='__main__':main()
