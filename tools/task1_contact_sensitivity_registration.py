"""Prepare one paired Rs-window sensitivity; import has no research side effects.

Only the two existing XY80 geometries are allowed. Raw PBS complex impedance is
interpolated before one Rs subtraction and one measurement-area conversion.
This is a model sensitivity, not a calibrated skin-contact correction.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
FREQUENCIES = (3000, 3030, 9000, 9090)
CASE_IDS = ('baseline-square15-rs2000-xy80', 'cross17p5-arm10-rs2000-xy80')
MIN_REMAINING_SECONDS = 1380
PROFILE = ROOT/'tis-java/runs/explore-20261017T133224038032Z/inputs/eis-profiles.json'
FIT_ROOT = ROOT/'tis-java/runs/eis-rs-window-analysis-20261019T123730Z/cases'
NOMINAL_FIT = FIT_ROOT/'eis010-f0500.json'
ALTERNATE_FIT = FIT_ROOT/'eis010-f2000.json'
VOLUME_AUDIT = ROOT/'docs/cloud-continuation-20261021/volume-cross.json'
SOURCE_CASES = (
    ('cloud-mesh-c1-20261019T190000Z', 'baseline-square15-xy80'),
    ('cloud-cross-20261021T043000Z', 'cross17p5-arm10-xy80'))


def require(value, message):
    if not value:
        raise ValueError(message)


def parse_properties(text):
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    result = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '!')):
            continue
        require('=' in line, 'Only explicit key=value properties are supported')
        key, value = line.split('=', 1)
        key = key.strip()
        require(key and key not in result, 'Duplicate or empty property key')
        result[key] = value.strip()
    return result


def interpolate_raw_complex(points, frequency):
    require(math.isfinite(frequency) and frequency > 0 and len(points) >= 2,
            'Positive finite frequency and raw measured spectrum required')
    values = [(float(p['frequency_Hz']), float(p['Z_real_ohm']), float(p['Z_imag_ohm'])) for p in points]
    require(all(math.isfinite(v) for row in values for v in row) and
            all(row[0] > 0 for row in values) and
            all(a[0] < b[0] for a, b in zip(values, values[1:])),
            'Finite strictly increasing raw frequencies required')
    require(values[0][0] <= frequency <= values[-1][0], 'Frequency extrapolation prohibited')
    for f, re, im in values:
        if f == frequency:
            return complex(re, im)
    for (lo, re0, im0), (hi, re1, im1) in zip(values, values[1:]):
        if lo < frequency < hi:
            # Match the frozen update_ngg_eis.py arithmetic, including rounding.
            weight = math.log(frequency/lo)/math.log(hi/lo)
            return complex(re0+weight*(re1-re0), im0+weight*(im1-im0))
    raise ValueError('Measured frequency bracket unavailable')


def derive_contact_rows(profile, fit, frequencies=FREQUENCIES):
    area = float(profile['measurement_area_m2'])
    require(area == 1e-4, 'Approved exposed measurement area must remain1cm2=1e-4m2')
    require(fit.get('status') == 'complete' and fit.get('selected_subtraction_passive') is True,
            'Completed passive selected Rs fit required')
    rs = float(fit['selected_fit']['Rs_ohm'])
    require(math.isfinite(rs) and rs >= 0, 'Nonnegative finite selected Rs required')
    result = []
    for frequency in frequencies:
        measured = interpolate_raw_complex(profile['points'], frequency)
        contact = (measured-complex(rs, 0))*area
        require(math.isfinite(contact.real) and math.isfinite(contact.imag) and contact.real > 0,
                'Strictly positive contact real impedance required; no clipping')
        result.append(dict(frequency_Hz=frequency, area_real_ohm_m2=contact.real,
                           area_imag_ohm_m2=contact.imag))
    return result


def verify_nominal_contact(profile, nominal_fit, config):
    properties = parse_properties(config)
    require(properties.get('frequencies') == ','.join(map(str, FREQUENCIES)),
            'Exactly four registered spectral lines required')
    for row in derive_contact_rows(profile, nominal_fit):
        frequency = row['frequency_Hz']
        for suffix, key in (('re', 'area_real_ohm_m2'), ('im', 'area_imag_ohm_m2')):
            observed = float(properties[f'z.{frequency}.{suffix}'])
            require(math.isfinite(observed) and observed == row[key],
                    'Frozen nominal Rs500 config does not reproduce direct raw/one-area conversion')
    return True


def transform_config(text, mask_path, contact_rows):
    """Preserve all non-contact bytes/fields, including exact pad area and wiring."""
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    before = parse_properties(text)
    require(tuple(row['frequency_Hz'] for row in contact_rows) == FREQUENCIES,
            'Exactly ordered four contact frequencies required')
    changes = {'mask.path': str(mask_path)}
    for row in contact_rows:
        re, im = float(row['area_real_ohm_m2']), float(row['area_imag_ohm_m2'])
        require(math.isfinite(re) and math.isfinite(im) and re > 0, 'Passive finite specific impedance required')
        changes[f'z.{row["frequency_Hz"]}.re'] = format(re, '.17g')
        changes[f'z.{row["frequency_Hz"]}.im'] = format(im, '.17g')
    require(set(changes) <= set(before), 'Existing mask and contact keys required; no added physical fields')
    lines = []
    for line in text.splitlines(keepends=True):
        key = line.split('=', 1)[0].strip() if '=' in line else None
        if key in changes:
            newline = '\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
            lines.append(key+'='+changes[key]+newline)
        else:
            lines.append(line)
    output = ''.join(lines).encode('utf-8')
    after = parse_properties(output)
    require(set(after) == set(before) and all(after[k] == v for k, v in before.items() if k not in changes),
            'Geometry, area, material, source or wiring changed')
    return output


def _source_case(core, run_name, ident, volume):
    run = core.REPO/'data-native'/run_name
    registration_path = run/'preregistration.json'
    registration = core.read(registration_path)
    matches = [c for c in registration['cases'] if c['id'] == ident]
    require(len(matches) == 1, 'One exact source case required')
    case = copy.deepcopy(matches[0])
    record_path = run/'cases'/(ident+'.json')
    record = core.read(record_path)
    summary_path = Path(record['postprocess_path'])
    config, mask = Path(case['config_file']), Path(case['mask_file'])
    for path in (summary_path, config, mask):
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(run),
                'Source case must use existing regular files in its run')
    require(record.get('status') == 'complete' and core.sha(summary_path) == record['postprocess_sha256'] and
            core.sha(config) == case['config_sha256'] and core.sha(mask) == case['mask_sha256'],
            'Completed source case SHA evidence required')
    require(case['h_xy_mm'] == .625 and case['sc_cells'] == 2 and case['bulk_counts'] == [14, 14, 40]
            and case['channels'] == 2 and case['cells'] == 351680,
            'Fixed XY80/SC2/bulk14,14,40 two-output source required')
    require(all(record['validation'][key] <= limit for key, limit in core.GATES.items()),
            'Source native numerical gates failed')
    summary = core.read(summary_path)
    require(summary['status'] == 'complete' and summary['id'] == ident, 'Source summary not complete')
    circuit = case['circuit']
    require(circuit['n_pads'] == 4 and circuit['n_outputs'] == 2 and
            circuit['source_resistance_ohm'] == 50 and circuit['n_return_nodes'] == 1 and
            circuit['pad_to_node'] == {'0': 'out0', '1': 'out1', '2': 'GND', '3': 'GND'} and
            circuit['carrier_assignment_Hz'] == [3000, 3030], 'Physical four-pad/two-output common-GND circuit changed')
    params = parse_properties(config.read_bytes())
    require(params['h_mm'] == '0.625' and params['channels'] == '2' and
            params['validation.sc_cells'] == '2' and params['bulk.counts'] == '14,14,40',
            'Config mesh differs from registered source')
    pins = {str(path): core.sha(path) for path in (registration_path, record_path, summary_path, config, mask)}
    rows = [c for c in volume['cases'] if c['case_id'] == ident and c['run_id'] == run_name]
    require(len(rows) == 1 and rows[0]['summary_path'] == str(summary_path), 'Source volume audit must identify this exact case')
    for path, expected in volume['inputs_sha256'].items():
        if (str(run)+'/' in path and ('/audit/' in path or path in pins)):
            require(core.sha(path) == expected, 'Source volume/audit SHA mismatch')
            pins[path] = expected
    require(any('/audit/' in path for path in pins), 'Source full-skin audit evidence required')
    return case, config, mask, pins


def prepare_contact_sensitivity(run):
    """Caller owns dual global execution locks; prepare only, never executes PDE."""
    import task1_cloud_batch as core
    from task1_grouped_registration import _caller_owns_execution_lock
    started = time.monotonic()
    run = Path(run)
    core.paths_check(run)
    require(run.is_absolute() and run == run.resolve() and not run.exists(), 'New canonical unique run required')
    _caller_owns_execution_lock()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    budget_path = core.REPO/'runtime/task1-budget.json'
    budget = core.read(budget_path)
    require(budget['limit_seconds'] == 6600 and 6600-budget['spent_seconds'] >= MIN_REMAINING_SECONDS,
            'Need1200s PDE+120s preparation+60s root postprocess reserve in existing6600s')
    test_path = core.REPO/'tests/test_task1_contact_sensitivity_registration.py'
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip()
    for path in (Path(__file__).resolve(), test_path):
        require(subprocess.check_output(['git', 'show', commit+':'+str(path.relative_to(core.REPO))], cwd=core.REPO)
                == path.read_bytes(), 'Commit exact implementation and tests before preparation')
    integrity = core.original_integrity()
    profile_all, nominal, alternate = core.read(PROFILE), core.read(NOMINAL_FIT), core.read(ALTERNATE_FIT)
    profile = profile_all['10']
    require(profile['thickness_nm'] == 10 and len(profile['points']) == 30, 'Approved initial10nm30point profile required')
    raw = core.REPO/profile['source_file']
    for fit, cutoff in ((nominal, 500), (alternate, 2000)):
        require(fit['case_id'] == f'eis010-f{cutoff:04d}' and fit['cutoff_Hz'] == cutoff and
                fit['input']['thickness_nm'] == 10 and fit['input']['profile_key'] == '10' and
                fit['input_profile_file_sha256'] == core.sha(PROFILE) and
                fit['input']['source_XLSX_file_sha256'] == profile['source_sha256'] == core.sha(raw),
                'Approved raw profile/fit/source provenance mismatch')
    rows = derive_contact_rows(profile, alternate)
    volume = core.read(VOLUME_AUDIT)
    require(volume['status'] == 'calculated_unadopted' and volume['inputs_unchanged'] is True and
            volume['new_PDE_solves'] == 0, 'Completed unchanged source volume-cross audit required')
    sources = [_source_case(core, *source, volume) for source in SOURCE_CASES]
    for case, config, _, _ in sources:
        require(case['source_coating_nm'] == 10 and case['source_Rs_fit_window_Hz'] == 500,
                'Both source geometries must use nominal10nm Rs500')
        verify_nominal_contact(profile, nominal, config.read_bytes())
    bound = 2*351680*600
    require(bound <= core.LIMITS['max_batch_added_bytes'] and
            shutil.disk_usage(run.parent).free >= 2*core.GIB+bound,
            'Two complete raw bases plus unchanged2GiB reserve required')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).resolve().parent/'java')
    require(Path(javac).is_file() and Path(java).is_file(), 'Existing matching JDK required')
    pins = core.source_pins()
    evidence = [Path(__file__).resolve(), test_path, PROFILE, NOMINAL_FIT, ALTERNATE_FIT, raw, VOLUME_AUDIT]
    pins.update({str(path): core.sha(path) for path in evidence})
    for _, _, _, original_pins in sources:
        pins.update(original_pins)
    run.mkdir()
    succeeded, registration = False, None
    try:
        for directory in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes', 'frozen-inputs'):
            (run/directory).mkdir()
        # Small input evidence is frozen separately from the root-owned code snapshot.
        for name, expected in list(pins.items()):
            source = Path(name)
            if source.suffix not in ('.py', '.java'):
                target = run/'frozen-inputs'/source.relative_to(core.REPO)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                require(core.sha(target) == expected, 'Frozen input copy SHA mismatch')
                pins[str(target)] = expected
        cases, mappings = [], []
        model_payload = dict(contact='raw_initial10nm_PBS_minus_selected_Rs2000_once_area1cm2_v1',
            selected_fit_sha256=core.sha(ALTERNATE_FIT), source_profile_sha256=core.sha(PROFILE), rows=rows)
        model_sha = hashlib.sha256(json.dumps(model_payload, sort_keys=True).encode()).hexdigest()
        for index, (ident, (original, old_config, old_mask, _)) in enumerate(zip(CASE_IDS, sources)):
            mask, config = run/'masks'/(ident+'.csv'), run/'configs'/(ident+'.properties')
            shutil.copyfile(old_mask, mask)
            require(core.sha(mask) == core.sha(old_mask), 'Physical mask must remain byte-identical')
            config.write_bytes(transform_config(old_config.read_bytes(), mask, rows))
            case = copy.deepcopy(original)
            case.pop('baseline_same_grid_reference', None)
            case.update(id=ident, template_case_id=original['id'], source_run_id=run.name,
                source_Rs_fit_window_Hz=2000, selected_Rs_ohm=alternate['selected_fit']['Rs_ohm'],
                source_coating_nm=10, java_class='CloudShapeBasis', postprocessor='legacy_native',
                exporter_class='SelectivityShapeBasis', n_outputs=2, n_pads=4,
                config_file=str(config), config_sha256=core.sha(config), mask_file=str(mask), mask_sha256=core.sha(mask),
                physical_model_version=model_sha, contact_model_version=model_payload,
                contact_uncertainty='PBS window sensitivity only; actual skin contact unvalidated',
                status='preregistered_not_executed', candidate_adopted=False,
                mesh_convergence_validated=False, experimental_validation=False,
                baseline_reference_case_id=CASE_IDS[0], nominal_Rs500_reference_case_id=original['id'])
            if index == 0:
                case['control'] = 'original_four_square'
            case['cache_signature'] = core.check_cached_operator(case, run)
            cases.append(case)
            mappings.append(dict(source_config=str(old_config), source_sha256=core.sha(old_config),
                new_config=str(config), new_sha256=core.sha(config), source_mask=str(old_mask),
                unchanged_mask_sha256=core.sha(mask), allowed_changed_fields=['mask.path',
                    *(f'z.{f}.{part}' for f in FREQUENCIES for part in ('re', 'im'))],
                changed_physics='selected real Rs subtraction only; imaginary contact unchanged',
                pad_area_rescaled=False, second_Rs_subtraction=False))
        def command(argv, stream):
            elapsed = time.monotonic()-started
            allowance = min(120-elapsed, 6600-budget['spent_seconds']-elapsed-1260)
            require(allowance > 0 and shutil.disk_usage(run).free >= 2*core.GIB,
                    'Preparation120s or subsequent1260s budget/reserve unavailable')
            core.write(run/'controller.json', dict(status='preparing', phase='contact_compile_selftest',
                pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now(), command=argv))
            subprocess.run(argv, check=True, stdout=stream, stderr=subprocess.STDOUT, timeout=allowance)
        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'), str(core.SOURCE/'ExploreBasis.java'),
                str(core.SOURCE/'SelectivityShapeBasis.java'), str(core.REPO/'tools/java/CloudShapeBasis.java')], log)
            command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1', '-cp', str(run/'classes'),
                     'CloudShapeBasis', '--selftest'], log)
        for path in [*(run/'configs').glob('*'), *(run/'masks').glob('*'), *(run/'classes').glob('*')]:
            pins[str(path)] = core.sha(path)
        for name, expected in pins.items():
            require(core.sha(name) == expected, 'Pinned sensitivity input/source changed: '+name)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='paired_Rs2000_contact_sensitivity',
            status='prepared', created_utc=core.now(), source_commit=commit,
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',
            package_integrity=integrity, limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES),
            cases=cases, java=java, new_PDE_conditions_maximum=2, expected_raw_bound_bytes=bound,
            source_and_input_sha256=pins, preparation_seconds=time.monotonic()-started, path_mapping=mappings,
            scientific_question='Does contact-loss-limited arm10 versus square baseline ranking persist at selected Rs2000?',
            physical_model_version=model_sha, contact_model=model_payload,
            comparison_waveforms=['square_3h', 'sine', 'triangle_3h'],
            planned_normalizations=['raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
                                    'skin_contact_only', 'legacy_composite_full_skin'],
            root_postprocess_reserve_seconds=60, candidate_adopted=False,
            mesh_convergence_validated=False, experimental_validation=False,
            existing_XY_contact_model_holds_preserved=True,
            physical_limits='PBS model window uncertainty, not confidence interval, skin calibration or safety limit',
            storage=dict(native_location=str(run), persistent_backup_verified=False,
                         retirement_of_old_environment_allowed=False),
            frozen_source_snapshot_owner='standalone CLI calls core.freeze_sources once inside dual lock; API caller owns one freeze; small inputs frozen here',
            next_decision='Compare both geometries within each contact cohort and paired changes versus nominal500; no automatic adoption')
        require(registration['preparation_seconds'] <= 120 and
                6600-budget['spent_seconds']-registration['preparation_seconds'] >= 1260,
                'Preserve two600s conditions and60s root postprocess reserve')
        core.write(run/'preregistration.json', registration)
        core.write(run/'controller.json', dict(status='prepared', updated_utc=core.now()))
        succeeded = True
    except BaseException as error:
        core.write(run/'preparation-failure.json', dict(status='preparation_failed_preserved',
            error_type=type(error).__name__, error=str(error), observed_utc=core.now(),
            partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        elapsed = time.monotonic()-started
        budget['spent_seconds'] += elapsed
        budget['runs'].append(dict(run_id=run.name, stage='preparation', seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path, budget)
    return registration


def main():
    import argparse
    import fcntl
    import task1_cloud_batch as core
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = prepare_contact_sensitivity(args.output)
        core.freeze_sources(args.output.resolve())
    print(json.dumps(dict(status=result['status'], run=str(args.output), cases=list(CASE_IDS))))


if __name__ == '__main__':
    main()
