"""Generic read-only adapter for explicitly registered native-potential bases.

It reads original explorer or independently meshed validation exports, validates
their pinned receipt/manifest/config/source/output hashes and supplies the pure
layered probe core.  It never starts Java/PDE, regenerates a cache, edits a
producer, or writes an output/GUI pointer.  A registry owns incremental versions
and immutable output publication; this adapter does not hard-code result IDs.
"""
from pathlib import Path
import hashlib
import json
import math
import time

import numpy as np

from layered_probe_analysis import (DEFAULT_LAYERS, FIELD_RECONSTRUCTION,
    LayeredPotentialSampler, ProbeDataMissing, SamplingLimits,
    evaluate_layered_probe, probe_layout)


EPS0 = 8.8541878128e-12  # Pinned TisSweep.java constant; not a fitted material.
MAX_CELLS = 800000
MAX_BASIS_SECONDS = 600
WAVES = {'sine': (1., 0.), 'square_3h': (3/(2*math.sqrt(2)), 1/(2*math.sqrt(2))),
         'triangle_3h': (.9, -.1)}


class NativeIntegrityError(ValueError):
    """Pinned data/receipts fail integrity or a preserved numerical gate."""


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _path(value, repo):
    path = Path(value)
    path = (path if path.is_absolute() else repo/path).resolve()
    if not path.is_relative_to(repo):
        raise NativeIntegrityError('Registered native input leaves repository: ' + str(value))
    if not path.is_file():
        raise ProbeDataMissing('Registered native input is absent: ' + str(path.relative_to(repo)))
    return path


def _pinned_file(path, expected, repo):
    target = _path(path, repo)
    if not isinstance(expected, str) or len(expected) != 64:
        raise NativeIntegrityError('Explicit SHA-256 required for registered native input')
    if _hash(target) != expected:
        raise NativeIntegrityError('Registered native input hash changed: ' + str(target.relative_to(repo)))
    return target


def _json(path):
    return json.loads(Path(path).read_text(), parse_constant=lambda x: (_ for _ in ()).throw(
        NativeIntegrityError('Nonfinite JSON: ' + x)))


def _properties(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if '=' not in line or line.lstrip().startswith(('#', '!')):
            continue
        key, value = line.split('=', 1)
        if key.strip() in result:
            raise NativeIntegrityError('Duplicate source configuration property')
        result[key.strip()] = value.strip()
    return result


def drive_coefficients(row, available_frequencies_Hz, amplitude=1.):
    """Actual wave/phase spectrum, including coincident-frequency coherent sums.

    Inputs are the source row, not a GUI scalar or an assumed probe waveform.
    The repository's sine convention is -j; harmonic phase is h*phase.
    """
    channels = row.get('output_channels')
    if not isinstance(channels, int) or channels not in (1, 2, 3, 4):
        raise ProbeDataMissing('Actual output count is missing')
    if row.get('waveform') not in WAVES:
        raise ProbeDataMissing('Waveform is unsupported by this registered spectrum contract')
    raw_groups = np.asarray(row.get('carrier_group'))
    if raw_groups.shape != (channels,) or not np.issubdtype(raw_groups.dtype, np.number) or not np.isfinite(raw_groups).all():
        raise NativeIntegrityError('Actual carrier groups must be finite integer assignments')
    groups = np.asarray(raw_groups, int)
    if not np.array_equal(raw_groups, groups):
        raise NativeIntegrityError('Fractional carrier assignments may not be rounded')
    phases = np.asarray(row.get('phase_deg'), float)
    if groups.shape != (channels,) or phases.shape != (channels,) or not np.isfinite(phases).all():
        raise NativeIntegrityError('Actual output group/phase dimensions are invalid')
    if np.any((groups < 0) | (groups > 1)) or channels == 1 and groups[0] != 0:
        raise NativeIntegrityError('Invalid actual carrier assignment')
    carrier, beat = row.get('carrier_Hz'), row.get('beat_Hz')
    if carrier is None or beat is None:
        raise ProbeDataMissing('Explicit source carrier and beat are required')
    if (not math.isfinite(carrier) or not math.isfinite(beat) or carrier <= 0 or beat < 0 or
            carrier != int(carrier) or beat != int(beat)):
        raise ProbeDataMissing('Exact integer-Hz actual carrier/beat are required')
    scale = float(amplitude)
    if not math.isfinite(scale) or scale < 0:
        raise NativeIntegrityError('Source amplitude scale must be finite and nonnegative')
    result, fundamentals = {}, set()
    for channel, (group, phase_deg) in enumerate(zip(groups, phases)):
        f0 = int(carrier + group*beat)
        fundamentals.add(f0)
        for harmonic, coefficient in zip((1, 3), WAVES[row['waveform']]):
            if coefficient == 0:
                continue
            f = harmonic*f0
            values = result.setdefault(f, np.zeros(channels, complex))
            values[channel] += -1j*scale*coefficient*np.exp(1j*harmonic*np.deg2rad(phase_deg))
    if set(result) - set(available_frequencies_Hz):
        raise ProbeDataMissing('Native basis omits an actually driven carrier or harmonic')
    return result, sorted(fundamentals)


def geometry_from_registered_grid(grid, config, entry):
    """Derive only pinned explorer mesh rules; validation needs explicit faces.

    The original Mesh rule uses SC=2 and ceil(thickness/(0.6*h)) bulk cells.
    The validation rule never infers z from h: registered SC2/4/8, fixed bulk
    counts and every actual z face must agree with its native grid.
    """
    kind = entry.get('exporter_kind')
    metadata = entry.get('mesh_metadata', {})
    h = float(config['h_mm'])
    if not math.isfinite(h) or h <= 0:
        raise NativeIntegrityError('Invalid physical mesh spacing')
    if metadata.get('h_xy_mm') is None or not math.isclose(metadata['h_xy_mm'], h, rel_tol=0, abs_tol=1e-12):
        raise ProbeDataMissing('Registered actual XY mesh metadata is missing or mismatched')
    thicknesses = [.1, 5., 5., 15.]
    if kind == 'explore_native':
        counts = [2] + [math.ceil((thickness/1000)/((h/1000)*.6)) for thickness in thicknesses[1:]]
        if metadata.get('layer_counts') != counts:
            raise ProbeDataMissing('Registered layer counts do not reproduce pinned original Mesh rule')
    elif kind == 'validation_native':
        counts = metadata.get('layer_counts')
        if not counts or len(counts) != 4 or counts[0] not in (2, 4, 8) or counts[1:] != [14, 14, 40]:
            raise ProbeDataMissing('Independent validation mesh requires actual SC2/4/8 and bulk14/14/40 metadata')
        if 'z_faces_mm' not in metadata:
            raise ProbeDataMissing('Validation native export requires explicit actual z faces; h-based inference prohibited')
    else:
        raise ProbeDataMissing('Explicit supported native exporter kind required')
    faces, cursor = [0.], 0.
    for thickness, count in zip(thicknesses, counts):
        for _ in range(count):
            cursor += thickness/count
            faces.append(cursor)
    if 'z_faces_mm' in metadata:
        declared = np.asarray(metadata['z_faces_mm'], float)
        if declared.shape != (sum(counts)+1,) or not np.allclose(declared, faces, rtol=0, atol=1e-9):
            raise NativeIntegrityError('Explicit actual faces disagree with declared layer counts/planes')
        faces = declared.tolist()
    geometry = dict(coordinate_system=dict(unit='mm', surface_z_mm=0., depth_axis='+z'),
        radius_mm=25., layers=[dict(layer) for layer in DEFAULT_LAYERS], z_faces_mm=faces,
        field_reconstruction=FIELD_RECONSTRUCTION,
        basis_normalization=dict(source_peak_V=.5, source_Vpp=1., source_resistance_ohm=50.,
                                 phasor_exponent='+jomega_t'))
    sampler = LayeredPotentialSampler(grid, geometry)
    nx = round(50/h)
    xy = -.025 + (np.arange(nx)+.5)*(h/1000)
    if not math.isclose(nx*h, 50, abs_tol=1e-9, rel_tol=0):
        raise NativeIntegrityError('Actual XY spacing does not tile source diameter')
    if any(len(axis) != nx or not np.allclose(axis, xy*1000, atol=1e-9, rtol=0) for axis in sampler.axes[:2]):
        raise NativeIntegrityError('Native XY centres differ from pinned original mesh')
    expected_mask = xy[:, None]**2 + xy[None, :]**2 < .025**2
    if sampler.lookup.shape[0] != sum(counts) or not np.all((sampler.lookup >= 0) == expected_mask[None, :, :]):
        raise NativeIntegrityError('Native cylindrical mask or actual z cell count differs')
    if 'volume_m3' not in (grid.dtype.names or ()):
        raise ProbeDataMissing('Native finite-volume cell volumes are required')
    expected_volumes = (h/1000)**2 * np.diff(faces)[sampler.iz]/1000
    if not np.allclose(grid['volume_m3'], expected_volumes, rtol=2e-10, atol=1e-18):
        raise NativeIntegrityError('Native cell volumes differ from supplied actual grid')
    geometry['mesh_provenance'] = dict(exporter_kind=kind, layer_counts=counts,
        h_xy_mm=h, cells=len(grid), z_faces_origin='explicit registered actual validation metadata' if kind == 'validation_native'
        else 'pinned TisSweep.Mesh SC=2/ceil(thickness/(0.6*h)) rule; all native centres/mask/volumes checked')
    return geometry


class NativeBasisAdapter:
    """Audit and memory-map one native basis, reusable for new wave/phase rows."""
    def __init__(self, registered_basis, repo_root):
        try:
            self._initialize(registered_basis, repo_root)
        except (ProbeDataMissing, NativeIntegrityError):
            raise
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise NativeIntegrityError('Malformed registered native input/receipt: ' + str(error)) from error

    def _initialize(self, registered_basis, repo_root):
        started = time.monotonic()
        self.entry, self.repo = dict(registered_basis), Path(repo_root).resolve()
        e = self.entry
        for key in ('source_run_id', 'source_condition_id', 'actual_native_path', 'config_path',
                    'config_sha256', 'receipt_path', 'receipt_sha256', 'receipt_case_id',
                    'native_manifest_path', 'native_manifest_sha256', 'old_probe_receipt_path',
                    'old_probe_receipt_sha256', 'source_hashes'):
            if key not in e:
                raise ProbeDataMissing('Registered native basis lacks ' + key)
        config_path = _pinned_file(e['config_path'], e['config_sha256'], self.repo)
        self.config = _properties(config_path)
        sources = e['source_hashes']
        if not sources or not any(Path(p).name == 'TisSweep.java' for p in sources):
            raise ProbeDataMissing('Pinned mesh/material source hashes are required')
        for path, expected in sources.items():
            actual = _pinned_file(path, expected, self.repo)
            if actual.name == 'TisSweep.java' and 'EPS0=8.8541878128e-12' not in actual.read_text():
                raise NativeIntegrityError('Original permittivity constant differs from registered adapter contract')
        receipt_path = _pinned_file(e['receipt_path'], e['receipt_sha256'], self.repo)
        manifest_path = _pinned_file(e['native_manifest_path'], e['native_manifest_sha256'], self.repo)
        old_path = _pinned_file(e['old_probe_receipt_path'], e['old_probe_receipt_sha256'], self.repo)
        receipt, manifest, old_receipt = _json(receipt_path), _json(manifest_path), _json(old_path)
        cases = receipt.get('cases', [receipt])
        case = next((case for case in cases if case.get('id') == e['receipt_case_id']), None)
        if case is None or case.get('status') != 'complete' or receipt.get('status') != 'complete':
            raise NativeIntegrityError('Native export receipt is absent, incomplete or failed')
        plan = next((item for item in manifest.get('plan', []) if item.get('id') == e['receipt_case_id']), None)
        if not plan or plan.get('config_sha256') != e['config_sha256'] or case.get('config_sha256') != e['config_sha256']:
            raise NativeIntegrityError('Manifest/receipt configuration is not the registered native basis')
        if manifest.get('output_only_source_check') is not True:
            raise NativeIntegrityError('Output-only source preservation was not validated')
        reference = manifest.get('potential_reference', {})
        if any(reference.get(key) != value for key, value in dict(common_ideal_return_ground_V=0,
                source_peak_V=.5, source_Vpp=1, source_resistance_ohm=50).items()):
            raise NativeIntegrityError('Native potential source normalization/gauge differs')
        if 'positive exponent' not in reference.get('phasor_convention', '') or 'peak' not in reference.get('phasor_convention', ''):
            raise NativeIntegrityError('Native peak/+jwt convention is not declared')
        prior = old_receipt
        if 'prior_phi_e_json_path' in e:
            for key in e['prior_phi_e_json_path']:
                prior = prior[key]
        elif e.get('old_probe_case_key'):
            prior = old_receipt['comparisons'][0]['cases'][e['old_probe_case_key']]['verification']['phi_E_consistency']
        else:
            raise ProbeDataMissing('Explicit prior phi/E receipt JSON path is required')
        if prior.get('passed') is not True:
            raise NativeIntegrityError('Preserved prior native phi/E gate did not pass')
        relative = Path(e['actual_native_path'])
        folder = (relative if relative.is_absolute() else self.repo/relative).resolve()
        if not folder.is_relative_to(self.repo) or not folder.is_dir():
            raise ProbeDataMissing('Registered full native basis directory is missing')
        if folder != Path(case['basis_dir']).resolve():
            raise NativeIntegrityError('Receipt refers to a different native basis directory')
        self.folder = folder
        reproduction = case.get('reproduction', {})
        if reproduction.get('status') != 'exact':
            raise NativeIntegrityError('Original output SHA reproduction is not exact')
        self.frequencies = [int(f) for f in self.config['frequencies'].split(',')]
        if len(set(self.frequencies)) != len(self.frequencies) or any(f <= 0 for f in self.frequencies):
            raise NativeIntegrityError('Invalid explicit native basis frequencies')
        if case.get('frequencies_Hz') != self.frequencies or plan.get('frequencies_Hz') != self.frequencies:
            raise NativeIntegrityError('Config/receipt/manifest native frequencies differ')
        self.channels = int(self.config['channels'])
        original_names = {'grid.csv', 'validation.json', 'BASIS_COMPLETE'} | {
            f'{kind}-{f}.{suffix}' for f in self.frequencies for kind, suffix in
            [('field', 'bin'), ('density', 'bin'), ('source', 'bin'), ('loss', 'bin'), ('contacts', 'csv')]}
        expected = reproduction.get('files', {})
        if set(expected) != original_names:
            raise NativeIntegrityError('Native receipt does not cover every original 23/13-style output')
        self.checked_files = {}
        for name, expected_sha in expected.items():
            path = _pinned_file(folder/name, expected_sha, self.repo)
            self.checked_files[str(path.relative_to(self.repo))] = expected_sha
        validation = _json(folder/'validation.json')
        for key, limit in dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6).items():
            value = float(validation[key])
            if not math.isfinite(value) or value < 0 or value > limit:
                raise NativeIntegrityError('Preserved native solver gate failed: ' + key)
        cells = validation.get('cells')
        if not isinstance(cells, int) or not 0 < cells <= MAX_CELLS or validation.get('channels') != self.channels:
            raise NativeIntegrityError('Native cells/channels exceed the registered dimensions')
        self.grid = np.genfromtxt(folder/'grid.csv', delimiter=',', names=True)
        if len(self.grid) != cells:
            raise NativeIntegrityError('Native grid row count differs from receipt')
        self.geometry = geometry_from_registered_grid(self.grid, self.config, e)
        self.geometry['gamma_S_m'] = {}
        self.potentials, self.fields = {}, {}
        for f in self.frequencies:
            schema = reproduction.get('potential', {}).get(str(f), {})
            if (schema.get('dtype') != '<c16' or schema.get('shape') != [self.channels, cells] or
                    schema.get('finite') is not True):
                raise NativeIntegrityError('Native complex potential schema is missing or mismatched')
            path = _pinned_file(folder/f'potential-{f}.bin', schema.get('sha256'), self.repo)
            self.checked_files[str(path.relative_to(self.repo))] = schema['sha256']
            if path.stat().st_size != self.channels*cells*16 or (folder/f'field-{f}.bin').stat().st_size != self.channels*cells*3*16:
                raise NativeIntegrityError('Native potential/E binary shape mismatch')
            self.potentials[f] = np.memmap(path, mode='r', dtype='<c16', shape=(self.channels, cells))
            self.fields[f] = np.memmap(folder/f'field-{f}.bin', mode='r', dtype='<c16', shape=(self.channels, cells, 3))
            self.geometry['gamma_S_m'][f] = {layer['id']: complex(float(self.config[layer['name']+'.sigma']),
                2*np.pi*f*EPS0*float(self.config[layer['name']+'.epsilon_r'])) for layer in DEFAULT_LAYERS}
        self.audit = dict(status='passed', config_sha256=e['config_sha256'],
            original_output_SHA_count=len(expected), native_potential_SHA_count=len(self.frequencies),
            checked_files=self.checked_files, original_solver_gates_preserved=True,
            prior_phi_E_pass_scope='preserved prior receipt only; new layer/40-point gate is separately required',
            source_hashes=dict(sources), receipt_sha256=e['receipt_sha256'],
            native_manifest_sha256=e['native_manifest_sha256'], prior_phi_E_receipt_sha256=e['old_probe_receipt_sha256'],
            mesh_provenance=self.geometry['mesh_provenance'], new_PDE_count=0,
            loading_noise_physiology_validated=False, preparation_wall_seconds=time.monotonic()-started)
        if self.audit['preparation_wall_seconds'] > MAX_BASIS_SECONDS:
            raise ProbeDataMissing('Native input audit exceeded registered 600-second postprocessing cap')

    def evaluate(self, record, amplitude=1., sampling=SamplingLimits()):
        """A changed input never inherits an old version's native result."""
        for record_key, entry_key in [('source_run_id', 'source_run_id'), ('condition_id', 'source_condition_id')]:
            if record.get(record_key) != self.entry.get(entry_key):
                raise ProbeDataMissing('Native basis is registered for a different source run/condition')
        if record.get('config_sha256') != self.entry['config_sha256']:
            raise ProbeDataMissing('Changed source config hash has no registered full native basis version')
        native_sources = {Path(path).name: value for path, value in self.entry['source_hashes'].items()}
        candidate_sources = {Path(path).name: value for path, value in record.get('code_hashes', {}).items()}
        required_sources = ('TisSweep.java', 'ExploreBasis.java') + (
            ('ValidationBasis.java',) if self.entry['exporter_kind'] == 'validation_native' else ())
        for name in required_sources:
            if name not in candidate_sources or name not in native_sources:
                raise ProbeDataMissing('Candidate/native solver identity is unavailable: ' + name)
            if candidate_sources[name] != native_sources[name]:
                raise ProbeDataMissing('Changed source solver hash has no registered native basis version: ' + name)
        row = record['conditions']
        if row.get('output_channels') != self.channels:
            raise ProbeDataMissing('Candidate/native source output count differs')
        for key, expected_value in dict(h_mm=float(self.config['h_mm']),
                pad_size_mm=float(self.config['size_mm']), pad_count=2*self.channels).items():
            if key in row and not math.isclose(row[key], expected_value, rel_tol=0, abs_tol=1e-10):
                raise NativeIntegrityError('Candidate physical condition differs from pinned native config: ' + key)
        if any(f'pad.{i}.{axis}_mm' not in self.config for i in range(2*self.channels) for axis in ('x', 'y')):
            raise ProbeDataMissing('Original native electrode patch coordinates are unavailable')
        pads = [[float(self.config[f'pad.{i}.x_mm']), float(self.config[f'pad.{i}.y_mm'])]
                for i in range(2*self.channels)]
        if 'xy_mm' in row and not np.allclose(row['xy_mm'], pads, rtol=0, atol=1e-10):
            raise NativeIntegrityError('Candidate electrode positions differ from pinned native config')
        coefficients, fundamentals = drive_coefficients(row, self.frequencies, amplitude)
        if WAVES[row['waveform']][1] != 0 and set(fundamentals) & {3*f for f in fundamentals}:
            raise ProbeDataMissing('Overlapping fundamental/harmonic frequencies need separately tagged fundamental envelope inputs')
        # Independently check the exact source candidate centre metric before use.
        sampler = LayeredPotentialSampler(self.grid, self.geometry)
        spectrum = []
        for f, c in coefficients.items():
            stencil = sampler.stencil([0., 0., 20.], self.geometry['gamma_S_m'][f])
            ef = np.einsum('cnk,n->ck', self.fields[f][:, stencil['indices']], stencil['weights'])
            spectrum.append(c @ ef)
        centre_rms = math.sqrt(float(np.sum(abs(np.asarray(spectrum))**2)/2))
        expected = record.get('original_metrics_SI', {}).get('target20_total_E_RMS_V_m')
        if expected is None:
            raise ProbeDataMissing('Source candidate centre total-E RMS is unavailable')
        if not math.isclose(centre_rms, expected*amplitude, rel_tol=2e-7, abs_tol=1e-12):
            raise NativeIntegrityError('Native actual carrier/harmonic/phase centre total-E RMS does not reproduce source result')
        provenance = dict(source_run_id=record['source_run_id'], source_condition_id=record['condition_id'],
            source_candidate_id=record['candidate_id'], **{key: record[key] for key in
            ('input_sha256', 'code_sha256', 'result_sha256')}, source_version_key=record.get('source_version_key'),
            native_config_sha256=self.entry['config_sha256'], native_receipt_sha256=self.entry['receipt_sha256'])
        result = evaluate_layered_probe(self.grid, self.potentials, self.fields, self.geometry, coefficients,
            provenance=provenance, fundamental_frequencies_Hz=fundamentals, sampling=sampling)
        result['native_input_audit'] = self.audit
        result['source_centre_RMS_reproduction'] = dict(passed=True, original_E_RMS_V_m=expected,
            reconstructed_E_RMS_V_m=centre_rms, source_amplitude_scale=amplitude,
            relative_tolerance=2e-7, not_physiological_matching=True)
        result['native_adapter_sha256'] = _hash(__file__)
        result['native_physical_conditions'] = dict(pads_xy_mm=pads,
            pad_size_mm=float(self.config['size_mm']), output_channels=self.channels,
            source_resistance_ohm=50, source_amplitude_scale=float(amplitude),
            basis_source_peak_V=.5, boundary_z_ohm_m2={str(f): {
                'real': float(self.config[f'z.{f}.re']), 'imaginary': float(self.config[f'z.{f}.im'])}
                for f in self.frequencies if f'z.{f}.re' in self.config},
            material_config={key: float(value) for key, value in self.config.items()
                             if key.endswith(('.sigma', '.epsilon_r'))})
        return result


def evaluate_candidate_native(record, registered_basis, repo_root, *, adapter=None,
                              amplitude=1., sampling=SamplingLimits()):
    """Registry convenience API; preserve all 40 rows even when data are held."""
    try:
        adapter = adapter or NativeBasisAdapter(registered_basis, repo_root)
        return adapter.evaluate(record, amplitude=amplitude, sampling=sampling)
    except (ProbeDataMissing, NativeIntegrityError) as error:
        status = 'held_data_missing' if isinstance(error, ProbeDataMissing) else 'validation_failed'
        measurements = [dict(row, status=status, reason=str(error)) for row in probe_layout()]
        return dict(schema_version=1, status=status, reason=str(error), expected_waveform_count=40,
            counts={'complete': 0, status: 40}, measurements=measurements,
            provenance=dict(source_run_id=record.get('source_run_id'),
                source_condition_id=record.get('condition_id'), source_candidate_id=record.get('candidate_id'),
                **{key: record.get(key) for key in ('input_sha256', 'code_sha256', 'result_sha256')}),
            numerical_checks={'all_passed': False}, new_PDE_executed=False,
            previous_result_never_relabelled_as_changed_source=True)
