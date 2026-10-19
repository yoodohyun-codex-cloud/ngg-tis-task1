"""One finite Rs-window TIS run: ten semantic slots, eight new solves, one reused basis.

Preparation compiles only private code and runs analytic/config guards. Actual
PDE and field postprocessing require the exact prepublished execution receipt.
All original modules, inputs, results, workers and GUI pointers stay untouched.
"""
from pathlib import Path
import argparse, copy, fcntl, gc, gzip, hashlib, json, math, os, re, shutil, signal, sys, time
if '--execute' in sys.argv:
    for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[_name]='1'
    if hasattr(os,'sched_getaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import mesh_validation as common
from mesh_validation_3k import LIMITS, NUMERICAL, FREQUENCIES, now, startticks
from explore_tis import ROOT, JAVAC, atomic, config_text, contact_rows, load_basis, summarize, WAVES
from validation_3k_postprocess import analyze_case

PREPARATION=ROOT/'runs/eis-rs-window-tis-preparation-20261019T124509Z'
PREP_SHA='d0f15e16ae9afa41562d8a25a4add1f84c5e7584e81cb5ba06cfd9e8df90917a'
MANIFEST_SHA='236af268f12bcb27add5641be2273f1aa7bbda6d2f764f3e4eb18866e4c7b7b5'
SOURCE_RESULT_COMMIT='272fc201b6db11be7add05298b8de63ae2325f51'
AUTHORIZATION='시뮬레이션 계속 돌려봐 변수 알아서 바꿔서'
SOURCES=('TisSweep.java','ExploreBasis.java','RsWindowTisBasis.java')
DEPENDENCIES=('rs_window_tis_validation.py','mesh_validation.py','mesh_validation_3k.py',
 'explore_tis.py','explore_inputs.py','fit_ngg_eis.py','update_ngg_eis.py','validation_3k_postprocess.py',
 'leader_spatial_diagnostics.py','layered_probe_analysis.py','native_probe_followup.py')
TESTS=('test_rs_window_tis_validation.py',)
CASE_IDS=tuple(f'coat{nm:03d}-f{cutoff:04d}-minusRs' for cutoff in (500,2000) for nm in (0,10,30,50,100))
ALIASES=tuple(x for x in CASE_IDS if x.startswith('coat050-'))
GIB=1024**3

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON '+x)))
def require(condition,message):
    if not condition:raise ValueError(message)
def finite_nonnegative(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0

def absolute_pins(pins):
    result={}
    for name,sha in pins.items():
        path=Path(name);path=(path if path.is_absolute() else ROOT.parent/path).resolve();key=str(path)
        require(key not in result or result[key]==sha,'Conflicting absolute/relative pin namespace')
        result[key]=sha
    return result

def runtime_profile(profiles,c):
    """Pure adapter for the established summarize/contact_rows profile contract.

    Prepared spectra/selected fit stay immutable. The minimal preparation schema
    stores window warnings under fit_source; summarize requires a top-level list.
    """
    p=copy.deepcopy(profiles[c['condition_id']])
    require(all(k in p for k in ('thickness_nm','points','selected_fit','fit_source')),'Incomplete prepared profile contract')
    require(p['thickness_nm']==c['thickness_nm'] and p['selected_fit']['Rs_ohm']==c['selected_Rs_ohm'],'Runtime coating/window profile mismatch')
    require(p['fit_source']==c['fit_source'] and len(p['points'])==30,'Runtime fit provenance/point count mismatch')
    require(all(all(k in point for k in ('frequency_Hz','Z_real_ohm','Z_imag_ohm','source_range')) for point in p['points']),'Raw measured point schema incomplete')
    top=p.get('warnings',[]);window=p['fit_source'].get('warnings',[])
    require(isinstance(top,list) and isinstance(window,list) and all(isinstance(w,str) for w in top+window),'Warning provenance must be lists of strings')
    p['warnings']=list(dict.fromkeys(top+window))
    p['runtime_warning_provenance']=dict(prepared_top_level_warnings_present='warnings' in profiles[c['condition_id']],
      prepared_warning_JSON_pointer='/'+c['condition_id']+'/fit_source/warnings',source_fit=copy.deepcopy(c['fit_source']),
      note='Schema adapter only; original points/selected fit unchanged. No fitting or physical interpretation change.')
    return p

def audit_preparation():
    require(common.sha256(PREPARATION/'manifest-v2.json')==MANIFEST_SHA,'Active preparation manifest changed')
    require(common.sha256(PREPARATION/'preregistration-v2.json')==PREP_SHA,'Active preparation registration changed')
    m=read(PREPARATION/'manifest-v2.json');s=read(PREPARATION/'preregistration-v2.json')
    require(m['active_preregistration']=='preregistration-v2.json' and m['active_preregistration_file_sha256']==PREP_SHA,'Active v2 namespace differs')
    require(s['resource_limits']==LIMITS and s['numerical_gates']==NUMERICAL,'Prepared limits changed')
    require(tuple(c['condition_id'] for c in s['case_plan'])==CASE_IDS,'Ten exact ordered window slots required')
    require((s['semantic_window_condition_slots'],s['unique_physical_configurations'],s['expected_reference_slots'],s['unique_reused_complete_basis_count'],s['maximum_new_PDE_cases'])==(10,9,2,1,8),'Prepared reuse/cost scope differs')
    guards=absolute_pins(m['input_file_sha256'])
    guards.update({str(PREPARATION/p):sha for p,sha in m['files'].items()})
    guards[str(PREPARATION/'manifest-v2.json')]=MANIFEST_SHA
    guards[str(PREPARATION/'preregistration-v2.json')]=PREP_SHA
    common.assert_hashes_unchanged(guards)
    publication=Path(s['source_EIS_fit_run'])/'publication.json';receipt=read(publication)
    require(receipt.get('status')=='published_verified' and receipt.get('remote_ref_verified') is True and receipt.get('result_commit')==SOURCE_RESULT_COMMIT,'Published EIS result receipt absent')
    require(receipt['preexecution_registration_commit']!=receipt['result_commit'],'Fit preregistration is not result publication')
    for name in ('completion.json','window-slots-summary.json'):
        path=publication.parent/name;relative=str(path.relative_to(ROOT.parent))
        require(common.sha256(path)==receipt['remote_exact_file_SHA256'][relative],'Published fit result byte SHA differs')
        guards[str(path)]=common.sha256(path)
    guards[str(publication)]=common.sha256(publication)
    profiles=read(PREPARATION/'inputs/eis-profiles-windowed.json')
    require(set(profiles)==set(CASE_IDS),'Exact window-specific profile namespace required')
    hashes=[]
    for c in s['case_plan']:
        ident=c['condition_id'];profile=runtime_profile(profiles,c)
        require(c['config_file']==f'configs/{ident}.properties','Unexpected prepared config path')
        require(c['cells']==791280 and c['sc_cells']==2 and c['bulk_z_counts']==[14,14,40] and c['frequencies_Hz']==list(FREQUENCIES),'Fixed final mesh/frequencies changed')
        require(c['phase_deg']==[0.0,0.0] and c['carrier_group']==[0,1] and c['source_Vpp_each_output']==1.0 and c['source_resistance_ohm']==50.0,'Source/phase convention changed')
        require(profile['selected_fit']['Rs_ohm']==c['selected_Rs_ohm'] and profile['fit_source']==c['fit_source'],'Window profile/selected-Rs mismatch')
        require(profile['thickness_nm']==c['thickness_nm'] and profile['nominal_lower_frequency_Hz']==c['nominal_fit_lower_frequency_Hz'],'Coating/window identity differs')
        require(len(profile['points'])==30 and profile['measurement_area_m2']==1e-4 and all(p['Z_real_ohm']-c['selected_Rs_ohm']>=0 for p in profile['points']),'Raw full-band passivity/area differs')
        cfg=PREPARATION/c['config_file'];require(common.sha256(cfg)==c['config_file_sha256'],'Prepared config changed')
        text=common.make_config(config_text(c['design'],profile,c['h_xy_mm']),c['h_xy_mm'],2)
        require(text.encode()==cfg.read_bytes(),'Raw-points/Rs/area config reconstruction differs')
        alias=ident in ALIASES
        require(bool(c['existing_result_link'])==alias and c['operator_equivalent_to_existing_1k_config']==alias,'Only exact50nm slots may alias')
        if alias:
            link=c['existing_result_link']
            require(link['source_condition_id']=='coat050-minusRs' and link['basis_config_file_sha256']==c['config_file_sha256'],'Wrong reused physical basis')
            require(guards.get(link['source_case_path'])==link['source_case_file_sha256'],'Reuse case SHA absent')
            common.assert_hashes_unchanged(link['basis_output_file_sha256'])
        hashes.append(c['config_file_sha256'])
    require(len(set(hashes))==9 and hashes[3]==hashes[8],'One duplicate physical config, only50nm aliases required')
    ref=s['normalization_reference'];require(ref['condition_id']=='xy120-leader' and ref['selected_Rs_ohm']==213.27997221512513,'Original bare1k reference changed')
    require(common.sha256(ref['case_path'])==ref['source_case_file_sha256'],'Bare1k baseline case changed')
    baseline=read(ref['case_path']);require(baseline['status']=='complete' and baseline['postprocess']['status']=='complete','Baseline incomplete')
    return s,guards,baseline

def plan_for(spec,output):
    plan=[]
    for original in spec['case_plan']:
        c=copy.deepcopy(original)
        c.update(id=c['condition_id'],boundary_mode='measured_minus_Rs',config_file=str(output/c['config_file']),
          config_sha256=c['config_file_sha256'],execution_action='reuse_verified_complete_basis_alias' if c['condition_id'] in ALIASES else 'new_private_solve')
        plan.append(c)
    return plan

def command(manifest):
    return [manifest['java'],'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',manifest['classes'],'RsWindowTisBasis']

def validate_manifest(m):
    output=Path(m['output_run']).resolve()
    require(output.parent==ROOT/'runs' and output.name.startswith('rs-window-tis-validation-'),'New separate output required')
    require(common.sha256(PREPARATION/'preregistration-v2.json')==PREP_SHA and common.sha256(PREPARATION/'manifest-v2.json')==MANIFEST_SHA,'Active preparation bytes changed')
    s=read(PREPARATION/'preregistration-v2.json');r=read(output/'preregistration.json')
    require(common.sha256(output/'preregistration.json')==m['preregistration_sha256'],'Execution registration changed')
    require(r['authorization']['user_instruction']==AUTHORIZATION and r['maximum_new_PDE_cases']==8 and r['semantic_window_slots']==10 and r['unique_reused_complete_basis_count']==1 and r['reference_alias_slots']==2,'Authorized scope differs')
    require(r['case_plan']==s['case_plan'] and r['resource_limits']==LIMITS and r['numerical_gates']==NUMERICAL and r['normalization_reference']==s['normalization_reference'],'Execution registration plan/limits/baseline differ')
    require(m['status']=='prepared' and m['plan']==plan_for(s,output) and m['classes']==str(output/'classes'),'Plan/action/private-classpath differs')
    require(m['preparation_sha256']==PREP_SHA and m['preparation_manifest_sha256']==MANIFEST_SHA and m['resource_limits']==LIMITS and m['numerical_gates']==NUMERICAL,'Prepared namespace or caps differ')
    require(finite_nonnegative(m['preparation_wall_seconds']) and m['preparation_wall_seconds']<6600,'Invalid preparation budget')
    required=[output/'preregistration.json',*[ROOT/n for n in SOURCES+DEPENDENCIES+TESTS],*[Path(c['config_file']) for c in m['plan']]]
    required += [p for d in ('inputs','private-src','classes') for p in (output/d).iterdir() if p.is_file()]
    require(all(str(p) in m['guard_hashes'] for p in required),'Frozen guard coverage incomplete')
    require(set(r['execution_source_hashes'])=={str(ROOT/n) for n in SOURCES+DEPENDENCIES+TESTS},'Producer/dependency namespaces differ')
    require(all(m['guard_hashes'].get(p)==sha for p,sha in r['execution_source_hashes'].items()),'Source code hash namespace mismatch')
    require(all(m['guard_hashes'].get(str(output/'private-src'/n))==r['execution_source_hashes'][str(ROOT/n)] for n in SOURCES),'Private numerical source is not exact frozen copy')
    require(r['source_fit_result_commit']==SOURCE_RESULT_COMMIT and m['guard_hashes'].get(r['source_fit_result_publication_path'])==r['source_fit_result_publication_sha256'],'Fit result publication namespace differs')
    require(all(m['guard_hashes'].get(c['config_file'])==c['config_sha256'] for c in m['plan']),'Config byte/hash namespace mismatch')
    prepguards=read(PREPARATION/'manifest-v2.json')
    requiredpins={**absolute_pins(prepguards['input_file_sha256']),**{str(PREPARATION/p):s for p,s in prepguards['files'].items()},str(PREPARATION/'manifest-v2.json'):MANIFEST_SHA,str(PREPARATION/'preregistration-v2.json'):PREP_SHA}
    require(all(m['guard_hashes'].get(p)==sha for p,sha in requiredpins.items()),'Original preparation/source pin omitted or rebound')
    common.assert_hashes_unchanged(m['guard_hashes'])
    return True

def check_stop(output):
    for name in ('STOP','needs_attention','needs_physical_validation'):
        if (Path(output)/name).exists():raise common.ValidationStop(name,dict(status='user_stopped',stop_marker=name))

def prepare(output):
    began=time.monotonic();output=Path(output).resolve()
    require(output.parent==ROOT/'runs' and output.name.startswith('rs-window-tis-validation-') and not output.exists(),'Use new separate run; preserve old/partial runs')
    spec,guards,baseline=audit_preparation();check_stop(output)
    require(common.available_disk_bytes(output.parent)>=2*GIB+spec['cost']['estimated_new_raw_bytes_if_equal_to_reference'],'Eight new bases plus reserve unavailable')
    javac=shutil.which('javac') or str(JAVAC);java=str(Path(javac).resolve().parent/'java')
    require(Path(javac).is_file() and Path(java).is_file(),'Existing matching JDK unavailable')
    output.mkdir()
    for d in ('private-src','classes','inputs','configs','bases','cases','logs','postprocess'):(output/d).mkdir()
    registration=dict(schema_version=1,status='execution_authorized_preregistered',created_utc=now(),
      authorization=dict(user_instruction=AUTHORIZATION,scope='Finite Rs-window TIS fixed C2 geometry',original_worker_restart=False,membrane_or_biological_experiment=False),
      preparation_path=str(PREPARATION),relative_preparation_input_paths_resolved_against=str(ROOT.parent),preparation_sha256=PREP_SHA,preparation_manifest_sha256=MANIFEST_SHA,
      maximum_new_PDE_cases=8,semantic_window_slots=10,reference_alias_slots=2,unique_reused_complete_basis_count=1,
      case_plan=spec['case_plan'],resource_limits=LIMITS,numerical_gates=NUMERICAL,normalization_reference=spec['normalization_reference'],
      source_fit_result_commit=SOURCE_RESULT_COMMIT,source_fit_result_publication_path=str(Path(spec['source_EIS_fit_run'])/'publication.json'),
      source_fit_result_publication_sha256=guards[str(Path(spec['source_EIS_fit_run'])/'publication.json')],
      source_fit_preexecution_registration_commit=read(Path(spec['source_EIS_fit_run'])/'publication.json')['preexecution_registration_commit'],
      analysis_plan=spec['analysis_plan'],full_measured_reference_cases=read(PREPARATION/'inputs/existing-field-references.json')['full_measured_Rs_zero_existing'],
      primary_fixed_source_objective=spec['primary_fixed_source_objective'],cost=spec['cost'],holds=spec['holds'],original_physical_hold_preserved=True,
      execution_source_hashes={str(ROOT/n):common.sha256(ROOT/n) for n in SOURCES+DEPENDENCIES+TESTS},
      failure_policy=spec['failure_policy'])
    atomic(output/'preregistration.json',registration)
    for p in (PREPARATION/'inputs').iterdir():shutil.copy2(p,output/'inputs'/p.name)
    shutil.copy2(PREPARATION/'preregistration-v2.json',output/'inputs/preparation-preregistration-v2.json')
    for c in spec['case_plan']:shutil.copy2(PREPARATION/c['config_file'],output/c['config_file'])
    for n in SOURCES:shutil.copy2(ROOT/n,output/'private-src'/n)
    guards.update(registration['execution_source_hashes'])
    for d in ('inputs','configs','private-src'):guards.update({str(p):common.sha256(p) for p in (output/d).iterdir()})
    guards[str(output/'preregistration.json')]=common.sha256(output/'preregistration.json')
    m=dict(status='preparing',schema_version=1,output_run=str(output),preparation_sha256=PREP_SHA,preparation_manifest_sha256=MANIFEST_SHA,
      preregistration_sha256=guards[str(output/'preregistration.json')],plan=plan_for(spec,output),resource_limits=LIMITS,numerical_gates=NUMERICAL,
      java=java,javac=javac,classes=str(output/'classes'),guard_hashes=guards,preparation_wall_seconds=time.monotonic()-began)
    atomic(output/'manifest.json',m)
    try:
        with common.diagnostic_lock():
            m['compiler']=common.run_guarded([javac,'-J-Xmx512m','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(output/'classes'),'-classpath',str(output/'classes'),'-sourcepath',str(output/'private-src')]+[str(output/'private-src'/n) for n in SOURCES],output/'logs/compile.log',timeout_s=120)
            m['selftest']=common.run_guarded(command(m)+['--selftest'],output/'logs/selftest.log',timeout_s=120)
            for c in m['plan']:common.run_guarded(command(m)+['--validate-config',c['config_file']],output/'logs'/(c['id']+'-config.log'),timeout_s=10)
            # Negative guards do not use a valid parent; no mesh or output is allowed.
            tampered=output/'inputs/negative-newline.properties';tampered.write_bytes(Path(m['plan'][0]['config_file']).read_bytes()+b'\n')
            negative=[('newline',tampered),('old-bare1k',Path(baseline['config_file']))]
            for label,path in negative:
                try:common.run_guarded(command(m)+['--validate-config',str(path)],output/'logs'/('negative-'+label+'.log'),timeout_s=10)
                except common.ValidationStop as e:require(e.resources.get('status')=='process_failed','Negative guard failed for resource reason')
                else:raise ValueError('Unregistered Java config accepted')
            target=output/'bases/negative-direct-parent'
            try:common.run_guarded(command(m)+['--execute-parent',str(os.getpid()),str(startticks(os.getpid())),m['plan'][0]['config_file'],str(target)],output/'logs/negative-parent.log',timeout_s=10)
            except common.ValidationStop as e:require(e.resources.get('status')=='process_failed' and not target.exists(),'Direct parent guard allocated output')
            else:raise ValueError('Detached/unregistered solve accepted')
        m['guard_hashes'].update({str(p):common.sha256(p) for d in ('classes','inputs') for p in (output/d).iterdir() if p.is_file()})
        m.update(status='prepared',preparation_wall_seconds=time.monotonic()-began);atomic(output/'manifest.json',m)
        validate_manifest(m)
    except BaseException as error:
        m.update(status='preparation_failed',error=str(error),preparation_wall_seconds=time.monotonic()-began);atomic(output/'manifest.json',m);raise
    (output/'README.md').write_text('# Rs-window TIS execution preparation\n\nPrepared private compile/analytic/config/negative guards only; no PDE or field postprocess yet. Ten window slots/9configs/8newsolve maximum/two50nm aliases to one existing complete basis. Original same-wave bare1k normalization and fullZ5 references unchanged. Exact manifest/prereg/source publication receipt is required before one execution. Failed/partial runs are preserved without retry. Coating/contact SCXY/whole3D/instrument/physiology holds remain.\n',encoding='utf-8')
    return m

def validate_publication(output,m):
    p=read(output/'execution-publication.json')
    require(p.get('status')=='published_before_PDE' and p.get('remote_ref_verified') is True and re.fullmatch('[0-9a-f]{40}',p.get('commit','')) is not None,'Exact preexecution publication absent')
    require(p.get('manifest_sha256')==common.sha256(output/'manifest.json') and p.get('preregistration_sha256')==m['preregistration_sha256'],'Publication byte hashes differ')

def matched_rows(metrics,baseline):
    require(len(metrics)==len(baseline)==3 and {x['waveform'] for x in metrics}==set(WAVES) and {x['waveform'] for x in baseline}==set(WAVES),'Three same-wave rows required')
    for row in metrics:
        ref=next(x for x in baseline if x['waveform']==row['waveform'])
        keys=('surface_J_RMS_max_A_m2','SC_power_W','contact_power_W','contact_voltage_RMS_max_V','source_power_W')
        require(all(finite_nonnegative(x[k]) and x[k]>0 for x in (row,ref) for k in keys),'Nonfinite/zero burden reference')
        scale=min(1,ref[keys[0]]/row[keys[0]],math.sqrt(ref[keys[1]]/row[keys[1]]),math.sqrt(ref[keys[2]]/row[keys[2]]),ref[keys[3]]/row[keys[3]])
        power=min(1,math.sqrt(ref['source_power_W']/row['source_power_W']))
        row['same_wave_bare_baseline']=dict(waveform=row['waveform'],source_run='leader-validation-3k-20261019T030136Z',condition_id='xy120-leader',selected_Rs_window_Hz=1000,
          burden_source_Vpp=scale,power_source_Vpp=power,burden_TIS_V_m=row['target20_modulation_V_m']*scale,burden_E_RMS_V_m=row['target20_total_E_RMS_V_m']*scale,
          power_TIS_V_m=row['target20_modulation_V_m']*power,power_E_RMS_V_m=row['target20_total_E_RMS_V_m']*power)
    return metrics

def assert_metric_input(metrics,c):
    require(len(metrics)==3 and {r['waveform'] for r in metrics}==set(WAVES),'Expected three fixed waveforms')
    for r in metrics:
        require(r['thickness_nm']==c['thickness_nm'] and r['boundary_mode']=='measured_minus_Rs' and r['carrier_Hz']==3000 and r['beat_Hz']==30 and r['carrier_group']==[0,1] and r['phase_deg']==[0.0,0.0],'Metric source/coating/wave/phase mismatch')
        require(all(finite_nonnegative(r[k]) for k in ('target20_modulation_V_m','target20_total_E_RMS_V_m','surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','SC_power_W','contact_power_W','source_power_W','contact_voltage_RMS_max_V')),'Nonfinite electrical metrics')

def alias_result(c,m):
    require(c['id'] in ALIASES and c['execution_action']=='reuse_verified_complete_basis_alias','Only preregistered50nm aliases may reuse')
    link=c['existing_result_link'];common.assert_hashes_unchanged(link['basis_output_file_sha256'])
    require(common.sha256(link['source_case_path'])==link['source_case_file_sha256'],'Reused case changed')
    original=read(link['source_case_path'])
    require(original['status']=='complete' and original['config_sha256']==c['config_sha256'] and original['postprocess']['status']=='complete','Incomplete or different reused basis')
    require(common.sha256(original['postprocess']['path'])==original['postprocess']['sha256'],'Reused postprocess changed')
    assert_metric_input(original['metrics'],c)
    return dict(c,status='complete',basis_dir=original['basis_dir'],validation=original['validation'],metrics=copy.deepcopy(original['metrics']),
      output_hashes=copy.deepcopy(original['output_hashes']),producer_kind=original['producer_kind'],producer_source_sha256=original['producer_source_sha256'],
      analysis_code_sha256=original['analysis_code_sha256'],postprocess=dict(original['postprocess'],reuse_only=True),
      resources=dict(status='reused_verified_complete_basis_alias',new_PDE=False),source_case_sha256=link['source_case_file_sha256'],
      semantic_window_alias_only=True,source_result_condition_id='coat050-minusRs',reused_original_metrics_without_recomputation=True,
      same_wave_bare_reference_unchanged=True)

def failure_status(error):
    resources=error.resources if isinstance(error,common.ValidationStop) else {}
    return ('user_stopped' if resources.get('status')=='user_stopped' else
      'resource_stopped' if resources.get('status') in ('case_timeout','total_timeout','rss_limit','driver_rss_limit','disk_reserve') else
      'interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) or resources.get('returncode',0)<0 else 'failed')

def failure_evidence(output,case,phase,error,status):
    """Classify only recognized failed-solver logs; never infer convergence from exit."""
    evidence=dict(failure_stage=phase,solver_status='not_inferred',unconverged=False,numerical_failed=False)
    if not case:return evidence
    log=Path(output)/'logs'/(case['id']+'.log')
    if log.is_file():
        evidence.update(log_path=str(log),log_file_sha256=common.sha256(log))
        with log.open('rb') as stream:
            stream.seek(max(0,log.stat().st_size-1024*1024));text=stream.read().decode('utf-8',errors='replace')
        resources=error.resources if isinstance(error,common.ValidationStop) else {}
        if status=='failed' and phase=='solving' and resources.get('status')=='process_failed':
            unconverged=[x for x in ('COCG solver failed','Residual ') if x in text]
            numerical=[x for x in ('Numerical conservation gate failed','Nonfinite validation','Physical pad area changed') if x in text]
            if unconverged:evidence.update(solver_status='unconverged',unconverged=True,recognized_solver_signatures=unconverged)
            elif numerical:evidence.update(solver_status='numerical_failed',numerical_failed=True,recognized_solver_signatures=numerical)
            else:evidence['solver_status']='unknown_process_failure_incomplete'
    folder=Path(output)/'bases'/case['id']
    if folder.exists():evidence['preserved_basis_directory']=str(folder)
    return evidence

def execute(m):
    entered=time.monotonic();validate_manifest(m);output=Path(m['output_run']);validate_publication(output,m);check_stop(output)
    with common.diagnostic_lock(),(output/'.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Java FileChannel uses POSIX locks, distinct from Linux flock. Hold both.
        fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        require(not any((output/n).exists() for n in ('summary.json','controller.json','failure.json')) and not any((output/'cases').iterdir()) and not any((output/'bases').iterdir()) and not any((output/'postprocess').iterdir()),'Prior complete/partial/failed run preserved; no retry')
        require(common.available_disk_bytes(output)>=2*GIB+8*456816923,'Eight prospective bases plus2GiB reserve unavailable')
        began=time.monotonic();prior=m['preparation_wall_seconds']+began-entered;deadline=began+6600-prior
        summary=dict(status='running',cases=[],new_PDE_started=0,new_PDE_count=0,reused_reference_alias_slots=0,unique_reused_complete_basis_count=0,
          resource_limits=LIMITS,numerical_gates=NUMERICAL,original_physical_hold_preserved=True,
          convergence=dict(status='held_for_changed_Rs_or_coatings',bare_1000Hz_registered_SC_XY='historical_only',whole3D='held'),normalization_reference=read(output/'preregistration.json')['normalization_reference'])
        state=dict(status='running',pid=os.getpid(),proc_start_ticks=startticks(os.getpid()),current_case=None,phase='starting',started_utc=now(),command=sys.argv)
        active=None;case_start=None
        def persist():
            summary.update(updated_utc=now(),total_wall_seconds=prior+time.monotonic()-began)
            state.update(updated_utc=now(),completed_cases=len(summary['cases']),new_PDE_started=summary['new_PDE_started']);atomic(output/'summary.json',summary);atomic(output/'controller.json',state)
        def interrupt(signum,frame):signal.setitimer(signal.ITIMER_REAL,0);raise KeyboardInterrupt('Interrupted signal '+str(signum))
        def watch(signum,frame):
            try:
                check_stop(output);t=time.monotonic()
                reason=('total_timeout' if t>=deadline else 'case_timeout' if case_start is not None and t-case_start>=600 else 'driver_rss_limit' if common.process_rss_bytes(os.getpid())>3*GIB else 'disk_reserve' if common.available_disk_bytes(output)<2*GIB else None)
                if reason:raise common.ValidationStop(reason,dict(status=reason))
            except BaseException:signal.setitimer(signal.ITIMER_REAL,0);raise
        oldterm,oldint=signal.signal(signal.SIGTERM,interrupt),signal.signal(signal.SIGINT,interrupt)
        oldalarm=signal.signal(signal.SIGALRM,watch);signal.setitimer(signal.ITIMER_REAL,.5,.5)
        try:
            persist();baseline=read(summary['normalization_reference']['case_path']);profiles=read(output/'inputs/eis-profiles-windowed.json')
            for c in m['plan']:
                case_start=time.monotonic();active=c;watch(None,None);common.assert_hashes_unchanged(m['guard_hashes'])
                state.update(current_case=c['id'],phase='source_validation');persist();gc.collect()
                if c['execution_action']=='reuse_verified_complete_basis_alias':
                    result=alias_result(c,m);summary['reused_reference_alias_slots']+=1;summary['unique_reused_complete_basis_count']=1
                else:
                    require(c['id'] not in ALIASES and summary['new_PDE_started']<8,'New-solve alias/cap gate')
                    profile=runtime_profile(profiles,c);require(profile['selected_fit']['Rs_ohm']==c['selected_Rs_ohm'],'Case/window profile differs')
                    reconstructed=common.make_config(config_text(c['design'],profile,c['h_xy_mm']),c['h_xy_mm'],2)
                    require(reconstructed.encode()==Path(c['config_file']).read_bytes(),'Postprocess contactZ/profile not identical to PDE config')
                    folder=output/'bases'/c['id'];require(not folder.exists(),'Preserve partial basis, no retry')
                    if common.available_disk_bytes(output)<2*GIB+c['cells']*680:raise common.ValidationStop('disk_reserve',dict(status='disk_reserve'))
                    summary['new_PDE_started']+=1;state['phase']='solving';persist()
                    remaining=600-(time.monotonic()-case_start);require(remaining>0,'Case budget exhausted before launch')
                    resources=common.run_guarded(command(m)+['--execute-parent',str(os.getpid()),str(state['proc_start_ticks']),c['config_file'],str(folder)],output/'logs'/(c['id']+'.log'),timeout_s=remaining,total_deadline=deadline)
                    summary['new_PDE_count']+=1;v=read(folder/'validation.json')
                    areas=common.check_numerical_gates(v,[folder/f'contacts-{f}.csv' for f in FREQUENCIES],15)
                    require(v['cells']==791280 and (folder/'BASIS_COMPLETE').is_file(),'Incomplete basis/dimensions')
                    state['phase']='electrical_postprocessing';persist();basis=load_basis(folder,2,FREQUENCIES)
                    producer=m['guard_hashes'][str(ROOT/'RsWindowTisBasis.java')];key=hashlib.sha256((c['config_sha256']+producer).encode()).hexdigest()[:18]
                    metrics=matched_rows(summarize(basis,c['design'],profile,key,c['h_xy_mm']),baseline['metrics']);assert_metric_input(metrics,c)
                    del basis;gc.collect()
                    result=dict(c,status='electrical_complete_postprocessing_pending',basis_dir=str(folder),validation=v,physical_pad_areas_m2=areas,metrics=metrics,resources=resources,
                      runtime_profile_warning_provenance=profile['runtime_warning_provenance'],
                      producer_kind='private_RsWindowTisBasis',producer_source_sha256=producer,analysis_code_sha256=m['guard_hashes'][str(ROOT/'rs_window_tis_validation.py')],
                      output_hashes={str(p):common.sha256(p) for p in folder.iterdir() if p.is_file()})
                    atomic(output/'cases'/(c['id']+'.json'),result);state['phase']='native_and_spatial_postprocessing';persist()
                    path=None
                    try:
                        metadata=read(folder/'mesh-metadata.json');metadata.update(config_path=c['config_file'],config_sha256=c['config_sha256'],source_run_id=output.name,source_condition_id=c['id'],source_hashes=m['guard_hashes'])
                        post=analyze_case(folder,metrics,metadata);path=output/'postprocess'/(c['id']+'.json.gz')
                        with gzip.open(path,'xt',encoding='utf-8') as f:json.dump(post,f,ensure_ascii=False,allow_nan=False)
                        result['postprocess']=dict(status='complete' if post['status']=='complete' and post['verification']['spatial_all_complete'] else 'failed',combined_status=post['status'],path=str(path),sha256=common.sha256(path),
                          native_probe_status='complete',spatial_status='complete' if post['verification']['spatial_all_complete'] else 'incomplete_or_failed')
                        require(result['postprocess']['status']=='complete','Stored native/spatial postprocessing failed; no completion inference')
                    except BaseException as error:
                        signal.setitimer(signal.ITIMER_REAL,0)
                        stop_status=failure_status(error);post_status='postprocessing_failed' if stop_status=='failed' else stop_status
                        result.update(status=post_status,postprocess=dict(result.get('postprocess',{}),status='failed' if stop_status=='failed' else stop_status,error=str(error)))
                        if path is not None and path.is_file():
                            result['preserved_postprocess_artifact']=dict(path=str(path),file_sha256=common.sha256(path),completeness='not_inferred_from_file_existence')
                        atomic(output/'cases'/(c['id']+'.json'),result);summary['status']=post_status;raise
                    result['status']='complete';resources.update(case_wall_seconds=time.monotonic()-case_start,driver_peak_rss_bytes=common.process_rss_bytes(os.getpid()))
                watch(None,None);common.assert_hashes_unchanged(m['guard_hashes']);watch(None,None);result['case_wall_seconds']=time.monotonic()-case_start
                atomic(output/'cases'/(c['id']+'.json'),result);summary['cases'].append(result);persist()
                print(json.dumps(dict(case=c['id'],status='complete',new_PDE=c['id'] not in ALIASES)),flush=True)
            case_start=None;watch(None,None)
            require(len(summary['cases'])==10 and summary['new_PDE_count']==summary['new_PDE_started']==8 and summary['reused_reference_alias_slots']==2 and summary['unique_reused_complete_basis_count']==1,'Final exact10/8/2/1 count gate failed')
            require(prior+time.monotonic()-began<=6600,'Final registered6600s budget exceeded')
            summary['status']='complete';summary['finished_utc']=now();state.update(status='complete',phase='finished',current_case=None,finished_utc=now());persist();return summary
        except BaseException as error:
            signal.setitimer(signal.ITIMER_REAL,0)
            resources=error.resources if isinstance(error,common.ValidationStop) else {}
            if summary['status']!='postprocessing_failed':summary['status']=failure_status(error)
            evidence=failure_evidence(output,active,state['phase'],error,summary['status']);summary.update(evidence)
            if summary['status']=='failed' and evidence['solver_status'] in ('unconverged','numerical_failed'):summary['status']=evidence['solver_status']
            summary.update(error=str(error),error_type=type(error).__name__,failed_case=active['id'] if active else None,failed_resources=resources)
            if active:summary['failed_case_artifacts']={str(p):common.sha256(p) for p in (output/'cases').glob(active['id']+'*.json') if p.is_file()}
            state.update(status=summary['status'],error=str(error));persist();atomic(output/'failure.json',dict(summary));raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,oldalarm);signal.signal(signal.SIGTERM,oldterm);signal.signal(signal.SIGINT,oldint)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    result=execute(read(a.output/'manifest.json')) if a.execute else prepare(a.output)
    print(json.dumps(dict(status=result['status'],completed_cases=len(result.get('cases',[])),new_PDE=result.get('new_PDE_count',0))),flush=True)
if __name__=='__main__':main()
