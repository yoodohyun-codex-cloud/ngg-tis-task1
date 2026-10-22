"""Honest native loader for GroupedPadBasis, with exactly two source outputs.

The caller owns the execution lock and resource/deadline monitor. This module
never solves a PDE, changes exporter identity, or relaxes the frozen four-pad
loader. Only contact labels in a separate in-memory view are grouped for reuse
of electrical accounting; physical IDs and their immutable files are preserved.
"""
from __future__ import annotations

import copy
import gzip
import json
import math
from pathlib import Path
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'tis-java'
FREQUENCIES = (3000, 3030, 9000, 9090)
RECONSTRUCTION = 'half_face_flux; top contact term averaged over full cell face h^2'


def _research():
    """Called only by the authorized locked calculation, never inventory."""
    if str(SOURCE) not in sys.path:
        sys.path.insert(0, str(SOURCE))
    import numpy as np
    import selectivity_postprocess as helpers
    from selectivity_volume import evaluate_volume
    from layered_probe_analysis import evaluate_layered_probe
    return np, helpers, evaluate_volume, evaluate_layered_probe


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def contact_labels(case, config, metadata):
    """Validate physical grouping, returning raw-pad-index -> helper label.

    Labels0/1 denote the two source nodes. Labels2/3 distinguish physical return
    groups, both of which are tied to the same GND node. No current is assigned
    to an exclusive source-return pair by this bookkeeping adapter.
    """
    n = int(case['n_pads'])
    _require(n in (4, 8, 12, 16) and int(case['n_outputs']) == 2,
             'Only physical4/8/12/16 pads with exactly2 outputs registered')
    nodes = case['pad_node_ids']
    _require(isinstance(nodes, list) and len(nodes) == n and
             all(type(node) is int and node in (-1, 0, 1) for node in nodes),
             'Explicit integer physical-pad to electrical-node mapping required')
    _require(nodes.count(0) == nodes.count(1) == n//4 and nodes.count(-1) == n//2,
             'Registered family requires equal output groups and half return pads')
    _require(metadata.get('n_pads') == n and metadata.get('n_outputs') == 2 and
             metadata.get('channels') == 2 and metadata.get('pad_node_ids') == nodes and
             metadata.get('n_return_nodes') == 1 and metadata.get('return_topology') == 'common_GND',
             'Actual grouped native metadata/case topology differs')
    _require(config.get('channels') == config.get('n_outputs') == '2' and
             config.get('n_pads') == str(n) and config.get('n_return_nodes') == '1' and
             config.get('return_topology') == 'common_GND', 'Grouped config topology differs')
    _require(all(config.get(f'pad.node.{i}') == str(node) for i, node in enumerate(nodes)),
             'Grouped config pad-node mapping differs')
    pads = case['pads']
    _require(len(pads) == n and {p['pad_id'] for p in pads} == set(range(n)),
             'Unique physical pad definitions required')
    labels = [None]*n
    for pad in pads:
        physical = pad['pad_id']
        group = pad['parent_group']
        _require(type(group) is int and group in (0, 1, 2, 3),
                 'Four declared physical parent groups required')
        expected = group if group < 2 else -1
        _require(pad['node'] == nodes[physical] == expected,
                 'Physical group and electrical node disagree')
        labels[physical] = group
    _require(all(labels.count(group) == n//4 for group in range(4)),
             'Registered physical parent-group counts differ')
    return labels


def _load_basis(folder, case, deadline):
    np, h, _, _ = _research()
    folder = Path(folder).resolve()
    _require(case.get('exporter_class') == 'GroupedPadBasis', 'Explicit grouped exporter case required')
    paths = {name: h._path(folder, name) for name in
             ('BASIS_COMPLETE', 'validation.json', 'mesh-metadata.json', 'grid.csv')}
    hashes = {str(path): h._sha(path, deadline) for path in paths.values()}
    metadata = json.loads(paths['mesh-metadata.json'].read_text())
    validation = json.loads(paths['validation.json'].read_text())
    _require(metadata.get('exporter_class') == 'GroupedPadBasis' and
             metadata.get('exporter_kind') == 'grouped_native' and
             metadata.get('numerical_base_class') == 'SelectivityShapeBasis',
             'Only honest GroupedPadBasis native metadata accepted')
    _require(metadata.get('source_peak_V') == .5 and metadata.get('source_resistance_ohm') == 50 and
             metadata.get('phasor_convention') == 'peak,+jomega_t' and
             metadata.get('field_reconstruction') == RECONSTRUCTION and
             metadata.get('frequencies_Hz') == list(FREQUENCIES),
             'Grouped normalization/frequency/reconstruction contract differs')
    _require(metadata.get('radius_mm') == 25 and metadata.get('total_depth_mm') == 25.1 and
             metadata.get('tissue_boundaries_mm') == [0, .1, 5.1, 10.1, 25.1] and
             metadata.get('h_xy_mm') == case['h_xy_mm'] and
             metadata.get('sc_cells') == case['sc_cells'] and
             metadata.get('bulk_layer_counts') == list(case['bulk_counts']),
             'Grouped fixed phantom or registered mesh differs')
    config_path = Path(case['config_file']).resolve()
    hashes[str(config_path)] = h._sha(config_path, deadline)
    _require(hashes[str(config_path)] == case['config_sha256'] == metadata.get('config_sha256'),
             'Grouped native config SHA differs from registration')
    config = h._properties(config_path)
    labels = contact_labels(case, config, metadata)
    npads = case['n_pads']
    _require(validation.get('n_pads') == npads and validation.get('n_outputs') == 2 and
             validation.get('channels') == 2, 'Grouped native validation topology differs')
    gate_status = {}
    for key, limit in h.LIMITS.items():
        value = float(validation[key])
        _require(math.isfinite(value) and 0 <= value <= limit, 'Grouped numerical gate failed: '+key)
        gate_status[key] = dict(status='passed', value=value, limit=limit)
    mask_path = Path(config['mask.path']).resolve()
    _require(mask_path == Path(case['mask_file']).resolve(), 'Grouped config/case mask path differs')
    hashes[str(mask_path)] = h._sha(mask_path, deadline)
    _require(hashes[str(mask_path)] == case['mask_sha256'] == config['mask.sha256'],
             'Grouped physical contact mask SHA differs')
    opener = gzip.open if paths['grid.csv'].suffix == '.gz' else open
    with opener(paths['grid.csv'], 'rt') as stream:
        grid = np.atleast_1d(np.genfromtxt(stream, delimiter=',', names=True))
    n = len(grid)
    _require(n == validation['cells'] == metadata['cells'] and 0 < n <= 800000,
             'Grouped actual native grid dimensions differ')
    expected_areas = np.asarray(case['expected_pad_areas_m2'], float)
    _require(expected_areas.shape == (npads,) and np.isfinite(expected_areas).all() and
             np.all(expected_areas > 0), 'Positive explicit per-physical-pad area required')
    if case.get('area_mode') == 'equal_total_area_900mm2':
        _require(abs(float(expected_areas.sum())/.0009-1) <= 1e-10 and
                 all(abs(float(expected_areas[np.asarray(labels) == group].sum())/.000225-1) <= 1e-10
                     for group in range(4)), 'Equal-total-area family must retain225mm2 per electrical parent group')
    for pad, expected in enumerate(expected_areas):
        _require(abs(float(config[f'pad.{pad}.represented_area_m2'])/expected-1) <= 1e-10,
                 'Grouped config/case physical pad areas differ')
    frequencies, contact_identity, receipts = {}, None, {}
    for f in FREQUENCIES:
        h._deadline(deadline, 'grouped_load_frequency:'+str(f))
        pf = {name: h._path(folder, f'{name}-{f}.{suffix}') for name, suffix in
              (('field', 'bin'), ('potential', 'bin'), ('density', 'bin'),
               ('loss', 'bin'), ('source', 'bin'), ('contacts', 'csv'))}
        for path in pf.values():
            hashes[str(path)] = h._sha(path, deadline)
        opener = gzip.open if pf['contacts'].suffix == '.gz' else open
        with opener(pf['contacts'], 'rt') as stream:
            physical_contacts = np.atleast_1d(np.genfromtxt(stream, delimiter=',', names=True))
        pad = np.asarray(physical_contacts['pad'], float)
        area = np.asarray(physical_contacts['area_m2'], float)
        xy = np.column_stack((physical_contacts['x_mm'], physical_contacts['y_mm']))
        _require(np.isfinite(pad).all() and np.equal(pad, np.round(pad)).all() and
                 set(pad.astype(int)) == set(range(npads)) and np.isfinite(area).all() and
                 np.all(area > 0) and np.isfinite(xy).all() and np.all(np.sum(xy*xy, axis=1) < 625),
                 'Invalid raw physical grouped contact patches')
        _, face_index = np.unique(xy, axis=0, return_inverse=True)
        face_area = np.bincount(face_index, weights=area)
        _require(np.all(face_area <= (case['h_xy_mm']/1000)**2*(1+1e-10)),
                 'Grouped contact patches exceed represented native face area')
        pad = pad.astype(int)
        actual_areas = np.bincount(pad, weights=area, minlength=npads)
        area_error = float(np.max(abs(actual_areas/expected_areas-1)))
        _require(area_error <= 1e-10, 'Grouped represented physical pad area changed')
        if contact_identity is None:
            contact_identity = physical_contacts.copy()
        else:
            _require(np.array_equal(contact_identity, physical_contacts),
                     'Grouped physical contact order differs between frequencies')
        field = h._array(pf['field'], (2, n, 3), deadline)
        potential = h._array(pf['potential'], (2, n), deadline)
        density = h._array(pf['density'], (2, len(pad)), deadline)
        loss = h._array(pf['loss'], (6, 2, 2), deadline)
        source = h._array(pf['source'], (2, 2), deadline)
        _require(np.allclose(loss, loss.conj().transpose(0, 2, 1), atol=1e-12, rtol=1e-10),
                 'Grouped loss matrices must be Hermitian')
        # The complex source transfer itself is generally NOT Hermitian.
        # Real supplied power is checked against the Hermitian loss form.
        patch_nodes = np.asarray(case['pad_node_ids'])[pad]
        currents_by_node = np.array([np.sum(density[:, patch_nodes == node]*area[patch_nodes == node], axis=1)
                                     for node in (0, 1)])
        signal_error = float(np.max(abs(currents_by_node-source))/max(float(np.max(abs(source))), 1e-30))
        balance = np.sum(density*area, axis=1)
        balance_error = float(np.max(abs(balance)/np.maximum(np.sum(abs(density)*area, axis=1), 1e-30)))
        _require(signal_error <= 2e-6 and balance_error <= 2e-6,
                 'Raw grouped pad currents fail electrical-node/source balance')
        power_errors = []
        for seed in range(3):
            c = np.random.default_rng(seed).normal(size=2)+1j*np.random.default_rng(seed+17).normal(size=2)
            supplied = float(.25*np.vdot(c, source@c).real)
            dissipated = float(np.einsum('i,kij,j->', c.conj(), loss, c).real)
            relative = abs(dissipated-supplied)/max(abs(supplied), 1e-20)
            _require(relative <= 2e-7 and supplied >= -1e-14,
                     'Grouped arbitrary complex-output power conservation failed')
            power_errors.append(relative)
        contacts = physical_contacts.copy()
        contacts['pad'] = np.asarray(labels, int)[pad]
        frequencies[f] = dict(field=field, potential=potential, density=density, loss=loss,
                              source=source, contacts=contacts, physical_contacts=physical_contacts)
        receipts[str(f)] = dict(represented_physical_pad_area_m2=actual_areas.tolist(),
            expected_physical_pad_area_m2=expected_areas.tolist(), max_area_relative_error=area_error,
            raw_signal_node_current_relative_error=signal_error,
            raw_total_current_balance_relative_error=balance_error,
            arbitrary_complex_output_power_relative_errors=power_errors)
    adapter = dict(schema='grouped-contact-accounting-v1', n_pads=npads, n_outputs=2,
        physical_pad_to_electrical_node=case['pad_node_ids'],
        physical_pad_to_helper_contact_label=labels,
        helper_contact_labels={'0': 'all patches on output0', '1': 'all patches on output1',
                               '2': 'physical return parent-group2, common GND',
                               '3': 'physical return parent-group3, common GND'},
        transformation='in-memory copy of contacts.pad only; patch order, area, J, raw IDs/files and fields unchanged',
        paired_return_current_assumption=False, raw_file_metadata_identity='GroupedPadBasis',
        old_strict_loader_used=False, exporter_identity_changed=False)
    return dict(grid=grid, f=frequencies, validation=validation, metadata=metadata,
                hashes=hashes, config=config, contact_validation=receipts,
                validation_gate_status=gate_status, grouped_contact_adapter=adapter)


def process_case(folder: Path, case: dict, output: Path, deadline_monotonic: float) -> dict:
    """Compute square_3h ROI, actual native-phi probes and honest grouped maps."""
    np, h, evaluate_volume, evaluate_layered_probe = _research()
    folder, output = Path(folder).resolve(), Path(output).resolve()
    _require(output != folder and not output.is_relative_to(folder), 'Native source must not be overwritten')
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Preserve existing grouped partial/completed postprocess')
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    stages = []

    def stage(name):
        h._deadline(deadline_monotonic, name)
        stages.append(dict(stage=name, elapsed_seconds=time.monotonic()-started))
        h._json(output/'progress.json', dict(status='running', id=case['id'], stages=stages))

    try:
        stage('grouped_native_validation')
        basis = _load_basis(folder, case, deadline_monotonic)
        _require('volume_metadata' in case, 'Explicit preregistered volume metadata/gates required')
        geometry, volume_meta = h._geometry(basis, case)
        geometry['reconstruction_adapter'].update(
            actual_exporter_class='GroupedPadBasis', grouped_contact_adapter=basis['grouped_contact_adapter'])
        coefficients = h._coefficients(2, 'square_3h')
        spectra = h._spectra(basis, coefficients)
        stage('grouped_native_volume_square_3h')
        volume = evaluate_volume(spectra, basis['grid'], volume_meta,
            fundamental_frequencies_Hz=(3000, 3030), thresholds=case.get('thresholds'),
            fibonacci_count=2048, chunk_cells=256, deadline_monotonic=deadline_monotonic)
        np.savez_compressed(output/'volume.npz', **{
            **{k: v for k, v in volume['scalars'].items()
               if k in ('maxTIS', 'fixedTIS', 'RMS', 'maxTIS_direction_index')},
            **{'region_'+k+'_m3': v for k, v in volume['region_weights_m3'].items()}})
        stage('grouped_native_phi_40_probes')
        input_manifest = h._digest(basis['hashes'])
        candidate_id = case['id']+'-square_3h'
        provenance = dict(source_run_id=case.get('source_run_id', folder.parent.parent.name),
            source_condition_id=case['id'], source_candidate_id=candidate_id,
            input_sha256=input_manifest, code_sha256=h._sha(Path(__file__), deadline_monotonic),
            result_sha256=h._digest(basis['validation']))
        probes = evaluate_layered_probe(basis['grid'],
            {f: basis['f'][f]['potential'] for f in FREQUENCIES},
            {f: basis['f'][f]['field'] for f in FREQUENCIES}, geometry, coefficients,
            provenance=provenance, fundamental_frequencies_Hz=(3000, 3030))
        for row in probes['measurements']:
            row.pop('time_plot', None)
        h._json(output/'probes.json', dict(status=probes['status'], conditions=[
            dict(id=candidate_id, waveform='square_3h', probe40=probes)],
            unloaded_prediction=True, actual_instrument_R_C_bandwidth_calibration_validated=False))
        _require(probes['status'] == 'complete' and probes['numerical_checks']['all_passed'],
                 'Grouped native phi/E 40-probe numerical gate failed; preserve evidence')
        stage('grouped_electrical_accounting')
        metrics = h._electrical(basis, coefficients, geometry, deadline_monotonic)
        # Keep actual per-physical-pad current totals alongside the two output totals.
        physical_squared = np.zeros(case['n_pads'])
        physical_spectrum = []
        for f, c in coefficients.items():
            row = basis['f'][f]
            physical = row['physical_contacts']['pad'].astype(int)
            area = row['physical_contacts']['area_m2']
            patch_current_density = c@row['density']
            currents = np.array([np.sum(patch_current_density[physical == pad]*area[physical == pad])
                                 for pad in range(case['n_pads'])])
            physical_squared += abs(currents)**2/2
            physical_spectrum.append(dict(frequency_Hz=f, real_A=currents.real.tolist(),
                                          imaginary_A=currents.imag.tolist()))
        metrics['physical_pad_current_RMS_mA'] = (np.sqrt(physical_squared)*1000).tolist()
        metrics['physical_pad_current_spectrum'] = physical_spectrum
        stage('grouped_native_phi_display_maps')
        maps = h._maps(basis, coefficients, geometry, output, deadline_monotonic)
        condition = dict(id=candidate_id, waveform='square_3h', actual_fundamental_Hz=[3000, 3030],
            carrier_group=[0, 1], phase_deg=[0., 0.], source_Vpp_per_output=1.,
            n_pads=case['n_pads'], n_outputs=2, metrics=metrics, volume_metrics=volume['metrics'],
            native_volume_archive='volume.npz', probe_status=probes['status'], probe_count=40,
            modulation_definition='Legacy finite2074-direction two-fundamental envelope width; actual4-frequency RMS and phi waveforms separate',
            full_harmonic_modulation_spatially_validated=False)
        stage('grouped_input_preservation')
        for path, expected in basis['hashes'].items():
            _require(h._sha(Path(path), deadline_monotonic) == expected,
                     'Grouped native source changed during postprocessing: '+path)
        target = volume['metrics']['regions']['target']['statistics']['maxTIS']
        surface = volume['metrics']['regions']['surface_0_5']['statistics']['maxTIS']
        artifacts = {str(path.relative_to(output)): dict(SHA256=h._sha(path, deadline_monotonic), bytes=path.stat().st_size)
                     for path in output.iterdir() if path.is_file() and path.name not in ('progress.json', 'failure.json')}
        result = dict(schema_version=1, status='complete', id=case['id'],
            postprocessor_kind='honest_grouped_native_v1', source_normalization=h.NORMALIZATION,
            validation=basis['validation'], validation_gate_status=basis['validation_gate_status'],
            mesh_metadata=basis['metadata'], geometry_adapter=geometry['reconstruction_adapter'],
            grouped_contact_adapter=basis['grouped_contact_adapter'], contact_area_validation=basis['contact_validation'],
            input_sha256=basis['hashes'], input_manifest_sha256=input_manifest,
            postprocessor_sha256=h._sha(Path(__file__), deadline_monotonic),
            conditions=[condition], maps=[dict(actual_carrier_Hz=None, directory='.', **maps)],
            selection_metrics=dict(roi_p10_TIS_V_m=target['p10'], roi_mean_TIS_V_m=target['mean'],
                target_superficial_p95_ratio=target['mean']/surface['p95'] if surface['p95'] else None,
                surface_J_RMS_max_A_m2=metrics['surface_J_RMS_max_A_m2'], source_power_W=metrics['source_power_W']),
            artifacts=dict(probes_json='probes.json', files=artifacts), stages=stages,
            elapsed_seconds=time.monotonic()-started, new_PDE=0,
            numerical_conservation_passed=True, mesh_convergence_validated=False,
            experimental_validation=False, instrument_loading_validated=False,
            limitations=['All carriers share both physical return groups at common GND.',
                'Contact-patch normal Jmax/J95 are not whole-skin-volume vector J.',
                'Physical-pad count increases while independent outputs remain2.',
                'ROI TIS metric uses fundamental carriers; full waveform reconstruction includes harmonics.',
                'Native algebraic agreement is not mesh convergence or physiological/safety validation.'])
        h._json(output/'summary.json', result)
        h._json(output/'progress.json', dict(status='complete', id=case['id'], stages=stages))
        return result
    except BaseException as error:
        h._json(output/'failure.json', dict(status='failed_preserved', id=case.get('id'),
            error_type=type(error).__name__, error=str(error), stages=stages,
            partial_artifacts_preserved=True, automatic_retry=False,
            elapsed_seconds=time.monotonic()-started))
        raise
