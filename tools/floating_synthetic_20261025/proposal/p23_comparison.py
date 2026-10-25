"""SOURCE-ONLY proposal: exactly two hypothetical floating P23 carrier RHS.

No scientific imports, input reads, array work, or numerical admission occur on
import. Every scientific operation is below build and explicit root admission.
Common P23/B0 stay immutable aliases. The raw-Q frame returns JSON identities
and exits before GC and the one full angular-metric evaluation.
"""
from __future__ import annotations
import copy
import gc
import importlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

SOURCE = Path('/dev/shm/task1-floating-P23-comparison-20261025/source')
DEFAULT_RUN = Path('/dev/shm/task1-floating-P23-comparison-20261025-run')
MODES = ('same_source_voltage', 'same_sum_output_RMS_current_bookkeeping',
         'same_source_real_power', 'joint_eight_surface_contact_burden_caps')
LEGACY_ELECTRICAL = ('source_Vpp_each', 'source_current_RMS_by_output_A',
    'sum_output_current_RMS_A_bookkeeping', 'source_power_W', 'layers_power_W',
    'SC_power_W', 'skin_power_W', 'contact_power_W', 'source_resistor_power_W',
    'contact_normal_J_RMS_max_A_m2', 'contact_normal_J_RMS_P95_A_m2',
    'contact_voltage_RMS_max_V')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check(guard, deadline):
    require(callable(guard), 'Continuous root resource guard required')
    guard()
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Hypothetical P23 comparison deadline exceeded')


def _inputs():
    # A root imports this proposal from the explicitly selected canonical folder.
    # A preloaded same-name module from another source tree is rejected.
    location = importlib.util.find_spec('p23_inputs')
    require(location is not None and Path(location.origin) == SOURCE / 'p23_inputs.py', 'Canonical input-contract source before import')
    module = importlib.import_module('p23_inputs')
    require(Path(module.__spec__.origin) == SOURCE / 'p23_inputs.py', 'Canonical input-contract module')
    return module


def required_inputs(admission):
    return _inputs().required_inputs(admission)


def make_spec(admission):
    context = _inputs().make_spec(admission)
    return dict(schema='task1-hypothetical-floating-P23-comparison-spec-v1',
        root_admission=copy.deepcopy(admission), inputs=context,
        input_sha256=context['input_sha256'], expected_new_driven_RHS=2,
        expected_new_metric_evaluations=1, immutable_common_control_aliases=2,
        expected_completed_conditions=3, new_eigen_solves=0,
        physical_pairs=[[0, 2], [1, 3]], frequency_output_assignment=[[2000, 0], [2010, 1]],
        source_voltage='1Vpp high-Z=.5Vpeak before one TOTAL differential50ohm/output',
        inactive_output='ideal0V DIFFERENTIAL through its own floating50ohm; no earth branch',
        source_pad_frequency_assignment_preserved=True, actual_wiring_claimed=False,
        memory_plan='One raw frame owns Q/profiles and writes each carrier separately; return JSON only, end frame, GC, then load saved E for one metrics evaluation. No Q/profiles/solver objects cross boundary.',
        forecast=dict(child_RSS_bytes=800000000, new_output_bytes=200000000,
                      forecast_output_range_bytes=[150000000, 200000000],
                      total_ALL_RSS_plus_ALL_owned_task1_tmpfs_cap_bytes=8000000000,
                      CPU=4, physical_evaluation_cells=793860, max_cells=800000),
        normalization_modes=list(MODES),
        min4='minimum(target AMmean ratio, target AMP10 ratio, target/surface mean ratio gain, target/off-target mean ratio gain); missing/zero reference means unavailable',
        holds=dict(provisional_2074_direction_lower_bound=True,
            original_5percent_and_XY_contact_burden_failures_preserved=True,
            SC_XY_bulk_edge_contact_uncertainty=True, full_numerical_convergence=False,
            material_contact_hardware_or_experiment_validated=False,
            physiological_activation_or_safety_claim=False, candidate_adopted=False),
        candidate_adopted=False, Windows_saved_verified=False)


def metadata_only(value):
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is dict:
        return all(type(k) is str and metadata_only(v) for k, v in value.items())
    if type(value) in (tuple, list):
        return all(metadata_only(v) for v in value)
    return False


def separated_stages(raw_stage, metric_stage, collector=gc.collect):
    artifacts = raw_stage()
    require(metadata_only(artifacts), 'BLOCKED: raw stage leaked arrays/Q/profile/solver into metrics')
    collector()
    return metric_stage(artifacts)


def new_json(path, value):
    require(metadata_only(value), 'JSON metadata must not contain numerical objects')
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, allow_nan=False,
            separators=(',', ':')) + '\n').encode())


def _dependencies(context):
    pins = context['input_sha256']
    modules = {}
    for name in ('frozen_floating_cem', 'frozen_design_screen', 'frozen_screen_metrics',
                 'frozen_allocation_electrical', 'p23_adapter'):
        path = SOURCE / (name + '.py')
        require(_inputs().digest(path) == pins[str(path)], 'Frozen source immediately before import')
        location = importlib.util.find_spec(name)
        require(location is not None and Path(location.origin) == path, 'Canonical scientific source before import')
        module = importlib.import_module(name)
        require(Path(module.__spec__.origin) == path, 'Reject same-name module from another source tree')
        modules[name] = module
    for name in ('frozen_coarse_cem', 'frozen_layer_dtn_backend', 'frozen_fourier_v1', 'provisional_field'):
        module = sys.modules[name]
        require(Path(module.__spec__.origin) == SOURCE / (name + '.py'), 'Canonical transitive scientific source')
    return modules


def _load(np, descriptor, keys, context, guard, deadline):
    check(guard, deadline)
    p = Path(descriptor['path'])
    expected = context['input_sha256'].get(str(p), descriptor['SHA256'])
    require(expected == descriptor['SHA256'] and p.is_file() and not p.is_symlink()
            and p == p.resolve() and p.stat().st_size == descriptor['bytes'] <= 80 * 1024**2
            and _inputs().digest(p) == expected, 'Authenticated full saved raw archive before decode')
    with np.load(p, allow_pickle=False) as saved:
        require(set(keys).issubset(saved.files), 'Required saved raw ABI; no implicit recomputation')
        result = {k: np.array(saved[k], copy=True) for k in keys}
    require(all(bool(np.isfinite(v).all()) for v in result.values()), 'Finite saved raw values')
    return result


def _authenticate_alias_files(context, guard, deadline):
    for key in ('common_P23', 'common_B0'):
        control = context[key]
        for descriptor in [control['scalar']] + list(control['raw_by_frequency'].values()):
            check(guard, deadline)
            require(_inputs().digest(descriptor['path']) == descriptor['SHA256'],
                    'Unchanged complete cached common-return control bytes')


def _raw_stage(np, context, modules, out, guard, deadline):
    """ONLY this frame owns cached Q and frequency-specific analytic profiles."""
    from scipy.sparse.linalg import LinearOperator, gmres
    science = modules['frozen_design_screen']
    floating = modules['frozen_floating_cem']
    adapter = modules['p23_adapter']
    require(science.NXY == 7860 and science.H == 0.0005 and
            tuple(science.THICKNESS) == (0.0001, 0.005, 0.005, 0.015), 'Same D50 physical discretization')
    phase, manifest = science.base._phase1_metadata()
    Q, cacheproof = science.base._load_cache(np, manifest, guard, deadline)
    path = science.base.PHASE1 / 'arrays.npz'
    require(_inputs().digest(path) == context['input_sha256'][str(path)], 'Frozen original graph/eigen archive')
    with np.load(path, allow_pickle=False) as saved:
        eigen = np.array(saved['eigenvalues_per_m2'], copy=True)
        xy = np.array(saved['XY_m'], copy=True)
        ij = np.array(saved['ij'], copy=True)
    require(eigen.shape == (7860,) and xy.shape == ij.shape == (7860, 2), 'Same frozen node-order ABI')
    import hashlib
    require(hashlib.sha256(xy.astype('<f8', copy=False).tobytes()).hexdigest() == phase['graph']['XY_float64_le_SHA256']
            and hashlib.sha256(ij.astype('<i4', copy=False).tobytes()).hexdigest() == phase['graph']['ij_int32_le_SHA256'],
            'Same Q/XY/contact ordering')
    _, _, zlist = science.base.kernel.f.make_grid(0.5, 8, [19, 18, 56])
    zs = np.asarray(zlist, float)
    layers = np.repeat(np.arange(4), science.COUNTS)
    candidate = context['physical_candidate']
    pads, cells, areas = science._mask(np, candidate, ij)
    directory = out / 'rhs'
    directory.mkdir()
    raw, proofs = {}, {}
    for frequency, output in ((2000, 0), (2010, 1)):
        check(guard, deadline)
        catalog = context['catalog']
        gamma = [complex(v['real'], v['imaginary']) for v in catalog['gamma_by_frequency'][str(frequency)]]
        z = catalog['z_by_frequency'][str(frequency)]
        zA = complex(z['real'], z['imaginary'])
        profile = science._profiles(np, Q, eigen, gamma, zs, guard, deadline)
        solution = adapter.solve(np, Q, profile, pads, cells, areas, zA, output,
            guard, deadline, floating_solver=floating.solve,
            transform=science.base._real_complex_transform, gmres=gmres,
            linear_operator=LinearOperator)
        proof = solution['proof']
        proof.update(candidate_id=context['floating_candidate_id'], physical_mask_candidate_id=candidate['candidate_id'],
            frequency_Hz=frequency, original_mask_SHA256=candidate['mask_sha256'],
            full_grid_ROI_SHA256=context['common_grid_ROI']['SHA256'],
            provisional_field=modules['frozen_design_screen'].provisional_field.provenance())
        stem = context['floating_candidate_id'] + '-' + str(frequency)
        proofpath = directory / (stem + '-solve-proof.json')
        new_json(proofpath, proof)
        science.archive(np, directory / (stem + '-surface-state.npz'),
            phi_surface_peak_V=solution['phi_surface'], metal_peak_V=solution['metal'],
            source_current_peak_A=solution['source_current'], modal_surface_coeff=solution['coeff'])
        require(proof['passed'] is True, 'Floating source physical gate failed; preserved iterate; no relaxed criterion')
        # Explicitly unchanged provisional XY field reconstruction and analytic Jz.
        phi, E, interface = science._fields(np, Q, profile, solution, ij, layers, guard, deadline)
        qpad = np.asarray([complex(v['real'], v['imaginary']) for v in
            proof['all_pad_outward_tissue_to_metal_current_peak_A']])
        artifact = science.archive(np, directory / (stem + '-raw.npz'),
            phi_peak_V=phi, E_peak_V_m=E, interface_downward_J_peak_A_m2=interface,
            modal_surface_coeff=solution['coeff'], phi_surface_peak_V=solution['phi_surface'],
            metal_peak_V=solution['metal'], source_current_peak_A=solution['source_current'],
            source_current_from_contact_peak_A=solution['source_current_from_contact'],
            all_pad_outward_tissue_to_metal_current_peak_A=qpad,
            contact_current_peak_A=solution['contact_current'],
            contact_outward_tissue_to_metal_current_peak_A=-solution['contact_current'],
            contact_normal_J_peak_A_m2=solution['contact_J'], contact_drop_peak_V=solution['contact_drop'],
            contact_pad=pads, contact_xy_index=cells, contact_area_m2=areas,
            layer_complex_power_W=solution['layer_power'],
            tissue_boundary_complex_power_W=np.asarray(complex(
                proof['tissue_boundary_complex_power_W']['real'],
                proof['tissue_boundary_complex_power_W']['imaginary'])),
            source_complex_power_W=np.asarray(solution['source_power']),
            contact_complex_power_W=np.asarray(solution['contact_power']),
            source_resistor_power_W=np.asarray(solution['resistor_power']))
        raw[str(frequency)] = artifact
        proofs[str(frequency)] = dict(path=str(proofpath), bytes=proofpath.stat().st_size,
            SHA256=_inputs().digest(proofpath), record=proof)
        new_json(out / ('checkpoint-floating-' + str(frequency) + '.json'),
            dict(status='new_hypothetical_floating_raw_RHS_saved', actual_new_driven_RHS=len(raw),
                 new_common_return_RHS=0, angular_metric_evaluations=0, raw=artifact))
        del phi, E, interface, qpad, solution, profile
    for chunk in cacheproof:
        check(guard, deadline)
        require(_inputs().digest(chunk['path']) == chunk['SHA256'], 'Full Q cache unchanged after both floating RHS')
    require(len(raw) == 2, 'Exactly two floating carrier RHS')
    return dict(raw_by_frequency=raw, proofs_by_frequency=proofs, actual_new_driven_RHS=2,
                new_common_return_RHS=0, new_B0_RHS=0, new_eigen_solves=0)


def reference(metrics):
    regions = metrics['regions']
    mean = regions['target']['statistics']['maxTIS']['mean']
    surface = regions['surface_0_5']['statistics']['maxTIS']['mean']
    off = regions['off_target']['statistics']['maxTIS']['mean']
    return dict(target_mean=mean, target_P10=regions['target']['statistics']['maxTIS']['p10'],
        target_to_surface_mean=mean / surface if surface > 0 else None,
        target_to_offtarget_mean=mean / off if off > 0 else None)


def min4(normalized, baseline_reference):
    fields = normalized['absolute_ROI_fields_V_m']
    target = fields['target']['maxTIS']
    mean, p10 = target['mean'], target['p10']
    surface = fields['surface_0_5']['maxTIS']['mean']
    off = fields['off_target']['maxTIS']['mean']
    values = dict(target_mean=mean, target_P10=p10,
        target_to_surface_mean=mean / surface if surface > 0 else None,
        target_to_offtarget_mean=mean / off if off > 0 else None)
    ratios = {k: v / baseline_reference[k] if v is not None and
        baseline_reference[k] is not None and baseline_reference[k] > 0 else None
        for k, v in values.items()}
    score = min(ratios.values()) if all(v is not None for v in ratios.values()) else None
    return dict(absolute=values, four_ratios_to_reference=ratios, robust_minimum_four_ratio=score,
        amplitude_scale=normalized['amplitude_scale'],
        electrical=copy.deepcopy(normalized['electrical']),
        limiting_constraints=copy.deepcopy(normalized.get('limiting_constraints', [])))


def comparison_rows(normalizations, baseline_metrics):
    require(normalizations['status'] == 'complete', 'All four separate normalization modes required')
    result = {}
    for mode in MODES:
        row = normalizations['comparisons'][mode]
        result[mode] = min4(row, reference(baseline_metrics)) if row['status'] == 'calculated_global_amplitude_rescaling' else copy.deepcopy(row)
    return result


def _metrics_stage(np, context, modules, artifacts, out, guard, deadline):
    """No Q/profiles/eigenobjects/solver in this frame; aliases are never rebuilt."""
    metrics = modules['frozen_screen_metrics']
    electrical_model = modules['frozen_allocation_electrical']
    adapter = modules['p23_adapter']
    common = _load(np, context['common_grid_ROI'], ['grid'] + [
        name + '_volume_weight_m3' for name in metrics.REGIONS], context, guard, deadline)
    grid = common.pop('grid')
    require(grid.shape == (793860, 5), 'Unchanged original physical evaluation grid')
    weights = {name: common[name + '_volume_weight_m3'] for name in metrics.REGIONS}
    cdir = out / 'candidates'
    cdir.mkdir()
    controls = []
    baseline = context['common_B0']['record']['metrics']
    for name in ('common_B0', 'common_P23'):
        cached = context[name]
        original = cached['record']
        alias = dict(candidate_id=original['candidate_id'], condition_id=original['candidate_id'] + '__common-return',
            status='immutable_published_common_return_control_alias',
            original_record_descriptor=cached['record_descriptor'], geometry=copy.deepcopy(original['geometry']),
            metrics=copy.deepcopy(original['metrics']), normalizations=copy.deepcopy(original['normalizations']),
            min4_to_common_B0=comparison_rows(original['normalizations'], baseline),
            source_physics_proofs=copy.deepcopy(original['source_physics_proofs']),
            raw_by_frequency=copy.deepcopy(cached['raw_by_frequency']), scalar_arrays=copy.deepcopy(cached['scalar']),
            actual_new_RHS=0, actual_new_metric_evaluations=0, no_field_reconstruction=True,
            no_angular_recalculation=True, candidate_adopted=False)
        new_json(cdir / (alias['condition_id'] + '-alias.json'), alias)
        controls.append(alias)
    raw, proofs = [], []
    for f in (2000, 2010):
        descriptor = artifacts['raw_by_frequency'][str(f)]
        raw.append(_load(np, descriptor, ['E_peak_V_m', 'source_current_peak_A',
            'contact_normal_J_peak_A_m2', 'contact_drop_peak_V', 'contact_area_m2',
            'contact_pad', 'contact_xy_index', 'layer_complex_power_W'], context, guard, deadline))
        pd = artifacts['proofs_by_frequency'][str(f)]
        proof = _inputs().read_json(pd['path'], pd['SHA256'])
        require(proof['passed'] is True and proof['frequency_Hz'] == f, 'Same saved complete floating source proof')
        proofs.append(proof)
    electrical, spectral = electrical_model.synthesize(np, raw[0], raw[1], proofs[0], proofs[1], 1., 1.)
    # The frozen helper has a common-return label. Preserve its arithmetic while
    # replacing that descriptive label explicitly before saving this scenario.
    electrical['return_topology'] = adapter.TOPOLOGY
    for row in spectral:
        row['return_topology'] = adapter.TOPOLOGY
        row['physical_pairs'] = [list(p) for p in adapter.PHYSICAL_PAIRS]
        row['actual_hardware_wiring_claimed'] = False
    scalar_electrical = {key: electrical[key] for key in LEGACY_ELECTRICAL}
    scalar_electrical['return_topology'] = adapter.TOPOLOGY
    gamma = context['catalog']['gamma_by_frequency']
    g0 = np.asarray([complex(v['real'], v['imaginary']) for v in gamma['2000']])
    g1 = np.asarray([complex(v['real'], v['imaginary']) for v in gamma['2010']])
    result = metrics.evaluate(np, grid, weights, raw[0]['E_peak_V_m'], raw[1]['E_peak_V_m'],
        g0, g1, scalar_electrical, guard, deadline)
    adapter.correct_metric_metadata(result)
    norms = metrics.normalize(result['summary'], baseline)
    pairwise = metrics.normalize(result['summary'], context['common_P23']['record']['metrics'])
    science = modules['frozen_design_screen']
    record = dict(candidate_id=context['floating_candidate_id'],
        physical_candidate_id=context['physical_candidate']['candidate_id'],
        status='hypothetical_floating_P23_computed_unadopted',
        geometry=adapter.floating_geometry(context['physical_candidate']),
        source_physics_proofs=proofs, metrics=result['summary'], normalizations=norms,
        min4_to_common_B0=comparison_rows(norms, baseline),
        pairwise_normalizations_to_same_mask_common_P23=pairwise,
        min4_to_same_mask_common_P23=comparison_rows(pairwise, context['common_P23']['record']['metrics']),
        per_frequency_signed_circuit=spectral,
        scalar_arrays=science.archive(np, cdir / (context['floating_candidate_id'] + '-scalars.npz'), **result['arrays']),
        raw_by_frequency=artifacts['raw_by_frequency'],
        actual_new_RHS=2, actual_new_metric_evaluations=1,
        Q_or_profiles_or_solver_resident_during_metrics=False, actual_hardware_wiring_claimed=False,
        candidate_adopted=False)
    new_json(cdir / (context['floating_candidate_id'] + '-summary.json'), record)
    return dict(candidates=controls + [record], actual_new_driven_RHS=2,
        actual_new_metric_evaluations=1, immutable_common_control_aliases=2,
        completed_conditions=3, raw_artifacts=artifacts['raw_by_frequency'])


def build(spec, guard, deadline_monotonic=None, output_dir=None, *, resource_probe=None):
    """Deferred sole-root entrypoint; a missing/live-insufficient resource probe blocks.

    resource_probe() must supply the LIVE complete ALL-RSS+ALL-owned-task1-tmpfs
    aggregate. It is deliberately required rather than guessed from child RSS.
    The guardian must already enforce CPU4/deadline/8e9 aggregate before import.
    """
    require(spec == make_spec(spec['root_admission']), 'Exact root-selected frozen comparison spec')
    check(guard, deadline_monotonic)
    require(callable(resource_probe), 'BLOCKED: current complete root resource forecast unavailable')
    forecast = _inputs().check_resource_forecast(resource_probe(), raw_stage=True)
    out = Path(output_dir or spec['root_admission']['output_directory'])
    require(out.is_absolute() and out == out.resolve() and out.is_dir() and not out.is_symlink()
            and out.parent == Path('/dev/shm') and str(out) == spec['root_admission']['output_directory'],
            'Unique root-created /dev/shm output; source/input trees remain read only')
    context = spec['inputs']
    _authenticate_alias_files(context, guard, deadline_monotonic)
    modules = _dependencies(context)
    import numpy as np
    new_json(out / 'resource-forecast.json', forecast)
    new_json(out / 'memory-plan.json', dict(plan=spec['memory_plan'], forecast=spec['forecast']))

    def raw_stage():
        return _raw_stage(np, context, modules, out, guard, deadline_monotonic)

    def collect():
        collected = gc.collect()
        check(guard, deadline_monotonic)
        live = _inputs().check_resource_forecast(resource_probe(), raw_stage=False)
        new_json(out / 'Q-release-boundary.json', dict(
            status='raw_frame_returned_Q_profiles_solver_out_of_scope_then_gc',
            raw_stage_return='JSON identities only', collected=collected,
            angular_metric_evaluations_started=0, resources=live))

    def metric_stage(artifacts):
        check(guard, deadline_monotonic)
        new_json(out / 'new-floating-raw-identities.json', artifacts)
        return _metrics_stage(np, context, modules, artifacts, out, guard, deadline_monotonic)

    result = separated_stages(raw_stage, metric_stage, collect)
    check(guard, deadline_monotonic)
    _inputs().check_resource_forecast(resource_probe(), raw_stage=False)
    summary = dict(schema='task1-hypothetical-floating-P23-comparison-result-v1',
        status='hypothetical_floating_P23_comparison_computed_unadopted', spec=spec, **result,
        ROI_receipt=context['ROI_receipt'], provisional_field=modules['frozen_design_screen'].provisional_field.provenance(),
        common_return_and_hypothetical_floating_separately_named=True,
        source_pad_frequency_assignment_preserved=True, physical_mask_changed=False,
        new_common_return_RHS=0, new_B0_RHS=0, new_eigen_solves=0,
        actual_hardware_wiring_claimed=False, holds=spec['holds'], candidate_adopted=False,
        Windows_saved_verified=False)
    return dict(summary=summary, arrays={})
