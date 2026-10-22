"""Register the exact-grid nominal Best1 and a genuine same-grid C1 control.

No solver or geometry import occurs on module import. The root controller
calls preparation under its global lock after reviewing the preceding batch.
Original sources, historical configurations and old native evidence stay intact.
"""
from __future__ import annotations

import copy
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import task1_cloud_batch as core
from task1_grouped_registration import _caller_owns_execution_lock, _mesh


H_EXACT_MM = 50/120
NOMINAL_CANDIDATE = 'coat010-f0500-minusRs-square_3h'
EXPECTED_CENTER20_V_M = 3.97673338723
MASK_ROUNDOFF_RELATIVE = 1e-10


def compare_reference(run, case, post):
    """Same-definition Best1 scalars/circuits, called under execution controls.

    Old native E/phi are missing. This checks released native-volume scalars and
    circuit matrices; it cannot manufacture an old full-field/probe comparison.
    """
    import numpy as np
    core.require(case['id'] == 'best1-square15-xy120' and case['channels'] == 2,
                 'Exact nominal Best1 comparison case required')
    source_csv = core.HIST/'analysis-rows-cm.csv'
    with source_csv.open() as stream:
        rows = list(csv.DictReader(stream))
    scalars = []
    for condition in post['conditions']:
        alias = 'reference-best1-final-'+condition['waveform']
        matches = [row for row in rows if row['condition_id'] == alias and
                   row['normalization'] == 'raw_1Vpp' and row['reference'] == 'latest_coated_same_mesh']
        core.require(len(matches) == 1, 'One exact historical nominal scalar row required')
        old = matches[0]
        metrics = condition['metrics']
        target = condition['volume_metrics']['regions']['target']['statistics']
        surface = condition['volume_metrics']['regions']['surface_0_5']['statistics']
        actual = dict(roi_mean_TIS_V_cm=target['maxTIS']['mean']/100,
            roi_P10_TIS_V_cm=target['maxTIS']['p10']/100,
            roi_mean_E_RMS_V_cm=target['RMS']['mean']/100,
            central20_TIS_V_cm=metrics['target20_modulation_V_m']/100,
            central20_E_RMS_V_cm=metrics['target20_total_E_RMS_V_m']/100,
            Jmax_mA_cm2=metrics['surface_J_RMS_max_A_m2']*.1,
            J95_area_weighted_mA_cm2=metrics['surface_J_RMS_p95_A_m2']*.1,
            contact_voltage_RMS_mV=metrics['contact_voltage_RMS_max_V']*1000,
            SC_power_uW=metrics['SC_power_W']*1e6,
            contact_power_uW=metrics['contact_power_W']*1e6,
            source_power_uW=metrics['source_power_W']*1e6,
            surface_0_5_P95_TIS_V_cm=surface['maxTIS']['p95']/100,
            surface_0_5_max_TIS_V_cm=surface['maxTIS']['max']/100)
        for metric, value in actual.items():
            expected = float(old[metric])
            error = abs(value-expected)
            scalars.append(dict(condition_id=condition['id'], historical_condition_alias=alias,
                metric=metric, actual=value, expected=expected,
                relative_error=error/max(abs(expected), 1e-30),
                passed=math.isfinite(value) and error <= 1e-14+1e-7*abs(expected)))
    matrices = []
    directory = core.HIST/'released-circuits/reference-best1-final'
    for f in (3000, 3030, 9000, 9090):
        for name, count in (('source', 8), ('loss', 48)):
            old_file = directory/f'{name}-{f}.bin'
            new_file = Path(run)/'bases'/case['id']/old_file.name
            old, new = np.fromfile(old_file, '<f8'), np.fromfile(new_file, '<f8')
            core.require(old.shape == new.shape == (count,), 'Released reference matrix dimensions differ')
            error = abs(new-old)
            matrices.append(dict(name=old_file.name, expected_sha256=core.sha(old_file),
                actual_sha256=core.sha(new_file), byte_equal=old_file.read_bytes() == new_file.read_bytes(),
                relative_max_error=float(error.max()/max(float(np.max(abs(old))), 1e-30)),
                passed=bool(np.isfinite(new).all() and np.all(error <= 1e-14+1e-8*abs(old)))))
    core.require(len(scalars) == 39 and len(matrices) == 8, 'Complete39-scalar/8-matrix reference comparison required')
    return dict(schema='task1-exact-nominal-reproduction-v1', run_id=Path(run).name, case_id=case['id'],
        status='passed' if all(row['passed'] for row in scalars+matrices) else 'failed',
        scalar_relative_tolerance=1e-7, matrix_relative_tolerance=1e-8, absolute_tolerance=1e-14,
        historical_scalar_csv=str(source_csv), historical_scalar_csv_sha256=core.sha(source_csv),
        historical_circuit_directory=str(directory), scalar_comparisons=scalars, circuit_comparisons=matrices,
        target20_definition='Trilinear native complex E at (0,0,20) within muscle; twofundamental2074 sampled directions',
        volume_definition='Native-cell volume-weighted r<=5mm z15–20mm; same fractional ROI integration',
        probe_definition='New40 nativephi differential waveforms; old fullphi traces unavailable here, no fabricated fulltrace match',
        no_original_E_or_phi_restored=True, mesh_convergence_validated=False, experimental_validation=False)


def _properties(data):
    values = {}
    for line in data.decode('utf-8').splitlines():
        if not line or line.startswith(('#', '!')):
            continue
        key, value = line.split('=', 1)
        core.require(key not in values, 'Duplicate frozen config property '+key)
        values[key] = value
    return values


def _changed_config(data, changes):
    old = _properties(data)
    core.require(set(changes) <= set(old), 'Only existing explicit config fields may change')
    lines = []
    seen = set()
    for line in data.splitlines(keepends=True):
        key = line.split(b'=', 1)[0].decode('utf-8')
        if key not in changes:
            lines.append(line)
            continue
        ending = b'\r\n' if line.endswith(b'\r\n') else (b'\n' if line.endswith(b'\n') else b'')
        lines.append((key+'='+str(changes[key])).encode('utf-8')+ending)
        seen.add(key)
    core.require(seen == set(changes), 'Requested exact config fields were not unique')
    output = b''.join(lines)
    revised = _properties(output)
    core.require(set(old) == set(revised) and all(old[k] == revised[k] for k in old if k not in changes),
                 'Unregistered material/contact/circuit config change')
    return output


def _full_face_mask(geom, design, h):
    """Canonicalize only mathematically aligned square-face roundoff.

    Tiny numerical polygon remnants are recorded, and true partial faces are
    rejected. This is not a general contact smoothing or geometry adjustment.
    """
    original = geom.mask(design, h)
    core.require(original.get('status') == 'valid_contact_mask', 'Exact reference mask geometry rejected')
    face = (h/1000)**2
    rows = []
    discarded, snapped = [], 0
    for patch in original['contacts']:
        area = float(patch['area_m2'])
        ratio = area/face
        core.require(math.isfinite(ratio) and ratio > 0, 'Nonfinite or nonpositive reference patch')
        if ratio <= MASK_ROUNDOFF_RELATIVE:
            discarded.append(copy.deepcopy(patch))
            continue
        core.require(abs(ratio-1) <= MASK_ROUNDOFF_RELATIVE,
                     'Aligned original square requires full faces; unexpected partial contact')
        snapped += area != face
        rows.append((int(patch['pad']), int(patch['i']), int(patch['j']), face))
    n_pads = len(design['pads'])
    areas = [math.fsum(row[3] for row in rows if row[0] == pad) for pad in range(n_pads)]
    core.require(all(abs(area/.000225-1) <= 1e-10 for area in areas),
                 'Canonical reference mask must preserve225mm2 per physical pad')
    core.require(len({(pad, i, j) for pad, i, j, _ in rows}) == len(rows),
                 'Duplicate physical reference face')
    covered = {}
    for _, i, j, area in rows:
        covered[i, j] = covered.get((i, j), 0.)+area
    core.require(all(area <= face*(1+1e-10) for area in covered.values()), 'Reference pad overlap')
    receipt = dict(rule='aligned-square-full-face-roundoff-v1', threshold_relative_to_h_squared=MASK_ROUNDOFF_RELATIVE,
        original_geometry_status=original['status'], original_contacts=len(original['contacts']),
        canonical_contacts=len(rows), discarded_numerical_remnant_patches=discarded,
        discarded_area_m2=math.fsum(float(p['area_m2']) for p in discarded),
        full_face_area_snap_count=snapped, canonical_face_area_m2=face,
        represented_pad_areas_m2=areas,
        meaning='Analytically aligned15mm square boundaries; no finite partial faces accepted; no physical geometry smoothing',
        numerical_geometry_or_contact_convergence_claimed=False)
    return rows, areas, original, receipt


def prepare_reference(run):
    start = time.monotonic()
    run = Path(run)
    core.paths_check(run)
    core.require(run.is_absolute() and run == run.resolve(), 'Canonical absolute new reference run required')
    core.require(not run.exists(), 'Never overwrite or retry a prepared/partial reference run')
    _caller_owns_execution_lock()
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    integrity = core.original_integrity()
    prereg_path = core.HIST/'preregistration.json'
    old = core.read(prereg_path)
    design_path = core.HIST/'inputs/designs.json'
    designs = {design['id']: design for design in core.read(design_path)}
    base_design = designs['baseline-square15']
    requests = [
        ('baseline-square15-xy100', 'baseline-square15-xy100', .5, False),
        ('best1-square15-xy120', 'baseline-square15-xy80', H_EXACT_MM, True),
        ('best1-square15-C1pair0-xy120', 'baseline-square15-C1pair0-xy80', H_EXACT_MM, True),
    ]
    cases = []
    for ident, template_id, h, regenerate in requests:
        case = copy.deepcopy(old['case_pool'][template_id])
        config = core.HIST/'configs'/Path(case['config_file']).name
        mask = core.HIST/'masks'/Path(case['mask_file']).name
        core.require(core.sha(config) == case['config_sha256'] and core.sha(mask) == case['mask_sha256'],
                     'Frozen reference template config/mask pin differs')
        case.update(id=ident, h_xy_mm=h, mesh_id='xy120_exact_best1' if regenerate else 'xy100',
            template_case_id=template_id, source_config_file=str(config), source_mask_file=str(mask),
            requires_regenerated_mask=regenerate, java_class='CloudShapeBasis', postprocessor='legacy_native',
            exporter_class='SelectivityShapeBasis', n_outputs=case['channels'], n_pads=2*case['channels'])
        case.update(_mesh(case))
        case['design'] = copy.deepcopy(case.get('control_design') or base_design)
        case['design']['channels'] = case['channels']
        case['design']['xy_mm'] = [pad['center_mm'] for pad in case['design']['pads']]
        case['historical_nominal_candidate_alias'] = NOMINAL_CANDIDATE
        case['nominal_reference_role'] = ('same_grid_true_single_pair_control' if case['channels'] == 1 else
                                        'exact_historical_nominal_Best1' if regenerate else 'XY_convergence_reference')
        if case['channels'] == 2 and regenerate:
            case.update(requires_historical_nominal_center_gate_before_next=True,
                historical_nominal_center_expected_V_m=EXPECTED_CENTER20_V_M,
                historical_nominal_center_tolerance_relative=1e-7,
                historical_nominal_center_waveform='square_3h',
                requires_full_reference_comparison_before_next=True,
                historical_scalar_alias_case_id='reference-best1-final')
        cases.append(case)
    bound = sum(case['cells']*(600 if case['channels'] == 2 else 340) for case in cases)
    core.require(len(cases) == 3 and bound <= core.LIMITS['max_batch_added_bytes'],
                 'Reference finite3-case storage cap exceeded')
    core.require(shutil.disk_usage(run.parent).free > 2*core.GIB+bound,
                 'Reference reserve plus conservative raw output bound unavailable')
    budgetpath = core.REPO/'runtime/task1-budget.json'
    budget = core.read(budgetpath) if budgetpath.exists() else dict(limit_seconds=6600, spent_seconds=0., runs=[])
    core.require(budget['limit_seconds'] == 6600 and budget['spent_seconds'] < 6600,
                 'Cumulative reference budget exhausted; no automatic expansion')
    jdk = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin')
    javac = shutil.which('javac') or str(jdk/'javac')
    java = str(Path(javac).parent/'java')
    core.require(Path(javac).is_file() and Path(java).is_file(), 'Reference Java compiler/runtime unavailable')
    run.mkdir()
    for directory in ('configs', 'masks', 'bases', 'cases', 'postprocess', 'logs', 'classes', 'geometry-audit'):
        (run/directory).mkdir()
    core.write(run/'controller.json', dict(status='preparing', phase='reviewed_geometry_import',
        pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now()))
    succeeded = False
    registration = None
    try:
        # Reviewed pure geometry preparation: NumPy/polygon clipping only, no PDE
        # or data fit. Import is intentionally inside this locked bounded stage.
        if str(core.SOURCE) not in sys.path:
            sys.path.insert(0, str(core.SOURCE))
        import selectivity_geometry as geom
        pins = core.source_pins()
        for path in (Path(__file__), core.REPO/'tools/task1_grouped_registration.py', prereg_path, design_path):
            pins[str(path)] = core.sha(path)
        for path in [core.HIST/'analysis-rows-cm.csv',
                     *(core.HIST/'released-circuits/reference-best1-final').glob('*.bin')]:
            pins[str(path)] = core.sha(path)
        mapping = []
        for case in cases:
            original_config = Path(case.pop('source_config_file'))
            original_mask = Path(case.pop('source_mask_file'))
            pins[str(original_config)] = core.sha(original_config)
            pins[str(original_mask)] = core.sha(original_mask)
            config = run/'configs'/(case['id']+'.properties')
            mask = run/'masks'/(case['id']+'.csv')
            h = case['h_xy_mm']
            changes = {'mask.path': str(mask)}
            geometry_files = []
            if case.pop('requires_regenerated_mask'):
                rows, areas, original_geometry, canonical = _full_face_mask(geom, case['design'], h)
                with mask.open('x', newline='') as stream:
                    writer = csv.writer(stream, lineterminator='\n')
                    writer.writerow(['pad', 'i', 'j', 'area_m2'])
                    for pad, i, j, area in rows:
                        writer.writerow([pad, i, j, format(area, '.17g')])
                original_audit = run/'geometry-audit'/(case['id']+'-original-clip.json')
                canonical_audit = run/'geometry-audit'/(case['id']+'-full-face.json')
                core.write(original_audit, original_geometry)
                core.write(canonical_audit, canonical)
                geometry_files = [str(original_audit), str(canonical_audit)]
                case['expected_pad_areas_m2'] = areas
                changes.update(h_mm=repr(h), **{'mask.sha256': core.sha(mask)})
            else:
                shutil.copy2(original_mask, mask)
            config.write_bytes(_changed_config(original_config.read_bytes(), changes))
            mapping.append(dict(original_config=str(original_config), original_sha256=core.sha(original_config),
                new_config=str(config), new_sha256=core.sha(config), changed_fields=list(changes),
                original_mask=str(original_mask), original_mask_sha256=core.sha(original_mask),
                new_mask=str(mask), new_mask_sha256=core.sha(mask), geometry_audit_files=geometry_files,
                phantom_material_contact_circuit_changed=False,
                grid_changed=case['h_xy_mm'] != old['case_pool'][case['template_case_id']]['h_xy_mm']))
            case.update(config_file=str(config), config_sha256=core.sha(config), mask_file=str(mask),
                mask_sha256=core.sha(mask), source_run_id=run.name, source_coating_nm=10,
                source_Rs_fit_window_Hz=500, status='preregistered_not_executed')
            case['cache_signature'] = core.check_cached_operator(case, run)
            channels = case['channels']
            case['circuit'] = dict(n_pads=2*channels, n_outputs=channels, n_signal_pads=channels,
                n_return_pads=channels, n_return_nodes=1, return_topology='all_actual_return_pads_ideal_common_GND',
                source_Vpp_each=1., source_peak_V=.5, source_resistance_ohm=50.,
                source_phase_deg=[0.]*channels, carrier_assignment_Hz=[3000, 3030] if channels == 2 else [3000],
                C1_separate_actual_carriers_Hz=[3000, 3030] if channels == 1 else None,
                pad_to_node={str(pad): f'out{pad}' if pad < channels else 'GND' for pad in range(2*channels)},
                inactive_source_at_other_frequencies='0 V through50 ohm for every actual inactive output',
                phantom_extra_pads_or_outputs_retained=False,
                note='C1 has one physical signal pad and one return; separately driven at each carrier, no two-carrier TIS')
            for audit in geometry_files:
                pins[audit] = core.sha(audit)

        def command(args, log):
            remaining = 6600-budget['spent_seconds']-(time.monotonic()-start)
            core.require(remaining > 0, 'Reference cumulative preparation budget exhausted')
            core.require(shutil.disk_usage(run).free >= 2*core.GIB, 'Reference2GiB preparation reserve')
            core.write(run/'controller.json', dict(status='preparing', phase='compile_or_analytic_selftest',
                command=args, pid=os.getpid(), proc_start_ticks=core.ticks(os.getpid()), updated_utc=core.now(),
                elapsed_seconds=time.monotonic()-start))
            subprocess.run(args, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=min(120., remaining))

        with (run/'logs/compile-selftest.log').open('x') as log:
            command([javac, '-J-Xmx2g', '-J-XX:ActiveProcessorCount=1', '-encoding', 'UTF-8', '-d', str(run/'classes'),
                str(core.SOURCE/'TisSweep.java'), str(core.SOURCE/'ExploreBasis.java'),
                str(core.SOURCE/'SelectivityShapeBasis.java'), str(core.REPO/'tools/java/CloudShapeBasis.java')], log)
            command([java, '-Xmx2g', '-XX:+UseSerialGC', '-XX:ActiveProcessorCount=1',
                     '-cp', str(run/'classes'), 'CloudShapeBasis', '--selftest'], log)
        for path in [*(run/'configs').glob('*'), *(run/'masks').glob('*'), *(run/'classes').glob('*')]:
            pins[str(path)] = core.sha(path)
        for path, expected in pins.items():
            core.require(core.sha(path) == expected, 'Reference source/input changed during preparation: '+path)
        registration = dict(schema='task1-cloud-finite-v1', batch_kind='exact_nominal_reference_and_C1',
            status='prepared', created_utc=core.now(),
            source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=core.REPO, text=True).strip(),
            historical_source_commit='8c3a30a778cc9bf19ccb52ca523598bff0a84650',
            package_integrity=integrity, limits=copy.deepcopy(core.LIMITS), gates=copy.deepcopy(core.GATES),
            cases=cases, new_PDE_conditions_maximum=3, expected_raw_bound_bytes=bound, java=java,
            source_and_input_sha256=pins, preparation_seconds=time.monotonic()-start, path_mapping=mapping,
            scientific_scope='Later3kHz10nmRs500 nominal Best1 exact-grid reproduction and genuine same-grid one-pair RMS/probe control',
            historical_nominal_reference=dict(candidate_alias=NOMINAL_CANDIDATE,
                source_result_commit='947c984f9a154d750acf36379fc859b25b56ac4f', h_xy_mm=H_EXACT_MM,
                target20_TIS_V_m=EXPECTED_CENTER20_V_M, relative_gate=1e-7,
                reproduction_kind='fresh PDE; missing historical native arrays were not restored',
                validated_deep_focus=False, experimental_validation=False),
            metric_definition_mapping=dict(
                historical_center='explore_tis.load_basis weights20 trilinear nativeE; summarize twofundamental2074 directions',
                current_center='selectivity_postprocess._electrical layered stencil times stored nativeE; within muscle reduces identical trilinear interpolation',
                display_maps='Separate _phi_gradient finite differences of nativephi; never used for central20 or nativeROI score',
                historical_native_ROI_alias='reference-best1-final; oldmean4.059343651347457/P10 3.6383960923394285V/m square_3h',
                differential_probe='phi(plus)-phi(minus),gap5mm; actual4 frequencies; full33.333ms Vpp bounds and spectrum'),
            mask_roundoff_contract=dict(relative_tolerance=MASK_ROUNDOFF_RELATIVE,
                rule='canonicalize mathematically full aligned square faces; preserve original clipping audit; reject finite partial faces'),
            historical_comparison=dict(relative_scalar_tolerance=1e-7, source_loss_matrix_tolerance=1e-8,
                allow_absolute_error_near_zero=1e-14,
                gate='Nominal exact-grid square_3h central20 must match historical scalar before same-grid C1 execution'),
            convergence=dict(field_ROI_percent=1, J_contact_voltage_percent=5, power_percent=2,
                mesh_convergence_validated=False, experimental_validation=False),
            storage=dict(native_location=str(run), persistent_backup_verified=False,
                retirement_of_old_environment_allowed=False),
            next_decision='Compare XY convergence, historical scalar, full ROI and matched-C1 point/ROI RMS; retain unresolved contact-edge/SC gates')
        core.write(run/'preregistration.json', registration)
        core.write(run/'controller.json', dict(status='prepared', updated_utc=core.now()))
        succeeded = True
    except BaseException as error:
        core.write(run/'preparation-failure.json', dict(status='preparation_failed_preserved',
            error_type=type(error).__name__, error=str(error), observed_utc=core.now(),
            partial_evidence_preserved=True, automatic_retry=False))
        raise
    finally:
        elapsed = registration['preparation_seconds'] if succeeded else time.monotonic()-start
        budget['spent_seconds'] += elapsed
        budget['runs'].append(dict(run_id=run.name, stage='preparation', seconds=elapsed,
            status='prepared' if succeeded else 'preparation_failed_preserved'))
        budgetpath.parent.mkdir(exist_ok=True)
        core.write(budgetpath, budget)
    print(json.dumps(dict(status='prepared', run=str(run), cases=[case['id'] for case in cases],
        bound_bytes=bound, batch_kind='exact_nominal_reference_and_C1'), ensure_ascii=False))
    return registration
