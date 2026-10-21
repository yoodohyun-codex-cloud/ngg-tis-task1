"""Prepare one role permutation of the completed asymmetric physical pads.

Only preparation is exposed. No work occurs on import; the existing finite
controller remains the sole PDE executor. Physical outlines and contact patches
are unchanged, while the two signal pads and common-GND pads exchange roles.
"""
from __future__ import annotations

import copy
import csv
import fcntl
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import task1_cloud_batch as core
import task1_contact_sensitivity_registration as contact
from task1_grouped_registration import _caller_owns_execution_lock, _mesh

SOURCE_RUN = 'cloud-asymmetric-20261021T051000Z'
SOURCE_ID = 'asym-cross281p25-return168p75-xy80'
CASE_ID = 'return-cross281p25-signal168p75-xy80'
OLD_TO_NEW = {0: 2, 1: 3, 2: 0, 3: 1}
OLD_CENTRES = ((-10., -10.), (10., 10.), (10., -10.), (-10., 10.))
EXPECTED_AREAS_MM2 = (168.75, 168.75, 281.25, 281.25)
EXPECTED_FACES = (432, 432, 720, 720)
EXPECTED_CELLS = 351680
EXPECTED_RAW_BOUND_BYTES = EXPECTED_CELLS*600
MIN_REMAINING_SECONDS = 900
PREPARATION_SECONDS = 60
EXECUTION_AND_VALIDATION_RESERVE = 600+180+60
VOLUME = core.REPO/'docs/cloud-continuation-20261021/volume-asymmetric.json'


def _mapping(mapping):
    core.require(mapping == OLD_TO_NEW and all(type(k) is int and type(v) is int for k, v in mapping.items()),
                 'Only the registered old2/3 to signal and old0/1 to common-GND permutation is allowed')


def _check_source_design(design):
    core.require(design['id'] == SOURCE_ID.removesuffix('-xy80') and design['total_pads'] == 4 and
        design['source_outputs'] == 2 and design['phantom_diameter_mm'] == 50 and
        design['contact_plane_z_mm'] == 0 and design['return_connection'] == 'all_return_pads_ideal_common_GND'
        and len(design['pads']) == 4, 'Exact original top four-pad/two-output D50 design required')
    for old, pad in enumerate(design['pads']):
        core.require(pad['pad'] == old and tuple(pad['center_mm']) == OLD_CENTRES[old] and
            pad['rotation_deg'] == 0 and pad['corner_radius_mm'] == 0 and
            pad['role'] == ('signal' if old < 2 else 'common_gnd_return') and
            pad['source_output'] == (old if old < 2 else None), 'Original physical pad identity/wiring differs')
        if old < 2:
            core.require(pad['shape'] == 'cross' and pad['width_mm'] == pad['height_mm'] ==
                pad['outer_length_mm'] == 17.5 and pad['arm_width_mm'] == 12.5 and
                pad['area_mm2'] == pad['analytic_area_mm2'] == 281.25, 'Original cross geometry differs')
        else:
            core.require(pad['shape'] == 'rectangle' and pad['width_mm'] == 15 and pad['height_mm'] == 11.25 and
                pad['area_mm2'] == pad['analytic_area_mm2'] == 168.75, 'Original rectangle geometry differs')


def remap_design(source_design, mapping=OLD_TO_NEW):
    _mapping(mapping)
    _check_source_design(source_design)
    design = copy.deepcopy(source_design)
    pads = [None]*4
    for old, new in mapping.items():
        pad = copy.deepcopy(source_design['pads'][old])
        pad.update(pad=new, role='signal' if new < 2 else 'common_gnd_return',
                   source_output=new if new < 2 else None)
        pads[new] = pad
    design.update(id=CASE_ID.removesuffix('-xy80'), pads=pads,
        xy_mm=[list(pad['center_mm']) for pad in pads],
        group='fixed_physical_geometry_source_return_role_permutation',
        physical_total_contact_area_mm2=900.,
        area_policy='Same physical900mm2 patches; only signal/common-GND role assignment changes',
        geometry_revision='original-asymmetric-physical-patches-role-permutation-v1')
    if 'xy_mm' in design:
        design['xy_mm'] = [copy.deepcopy(pad['center_mm']) for pad in pads]
    return design


def relabel_mask(source_rows, source_design, mapping=OLD_TO_NEW):
    """Validate the exact old patches and change only their physical pad labels."""
    _mapping(mapping)
    _check_source_design(source_design)
    h = .625
    face = (h/1000)**2
    expected = set()
    for pad, (x, y) in enumerate(OLD_CENTRES):
        for j in range(80):
            for i in range(80):
                dx, dy = -25+(i+.5)*h-x, -25+(j+.5)*h-y
                active = ((abs(dx) < 8.75 and abs(dy) < 6.25) or
                          (abs(dx) < 6.25 and abs(dy) < 8.75)) if pad < 2 else (
                          abs(dx) < 7.5 and abs(dy) < 5.625)
                if active:
                    expected.add((pad, i, j))
    actual, occupied, rows = set(), set(), []
    for row in source_rows:
        core.require(len(row) == 4, 'Four-column physical mask required')
        pad, i, j, area = row
        core.require(all(type(v) is int for v in (pad, i, j)) and type(area) in (int, float) and
            math.isfinite(area) and math.isclose(area, face, rel_tol=1e-12, abs_tol=0), 'Exact full-face mask required')
        core.require((pad, i, j) not in actual and (i, j) not in occupied, 'Duplicate/overlapping physical contact')
        actual.add((pad, i, j)); occupied.add((i, j))
        core.require(pad in mapping, 'Unknown original pad label')
        rows.append((mapping[pad], i, j, area))
    core.require(actual == expected and len(rows) == 2304, 'Original asymmetric physical mask must be unchanged')
    rows.sort(key=lambda row: (row[0], row[2], row[1]))
    counts = [sum(row[0] == pad for row in rows) for pad in range(4)]
    areas = [math.fsum(row[3] for row in rows if row[0] == pad) for pad in range(4)]
    core.require(tuple(counts) == EXPECTED_FACES and all(math.isclose(area, expected*1e-6,
        rel_tol=1e-12, abs_tol=0) for area, expected in zip(areas, EXPECTED_AREAS_MM2)), 'Remapped physical areas differ')
    receipt = dict(rule='exact-existing-physical-mask-pad-role-permutation-v1', h_xy_mm=h,
        old_to_new_pad=mapping, faces_per_pad=counts, represented_pad_areas_m2=areas,
        contacts=2304, physical_total_contact_area_mm2=900., physical_union_unchanged=True,
        per_physical_pad_patches_unchanged=True, partial_faces=0, discarded_slivers=0,
        renormalization=False, geometry_convergence_claimed=False)
    return rows, areas, receipt


def remap_config(data, mask_path, mask_sha, areas, design):
    """Move every pad metadata suffix; preserve every non-pad physical property."""
    core.require(len(areas) == 4 and all(math.isclose(a, e*1e-6, rel_tol=1e-12, abs_tol=0)
        for a, e in zip(areas, EXPECTED_AREAS_MM2)), 'Registered remapped areas required')
    core.require(len(mask_sha) == 64 and all(c in '0123456789abcdef' for c in mask_sha), 'SHA256 mask pin required')
    before = contact.parse_properties(data)
    groups = {pad: {} for pad in range(4)}
    for key, value in before.items():
        if key.startswith('pad.'):
            parts = key.split('.', 2)
            core.require(len(parts) == 3 and parts[1] in ('0', '1', '2', '3') and parts[2], 'Unknown pad metadata key')
            groups[int(parts[1])][parts[2]] = value
    required = {'represented_area_m2', 'shape', 'width_mm', 'height_mm', 'rotation_deg', 'analytic_area_mm2', 'x_mm', 'y_mm'}
    core.require(all(required <= set(group) for group in groups.values()), 'Complete original pad geometry metadata required')
    changed = {'mask.path': str(mask_path), 'mask.sha256': mask_sha}
    core.require(set(changed) <= set(before), 'Original explicit mask fields required')
    for old, new in OLD_TO_NEW.items():
        for suffix, value in groups[old].items():
            changed[f'pad.{new}.{suffix}'] = value
        pad = design['pads'][new]
        core.require(pad['pad'] == new and float(groups[old]['represented_area_m2']) == areas[new] and
            groups[old]['shape'] == pad['shape'] and float(groups[old]['x_mm']) == pad['center_mm'][0] and
            float(groups[old]['y_mm']) == pad['center_mm'][1], 'Remapped physical metadata differs from patches')
    output, inserted = [], False
    for line in data.splitlines(keepends=True):
        key = line.split(b'=', 1)[0].decode('utf-8').strip() if b'=' in line else None
        if key and key.startswith('pad.'):
            if not inserted:
                output.extend((k+'='+v+'\n').encode() for k, v in changed.items() if k.startswith('pad.'))
                inserted = True
            continue
        if key in ('mask.path', 'mask.sha256'):
            ending = b'\r\n' if line.endswith(b'\r\n') else b'\n' if line.endswith(b'\n') else b''
            output.append((key+'='+changed[key]).encode()+ending)
        else:
            output.append(line)
    result = b''.join(output)
    after = contact.parse_properties(result)
    core.require(all(after[k] == value for k, value in before.items() if not k.startswith('pad.') and
        k not in ('mask.path', 'mask.sha256')), 'Material/contact/frequency/grid/circuit changed')
    core.require({k: v for k, v in after.items() if k.startswith('pad.')} ==
        {k: v for k, v in changed.items() if k.startswith('pad.')}, 'Incomplete or stale pad metadata remap')
    return result, {key: after.get(key) for key in set(before) | set(after) if before.get(key) != after.get(key)}


def verify_decision(path):
    path = Path(path).resolve()
    decision = core.read(path)
    core.require(decision.get('schema') == 'task1-return-role-decision-v1' and
        decision.get('status') == 'preregistered_not_started' and decision.get('source_run_id') == SOURCE_RUN and
        decision.get('source_case_id') == SOURCE_ID and decision.get('chosen_case_id') == CASE_ID and
        isinstance(decision.get('chosen_wiring_question'), str) and decision['chosen_wiring_question'].strip() and
        decision.get('adopted') is False, 'Explicit native-evidence wiring decision required; ROI-only selection is insufficient')
    native = decision['native_audit']; audit_path = Path(native['path']).resolve()
    core.require(audit_path.is_file() and not audit_path.is_symlink() and core.sha(audit_path) == native['SHA256'],
                 'Completed native causal audit SHA mismatch')
    audit = core.read(audit_path)
    core.require(audit.get('status') in ('complete_diagnostic_only', 'complete_cached_native_causal_audit',
        'calculated_unadopted') and audit.get('inputs_unchanged') is True, 'Completed unchanged native causal audit required')
    declared = decision['inputs_sha256']; observed = audit.get('inputs_sha256', audit.get('input_sha256', {}))
    source = core.REPO/'data-native'/SOURCE_RUN
    required = (source/'postprocess'/SOURCE_ID/'summary.json', source/'configs'/(SOURCE_ID+'.properties'),
                source/'masks'/(SOURCE_ID+'.csv'))
    pins = {str(path): core.sha(path), str(audit_path): native['SHA256']}
    for item in required:
        expected = core.sha(item)
        core.require(declared.get(str(item)) == expected and observed.get(str(item)) == expected,
                     'Decision and native audit must bind original source summary/config/mask')
    for name, expected in declared.items():
        item = Path(name).resolve()
        core.require(item.is_file() and not item.is_symlink() and core.sha(item) == expected, 'Decision input SHA changed: '+name)
        pins[str(item)] = expected
    return decision, pins


def prepare_return_role(run, decision_path):
    started = time.monotonic(); run = Path(run)
    core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve() and not run.exists(), 'New unique canonical run required')
    _caller_owns_execution_lock(); os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    budget_path = core.REPO/'runtime/task1-budget.json'; budget = core.read(budget_path)
    core.require(budget['limit_seconds'] == 6600 and math.isfinite(budget['spent_seconds']) and
        0 <= budget['spent_seconds'] <= 6600-MIN_REMAINING_SECONDS, 'Need900s inside unchanged6600s ledger')
    succeeded = False
    try:
        decision, decision_pins = verify_decision(decision_path)
        volume = core.read(VOLUME)
        core.require(volume['status'] == 'calculated_unadopted' and volume['inputs_unchanged'] is True,
                     'Completed source-bound asymmetric volume audit required')
        source, old_config, old_mask, source_pins = contact._source_case(core, SOURCE_RUN, SOURCE_ID, volume)
        core.require(source.get('java_class', 'CloudShapeBasis') == 'CloudShapeBasis', 'Original CloudShapeBasis ABI required')
        design = remap_design(source['design'])
        with old_mask.open() as stream:
            reader = csv.DictReader(stream)
            core.require(reader.fieldnames == ['pad', 'i', 'j', 'area_m2'], 'Original physical mask schema differs')
            old_rows = [(int(r['pad']), int(r['i']), int(r['j']), float(r['area_m2'])) for r in reader]
        rows, areas, mask_receipt = relabel_mask(old_rows, source['design'])
        pins = core.source_pins(); pins.update(source_pins); pins.update(decision_pins)
        test = core.REPO/'tests/test_task1_return_role_registration.py'
        for p in (Path(__file__).resolve(), test, Path(contact.__file__).resolve(), VOLUME): pins[str(p)] = core.sha(p)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip()
        for name, expected in pins.items():
            p = Path(name); core.require(core.sha(p) == expected, 'Pinned source changed: '+name)
            if p.suffix in ('.py', '.java') or p == Path(decision_path).resolve():
                core.require(p.is_relative_to(core.REPO) and subprocess.check_output(
                    ['git', 'show', commit+':'+str(p.relative_to(core.REPO))], cwd=core.REPO) == p.read_bytes(),
                    'Implementation/tests/decision must be committed before preparation: '+name)
        core.require(shutil.disk_usage(run.parent).free >= 2*core.GIB+EXPECTED_RAW_BOUND_BYTES,
                     'Raw storage plus2GiB reserve unavailable')
        integrity = core.original_integrity()
        run.mkdir()
        for directory in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes', 'geometry-audit'):
            (run/directory).mkdir()
        mask = run/'masks'/(CASE_ID+'.csv')
        with mask.open('x', newline='') as stream:
            writer = csv.writer(stream, lineterminator='\n'); writer.writerow(['pad', 'i', 'j', 'area_m2'])
            writer.writerows((p, i, j, format(a, '.17g')) for p, i, j, a in rows)
        config = run/'configs'/(CASE_ID+'.properties')
        transformed, changes = remap_config(old_config.read_bytes(), mask, core.sha(mask), areas, design)
        config.write_bytes(transformed)
        core.write(run/'geometry-audit/role-design.json', design); core.write(run/'geometry-audit/mask-receipt.json', mask_receipt)
        case = copy.deepcopy(source)
        case.update(id=CASE_ID, design_id=design['id'], design=design, source_run_id=run.name,
            config_file=str(config), config_sha256=core.sha(config), mask_file=str(mask), mask_sha256=core.sha(mask),
            expected_pad_areas_m2=areas, physical_total_contact_area_mm2=900., status='preregistered_not_executed',
            candidate_adopted=False, combined_geometry_and_area_allocation=False,
            isolated_wiring_role_effect=True, physical_geometry_unchanged=True, isolated_area_effect_claimed=False,
            prototype_reference=dict(run_id=SOURCE_RUN, case_id=SOURCE_ID, old_to_new_pad=OLD_TO_NEW),
            contact_area_policy=design['area_policy'], mesh_convergence_validated=False,
            existing_XY_contact_model_holds_preserved=True)
        case['circuit'] = copy.deepcopy(source['circuit'])
        case['circuit']['physical_pad_identity_old_to_new'] = OLD_TO_NEW
        case.update(_mesh(case)); core.require(case['cells'] == EXPECTED_CELLS, 'Fixed cell count changed')
        case['cache_signature'] = core.check_cached_operator(case, run)
        core.require(case['cache_signature'] != core.operator_signature(source), 'Role permutation must change the operator')
        def allowance():
            elapsed = time.monotonic()-started
            return min(PREPARATION_SECONDS-elapsed, 6600-budget['spent_seconds']-elapsed-EXECUTION_AND_VALIDATION_RESERVE)
        def command(argv, log):
            remaining = allowance(); core.require(remaining > 0, 'Finite preparation/reserve exhausted')
            core.write(run/'controller.json', dict(status='preparing', phase='return_role_compile_selftest',
                command=argv, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
            proc = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic()+remaining
            try:
                while proc.poll() is None:
                    core.require(time.monotonic() < deadline and core.rss(proc.pid)+core.rss(os.getpid()) <= 3*core.GIB and
                        shutil.disk_usage(run).free >= 2*core.GIB, 'Preparation time/RSS/disk reserve exceeded')
                    time.sleep(.1)
                core.require(proc.returncode == 0, 'Preparation child failed: '+str(proc.returncode))
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL); proc.wait()
        jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
        javac = shutil.which('javac') or str(jdk/'javac'); java = str(Path(javac).resolve().parent/'java')
        core.require(Path(javac).is_file() and Path(java).is_file(), 'Installed matching Java toolchain required')
        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                *(str(core.SOURCE/n) for n in ('TisSweep.java', 'ExploreBasis.java', 'SelectivityShapeBasis.java')),
                str(core.REPO/'tools/java/CloudShapeBasis.java')], log)
            command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1', '-cp', str(run/'classes'),
                     'CloudShapeBasis', '--selftest'], log)
        for p in [*(run/'configs').glob('*'), *(run/'masks').glob('*'), *(run/'classes').glob('*'), *(run/'geometry-audit').glob('*')]:
            pins[str(p)] = core.sha(p)
        core.require(allowance() > 0, '60s preparation allowance exhausted')
        for name, expected in pins.items(): core.require(core.sha(name) == expected, 'Pinned preparation input changed: '+name)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='one_existing_physical_mask_return_role_permutation',
            status='prepared', created_utc=core.now(), source_commit=commit, package_integrity=integrity,
            limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES), cases=[case], java=java,
            source_and_input_sha256=pins, new_PDE_conditions_maximum=1, expected_raw_bound_bytes=EXPECTED_RAW_BOUND_BYTES,
            preparation_seconds=time.monotonic()-started, scientific_question=decision['chosen_wiring_question'],
            decision=dict(path=str(Path(decision_path).resolve()), SHA256=core.sha(decision_path)),
            path_mapping=[dict(original_config=str(old_config), new_config=str(config), changed_fields=sorted(changes),
                old_to_new_pad=OLD_TO_NEW, physical_patches_unchanged=True, electrical_physics_grid_changed_fields=[])],
            planned_normalizations=['raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
                'skin_contact_only', 'legacy_composite_full_skin'], comparison_waveforms=['square_3h', 'sine', 'triangle_3h'],
            fixed_ROIs='Primary r<=5mm depth15to20; supplementalwholeXYsame-depth; surface0to5 and bothcomplements',
            root_validation_reserve_seconds=180, root_UI_reserve_seconds=60, candidate_adopted=False,
            mesh_convergence_validated=False, experimental_validation=False, existing_XY_contact_model_holds_preserved=True,
            contact_uncertainty='Unchanged nominalPBSRs500 specificZ; no subtraction/area conversion repeated; actualskin held',
            frozen_source_snapshot_owner='standalone CLI freezes once under dual global execution locks',
            storage=dict(native_location=str(run), persistent_backup_verified=False, retirement_of_old_environment_allowed=False),
            next_decision='Evaluate fixed baseline burdens AND absolute target/non-target distributions; no adoption or automatic second PDE')
        core.write(run/'preregistration.json', registration)
        core.write(run/'controller.json', dict(status='prepared', updated_utc=core.now()))
        succeeded = True
        return registration
    except BaseException as error:
        if run.exists():
            core.write(run/'preparation-failure.json', dict(status='preparation_failed_preserved',
                error_type=type(error).__name__, error=str(error), observed_utc=core.now(),
                partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        elapsed = time.monotonic()-started; budget['spent_seconds'] += elapsed
        budget['runs'].append(dict(run_id=run.name, stage='preparation', seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'))
        core.write(budget_path, budget)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--decision', type=Path, required=True)
    args = parser.parse_args()
    with (core.REPO/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = prepare_return_role(args.output, args.decision)
        core.freeze_sources(args.output.resolve())
    print(dict(status=result['status'], run=str(args.output), case_id=CASE_ID))


if __name__ == '__main__':
    main()
