#!/usr/bin/env python3
"""Finite, source-bound small contact-patch audit. No PDE/research imports.

Only contacts, channel-major density, mask, metadata/config/receipts and frozen
WAVES source are read. Optional small source/loss matrices require explicit
preregistration. E, phi, grid and scalar/display archives are excluded.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
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

import task1_contact_edge_audit as frozen
import task1_results_view as view

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 32*1024**2
GIB = 1024**3
FREQUENCIES = (3000, 3030, 9000, 9090)
FRACTION_BINS = (0., .001, .01, .1, .5, 1.+1e-12)
REGRESSION_REL = 1e-10
REGRESSION_ABS = 1e-14
SCHEMA = 'task1-contact-patch-audit-preregistration-v1'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def small_path(path):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve() and path.is_relative_to(ROOT)
        and path.is_file() and not path.is_symlink(), 'Canonical regular repository input required: '+str(path))
    name = path.name
    require(not (name.startswith(('field-', 'potential-', 'grid.csv')) or path.suffix == '.npz'),
        'E/phi/grid/NPZ reads are forbidden: '+str(path))
    require(path.stat().st_size <= MAX_FILE_BYTES, 'Small input exceeds32MiB: '+str(path))
    return path


def pin(path, planned, used, expected=None):
    path = small_path(path)
    name = str(path)
    require(name in planned, 'Consumed file lacks preregistered SHA: '+name)
    digest = frozen.sha(path)
    require(digest == planned[name] and (expected is None or digest == expected), 'Input SHA mismatch: '+name)
    used[name] = digest
    return path


def implementation_source_paths():
    return [Path(__file__).resolve(), Path(frozen.__file__).resolve(), Path(view.__file__).resolve()]


def implementation_receipt():
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=5).stdout.strip()
    sources = implementation_source_paths()
    hashes = {}
    for path in sources:
        relative = path.relative_to(ROOT).as_posix()
        expected = subprocess.run(['git', 'show', commit+':'+relative], cwd=ROOT,
            check=True, capture_output=True, timeout=5).stdout
        require(path.read_bytes() == expected, 'Audit/helper source must match committed HEAD: '+relative)
        hashes[str(path)] = frozen.sha(path)
    return dict(implementation_git_commit=commit, implementation_files_sha256=hashes)


def verify_preregistration(path, summary_paths, *, expected_sha=None):
    path = small_path(path)
    digest = frozen.sha(path)
    require(expected_sha is None or digest == expected_sha, 'Preregistration changed during audit')
    plan = frozen.read(path)
    require(plan.get('schema') == SCHEMA and plan.get('status') == 'preregistered_not_executed'
        and plan.get('new_PDE_conditions') == 0, 'Expected unexecuted no-PDE contact-patch preregistration')
    rows = plan['cases']
    actual = [str(Path(p).resolve()) for p in summary_paths]
    declared = [row['summary'] for row in rows]
    require(1 <= len(rows) <= 12 and len(set(actual)) == len(actual) and actual == declared
        and len({row['case_id'] for row in rows}) == len(rows), 'Exact ordered1..12 unique preregistered cases required')
    require(type(plan.get('include_circuit_matrices', False)) is bool, 'Explicit boolean circuit-matrix option required')
    planned = plan['input_sha256']
    require(bool(planned), 'Preregistered small-file hashes required')
    for input_path, expected in planned.items():
        require(isinstance(expected, str) and len(expected) == 64 and all(c in '0123456789abcdef' for c in expected),
            'Invalid input SHA256')
        require(frozen.sha(small_path(input_path)) == expected, 'Preregistered input hash mismatch: '+input_path)
    for row in rows:
        require(planned.get(row['summary']) == row['summary_sha256'], 'Preregistered summary hash mismatch')
        summary = frozen.read(row['summary'])
        require(summary['id'] == row['case_id'] and summary['input_sha256'] == row['native_expected_input_sha256'],
            'Case ID or declared native manifest differs from preregistration')
    for group in plan.get('comparison_groups', []):
        require(isinstance(group.get('label'), str) and bool(group['label'])
            and len(group['case_ids']) >= 2 and set(group['case_ids']) <= {row['case_id'] for row in rows},
            'Comparison labels must name explicit included cases')
    return plan, digest


def make_preregistration(summary_paths, *, include_circuit_matrices=False,
                        labels=None, comparison_groups=None):
    """Metadata/hash-only plan builder; never parses density or field arrays.

    Root may serialize the returned dictionary to a new plan using open('x').
    Each declared density/contact file is byte-hashed with a32MiB limit; its
    numerical contents are not analyzed here. Call under the root's serial slot.
    """
    paths = [small_path(Path(path).resolve()) for path in summary_paths]
    require(1 <= len(paths) <= 12 and len(set(paths)) == len(paths), '1..12 unique source summaries required')
    require(type(include_circuit_matrices) is bool, 'Boolean circuit matrix option required')
    plan = dict(schema=SCHEMA, status='preregistered_not_executed', created_utc=datetime.now(timezone.utc).isoformat(),
        execution_owner='root', new_PDE_conditions=0, include_circuit_matrices=include_circuit_matrices,
        feedback_id='T1-F010-S1-GH6297472037', source_comment_id=6297472037,
        source_comment_url='https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6297472037',
        purpose='Independent cached small contact-patch/partial-face readback and sensitivity description; no geometry-artifact proof or adoption',
        comparison_groups=comparison_groups or [], cases=[], input_sha256={},
        regression_tolerance=dict(relative=REGRESSION_REL, absolute=REGRESSION_ABS),
        fraction_bins=list(FRACTION_BINS),
        density_layout='complex128(2,npatches), channel major, not interleaved by patch',
        resource_limits=dict(CPU_count=1, wall_seconds=180, RSS_bytes=3*GIB, disk_reserve_bytes=2*GIB,
            maximum_input_file_bytes=MAX_FILE_BYTES, cumulative_budget_seconds=6600),
        retained_holds=['Every original SC/XY/bulk/edge/contact convergence failure remains unchanged',
            'PBS-derived contact impedance remains an unvalidated skin-contact hypothesis',
            'No candidate adoption, full-skin-vector J inference, human safety or physiological equivalence claim'],
        native_hash_scope='All consumed small files byte-hashed; unused E/phi/grid/NPZ manifest digests retained as declarations only')
    refs = plan['input_sha256']
    def add(path, expected=None):
        path = small_path(path)
        digest = frozen.sha(path)
        require(expected is None or digest == expected, 'Plan source hash mismatch: '+str(path))
        refs[str(path)] = digest
        return path
    for source in implementation_source_paths():
        add(source)
    for path in paths:
        add(path)
        summary, run = frozen.read(path), path.parents[2]
        registration_path = add(run/'preregistration.json')
        registration = frozen.read(registration_path)
        found = [row for row in registration['cases'] if row['id'] == summary['id']]
        require(len(found) == 1, 'One registered source case required')
        case = found[0]
        add(run/'cases'/(case['id']+'.json'))
        if (run/'reference-comparison.json').is_file():
            add(run/'reference-comparison.json')
        require(view.case_eligibility(path, summary)['eligible'] and view.result_kind(path, summary)['kind'] == 'tis',
            'Only genuine completed eligible TIS cases may be preregistered')
        native = summary['input_sha256']
        add(Path(case['config_file']), case['config_sha256'])
        add(Path(case['mask_file']), case['mask_sha256'])
        basis = run/'bases'/case['id']
        names = ['BASIS_COMPLETE', 'mesh-metadata.json', 'validation.json']
        for frequency in FREQUENCIES:
            names += [f'contacts-{frequency}.csv', f'density-{frequency}.bin']
            if include_circuit_matrices:
                names += [f'source-{frequency}.bin', f'loss-{frequency}.bin']
        for name in names:
            add(basis/name, native[str(basis/name)])
        waveform = run/'frozen-source/tis-java/explore_tis.py'
        add(waveform, registration['source_and_input_sha256'][str(ROOT/'tis-java/explore_tis.py')])
        plan['cases'].append(dict(case_id=case['id'], run_id=run.name, summary=str(path),
            summary_sha256=refs[str(path)], native_expected_input_sha256=native,
            labels=(labels or {}).get(case['id'], [])))
    require(all(frozen.sha(path) == digest for path, digest in refs.items()), 'Plan inputs changed while pinning')
    return plan


def contact_rows(path):
    with Path(path).open() as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ['pad', 'x_mm', 'y_mm', 'area_m2'], 'Unexpected contact CSV columns')
        result = [(int(row['pad']), float(row['x_mm']), float(row['y_mm']), float(row['area_m2'])) for row in reader]
    require(bool(result), 'Nonempty physical contact patches required')
    return result


def validate_mask(contacts, mask_path, h):
    require(math.isfinite(h) and h > 0, 'Positive XY spacing required')
    face_area = h*h*1e-6
    actual = {}
    for pad, x, y, area in contacts:
        require(pad in range(4) and all(math.isfinite(v) for v in (x, y, area))
            and x*x+y*y < 625. and 0 < area/face_area <= FRACTION_BINS[-1],
            'Finite positive contact fraction within fixed D50 full XY face required')
        i, j = round((x+25.)/h-.5), round((y+25.)/h-.5)
        require(abs(x-(-25.+(i+.5)*h)) <= 1e-9 and abs(y-(-25.+(j+.5)*h)) <= 1e-9,
            'Contact location is not a native XY cell center')
        key = (pad, i, j)
        require(key not in actual, 'Duplicate physical contact patch')
        actual[key] = area
    declared = {}
    with Path(mask_path).open() as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ['pad', 'i', 'j', 'area_m2'], 'Unexpected contact mask CSV columns')
        for row in reader:
            key = (int(row['pad']), int(row['i']), int(row['j']))
            value = float(row['area_m2'])
            require(key not in declared and math.isfinite(value) and value > 0, 'Invalid/duplicate mask area')
            declared[key] = value
    require(set(actual) == set(declared) and {key[0] for key in actual} == set(range(4)),
        'Mask and contact patch identities must agree for all4 physical pads')
    require(all(math.isclose(area, declared[key], rel_tol=1e-12, abs_tol=1e-24)
        for key, area in actual.items()), 'Mask and physical contact patch areas differ')
    return [row[3]/face_area for row in contacts]


def reconstruct(contacts, density_by_frequency, za_by_frequency, coefficients):
    """Native ABI is complex128(2,npatches), basis-channel-major, peak phasors."""
    n = len(contacts)
    require(n > 0 and len(coefficients) == 2 and all(math.isfinite(a) and a > 0 for a in coefficients),
        'Positive frozen fundamental/third-harmonic coefficients required')
    j2, v2, patch_power = [0.]*n, [0.]*n, [0.]*n
    by_frequency = []
    for frequency in FREQUENCIES:
        density = density_by_frequency[frequency]
        za = za_by_frequency[frequency]
        require(len(density) == 2*n and all(math.isfinite(z.real) and math.isfinite(z.imag) for z in density)
            and math.isfinite(za.real) and math.isfinite(za.imag) and za.real >= 0,
            'Finite channel-major density and passive area-specific contact impedance required')
        active = 0 if frequency in (3000, 9000) else 1
        amplitude = coefficients[0 if frequency < 9000 else 1]
        power = 0.
        for patch, row in enumerate(contacts):
            peak_j = -1j*amplitude*density[active*n+patch]
            jrms2 = abs(peak_j)**2/2
            loss = jrms2*za.real*row[3]
            vrms2 = abs(peak_j*za)**2/2
            require(all(math.isfinite(x) for x in (jrms2, vrms2, loss)), 'Nonfinite reconstructed patch square/power')
            j2[patch] += jrms2
            v2[patch] += vrms2
            patch_power[patch] += loss
            require(all(math.isfinite(x) for x in (j2[patch], v2[patch], patch_power[patch])),
                'Nonfinite accumulated patch square/power')
            power += loss
        by_frequency.append(dict(frequency_Hz=frequency, active_basis_channel=active,
            harmonic=1 if frequency < 9000 else 3, sine_harmonic_coefficient=amplitude,
            area_specific_impedance_ohm_m2=dict(real=za.real, imaginary=za.imag), contact_power_W=power))
    return dict(J_RMS_A_m2=[math.sqrt(v) for v in j2], contact_V_RMS_V=[math.sqrt(v) for v in v2],
        contact_power_by_patch_W=patch_power, by_frequency=by_frequency)


def generic_stats(values, areas, unit):
    if not values:
        return None
    result = frozen.weighted_stats(values, areas)
    return dict(mean=result['mean_A_m2'], p95=result['p95_A_m2'], max=result['max_A_m2'], unit=unit,
        contact_area_mm2=result['contact_area_mm2'], p95_definition=result['p95_definition'])


def describe_patches(contacts, fractions, electrical):
    j, v, power = (electrical[key] for key in ('J_RMS_A_m2', 'contact_V_RMS_V', 'contact_power_by_patch_W'))
    area = [row[3] for row in contacts]
    total_area, total_power = sum(area), sum(power)
    def patch(index):
        pad, x, y, a = contacts[index]
        return dict(native_contact_index=index, pad=pad, center_xy_mm=[x, y], depth_mm=0.,
            contact_area_m2=a, contact_to_full_XY_face_fraction=fractions[index],
            J_RMS_A_m2=j[index], contact_V_RMS_V=v[index], contact_power_W=power[index])
    def distribution(indices):
        subset_area = sum(area[i] for i in indices)
        subset_power = sum(power[i] for i in indices)
        bins = []
        for bin_index, (lo, hi) in enumerate(zip(FRACTION_BINS, FRACTION_BINS[1:])):
            selected = [i for i in indices if lo <= fractions[i] < hi
                or (bin_index == len(FRACTION_BINS)-2 and fractions[i] == hi)]
            a, p = sum(area[i] for i in selected), sum(power[i] for i in selected)
            bins.append(dict(contact_face_fraction_interval=[lo, hi],
                interval='left closed/right open; last interval includes final endpoint', patches=len(selected),
                contact_area_m2=a, contact_area_mm2=a*1e6,
                area_share_of_subset=a/subset_area, area_share_of_all_contacts=a/total_area,
                contact_power_W=p, power_share_of_subset=p/subset_power if subset_power else None,
                power_share_of_all_contacts=p/total_power if total_power else None,
                zero_power_share_reason=None if subset_power else 'zero subset contact power',
                J_RMS=generic_stats([j[i] for i in selected], [area[i] for i in selected], 'A/m2'),
                contact_V_RMS=generic_stats([v[i] for i in selected], [area[i] for i in selected], 'V')))
        return bins
    pads = []
    for pad in range(4):
        ids = [i for i, row in enumerate(contacts) if row[0] == pad]
        require(bool(ids), 'All4 physical pads require represented contact')
        imax_j, imax_v = max(ids, key=lambda i:j[i]), max(ids, key=lambda i:v[i])
        pads.append(dict(pad=pad, patches=len(ids), physical_contact_area_m2=sum(area[i] for i in ids),
            physical_contact_area_mm2=sum(area[i] for i in ids)*1e6,
            area_fraction_min=min(fractions[i] for i in ids), area_fraction_max=max(fractions[i] for i in ids),
            area_fraction_area_weighted_mean=sum(fractions[i]*area[i] for i in ids)/sum(area[i] for i in ids),
            J_RMS=generic_stats([j[i] for i in ids], [area[i] for i in ids], 'A/m2'),
            contact_V_RMS=generic_stats([v[i] for i in ids], [area[i] for i in ids], 'V'),
            Jmax_patch=patch(imax_j), Vmax_patch=patch(imax_v),
            contact_power_W=sum(power[i] for i in ids), fraction_distribution=distribution(ids)))
    return dict(physical_contact_area_m2=total_area, physical_contact_area_mm2=total_area*1e6,
        contact_normal_J_RMS=generic_stats(j, area, 'A/m2'),
        contact_V_RMS=generic_stats(v, area, 'V'), contact_power_W=total_power,
        Jmax_patch=patch(max(range(len(j)), key=lambda i:j[i])),
        Vmax_patch=patch(max(range(len(v)), key=lambda i:v[i])), pads=pads,
        fraction_distribution=distribution(list(range(len(j)))),
        top8_J_patches=[patch(i) for i in sorted(range(len(j)), key=lambda i:j[i], reverse=True)[:8]],
        top8_V_patches=[patch(i) for i in sorted(range(len(v)), key=lambda i:v[i], reverse=True)[:8]])


class MetricMismatchError(ValueError):
    def __init__(self, evidence):
        self.evidence = evidence
        super().__init__('Independent contact metrics differ from published values at fixed1e-10rel+1e-14abs')


def metric_verification(actual, saved):
    checks = {}
    for key, value in actual.items():
        expected = saved[key]
        require(isinstance(expected, (int, float)) and math.isfinite(expected) and expected >= 0
            and math.isfinite(value) and value >= 0,
            'Finite nonnegative published contact metric required')
        difference = abs(value-expected)
        checks[key] = dict(independent=value, published=expected, absolute_difference=difference,
            relative_difference=difference/abs(expected) if expected else None,
            passed=difference <= REGRESSION_REL*abs(expected)+REGRESSION_ABS)
    return checks


def audit_case(declared, plan, used):
    planned = plan['input_sha256']
    path = pin(declared['summary'], planned, used, declared['summary_sha256'])
    run = path.parents[2]
    post = frozen.read(path)
    registration = frozen.read(pin(run/'preregistration.json', planned, used))
    matches = [c for c in registration['cases'] if c['id'] == declared['case_id']]
    require(len(matches) == 1, 'One exact registered case required')
    case = matches[0]
    pin(run/'cases'/(case['id']+'.json'), planned, used)
    if (run/'reference-comparison.json').is_file():
        pin(run/'reference-comparison.json', planned, used)
    eligibility = view.case_eligibility(path, post)
    require(eligibility['eligible'], 'Held/failed cases cannot enter patch audit: '+json.dumps(eligibility))
    require(view.result_kind(path, post)['kind'] == 'tis', 'Only registered two-output TIS cases supported')
    inputs = post['input_sha256']
    manifest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    require(manifest == post['input_manifest_sha256'] and inputs == declared['native_expected_input_sha256'],
        'Postprocess native manifest differs')
    config_path = pin(Path(case['config_file']), planned, used, case['config_sha256'])
    require(inputs[str(config_path)] == case['config_sha256'], 'Summary config digest mismatch')
    config = view.properties(config_path)
    mask_path = pin(Path(case['mask_file']), planned, used, case['mask_sha256'])
    basis = run/'bases'/case['id']
    for filename in ('BASIS_COMPLETE', 'mesh-metadata.json', 'validation.json'):
        pin(basis/filename, planned, used, inputs[str(basis/filename)])
    meta = frozen.read(basis/'mesh-metadata.json')
    require(meta == post['mesh_metadata'] and meta['config_sha256'] == case['config_sha256'], 'Metadata/config mismatch')
    circuit = case.get('circuit') or {key:case.get(key) for key in ('n_pads', 'n_outputs')}
    require(circuit.get('n_pads') == 4 and circuit.get('n_outputs') == 2 and meta['channels'] == 2
        and meta['radius_mm'] == 25 and meta['total_depth_mm'] == 25.1
        and meta['tissue_boundaries_mm'] == [0, .1, 5.1, 10.1, 25.1]
        and 0 < meta['cells'] <= 800000 and isinstance(meta['sc_cells'], int) and 0 < meta['sc_cells'] <= 64
        and len(meta['bulk_layer_counts']) == 3 and all(isinstance(n, int) and n > 0 for n in meta['bulk_layer_counts'])
        and meta['source_peak_V'] == .5 and meta['source_resistance_ohm'] == 50
        and meta['phasor_convention'] == 'peak,+jomega_t' and meta['frequencies_Hz'] == list(FREQUENCIES)
        and meta['h_xy_mm'] == float(config['h_mm']), 'Fixed D50/two-output/native peak-phasor contract differs')
    conditions = [c for c in post['conditions'] if c['waveform'] == 'square_3h']
    require(len(conditions) == 1, 'One exact square_3h condition required')
    condition = conditions[0]
    require(condition['actual_fundamental_Hz'] == [3000, 3030] and condition['carrier_group'] == [0, 1]
        and condition['phase_deg'] == [0., 0.] and condition['source_Vpp_per_output'] == 1.,
        'Frozen1Vpp two-carrier square_3h condition differs')
    source = run/'frozen-source/tis-java/explore_tis.py'
    source_digest = registration['source_and_input_sha256'][str(ROOT/'tis-java/explore_tis.py')]
    pin(source, planned, used, source_digest)
    coefficients = frozen.frozen_square_coefficients(run, registration, used)
    contacts, densities, impedance, matrix_powers = None, {}, {}, dict(contact_power_W=0., source_power_W=0.)
    for frequency in FREQUENCIES:
        contact_path = pin(basis/f'contacts-{frequency}.csv', planned, used, inputs[str(basis/f'contacts-{frequency}.csv')])
        rows = contact_rows(contact_path)
        if contacts is None:
            contacts = rows
        require(rows == contacts, 'Physical contact ordering differs across frequencies')
        density_path = pin(basis/f'density-{frequency}.bin', planned, used, inputs[str(basis/f'density-{frequency}.bin')])
        densities[frequency] = frozen.complex_array(density_path, 2*len(contacts))
        impedance[frequency] = complex(float(config[f'z.{frequency}.re']), float(config[f'z.{frequency}.im']))
        if plan.get('include_circuit_matrices', False):
            source_path = pin(basis/f'source-{frequency}.bin', planned, used, inputs[str(basis/f'source-{frequency}.bin')])
            loss_path = pin(basis/f'loss-{frequency}.bin', planned, used, inputs[str(basis/f'loss-{frequency}.bin')])
            source_values = frozen.complex_array(source_path, 4)
            loss_values = frozen.complex_array(loss_path, 24)
            channel = 0 if frequency in (3000, 9000) else 1
            amplitude2 = coefficients[0 if frequency < 9000 else 1]**2
            matrix_powers['contact_power_W'] += amplitude2*loss_values[16+3*channel].real
            matrix_powers['source_power_W'] += .25*amplitude2*source_values[3*channel].real
    fractions = validate_mask(contacts, mask_path, meta['h_xy_mm'])
    electrical = reconstruct(contacts, densities, impedance, coefficients)
    result = describe_patches(contacts, fractions, electrical)
    checks = metric_verification(dict(surface_J_RMS_max_A_m2=result['contact_normal_J_RMS']['max'],
        surface_J_RMS_p95_A_m2=result['contact_normal_J_RMS']['p95'],
        contact_voltage_RMS_max_V=result['contact_V_RMS']['max'], contact_power_W=result['contact_power_W']), condition['metrics'])
    optional = metric_verification(matrix_powers, condition['metrics']) if plan.get('include_circuit_matrices', False) else None
    result.update(case_id=case['id'], condition_id=condition['id'], run_id=run.name,
        summary_path=str(path), summary_sha256=used[str(path)], case_eligibility=eligibility,
        result_labels=declared.get('labels', []), mesh={key:meta[key] for key in
            ('h_xy_mm', 'sc_cells', 'bulk_layer_counts', 'cells')}, circuit=circuit,
        source_commit=registration['source_commit'], config_sha256=case['config_sha256'], mask_sha256=case['mask_sha256'],
        source_Vpp_per_output=1., waveform='square_3h', source_coefficients=coefficients,
        frequency_contributions=electrical['by_frequency'], summary_metric_verification=checks,
        optional_small_matrix_verification=optional,
        numerical_status='contact scalar readback only; prior convergence/held gates unchanged', adopted=False)
    if not all(c['passed'] for c in checks.values()) or (optional and not all(c['passed'] for c in optional.values())):
        raise MetricMismatchError(result)
    return result


def build_audit(summary_paths, plan, *, used=None):
    used = {} if used is None else used
    rows = [audit_case(declared, plan, used) for declared in plan['cases']]
    require([str(Path(path).resolve()) for path in summary_paths] == [r['summary'] for r in plan['cases']],
        'Ordered source summaries changed')
    return dict(schema='task1-contact-patch-audit-v1', status='complete_diagnostic_only', new_PDE=0,
        full_E_phi_grid_NPZ_read=False, research_modules_imported=False, cases=rows,
        comparison_groups=plan.get('comparison_groups', []),
        definitions=dict(density_storage='little-endian complex128(2,npatches); basis channel major, density[channel*npatches+patch]',
            phasor='peak,+jomega_t; source basis0.5Vpeak through50ohm; square sine coefficients -j*a',
            J_RMS='sqrt(sum_f |a_f*density[active_channel,patch]|^2/2)',
            contact_V_RMS='sqrt(sum_f |a_f*density[active_channel,patch]*Z_A(f)|^2/2)',
            contact_power_W='sum_patch,f |a_f*density|^2/2 * Re(Z_A(f)) * physical_contact_area_m2',
            contact_impedance='Area-specific complex Z_A in ohm*m2 from pinned config; no additional area division or Rs subtraction',
            contact_fraction='physical contact patch area divided by native full XY face h^2; no SC thickness or tissue-volume denominator',
            percentile='frozen nearest sequential cumulative area: first value reaching0.95*sequential_prefix[-1], no interpolation',
            fraction_bins=list(FRACTION_BINS), max_patch_ties='first native patch in stored order; top8 stable native ordering'),
        input_sha256=used, regression_tolerance=dict(relative=REGRESSION_REL, absolute=REGRESSION_ABS),
        limitations=['Patch-normal contact J is not full-vector skin J or deep TIS modulation',
            'Small contact area fractions and hotspot coincidence describe numerical contact representation; they do not prove an unphysical artifact',
            'No geometric edge/corner distance is inferred for arbitrary concave/elliptical shapes',
            'Nearest area-CDF P95 retains one-patch rank sensitivity at cumulative-area ties',
            'PBS interface remains an uncertain skin-contact model; no new Rs subtraction, area correction or experiment validation',
            'Prior SC/XY/bulk/edge/contact gates remain unchanged; no candidate adoption or safety/physiology claim'],
        numerical_validation_promoted=False, experimental_validation=False, safety_validation=False, adopted=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, action='append', required=True)
    parser.add_argument('--preregistration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    allowed = ROOT/'docs/cloud-continuation-20261021'
    require(args.output.absolute() == output and output.is_relative_to(allowed)
        and output.suffix == '.json' and not output.exists(), 'Unique canonical JSON output under continuation evidence required')
    implementation = implementation_receipt()
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        budget_path = ROOT/'runtime/task1-budget.json'
        budget = frozen.read(budget_path)
        require(budget['limit_seconds'] == 6600 and budget['spent_seconds'] < 6600, 'Existing6600s budget allocation exhausted')
        seconds = min(180., 6600-budget['spent_seconds'])
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        output.parent.mkdir(parents=True, exist_ok=True)
        start, used = time.monotonic(), {}
        result = dict(status='failed_preserved', schema='task1-contact-patch-audit-v1', new_PDE=0,
            full_E_phi_grid_NPZ_read=False, **implementation)
        def expired(signum, frame):
            raise TimeoutError('Finite contact-patch audit180s/remaining6600s allocation expired')
        signal.signal(signal.SIGALRM, expired)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            require(shutil.disk_usage(output.parent).free >= 2*GIB+16*1024**2, 'Preserve2GiB disk reserve plus16MiB output allowance')
            plan, plan_sha = verify_preregistration(args.preregistration, args.summary)
            result.update(build_audit(args.summary, plan, used=used))
            verify_preregistration(args.preregistration, args.summary, expected_sha=plan_sha)
            require(all(frozen.sha(path) == expected for path, expected in used.items()), 'Consumed input changed during audit')
            require(implementation_receipt() == implementation, 'Implementation changed during audit')
            require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, 'Existing3GiB RSS cap exceeded')
            result.update(preregistration=dict(path=str(args.preregistration.resolve()), SHA256=plan_sha,
                verified_before_and_after=True), inputs_unchanged=True,
                planned_input_sha256=plan['input_sha256'],
                source_feedback={key:plan.get(key) for key in ('feedback_id', 'source_comment_id', 'source_comment_url')})
        except BaseException as exc:
            result.update(status='failed_preserved', error_type=type(exc).__name__, error=str(exc),
                input_sha256=used, failed_case_evidence=getattr(exc, 'evidence', None))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-start
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak >= 3*GIB:
                result.update(status='failed_preserved', error='Existing3GiB RSS cap exceeded')
            result.update(wall_seconds=elapsed, peak_RSS_bytes=peak, finished_utc=datetime.now(timezone.utc).isoformat(),
                resource_limits=dict(CPU_count=1, simultaneous_jobs=1, wall_seconds=seconds,
                    RSS_bytes=3*GIB, reserve_bytes=2*GIB, maximum_input_file_bytes=MAX_FILE_BYTES))
            budget['spent_seconds'] += elapsed
            budget['runs'].append(dict(run_id=output.stem, stage='cached_contact_patch_audit', seconds=elapsed,
                status=result['status'], failure_reason=result.get('error'), finished_utc=result['finished_utc']))
            temporary = budget_path.with_suffix('.json.partial')
            temporary.write_text(json.dumps(budget, indent=2)+'\n')
            temporary.replace(budget_path)
            payload = json.dumps(result, indent=2, allow_nan=False)+'\n'
            require(shutil.disk_usage(output.parent).free >= 2*GIB+len(payload.encode()), 'Evidence write would violate2GiB reserve; failure retained in budget ledger')
            with output.open('x') as stream:
                stream.write(payload)
        print(json.dumps(dict(status=result['status'], output=str(output), new_PDE=0)))


if __name__ == '__main__':
    main()
