"""Bounded, owner-called metrics for the frozen two actual carrier responses.

No imports, IO, subprocesses, research execution, or native-array allocations happen on import.
``evaluate`` consumes a repeatable factory of (first,last,E2000,E2010) chunks;
each input is an unscaled complex128 C-order (<=128,3) peak-phasor array.
The three-tuple (first,E2000,E2010) adapter is accepted as well.

``grid`` may be a Float64 ndarray or a lazy adapter exposing shape, len,
grid[first:last,:], and grid[index,:3]. ``weights`` is a mapping exposing the
exact six original REGIONS; __getitem__ may materialize one Float64 N-vector.
No input arrays are changed. A sampler take_rows(indices)->(E2000,E2010) can
avoid a second carrier scan for the representative waveform checks.

All eight scalar statistics and all actually saved baseline maps are retained.
Only the two requested candidate maps leave evaluate; baseline maps do not.
The fixed tolerances below must be frozen before the owner executes this code.
"""

FREQUENCIES_HZ = (2000, 2010)
REGIONS = ('total', 'target', 'surface_0_5', 'subsurface_5_10', 'remaining', 'off_target')
LAYER_NAMES = ('sc', 'dermis', 'fat', 'muscle')
SCOPES = REGIONS + ('surface_without_SC', 'skin_SC_plus_dermis') + tuple('layer_' + v for v in LAYER_NAMES)
LINEAR_BURDENS = ('contact_normal_J_RMS_max_A_m2', 'contact_normal_J_RMS_P95_A_m2',
                 'contact_voltage_RMS_max_V', 'skin_vector_J_RMS_max_A_m2', 'skin_vector_J_RMS_P95_A_m2')
POWER_BURDENS = ('SC_power_W', 'skin_power_W', 'contact_power_W')
MAX_CHUNK_CELLS = 128
MAP_RTOL = 2e-7
MAP_ATOL = 1e-10
ELECTRICAL_RTOL = 2e-7
ELECTRICAL_ATOL = 1e-15
VOLUME_RTOL = 1e-12
VOLUME_ATOL = 1e-25
COORDINATE_RTOL = 1e-12
COORDINATE_ATOL = 1e-12
MAP_NAMES = ('AM_max2074', 'carrier_RMS', 'AM_x', 'AM_y', 'AM_z',
             'carrier0_RMS', 'carrier1_RMS', 'Jtotal_vector_RMS')
BASELINE_MAP_NAMES = ('AM_max2074', 'carrier_RMS', 'Jtotal_vector_RMS')
UNAVAILABLE_BASELINE_MAP_NAMES = ('AM_x', 'AM_y', 'AM_z', 'carrier0_RMS', 'carrier1_RMS')
SCALAR_NAMES = ('maxTIS', 'RMS', 'X_TIS', 'Y_TIS', 'Z_TIS',
                'carrier0_RMS', 'carrier1_RMS', 'Jtotal_vector_RMS')


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _check(guard, deadline):
    import time
    guard()
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Incomplete streamed metrics: deadline reached; no partial maximum is valid')


def _chunks(np, factory, n, guard, deadline):
    """Validate bounded C-order rows and exact native order, without conversion."""
    expected = 0
    for row in factory():
        _check(guard, deadline)
        _require(isinstance(row, (tuple, list)) and len(row) in (3, 4), 'Carrier chunk tuple ABI')
        if len(row) == 4:
            first, last, a, b = row
        else:
            first, a, b = row
            last = first + len(a)
        _require(type(first) is int and type(last) is int and first == expected and
                 first < last <= n and last - first <= MAX_CHUNK_CELLS,
                 'Contiguous complete native carrier order and chunk <=128 required')
        for value in (a, b):
            _require(isinstance(value, np.ndarray) and value.dtype == np.dtype(np.complex128) and
                     value.shape == (last - first, 3) and value.flags.c_contiguous and
                     np.isfinite(value).all(), 'Finite complex128 C-order native carrier chunks required')
        yield first, last, a, b
        expected = last
    _require(expected == n, 'Incomplete native carrier stream; no partial maximum is valid')


def _base_weight(np, weights, key, n, guard, deadline):
    _check(guard, deadline)
    value = weights[key]
    _require(isinstance(value, np.ndarray) and value.dtype == np.dtype(float) and
             value.shape == (n,), 'Exact complete Float64 native m3 weight: ' + key)
    # These one-byte-per-cell temporaries are included in the scratch bound.
    _require(np.isfinite(value).all() and np.all(value >= 0), 'Finite nonnegative native weights: ' + key)
    return value


def _scope_weight(np, grid, weights, scope, n, guard, deadline):
    """At most one supplied weight plus one derived weight; never six masks."""
    if scope in REGIONS:
        return _base_weight(np, weights, scope, n, guard, deadline)
    key = 'surface_0_5' if scope == 'surface_without_SC' else 'total'
    original = _base_weight(np, weights, key, n, guard, deadline)
    out = np.array(original, dtype=float, copy=True)
    del original
    if isinstance(grid, np.ndarray):
        layers = grid[:, 3]  # Native view; no persistent integer layer array.
        if scope == 'surface_without_SC':
            keep = layers != 0
        elif scope == 'skin_SC_plus_dermis':
            keep = layers <= 1
        else:
            keep = layers == LAYER_NAMES.index(scope[len('layer_'):])
        out *= keep
        _check(guard, deadline)
        return out
    for first in range(0, n, MAX_CHUNK_CELLS):
        last = min(n, first + MAX_CHUNK_CELLS)
        _check(guard, deadline)
        layers = grid[first:last, :][:, 3]
        if scope == 'surface_without_SC':
            keep = layers != 0
        elif scope == 'skin_SC_plus_dermis':
            keep = layers <= 1
        else:
            keep = layers == LAYER_NAMES.index(scope[len('layer_'):])
        out[first:last] *= keep
    return out


def _validate_inputs(np, grid, weights, gamma0, gamma1, electrical, guard, deadline):
    n = len(grid)
    _require(0 < n <= 800000 and tuple(grid.shape) == (n, 5), 'Complete native grid N by 5; maximum800000 cells')
    _require(set(weights) == set(REGIONS), 'Exact original six native-region weight keys required')
    for first in range(0, n, MAX_CHUNK_CELLS):
        last = min(n, first + MAX_CHUNK_CELLS)
        _check(guard, deadline)
        cells = grid[first:last, :]
        _require(isinstance(cells, np.ndarray) and cells.dtype == np.dtype(float) and
                 cells.shape == (last - first, 5) and np.isfinite(cells).all(), 'Finite Float64 native grid chunks required')
        layers = cells[:, 3]
        _require(np.array_equal(layers.astype(int), layers) and np.all((layers >= 0) & (layers < 4)),
                 'Four exact integer layer labels required')
    # Validate the total/target/off-target identities in bounded row slices.
    # Lazy weights can implement read_rows to avoid keeping three N-vectors.
    if hasattr(weights, 'read_rows'):
        for first in range(0, n, MAX_CHUNK_CELLS):
            last = min(n, first + MAX_CHUNK_CELLS)
            _check(guard, deadline)
            total, target, off = (weights.read_rows(key, first, last) for key in ('total', 'target', 'off_target'))
            _validate_weight_identity(np, total, target, off, grid[first:last, :][:, 4])
    else:
        total = _base_weight(np, weights, 'total', n, guard, deadline)
        target = _base_weight(np, weights, 'target', n, guard, deadline)
        off = _base_weight(np, weights, 'off_target', n, guard, deadline)
        for first in range(0, n, MAX_CHUNK_CELLS):
            last = min(n, first + MAX_CHUNK_CELLS)
            _check(guard, deadline)
            _validate_weight_identity(np, total[first:last], target[first:last], off[first:last], grid[first:last, :][:, 4])
        del total, target, off
    for key in REGIONS:
        weight = _base_weight(np, weights, key, n, guard, deadline)
        del weight
    g0 = np.asarray(gamma0, np.complex128)
    g1 = np.asarray(gamma1, np.complex128)
    _require(g0.shape == g1.shape == (4,) and np.isfinite(g0).all() and np.isfinite(g1).all() and
             np.all(abs(g0) > 0) and np.all(abs(g1) > 0), 'Actual complex four-layer admittivities required')
    _require(float(electrical['source_Vpp_each']) == 1., 'Original maximum active source is 1 Vpp high-Z')
    return n, g0, g1


def _validate_weight_identity(np, total, target, off, volume):
    _require(all(np.asarray(v).shape == volume.shape and np.isfinite(v).all() and np.all(v >= 0)
                 for v in (total, target, off)) and
             np.allclose(total, volume, rtol=VOLUME_RTOL, atol=VOLUME_ATOL) and
             np.all(target <= total * (1 + VOLUME_RTOL)) and
             np.allclose(off, total - target, rtol=VOLUME_RTOL, atol=VOLUME_ATOL),
             'Native total/target/off-target weights must agree with supplied actual grid')


def _array_comparison(n):
    return dict(status='pending', native_cells=n, float_maps={name: dict(compared_cells=0, failed_cells=0, max_absolute_error=0.)
                                            for name in BASELINE_MAP_NAMES},
                unavailable_original_pixel_maps=list(UNAVAILABLE_BASELINE_MAP_NAMES),
                unavailable_scope='Original E13 producer did not save these five pixel maps; summary statistics remain gated',
                all_eight_scalar_summary_metrics_required=True,
                direction_first_tie=dict(compared_cells=0, differing_cells=0,
                                         semantics='Diagnostic only; all2074 directions and AM values are gated'),
                rtol=MAP_RTOL, atol=MAP_ATOL)


def _compare_chunk(np, reference, checks, values, winner, first, last, guard, deadline):
    for name, value in zip(MAP_NAMES, values):
        if name not in BASELINE_MAP_NAMES:
            continue
        _check(guard, deadline)
        old = reference(name, first, last)
        _require(isinstance(old, np.ndarray) and old.shape == (last - first,) and
                 old.dtype == np.dtype(float) and np.isfinite(old).all(), 'Complete finite frozen scalar map chunk: ' + name)
        error = np.abs(value - old)
        row = checks['float_maps'][name]
        row['compared_cells'] += last - first
        row['failed_cells'] += int(np.count_nonzero(error > MAP_ATOL + MAP_RTOL * np.abs(old)))
        row['max_absolute_error'] = max(row['max_absolute_error'], float(np.max(error)))
    old = reference('AM_direction_index', first, last)
    _require(isinstance(old, np.ndarray) and old.shape == (last - first,) and np.isfinite(old).all() and
             np.array_equal(old, old.astype(int)) and np.all((old >= 0) & (old < 2074)),
             'Complete original integer sampled-direction chunk required')
    checks['direction_first_tie']['compared_cells'] += last - first
    checks['direction_first_tie']['differing_cells'] += int(np.count_nonzero(old != winner))


def _take_waveform_rows(np, factory, take_rows, indices, n, guard, deadline):
    if take_rows is not None:
        _check(guard, deadline)
        a, b = take_rows(indices)
        _require(all(isinstance(v, np.ndarray) and v.dtype == np.dtype(np.complex128) and
                     v.shape == (len(indices), 3) and np.isfinite(v).all() for v in (a, b)),
                 'Sampler must return ordered complete actual carrier vectors')
        return a, b
    a = np.empty((len(indices), 3), np.complex128)
    b = np.empty_like(a)
    found = 0
    for first, last, e0, e1 in _chunks(np, factory, n, guard, deadline):
        for row, index in enumerate(indices):
            if first <= index < last:
                a[row] = e0[index - first]
                b[row] = e1[index - first]
                found += 1
    _require(found == len(indices), 'Representative waveform rows unavailable')
    return a, b


def _waveform_checks(np, factory, take_rows, maximum, winner, dirs, grid, weights,
                     a0, a1, guard, deadline):
    n = len(maximum)
    indices = {int(np.argmax(maximum))}
    target = _base_weight(np, weights, 'target', n, guard, deadline)
    target_index = None
    target_maximum = -1.
    for first in range(0, n, MAX_CHUNK_CELLS):
        last = min(n, first + MAX_CHUNK_CELLS)
        _check(guard, deadline)
        valid = target[first:last] > 0
        if np.any(valid):
            values = np.where(valid, maximum[first:last], -1.)
            local = int(np.argmax(values))
            if float(values[local]) > target_maximum:
                target_index = first + local
                target_maximum = float(values[local])
    del target
    if target_index is not None:
        indices.add(target_index)
    indices = sorted(indices)
    E0, E1 = _take_waveform_rows(np, factory, take_rows, indices, n, guard, deadline)
    rows = []
    t = np.arange(8192, dtype=float) * (.1 / 8192.)
    carrier0 = np.exp(2j * np.pi * 2000. * t)
    carrier1 = np.exp(2j * np.pi * 2010. * t)
    for row, index in enumerate(indices):
        for label, u in [('x', np.asarray([1., 0., 0.])), ('y', np.asarray([0., 1., 0.])),
                         ('z', np.asarray([0., 0., 1.])), ('sampled_winner', dirs[winner[index]])]:
            _check(guard, deadline)
            a = complex((E0[row] * a0) @ u)
            b = complex((E1[row] * a1) @ u)
            constructive = (np.angle(a) - np.angle(b)) / (2. * np.pi * 10.)
            destructive = constructive + .05
            envelope_max = float(abs(a + b * np.exp(2j * np.pi * 10. * constructive)))
            envelope_min = float(abs(a + b * np.exp(2j * np.pi * 10. * destructive)))
            expected_am = 2. * min(abs(a), abs(b))
            observed_am = envelope_max - envelope_min
            waveform = np.real(a * carrier0 + b * carrier1)
            observed_rms = float(np.sqrt(np.mean(waveform ** 2)))
            expected_rms = float(np.sqrt((abs(a) ** 2 + abs(b) ** 2) / 2.))
            am_error = abs(observed_am - expected_am)
            rms_error = abs(observed_rms - expected_rms)
            _require(am_error <= 1e-10 + 1e-10 * expected_am and rms_error <= 1e-10 + 1e-10 * expected_rms,
                     'Exact two-carrier representative waveform check failed')
            rows.append(dict(native_cell_index=index, direction=label, unit_vector=u.tolist(),
                             envelope_max_V_m=envelope_max, envelope_min_V_m=envelope_min,
                             AM_formula_V_m=expected_am, AM_waveform_V_m=observed_am,
                             carrier_RMS_formula_V_m=expected_rms, carrier_RMS_time_V_m=observed_rms,
                             AM_absolute_error_V_m=am_error, RMS_absolute_error_V_m=rms_error, passed=True))
    return dict(status='passed', scope='Representative cells/directions, exact two actual carrier phasors only',
                duration_s=.1, samples=8192, sample_rate_Hz=81920., rows=rows,
                full_field_time_sampled=False, multifrequency_formula_generalization_claimed=False)


def compare_baseline(np, summary, baseline_summary, array_checks):
    """Gate every original ROI/scalar/electrical/waveform field at fixed tolerances.

    The frozen summary's schema/display metadata are not numerical physics.
    Numerical extrema indices, positive cell counts, tie counts and row order
    are exact; volume and coordinate fields use their tighter fixed tolerances.
    Full-field direction-index agreement is reported separately as a diagnostic.
    """
    import math
    failures = []
    compared = 0

    def walk(new, old, path):
        nonlocal compared
        if isinstance(old, dict):
            if not isinstance(new, dict) or not set(old).issubset(new):
                failures.append(dict(path=path, reason='required frozen mapping keys missing'))
                return
            for key in old:
                walk(new[key], old[key], path + '/' + str(key))
        elif isinstance(old, (list, tuple)):
            if not isinstance(new, (list, tuple)) or len(new) != len(old):
                failures.append(dict(path=path, reason='sequence shape differs'))
                return
            for index, value in enumerate(old):
                walk(new[index], value, path + '/' + str(index))
        elif type(old) is bool or old is None or isinstance(old, str):
            if new != old:
                failures.append(dict(path=path, reason='categorical field differs'))
        elif isinstance(old, (int, float)):
            compared += 1
            if not isinstance(new, (int, float)) or not math.isfinite(float(new)) or not math.isfinite(float(old)):
                failures.append(dict(path=path, reason='nonfinite or missing number'))
                return
            if type(old) is int:
                valid = type(new) is int and new == old
            else:
                if 'volume_m3' in path:
                    rtol, atol = VOLUME_RTOL, VOLUME_ATOL
                elif 'xyz_mm' in path:
                    rtol, atol = COORDINATE_RTOL, COORDINATE_ATOL
                elif path.startswith('electrical/'):
                    rtol, atol = ELECTRICAL_RTOL, ELECTRICAL_ATOL
                else:
                    rtol, atol = MAP_RTOL, MAP_ATOL
                valid = abs(float(new) - float(old)) <= atol + rtol * abs(float(old))
            if not valid:
                failures.append(dict(path=path, reason='fixed numeric tolerance failed', computed=new, frozen=old))
        else:
            failures.append(dict(path=path, reason='unsupported frozen summary type'))

    for key in ('regions', 'electrical', 'waveform_checks'):
        if key not in summary or key not in baseline_summary:
            failures.append(dict(path=key, reason='required complete baseline field missing'))
        else:
            walk(summary[key], baseline_summary[key], key)
    old_regions = baseline_summary.get('regions', {})
    if set(old_regions) != set(SCOPES) or any(set(row.get('statistics', {})) != set(SCALAR_NAMES)
                                            for row in old_regions.values()):
        failures.append(dict(path='regions', reason='all original scopes and all eight scalar statistics required'))
    complete_arrays = False
    if isinstance(array_checks, dict) and array_checks.get('status') == 'passed':
        count = array_checks.get('native_cells')
        maps = array_checks.get('float_maps', {})
        complete_arrays = (type(count) is int and 0 < count <= 800000 and set(maps) == set(BASELINE_MAP_NAMES) and
                           all(row.get('compared_cells') == count and row.get('failed_cells') == 0
                               for row in maps.values()) and
                           array_checks.get('direction_first_tie', {}).get('compared_cells') == count)
    return dict(schema='task1-streamed-baseline-agreement-v1',
                status='passed' if complete_arrays and not failures else 'failed',
                verified_native_cells=array_checks.get('native_cells') if complete_arrays else None,
                array_agreement=array_checks, compared_summary_numbers=compared,
                summary_failures=failures,
                map_tolerances=dict(rtol=MAP_RTOL, atol=MAP_ATOL),
                electrical_tolerances=dict(rtol=ELECTRICAL_RTOL, atol=ELECTRICAL_ATOL),
                volume_tolerances=dict(rtol=VOLUME_RTOL, atol=VOLUME_ATOL),
                coordinate_tolerances=dict(rtol=COORDINATE_RTOL, atol=COORDINATE_ATOL),
                pointwise_compared_original_float_maps=list(BASELINE_MAP_NAMES),
                unavailable_original_pixel_maps=list(UNAVAILABLE_BASELINE_MAP_NAMES),
                tolerance_changed_after_execution=False,
                baseline_maps_exported=False)


def evaluate(np, grid, weights, carrier_factory, gamma0_by_layer, gamma1_by_layer, electrical,
             a0=1., a1=1., take_rows=None, guard=lambda: None, deadline=None,
             baseline_arrays=None, baseline_summary=None, baseline_gate=None, export_maps=True):
    """Return old-compatible summary, optional two candidate maps, baseline gate.

    baseline_arrays(name,first,last) must return each frozen scalar Float64
    chunk and the original direction-index chunk. Baseline a0=a1=1 performs
    all three actually saved float-map comparisons and complete eight-scalar
    scope/electrical/waveform QA; only a
    passed gate permits either registered candidate. No baseline output maps
    are returned regardless of export_maps. An unevidenced baseline can be
    evaluated for diagnostics, but its result cannot authorize candidates.
    """
    _check(guard, deadline)
    a0, a1 = float(a0), float(a1)
    _require((a0, a1) in ((1., 1.), (.8, 1.), (1., .8)), 'Only registered baseline/0.8/1.25 allocations')
    baseline = a0 == a1 == 1.
    if not baseline:
        _require(isinstance(baseline_gate, dict) and baseline_gate.get('schema') == 'task1-streamed-baseline-agreement-v1'
                 and baseline_gate.get('status') == 'passed', 'Both new allocations require the complete passed baseline gate')
        _require(baseline_arrays is None and baseline_summary is None, 'Candidate never substitutes for baseline verification')
    n, g0, g1 = _validate_inputs(np, grid, weights, gamma0_by_layer, gamma1_by_layer, electrical, guard, deadline)
    if not baseline:
        _require(baseline_gate.get('verified_native_cells') == n, 'Passed baseline gate must cover this complete native grid')
    if not baseline or 'source_Vpp_by_frequency' in electrical:
        source = electrical.get('source_Vpp_by_frequency', {})
        _require(set(source) == {'2000', '2010'} and float(source['2000']) == a0 and float(source['2010']) == a1,
                 'Electrical synthesis must use these two actual registered source amplitudes')
    dirs = directions(np)
    _require(dirs.shape == (2074, 3), 'Exact original 2074 sampled directions required')
    scalars = {name: np.empty(n, float) for name in SCALAR_NAMES}
    winner = np.empty(n, np.int32)
    checks = _array_comparison(n) if baseline_arrays is not None else dict(status='not_run_no_frozen_array_reader')
    for first, last, raw0, raw1 in _chunks(np, carrier_factory, n, guard, deadline):
        a = raw0 if a0 == 1. else raw0 * a0
        b = raw1 if a1 == 1. else raw1 * a1
        sq0 = np.sum(abs(a) ** 2, axis=1)
        sq1 = np.sum(abs(b) ** 2, axis=1)
        rms = np.sqrt((sq0 + sq1) / 2.)
        xyz = 2. * np.minimum(abs(a), abs(b))
        pa = np.abs(a @ dirs.T)
        pb = np.abs(b @ dirs.T)
        np.minimum(pa, pb, out=pa)
        k = np.argmax(pa, axis=1)
        maximum = 2. * pa[np.arange(last - first), k]
        del pa, pb
        upper = 2. * np.minimum(np.sqrt(sq0), np.sqrt(sq1))
        tol = 256. * np.finfo(float).eps * np.maximum(rms, upper)
        _require(np.isfinite(rms).all() and np.isfinite(maximum).all() and np.all(maximum <= upper + tol),
                 'Finite completed sampled modulation must respect analytic vector upper bound')
        layers = grid[first:last, :][:, 3].astype(int)
        jrms = np.sqrt((abs(g0[layers]) ** 2 * sq0 + abs(g1[layers]) ** 2 * sq1) / 2.)
        _require(np.isfinite(jrms).all(), 'Derived total-current RMS must be finite')
        values = (maximum, rms, xyz[:, 0], xyz[:, 1], xyz[:, 2], np.sqrt(sq0 / 2.), np.sqrt(sq1 / 2.), jrms)
        for name, value in zip(SCALAR_NAMES, values):
            scalars[name][first:last] = value
        winner[first:last] = k
        if baseline_arrays is not None:
            _compare_chunk(np, baseline_arrays, checks, values, k, first, last, guard, deadline)
    if baseline_arrays is not None:
        checks['status'] = 'passed' if all(v['compared_cells'] == n and v['failed_cells'] == 0
                                           for v in checks['float_maps'].values()) else 'failed'
        checks['direction_first_tie']['status'] = ('identical' if checks['direction_first_tie']['differing_cells'] == 0
                                                   else 'different_with_amplitude_gate_preserved')
    regions = {key: dict(volume_m3=0., statistics={}) for key in SCOPES}
    for name, values in scalars.items():
        _check(guard, deadline)
        order = np.argsort(values, kind='stable')
        for key in SCOPES:
            _check(guard, deadline)
            weight = _scope_weight(np, grid, weights, key, n, guard, deadline)
            regions[key]['volume_m3'] = float(np.sum(weight))
            regions[key]['statistics'][name] = weighted_stats(np, values, weight, grid, order)
            stats = regions[key]['statistics'][name]
            if stats.get('status') == 'complete':
                stats['CV'] = float(stats['std'] / stats['mean']) if stats['mean'] > 0 else None
            del weight
        del order
    electrical = dict(electrical)
    skin = regions['skin_SC_plus_dermis']['statistics']['Jtotal_vector_RMS']
    _require(skin['status'] == 'complete', 'Actual skin has positive weighted volume')
    electrical['skin_vector_J_RMS_max_A_m2'] = skin['max']
    electrical['skin_vector_J_RMS_P95_A_m2'] = skin['p95']
    waveform = _waveform_checks(np, carrier_factory, take_rows, scalars['maxTIS'], winner, dirs,
                                grid, weights, a0, a1, guard, deadline)
    _check(guard, deadline)
    summary = _summary(regions, electrical, waveform)
    summary['allocation_amplitudes'] = dict(a0=a0, a1=a1, relative_multiplier=a0 / a1,
                                           maximum_original_source_Vpp=1., new_PDE_runs=0)
    gate = (compare_baseline(np, summary, baseline_summary, checks)
            if baseline_summary is not None else dict(schema='task1-streamed-baseline-agreement-v1',
                                                      status='not_run_no_frozen_summary', array_agreement=checks))
    arrays = (dict(AM_max2074=scalars['maxTIS'], carrier_RMS=scalars['RMS'])
              if not baseline and export_maps else {})
    return dict(summary=summary, arrays=arrays, baseline_agreement=gate)


def _summary(regions, electrical, waveform):
    return dict(schema='task1-provisional-coarse-dtn-screen-metrics-v1', status='calculated_provisional_complete',
                frequencies_Hz=list(FREQUENCIES_HZ), pads=4, independent_outputs=2,
                return_topology='Two driven pads; two returns at common ground; inactive output retained through 50 ohm',
                regions=regions, electrical=electrical, waveform_checks=waveform,
                directional_search=dict(completed=True, directions=2074, chunk_cells=MAX_CHUNK_CELLS,
                    method='Exact original 26 lattice directions plus 2048 Fibonacci directions, original order',
                    metric='max_sampled_real_unit_u 2 min(abs(E2000 dot u),abs(E2010 dot u))',
                    angular_maximum_scope='Sampled lower bound; not continuum angular maximum'),
                coordinate_system=dict(surface_z_mm=0., depth_axis='+z', target='r<=5 mm;15<=z<=20 mm',
                    weighting='Caller-passed original fractional native ROI weights in m3; stable inverse volume ECDF'),
                units=dict(E='V/m', Jtotal='A/m2', volume='m3'),
                conventions=dict(phasor='peak,+jomega*t', carrier_RMS='sqrt((||E2000||²+||E2010||²)/2)',
                    current='Derived gamma*E total current including displacement; not independent validation',
                    modulation='Two actual distinct sinusoidal carriers only; no multi-frequency extrapolation'),
                thresholds=dict(high_modulation_volume='not_run; no preregistered numerical cutoffs in this provisional batch',
                    physiological_activation_threshold='unvalidated'),
                holds=dict(candidate_adopted=False, full_numerical_convergence=False, experimental_validation=False,
                    old_5percent_failures_preserved=True, SC_XY_bulk_edge_contact_uncertainty=True,
                    electrical_proxy_is_not_activation_or_safety=True))


def allocation_budget(n=793848, resident_grid=True, resident_weights=1):
    """Conservative source-level forecast; not a substitute for owner's RSS guard.

    Counts all module arrays and supplied persistent grid/weights, stable sort
    working storage, original weighted_stats temporaries, one copied scope,
    and a 60MB interpreter/NumPy/allocator margin. IO owner must separately
    bound its buffers and actual aggregate RSS+all owned tmpfs <=8,000,000,000.
    Retaining candidate maps from an earlier call adds 16*N outside this bound.
    """
    _require(type(n) is int and 0 < n <= 800000 and type(resident_weights) is int and 0 <= resident_weights <= 6,
             'Registered maximum800000 cells;0..6 resident original weights')
    rows = dict(grid_bytes=40 * n if resident_grid else 128 * 5 * 8,
                original_weight_bytes=8 * n * resident_weights,
                eight_scalar_arrays_and_winner_bytes=68 * n,
                one_scope_and_original_weight_bytes=16 * n,
                sort_indices_and_stable_sort_workspace_bytes=16 * n,
                frozen_weighted_stats_scratch_bytes=42 * n,
                angular_and_carrier_chunk_bytes=9000000,
                python_numpy_allocator_margin_bytes=60000000)
    base = (rows['grid_bytes'] + rows['original_weight_bytes'] +
            rows['eight_scalar_arrays_and_winner_bytes'] + rows['python_numpy_allocator_margin_bytes'])
    # Angular projection and weighted statistics occur in separate phases.
    statistics = (rows['one_scope_and_original_weight_bytes'] +
                  rows['sort_indices_and_stable_sort_workspace_bytes'] +
                  rows['frozen_weighted_stats_scratch_bytes'])
    rows['total_forecast_bytes'] = base + max(rows['angular_and_carrier_chunk_bytes'], statistics)
    rows['provisional_workspace_limit_bytes'] = 220000000
    rows['within_provisional_workspace_limit'] = rows['total_forecast_bytes'] <= 220000000
    rows['two_conditions_two_maps_raw_bytes'] = 32 * n
    rows['provisional_new_output_forecast_bytes'] = 35000000
    rows['output_forecast_is_storage_quota'] = False
    rows['actual_aggregate_RSS_plus_owned_tmpfs_hard_limit_bytes'] = 8000000000
    rows['actual_guard_must_include_both_owned_tmpfs_roots'] = True
    return rows


# The following original metric/statistics/scaling function bodies are copied exactly.

def directions(np):
    """Exact original explore_tis.directions(2048) ordering: 26+2048 real units."""
    base=[]
    for x in(-1,0,1):
        for y in(-1,0,1):
            for z in(-1,0,1):
                if x or y or z:
                    v=np.asarray([x,y,z],float);base.append(v/np.linalg.norm(v))
    for i in range(2048):
        z=1.-2.*(i+.5)/2048.;p=i*np.pi*(3.-np.sqrt(5.));r=np.sqrt(1.-z*z)
        base.append([r*np.cos(p),r*np.sin(p),z])
    return np.asarray(base,float)


def weighted_stats(np,values,w,grid,order=None):
    """Inverse volume ECDF; native representative extrema, not continuum maxima."""
    values=np.asarray(values,float);w=np.asarray(w,float)
    _require(values.shape==w.shape and values.ndim==1 and np.isfinite(values).all()and
             np.isfinite(w).all()and np.all(w>=0),'Finite scalar values and nonnegative m3 weights required')
    use=w>0;indices=np.flatnonzero(use)
    if not len(indices):return dict(status='not_run_no_positive_volume',volume_m3=0.)
    total=float(np.sum(w));mean=float(np.sum(values*w)/total)
    std=float(np.sqrt(np.sum(w*(values-mean)**2)/total))
    if order is None:order=np.argsort(values,kind='stable')
    cumulative=np.cumsum(w[order]);lo=int(indices[np.argmin(values[use])]);hi=int(indices[np.argmax(values[use])])
    result=dict(status='complete',volume_m3=total,positive_weight_cells=len(indices),
                min=float(values[lo]),max=float(values[hi]),mean=mean,std=std,
                minimum_native_cell_index=lo,maximum_native_cell_index=hi,
                minimum_xyz_mm=[float(v)for v in grid[lo,:3]],maximum_xyz_mm=[float(v)for v in grid[hi,:3]],
                maximum_tied_cells=int(np.sum(use&(values==values[hi]))),
                maximum_tied_volume_m3=float(np.sum(w[values==values[hi]])),
                extrema_scope='Cell-constant samples with positive fractional ROI weight; representative centre may lie outside a fractional ROI boundary')
    for name,p in(('p10',.1),('median',.5),('p95',.95),('p99',.99)):
        k=min(int(np.searchsorted(cumulative,p*cumulative[-1],side='left')),len(values)-1)
        result[name]=float(values[order[k]])
    return result


def _cap(reference,candidate,exponent):
    import math
    reference=float(reference);candidate=float(candidate)
    _require(math.isfinite(reference)and math.isfinite(candidate)and reference>=0 and candidate>=0,
             'Finite nonnegative normalization quantities required')
    if candidate==0:return None
    return (reference/candidate)**(1./exponent)


def normalize(metrics,baseline):
    """Separate global-amplitude comparisons; never assume simultaneous equality.

    Inputs are evaluate()['summary'] dicts. Joint8 uses FIVE linear contact/skin
    burdens and THREE loss powers with quadratic scaling. Baseline quantities
    are numerical comparison caps, not human safety limits. A zero candidate
    burden gives no cap for that constraint, explicitly represented as None.
    """
    import math
    e=metrics['electrical'];b=baseline['electrical'];required=('source_Vpp_each',
        'sum_output_current_RMS_A_bookkeeping','source_power_W')+LINEAR_BURDENS+POWER_BURDENS
    missing=[key for key in required if key not in e or key not in b]
    if missing:return dict(status='not_run_missing_normalization_inputs',missing_keys=missing)
    caps={key:_cap(b[key],e[key],1 if key in LINEAR_BURDENS else 2)for key in LINEAR_BURDENS+POWER_BURDENS}
    finite=[v for v in caps.values()if v is not None]
    scenarios=dict(same_source_voltage=_cap(b['source_Vpp_each'],e['source_Vpp_each'],1),
        same_sum_output_RMS_current_bookkeeping=_cap(b['sum_output_current_RMS_A_bookkeeping'],e['sum_output_current_RMS_A_bookkeeping'],1),
        same_source_real_power=_cap(b['source_power_W'],e['source_power_W'],2),
        joint_eight_surface_contact_burden_caps=min(finite)if finite else None)
    rows={}
    for name,s in scenarios.items():
        if s is None:rows[name]=dict(status='not_run_unbounded_or_zero_candidate_reference');continue
        _require(math.isfinite(s)and s>=0,'Finite normalization scale required')
        fields={}
        for region in('target','surface_0_5','surface_without_SC','off_target','total'):
            fields[region]={}
            for metric in('maxTIS','RMS','X_TIS','Y_TIS','Z_TIS'):
                values=metrics['regions'][region]['statistics'][metric]
                fields[region][metric]={key:float(values[key])*s for key in('mean','p10','median','p95','p99','max','std')if key in values}
        rows[name]=dict(status='calculated_global_amplitude_rescaling',amplitude_scale=s,
                       absolute_ROI_fields_V_m=fields,electrical=_scaled_electrical(e,s))
        if name=='joint_eight_surface_contact_burden_caps':
            rows[name]['individual_amplitude_caps']=caps
            rows[name]['limiting_constraints']=[key for key,v in caps.items()if v is not None and abs(v-s)<=1e-12*max(1.,s)]
    return dict(schema='task1-provisional-normalization-v1',status='complete',comparisons=rows,
                current_definition='Sum of individual independent-output RMS magnitudes as bookkeeping, not a unique total-current physical invariant',
                simultaneous_equal_current_power_burden_assumed=False,
                burden_caps_scope='Baseline numerical values only; not human safety limits',
                fixed_voltage_raw_result_preserved=True,candidate_adopted=False)


def _number(value):
 import math
 result=float(value);_require(math.isfinite(result),'Finite scaling input required');return result


def _complex_pair(value,factor):
 _require(isinstance(value,dict)and set(value)=={'real','imaginary'},'Explicit signed complex pair required')
 return dict(real=_number(value['real'])*factor,imaginary=_number(value['imaginary'])*factor)


def scale_electrical(e,s):
 import copy
 s=_number(s);_require(s>=0,'Nonnegative finite amplitude scale');square=s*s;out={}
 pair_keys=('source_complex_power_W','contact_complex_power_W')
 linear_maps=('source_Vpp_by_frequency','source_peak_V_by_frequency','active_source_current_RMS_by_frequency_A')
 linear_scalars=('source_Vpp_each','max_source_Vpp','sum_output_current_RMS_A_bookkeeping','contact_normal_J_RMS_max_A_m2','contact_normal_J_RMS_P95_A_m2','contact_voltage_RMS_max_V','skin_vector_J_RMS_max_A_m2','skin_vector_J_RMS_P95_A_m2')
 for key,value in e.items():
  if key in pair_keys:out[key]=_complex_pair(value,square)
  elif key=='layer_complex_power_W':out[key]=[_complex_pair(v,square)for v in value]
  elif key=='layers_power_W':out[key]={name:_number(v)*square for name,v in value.items()}
  elif key in linear_maps:out[key]={frequency:_number(v)*s for frequency,v in value.items()}
  elif key in linear_scalars:out[key]=_number(value)*s
  elif key=='source_current_RMS_by_output_A':out[key]=[_number(v)*s for v in value]
  elif key=='physical_pad_current_RMS_A':
   out[key]=[]
   for row in value:
    _require(type(row['physical_pad_id'])is int and row['physical_pad_id']>=0,'Physical pad IDs preserved as exact integers')
    out[key].append({**copy.deepcopy(row),'current_RMS_A':_number(row['current_RMS_A'])*s})
  elif key.endswith('_power_W'):
   _require(type(value)in(int,float),'Unknown structured power needs an explicit schema, never float(dict/list)')
   out[key]=_number(value)*square
  else:out[key]=copy.deepcopy(value) # Dimensionless ratios/topology/IDs/text.
 return out


def _scaled_electrical(e, s):
    return scale_electrical(e, s)
