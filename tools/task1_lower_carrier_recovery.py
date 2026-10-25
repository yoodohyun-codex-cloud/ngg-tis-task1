#!/usr/bin/env python3
"""Recover a verified completed3k donor, then solve only eight lower-carrier RHS.

The fixed failed donor already completed3000/3030 native exports. This new
consumer validates/reuses those bytes before1000/1030/2000/2030 new solves. No
old file or failed evidence is modified. No old field is relabeled,
no frozen frequency constant is patched, and no PDE follows a failed regression.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import gc
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import threading
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
import numpy as np
import task1_cloud_batch as core
import task1_resource_policy as policy
import task1_frequency_resynthesis as prior
import task1_contact_sensitivity_registration as contact
import task1_candidate_screen as screen
import task1_lower_carrier_native_v2 as native

ROOT = core.REPO
GIB = core.GIB
SCHEMA = 'task1-lower-carrier-recovery-preregistration-v1'
REGRESSION_ID = 'regression-3000-3030'
LOWER_ID = 'lower-1000-1030-2000-2030'
JOBS = ((LOWER_ID, (1000, 1030, 2000, 2030)),)
DONOR_RUN = ROOT/'data-native/cloud-lower-carrier-20261021T152000Z'
DONOR_REGISTRATION_SHA256 = '362506b54723645bb1948131a801b35d2deb7a98250bf6aee9367113e92dd1ca'
DONOR_SOURCE_COMMIT = 'e0bb950eadfd6b9f0184d9628da18039b04d7fdb'
PAIRS = ((1000, 1030), (2000, 2030))
CONDITIONS = tuple(dict(id=f'sine-{a}-{b}-beat30', actual_fundamental_Hz=[a, b], beat_frequency_Hz=30) for a, b in PAIRS)
BASELINE_SUMMARY = ROOT/'data-native/cloud-mesh-c1-20261019T190000Z/postprocess/baseline-square15-xy80/summary.json'
SINE_REFERENCE = ROOT/'docs/cloud-next-frequency-20261021T104000Z/sine-3000-3030-beat30/condition.json'
VOLUME_REFERENCE = ROOT/'docs/cloud-next-20261021T085200Z/return-role-volume.json'
PROFILE = contact.PROFILE
FIT = contact.NOMINAL_FIT
COHORTS = ('cached_original_square_3000_3030_caps', 'cached_sine_3000_3030_caps')
require = core.require


def unit_coefficients(pair):
    require(tuple(pair) in (*PAIRS, (3000, 3030)), 'Only preregistered actual beat30Hz sine pairs are permitted')
    return {int(pair[0]):np.array([-1j, 0j]), int(pair[1]):np.array([0j, -1j])}


def electrical_for_pair(basis, coefficients, geometry, pair, sampler_class, directions, deadline):
    """Frequency-explicit two-output electrical readback; original0.5Vpeak basis."""
    expected = unit_coefficients(pair)
    require(set(coefficients) == set(expected) and all(np.array_equal(coefficients[f], expected[f]) for f in pair),
        'New sine outputs require their actual unit coefficients, never old harmonic factors')
    require(time.monotonic() < deadline, 'Lower-carrier electrical deadline')
    sampler = sampler_class(basis['grid'], geometry)
    contacts = basis['f'][pair[0]]['contacts']; area, pads = contacts['area_m2'], contacts['pad'].astype(int)
    j2, polar2, current2, losses = np.zeros(len(area)), np.zeros(len(area)), np.zeros(2), np.zeros(6)
    supplied, centres, current_spectra, metal_spectra, current_errors, power_errors = 0., {}, [], [], [], []
    for frequency in pair:
        row, coefficient = basis['f'][frequency], coefficients[frequency]
        require(np.array_equal(row['contacts'], contacts), 'Frequency contact identity differs')
        density, current = coefficient@row['density'], row['source']@coefficient
        power = np.einsum('i,kij,j->k', coefficient.conj(), row['loss'], coefficient).real
        source_power = float(.25*np.vdot(coefficient, current).real)
        integrated = np.array([np.sum(density[pads == i]*area[pads == i]) for i in range(2)])
        error = float(np.max(abs(integrated-current))/max(float(np.max(abs(current))), 1e-30))
        balance = float(abs(np.sum(density*area))/max(float(np.sum(abs(density)*area)), 1e-30))
        power_error = float(abs(power.sum()-source_power)/max(abs(source_power), 1e-20))
        require(max(error, balance) <= 2e-6 and power_error <= 2e-7, 'Actual lower-frequency driven conservation failed')
        stencil = sampler.stencil([0, 0, 20], geometry['gamma_S_m'][frequency])
        target = np.einsum('p,cpk->ck', stencil['weights'], row['field'][:, stencil['indices'], :])
        centres[frequency] = coefficient@target
        za = complex(float(basis['config'][f'z.{frequency}.re']), float(basis['config'][f'z.{frequency}.im']))
        j2 += abs(density)**2/2; polar2 += abs(density*za)**2/2; current2 += abs(current)**2/2
        losses += power; supplied += source_power; current_errors.append(max(error, balance)); power_errors.append(power_error)
        current_spectra.append(dict(frequency_Hz=frequency, real_A=current.real.tolist(), imaginary_A=current.imag.tolist()))
        metal = .5*coefficient-50*current
        metal_spectra.append(dict(frequency_Hz=frequency, real_V=metal.real.tolist(), imaginary_V=metal.imag.tolist()))
    jrms = np.sqrt(j2); order = np.argsort(jrms, kind='stable'); cumulative = np.cumsum(area[order])
    p95 = float(jrms[order[min(int(np.searchsorted(cumulative, .95*cumulative[-1], side='left')), len(order)-1)]])
    return dict(actual_fundamental_Hz=list(pair), beat_frequency_Hz=30,
        target20_modulation_V_m=float(2*np.minimum(abs(directions@centres[pair[0]]), abs(directions@centres[pair[1]])).max()),
        target20_total_E_RMS_V_m=float(np.sqrt(sum(np.vdot(v, v).real for v in centres.values())/2)),
        surface_J_RMS_max_A_m2=float(jrms.max()), surface_J_RMS_p95_A_m2=p95,
        contact_voltage_RMS_max_V=float(np.sqrt(polar2.max())), max_source_current_RMS_mA=float(np.sqrt(current2.max())*1000),
        source_current_RMS_by_output_mA=(np.sqrt(current2)*1000).tolist(), SC_power_W=float(losses[0]),
        contact_power_W=float(losses[4]), skin_power_W=float(losses[0]+losses[4]),
        tissue_contact_power_W=float(sum(losses[:5])), source_power_W=supplied, source_resistor_power_W=float(losses[5]),
        source_current_spectrum=current_spectra, loaded_metal_voltage_spectrum=metal_spectra,
        centre_field_spectrum=[dict(frequency_Hz=f, real_V_m=v.real.tolist(), imaginary_V_m=v.imag.tolist()) for f, v in centres.items()],
        driven_max_current_relative_error=max(current_errors), driven_max_power_relative_error=max(power_errors), sampled_direction_count=len(directions))


def implementation_receipt():
    inherited = prior.implementation_receipt()
    refs = dict(inherited['implementation_files_sha256'])
    paths = (Path(__file__).resolve(), Path(native.__file__).resolve(), Path(contact.__file__).resolve(), Path(screen.__file__).resolve(),
        ROOT/'tools/java/CloudFrequencyRecoveryBasis.java', ROOT/'tests/test_task1_lower_carrier_recovery.py',
        ROOT/'tests/test_task1_lower_carrier_native_v2.py', ROOT/'tests/test_cloud_frequency_recovery_basis.py')
    commit = inherited['implementation_git_commit']
    for path in paths:
        require(subprocess.check_output(['git', 'show', commit+':'+path.relative_to(ROOT).as_posix()], cwd=ROOT) == path.read_bytes(),
            'Commit all lower-carrier source/helper/tests before preparation: '+str(path))
        refs[str(path)] = core.sha(path)
    return dict(source_commit=commit, implementation_files_sha256=refs)


def changed_frequency_config(original, mask_path, mask_sha, frequencies, rows):
    before = contact.parse_properties(original)
    require(before['frequencies'] == '3000,3030,9000,9090' and before['channels'] == '2'
        and before['h_mm'] == '0.625' and before['validation.sc_cells'] == '2', 'Exact original same-grid source config required')
    require(tuple(row['frequency_Hz'] for row in rows) == tuple(frequencies), 'Exact actual-frequency impedance rows required')
    after = {k:v for k, v in before.items() if not k.startswith('z.')}
    after.update(frequencies=','.join(map(str, frequencies)), **{'mask.path':str(mask_path), 'mask.sha256':mask_sha})
    for row in rows:
        f = row['frequency_Hz']
        for suffix, key in (('re','area_real_ohm_m2'),('im','area_imag_ohm_m2')):
            name=f'z.{f}.{suffix}'
            # Preserve existing lexical bytes when the exact validated numeric
            # interface is unchanged, including producer-regression3k lines.
            after[name]=before[name] if name in before and float(before[name])==row[key] else format(row[key],'.17g')
    excluded = {'frequencies', 'mask.path', 'mask.sha256'}
    require({k:v for k,v in before.items() if not k.startswith('z.') and k not in excluded}
        == {k:v for k,v in after.items() if not k.startswith('z.') and k not in excluded}, 'Non-frequency physical input changed')
    return ''.join(k+'='+v+'\n' for k,v in after.items()).encode()


def require_regression_before_job(summary, case_id):
    if case_id == LOWER_ID:
        require(summary.get('producer_regression',{}).get('status')=='passed',
            'Producer regression must pass before any lower-frequency native job is started')


def check_existing_frequency_work(parent):
    """Do not enqueue a second copy of a completed or still-owned native plan."""
    for path in Path(parent).glob('cloud-*/preregistration.json'):
        existing=core.read(path)
        if existing.get('schema')!=SCHEMA:continue
        run=path.parent
        state=core.read(run/'controller.json')if(run/'controller.json').exists()else{}
        completed=core.read(run/'cases'/(LOWER_ID+'.json'))if(run/'cases'/(LOWER_ID+'.json')).exists()else{}
        require(state.get('status')not in ('prepared','running')and completed.get('status')!='calculated_unadopted',
            'Existing lower-carrier plan must be resumed/reused, never duplicated: '+str(run))


def donor_inventory(donor=DONOR_RUN):
    """Pin the one completed donor export; do not decode arrays or alter it."""
    donor=Path(donor).resolve()
    require(donor==DONOR_RUN.resolve(),'Only the fixed failed donor is authorized for recovery')
    pre_path=donor/'preregistration.json'
    require(core.sha(pre_path)==DONOR_REGISTRATION_SHA256,'Original donor registration SHA changed')
    pre=core.read(pre_path);failure=core.read(donor/'failure.json');summary=core.read(donor/'summary.json')
    controller=core.read(donor/'controller.json')
    require(pre['schema']=='task1-lower-carrier-preregistration-v1'and pre['status']=='prepared'
        and pre['source_commit']==DONOR_SOURCE_COMMIT and pre['gates']==core.GATES,
        'Exact original donor source and equation gate definitions required')
    require(failure==dict(status='failed_preserved',error='ValueError: Exact original full-face square mask required',
        current_case=REGRESSION_ID,phase='loading_native',evidence_preserved=True)
        and summary['status']=='failed_preserved'and summary['source_commit']==DONOR_SOURCE_COMMIT
        and summary['registration_sha256']==DONOR_REGISTRATION_SHA256
        and summary['error']==failure['error']and controller['status']=='failed_preserved',
        'Only the preserved post-export ULP-loader failure is eligible, never a failed PDE')
    require(not(donor/'bases'/LOWER_ID).exists(),'Donor lower bundle already attempted; do not duplicate it')
    require(not(donor/'producer-regression.json').exists(),'Donor regression result unexpectedly existed')
    refs={str(p):core.sha(p)for p in (pre_path,donor/'failure.json',donor/'summary.json',donor/'controller.json')}
    case=copy.deepcopy(next(c for c in pre['cases']if c['id']==REGRESSION_ID))
    require(case['actual_frequencies_Hz']==[3000,3030]and case['java_class']=='CloudFrequencyBasis',
        'Donor must be the completed two-frequency producer regression')
    for path,expected in pre['source_and_input_sha256'].items():
        p=Path(path)
        if p.suffix in ('.py','.java','.class','.json','.properties','.csv')and p.name!='grid.csv':
            require(p.is_file()and not p.is_symlink()and core.sha(p)==expected,'Original donor source/Java/config metadata drift: '+path)
            refs[str(p)]=expected
    basis=donor/'bases'/REGRESSION_ID
    require((basis/'BASIS_COMPLETE').is_file()and not(basis/'BASIS_COMPLETE').is_symlink(),
        'Donor native BASIS_COMPLETE marker is absent')
    progress=core.read(basis/'basis-progress.json');validation=core.read(basis/'validation.json');metadata=core.read(basis/'mesh-metadata.json')
    require(progress['status']=='complete'and progress['requested_basis_RHS_solves']==progress['completed_basis_RHS_solves']==4
        and progress['last_frequency_Hz']==3030 and progress['last_basis_channel']==1
        and progress['extra_potential_export_solves']==0,'Donor four-RHS export completion receipt required')
    require(metadata['exporter_class']=='CloudFrequencyBasis'and metadata['exporter_kind']=='frequency_native'
        and metadata['frequencies_Hz']==[3000,3030]and metadata['actual_basis_RHS_solves']==4
        and metadata['config_sha256']==case['config_sha256'],'Donor original native producer/config identity differs')
    require(all(type(validation[k])in(int,float)and math.isfinite(validation[k])and 0<=validation[k]<=limit
        for k,limit in core.GATES.items()),'Donor existing native equation gates failed')
    files={str(p):core.sha(p)for p in sorted(basis.iterdir())if p.is_file()and not p.is_symlink()}
    required={'BASIS_COMPLETE','validation.json','mesh-metadata.json','grid.csv.gz','runtime-wrapper.json','basis-progress.json'}
    for f in (3000,3030):
        required.update((f'field-{f}.bin.gz',f'potential-{f}.bin.gz',f'density-{f}.bin',f'source-{f}.bin',f'loss-{f}.bin',f'contacts-{f}.csv'))
    require({Path(name).name for name in files}==required,'Donor complete native export inventory differs')
    refs.update(files)
    manifest=donor/'frozen-source-manifest.json';refs[str(manifest)]=core.sha(manifest)
    frozen=core.read(manifest)
    require(frozen['source_commit']==DONOR_SOURCE_COMMIT,'Donor frozen source commit changed')
    for original,entry in frozen['files'].items():
        p=Path(entry['path'])
        require(pre['source_and_input_sha256'].get(original)==entry['sha256']and core.sha(p)==entry['sha256'],
            'Donor frozen source/Java bytes changed')
        refs[str(p)]=entry['sha256']
    return dict(run_path=str(donor),basis_path=str(basis),case=case,source_commit=DONOR_SOURCE_COMMIT,
        original_registration_SHA256=DONOR_REGISTRATION_SHA256,original_failure=dict(path=str(donor/'failure.json'),SHA256=refs[str(donor/'failure.json')]),
        original_java_source_sha256=pre['source_and_input_sha256'][str(ROOT/'tools/java/CloudFrequencyBasis.java')],
        actual_reused_RHS_solves=4,new_regression_RHS_solves=0,original_failure_preserved=True,
        input_sha256=refs,native_file_inventory_sha256=files,
        hash_capture_scope='First recovery hash inventory of completed native exports after preserved consumer failure; decoded regression remains a separate required gate')


def prepare(run):
    """Unique metadata/compile preparation; source hashes copied, no native reads."""
    started = time.monotonic(); run = Path(run).resolve(); core.paths_check(run)
    require(not run.exists(), 'Never overwrite/retry lower-carrier preparation')
    check_existing_frequency_work(run.parent)
    ledger_path = ROOT/'runtime/task1-budget.json'; ledger = policy.load_ledger(ledger_path)
    require(policy.remaining_seconds(ledger) >= 1800, 'Lower-carrier preparation requires authorized1800s remaining')
    donor=donor_inventory()
    charged=[entry for entry in ledger['runs']if entry.get('run_id')==DONOR_RUN.name
        and entry.get('stage')=='lower_carrier_regression_and_actual_sine']
    require(len(charged)==1 and charged[0]['status']=='failed_preserved'and charged[0]['seconds']>0,
        'Original donor failed-stage time charge must remain preserved exactly once')
    donor['original_failed_stage_charge']=copy.deepcopy(charged[0])
    implementation = implementation_receipt(); refs = core.source_pins(ledger)
    refs.update(implementation['implementation_files_sha256'])
    refs.update(donor['input_sha256'])
    source = prior.drive.baseline_item(BASELINE_SUMMARY)
    source_plan = prior.drive.make_preregistration(BASELINE_SUMMARY, run/'postprocess')
    refs.update(source_plan['input_sha256'])
    source_expected = source['summary']['input_sha256']
    refs.update(source_expected)  # copied declarations; no native field arrays read in preparation
    profile, fit = core.read(PROFILE)['10'], core.read(FIT)
    require(fit['selected_fit']['Rs_ohm'] == 236.5717747232937, 'Preserve nominal Rs500 selection, not old profile Rs1000 fit')
    contact.verify_nominal_contact(profile, fit, Path(source['case']['config_file']).read_bytes())
    square_row = next(row for row in core.read(VOLUME_REFERENCE)['cases'] if row['case_id'] == 'baseline-square15-xy80')
    sine = core.read(SINE_REFERENCE)
    require(sine['status'] == 'calculated_unadopted' and sine['source_provenance']['case_id'] == 'baseline-square15-xy80'
        and sine['actual_fundamental_Hz'] == [3000,3030], 'Completed actual sine3k reference required')
    require(square_row['fixed_same_grid_baseline_cutoffs_V_m']==sine['shared_square_baseline_cutoffs_V_m'],
        'Original square cutoff definitions disagree across immutable references')
    square_burden, square_current = prior.volume.burdens(source, source['conditions'][0])
    sine_burden = prior.candidate_burdens(sine['electrical_metrics'], sine['bulk_skin_J'], sine['layer_contact_source_losses'])
    comparisons = {COHORTS[0]:dict(id=source['conditions'][0]['id'], burdens=square_burden, currents=square_current, waveform='square_3h', actual_fundamental_Hz=[3000,3030]),
        COHORTS[1]:dict(id=sine['id'], burdens=sine_burden, currents=sine['electrical_metrics']['source_current_RMS_by_output_mA'], waveform='sine', actual_fundamental_Hz=[3000,3030])}
    for p in (PROFILE, FIT, VOLUME_REFERENCE, SINE_REFERENCE): refs[str(p)] = core.sha(p)
    require(shutil.disk_usage(run.parent).free >= 2*GIB+512*1024**2, 'Two native bundles plus existing2GiB reserve unavailable')
    run.mkdir(); succeeded = False
    try:
        for name in ('configs','masks','bases','cases','postprocess','logs','classes'): (run/name).mkdir()
        mask = run/'masks/baseline-four-square225.csv'; shutil.copyfile(source['case']['mask_file'], mask)
        require(core.sha(mask) == source['case']['mask_sha256'], 'Baseline mask must be byte-identical')
        refs[str(mask)] = core.sha(mask); cases = []
        for ident, frequencies in JOBS:
            rows = contact.derive_contact_rows(profile, fit, frequencies)
            config = run/'configs'/(ident+'.properties')
            config.write_bytes(changed_frequency_config(Path(source['case']['config_file']).read_bytes(), mask, core.sha(mask), frequencies, rows))
            case = copy.deepcopy(source['case'])
            case.update(id=ident, source_run_id=run.name, config_file=str(config), config_sha256=core.sha(config),
                mask_file=str(mask), mask_sha256=core.sha(mask), actual_frequencies_Hz=list(frequencies), java_class='CloudFrequencyRecoveryBasis',
                frequencies_Hz=list(frequencies),
                kind='producer_regression_only' if ident == REGRESSION_ID else 'two_actual_lower_carrier_sine_pairs',
                candidate_adopted=False)
            case['circuit'] = copy.deepcopy(source['circuit'])
            case['circuit'].update(carrier_assignment_Hz=list(frequencies)if ident==REGRESSION_ID else None,
                separate_sine_frequency_pairs_Hz=[[3000,3030]]if ident==REGRESSION_ID else [list(p)for p in PAIRS],harmonics_Hz=[],
                drive_condition_scope='Regression3kpair' if ident == REGRESSION_ID else 'Two separate sine pairs1000/1030 and2000/2030, never four-carrier TIS')
            refs[str(config)] = core.sha(config); cases.append(case)
        jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
        javac = shutil.which('javac') or str(jdk/'javac'); java = str(Path(javac).resolve().parent/'java')
        require(Path(javac).is_file() and Path(java).is_file(), 'Existing matching Java compiler/runtime required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            subprocess.run([javac,'-J-Xmx2g','-J-XX:ActiveProcessorCount=1','-encoding','UTF-8','-d',str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'),str(core.SOURCE/'ExploreBasis.java'),str(core.SOURCE/'SelectivityShapeBasis.java'),
                str(ROOT/'tools/java/CloudShapeBasis.java'),str(ROOT/'tools/java/CloudFrequencyRecoveryBasis.java')],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=max(.01,60-(time.monotonic()-started)))
            subprocess.run([java,'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudFrequencyRecoveryBasis','--selftest'],
                stdout=log,stderr=subprocess.STDOUT,check=True,timeout=max(.01,60-(time.monotonic()-started)))
        for p in (run/'classes').glob('*'): refs[str(p)] = core.sha(p)
        require(time.monotonic()-started < 60, 'Preparation finite60s deadline exceeded')
        pre = dict(schema=SCHEMA,status='prepared',created_utc=core.now(),source_commit=implementation['source_commit'],
            source_and_input_sha256=refs,input_sha256=refs,cases=cases,java=java,
            implementation_files_sha256=implementation['implementation_files_sha256'],
            source_baseline_summary=str(BASELINE_SUMMARY), source_baseline_native_input_sha256=source_expected,
            source_frozen_resolution=source_plan['frozen_source_resolution'], comparison_references=comparisons,
            donor_reference=donor,
            original_square_volume_reference_row=square_row,fixed_square_SC2_cutoffs_V_m=sine['shared_square_baseline_cutoffs_V_m'],
            conditions=[dict(c) for c in CONDITIONS],package_integrity=core.original_integrity(),
            limits=core.effective_limits(ledger),gates=core.GATES,resource_policy_refs=policy.policy_refs(ledger),
            resources=dict(whole_seconds=1800,native_job_seconds=600,per_scalar_condition_seconds=180,preparation_seconds=60,
                CPU_count=1,RSS_bytes=3*GIB,heap_bytes=2*GIB,disk_reserve_bytes=2*GIB,max_added_bytes=2*GIB),
            contact=dict(profile=str(PROFILE),profile_thickness_nm=10,fit=str(FIT),Rs_ohm=236.5717747232937,
                measured_area_m2=1e-4,method='Raw complex log-frequency interpolation; subtract selectedRs once; multiply measurement area once',
                warning='PBS interface surrogate, not verified actual skin contact; old profile selected_fit Rs1000 not used'),
            regression_required_before_lower_bundle=True,actual_new_native_RHS_solves_max=8,reused_regression_RHS_solves=4,
            historical_2000_2010_bare_is_distinct=True,candidate_adopted=False,full_convergence_validated=False,
            no_physiological_equivalence=True,probe_loading_validated=False)
        core.write(run/'preregistration.json',pre); core.freeze_sources(run)
        manifest = core.read(run/'frozen-source-manifest.json')
        refs[str(run/'frozen-source-manifest.json')] = core.sha(run/'frozen-source-manifest.json')
        for entry in manifest['files'].values(): refs[str(Path(entry['path']).resolve())] = entry['sha256']
        pre['source_and_input_sha256']=dict(refs);pre['input_sha256']=dict(refs)
        core.write(run/'preregistration.json',pre);core.write(run/'controller.json',dict(status='prepared',updated_utc=core.now()))
        succeeded = True
        return pre
    except BaseException as error:
        core.write(run/'preparation-failure.json',dict(status='failed_preserved',error=type(error).__name__+': '+str(error),automatic_retry=False));raise
    finally:
        elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
        ledger['runs'].append(dict(run_id=run.name,stage='lower_carrier_recovery_preparation',seconds=elapsed,
            status='prepared' if succeeded else 'failed_preserved',finished_utc=core.now()))
        core.write(ledger_path,ledger)


def verify_prepared(run, *, rehash_native=True):
    pre = core.read(run/'preregistration.json')
    require(pre['schema']==SCHEMA and pre['status']=='prepared' and pre['gates']==core.GATES
        and [(c['id'],tuple(c['actual_frequencies_Hz'])) for c in pre['cases']]==list(JOBS)
        and pre['conditions']==[dict(c)for c in CONDITIONS], 'Exact two-job finite lower-carrier registration required')
    require(implementation_receipt()['implementation_files_sha256']==pre['implementation_files_sha256'], 'Lower-carrier implementation changed')
    require(pre['donor_reference']['original_registration_SHA256']==DONOR_REGISTRATION_SHA256
        and pre['donor_reference']['basis_path']==str(DONOR_RUN/'bases'/REGRESSION_ID)
        and pre['donor_reference']['actual_reused_RHS_solves']==4
        and pre['donor_reference']['new_regression_RHS_solves']==0,'Exact immutable donor recovery reference required')
    for path,digest in pre['source_and_input_sha256'].items():
        p=Path(path)
        require(p.is_absolute()and p==p.resolve()and p.is_relative_to(ROOT)and p.is_file()and not p.is_symlink(), 'Canonical pinned input required')
        if rehash_native or p.suffix in ('.py','.java','.json','.properties','.class'):
            require(core.sha(p)==digest,'Pinned lower-carrier input changed: '+path)
    return pre


def derive_condition(basis,case,declared,geometry,volume_meta,cached,pre,post,scalar,probe,folder,deadline,checkpoint):
    pair=declared['actual_fundamental_Hz'];coeff=unit_coefficients(pair)
    spectra={f:np.einsum('c,cnk->nk',coeff[f],basis['f'][f]['field'])for f in pair}
    electrical=electrical_for_pair(basis,coeff,geometry,pair,post.LayeredPotentialSampler,post._DIRECTIONS,deadline)
    checkpoint('native_volume_projection',condition_id=declared['id'])
    weights={r:cached['arrays']['region_'+r+'_m3']for r in ('total','target','surface_0_5','subsurface_5_10','remaining','off_target')}
    evaluated=scalar.evaluate_volume(spectra,basis['grid'],volume_meta,fundamental_frequencies_Hz=pair,
        region_weights=weights,fibonacci_count=2048,chunk_cells=256,deadline_monotonic=deadline)
    arrays={k:evaluated['scalars'][k]for k in (*prior.volume.METRICS,'maxTIS_direction_index')}
    arrays.update({'region_'+k+'_m3':v for k,v in evaluated['region_weights_m3'].items()})
    np.savez_compressed(folder/'volume.npz',**arrays)
    prior.drive.write_json(folder/'native-volume-metrics.json',evaluated['metrics'])
    regions=prior.volume.region_weights(arrays,basis['grid'],basis['metadata'])
    balance=prior.carrier.carrier_metrics(spectra[pair[0]],spectra[pair[1]],evaluated['scalars']['maxTIS_direction_index'],evaluated['scalars']['maxTIS'],evaluated['scalars']['fixedTIS'])
    skin=prior.waveform.bulk_skin_current_density(spectra,basis['grid'],geometry['gamma_S_m'])
    losses=prior.waveform.layer_losses_from_matrices({f:basis['f'][f]['loss']for f in pair},{f:basis['f'][f]['source']for f in pair},coeff,electrical)
    burden=prior.candidate_burdens(electrical,skin,losses);currents=electrical['source_current_RMS_by_output_mA']
    provenance=dict(source_run_id=case['source_run_id'],source_condition_id=case['id'],source_candidate_id=declared['id'],
        input_sha256=post._digest(basis['hashes']),code_sha256=core.sha(__file__),result_sha256=post._digest(basis['validation']))
    checkpoint('native_phi_40probes',condition_id=declared['id'])
    probes=probe.evaluate_layered_probe(basis['grid'],{f:basis['f'][f]['potential']for f in pair},
        {f:basis['f'][f]['field']for f in pair},geometry,coeff,provenance=provenance,fundamental_frequencies_Hz=pair,
        tip_gap_mm=5.,plus_pitch_mm=5.,depths_mm=(5.,10.,15.,20.))
    for row in probes['measurements']:row.pop('time_plot',None)
    require(probes['status']=='complete'and probes['numerical_checks']['all_passed'],'Actual lower-frequency40phi/E probe check failed')
    prior.drive.write_json(folder/'probes.json',probes)
    field_audit=prior.waveform.field_check(dict(id=declared['id'],waveform='sine',actual_fundamental_Hz=pair,metrics=electrical))
    probe_audit=prior.waveform.probe_check(dict(id=declared['id'],probe40=probes))
    cohorts={}
    for name,reference in pre['comparison_references'].items():
        modes=prior.volume.normalization_modes(burden,reference['burdens'],sum(currents),sum(reference['currents']))
        for mode in modes.values():
            scale=mode['amplitude_scale'];mode['source_output_RMS_by_output_mA']=[v*scale for v in currents]
            mode['source_Vpp_by_output']=[scale,scale]
            mode['regions']=prior.volume.summarize_regions(evaluated['scalars'],regions,basis['grid'],scale,pre['fixed_square_SC2_cutoffs_V_m'])
            mode['carrier_and_balance_regions']={region:{key:prior.carrier.weighted(value if key.endswith('_balance')else value*scale,w,basis['grid'])
                for key,value in balance.items()if key in ('carrier0_RMS_V_m','carrier1_RMS_V_m','combined_fundamental_RMS_V_m','max_direction_balance','fixed_direction_balance')}
                for region,w in regions.items()}
            mode['probe40_unloaded']=prior.drive.scaled_probe_rows(probes,scale)
            require(time.monotonic()<deadline,'Lower-frequency scalar condition180s exceeded')
        cohorts[name]=dict(reference_id=reference['id'],reference_waveform=reference['waveform'],
            reference_actual_fundamental_Hz=reference['actual_fundamental_Hz'],normalizations=modes)
    checks=screen.screen_checks(dict(normalizations=cohorts[COHORTS[0]]['normalizations']),pre['original_square_volume_reference_row'])
    condition_circuit=copy.deepcopy(case['circuit']);condition_circuit['carrier_assignment_Hz']=list(pair)
    result=dict(schema='task1-lower-carrier-condition-v1',status='calculated_unadopted',**declared,
        source_provenance=dict(run_id=case['source_run_id'],native_case_id=case['id'],source_commit=pre['source_commit'],
            configuration_sha256=case['config_sha256'],native_input_sha256=basis['hashes'],circuit=condition_circuit),
        waveform='sine',source_Vpp_by_output=[1.,1.],coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coeff.items()},
        electrical_metrics=electrical,bulk_skin_J=skin,layer_contact_source_losses=losses,cohorts=cohorts,
        field_waveform_audit=field_audit,probe_waveform_audit=probe_audit,output_power_evidence=prior.carrier.output_power_evidence(electrical),
        canonical_square_cap_screen=dict(normalization='skin_contact_only',checks=checks,all_screen_checks_passed=all(c['passed']for c in checks),
            fixed_definition_source=str(screen.TEMPLATE),candidate_adopted=False,
            interpretation='Electrical screening only; pass permits separately registered convergence diagnostics, never adoption'),
        fixed_square_SC2_cutoffs_V_m=pre['fixed_square_SC2_cutoffs_V_m'],
        source_reference_scope='Actual new low-frequency native basis; cached3k data supply reference caps/weights only, never relabeled fields',
        new_physical_PDE_bundle=LOWER_ID,carrier_and_beat_scope='Allnewconditions beat30Hz; initialbare2000/2010Hz remains separate',
        candidate_adopted=False,full_convergence_validated=False,instrument_loading_validated=False,
        C1_status='No new frequency-matched true electrode-pair control computed',
        holds=['Native equation/waveform checks are separate from SC/XY/bulk/edge/contact convergence',
            'PBS surrogate is not validated actualskincontact; no activation/safety/physiological equivalence',
            '2074direction lower bound and40unloadedphi probes only'])
    prior.drive.write_json(folder/'condition.json',result)
    return dict(id=declared['id'],status=result['status'],actual_fundamental_Hz=pair,beat_frequency_Hz=30,
        canonical_screen_all_passed=result['canonical_square_cap_screen']['all_screen_checks_passed'],
        artifacts={name:dict(path=str(folder/name),SHA256=core.sha(folder/name))for name in ('condition.json','probes.json','volume.npz','native-volume-metrics.json')})


def execute(run):
    run=Path(run).resolve();core.paths_check(run)
    require(not(run/'execution-attempt.json').exists(),'Never retry attempted lower-carrier execution')
    ledger_path=ROOT/'runtime/task1-budget.json';ledger=policy.load_ledger(ledger_path)
    require(policy.remaining_seconds(ledger)>=1800,'Lower-carrier execution admission requires1800s remaining')
    pre=verify_prepared(run);require(pre['limits']==core.effective_limits(ledger),'Resource policy limits changed')
    require(pre['resource_policy_refs']==policy.policy_refs(ledger),'Immutable resource authorization changed')
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    started=time.monotonic();deadline=started+1800;phase_deadline=[deadline];pid=os.getpid();child=[None]
    initial_free=shutil.disk_usage(run).free;peak=[core.rss(pid)];stop=threading.Event();guard_errors=[];mutex=threading.RLock()
    state=dict(status='running',pid=pid,proc_start_ticks=core.ticks(pid),started_utc=core.now(),phase='starting',current_case=None)
    summary=dict(schema='task1-lower-carrier-recovery-result-v1',status='running',run_id=run.name,source_commit=pre['source_commit'],
        registration_sha256=core.sha(run/'preregistration.json'),cases=[],conditions=[],new_native_jobs_started=0,
        candidate_adopted=False,full_convergence_validated=False,experimentally_validated=False)
    core.write(run/'execution-attempt.json',dict(pid=pid,proc_start_ticks=state['proc_start_ticks'],started_utc=core.now()))
    def checkpoint(phase,**extra):
        with mutex:
            state.update(phase=phase,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started,**extra)
            core.write(run/'controller.json',state);core.write(run/'summary.json',summary)
    def interrupt(signum,frame):raise RuntimeError(guard_errors[0]if guard_errors else 'Controlled lower-carrier signal '+str(signum))
    previous={s:signal.getsignal(s)for s in (signal.SIGTERM,signal.SIGINT,signal.SIGUSR1,signal.SIGALRM)}
    for sig in previous:signal.signal(sig,interrupt)
    def monitor():
        last=0.
        while not stop.wait(.25):
            try:
                current=child[0];value=core.rss(pid)+(core.rss(current.pid)if current is not None else 0)
                peak[0]=max(peak[0],value);free=shutil.disk_usage(run).free;t=time.monotonic()
                require(value<3*GIB,'Aggregate RSS3GiB limit');require(free>=2*GIB and initial_free-free<=2*GIB,'Disk reserve/added2GiB limit')
                require(t<deadline and t<phase_deadline[0],'Finite lower-carrier whole/native/scalar deadline')
                require(not any((run/n).exists()for n in ('STOP','needs_attention','needs_physical_validation')),'Stopped by marker')
                if t-last>=5:
                    with mutex:core.write(run/'heartbeat.json',dict(state,observed_utc=core.now(),aggregate_RSS_bytes=value,
                        peak_aggregate_RSS_bytes=peak[0],disk_free_bytes=free,elapsed_seconds=t-started))
                    last=t
            except BaseException as error:guard_errors.append(str(error));os.kill(pid,signal.SIGUSR1);return
    thread=threading.Thread(target=monitor,daemon=True);failure=None
    try:
        thread.start();checkpoint('verify_native_references');all_native_hashes={}
        # Frozen generic samplers are imported only here, under global execution lock.
        source=prior.drive.baseline_item(BASELINE_SUMMARY)
        cached=prior.volume.load_native(source)
        post,scalar,probe=prior.drive.import_frozen(source['run'],dict(input_sha256=pre['source_and_input_sha256']))
        phase_deadline[0]=min(deadline,time.monotonic()+180)
        donor=pre['donor_reference'];donor_case=donor['case']
        checkpoint('loading_completed_donor_regression',current_case=REGRESSION_ID,current_config_sha256=donor_case['config_sha256'])
        donor_basis=native.load_basis(Path(donor['basis_path']),donor_case,phase_deadline[0])
        require(np.array_equal(donor_basis['grid'],cached['grid']),'Donor grid differs from original ROI weight geometry')
        all_native_hashes.update(donor_basis['hashes'])
        checkpoint('validating_reused_donor_regression')
        comparison=native.strict_regression_compare(donor_basis,source['run']/'bases'/source['case']['id'],phase_deadline[0])
        require(len(comparison['comparisons'])==10 and comparison['inputs_unchanged'] is True
            and comparison['decoded_grid_and_contact_identity'] is True,
            'All ten decoded regression comparisons and unchanged input bindings are required before any new PDE')
        comparison.update(reused_from_donor=dict(run_path=donor['run_path'],basis_path=donor['basis_path'],
            original_registration_SHA256=donor['original_registration_SHA256'],source_commit=donor['source_commit'],
            original_failure=donor['original_failure'],native_file_inventory_sha256=donor['native_file_inventory_sha256']),
            reused_regression_RHS_solves=4,new_regression_RHS_solves=0)
        all_native_hashes.update(comparison['input_sha256']);core.write(run/'producer-regression.json',comparison)
        summary['producer_regression']=dict(path=str(run/'producer-regression.json'),SHA256=core.sha(run/'producer-regression.json'),status=comparison['status'])
        summary['donor_reference']=dict(run_path=donor['run_path'],basis_path=donor['basis_path'],source_commit=donor['source_commit'],
            original_registration_SHA256=donor['original_registration_SHA256'],original_failure=donor['original_failure'],
            native_file_inventory_sha256=donor['native_file_inventory_sha256'],
            original_failed_stage_charge=donor['original_failed_stage_charge'],reused_regression_RHS_solves=4,new_regression_RHS_solves=0)
        require(comparison['status']=='passed'and all(c['passed']is True for c in comparison['comparisons']),
            'Reused donor decoded-array regression failed; lowerbundle notstarted')
        reused_record=dict(id=REGRESSION_ID,status='producer_regression_passed_reused',validation=donor_basis['validation'],
            diagnostic_only=True,reused_regression_RHS_solves=4,new_RHS_solves=0,source_donor_run=donor['run_path'],
            configuration_sha256=donor_case['config_sha256'],new_scientific_candidate=False)
        core.write(run/'cases'/(REGRESSION_ID+'.json'),reused_record);summary['cases'].append(reused_record)
        del donor_basis;gc.collect()
        for case in pre['cases']:
            require_regression_before_job(summary,case['id'])
            verify_prepared(run)
            phase_deadline[0]=min(deadline,time.monotonic()+600)
            checkpoint('solving',current_case=case['id'],current_config_sha256=case['config_sha256'])
            basis_dir=run/'bases'/case['id'];require(not basis_dir.exists(),'Never overwrite native basis attempt')
            command=[pre['java'],'-Xmx2g','-XX:+UseSerialGC','-XX:ActiveProcessorCount=1','-cp',str(run/'classes'),'CloudFrequencyRecoveryBasis',
                '--execute-parent',str(pid),str(state['proc_start_ticks']),case['config_file'],str(basis_dir)]
            with(run/'logs'/(case['id']+'.log')).open('x')as log:
                child[0]=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
                summary['new_native_jobs_started']+=1;checkpoint('solving',java_pid=child[0].pid,java_proc_start_ticks=core.ticks(child[0].pid))
                code=child[0].wait(timeout=max(.01,phase_deadline[0]-time.monotonic()));child[0]=None
                require(code==0,'CloudFrequencyRecoveryBasis exit '+str(code))
            checkpoint('loading_native',java_pid=None)
            basis=native.load_basis(basis_dir,case,phase_deadline[0])
            all_native_hashes.update(basis['hashes'])
            require(np.array_equal(basis['grid'],cached['grid']),'Lower-carrier grid differs from original ROI weight geometry')
            if case['id']==REGRESSION_ID:
                checkpoint('producer_regression')
                comparison=native.strict_regression_compare(basis,source['run']/'bases'/source['case']['id'],phase_deadline[0])
                all_native_hashes.update(comparison['input_sha256'])
                core.write(run/'producer-regression.json',comparison)
                require(comparison['status']=='passed','New native adapter regression failed; lowerbundle notstarted')
                summary['producer_regression']=dict(path=str(run/'producer-regression.json'),SHA256=core.sha(run/'producer-regression.json'),status='passed')
                record=dict(id=case['id'],status='producer_regression_passed',validation=basis['validation'],actual_RHS_solves=4,
                    diagnostic_only=True,configuration_sha256=case['config_sha256'],new_scientific_candidate=False)
                del basis;gc.collect()
            else:
                require(summary.get('producer_regression',{}).get('status')=='passed','Regression prerequisite absent')
                geometry,volume_meta=native.geometry(basis,case)
                for declared in pre['conditions']:
                    phase_deadline[0]=min(deadline,time.monotonic()+180)
                    folder=run/'postprocess'/declared['id'];folder.mkdir()
                    summary['conditions'].append(derive_condition(basis,case,declared,geometry,volume_meta,cached,pre,post,scalar,probe,
                        folder,phase_deadline[0],checkpoint))
                record=dict(id=case['id'],status='calculated_unadopted',validation=basis['validation'],actual_RHS_solves=8,
                    configuration_sha256=case['config_sha256'],actual_frequency_Hz=case['actual_frequencies_Hz'])
                summary['new_native_input_sha256']=dict(basis['hashes'])
            core.write(run/'cases'/(case['id']+'.json'),record);summary['cases'].append(record)
            checkpoint('native_job_complete')
        phase_deadline[0]=deadline
        verify_prepared(run)
        require(all(core.sha(path)==expected for path,expected in all_native_hashes.items()),'Native input changed during actual-frequency postprocessing')
        summary.update(status='calculated_unadopted',inputs_unchanged=True,input_sha256=dict(pre['source_and_input_sha256'],**all_native_hashes),
            resources=dict(wall_seconds=time.monotonic()-started,max_whole_seconds=1800,native_job_seconds=600,scalar_condition_seconds=180,
                CPU_count=1,global_limit_seconds=policy.effective_limit(ledger),peak_aggregate_RSS_bytes=peak[0],actual_native_RHS_solves=8,reused_regression_RHS_solves=4),
            actual_frequency_pairs=[list(p)for p in PAIRS],actual_beat_frequencies_Hz=[30,30],
            holds=['New producer regression is same discrete operator/code-path validation, not independent solver verification',
                'No mesh/contact/experimental/physiological validation promotion; no candidate adoption',
                'Initialbare2000/2010Hz remains a separatehistoricalcohort;40probesunloaded'])
        checkpoint('complete',status='complete')
        return summary
    except BaseException as error:
        failure=type(error).__name__+': '+str(error)
        summary.update(status='failed_preserved',error=failure,inputs_unchanged=False,automatic_retry=False)
        core.write(run/'failure.json',dict(status='failed_preserved',error=failure,current_case=state['current_case'],phase=state['phase'],evidence_preserved=True))
        checkpoint('failed_preserved',status='failed_preserved');raise
    finally:
        current=child[0]
        if current is not None and current.poll() is None:
            try:os.killpg(current.pid,signal.SIGTERM);current.wait(timeout=3)
            except (ProcessLookupError,subprocess.TimeoutExpired):
                if current.poll() is None:os.killpg(current.pid,signal.SIGKILL);current.wait(timeout=3)
        stop.set()
        if thread.ident is not None:thread.join(timeout=1)
        elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
        ledger['runs'].append(dict(run_id=run.name,stage='lower_carrier_recovery_actual_sine',seconds=elapsed,
            status=summary['status'],error=failure,finished_utc=core.now()))
        core.write(ledger_path,ledger);core.write(run/'summary.json',summary)
        for sig,handler in previous.items():signal.signal(sig,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--prepare',action='store_true');mode.add_argument('--execute',action='store_true')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run=args.output.resolve()
    with(ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=prepare(run)if args.prepare else execute(run)
    print(json.dumps(dict(status=result['status'],run=str(run))))


if __name__=='__main__':main()
