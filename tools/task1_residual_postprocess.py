"""Honest one-frequency ResidualShapeBasis readback; no solver or TIS inference.

The locked root controller provides a finite deadline. Native exporter identity,
configuration bytes and reference failures are never adapted or overwritten.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path
import time

FREQUENCY = 3000
RELATIVE = 1e-8
ABSOLUTE = 1e-14
GATES = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
             max_area_relative_error=1e-10, max_interface_normal_current_relative_error=2e-7)
RECONSTRUCTION = 'half_face_flux; top contact term averaged over full cell face h^2'
SOLVER_VERSION = 'literal-frozen-COCG-rtol-v1'


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _deadline(deadline, phase):
    _require(time.monotonic() < deadline, 'Residual postprocess deadline: '+phase)


def _write(path, value):
    temporary = path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def _sha(path, deadline):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while True:
            _deadline(deadline, 'hash:'+str(path))
            block = stream.read(4*1024**2)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _path(folder, name):
    choices = [p for p in (folder/name, folder/(name+'.gz')) if p.is_file()]
    _require(len(choices) == 1 and not choices[0].is_symlink(), 'One canonical native file required: '+name)
    return choices[0]


def _open(path, mode='rb'):
    return gzip.open(path, mode) if path.suffix == '.gz' else path.open(mode)


def _array(path, shape, deadline, np):
    _deadline(deadline, 'array:'+str(path))
    expected = math.prod(shape)*16
    with _open(path) as stream:
        raw = stream.read(expected+1)
    _require(len(raw) == expected, 'Exact complex128 array byte count differs: '+str(path))
    values = np.frombuffer(raw, dtype='<c16').reshape(shape)
    _require(np.isfinite(values).all(), 'Nonfinite complex native array: '+str(path))
    return values


def _properties(path):
    result = {}
    for line in path.read_text().splitlines():
        if '=' in line and not line.startswith(('#', '!')):
            key, value = line.split('=', 1)
            _require(key not in result, 'Duplicate config field')
            result[key] = value
    return result


def _same_decoded_bytes(left, right, deadline):
    with _open(left) as a, _open(right) as b:
        while True:
            _deadline(deadline, 'exact_decoded_grid_or_contact_comparison')
            aa, bb = a.read(1024**2), b.read(1024**2)
            if aa != bb:
                return False
            if not aa:
                return True


def compare_arrays(actual, reference, np, *, include_failed_entries=False):
    """Separate fixed componentwise and global-component-maxnorm criteria.

    All real/imaginary failed entries are recorded for small source/loss matrices.
    No criterion replaces the preserved historical componentwise comparison.
    """
    _require(actual.shape == reference.shape and np.isfinite(actual).all() and np.isfinite(reference).all(),
             'Comparison shape/nonfinite failure')
    a = np.ascontiguousarray(actual).view('<f8').reshape(actual.shape+(2,))
    b = np.ascontiguousarray(reference).view('<f8').reshape(reference.shape+(2,))
    difference = abs(a-b)
    magnitude = float(np.max(abs(b)))
    maximum = float(np.max(difference))
    limit = ABSOLUTE+RELATIVE*abs(b)
    failed = difference > limit
    result = dict(shape=list(actual.shape), components='little-endianFloat64 real/imag separately',
        decoded_binary_byte_equal=bool(np.array_equal(a.view('<u8'), b.view('<u8'))),
        maximum_reference_component_abs=magnitude, max_abs_error=maximum,
        relative_global_maxnorm_error=maximum/max(magnitude, 1e-300),
        normwise_limit_abs=ABSOLUTE+RELATIVE*magnitude,
        normwise_passed=bool(maximum <= ABSOLUTE+RELATIVE*magnitude),
        componentwise_passed=bool(not np.any(failed)), failed_component_count=int(np.count_nonzero(failed)),
        componentwise_tolerance=dict(relative=RELATIVE, absolute=ABSOLUTE))
    if include_failed_entries:
        result['failed_entries'] = [dict(index=[int(x) for x in index[:-1]],
            component='real' if index[-1] == 0 else 'imag', actual=float(a[index]), reference=float(b[index]),
            absolute_error=float(difference[index]), allowed_absolute_error=float(limit[index]))
            for index in zip(*np.nonzero(failed))]
    return result


def _load_basis(folder, case, deadline, np):
    _require(case.get('java_class') == case.get('exporter_class') == 'ResidualShapeBasis' and
             case.get('postprocessor') == 'residual_diagnostic' and case.get('frequencies_Hz') == [3000] and
             case.get('n_outputs') == case.get('channels') == 2 and case.get('n_pads') == 4,
             'Explicit2output4pad single-frequency residual registration required')
    names = ['BASIS_COMPLETE', 'validation.json', 'mesh-metadata.json', 'solver-diagnostics.json',
             'grid.csv', 'contacts-3000.csv']+[name+'-3000.bin' for name in ('field', 'potential', 'density', 'source', 'loss')]
    paths = {name: _path(folder, name) for name in names}
    hashes = {str(path): _sha(path, deadline) for path in paths.values()}
    metadata = json.loads(paths['mesh-metadata.json'].read_text())
    validation = json.loads(paths['validation.json'].read_text())
    solver = json.loads(paths['solver-diagnostics.json'].read_text())
    tolerance = case['requested_relative_tolerance']
    _require(tolerance in (1e-9, 1e-11) and metadata.get('exporter_class') == 'ResidualShapeBasis' and
             metadata.get('exporter_kind') == 'residual_diagnostic_native' and
             metadata.get('numerical_base_class') == 'SelectivityShapeBasis.ShapeNet' and
             metadata.get('solver_version') == SOLVER_VERSION and metadata.get('frequencies_Hz') == [3000] and
             metadata.get('solver_relative_tolerance') == tolerance and metadata.get('solver_max_iterations') == 12000,
             'Honest residual exporter/solver/frequency metadata differs')
    _require(metadata.get('channels') == metadata.get('n_outputs') == 2 and metadata.get('n_pads') == 4 and
             metadata.get('pad_node_ids') == [0, 1, -1, -1] and metadata.get('n_return_nodes') == 1 and
             metadata.get('return_topology') == 'common_GND' and metadata.get('basis_RHS_solves') == 2 and
             metadata.get('extra_potential_export_solves') == 0 and metadata.get('source_peak_V') == .5 and
             metadata.get('source_resistance_ohm') == 50 and metadata.get('phasor_convention') == 'peak,+jomega_t' and
             metadata.get('field_reconstruction') == RECONSTRUCTION,
             'Actual physical/electrical/field normalization differs')
    _require(metadata.get('radius_mm') == 25 and metadata.get('total_depth_mm') == 25.1 and
             metadata.get('tissue_boundaries_mm') == [0, .1, 5.1, 10.1, 25.1] and
             metadata.get('h_xy_mm') == case['h_xy_mm'] and metadata.get('sc_cells') == case['sc_cells'] == 2 and
             metadata.get('bulk_layer_counts') == case['bulk_counts'] == [14, 14, 40], 'Fixed phantom/mesh differs')
    config, mask = Path(case['config_file']).resolve(), Path(case['mask_file']).resolve()
    for path, expected in ((config, case['config_sha256']), (mask, case['mask_sha256'])):
        hashes[str(path)] = _sha(path, deadline)
        _require(hashes[str(path)] == expected, 'Registered physical input SHA differs')
    _require(metadata.get('config_sha256') == case['config_sha256'], 'Native config SHA differs')
    properties = _properties(config)
    _require(properties.get('frequencies') == '3000' and properties.get('channels') == '2' and
             float(properties['solver.relative_tolerance']) == tolerance and properties.get('solver.max_iterations') == '12000' and
             Path(properties['mask.path']).resolve() == mask and properties.get('mask.sha256') == case['mask_sha256'],
             'Actual configuration fields differ')
    gates = {}
    for key, limit in GATES.items():
        value = validation[key]
        _require(isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= limit,
                 'Original native numerical gate failed: '+key)
        gates[key] = dict(status='passed', value=value, limit=limit)
    actual_limit = 1e-9 if tolerance == 1e-11 else 2e-7
    _require(solver.get('schema') == 'task1-residual-solver-v1' and solver.get('status') == 'complete' and
             solver.get('solver_version') == SOLVER_VERSION and solver.get('relative_tolerance') == tolerance and
             solver.get('max_iterations') == 12000 and solver.get('native_residual_limit') == 2e-7 and
             solver.get('recomputed_diagnostic_limit') == actual_limit and len(solver.get('solves', [])) == 2,
             'Complete perRHS diagnostic receipt required')
    _require({row['basis_channel'] for row in solver['solves']} == {0, 1}, 'Unique2 basis RHS receipts required')
    for row in solver['solves']:
        _require(row['status'] == 'complete' and type(row['iterations']) is int and 1 <= row['iterations'] <= 12000 and
                 row['requested_relative_tolerance'] == tolerance and
                 all(isinstance(row[key], (int, float)) and math.isfinite(row[key]) and row[key] >= 0
                     for key in ('recursive_relative_residual', 'recomputed_relative_residual', 'relative_residual')) and
                 row['recursive_relative_residual'] <= tolerance and
                 row['relative_residual'] == row['recomputed_relative_residual'] <= actual_limit,
                 'Invalid/incomplete residual solve receipt')
    _require(validation['max_residual'] == max(row['recomputed_relative_residual'] for row in solver['solves']),
             'Native maxresidual differs from recomputed RHS receipts')
    with _open(paths['grid.csv'], 'rt') as stream:
        grid = np.atleast_1d(np.genfromtxt(stream, delimiter=',', names=True))
    n = len(grid)
    _require(n == metadata['cells'] == validation['cells'] == case['cells'] and 0 < n <= 800000 and
             validation['channels'] == validation['n_outputs'] == 2 and validation['n_pads'] == 4 and
             all(np.isfinite(grid[key]).all() for key in grid.dtype.names) and np.all(grid['volume_m3'] > 0),
             'Invalid actual native grid')
    _require(set(grid.dtype.names) == {'x_mm', 'y_mm', 'z_mm', 'layer', 'volume_m3'} and
             np.all(grid['x_mm']**2+grid['y_mm']**2 < 625) and
             np.all((grid['z_mm'] > 0) & (grid['z_mm'] < 25.1)) and
             np.equal(grid['layer'], np.round(grid['layer'])).all() and set(grid['layer'].astype(int)) == {0, 1, 2, 3},
             'Native grid leaves fixed phantom or has invalid tissue layers')
    expected_layer = np.searchsorted(np.asarray([.1, 5.1, 10.1]), grid['z_mm'], side='right')
    _require(np.array_equal(grid['layer'].astype(int), expected_layer), 'Native layer/depth assignment differs')
    with _open(paths['contacts-3000.csv'], 'rt') as stream:
        contacts = np.atleast_1d(np.genfromtxt(stream, delimiter=',', names=True))
    _require(set(contacts.dtype.names) == {'pad', 'x_mm', 'y_mm', 'area_m2'} and
             all(np.isfinite(contacts[key]).all() for key in contacts.dtype.names) and
             np.equal(contacts['pad'], np.round(contacts['pad'])).all() and
             set(contacts['pad'].astype(int)) == {0, 1, 2, 3} and np.all(contacts['area_m2'] > 0),
             'Invalid physical contact rows')
    pad, area = contacts['pad'].astype(int), contacts['area_m2']
    xy = np.column_stack((contacts['x_mm'], contacts['y_mm']))
    _require(np.all(np.sum(xy*xy, axis=1) < 625), 'Physical contact patch outside fixed top face')
    _, face_index = np.unique(xy, axis=0, return_inverse=True)
    _require(np.all(np.bincount(face_index, weights=area) <= (case['h_xy_mm']/1000)**2*(1+1e-10)),
             'Physical contact patches exceed top grid face area')
    areas = np.bincount(pad, weights=area, minlength=4)
    _require(all(abs(float(value)/.000225-1) <= 1e-10 for value in areas), 'Four225mm2 physical pads required')
    for p in range(4):
        _require(abs(float(properties[f'pad.{p}.represented_area_m2'])/.000225-1) <= 1e-10,
                 'Configuration pad area differs')
    shapes = dict(field=(2, n, 3), potential=(2, n), density=(2, len(contacts)), source=(2, 2), loss=(6, 2, 2))
    arrays = {kind: _array(paths[kind+'-3000.bin'], shape, deadline, np) for kind, shape in shapes.items()}
    source, loss, density = arrays['source'], arrays['loss'], arrays['density']
    current_by_signal = np.asarray([np.sum(density[:, pad == p]*area[pad == p], axis=1) for p in (0, 1)])
    signal_error = float(np.max(abs(current_by_signal-source))/max(float(np.max(abs(source))), 1e-30))
    balance_error = float(np.max(abs(np.sum(density*area, axis=1))/np.maximum(np.sum(abs(density)*area, axis=1), 1e-30)))
    _require(signal_error <= 2e-6 and balance_error <= 2e-6, 'Physical source/contact current balance failed')
    hermitian_error = float(np.max(abs(loss-loss.conj().transpose(0, 2, 1))))
    _require(np.allclose(loss, loss.conj().transpose(0, 2, 1), rtol=1e-10, atol=1e-12), 'Loss matrices not Hermitian')
    eigenvalues = np.linalg.eigvalsh((loss+loss.conj().transpose(0, 2, 1))/2)
    floor = 1e-14+1e-10*float(np.max(abs(loss)))
    _require(float(eigenvalues.min()) >= -floor, 'Loss matrix violates registered numerical passivity floor')
    power_errors = []
    coefficients = [np.asarray([1, 0], complex), np.asarray([0, 1], complex),
                    np.asarray([1, 1], complex), np.asarray([1, 1j], complex), np.asarray([.7+.2j, -.3+.9j], complex)]
    for c in coefficients:
        supplied = float(.25*np.vdot(c, source@c).real)
        dissipated = float(np.einsum('i,kij,j->', c.conj(), loss, c).real)
        error = abs(dissipated-supplied)/max(abs(supplied), 1e-20)
        _require(supplied >= -floor and error <= 2e-7, 'Arbitrary complex coefficient power balance failed')
        power_errors.append(error)
    hermitian_source_power = .125*(source+source.conj().T)
    power_defect = float(np.max(abs(loss.sum(axis=0)-hermitian_source_power)))
    diagnostics = dict(source_reciprocity=dict(absolute_A=float(abs(source[0, 1]-source[1, 0])),
        relative_to_source_max=float(abs(source[0, 1]-source[1, 0]))/max(float(np.max(abs(source))), 1e-30),
        acceptance_gate=False), loss_Hermitian_PSD=dict(status='passed', hermitian_max_abs_error_W=hermitian_error,
        eigenvalues_W=eigenvalues.tolist(), negative_eigenvalue_numerical_floor_W=floor),
        power_balance=dict(status='passed', fixed_complex_coefficients_relative_errors=power_errors,
            matrix_defect_max_abs_W=power_defect, matrix_defect_relative_global_maxnorm=power_defect/max(float(np.max(abs(loss.sum(axis=0)))), 1e-30),
            source_power_definition='.25*Re(c^H source c); peak0.5V basis; loss includes50ohm outputs'),
        source_current_balance=dict(status='passed', signal_node_relative_error=signal_error,
            all_contact_current_relative_error=balance_error, represented_pad_area_m2=areas.tolist()))
    return dict(arrays=arrays, paths=paths, hashes=hashes, metadata=metadata, validation=validation,
                gates=gates, solver=solver, numerical_diagnostics=diagnostics)


def process_case(folder, case, out, deadline):
    """Return calculated status independently of strict historical pass/fail."""
    from task1_grouped_registration import _caller_owns_execution_lock
    _caller_owns_execution_lock()
    import numpy as np

    folder, out = Path(folder).resolve(), Path(out).resolve()
    _require(out != folder and not out.is_relative_to(folder), 'Native files must remain immutable')
    _require(not out.exists() or not any(out.iterdir()), 'Never overwrite residual postprocess evidence')
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    stages = []

    def stage(name):
        _deadline(deadline, name)
        stages.append(dict(stage=name, elapsed_seconds=time.monotonic()-started))
        _write(out/'progress.json', dict(status='running', id=case['id'], stages=stages))

    try:
        stage('validate_honest_native_residual_basis')
        basis = _load_basis(folder, case, deadline, np)
        reference = case['diagnostic_reference']
        hashes = dict(basis['hashes'])
        for name, expected in reference['input_sha256'].items():
            hashes[name] = _sha(Path(name), deadline)
            _require(hashes[name] == expected, 'Pinned cached reference changed: '+name)
        comparisons = []
        stage('cached_native_array_comparison')
        for kind, values in basis['arrays'].items():
            ref_path = Path(reference['files'][kind+'-3000.bin'])
            previous = _array(ref_path, values.shape, deadline, np)
            row = compare_arrays(values, previous, np, include_failed_entries=kind in ('source', 'loss'))
            row['array_kind'] = kind
            comparisons.append(row)
            del previous
        exact_grid = _same_decoded_bytes(basis['paths']['grid.csv'], Path(reference['files']['grid.csv']), deadline)
        exact_contacts = _same_decoded_bytes(basis['paths']['contacts-3000.csv'], Path(reference['files']['contacts-3000.csv']), deadline)
        _require(exact_grid and exact_contacts, 'Fixed operator diagnostic grid/contact bytes differ')
        comparison = dict(schema='task1-residual-comparison-v1', id=case['id'],
            diagnostic_kind='single_frequency_solver_residual', frequency_Hz=3000,
            reference=reference, exact_grid_decoded_bytes=exact_grid, exact_contacts_decoded_bytes=exact_contacts,
            comparisons=comparisons, no_TIS_or_ROI_claim=True)
        if case['diagnostic_role'] == 'producer_regression':
            comparison['producer_regression'] = dict(status='passed' if all(row['normwise_passed'] for row in comparisons) else 'failed',
                criterion='max(abs(Float64_new-Float64_old)) <= 1e-14 + 1e-8*max(abs(Float64_old))',
                comparisons=comparisons, exact_grid_decoded_bytes=exact_grid, exact_contacts_decoded_bytes=exact_contacts,
                reference_producer='CloudShapeBasis exporting SelectivityShapeBasis identity',
                new_producer='ResidualShapeBasis with literal inherited default1e-9 arithmetic',
                independent_solver_validation=False)
        else:
            comparison['current_default_comparison'] = dict(status='calculated',
                reference_requested_tolerance=1e-9, new_requested_tolerance=case['requested_relative_tolerance'],
                comparisons=comparisons, original_D_strict_failure_reclassified=False)
            stage('preserved_componentwise_historical_matrices')
            matrices = []
            for kind in ('source', 'loss'):
                path = Path(case['historical_matrix_files'][kind])
                hashes[str(path)] = _sha(path, deadline)
                historical = _array(path, basis['arrays'][kind].shape, deadline, np)
                row = compare_arrays(basis['arrays'][kind], historical, np, include_failed_entries=True)
                row['array_kind'] = kind
                matrices.append(row)
            comparison['strict_historical_comparison'] = dict(status='passed' if all(row['componentwise_passed'] for row in matrices) else 'failed',
                componentwise_tolerance=dict(relative=RELATIVE, absolute=ABSOLUTE), matrices=matrices,
                criterion='abs(new_component-old_component) <= 1e-14 + 1e-8*abs(old_component)',
                previous_D_failure_preserved=True, old_fine_C1_promoted=False,
                scope='3000Hz source/loss only; not full4frequency historical reproduction',
                normwise_diagnostics_substituted_for_strict_gate=False)
        stage('verify_all_inputs_unchanged')
        for name, expected in hashes.items():
            _require(_sha(Path(name), deadline) == expected, 'Input changed during residual readback: '+name)
        pre_path = folder.parents[1]/'preregistration.json'
        pre = json.loads(pre_path.read_text())
        _require(any(c['id'] == case['id'] and c['config_sha256'] == case['config_sha256'] for c in pre['cases']),
                 'Current registration/case differs')
        _write(out/'comparison.json', comparison)
        summary = dict(schema_version=1, status='complete', calculation_status='calculated', id=case['id'],
            diagnostic_kind='single_frequency_solver_residual', frequencies_Hz=[3000],
            config_sha256=case['config_sha256'], requested_relative_tolerance=case['requested_relative_tolerance'],
            source_commit=pre['source_commit'], source_and_input_sha256=pre['source_and_input_sha256'],
            mesh_metadata=basis['metadata'], validation=basis['validation'], validation_gate_status=basis['gates'],
            solver_diagnostics=basis['solver'], numerical_diagnostics=basis['numerical_diagnostics'],
            input_sha256=hashes, postprocessor_sha256=_sha(Path(__file__), deadline),
            artifacts=dict(summary=str(out/'summary.json'), comparison=str(out/'comparison.json'),
                progress=str(out/'progress.json'), native_validation=str(basis['paths']['validation.json']),
                solver_diagnostics=str(basis['paths']['solver-diagnostics.json'])),
            stages=stages, elapsed_seconds=time.monotonic()-started, new_PDE=0,
            source_inputs_unchanged=True, full_TIS_waveform_or_probe_prediction=False,
            rigorous_forward_error_bound=False, independent_solver_validation=False,
            historical_strict_failure_hold=pre['historical_strict_failure_hold'],
            holds=['Single frequency diagnostic; no modulation/ROI/probe or activation inference',
                   'Original D full-reference strict failure remains unchanged; any new pass has narrower3000Hz scope'])
        for key in ('producer_regression', 'current_default_comparison', 'strict_historical_comparison'):
            if key in comparison:
                summary[key] = comparison[key]
        _write(out/'summary.json', summary)
        _write(out/'progress.json', dict(status='complete', calculation_status='calculated', id=case['id'], stages=stages,
            elapsed_seconds=summary['elapsed_seconds']))
        return summary
    except BaseException as error:
        _write(out/'failure.json', dict(status='postprocess_failed_preserved', id=case['id'],
            error_type=type(error).__name__, error=str(error), stages=stages,
            elapsed_seconds=time.monotonic()-started, partial_evidence_preserved=True))
        raise
