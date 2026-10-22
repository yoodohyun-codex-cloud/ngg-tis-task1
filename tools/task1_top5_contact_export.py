"""Bounded-input contact-normal J exporter for a reviewed top-five catalog row.

Import performs no research reads. The caller owns the finite execution guard,
both global locks and ledger. E, phi, grid and scalar archives are never read.
"""
from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 32*1024**2
MAX_PATCHES = 12800
REGRESSION_REL = 2e-7
REGRESSION_ABS = 1e-14
J_KEYS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2')
NATIVE_GATES = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
                    max_area_relative_error=1e-10, max_interface_normal_current_relative_error=2e-7)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check_time(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Finite contact export deadline exceeded')


def decode_coefficients(obj, frequencies):
    frequencies = tuple(frequencies)
    require(frequencies and len(set(frequencies)) == len(frequencies) and
            all(type(f) is int and f > 0 for f in frequencies), 'Distinct native integer-Hz frequencies required')
    require(isinstance(obj, dict) and bool(obj), 'Bound saved complex coefficient vectors required')
    result = {f: np.zeros(2, complex) for f in frequencies}
    seen = set()
    for key, value in obj.items():
        require(type(key) in (str, int) and str(key).isdigit(), 'Integer coefficient frequency key required')
        f = int(key)
        require(f in result and f not in seen, 'Unknown or duplicate coefficient frequency')
        seen.add(f)
        require(isinstance(value, dict) and 'real' in value and
                (('imaginary' in value) != ('imag' in value)), 'One explicit imaginary/imag coefficient component required')
        re = np.asarray(value['real'], float)
        im = np.asarray(value.get('imaginary', value.get('imag')), float)
        require(re.shape == im.shape == (2,) and np.isfinite(re).all() and np.isfinite(im).all(),
                'Finite two-output complex coefficients required')
        result[f] = re+1j*im
    require(any(np.any(c) for c in result.values()), 'Zero command cannot represent an evaluated TIS row')
    return result


def contact_rms(density_by_frequency, coefficients):
    require(bool(density_by_frequency) and set(density_by_frequency) == set(coefficients),
            'Identical explicit native density/coefficient frequency sets required')
    squares, count = None, None
    for f, values in density_by_frequency.items():
        density = np.asarray(values, complex)
        c = np.asarray(coefficients[f], complex)
        require(density.ndim == 2 and density.shape[0] == 2 and 0 < density.shape[1] <= MAX_PATCHES and
                c.shape == (2,) and np.isfinite(density).all() and np.isfinite(c).all(),
                'Finite channel-major complex128(2,npatches) density required')
        if count is None:
            count = density.shape[1]
            squares = np.zeros(count)
        require(density.shape[1] == count, 'Native contact ordering/count must agree across frequencies')
        # Coherent source outputs are combined BEFORE magnitude/squaring.
        squares += np.abs(c@density)**2/2
    result = np.sqrt(squares)
    require(np.isfinite(result).all(), 'Contact RMS overflow')
    return result


def weighted_p95(values, areas):
    values, areas = np.asarray(values, float), np.asarray(areas, float)
    require(values.ndim == areas.ndim == 1 and values.shape == areas.shape and len(values) and
            np.isfinite(values).all() and np.isfinite(areas).all() and np.all(values >= 0) and np.all(areas > 0),
            'Finite nonnegative patch values and positive physical contact areas required')
    order = np.argsort(values, kind='stable')
    # Match the executed frozen postprocessor, including sequential CDF rounding.
    cumulative = np.cumsum(areas[order])
    require(np.isfinite(cumulative).all(), 'Contact-area cumulative overflow')
    index = min(int(np.searchsorted(cumulative, .95*cumulative[-1])), len(order)-1)
    return float(values[order[index]])


def validate_contacts(rows, h_mm, n_pads=4):
    require(type(n_pads) is int and 4 <= n_pads <= 16 and type(h_mm) in (int, float) and
            math.isfinite(h_mm) and h_mm > 0 and 0 < len(rows) <= MAX_PATCHES,
            'Supported physical-pad count, positive spacing and bounded patches required')
    seen, sums = set(), np.zeros(n_pads)
    face = (h_mm/1000)**2
    for pad, x, y, area in rows:
        require(type(pad) is int and 0 <= pad < n_pads and all(math.isfinite(v) for v in (x, y, area)) and
                x*x+y*y < 625 and 0 < area <= face*(1+1e-12), 'Invalid physical top contact patch')
        i, j = round((x+25)/h_mm-.5), round((y+25)/h_mm-.5)
        require(abs(x-(-25+(i+.5)*h_mm)) <= 1e-9 and abs(y-(-25+(j+.5)*h_mm)) <= 1e-9,
                'Contact coordinates must be actual native XY cell centers')
        key = (pad, i, j)
        require(key not in seen, 'Duplicate physical contact patch')
        seen.add(key)
        sums[pad] += area
    require(set(k[0] for k in seen) == set(range(n_pads)), 'Every physical pad needs a positive contact area')
    return dict(n_patches=len(rows), pad_areas_m2=sums.tolist(), total_area_m2=float(sums.sum()))


def regression_checks(values, areas, raw_metrics, normalizations, scales):
    aggregate = dict(zip(J_KEYS, (float(np.max(values)), weighted_p95(values, areas))))
    require('skin_contact_only' in normalizations and 'skin_contact_only' in scales,
            'Bound original eight-cap skin_contact_only mode required')
    checks = []
    for mode, metrics, scale in [('raw', raw_metrics, 1.)]+[
            (name, normalizations[name]['normalized_burdens'], scales[name]) for name in scales]:
        require(type(scale) in (int, float) and math.isfinite(scale) and scale > 0, 'Positive finite saved amplitude scale required')
        if mode != 'raw':
            require(math.isclose(scale, normalizations[mode]['amplitude_scale'], rel_tol=1e-12, abs_tol=0),
                    'Catalog mode scale differs from its saved normalization')
        for key in J_KEYS:
            expected, actual = metrics[key], aggregate[key]*scale
            require(type(expected) in (int, float) and math.isfinite(expected) and expected >= 0,
                    'Finite saved J aggregate required')
            error = abs(actual-expected)
            passed = error <= REGRESSION_ABS+REGRESSION_REL*abs(expected)
            checks.append(dict(mode=mode, metric=key, actual_A_m2=actual, saved_A_m2=expected,
                               absolute_error_A_m2=error, relative_error=error/max(abs(expected), 1e-30), passed=passed))
    require(all(c['passed'] for c in checks), 'Contact J max/P95 disagrees with bound saved raw/normalized metrics')
    return aggregate, checks


def _descriptor(value):
    require(isinstance(value, dict) and isinstance(value.get('path'), str), 'Bound path/SHA descriptor required')
    digest = value.get('SHA256', value.get('sha256'))
    require(isinstance(digest, str) and len(digest) == 64, 'Descriptor SHA256 required')
    return Path(value['path']), digest


def _basis(row):
    path, _ = _descriptor(row['native_summary'])
    return path.parents[2]/'bases'/row['source_case_id']


def _native_path(row, name):
    paths = [Path(p) for p in row['declared_native_inputs'] if Path(p).parent == _basis(row) and
             Path(p).name in (name, name+'.gz')]
    require(len(paths) == 1, 'Missing/ambiguous declared small native input: '+name)
    return paths[0]


def required_contact_paths(row):
    """Return path:SHA pins; only the small frozen manifest is read, no native data.

    This metadata helper is for the caller's preregistration stage. Its newly
    observed manifest digest is frozen there, before export_contact is called.
    """
    basis = _basis(row)
    result = dict(row.get('source_refs', {}))
    for key in ('native_summary', 'native_registration', 'native_case_record', 'native_config', 'mesh'):
        path, digest = _descriptor(row[key])
        result[str(path)] = digest
    for name in ('BASIS_COMPLETE', 'validation.json', 'mesh-metadata.json'):
        path = _native_path(row, name)
        result[str(path)] = row['declared_native_inputs'][str(path)]
    result[str(Path(row['case']['mask_file']))] = row['case']['mask_sha256']
    for f in row['mesh_metadata']['frequencies_Hz']:
        for name in (f'contacts-{f}.csv', f'density-{f}.bin'):
            path = _native_path(row, name)
            result[str(path)] = row['declared_native_inputs'][str(path)]
    if row.get('condition_source'):
        path, digest = _descriptor(row['condition_source'])
        result[str(path)] = digest
    else:
        manifest_path = basis.parents[1]/'frozen-source-manifest.json'
        require(manifest_path.is_absolute() and manifest_path == manifest_path.resolve() and
                manifest_path.is_relative_to(ROOT) and manifest_path.is_file() and not manifest_path.is_symlink() and
                manifest_path.stat().st_size <= MAX_FILE_BYTES, 'Bound small frozen-source manifest required')
        data = manifest_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(str(manifest_path) not in result or result[str(manifest_path)] == digest, 'Frozen source manifest changed')
        result[str(manifest_path)] = digest
        identity = json.loads(data)['files'][str(ROOT/'tis-java/explore_tis.py')]
        wave = basis.parents[1]/'frozen-source/tis-java/explore_tis.py'
        require((ROOT/identity['path']).resolve() == wave, 'Frozen waveform source path mismatch')
        result[str(wave)] = identity['sha256']
    return result


def _literal(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_literal(node.operand)
    if isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
        a, b = _literal(node.left), _literal(node.right)
        return {ast.Add: lambda:a+b, ast.Sub: lambda:a-b, ast.Mult: lambda:a*b, ast.Div: lambda:a/b}[type(node.op)]()
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == 'math' and node.func.attr == 'sqrt' and len(node.args) == 1 and not node.keywords:
        return math.sqrt(_literal(node.args[0]))
    raise ValueError('Unsupported frozen waveform literal arithmetic')


def _native_coefficients(condition, frequencies, wave_source):
    waves = None
    for node in ast.parse(wave_source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'WAVES' for t in node.targets):
            require(waves is None and isinstance(node.value, ast.Dict), 'Unique literal frozen WAVES required')
            waves = {k.value:tuple(_literal(e) for e in v.elts) for k, v in zip(node.value.keys, node.value.values)}
    require(waves is not None and condition['waveform'] in waves, 'Unsupported bound native waveform')
    require(condition['carrier_group'] == [0, 1] and condition['actual_fundamental_Hz'] == [3000, 3030] and
            condition['source_Vpp_per_output'] == 1., 'Only actual native canonical two-output source recipe supported')
    phase = np.asarray(condition['phase_deg'], float)
    require(phase.shape == (2,) and np.isfinite(phase).all(), 'Explicit finite native source phases required')
    coefficients = {f:np.zeros(2, complex) for f in frequencies}
    for output, carrier in enumerate((3000, 3030)):
        for harmonic, amplitude in zip((1, 3), waves[condition['waveform']]):
            if amplitude:
                f = carrier*harmonic
                require(f in coefficients, 'Active native harmonic missing from exported basis')
                coefficients[f][output] = -1j*amplitude*np.exp(1j*harmonic*math.radians(float(phase[output])))
    return coefficients


def export_contact(row, *, required_pins, deadline=None):
    """Export contact patches only after raw and all five saved-mode regressions.

    Missing/unsupported/unbound sources raise ValueError; no substitute map is
    returned. The finite caller must report this as missing rather than fabricate.
    """
    used = {}
    def pin(path, expected=None):
        check_time(deadline)
        path = Path(path)
        require(path.is_absolute() and path == path.resolve() and path.is_relative_to(ROOT) and path.is_file() and
                not path.is_symlink(), 'Canonical regular repository input required: '+str(path))
        require(not path.name.startswith(('field-', 'potential-', 'grid.csv')) and path.suffix != '.npz' and
                path.stat().st_size <= MAX_FILE_BYTES, 'Excluded/oversized contact-export input: '+str(path))
        require(str(path) in required_pins, 'Contact input lacks caller preregistration SHA: '+str(path))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == required_pins[str(path)] and (expected is None or digest == expected), 'Pinned contact input changed: '+str(path))
        used[str(path)] = digest
        return path
    def read_desc(desc):
        path, digest = _descriptor(desc)
        return json.loads(pin(path, digest).read_text())
    for name, digest in row.get('source_refs', {}).items():
        pin(name, digest)
    summary = read_desc(row['native_summary'])
    registration = read_desc(row['native_registration'])
    record = read_desc(row['native_case_record'])
    config_path, config_sha = _descriptor(row['native_config'])
    pin(config_path, config_sha)
    require(summary['status'] == record['status'] == 'complete' and summary['id'] == record['id'] == row['source_case_id'],
            'One genuinely completed native source case required')
    require(summary['input_sha256'] == row['declared_native_inputs'], 'Catalog native declarations differ from completed source manifest')
    cases = [c for c in registration['cases'] if c['id'] == row['source_case_id']]
    require(len(cases) == 1 and cases[0] == row['case'], 'Catalog physical case differs from exact native registration')
    case = cases[0]
    require(case['config_sha256'] == config_sha == row['configuration_sha256'] == record['config_sha256'] and
            Path(case['config_file']) == config_path and record['postprocess_sha256'] == _descriptor(row['native_summary'])[1],
            'Native configuration/postprocess receipt identity mismatch')
    circuit = case['circuit']
    require(circuit == row['circuit'] and circuit['n_outputs'] == 2 and circuit['n_return_nodes'] == 1 and
            circuit['source_peak_V'] == .5 and circuit['source_resistance_ohm'] == 50 and
            'common_GND' in circuit['return_topology'], 'Two actual50ohm outputs and one common-GND return required')
    def native(name):
        p = _native_path(row, name)
        return pin(p, summary['input_sha256'][str(p)])
    native('BASIS_COMPLETE')
    meta = json.loads(native('mesh-metadata.json').read_text())
    meta_desc = read_desc(row['mesh'])
    require(meta == meta_desc == row['mesh_metadata'] == summary['mesh_metadata'] and meta['channels'] == 2 and
            type(meta['cells']) is int and 0 < meta['cells'] <= 800000 and meta['radius_mm'] == 25 and
            meta['source_peak_V'] == .5 and meta['source_resistance_ohm'] == 50 and
            meta['config_sha256'] == config_sha and
            (meta['exporter_kind'], meta['exporter_class']) in
                (('selectivity_native', 'SelectivityShapeBasis'), ('grouped_native', 'GroupedPadBasis')) and
            'half_face_flux' in meta['field_reconstruction'], 'Unsupported native model/reconstruction metadata')
    validation = json.loads(native('validation.json').read_text())
    require(validation == summary['validation'] == record['validation'], 'Native validation receipt differs from source postprocess')
    for key, limit in NATIVE_GATES.items():
        require(type(validation.get(key)) in (int, float) and math.isfinite(validation[key]) and 0 <= validation[key] <= limit,
                'Preserved native gate failed: '+key)
    frequencies = meta['frequencies_Hz']
    condition = None
    if row.get('condition_source'):
        condition = read_desc(row['condition_source'])
        source = condition.get('source_provenance', condition)
        require(condition['id'] == row['condition_id'] and source.get('source_case_id', source.get('case_id')) == case['id'] and
                source.get('configuration_sha256', condition.get('configuration_sha256')) == config_sha,
                'Actual saved command belongs to a different case/configuration')
        require(condition.get('status') == 'calculated_unadopted' and condition.get('candidate_adopted') is False,
                'Completed, explicitly unadopted actual saved command required')
        require('coefficient_vectors' in condition, 'Actual command lacks explicit final coefficient vectors')
        coefficients = decode_coefficients(condition['coefficient_vectors'], frequencies)
        if row.get('coefficient_vectors') is not None:
            supplied = decode_coefficients(row['coefficient_vectors'], frequencies)
            require(all(np.array_equal(coefficients[f], supplied[f]) for f in frequencies), 'Catalog command differs from saved final vectors')
        recipe = 'Saved final raw complex coefficient_vectors used verbatim; no second global/column normalization and no extra0.5 factor'
    else:
        found = [c for c in summary['conditions'] if c['id'] == row['condition_id']]
        require(len(found) == 1 and found[0] == row['native_condition'], 'Exact native postprocess condition required')
        condition = found[0]
        run = _basis(row).parents[1]
        frozen = json.loads(pin(run/'frozen-source-manifest.json').read_text())
        wave = run/'frozen-source/tis-java/explore_tis.py'
        identity = frozen['files'][str(ROOT/'tis-java/explore_tis.py')]
        require((ROOT/identity['path']).resolve() == wave and frozen['source_commit'] == registration['source_commit'] and
                identity['sha256'] == registration['source_and_input_sha256'][str(ROOT/'tis-java/explore_tis.py')],
                'Frozen waveform source/registration mismatch')
        coefficients = _native_coefficients(condition, frequencies, pin(wave, identity['sha256']).read_text())
        recipe = 'Bound native condition group/phases plus exact frozen WAVES literal; peak0.5V density basis already includes source amplitude'
    raw_metrics = condition.get('electrical_metrics', condition.get('metrics'))
    require(isinstance(raw_metrics, dict) and row['electrical_metrics'] == raw_metrics, 'Catalog raw electrical metrics differ from actual source')
    densities, contacts = {}, None
    for f in frequencies:
        contact_path = native(f'contacts-{f}.csv')
        opener = gzip.open if contact_path.suffix == '.gz' else open
        with opener(contact_path, 'rt') as stream:
            reader = csv.DictReader(stream)
            require(reader.fieldnames == ['pad', 'x_mm', 'y_mm', 'area_m2'], 'Unsupported physical contact CSV schema')
            rows = [(int(r['pad']), float(r['x_mm']), float(r['y_mm']), float(r['area_m2'])) for r in reader]
        if contacts is None:
            contacts = rows
            area_proof = validate_contacts(rows, meta['h_xy_mm'], circuit['n_pads'])
        require(rows == contacts, 'Native contact identity/order differs across frequencies')
        density_path = native(f'density-{f}.bin')
        opener = gzip.open if density_path.suffix == '.gz' else open
        expected_bytes = 2*len(rows)*16
        with opener(density_path, 'rb') as stream:
            data = stream.read(expected_bytes+1)
        require(len(data) == expected_bytes, 'Truncated/oversized native density; expected little-endian complex128(2,npatches)')
        densities[f] = np.frombuffer(data, dtype='<c16').reshape(2, len(rows))
    expected_areas = np.asarray(case['expected_pad_areas_m2'], float)
    actual_areas = np.asarray(area_proof['pad_areas_m2'])
    require(expected_areas.shape == actual_areas.shape and np.isfinite(expected_areas).all() and np.all(expected_areas > 0) and
            np.max(abs(actual_areas/expected_areas-1)) <= 1e-10, 'Physical represented pad areas differ from registration')
    mask = pin(case['mask_file'], case['mask_sha256'])
    with mask.open() as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ['pad', 'i', 'j', 'area_m2'], 'Explicit physical contact mask required')
        declared = {}
        for r in reader:
            key = (int(r['pad']), int(r['i']), int(r['j']))
            require(key not in declared, 'Duplicate mask physical face')
            declared[key] = float(r['area_m2'])
    actual = {(p, round((x+25)/meta['h_xy_mm']-.5), round((y+25)/meta['h_xy_mm']-.5)):a for p,x,y,a in contacts}
    require(actual.keys() == declared.keys() and all(math.isclose(a, declared[k], rel_tol=1e-12, abs_tol=1e-24) for k,a in actual.items()),
            'Actual physical contact patches differ from registered mask')
    values = contact_rms(densities, coefficients)
    aggregate, checks = regression_checks(values, [r[3] for r in contacts], raw_metrics, row['normalizations'], row['scales'])
    for path, digest in used.items():
        check_time(deadline)
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'Consumed contact input changed during export')
    columns = dict(pad=np.asarray([r[0] for r in contacts], int), x_mm=np.asarray([r[1] for r in contacts]),
                   y_mm=np.asarray([r[2] for r in contacts]), area_m2=np.asarray([r[3] for r in contacts]),
                   raw_J_RMS_A_m2=values)
    return dict(schema='task1-top5-contact-normal-J-v1', status='verified_cached_contact_export', id=row['id'],
        source_case_id=case['id'], condition_id=row['condition_id'], configuration_sha256=config_sha,
        source_postprocessor_sha256=summary['postprocessor_sha256'],
        frequency_bindings={str(f):dict(contacts=dict(path=str(_native_path(row, f'contacts-{f}.csv')),
            SHA256=summary['input_sha256'][str(_native_path(row, f'contacts-{f}.csv'))]),
            density=dict(path=str(_native_path(row, f'density-{f}.bin')),
            SHA256=summary['input_sha256'][str(_native_path(row, f'density-{f}.bin'))])) for f in frequencies},
        input_sha256=used, inputs_unchanged=True, aggregate_raw=aggregate, regression_checks=checks,
        regression=dict(passed=True, aggregate_raw=aggregate, checks=checks,
                        relative_tolerance=REGRESSION_REL, absolute_tolerance_A_m2=REGRESSION_ABS),
        weighted_p95_A_m2=aggregate['surface_J_RMS_p95_A_m2'], **columns,
        regression_tolerance=dict(relative=REGRESSION_REL, absolute_A_m2=REGRESSION_ABS), area_validation=area_proof,
        coefficient_recipe=recipe, coefficient_vectors={str(f):dict(real=c.real.tolist(), imaginary=c.imag.tolist()) for f,c in coefficients.items()},
        frequencies_Hz=frequencies, inactive_frequencies_Hz=[f for f in frequencies if not np.any(coefficients[f])],
        inactive_output_termination='Uncommanded frequency remains0V through50ohm in original basis; no circuit/operator change',
        density_storage='little-endian complex128(2,npatches), channel major; peak0.5V source basis,+jwt',
        J_definition='Contact-face normal RMS sqrt(sum_f |sum_output c_f*density_f|^2/2); not skin-cell vector RMS',
        percentile_definition='Stable sorted values; nearest first sequential cumulative physical contact area reaching95%; no interpolation',
        contact_plane_z_mm=0,
        saved_mode_amplitude_scales=dict(row['scales']), instrument_prediction=False, new_PDE=0,
        full_skin_vector_J_inferred=False, candidate_adopted=False, convergence_promoted=False,
        PBS_skin_contact_validation=False)
