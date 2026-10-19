"""Pure stored-data postprocessing for the finite 3 kHz SC/XY diagnostic.

No Java, PDE, process, git, producer, source-result or GUI-pointer operation is
available here.  ``analyze_case`` returns a JSON-serializable result; the caller
owns new-run publication, failure preservation and resource supervision.
Native phi gates are hard failures, separate from the producer's PDE status.
"""
from pathlib import Path
import hashlib
import json
import math
import time

import numpy as np

from layered_probe_analysis import (LayeredPotentialSampler, SamplingLimits,
                                    evaluate_layered_probe)
from native_probe_followup import (EPS0, drive_coefficients,
                                   geometry_from_registered_grid)
from leader_spatial_diagnostics import (CacheUnavailable as SpatialCacheUnavailable,
                                        analyze_case as analyze_spatial_case)


FREQUENCIES_HZ = (3000, 3030, 9000, 9090)
WAVEFORMS = ('sine', 'square_3h', 'triangle_3h')
REPO_ROOT = Path(__file__).resolve().parent.parent
NUMERICAL_LIMITS = dict(max_residual=2e-7, max_power_error=2e-7,
                        max_current_error=2e-6)


class PostprocessValidationError(ValueError):
    """Keep raw electrical outputs, report a distinct postprocessing failure."""


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def _canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _resolve(path):
    value = Path(path)
    return (value if value.is_absolute() else REPO_ROOT/value).resolve()


def _json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda value: (_ for _ in ()).throw(
        PostprocessValidationError('Nonfinite original JSON: ' + value)))


def _properties(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if '=' not in line or line.lstrip().startswith(('#', '!')):
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip()
        if key in values:
            raise PostprocessValidationError('Duplicate source configuration key: ' + key)
        values[key] = value
    return values


def _pin(path, expected=None):
    path = _resolve(path)
    if not path.is_file():
        raise PostprocessValidationError('Required stored input is missing: ' + str(path))
    actual = _sha256(path)
    if expected is not None and expected != actual:
        raise PostprocessValidationError('Pinned stored input changed: ' + str(path))
    return path, actual


def _declared_source_hashes(metadata):
    """Use explicit guard paths; basename source labels need a pinned path join."""
    paths = {}
    guards = metadata.get('guard_hashes', {})
    for path, expected in guards.items():
        actual_path, actual = _pin(path, expected)
        paths[str(actual_path)] = actual
    for label, expected in metadata.get('source_hashes', {}).items():
        path = _resolve(label)
        if not path.is_file() and Path(label).name == label:
            matches = [Path(p) for p, value in paths.items()
                       if Path(p).name == label and value == expected]
            if len(matches) != 1:
                raise PostprocessValidationError('Source hash label needs one explicit matching guard path: ' + label)
            path = matches[0]
        actual_path, actual = _pin(path, expected)
        paths[str(actual_path)] = actual
    return paths


def _metric_rows(metrics, config, condition_id):
    if isinstance(metrics, dict):
        metrics = metrics.get('metrics', [metrics])
    rows = [dict(row) for row in metrics]
    if len(rows) != 3 or {row.get('waveform') for row in rows} != set(WAVEFORMS):
        raise PostprocessValidationError('Exactly the three registered sine/square_3h/triangle_3h rows are required')
    for row in rows:
        # These are the fixed preregistered drive conditions, not silent 2 kHz defaults.
        expected = dict(output_channels=2, carrier_Hz=3000, beat_Hz=30,
                        carrier_group=[0, 1], phase_deg=[0., 0.])
        for key, value in expected.items():
            if key not in row or row[key] != value:
                raise PostprocessValidationError('Registered 3 kHz candidate condition differs or is absent: ' + key)
        if 'h_mm' in row and not math.isclose(float(row['h_mm']), float(config['h_mm']), rel_tol=0, abs_tol=1e-12):
            raise PostprocessValidationError('Candidate XY mesh differs from actual config')
        for metric in ('target20_total_E_RMS_V_m', 'target20_modulation_V_m'):
            value = float(row[metric])
            if not math.isfinite(value) or value <= 0:
                raise PostprocessValidationError('Invalid stored source metric: ' + metric)
        row.setdefault('id', condition_id+'-'+row['waveform'])
    return rows


def analyze_case(basis_dir, metrics, mesh_metadata, *, potential_dir=None):
    """Return three waveforms' 40 native probes and existing spatial diagnostics.

    ``mesh_metadata`` requires actual h_xy_mm/layer_counts/z_faces_mm plus
    config_path/config_sha256 and source_run_id/source_condition_id (or case_id).
    Optional source_hashes/guard_hashes and expected_output_hashes are enforced.
    Materials are read from the exact config, never replaced with default tissue
    constants.  The original 0.5 V peak/50 ohm/+jwt basis convention is retained.

    ``potential_dir`` may point to an already completed native baseline export.
    Its grid and every actual-frequency complex E file must match ``basis_dir``
    byte for byte; missing potential is never inferred or regenerated.

    Hard native phi/E or centre-RMS failures raise PostprocessValidationError.
    Incomplete/failed spatial interpolation remains in its separate spatial key;
    it cannot hide behind a passed native probe or electrical producer status.
    """
    started = time.monotonic()
    folder = _resolve(basis_dir)
    native = _resolve(potential_dir) if potential_dir is not None else folder
    metadata = dict(mesh_metadata)
    run_id = metadata.get('source_run_id')
    condition_id = metadata.get('source_condition_id', metadata.get('case_id'))
    if not isinstance(run_id, str) or not run_id or not isinstance(condition_id, str) or not condition_id:
        raise PostprocessValidationError('Explicit new-run and mesh-case source IDs are required')
    if 'config_path' not in metadata or 'config_sha256' not in metadata:
        raise PostprocessValidationError('Exact original config path and SHA-256 are required')
    config_path, config_sha = _pin(metadata['config_path'], metadata['config_sha256'])
    config = _properties(config_path)
    if tuple(int(f) for f in config.get('frequencies', '').split(',') if f) != FREQUENCIES_HZ or config.get('channels') != '2':
        raise PostprocessValidationError('The finite postprocessor fixes 3000/3030/9000/9090 Hz and two outputs')
    source_hashes = _declared_source_hashes(metadata)
    input_hashes = {str(config_path): config_sha}
    names = ['BASIS_COMPLETE', 'validation.json', 'grid.csv'] + [f'field-{f}.bin' for f in FREQUENCIES_HZ]
    for name in names:
        path, actual = _pin(folder/name)
        input_hashes[str(path)] = actual
    validation = _json(folder/'validation.json')
    for key, limit in NUMERICAL_LIMITS.items():
        value = float(validation[key])
        if not math.isfinite(value) or not 0 <= value <= limit:
            raise PostprocessValidationError('Stored producer numerical gate failed: ' + key)
    if validation.get('channels') != 2 or not isinstance(validation.get('cells'), int) or not 0 < validation['cells'] <= 800000:
        raise PostprocessValidationError('Stored producer dimensions exceed registered limits')
    if 'max_area_relative_error' in validation:
        area_error = float(validation['max_area_relative_error'])
        if not math.isfinite(area_error) or not 0 <= area_error <= 1e-10:
            raise PostprocessValidationError('Stored producer electrode-area gate failed')
    grid = np.genfromtxt(folder/'grid.csv', delimiter=',', names=True)
    if len(grid) != validation['cells']:
        raise PostprocessValidationError('Stored grid/producer cell counts differ')
    if metadata.get('exporter_kind', 'validation_native') != 'validation_native':
        raise PostprocessValidationError('Independent SC/XY postprocessing requires explicit validation-native mesh metadata')
    geometry = geometry_from_registered_grid(grid, config,
        dict(exporter_kind='validation_native', mesh_metadata=metadata))
    # A producer's actual mesh file is itself an input if present.
    if (folder/'mesh-metadata.json').is_file():
        path, actual = _pin(folder/'mesh-metadata.json')
        input_hashes[str(path)] = actual
        actual_metadata = _json(path)
        for key in ('layer_counts', 'z_faces_mm', 'h_xy_mm'):
            if key not in actual_metadata:
                raise PostprocessValidationError('Actual exporter mesh metadata lacks ' + key)
            if not np.allclose(np.asarray(actual_metadata[key]), np.asarray(metadata[key]), rtol=0, atol=1e-9):
                raise PostprocessValidationError('Caller and actual exporter mesh metadata differ: ' + key)
    elif potential_dir is None:
        raise PostprocessValidationError('New validation-native basis lacks its actual mesh-metadata.json')
    potential_grid_match = None
    if native != folder:
        for name in ('BASIS_COMPLETE', 'grid.csv', *[f'field-{f}.bin' for f in FREQUENCIES_HZ]):
            path, actual = _pin(native/name)
            input_hashes[str(path)] = actual
            if name != 'BASIS_COMPLETE' and actual != input_hashes[str((folder/name).resolve())]:
                raise PostprocessValidationError('Retained native export does not reproduce original baseline: ' + name)
        potential_grid_match = dict(passed=True, grid_and_each_frequency_field_exact_SHA=True,
                                    original_basis_dir=str(folder), retained_native_dir=str(native))
    potentials, fields = {}, {}
    geometry['gamma_S_m'] = {}
    for f in FREQUENCIES_HZ:
        p, actual = _pin(native/f'potential-{f}.bin')
        input_hashes[str(p)] = actual
        if p.stat().st_size != 2*len(grid)*16 or (folder/f'field-{f}.bin').stat().st_size != 2*len(grid)*3*16:
            raise PostprocessValidationError('Native potential/E shape is not [2,cells] / [2,cells,3]')
        potentials[f] = np.memmap(p, mode='r', dtype='<c16', shape=(2, len(grid)))
        fields[f] = np.memmap(folder/f'field-{f}.bin', mode='r', dtype='<c16', shape=(2, len(grid), 3))
        geometry['gamma_S_m'][f] = {i: complex(float(config[name+'.sigma']),
            2*np.pi*f*EPS0*float(config[name+'.epsilon_r'])) for i, name in enumerate(('sc', 'dermis', 'fat', 'muscle'))}
    for label, expected in metadata.get('expected_output_hashes', {}).items():
        path = Path(label)
        actual_path = path if path.is_absolute() else folder/path
        actual_path, actual = _pin(actual_path, expected)
        input_hashes[str(actual_path)] = actual
    rows = _metric_rows(metrics, config, condition_id)
    helper_hashes = {str(Path(__file__).resolve()): _sha256(__file__)}
    for name in ('layered_probe_analysis.py', 'native_probe_followup.py', 'leader_spatial_diagnostics.py'):
        path = Path(__file__).resolve().parent/name
        helper_hashes[str(path)] = _sha256(path)
    provenance_code = _canonical_sha256(dict(producer_source_hashes=source_hashes, helper_hashes=helper_hashes))
    input_sha = _canonical_sha256(dict(actual_files=input_hashes,
        mesh=dict(h_xy_mm=metadata['h_xy_mm'], layer_counts=metadata['layer_counts'], z_faces_mm=metadata['z_faces_mm'])))
    sampler = LayeredPotentialSampler(grid, geometry)
    results = []
    for row in rows:
        coefficients, fundamentals = drive_coefficients(row, FREQUENCIES_HZ)
        provenance = dict(source_run_id=run_id, source_condition_id=condition_id,
            source_candidate_id=row['id'], input_sha256=input_sha, code_sha256=provenance_code,
            result_sha256=_canonical_sha256(row))
        probe = evaluate_layered_probe(grid, potentials, fields, geometry, coefficients,
            provenance=provenance, fundamental_frequencies_Hz=fundamentals, sampling=SamplingLimits())
        if probe.get('status') != 'complete' or not probe['numerical_checks']['all_passed'] or probe['counts']['complete'] != 40:
            raise PostprocessValidationError('Layer-aware native phi/E or 40-probe gate failed for ' + row['id'])
        centre_spectrum = []
        for f, c in coefficients.items():
            stencil = sampler.stencil([0., 0., 20.], geometry['gamma_S_m'][f])
            centre_field = np.einsum('cnk,n->ck', fields[f][:, stencil['indices']], stencil['weights'])
            centre_spectrum.append(c @ centre_field)
        rms = math.sqrt(float(np.sum(abs(np.asarray(centre_spectrum))**2)/2))
        if not math.isclose(rms, row['target20_total_E_RMS_V_m'], rel_tol=2e-7, abs_tol=1e-12):
            raise PostprocessValidationError('Source centre total-E RMS reconstruction failed for ' + row['id'])
        probe['source_centre_RMS_reproduction'] = dict(passed=True,
            stored_E_RMS_V_m=row['target20_total_E_RMS_V_m'], reconstructed_E_RMS_V_m=rms,
            relative_tolerance=2e-7)
        try:
            spatial = analyze_spatial_case(row, folder)
        except SpatialCacheUnavailable as error:
            spatial = dict(status='held_data_missing', reason=str(error),
                           source_metric_relative_tolerance=2e-7)
        except ValueError as error:
            spatial = dict(status='validation_failed', reason=str(error),
                           source_metric_relative_tolerance=2e-7,
                           numerical_failure_not_relaxed=True)
        results.append(dict(id=row['id'], waveform=row['waveform'],
                            conditions=row, probe_40=probe, spatial=spatial))
    # Detect concurrent changes: all files and frozen code checked before use
    # must still have the same bytes.  This helper never writes them.
    for path, expected in {**input_hashes, **source_hashes, **helper_hashes}.items():
        _pin(path, expected)
    spatial_complete = all(item['spatial'].get('status') == 'complete' for item in results)
    return dict(schema_version=1,
        status='complete' if spatial_complete else 'incomplete_spatial_diagnostics',
        source_run_id=run_id, source_condition_id=condition_id,
        waveform_count=3, completed_native_probe_waveforms=120,
        expected_native_probe_waveforms=120, waveforms=results,
        input_audit=dict(status='passed', input_sha256=input_sha,
            original_config_path=str(config_path), original_config_sha256=config_sha,
            actual_input_file_sha256=input_hashes, producer_source_sha256=source_hashes,
            postprocessor_sha256=helper_hashes, all_input_and_code_sha_unchanged_after=True,
            actual_mesh=geometry['mesh_provenance'], retained_native_baseline_reproduction=potential_grid_match),
        verification=dict(native_phi_E_all_layers_passed=True, centre_RMS_reproduction_passed=True,
            spatial_all_complete=spatial_complete,
            electrical_solver_status='preserved separately in original validation.json',
            convergence_or_physiology_inferred=False),
        resources=dict(postprocess_wall_seconds=time.monotonic()-started,
            new_PDE_count=0, output_written_by_helper=False, resource_enforcement='caller finite-run supervisor'),
        limitations=['Native phi/E is an algebraic consistency gate, not grid/contact/physiological convergence.',
            'Spatial diagnostics reuse fixed physical probes and 2074 directions; reported incompleteness is preserved.',
            '40 unloaded 5 mm probe voltages are not whole-space maxima or neural/muscle recruitment.',
            'Source original 1 Vpp, 50 ohm, peak/+jwt convention and every historical result are unchanged.'])
