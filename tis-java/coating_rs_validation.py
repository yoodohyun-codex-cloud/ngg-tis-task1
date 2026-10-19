"""Finite, separately authorized coating/Rs experiment. Never resumes old workers.

Physical inputs are the ten immutable prepared configs. Completed bare data are
referenced without recalculation. Failed/partial execution is never retried.
"""
from pathlib import Path
import argparse
import copy
import fcntl
import gc
import gzip
import hashlib
import json
import math
import os
import shutil
import signal
import time

import mesh_validation as common
from mesh_validation_3k import LIMITS, NUMERICAL, FREQUENCIES, now, startticks
from explore_tis import ROOT, JAVAC, atomic, config_text, load_basis, summarize
from validation_3k_postprocess import analyze_case

PREPARATION = ROOT/'runs/coating-rs-preparation-20261019T042330Z'
PREP_SHA = 'eee6de01ed22e6040cb569414d587064ddbcc91c91477fc9463a94356531b75d'
AUTHORIZATION = '시뮬레이션 계속 돌려봐 변수 알아서 바꿔서'
SOURCES = ('TisSweep.java', 'ExploreBasis.java', 'CoatingRsBasis.java')
DEPENDENCIES = ('coating_rs_validation.py', 'mesh_validation_3k.py', 'mesh_validation.py',
    'explore_tis.py', 'explore_inputs.py', 'fit_ngg_eis.py', 'update_ngg_eis.py',
    'ValidationBasis.java', 'Validation3kBasis.java', 'validation_3k_postprocess.py',
    'leader_spatial_diagnostics.py', 'layered_probe_analysis.py', 'native_probe_followup.py')
GIB = 1024**3


def audit_preparation():
    if common.sha256(PREPARATION/'preregistration.json') != PREP_SHA:
        raise ValueError('Immutable input preparation changed')
    spec = json.loads((PREPARATION/'preregistration.json').read_text())
    if spec['resource_limits'] != LIMITS or spec['numerical_gates'] != NUMERICAL:
        raise ValueError('Prepared limits differ from the existing caps')
    if len(spec['case_plan']) != 10 or len({c['config_sha256'] for c in spec['case_plan']}) != 10:
        raise ValueError('Exactly ten unique prepared physical conditions required')
    guards = {str(p):common.sha256(p) for p in [PREPARATION/'preregistration.json', PREPARATION/'manifest.json']}
    for name in ('source-code-hashes.json', 'completed-3k-source-artifact-hashes.json'):
        data = json.loads((PREPARATION/'inputs'/name).read_text())
        common.assert_hashes_unchanged(data)
        guards.update(data)
    audit = json.loads((PREPARATION/'inputs/EIS-source-audit.json').read_text())
    for row in audit['profiles']:
        guards[row['source_file']] = row['source_sha256']
    profiles = json.loads((PREPARATION/'inputs/eis-profiles.json').read_text())
    if common.sha256(PREPARATION/'inputs/eis-profiles.json') != spec['EIS_profile_sha256']:
        raise ValueError('EIS profile changed')
    for c in spec['case_plan']:
        config = PREPARATION/c['config_file']
        if common.sha256(config) != c['config_sha256']:
            raise ValueError('Prepared config changed: '+c['condition_id'])
        if c['cells'] != 791280 or c['sc_cells'] != 2 or c['bulk_z_counts'] != [14,14,40] or c['frequencies_Hz'] != list(FREQUENCIES):
            raise ValueError('Only prepared final-grid coating/Rs conditions allowed')
        generated = common.make_config(config_text(c['design'], profiles[str(c['thickness_nm'])], c['h_xy_mm']), c['h_xy_mm'], 2)
        if common.parse_properties(generated) != common.parse_properties(config.read_text()):
            raise ValueError('EIS/material/source reconstruction differs: '+c['condition_id'])
        guards[str(config)] = c['config_sha256']
    link = spec['case_plan'][0]['existing_result_link']
    common.assert_hashes_unchanged(link['basis_output_hashes'])
    guards.update(link['basis_output_hashes'])
    source = Path(spec['source_run'])/'cases/xy120-leader.json'
    if common.sha256(source) != spec['source_result_sha256']:
        raise ValueError('Completed source result changed')
    baseline = json.loads(source.read_text())
    post = baseline['postprocess']
    if baseline['status'] != 'complete' or post['status'] != 'complete' or common.sha256(post['path']) != post['sha256']:
        raise ValueError('Completed baseline postprocessing unavailable; do not regenerate')
    guards[str(source)] = spec['source_result_sha256']
    guards[post['path']] = post['sha256']
    for p in (PREPARATION/'inputs').iterdir():
        guards[str(p)] = common.sha256(p)
    common.assert_hashes_unchanged(guards)
    return spec, guards, baseline


def command(manifest):
    return [manifest['java'], '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
            '-cp', manifest['classes'], 'CoatingRsBasis']


def plan_for(spec, output):
    plan = []
    for original in spec['case_plan']:
        c = copy.deepcopy(original)
        c.update(id=c['condition_id'], config_file=str(output/c['config_file']),
                 execution_action='reuse_verified_complete_basis' if c['existing_result_link'] else 'new_private_solve')
        plan.append(c)
    return plan


def validate_manifest(manifest):
    output = Path(manifest['output_run']).resolve()
    if output.parent != ROOT/'runs' or not output.name.startswith('coating-rs-validation-'):
        raise ValueError('Only a new separate coating-rs-validation-* output allowed')
    spec = json.loads((PREPARATION/'preregistration.json').read_text())
    if common.sha256(PREPARATION/'preregistration.json') != PREP_SHA:
        raise ValueError('Prepared input identity changed')
    registration = json.loads((output/'preregistration.json').read_text())
    if common.sha256(output/'preregistration.json') != manifest['preregistration_sha256']:
        raise ValueError('Execution registration changed')
    if registration['authorization']['user_instruction'] != AUTHORIZATION or registration['maximum_new_PDE_cases'] != 9:
        raise ValueError('Finite execution authorization absent')
    if manifest['resource_limits'] != LIMITS or manifest['numerical_gates'] != NUMERICAL:
        raise ValueError('Execution limits changed')
    if manifest['status'] != 'prepared' or manifest['plan'] != plan_for(spec,output) or manifest['classes'] != str(output/'classes'):
        raise ValueError('Execution plan/action/classpath differs')
    if manifest['preparation_sha256'] != PREP_SHA:
        raise ValueError('Preparation namespace differs')
    if registration['case_plan'] != spec['case_plan'] or registration['resource_limits'] != LIMITS or registration['numerical_gates'] != NUMERICAL:
        raise ValueError('Registration physical plan or caps changed')
    for case in manifest['plan']:
        if manifest['guard_hashes'].get(case['config_file']) != case['config_sha256']:
            raise ValueError('Config file/content hash namespace differs')
    expected_code = registration['execution_source_hashes']
    required = [output/'preregistration.json', *[ROOT/n for n in SOURCES+DEPENDENCIES]]
    required += [Path(c['config_file']) for c in manifest['plan']]
    required += [p for d in ('private-src','classes','inputs') for p in (output/d).iterdir() if p.is_file()]
    if any(str(p) not in manifest['guard_hashes'] for p in required):
        raise ValueError('Source/class/config/input guards incomplete')
    if any(manifest['guard_hashes'].get(p) != sha for p,sha in expected_code.items()):
        raise ValueError('Source namespace differs from registration')
    common.assert_hashes_unchanged(manifest['guard_hashes'])
    return True


def prepare(output):
    started = time.monotonic()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Output exists; preserve previous run instead of implicit retry')
    if output.parent != ROOT/'runs' or not output.name.startswith('coating-rs-validation-'):
        raise ValueError('Use a separate coating-rs-validation-* run')
    spec, guards, baseline = audit_preparation()
    if common.available_disk_bytes(output.parent) < 2*GIB + 9*456816860:
        raise ValueError('Nine new complete bases plus unchanged 2GiB disk reserve unavailable')
    javac = shutil.which('javac') or str(JAVAC)
    java = str(Path(javac).resolve().parent/'java')
    if not Path(java).is_file() or not Path(javac).is_file():
        raise ValueError('Existing matching JDK unavailable')
    output.mkdir()
    for d in ('private-src','classes','inputs','configs','bases','cases','logs','postprocess'):
        (output/d).mkdir()
    registration = dict(schema_version=1, created_utc=now(), status='execution_authorized_preregistered',
        authorization=dict(user_instruction=AUTHORIZATION, scope='First finite five-coating/two-Rs treatment batch',
            original_worker_restart=False, membrane_or_biological_experiment=False),
        preparation_path=str(PREPARATION), preparation_preregistration_sha256=PREP_SHA,
        source_run=spec['source_run'], source_result_sha256=spec['source_result_sha256'],
        maximum_new_PDE_cases=9, complete_basis_reuse_count=1,
        primary_fixed_source_objective=spec['primary_fixed_source_objective'],
        case_plan=spec['case_plan'], resource_limits=LIMITS, numerical_gates=NUMERICAL,
        analysis_plan=spec['analysis_plan'], original_physical_hold_preserved=True,
        uncertainty='PBS contact surrogate; changed coatings lack independent SC/XY/whole3D/dry-contact/physiological validation',
        execution_source_hashes={str(ROOT/n):common.sha256(ROOT/n) for n in SOURCES+DEPENDENCIES},
        cost=spec['cost_proposal'], historical_preparation_authorization_superseded_for_this_execution_only=True,
        failure_policy='Preserve incomplete, unconverged, interrupted and postprocess_failed separately. Stop without retry or cap relaxation.')
    atomic(output/'preregistration.json',registration)
    for p in (PREPARATION/'inputs').iterdir():
        shutil.copy2(p,output/'inputs'/p.name)
    shutil.copy2(PREPARATION/'preregistration.json',output/'inputs/preparation-preregistration.json')
    for c in spec['case_plan']:
        shutil.copy2(PREPARATION/c['config_file'],output/c['config_file'])
    for n in SOURCES:
        shutil.copy2(ROOT/n,output/'private-src'/n)
    guards.update(registration['execution_source_hashes'])
    guards.update({str(p):common.sha256(p) for p in ROOT.glob('*.class')})
    for d in ('inputs','configs','private-src'):
        guards.update({str(p):common.sha256(p) for p in (output/d).iterdir()})
    guards[str(output/'preregistration.json')] = common.sha256(output/'preregistration.json')
    manifest = dict(schema_version=1, created_utc=now(), status='preparing',output_run=str(output),
        preparation_sha256=PREP_SHA, preregistration_sha256=guards[str(output/'preregistration.json')],
        plan=plan_for(spec,output),resource_limits=LIMITS,numerical_gates=NUMERICAL,
        java=java,javac=javac,classes=str(output/'classes'),guard_hashes=guards)
    atomic(output/'manifest.json',manifest)
    try:
        with common.diagnostic_lock():
            manifest['compiler'] = common.run_guarded([javac,'-J-Xmx512m','-J-XX:ActiveProcessorCount=1',
                '-encoding','UTF-8','-d',str(output/'classes'),'-classpath',str(output/'classes'),
                '-sourcepath',str(output/'private-src')]+[str(output/'private-src'/n) for n in SOURCES],output/'logs/compile.log',timeout_s=120)
            manifest['selftest'] = common.run_guarded(command(manifest)+['--selftest'],output/'logs/selftest.log',timeout_s=120)
            for c in manifest['plan']:
                common.run_guarded(command(manifest)+['--validate-config',c['config_file']],output/'logs'/(c['id']+'-config.log'),timeout_s=10)
        manifest['guard_hashes'].update({str(p):common.sha256(p) for p in (output/'classes').iterdir()})
        manifest.update(status='prepared',preparation_wall_seconds=time.monotonic()-started)
        atomic(output/'manifest.json',manifest)
        validate_manifest(manifest)
    except BaseException as error:
        manifest.update(status='preparation_failed',error=str(error),preparation_wall_seconds=time.monotonic()-started)
        atomic(output/'manifest.json',manifest)
        raise
    return manifest


def matched_rows(metrics, baseline):
    for row in metrics:
        ref = next(r for r in baseline if r['waveform']==row['waveform'])
        scale = min(1,ref['surface_J_RMS_max_A_m2']/row['surface_J_RMS_max_A_m2'],
            math.sqrt(ref['SC_power_W']/row['SC_power_W']),math.sqrt(ref['contact_power_W']/row['contact_power_W']),
            ref['contact_voltage_RMS_max_V']/row['contact_voltage_RMS_max_V'])
        power = min(1,math.sqrt(ref['source_power_W']/row['source_power_W']))
        row['same_wave_bare_baseline'] = dict(waveform=ref['waveform'],source_run='leader-validation-3k-20261019T030136Z',
            condition_id='xy120-leader', burden_source_Vpp=scale, power_source_Vpp=power,
            burden_TIS_V_m=row['target20_modulation_V_m']*scale,
            burden_E_RMS_V_m=row['target20_total_E_RMS_V_m']*scale,
            power_TIS_V_m=row['target20_modulation_V_m']*power,
            power_E_RMS_V_m=row['target20_total_E_RMS_V_m']*power)
    return metrics


def execute(manifest):
    entry_started = time.monotonic()
    validate_manifest(manifest)
    output = Path(manifest['output_run'])
    receipt=json.loads((output/'execution-publication.json').read_text())
    if receipt.get('status')!='published_before_PDE' or receipt.get('manifest_sha256')!=common.sha256(output/'manifest.json') or receipt.get('preregistration_sha256')!=manifest['preregistration_sha256']:
        raise ValueError('Exact execution preregistration must be published before PDE')
    with common.diagnostic_lock(),(output/'.execution.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (output/'summary.json').exists():
            raise ValueError('Prior execution exists: never retry completed/partial/failed run')
        started=time.monotonic(); prior=manifest['preparation_wall_seconds']+started-entry_started; deadline=started+6600-prior
        summary=dict(schema_version=1,status='running',created_utc=now(),cases=[],new_PDE_started=0,new_PDE_count=0,
            reused_complete_basis_count=0,resource_limits=LIMITS,original_physical_hold_preserved=True,
            convergence=dict(status='held_for_changed_coatings',bare_status='passed_only_for_registered_bare_SC_XY',whole3D='held'))
        state=dict(pid=os.getpid(),proc_start_ticks=startticks(os.getpid()),status='running',started_utc=now(),
            command=Path('/proc/self/cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),current_case=None,phase='starting')
        watch={'started':None}; active=None
        def persist():
            summary.update(updated_utc=now(),total_wall_seconds=prior+time.monotonic()-started)
            state.update(updated_utc=now(),completed_cases=len(summary['cases']),new_PDE_started=summary['new_PDE_started'])
            atomic(output/'summary.json',summary);atomic(output/'controller.json',state)
        def stopcheck(signum,frame):
            t=time.monotonic()
            reason=('total_timeout' if t>=deadline else 'case_timeout' if watch['started'] is not None and t-watch['started']>600 else
                'driver_rss_limit' if common.process_rss_bytes(os.getpid())>3*GIB else
                'disk_reserve' if common.available_disk_bytes(output)<2*GIB else
                'STOP' if (output/'STOP').exists() else None)
            if reason:
                signal.setitimer(signal.ITIMER_REAL,0)
                raise common.ValidationStop(reason,dict(status=reason))
        def interrupt(signum,frame):
            raise KeyboardInterrupt('Execution interrupted by signal '+str(signum))
        oldterm=signal.signal(signal.SIGTERM,interrupt)
        oldint=signal.signal(signal.SIGINT,interrupt)
        old=signal.signal(signal.SIGALRM,stopcheck);signal.setitimer(signal.ITIMER_REAL,.5,.5)
        try:
            persist()
            baseline=json.loads((Path(json.loads((output/'inputs/preparation-preregistration.json').read_text())['source_run'])/'cases/xy120-leader.json').read_text())
            profiles=json.loads((output/'inputs/eis-profiles.json').read_text())
            for c in manifest['plan']:
                active=c;watch['started']=time.monotonic();common.assert_hashes_unchanged(manifest['guard_hashes'])
                state.update(current_case=c['id'],phase='source_validation');persist();gc.collect()
                reused=c['execution_action']=='reuse_verified_complete_basis'
                if reused:
                    result=dict(c,status='complete',basis_dir=baseline['basis_dir'],validation=baseline['validation'],
                        metrics=matched_rows(copy.deepcopy(baseline['metrics']),baseline['metrics']),output_hashes=baseline['output_hashes'],
                        historical_normalization_note='Legacy burden_matched/equal_power fields copied from old reference-sine normalization; this experiment uses only explicit same_wave_bare_baseline fields',
                        producer_kind=baseline['producer_kind'],producer_source_sha256=baseline['producer_source_sha256'],
                        postprocess=dict(baseline['postprocess'],reuse_only=True),
                        resources=dict(status='reused_verified_complete_basis',new_PDE=False),
                        source_case_sha256=manifest['guard_hashes'][str(Path(json.loads((output/'inputs/preparation-preregistration.json').read_text())['source_run'])/'cases/xy120-leader.json')],
                        reused_original_metrics_without_recomputation=True)
                    summary['reused_complete_basis_count']+=1
                else:
                    folder=output/'bases'/c['id']
                    if folder.exists():raise ValueError('Partial basis exists; preserve without retry')
                    if common.available_disk_bytes(output)<2*GIB+c['cells']*680:raise common.ValidationStop('disk_reserve',dict(status='disk_reserve'))
                    if summary['new_PDE_started']>=9:raise ValueError('New PDE cap reached')
                    summary['new_PDE_started']+=1;state['phase']='solving';persist()
                    resources=common.run_guarded(command(manifest)+[c['config_file'],str(folder)],output/'logs'/(c['id']+'.log'),
                        total_deadline=deadline,timeout_s=600-(time.monotonic()-watch['started']))
                    summary['new_PDE_count']+=1
                    v=json.loads((folder/'validation.json').read_text())
                    areas=common.check_numerical_gates(v,[folder/f'contacts-{f}.csv' for f in FREQUENCIES],15)
                    if v['cells']!=c['cells'] or not (folder/'BASIS_COMPLETE').is_file():raise ValueError('Incomplete basis/dimensions')
                    state['phase']='electrical_postprocessing';persist()
                    basis=load_basis(folder,2,FREQUENCIES)
                    producer_sha=manifest['guard_hashes'][str(ROOT/'CoatingRsBasis.java')]
                    key=hashlib.sha256((c['config_sha256']+producer_sha).encode()).hexdigest()[:18]
                    metrics=matched_rows(summarize(basis,c['design'],profiles[str(c['thickness_nm'])],key,c['h_xy_mm']),baseline['metrics'])
                    del basis;gc.collect()
                    result=dict(c,status='complete',basis_dir=str(folder),validation=v,physical_pad_areas_m2=areas,
                        metrics=metrics,resources=resources,producer_kind='private_CoatingRsBasis',producer_source_sha256=producer_sha,
                        analysis_code_sha256=manifest['guard_hashes'][str(ROOT/'coating_rs_validation.py')],
                        output_hashes={str(p):common.sha256(p) for p in folder.iterdir() if p.is_file()})
                    atomic(output/'cases'/(c['id']+'.json'),result)
                    state['phase']='native_and_spatial_postprocessing';persist()
                    try:
                        metadata=json.loads((folder/'mesh-metadata.json').read_text())
                        metadata.update(config_path=c['config_file'],config_sha256=c['config_sha256'],source_run_id=output.name,
                            source_condition_id=c['id'],source_hashes=manifest['guard_hashes'])
                        post=analyze_case(folder,metrics,metadata)
                        path=output/'postprocess'/(c['id']+'.json.gz')
                        with gzip.open(path,'wt',encoding='utf-8') as stream:json.dump(post,stream,ensure_ascii=False,allow_nan=False)
                        result['postprocess']=dict(status='complete',combined_status=post['status'],path=str(path),sha256=common.sha256(path),
                            native_probe_status='complete',spatial_status='complete' if post['verification']['spatial_all_complete'] else 'incomplete_or_failed')
                        if post['status'] != 'complete' or not post['verification']['spatial_all_complete']:
                            raise ValueError('Native probe passed but spatial postprocessing incomplete/failed; no completion inference')
                    except BaseException as error:
                        result['postprocess']=dict(result.get('postprocess',{}),status='failed',error=str(error));atomic(output/'cases'/(c['id']+'.json'),result)
                        summary['status']='postprocessing_failed';raise
                    resources.update(case_wall_seconds=time.monotonic()-watch['started'],driver_peak_rss_bytes=common.process_rss_bytes(os.getpid()))
                atomic(output/'cases'/(c['id']+'.json'),result);summary['cases'].append(result)
                common.assert_hashes_unchanged(manifest['guard_hashes']);persist()
                print(json.dumps(dict(case=c['id'],status='complete',new_PDE=not reused)),flush=True)
            summary['status']='complete';state.update(status='complete',phase='finished',current_case=None)
        except BaseException as error:
            if summary['status']!='postprocessing_failed':
                summary['status']='interrupted' if isinstance(error,(KeyboardInterrupt,SystemExit)) else 'stopped'
            summary.update(error=str(error),failed_case=active['id'] if active else None)
            if isinstance(error,common.ValidationStop):summary['failed_resources']=error.resources
            state.update(status=summary['status'],error=str(error));persist();raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
            signal.signal(signal.SIGTERM,oldterm);signal.signal(signal.SIGINT,oldint)
        persist();return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--execute',action='store_true');args=p.parse_args()
    result=execute(json.loads((args.output/'manifest.json').read_text())) if args.execute else prepare(args.output)
    print(json.dumps(dict(status=result['status'],completed_cases=len(result.get('cases',[])),actual_new_PDE=result.get('new_PDE_count',0))),flush=True)


if __name__=='__main__':main()
