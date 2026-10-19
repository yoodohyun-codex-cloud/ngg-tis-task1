"""Checkpointed phantom exploration; pad count <= 8, fixed measured interfaces.

Common ground, 50 ohm source impedance and material assumptions are retained.
Optimizes electric-field proxies, not neural activation or a clinical threshold.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,csv,hashlib,itertools,json,math,os,shutil,subprocess,sys,time,tempfile
import numpy as np
from explore_inputs import ROOT,FREQUENCIES,build_inputs,dump

JAVAC=Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin/javac')
MATERIALS={'sc.sigma':.0002,'sc.epsilon_r':110000,'dermis.sigma':.2,'dermis.epsilon_r':10000,
           'fat.sigma':.04,'fat.epsilon_r':1000,'muscle.sigma':.3,'muscle.epsilon_r':100000}
WAVES={'sine':(1,0),'square_3h':(3/(2*math.sqrt(2)),1/(2*math.sqrt(2))),
       'triangle_3h':(.9,-.1)}

def atomic(path,value):
    path=Path(path);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='.'+path.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)

def directions(count=512):
    base=[np.array(v)/np.linalg.norm(v) for v in itertools.product((-1,0,1),repeat=3) if any(v)]
    for i in range(count):
        z=1-2*(i+.5)/count;p=i*np.pi*(3-np.sqrt(5));r=np.sqrt(1-z*z);base.append([r*np.cos(p),r*np.sin(p),z])
    return np.array(base)

DIRS=directions(2048)
def modulation(a,b):
    return float(2*np.minimum(abs(DIRS@a),abs(DIRS@b)).max())

def geometry_valid(xy,size,gap=1.25):
    xy=np.asarray(xy)
    if len(xy)>8 or len(xy)%2 or size<=0:return False
    for p in xy:
        if any(np.linalg.norm(p+np.array([i,j])*size/2)>25+1e-9 for i,j in itertools.product((-1,1),repeat=2)):return False
    for p,q in itertools.combinations(xy,2):
        d=np.maximum(abs(p-q)-size,0)
        if np.linalg.norm(d)<gap-1e-9:return False
    return True

def mesh_representable(design,h):
    axis=np.arange(int(round(50/h)))*h-25+h/2
    x,y=np.meshgrid(axis,axis);inside=x*x+y*y<25*25
    for px,py in design['xy_mm']:
        s=design['size_mm']
        ax=np.maximum(0,np.minimum(x+h/2,px+s/2)-np.maximum(x-h/2,px-s/2))
        ay=np.maximum(0,np.minimum(y+h/2,py+s/2)-np.maximum(y-h/2,py-s/2))
        if not math.isclose(float((ax*ay*inside).sum()),s*s,rel_tol=1e-9,abs_tol=1e-7):return False
    return True

def designs():
    result=[];seen=set()
    def add(name,xy,size):
        if not geometry_valid(xy,size):return
        key=(size,tuple(np.round(np.asarray(xy).ravel(),4)))
        if key in seen:return
        seen.add(key);result.append({'layout':name,'xy_mm':np.asarray(xy).tolist(),'size_mm':size,'channels':len(xy)//2})
    add('reference-a12.5-b12.5-p1',[[-12.5,-12.5],[12.5,12.5],[12.5,-12.5],[-12.5,12.5]],10)
    # Cover pad count and size before adding densely spaced layout variants.
    for size in (15,12.5,10,7.5,5,17.5,20):
        for channels in (2,4,3,1):
            for radius in (12.5,17.5,10,15,20):
                for offset in (0,22.5,45):
                    angle=np.arange(channels*2)*np.pi/channels+np.deg2rad(offset)
                    points=np.c_[np.cos(angle),np.sin(angle)]*radius
                    for pattern in ('alternating','separated'):
                        order=list(range(0,2*channels,2))+list(range(1,2*channels,2)) if pattern=='alternating' else list(range(2*channels))
                        add(f'ring-{channels*2}pad-r{radius}-rot{offset}-{pattern}',points[order],size)
    for size in (5,7.5,10,12.5,15):
        for a in (7.5,10,12.5,15,17.5):
            for b in (7.5,10,12.5,15):
                for pattern in (0,1,2):
                    pos=np.array([[-a,-b],[a,-b],[a,b],[-a,b]])
                    order=([0,1,2,3],[0,2,1,3],[0,3,1,2])[pattern]
                    add(f'rect-a{a}-b{b}-p{pattern}',pos[order],size)
        for inner,outer in ((7.5,17.5),(10,20),(7.5,20)):
            active=[[inner,0],[0,inner],[-inner,0],[0,-inner]]
            ground=[[outer,0],[0,outer],[-outer,0],[0,-outer]]
            add(f'nested-inner{inner}-outer{outer}',active+ground,size)
    return result

def design_frequencies(design):
    f=int(design.get('carrier_Hz',2000));beat=int(design.get('beat_Hz',10))
    return (f,f+beat,3*f,3*(f+beat)) if 3*(f+beat)<=10000 else (f,f+beat)

def contact_rows(design,profile):
    from update_ngg_eis import interpolate_complex
    result=[]
    for frequency in design_frequencies(design):
        measured=interpolate_complex(profile['points'],frequency)
        rs=0 if design.get('boundary_mode')=='full_measured' else profile['selected_fit']['Rs_ohm']
        re=measured['Z_real_ohm']-rs
        if re< -1e-9:raise ValueError('Nonpassive boundary at selected frequency')
        result.append({'frequency_Hz':frequency,'area_real_ohm_m2':max(0,re)*1e-4,'area_imag_ohm_m2':measured['Z_imag_ohm']*1e-4})
    return result

def config_text(design,profile,h):
    values=dict(MATERIALS,h_mm=h,size_mm=design['size_mm'],channels=design['channels'],frequencies=','.join(map(str,design_frequencies(design))))
    for i,(x,y) in enumerate(design['xy_mm']):values.update({f'pad.{i}.x_mm':x,f'pad.{i}.y_mm':y})
    for row in contact_rows(design,profile):
        f=row['frequency_Hz'];values[f'z.{f}.re']=row['area_real_ohm_m2'];values[f'z.{f}.im']=row['area_imag_ohm_m2']
    return ''.join(f'{k}={v}\n' for k,v in values.items())

def compile_solver():
    executable=shutil.which('javac') or (str(JAVAC) if JAVAC.is_file() else None)
    if not executable:raise RuntimeError('Java JDK compiler is required')
    subprocess.run([executable,'-encoding','UTF-8','TisSweep.java','ExploreBasis.java'],cwd=ROOT,check=True)

def solve_basis(run,design,profile,h):
    config=config_text(design,profile,h);key=hashlib.sha256(config.encode()).hexdigest()[:18]
    folder=run/'bases'/key;cfg=run/'configs'/f'{key}.properties';cfg.parent.mkdir(exist_ok=True)
    cfg.write_text(config)
    if not (folder/'BASIS_COMPLETE').exists():
        if folder.exists():shutil.rmtree(folder)
        (run/'bases').mkdir(exist_ok=True)
        with (run/'solver.log').open('a') as log:
            result=subprocess.run([os.environ.get('NGG_JAVA','java'),'-Xmx2g','-cp',str(ROOT),'ExploreBasis',str(cfg),str(folder)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError(f'Basis solve failed; see {run}/solver.log')
    return key,load_basis(folder,design['channels'],design_frequencies(design))

def load_basis(folder,channels,frequencies=FREQUENCIES):
    grid=np.genfromtxt(folder/'grid.csv',delimiter=',',names=True)
    n=len(grid);basis={'grid':grid,'validation':json.loads((folder/'validation.json').read_text()),'f':{}}
    x=np.unique(grid['x_mm']);y=np.unique(grid['y_mm']);z=np.unique(grid['z_mm'])
    # Same trilinear centre-axis interpolation as the established Java model.
    def weights(depth):
        weight=np.zeros(n);lo=np.searchsorted(z,depth)-1;lo=max(0,min(lo,len(z)-2));t=(depth-z[lo])/(z[lo+1]-z[lo])
        for iz,wz in ((lo,1-t),(lo+1,t)):
            for xx in (x[len(x)//2-1],x[len(x)//2]):
                for yy in (y[len(y)//2-1],y[len(y)//2]):weight[(grid['x_mm']==xx)&(grid['y_mm']==yy)&(grid['z_mm']==z[iz])]=wz/4
        return weight
    basis['weight20']=weights(20);basis['weightcenter']=weights(12.55)
    for f in frequencies:
        field=np.fromfile(folder/f'field-{f}.bin',dtype='<f8').reshape(channels,n,3,2)
        field=field[...,0]+1j*field[...,1]
        contacts=np.genfromtxt(folder/f'contacts-{f}.csv',delimiter=',',names=True)
        density=np.fromfile(folder/f'density-{f}.bin',dtype='<f8').view(np.complex128).reshape(channels,-1)
        loss=np.fromfile(folder/f'loss-{f}.bin',dtype='<f8').view(np.complex128).reshape(6,channels,channels)
        source=np.fromfile(folder/f'source-{f}.bin',dtype='<f8').view(np.complex128).reshape(channels,channels)
        if not all(np.isfinite(v).all() for v in (field,density,loss,source)):raise ValueError('Non-finite transfer basis')
        if not np.allclose(loss,loss.conj().transpose(0,2,1),atol=1e-12):raise ValueError('Non-Hermitian loss matrix')
        for _ in range(3):
            c=np.random.default_rng(_).normal(size=channels)+1j*np.random.default_rng(_+17).normal(size=channels)
            actual=float(np.einsum('i,kij,j->',c.conj(),loss,c).real)
            expected=float(.25*np.vdot(c,source@c).real)
            if abs(actual-expected)>2e-7*max(abs(expected),1e-20):raise ValueError('Combined-source power conservation failed')
        basis['f'][f]={'field':field,'density':density,'loss':loss,'source':source,'contacts':contacts,
            'target':np.einsum('p,cpk->ck',basis['weight20'],field),'center':np.einsum('p,cpk->ck',basis['weightcenter'],field)}
    return basis

def drive_patterns(channels,seed=0):
    if channels==1:return [([0],np.zeros(1))]
    patterns=[];rng=np.random.default_rng(seed)
    # Each distinct partition appears once, fixing channel 0 in carrier group 0.
    for count in sorted(set((channels//2,(channels+1)//2))):
        for group0 in itertools.combinations(range(channels),count):
            if 0 not in group0:continue
            group=np.ones(channels,dtype=int);group[list(group0)]=0
            free=[i for i in range(channels) if i not in (group0[0],int(np.flatnonzero(group==1)[0]))]
            for signs in itertools.product((0,np.pi),repeat=len(free)):
                phase=np.zeros(channels);phase[free]=signs;patterns.append((group.tolist(),phase))
            if free:
                for _ in range(8):
                    phase=np.zeros(channels);phase[free]=rng.uniform(-np.pi,np.pi,len(free));patterns.append((group.tolist(),phase))
    return patterns

def summarize(basis,design,profile,key,h,reference=None,seed=0):
    carrier0=int(design.get('carrier_Hz',2000));beat=int(design.get('beat_Hz',10));carrier1=carrier0+beat
    boundaries=contact_rows(design,profile);frequencies=tuple(basis['f'])
    rows=[];contacts=basis['f'][carrier0]['contacts'];area=contacts['area_m2']
    for group,phase in drive_patterns(design['channels'],seed):
        group=np.asarray(group);phase=np.asarray(phase)
        for wave,(fund,third) in WAVES.items():
            if len(frequencies)==2 and wave!='sine':continue
            spectra={};target_spectra={};loss=np.zeros(6);source_power=0;max_current_sq=np.zeros(design['channels']);j2=np.zeros(len(area));polar2=np.zeros(len(area));charge_bound=np.zeros(len(area))
            for f in frequencies:
                harmonic=1 if f in (carrier0,carrier1) else 3;carrier=0 if f in (carrier0,3*carrier0) else 1
                factor=fund if harmonic==1 else third
                # Coefficients describe sine harmonics, not cosine harmonics.
                c=-1j*(group==carrier)*np.exp(1j*harmonic*phase)*factor
                row=basis['f'][f];j=c@row['density'];e=c@row['target'];spectra[f]=c;target_spectra[f]=e
                loss+=np.einsum('i,kij,j->k',c.conj(),row['loss'],c).real
                source_power+=.25*np.vdot(c,row['source']@c).real
                currents=row['source']@c;max_current_sq+=abs(currents)**2/2
                j2+=abs(j)**2/2
                boundary=next(r for r in boundaries if r['frequency_Hz']==f)
                za=complex(boundary['area_real_ohm_m2'],boundary['area_imag_ohm_m2'])
                polar2+=abs(j*za)**2/2
                charge_bound+=2*abs(j)/(2*np.pi*f)*.1
            target=modulation(target_spectra[carrier0],target_spectra[carrier1])
            jrms=np.sqrt(j2);order=np.argsort(jrms);p95=float(jrms[order][min(np.searchsorted(np.cumsum(area[order]),area.sum()*.95),len(order)-1)])
            metric={'basis_id':key,'layout':design['layout'],'thickness_nm':profile['thickness_nm'],
                'h_mm':h,'pad_size_mm':design['size_mm'],'pad_count':2*design['channels'],'output_channels':design['channels'],
                'waveform':wave,'carrier_group':group.tolist(),'phase_deg':np.rad2deg(phase).tolist(),
                'carrier_Hz':carrier0,'beat_Hz':beat,'boundary_mode':design.get('boundary_mode','measured_minus_Rs'),
                'target20_modulation_V_m':target,'target20_total_E_RMS_V_m':float(np.sqrt(sum(np.vdot(e,e).real for e in target_spectra.values())/2)),
                'surface_J_RMS_max_A_m2':float(jrms.max()),'surface_J_RMS_p95_A_m2':p95,
                'SC_power_W':float(loss[0]),'contact_power_W':float(loss[4]),'skin_power_W':float(loss[0]+loss[4]),
                'tissue_contact_power_W':float(sum(loss[:5])),'source_power_W':float(source_power),
                'max_source_current_RMS_mA':float(np.sqrt(max_current_sq.max())*1000),
                'contact_voltage_RMS_max_V':float(np.sqrt(polar2.max())),
                'charge_excursion_upper_mC_cm2':float(charge_bound.max()),
                'max_residual':basis['validation']['max_residual'],'max_power_error':basis['validation']['max_power_error'],
                'xy_mm':design['xy_mm'],'coating_model_warnings':profile['warnings']}
            if beat==10:metric['target20_TI10_V_m']=target
            if reference:
                scale=min(1,reference['surface_J_RMS_max_A_m2']/max(metric['surface_J_RMS_max_A_m2'],1e-30),
                    math.sqrt(reference['SC_power_W']/max(metric['SC_power_W'],1e-30)),
                    math.sqrt(reference['contact_power_W']/max(metric['contact_power_W'],1e-30)),
                    reference['contact_voltage_RMS_max_V']/max(metric['contact_voltage_RMS_max_V'],1e-30))
                power_scale=min(1,math.sqrt(reference['source_power_W']/max(metric['source_power_W'],1e-30)))
                reference_target=reference.get('target20_modulation_V_m',reference.get('target20_TI10_V_m'))
                metric.update(burden_matched_source_Vpp=scale,target20_at_baseline_burden_V_m=target*scale,
                    equal_power_source_Vpp=power_scale,target20_at_baseline_power_V_m=target*power_scale,
                    gain_at_baseline_burden_percent=(target*scale/reference_target-1)*100)
                metric.update(target20_E_RMS_at_baseline_burden_V_m=metric['target20_total_E_RMS_V_m']*scale,
                    target20_E_RMS_at_baseline_power_V_m=metric['target20_total_E_RMS_V_m']*power_scale,
                    gain_E_RMS_at_baseline_burden_percent=(metric['target20_total_E_RMS_V_m']*scale/reference['target20_total_E_RMS_V_m']-1)*100)
                if target>=reference_target:
                    a=reference_target/target
                    metric.update(equal_target_source_Vpp=a,
                        equal_target_J_ratio=metric['surface_J_RMS_max_A_m2']*a/reference['surface_J_RMS_max_A_m2'],
                        equal_target_skin_power_ratio=metric['skin_power_W']*a*a/reference['skin_power_W'])
            rows.append(metric)
    return rows

def create_run():
    run=ROOT/'runs'/('explore-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    run.mkdir();(run/'cases').mkdir();build_inputs(run/'inputs')
    atomic(run/'state.json',{'status':'prepared','created_utc':datetime.now(timezone.utc).isoformat(),'completed':0,'stage':'screen',
        'assumptions':['Total pad count <=8; at most4 outputs; common ground','0.5 V peak through50 ohm per output',
        '5–20 mm square pads; >=1.25 mm edge gap; all pads on top surface','EIS area-specific boundary scaled by physical pad area',
        'square_3h and triangle_3h are band-limited at6030 Hz, not ideal waveforms','CV does not define a verified CIC/safety threshold']})
    return run

def run_batch(run,limit=12):
    run=Path(run).resolve();compile_solver();profiles=json.loads((run/'inputs/eis-profiles.json').read_text())
    state=json.loads((run/'state.json').read_text());state['status']='running';atomic(run/'state.json',state)
    queue=designs();h=2.5
    source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('TisSweep.java','ExploreBasis.java')}
    source_path=run/'solver-sources.json'
    if source_path.exists() and json.loads(source_path.read_text())!=source_hashes:raise ValueError('Solver source changed: create a new run instead of reusing bases')
    if not source_path.exists():
        atomic(source_path,source_hashes)
        for name in source_hashes:shutil.copy2(ROOT/name,run/'inputs'/name)
    if not (run/'reference.json').exists():
        key,basis=solve_basis(run,queue[0],profiles['0'],h)
        reference=summarize(basis,queue[0],profiles['0'],key,h)[0]
        old=json.loads((ROOT/'gui/dist/current.json').read_text())
        expected=next(d['summary']['target20_V_m'] for d in old['datasets'] if d['scenario']=='ngg_initial' and d['layout']=='a12.5_b12.5_p1' and d['resolution']=='coarse')
        if not math.isclose(reference['target20_TI10_V_m'],expected,rel_tol=2e-7):raise ValueError(f'Prior baseline mismatch {reference["target20_TI10_V_m"]} versus {expected}')
        atomic(run/'reference.json',reference)
    reference=json.loads((run/'reference.json').read_text())
    # Rotate coating and pad count early; later batches finish the full queue.
    default_tasks=[(d,t) for d in queue for t in ('0','50','100','10','30')]
    plan_path=run/'queue.json'
    if not plan_path.exists():
        tasks=default_tasks[:5]
        # Frequency screen on the established geometry, then balanced geometry
        # coverage, before completing the larger design grid.
        for f in (250,500,1000,2000,3000,5000,8000):
            for beat in (5,10,20,50):
                if f==2000 and beat==10:continue
                tasks.extend((dict(queue[0],carrier_Hz=f,beat_Hz=beat),t) for t in ('0','50','100','10','30'))
        covered=set()
        for design in queue[1:]:
            family=(design['channels'],design['size_mm'])
            if family in covered:continue
            covered.add(family);tasks.extend((design,t) for t in ('0','50','100'))
        included={json.dumps([d,t],sort_keys=True) for d,t in tasks}
        tasks.extend((d,t) for d,t in default_tasks[5:] if json.dumps([d,t],sort_keys=True) not in included)
        atomic(plan_path,{'tasks':[{'design':d,'thickness':t,'h_mm':h} for d,t in tasks]})
    planned=json.loads(plan_path.read_text())['tasks']
    tasks=[(task['design'],task['thickness']) for task in planned]
    complete=set(json.loads(p.read_text())['task_key'] for p in (run/'cases').glob('*.json'))
    rejected=run/'rejections';rejected.mkdir(exist_ok=True)
    complete.update(p.stem for p in rejected.glob('*.json'))
    performed=0
    for index in sorted(range(len(tasks)),key=lambda i:(planned[i].get('priority',10),i)):
        design,thickness=tasks[index]
        task_key=f'{index:05d}'
        if task_key in complete:continue
        h=float(planned[index].get('h_mm',2.5))
        if not mesh_representable(design,h):
            atomic(rejected/f'{task_key}.json',{'task_key':task_key,'reason':'Physical pad area would be clipped by the cylindrical mesh at this resolution','design':design,'h_mm':h})
            performed+=1;state['completed']=len(complete)+performed;atomic(run/'state.json',state)
            print(f'REJECT {task_key}: pad area not fully represented at h={h}',flush=True)
            if performed>=limit:break
            continue
        if h!=2.5:
            ref_path=run/f'reference-h{h:g}.json'
            if not ref_path.exists():
                ref_key,ref_basis=solve_basis(run,queue[0],profiles['0'],h)
                fine_ref=summarize(ref_basis,queue[0],profiles['0'],ref_key,h)[0]
                if h==1.25:
                    if not math.isclose(fine_ref['target20_modulation_V_m'],2.95184754429,rel_tol=2e-7):raise ValueError('Prior fine baseline mismatch')
                atomic(ref_path,fine_ref)
            reference=json.loads(ref_path.read_text())
        else:reference=json.loads((run/'reference.json').read_text())
        state.update(current_task=task_key,layout=design['layout'],pad_count=2*design['channels'],thickness_nm=int(thickness),updated_utc=datetime.now(timezone.utc).isoformat())
        atomic(run/'state.json',state)
        key,basis=solve_basis(run,design,profiles[thickness],h)
        rows=summarize(basis,design,profiles[thickness],key,h,reference,index)
        for row in rows:
            row['stage']=planned[index].get('stage','screen')
            row['reference_h_mm']=h
            row['reference_modulation_V_m']=reference.get('target20_modulation_V_m',reference.get('target20_TI10_V_m'))
        atomic(run/'cases'/f'{task_key}.json',{'task_key':task_key,'design':design,'candidates':rows,'validation':basis['validation']})
        performed+=1;state['completed']=len(complete)+performed
        state['candidate_count']=sum(len(json.loads(p.read_text())['candidates']) for p in (run/'cases').glob('*.json'))
        atomic(run/'state.json',state)
        print(f'CASE {state["completed"]}/{len(tasks)} pads={2*design["channels"]} size={design["size_mm"]} PEDOT={thickness} freq={design.get("carrier_Hz",2000)}+{design.get("beat_Hz",10)} best_TI={max(r["target20_modulation_V_m"] for r in rows):.5g} burden_matched={max(r["target20_at_baseline_burden_V_m"] for r in rows):.5g}',flush=True)
        if performed>=limit:break
    state.update(status='batch_complete',queue_size=len(tasks),updated_utc=datetime.now(timezone.utc).isoformat())
    if state['completed']>=len(tasks):state['status']='screen_complete'
    atomic(run/'state.json',state)
    return state

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run');parser.add_argument('--limit',type=int,default=12);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    run=Path(args.run) if args.run else create_run();print('RUN',run,flush=True)
    if not args.prepare:print(json.dumps(run_batch(run,args.limit),ensure_ascii=False,indent=2))
