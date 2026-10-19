"""Finite preregistered fixed-phantom shape/ROI experiment, never a resident worker.

Preparation freezes geometry masks, configs, private numerical code and resource
limits before publication. Execution is sequential with no retries, keeps failed
and partial artifacts, and never changes original workers/results/GUI pointers.
"""
from pathlib import Path
from datetime import datetime, timezone
from contextlib import ExitStack
import argparse
import copy
import csv
import fcntl
import gc
import hashlib
import json
import math
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
GIB = 1024**3
SOURCE_RUN = ROOT/'runs/rs-window-tis-validation-20261019T135413Z'
SOURCE_CONFIG = SOURCE_RUN/'configs/coat010-f0500-minusRs.properties'
SOURCE_CASE = SOURCE_RUN/'cases/coat010-f0500-minusRs.json'
SOURCE_CONFIG_SHA = 'ebd3fa7a62ceeb9e769a32c3e9217ede10548d0b31059cab09287684d892f773'
SOURCE_CASE_SHA = '9e96bb3a298e94678ccac1a871a5c232449da01ec2bc79ddd14407c7924c1dde'
JDK = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
LIMITS = dict(max_cells=800000, per_case_seconds=600, total_seconds=6600,
              max_aggregate_rss_bytes=3*GIB, java_heap='2g', java_active_processors=1,
              java_gc='SerialGC', simultaneous_jobs=1, minimum_free_disk_bytes=2*GIB)
MESHES = {'coarse':(1.25,2,[14,14,40]), 'xy80':(.625,2,[14,14,40]),
          'xy100':(.5,2,[14,14,40]), 'sc4':(.625,4,[14,14,40]),
          'bulk':(.625,2,[18,18,56])}
CODE_FILES = ('selectivity_design.py','SelectivityShapeBasis.java','selectivity_geometry.py',
              'selectivity_volume.py','selectivity_postprocess.py','analyze_selectivity_design.py','test_selectivity_geometry.py',
              'test_selectivity_volume.py','test_selectivity_design.py','test_selectivity_postprocess.py','TisSweep.java','ExploreBasis.java',
              'explore_tis.py','explore_inputs.py','fit_ngg_eis.py','update_ngg_eis.py',
              'leader_spatial_diagnostics.py','layered_probe_analysis.py','native_probe_followup.py')
NUMERICAL_GATES = dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,
                      max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7)
CONVERGENCE_PERCENT = dict(target20_modulation_V_m=1,target20_total_E_RMS_V_m=1,
 roi_mean_TIS_V_m=1,roi_p10_TIS_V_m=1,roi_mean_RMS_V_m=1,target_superficial_p95_ratio=1,
 surface_J_RMS_max_A_m2=5,surface_J_RMS_p95_A_m2=5,contact_voltage_RMS_max_V=5,
 SC_power_W=2,contact_power_W=2,source_power_W=2)


def now(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text())
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def atomic(path,obj):
    path=Path(path); temp=path.with_name(path.name+'.partial')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    os.replace(temp,path)
def require(ok,msg):
    if not ok: raise ValueError(msg)
def ticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
def physical_processes():
    result=[]
    markers=('explore_controller.py','companion_controller.py','mesh_validation.py',
      'coating_rs_validation.py','rs_window_tis_validation.py','selectivity_design.py')
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:
            args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            state=(p/'stat').read_text().rsplit(')',1)[1].split()[0]
            if state=='Z':continue
            if any(any(Path(arg).name==m for m in markers) for arg in args):
                result.append(dict(pid=int(p.name),startticks=ticks(int(p.name)),state=state,argv=args))
        except (OSError,ValueError):pass
    return result

def check_stop(run):
    for name in ('STOP','needs_attention','needs_physical_validation'):
        if (Path(run)/name).exists():raise ExperimentStop('user_stopped',name)
def check_pins(pins):
    for p,v in pins.items():require(sha(p)==v,'Frozen file changed: '+p)

def check_fresh_run(run):
    run=Path(run)
    require(read(run/'summary.json')['status']=='prepared','No completed/partial/failed run restart')
    require(read(run/'controller.json')['status']=='prepared','Controller has execution history; no restart')
    require(not (run/'execution-attempt.json').exists() and not (run/'failure.json').exists(),'Prior execution attempt/failure must be preserved')
    for d in ('cases','bases','postprocess'):
        require(not any((run/d).iterdir()),'Partial/completed artifacts present: '+d)

def check_publication(run, publication):
    commit=publication.get('commit_sha','')
    require(publication.get('status')=='published_verified' and publication.get('remote_ref_verified') is True
            and isinstance(commit,str) and len(commit)==40 and all(c in '0123456789abcdef' for c in commit)
            and publication.get('preregistration_sha256')==sha(run/'preregistration.json')
            and publication.get('manifest_sha256')==sha(run/'manifest.json'),
            'Verified preexecution publication required')
def mesh_meta(h,sc,bulk):
    nx=round(50/h);require(abs(nx*h-50)<1e-10,'XY must tile fixed diameter')
    nxy=sum((-25+(i+.5)*h)**2+(-25+(j+.5)*h)**2<625 for j in range(nx) for i in range(nx))
    cells=nxy*(sc+sum(bulk));require(cells<=800000,'800000 cell cap')
    return dict(h_xy_mm=h,sc_cells=sc,bulk_counts=bulk,cells=cells,nx=nx,
      volume_metadata=dict(h_xy_mm=h,sc_cells=sc,bulk_layer_counts=bulk,layer_counts=[sc,*bulk],
        radius_mm=25,geometry_volume_tolerance_relative=.01 if h==1.25 else .002,
        target_volume_tolerance_relative=.001))

def controls_for(design,pair):
    d=copy.deepcopy(design);c=len(d['pads'])//2
    d['pads']=[d['pads'][pair],d['pads'][pair+c]]
    for k,p in enumerate(d['pads']):
        p['original_source_pad']=p['pad'];p['original_source_output']=p.get('source_output')
        p['pad']=k;p['role']='signal' if k==0 else 'common_gnd_return';p['source_output']=0 if k==0 else None
    d.update(source_outputs=1,total_pads=2,control_for_design=design['id'],indexed_pair=pair,
             id=design['id']+f'-C1pair{pair}')
    return d

def prepare(run):
    preparation_started=time.monotonic()
    import selectivity_geometry as geom
    run=Path(run).resolve();require(run.parent==ROOT/'runs' and run.name.startswith('selectivity-design-'),'Separate run required')
    require((run/'ANALYSIS_PLAN.md').is_file(),'Write analysis plan before preparation')
    require(not (run/'manifest.json').exists(),'Preserve previous prepared/partial run')
    check_stop(run);require(not physical_processes(),'Actual research process active; do not duplicate')
    source_case=read(SOURCE_CASE);require(source_case.get('status')=='complete','Current Best1 not complete')
    require(sha(SOURCE_CASE)==SOURCE_CASE_SHA,'Pinned published Best1 case bytes changed')
    require(sha(SOURCE_CONFIG)==SOURCE_CONFIG_SHA==source_case['config_sha256'],'Best1 exact config/case join failed')
    require(Path(source_case['config_file']).resolve()==SOURCE_CONFIG.resolve(),'Best1 config path differs')
    post=source_case['postprocess'];require(post['status']=='complete' and post['native_probe_status']=='complete' and post['spatial_status']=='complete','Best1 source postprocessing incomplete')
    require(sha(post['path'])==post['sha256'],'Best1 original numerical postprocess SHA differs')
    initial_free=shutil.disk_usage(run).free;require(initial_free>=2*GIB,'Disk reserve unavailable')
    config={}
    for line in SOURCE_CONFIG.read_text().splitlines():
        if line and not line.startswith('#'):k,v=line.split('=',1);config[k]=v
    codes={str(ROOT/f):sha(ROOT/f) for f in CODE_FILES}
    for f in ('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java'):shutil.copy2(ROOT/f,run/'private-src'/f)
    designs=geom.designs();atomic(run/'inputs/designs.json',designs)
    proposals=[]
    for d in geom.proposed_rejections():
        try: verdict=geom.validate_design(d)
        except Exception as e:verdict=dict(status='rejected_geometry',error=str(e))
        proposals.append(dict(design=d,preparation_verdict=verdict))
    atomic(run/'inputs/original-proposals-preserved.json',proposals)
    masks={}; cases={}; rejection=[]
    # All possible refinement/C1 config bytes are frozen, but only bounded
    # deterministic selected branches may execute.
    for d in designs:
        for mesh_id,(h,sc,bulk) in MESHES.items():
            key=d['id']+f'-{mesh_id}'
            mask_key=d['id']+f'-h{h:g}'
            if mask_key not in masks:
                result=geom.mask(d,h)
                if result.get('status')!='valid_contact_mask':
                    rejection.append(dict(case_id=key,geometry=result));continue
                contact_rows=result['contacts']; path=run/'masks'/f'{mask_key}.csv'
                with path.open('w',newline='') as out:
                    w=csv.writer(out,lineterminator='\n');w.writerow(['pad','i','j','area_m2'])
                    for row in contact_rows:
                        if isinstance(row,dict):w.writerow([row['pad'],row['i'],row['j'],format(row['area_m2'],'.17g')])
                        else:w.writerow(row)
                masks[mask_key]=dict(path=str(path),sha256=sha(path),audit=result)
            if mask_key not in masks:continue
            mm=masks[mask_key]
            expected=[geom.polygon_area(p['polygon_mm'])*1e-6 for p in d['pads']]
            values={k:v for k,v in config.items() if not k.startswith('pad.') and k!='size_mm'}
            values.update(h_mm=repr(h),channels='2',**{'validation.sc_cells':str(sc),
              'bulk.counts':','.join(map(str,bulk)),'mask.path':mm['path'],'mask.sha256':mm['sha256']})
            for e,area in enumerate(expected):
                values[f'pad.{e}.represented_area_m2']=format(area,'.17g')
                for k in ('shape','width_mm','height_mm','rotation_deg','analytic_area_mm2'):values[f'pad.{e}.'+k]=str(d['pads'][e][k])
                values[f'pad.{e}.x_mm']=str(d['pads'][e]['center_mm'][0]);values[f'pad.{e}.y_mm']=str(d['pads'][e]['center_mm'][1])
            path=run/'configs'/f'{key}.properties';path.write_text(''.join(f'{k}={v}\n' for k,v in values.items()))
            cases[key]=dict(id=key,design_id=d['id'],mesh_id=mesh_id,config_file=str(path),config_sha256=sha(path),
              mask_file=mm['path'],mask_sha256=mm['sha256'],expected_pad_areas_m2=expected,channels=2,
              **mesh_meta(h,sc,bulk))
        # Actual two-pad controls are frozen only at the common refined h=.625.
        for pair in (0,1):
            cd=controls_for(d,pair);result=geom.mask(cd,.625)
            if result.get('status')!='valid_contact_mask':
                rejection.append(dict(case_id=cd['id'],geometry=result));continue
            key=cd['id']+'-xy80';path=run/'masks'/f'{key}.csv'
            with path.open('w',newline='') as out:
                w=csv.writer(out,lineterminator='\n');w.writerow(['pad','i','j','area_m2'])
                for row in result['contacts']:
                    if isinstance(row,dict):w.writerow([row['pad'],row['i'],row['j'],format(row['area_m2'],'.17g')])
                    else:w.writerow(row)
            expected=[geom.polygon_area(p['polygon_mm'])*1e-6 for p in cd['pads']]
            values={k:v for k,v in config.items() if not k.startswith('pad.') and k!='size_mm'}
            values.update(h_mm='.625',channels='1',**{'validation.sc_cells':'2','bulk.counts':'14,14,40',
              'mask.path':str(path),'mask.sha256':sha(path)})
            for e,a in enumerate(expected):
                values[f'pad.{e}.represented_area_m2']=format(a,'.17g')
                for k in ('shape','width_mm','height_mm','rotation_deg','analytic_area_mm2'):values[f'pad.{e}.'+k]=str(cd['pads'][e][k])
                values[f'pad.{e}.x_mm']=str(cd['pads'][e]['center_mm'][0]);values[f'pad.{e}.y_mm']=str(cd['pads'][e]['center_mm'][1])
            cfg=run/'configs'/f'{key}.properties';cfg.write_text(''.join(f'{k}={v}\n' for k,v in values.items()))
            cases[key]=dict(id=key,design_id=d['id'],control_design=cd,indexed_pair=pair,mesh_id='xy80',channels=1,
              config_file=str(cfg),config_sha256=sha(cfg),mask_file=str(path),mask_sha256=sha(path),
              expected_pad_areas_m2=expected,**mesh_meta(.625,2,[14,14,40]))
    original_folder=Path(source_case['basis_dir']);original_files={p.name:sha(p) for p in original_folder.iterdir() if p.is_file()}
    for p,v in source_case['output_hashes'].items():
        original=Path(p) if Path(p).is_absolute() else original_folder/p
        require(sha(original)==v,'Published original Best1 output changed: '+str(original))
    reference_pins=dict(source_case_path=str(SOURCE_CASE),source_case_sha256=sha(SOURCE_CASE),
      source_postprocess_path=source_case['postprocess']['path'],source_postprocess_sha256=source_case['postprocess']['sha256'],
      config_sha256=SOURCE_CONFIG_SHA,basis_input_sha256=original_files)
    cases['reference-best1-final']=dict(id='reference-best1-final',design_id='baseline-square15',mesh_id='original_xy120',
      channels=2,existing_reference=True,expected_source_exporter='RsWindowTisBasis',existing_reference_pins=reference_pins,
      source_original_case=str(SOURCE_CASE),
      config_file=str(SOURCE_CONFIG),config_sha256=SOURCE_CONFIG_SHA,source_basis_dir=str(original_folder),
      expected_pad_areas_m2=[.000225]*4,**mesh_meta(50/120,2,[14,14,40]))
    atomic(run/'inputs/geometry-audits.json',dict(masks=masks,rejections=rejection))
    pre=dict(schema='fixed-phantom-selectivity-preregistration-v1',created_utc=now(),
      authorization='작업1: 고정팬텀의15–20mm TIS 선택성·표층부담 전극설계 탐색을단계별한정수행',
      existing_current20mm_1Vpp_objective_preserved=True,analysis_plan_sha256=sha(run/'ANALYSIS_PLAN.md'),
      current_best1=dict(run_id=SOURCE_RUN.name,candidate_id='coat010-f0500-minusRs-square_3h',
        source_result_commit='947c984f9a154d750acf36379fc859b25b56ac4f',case_sha256=sha(SOURCE_CASE),config_sha256=sha(SOURCE_CONFIG)),
      physical_phantom=dict(diameter_mm=50,layer_thicknesses_mm=[.1,5,5,15],insulating_side_bottom=True),
      common_condition=dict(coating_nm=10,Rs_fit_nominal_lower_Hz=500,source_Vpp_each=1,source_ohm=50,
        phase_deg=[0,0],carrier_Hz=[3000,3030],harmonics_Hz=[9000,9090],primary_waveform='square_3h'),
      resource_limits=LIMITS,numerical_gates=NUMERICAL_GATES,convergence_percent=CONVERGENCE_PERCENT,
      case_pool=cases,maximum_actual_new_PDE_conditions=25,existing_Best1_new_ROI_reference_count=1,maximum_ledger_cases=26,maximum_TIS_conditions=19,maximum_true_2pad_control_bases=6,
      initial_coarse_case_ids=[d['id']+'-coarse' for d in designs if d['id']+'-coarse' in cases],
      deterministic_selection=dict(first='max Pareto target P10',second='max Pareto target mean / superficial P95; if duplicate next Pareto absolute mean',
        refined_champion='largest min(relative ROI P10, relative target/superficial-P95 ratio); tie absolute P10'),
      failure_policy='No retries. Stop current batch on numerical/postprocess failure; retain completed/partial/failed and mark remaining not_run. No cap/threshold relaxation.',
      initial_available_bytes=initial_free,
      raw_storage_upper_estimate=dict(bytes_per_cell_2channel=600,bytes_per_cell_1channel=340,
        coarse_10_max=10*600*mesh_meta(1.25,2,[14,14,40])['cells'],
        note='Native fields/potential/grid stream directly to lossless gzip; actual ratio unknown. Require per-case raw bound plus2GiB before each execution.'),
      original_exploration_physical_hold_preserved=True,old_GUI_pointers_unchanged=True,
      original_model_monitoring_usage_settings_unchanged=True,code_sha256=codes)
    atomic(run/'preregistration.json',pre)
    pins={**codes,str(SOURCE_CONFIG):sha(SOURCE_CONFIG),str(SOURCE_CASE):sha(SOURCE_CASE),str(Path(source_case['postprocess']['path'])):source_case['postprocess']['sha256']}
    for filename,value in original_files.items():pins[str(original_folder/filename)]=value
    # Original frozen numerical inputs and new prepared files are immutable pins.
    for p in [run/'ANALYSIS_PLAN.md',run/'preregistration.json',*(run/'inputs').glob('*.json'),*(run/'configs').glob('*'),*(run/'masks').glob('*'),*(run/'private-src').glob('*')]:
        pins[str(p)]=sha(p)
    cmd=[str(JDK/'javac'),'-encoding','UTF-8','-d',str(run/'classes'),*[str(p) for p in (run/'private-src').glob('*.java')]]
    compile_started=time.monotonic()
    subprocess.run(cmd,check=True,stdout=(run/'logs/compile.log').open('w'),stderr=subprocess.STDOUT,timeout=120)
    selftest=[str(JDK/'java'),'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'SelectivityShapeBasis','--selftest']
    subprocess.run(selftest,check=True,stdout=(run/'logs/selftest.log').open('w'),stderr=subprocess.STDOUT,timeout=120)
    for p in (run/'classes').glob('*.class'):pins[str(p)]=sha(p)
    m=dict(schema='fixed-phantom-selectivity-execution-v1',status='prepared',output_run=str(run),java=str(JDK/'java'),
      classes=str(run/'classes'),preregistration_sha256=sha(run/'preregistration.json'),guard_hashes=pins,
      preparation_compile_selftest_seconds=time.monotonic()-compile_started,
      preparation_wall_seconds=time.monotonic()-preparation_started,
      actual_preparation_PDE_jobs=0,actual_field_postprocess_jobs=0)
    atomic(run/'manifest.json',m)
    atomic(run/'controller.json',dict(status='prepared',created_utc=now(),new_PDE_jobs=0))
    atomic(run/'summary.json',dict(status='prepared',cases=[],unexecuted_case_pool=list(cases),new_PDE_jobs=0))
    print(json.dumps(dict(run=str(run),status='prepared',case_pool=len(cases),initial_coarse=len(pre['initial_coarse_case_ids']),new_PDE_jobs=0)))


class ExperimentStop(RuntimeError):
    def __init__(self,status,message):super().__init__(message);self.status=status

def process_rss(pid):
    try:
        x=dict(r.split(':',1) for r in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in r)
        return int(x.get('VmRSS','0 kB').split()[0])*1024
    except OSError:return 0

def execute(run):
    entry_started=time.monotonic()
    run=Path(run).resolve();m=read(run/'manifest.json');pre=read(run/'preregistration.json')
    require(m['status']=='prepared' and m['output_run']==str(run),'Invalid prepared run')
    require(sha(run/'preregistration.json')==m['preregistration_sha256'],'Preregistration changed')
    require(pre['resource_limits']==LIMITS and pre['numerical_gates']==NUMERICAL_GATES,'Caps/gates changed')
    check_pins(m['guard_hashes']);check_stop(run)
    require(not physical_processes(),'Live research worker present')
    publication=read(run/'execution-publication.json')
    check_publication(run,publication)
    check_fresh_run(run)
    from selectivity_postprocess import process_case
    designs={d['id']:d for d in read(run/'inputs/designs.json')}
    preparation_seconds=float(m['preparation_wall_seconds'])
    require(math.isfinite(preparation_seconds) and 0<=preparation_seconds<6600,'Invalid preparation budget')
    began=entry_started;deadline=entry_started+6600-preparation_seconds;pid=os.getpid();start=ticks(pid)
    state=dict(status='running',pid=pid,proc_start_ticks=start,started_utc=now(),current_case='',current_config_sha256='',phase='starting')
    summary=dict(status='running',started_utc=now(),cases=[],new_PDE_jobs=0,source_result_versions=[],selected_coarse=[],refined_champion=None,
                 preparation_wall_seconds=preparation_seconds,total_budget_includes_preparation_and_entry_checks=True)
    shared=Path(tempfile.gettempdir())/f'ngg-mesh-validation-{os.getuid()}.lock'
    cpu=min(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    def alarm(*_):
        if time.monotonic()>=deadline:raise ExperimentStop('total_timeout','6600s total including postprocessing')
        raise ExperimentStop('case_timeout','600s condition including postprocessing')
    signal.signal(signal.SIGALRM,alarm)
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(ExperimentStop('interrupted','SIGTERM')))
    signal.signal(signal.SIGINT,lambda *_:(_ for _ in ()).throw(ExperimentStop('interrupted','SIGINT')))
    launched=None;active=None;finished=set();post_guard_error=[None]
    def post_guard_signal(*_):
        error=post_guard_error[0]
        if error is not None:raise error
    signal.signal(signal.SIGUSR1,post_guard_signal)
    with ExitStack() as stack:
        for path in (shared,run/'.execution.lock'):
            f=stack.enter_context(path.open('a+'));fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        check_pins(m['guard_hashes'])
        with (run/'execution-attempt.json').open('x') as attempt:
            json.dump(dict(started_utc=now(),pid=pid,proc_start_ticks=start,automatic_restart=False),attempt)
            attempt.write('\n')
        def flush():
            state['updated_utc']=now();atomic(run/'controller.json',state)
            summary['updated_utc']=now();atomic(run/'summary.json',summary)
        def perform(ident):
            nonlocal launched,active
            require(ident not in finished,'Do not repeat a physical condition')
            require(len(summary['cases'])<26,'Finite maximum25 new conditions plus1 existing reference')
            check_stop(run);check_pins(m['guard_hashes'])
            if time.monotonic()>=deadline:raise ExperimentStop('total_timeout','6600s total')
            c=copy.deepcopy(pre['case_pool'][ident]);c['design']=copy.deepcopy(c.get('control_design') or designs[c['design_id']])
            c['design']['channels']=c['channels'];c['design']['xy_mm']=[p['center_mm'] for p in c['design']['pads']]
            c['source_run_id']=run.name;c['source_coating_nm']=10;c['source_Rs_fit_window_Hz']=500
            raw=0 if c.get('existing_reference') else c['cells']*(600 if c['channels']==2 else 340)
            if shutil.disk_usage(run).free<2*GIB+raw:raise ExperimentStop('disk_budget_not_run',f'{ident}: need reserve+raw bound {2*GIB+raw}')
            active=c;state.update(current_case=ident,current_config_sha256=c['config_sha256'],phase='solving')
            atomic(run/'cases'/f'{ident}.json',dict(c,status='running',started_utc=now()));flush()
            t=time.monotonic();signal.setitimer(signal.ITIMER_REAL,min(600,deadline-t));rss_peak=process_rss(pid)
            if c.get('existing_reference'):
                folder=Path(c['source_basis_dir'])
                summary['existing_Best1_ROI_reference_reused']=True
            else:
                command=[m['java'],'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',m['classes'],
                         'SelectivityShapeBasis','--execute-parent',str(pid),str(start),c['config_file'],str(run/'bases'/ident)]
                with (run/'logs'/f'{ident}.log').open('w') as log:
                    launched=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
                    summary['new_PDE_jobs']+=1
                    state['java_pid']=launched.pid;state['java_startticks']=ticks(launched.pid);state['java_argv']=command;flush()
                    atomic(run/'audit'/f'{ident}-process-start.json',dict(observed_utc=now(),parent=state.copy(),
                      actual_java_cmdline=Path(f'/proc/{launched.pid}/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),
                      shared_lock=str(shared),execution_lock=str(run/'.execution.lock'),cpu_affinity=sorted(os.sched_getaffinity(pid))))
                    while launched.poll() is None:
                        check_stop(run)
                        if time.monotonic()>deadline:raise ExperimentStop('total_timeout','6600s')
                        rss=process_rss(pid)+process_rss(launched.pid);rss_peak=max(rss_peak,rss)
                        if rss>3*GIB:raise ExperimentStop('rss_limit','Aggregate RSS3GiB')
                        if shutil.disk_usage(run).free<2*GIB:raise ExperimentStop('disk_reserve','Reserve2GiB')
                        time.sleep(.2)
                    code=launched.returncode;launched=None
                    if code:raise ExperimentStop('solver_failed',f'Java exit{code}')
                folder=run/'bases'/ident
            require((folder/'BASIS_COMPLETE').is_file(),'Missing completed basis')
            v=read(folder/'validation.json')
            for k,l in NUMERICAL_GATES.items():
                if k=='max_interface_normal_current_relative_error' and c.get('existing_reference'):continue
                require(math.isfinite(v[k]) and 0<=v[k]<=l,'Numerical gate:'+k)
            state.update(phase='postprocessing',java_pid=None);flush()
            stop_guard=threading.Event()
            def guard_postprocessing():
                nonlocal rss_peak
                while not stop_guard.wait(.2):
                    try:
                        check_stop(run)
                        current_rss=process_rss(pid);rss_peak=max(rss_peak,current_rss)
                        if current_rss>3*GIB:raise ExperimentStop('rss_limit','Postprocessing RSS3GiB')
                        if shutil.disk_usage(run).free<2*GIB:raise ExperimentStop('disk_reserve','Postprocessing reserve2GiB')
                        if time.monotonic()>=deadline:raise ExperimentStop('total_timeout','6600s total')
                    except ExperimentStop as error:
                        post_guard_error[0]=error;os.kill(pid,signal.SIGUSR1);return
            post_guard_error[0]=None
            guard=threading.Thread(target=guard_postprocessing,name='finite-case-resource-guard',daemon=True)
            guard.start()
            try:result=process_case(folder,c,run/'postprocess'/ident,min(deadline,t+600))
            finally:stop_guard.set();guard.join(timeout=1)
            require(result.get('status')=='complete','Postprocessing incomplete/held; not promote')
            gc.collect();rss_peak=max(rss_peak,process_rss(pid));require(rss_peak<=3*GIB,'Postprocess RSS cap')
            check_pins(m['guard_hashes']);check_stop(run)
            record=dict(c,status='complete',validation=v,postprocess=dict(status='complete',path=str(run/'postprocess'/ident/'summary.json'),
                sha256=sha(run/'postprocess'/ident/'summary.json')),resources=dict(wall_seconds=time.monotonic()-t,peak_sampled_aggregate_rss_bytes=rss_peak,rss_sampling_seconds=.2),
                basis_file_sha256={p.name:sha(p) for p in folder.iterdir() if p.is_file()})
            atomic(run/'cases'/f'{ident}.json',record)
            summary['cases'].append(dict(id=ident,status='complete',design_id=c['design_id'],mesh_id=c['mesh_id'],channels=c['channels'],postprocess=record['postprocess'],resources=record['resources']))
            summary['source_result_versions'].append(dict(case_id=ident,config_sha256=c['config_sha256'],result_sha256=sha(run/'cases'/f'{ident}.json')))
            finished.add(ident);signal.setitimer(signal.ITIMER_REAL,0);active=None;flush()
            print('COMPLETE',ident,record['resources'],flush=True)
            return result
        try:
            flush();results={}
            results['reference-best1-final']=perform('reference-best1-final')
            for ident in pre['initial_coarse_case_ids']:results[ident]=perform(ident)
            selected=select_candidates(results,pre['initial_coarse_case_ids'])
            summary['selected_coarse']=selected;atomic(run/'selection-coarse.json',dict(status='selected',selected_design_ids=selected,rule=pre['deterministic_selection'],observed_utc=now()));flush()
            for d in ['baseline-square15',*selected]:
                ident=d+'-xy80'
                if ident in pre['case_pool']:results[ident]=perform(ident)
            champion=select_champion(results,selected)
            summary['refined_champion']=champion;atomic(run/'selection-refined.json',dict(champion=champion,selected=selected,observed_utc=now()));flush()
            for mesh in ['xy100','sc4','bulk']:
                for d in ['baseline-square15',champion]:
                    ident=d+'-'+mesh
                    if ident in pre['case_pool']:results[ident]=perform(ident)
            for d in ['baseline-square15',*selected]:
                for pair in (0,1):
                    ident=d+f'-C1pair{pair}-xy80'
                    if ident in pre['case_pool']:results[ident]=perform(ident)
            summary.update(status='complete',finished_utc=now(),wall_seconds=time.monotonic()-began)
            state.update(status='complete',phase='finished',current_case=None,current_config_sha256=None)
        except BaseException as error:
            signal.setitimer(signal.ITIMER_REAL,0)
            if launched is not None and launched.poll() is None:
                try:os.killpg(launched.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                try:launched.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:os.killpg(launched.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    launched.wait(timeout=5)
            status=error.status if isinstance(error,ExperimentStop) else ('total_timeout' if time.monotonic()>=deadline else 'case_timeout') if isinstance(error,TimeoutError) else 'postprocessing_failed' if state.get('phase')=='postprocessing' else 'validation_failed'
            failed_phase=state.get('phase')
            summary.update(status=status,error=str(error),error_type=type(error).__name__,failed_case=active['id'] if active else None,wall_seconds=time.monotonic()-began)
            state.update(status=status,phase='stopped')
            if active:
                atomic(run/'cases'/f"{active['id']}-failure.json",dict(case_id=active['id'],status=status,error=str(error),phase=failed_phase,observed_utc=now(),partial_basis_preserved=True,automatic_retry=False))
            atomic(run/'failure.json',summary)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            summary['never_executed_pool_case_ids']=[k for k in pre['case_pool'] if k not in finished and (not active or k!=active['id'])]
            flush()
    print(json.dumps(dict(status=summary['status'],completed=len(summary['cases']),new_PDE_jobs=summary['new_PDE_jobs'],wall_seconds=summary.get('wall_seconds'))),flush=True)
    return 0 if summary['status']=='complete' else 2


def selection_values(result):
    # Postprocessor documents the same canonical flat square_3h selection keys.
    return result['selection_metrics']
def pareto(items):
    result=[]
    for key,a in items:
        aa=selection_values(a);vec=[aa['roi_p10_TIS_V_m'],aa['roi_mean_TIS_V_m'],aa['target_superficial_p95_ratio'],-aa['surface_J_RMS_max_A_m2'],-aa['source_power_W']]
        dominated=False
        for other,b in items:
            if other==key:continue
            bb=selection_values(b);v=[bb['roi_p10_TIS_V_m'],bb['roi_mean_TIS_V_m'],bb['target_superficial_p95_ratio'],-bb['surface_J_RMS_max_A_m2'],-bb['source_power_W']]
            if all(x>=y for x,y in zip(v,vec)) and any(x>y for x,y in zip(v,vec)):dominated=True;break
        if not dominated:result.append(key)
    return result

def select_candidates(results,ids):
    eligible=[(k,results[k]) for k in ids if k in results and not k.startswith('baseline-square15')]
    require(eligible,'No valid non-baseline candidates')
    pool=pareto(eligible)
    first=max(pool,key=lambda k:(selection_values(results[k])['roi_p10_TIS_V_m'],selection_values(results[k])['roi_mean_TIS_V_m'],k))
    second=max(pool,key=lambda k:(selection_values(results[k])['target_superficial_p95_ratio'],selection_values(results[k])['roi_mean_TIS_V_m'],k))
    selected=[first]
    if second==first:
        alternatives=[k for k in pool if k!=first]
        if alternatives:second=max(alternatives,key=lambda k:(selection_values(results[k])['roi_mean_TIS_V_m'],k))
    if second not in selected:selected.append(second)
    return [k.removesuffix('-coarse') for k in selected]

def select_champion(results,selected):
    b=selection_values(results['baseline-square15-xy80'])
    valid=[d for d in selected if d+'-xy80' in results];require(valid,'No refined candidate')
    def score(d):
        m=selection_values(results[d+'-xy80'])
        return (min(m['roi_p10_TIS_V_m']/b['roi_p10_TIS_V_m'],m['target_superficial_p95_ratio']/b['target_superficial_p95_ratio']),m['roi_p10_TIS_V_m'],d)
    return max(valid,key=score)


def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--prepare',action='store_true');g.add_argument('--execute',action='store_true');parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[name]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    if a.prepare:prepare(a.output);return 0
    return execute(a.output)
if __name__=='__main__':sys.exit(main())
