"""Native-cell, volume-weighted electrical selectivity (pure postprocessing).

Inputs are actual peak/+jωt complex E, already summed coherently at each real
frequency. No PDE, source scaling, neural threshold, or interpolation is done.
The represented domain is exactly the existing FVM cylinder mask (whole square
cells). Only the r<=5 mm target uses fractional XY overlap; z overlap is exact.
Stored native E is treated as constant inside each finite volume. Thus native
sample maxima and finite sampled direction maxima are not continuum maxima.
"""
from __future__ import annotations

import math
import time
from typing import Mapping

import numpy as np

# Unused direction helper import omitted for portable native_region_weights.


LAYER_FACES_MM = np.array([0.0, 0.1, 5.1, 10.1, 25.1])
REGIONS = ("total", "target", "surface_0_5", "subsurface_5_10", "remaining", "off_target")
TARGET_SUBDIVISIONS = 128


class VolumeAnalysisError(ValueError):
    """Incomplete source, geometry, or numerical input; never silently skipped."""


class VolumeDeadlineExceeded(TimeoutError):
    """Caller must preserve this incomplete postprocessing rather than retry."""


def _check_deadline(deadline, processed_cells=0):
    if deadline is not None and time.monotonic() >= deadline:
        raise VolumeDeadlineExceeded(f"Volume deadline exceeded after {processed_cells} cells")


def _column(grid, name):
    try:
        values = np.asarray(grid[name], dtype=float)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise VolumeAnalysisError(f"Missing/invalid native grid column: {name}") from exc
    if values.ndim != 1 or not np.isfinite(values).all():
        raise VolumeAnalysisError(f"Nonfinite/non-vector grid column: {name}")
    return values


def _overlap(lo, hi, a, b):
    return np.maximum(0.0, np.minimum(hi, b)-np.maximum(lo, a))


def _disk_fractions(xy, h, radius=5.0, subdivisions=TARGET_SUBDIVISIONS):
    """128² midpoint subcells at boundary squares only; no E resampling."""
    half = h/2
    minimum_r2 = np.sum(np.maximum(np.abs(xy)-half, 0)**2, axis=1)
    maximum_r2 = np.sum((np.abs(xy)+half)**2, axis=1)
    fractions = np.zeros(len(xy))
    fractions[maximum_r2 <= radius*radius] = 1.0
    boundary = (minimum_r2 < radius*radius) & (maximum_r2 > radius*radius)
    offsets = ((np.arange(subdivisions)+0.5)/subdivisions-0.5)*h
    ox, oy = np.meshgrid(offsets, offsets, indexing="xy")
    for index in np.flatnonzero(boundary):
        fractions[index] = np.count_nonzero((xy[index, 0]+ox)**2 +
                                           (xy[index, 1]+oy)**2 <= radius*radius)/subdivisions**2
    return fractions, int(np.count_nonzero(boundary))


def native_region_weights(grid, meta, *, deadline_monotonic=None):
    """Return m³ region weights and an auditable, unnormalized geometry receipt.

    Required metadata: h_xy_mm, actual z_faces_mm and layer_counts, radius_mm=25,
    geometry_volume_tolerance_relative (predeclared coarse .01/fine .002).
    target_volume_tolerance_relative defaults to the predeclared .001. The
    function validates the complete z×XY mask, cell volumes and tissue IDs.
    """
    _check_deadline(deadline_monotonic)
    x, y, z, layer, volume = [_column(grid, key) for key in
                              ("x_mm", "y_mm", "z_mm", "layer", "volume_m3")]
    n = len(x)
    if n == 0 or n > 800000 or any(len(v) != n for v in (y, z, layer, volume)):
        raise VolumeAnalysisError("Grid cell count/column lengths violate the native input contract")
    if not np.equal(layer, np.rint(layer)).all() or np.any(volume <= 0):
        raise VolumeAnalysisError("Integer tissue IDs and positive native cell volumes are required")
    try:
        h, radius = float(meta["h_xy_mm"]), float(meta["radius_mm"])
        faces = np.asarray(meta["z_faces_mm"], dtype=float)
        raw_counts = np.asarray(meta["layer_counts"], dtype=float)
        tolerance = float(meta["geometry_volume_tolerance_relative"])
        target_tolerance = float(meta.get("target_volume_tolerance_relative", .001))
    except (KeyError, TypeError, ValueError) as exc:
        raise VolumeAnalysisError("Actual mesh metadata and predeclared volume tolerance are required") from exc
    if not (math.isfinite(h) and h > 0 and radius == 25 and
            math.isfinite(tolerance) and 0 < tolerance <= .01 and
            math.isfinite(target_tolerance) and 0 < target_tolerance <= .001):
        raise VolumeAnalysisError("Invalid phantom dimensions or unsupported preregistered volume tolerances")
    if (raw_counts.shape != (4,) or not np.isfinite(raw_counts).all() or
            not np.equal(raw_counts, np.rint(raw_counts)).all() or np.any(raw_counts < 1)):
        raise VolumeAnalysisError("Four positive actual layer counts are required")
    counts = raw_counts.astype(int)
    if (faces.ndim != 1 or len(faces) != counts.sum()+1 or not np.isfinite(faces).all()
            or not np.all(np.diff(faces) > 0)):
        raise VolumeAnalysisError("Missing/nonmonotone actual z faces")
    if not np.allclose(faces[np.r_[0, np.cumsum(counts)]], LAYER_FACES_MM, rtol=0, atol=1e-9):
        raise VolumeAnalysisError("Mesh tissue interfaces disagree with the preserved phantom")
    centres = (faces[:-1]+faces[1:])/2
    dz = np.diff(faces)
    zs, iz = np.unique(z, return_inverse=True)
    if len(zs) != len(centres) or not np.allclose(zs, centres, rtol=0, atol=1e-9):
        raise VolumeAnalysisError("Native z centres do not reproduce the actual z-face metadata")
    expected_layers = np.repeat(np.arange(4), counts)
    if not np.array_equal(layer.astype(int), expected_layers[iz]):
        raise VolumeAnalysisError("Tissue ID does not match the actual z layer")
    nx = round(2*radius/h)
    if nx < 2 or not math.isclose(nx*h, 2*radius, rel_tol=0, abs_tol=1e-9):
        raise VolumeAnalysisError("Native XY spacing does not tile the phantom bounding square")
    axis = -radius+(np.arange(nx)+.5)*h
    ix, iy = np.rint((x-axis[0])/h).astype(int), np.rint((y-axis[0])/h).astype(int)
    if (np.any(ix < 0) or np.any(ix >= nx) or np.any(iy < 0) or np.any(iy >= nx)
            or not np.allclose(x, axis[ix], rtol=0, atol=1e-9)
            or not np.allclose(y, axis[iy], rtol=0, atol=1e-9)):
        raise VolumeAnalysisError("Grid XY coordinates disagree with the actual FVM lattice")
    gy, gx = np.meshgrid(axis, axis, indexing="ij")
    expected_xy_ids = np.flatnonzero((gx*gx+gy*gy < radius*radius).ravel())
    xy_ids = iy*nx+ix
    expected_n = len(expected_xy_ids)*len(zs)
    ids = iz*nx*nx+xy_ids
    if (n != expected_n or len(np.unique(ids)) != n or
            not np.isin(xy_ids, expected_xy_ids).all()):
        raise VolumeAnalysisError("Incomplete/duplicated native FVM cylinder mask")
    expected_volume = h*h*dz[iz]*1e-9
    if not np.allclose(volume, expected_volume, rtol=2e-10, atol=1e-20):
        raise VolumeAnalysisError("Native cell volumes do not match h² times actual dz")
    unique_xy = np.column_stack((gx.ravel()[expected_xy_ids], gy.ravel()[expected_xy_ids]))
    fractions, boundary_count = _disk_fractions(unique_xy, h)
    lookup = np.zeros(nx*nx)
    lookup[expected_xy_ids] = fractions
    # CSV volume_m3 is printed at 12 significant digits. Use the checked actual
    # h²dz geometry consistently for partition arithmetic, not its rounded CSV.
    total = expected_volume.copy()
    target = h*h*lookup[xy_ids]*_overlap(faces[iz], faces[iz+1], 15, 20)*1e-9
    surface = h*h*_overlap(faces[iz], faces[iz+1], 0, 5)*1e-9
    subsurface = h*h*_overlap(faces[iz], faces[iz+1], 5, 10)*1e-9
    remaining = total-surface-subsurface-target
    rounding_bound = 64*np.finfo(float).eps*total
    if np.any(remaining < -rounding_bound):
        raise VolumeAnalysisError("Overlapping regions produced negative off-target remainder")
    remaining = np.maximum(remaining, 0.0)  # arithmetic roundoff only, bound above
    weights = dict(total=total, target=target, surface_0_5=surface,
                   subsurface_5_10=subsurface, remaining=remaining,
                   off_target=total-target)
    analytic_total = math.pi*radius**2*(LAYER_FACES_MM[-1]-LAYER_FACES_MM[0])*1e-9
    analytic_target = math.pi*5**2*5*1e-9
    domain_error = float(total.sum()/analytic_total-1)
    target_error = float(target.sum()/analytic_target-1)
    if abs(domain_error) > tolerance:
        raise VolumeAnalysisError(f"Represented FVM volume deviation {domain_error:.12g} exceeds {tolerance}")
    if abs(target_error) > target_tolerance:
        raise VolumeAnalysisError(f"Target overlap volume deviation {target_error:.12g} exceeds {target_tolerance}")
    partition_error = float(np.max(abs(total-(surface+subsurface+remaining+target))/total))
    if partition_error > 128*np.finfo(float).eps:
        raise VolumeAnalysisError("Target plus disjoint non-target slabs do not partition the source cells")
    receipt = dict(domain_definition="source FVM whole-square centre-inside-cylinder mask; no outer-wall clipping",
                   field_integration="native cell-constant E; fractional target XY area and exact z overlap",
                   target_definition="r<=5mm and surface-depth 15<=z<=20mm",
                   region_definitions=dict(surface_0_5="0<=z<5mm", subsurface_5_10="5<=z<10mm",
                                           remaining="10<=z<=25.1mm excluding target", off_target="all cells excluding target"),
                   coordinate_system=dict(surface_z_mm=0, depth_axis="+z", xy="local phantom axes, no anatomical registration"),
                   layer_faces_mm=LAYER_FACES_MM.tolist(), layer_counts=counts.tolist(),
                   cells=n, xy_cells=len(expected_xy_ids), h_xy_mm=h,
                   target_xy_boundary_cells=boundary_count, target_boundary_subdivisions=TARGET_SUBDIVISIONS,
                   analytic_cylinder_volume_m3=analytic_total, represented_domain_volume_m3=float(total.sum()),
                   domain_relative_volume_deviation=domain_error, domain_relative_volume_tolerance=tolerance,
                   analytic_target_volume_m3=analytic_target, represented_target_volume_m3=float(target.sum()),
                   target_relative_volume_deviation=target_error, target_relative_volume_tolerance=target_tolerance,
                   max_relative_partition_roundoff=partition_error,
                   source_csv_volume_relative_rounding=float(volume.sum()/total.sum()-1),
                   renormalized_to_analytic_volume=False,
                   target_boundary_cell_centres_can_be_outside_ROI=True,
                   region_volumes_m3={key: float(value.sum()) for key, value in weights.items()})
    _check_deadline(deadline_monotonic)
    return weights, receipt


def weighted_statistics(values, weights):
    """Inverse weighted ECDF, including values exactly on percentile thresholds."""
    values, weights = np.asarray(values, float), np.asarray(weights, float)
    if (values.ndim != 1 or values.shape != weights.shape or not np.isfinite(values).all()
            or not np.isfinite(weights).all() or np.any(weights < 0)):
        raise VolumeAnalysisError("Finite scalar values and nonnegative complete volume weights are required")
    use = weights > 0
    if not np.any(use):
        raise VolumeAnalysisError("A required region has no represented positive volume")
    v, w = values[use], weights[use]
    order = np.argsort(v, kind="stable")
    cumulative = np.cumsum(w[order])
    result = dict(min=float(v.min()), max=float(v.max()), mean=float(v@w/w.sum()),
                  volume_m3=float(w.sum()), positive_weight_cells=int(use.sum()),
                  maximum_scope="native cell-constant represented samples; not continuum maximum")
    for key, fraction in (("p10", .1), ("p50", .5), ("p95", .95)):
        result[key] = float(v[order[min(int(np.searchsorted(cumulative, fraction*cumulative[-1], side="left")), len(v)-1)]])
    return result


def _threshold_metadata(thresholds):
    result = {}
    for name, entry in (thresholds or {}).items():
        entry = dict(entry) if isinstance(entry, Mapping) else {"value_V_m": entry}
        value = float(entry["value_V_m"])
        if not math.isfinite(value) or value <= 0:
            raise VolumeAnalysisError("Frozen relative high-modulation thresholds must be finite and positive")
        result[str(name)] = {**entry, "value_V_m": value,
                             "interpretation": "baseline-relative electrical comparison; not activation/safety threshold"}
    return result


def evaluate_volume(spectra, grid, meta, *, fundamental_frequencies_Hz=None,
                    fixed_direction=(1/math.sqrt(2), 1/math.sqrt(2), 0),
                    region_weights=None, thresholds=None, fibonacci_count=2048,
                    chunk_cells=256, deadline_monotonic=None):
    """Score every source native cell, returning JSON metrics plus NumPy arrays.

    spectra: {actual_integer_Hz: complex[N,3] peak V/m}; all source coefficients
    and phases must already be applied/coherently summed. Fundamentals are an
    explicit pair, harmonics contribute to actual total RMS only. An optional
    region_weights cache must exactly reproduce this source-grid geometry.
    A caller's monotonic deadline is checked between bounded chunks; no retry.
    No file writes and no mutation of any supplied array or metadata occur.
    """
    started = time.monotonic()
    _check_deadline(deadline_monotonic)
    frozen = _threshold_metadata(thresholds)
    if not isinstance(fibonacci_count, int) or fibonacci_count < 1:
        raise VolumeAnalysisError("Positive explicit Fibonacci direction count required")
    if not isinstance(chunk_cells, int) or not 1 <= chunk_cells <= 1024:
        raise VolumeAnalysisError("Predeclared bounded direction chunk must contain 1..1024 cells")
    weights, geometry = native_region_weights(grid, meta, deadline_monotonic=deadline_monotonic)
    n = geometry["cells"]
    if region_weights is not None:
        if set(region_weights) != set(REGIONS):
            raise VolumeAnalysisError("Cached region weights must contain the complete disjoint-region contract")
        for key in REGIONS:
            cached = np.asarray(region_weights[key], float)
            if cached.shape != (n,) or not np.array_equal(cached, weights[key]):
                raise VolumeAnalysisError(f"Cached volume weights mismatch actual source geometry: {key}")
    pair = fundamental_frequencies_Hz or meta.get("fundamental_frequencies_Hz")
    if pair is None or len(pair) != 2:
        raise VolumeAnalysisError("The actual two fundamental frequencies must be explicit")
    if any(not isinstance(f, (int, np.integer)) or f <= 0 for f in pair) or pair[0] == pair[1]:
        raise VolumeAnalysisError("Two distinct positive integer-Hz fundamentals are required")
    spectra_copy = {}
    for f, values in spectra.items():
        if not isinstance(f, (int, np.integer)) or f <= 0:
            raise VolumeAnalysisError("Spectrum keys must be actual positive integer-Hz frequencies")
        array = np.asarray(values)
        if array.shape != (n, 3) or not np.issubdtype(array.dtype, np.complexfloating) or not np.isfinite(array).all():
            raise VolumeAnalysisError(f"Incomplete/nonfinite native complex vector field at {f} Hz")
        spectra_copy[int(f)] = array
    if not all(f in spectra_copy for f in pair):
        raise VolumeAnalysisError("Both fundamental complex fields are required; no inferred missing carrier")
    direction = np.asarray(fixed_direction, float)
    if direction.shape != (3,) or not np.isfinite(direction).all() or not math.isclose(float(np.linalg.norm(direction)), 1, rel_tol=0, abs_tol=1e-12):
        raise VolumeAnalysisError("Fixed physical direction must be an explicit finite unit vector")
    dirs = directions(fibonacci_count)
    a, b = spectra_copy[int(pair[0])], spectra_copy[int(pair[1])]
    squared_rms = np.zeros(n)
    for field in spectra_copy.values():
        squared_rms += np.sum(np.abs(field)**2, axis=1)/2
    rms = np.sqrt(squared_rms)
    if not np.isfinite(rms).all():
        raise VolumeAnalysisError("Native spectrum magnitudes overflowed the actual total RMS calculation")
    af, bf = np.abs(a@direction), np.abs(b@direction)
    fixed = 2*np.minimum(af, bf)
    largest = np.maximum(af, bf)
    depth = np.divide(np.minimum(af, bf), largest, out=np.zeros(n), where=largest > 0)
    maximum, winner = np.zeros(n), np.zeros(n, dtype=np.int32)
    if np.any(a) and np.any(b):
        for start in range(0, n, chunk_cells):
            _check_deadline(deadline_monotonic, start)
            stop = min(n, start+chunk_cells)
            # Two bounded complex products only; never allocate N×2074.
            projected_a = np.abs(a[start:stop]@dirs.T)
            projected_b = np.abs(b[start:stop]@dirs.T)
            np.minimum(projected_a, projected_b, out=projected_a)
            winner[start:stop] = np.argmax(projected_a, axis=1)
            maximum[start:stop] = 2*projected_a[np.arange(stop-start), winner[start:stop]]
    _check_deadline(deadline_monotonic, n)
    upper = 2*np.minimum(np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1))
    bound_roundoff = 256*np.finfo(float).eps*np.maximum(rms, upper)
    if np.any(maximum > upper+bound_roundoff) or np.any(maximum > 2*rms+bound_roundoff):
        raise VolumeAnalysisError("Sampled directional modulation violates analytic field upper bound")
    axis_tis = 2*np.minimum(np.abs(a), np.abs(b))
    scalars = dict(maxTIS=maximum, fixedTIS=fixed, RMS=rms,
                   maxTIS_direction_index=winner, directional_upper_bound=upper,
                   fixed_carrier0_peak=af, fixed_carrier1_peak=bf,
                   fixed_modulation_depth=depth, fixed_modulation_depth_defined=largest > 0,
                   X_TIS=axis_tis[:, 0], Y_TIS=axis_tis[:, 1], Z_TIS=axis_tis[:, 2])
    region_metrics = {}
    layer = _column(grid, "layer").astype(int)
    for region, w in weights.items():
        _check_deadline(deadline_monotonic, n)
        statistics = {key: weighted_statistics(scalars[key], w)
                      for key in ("maxTIS", "fixedTIS", "RMS", "X_TIS", "Y_TIS", "Z_TIS")}
        high = {}
        for name, threshold in frozen.items():
            high[name] = {}
            for key in ("maxTIS", "fixedTIS"):
                volume = float(w[scalars[key] >= threshold["value_V_m"]].sum())
                high[name][key] = dict(volume_m3=volume, volume_mm3=volume*1e9,
                                       fraction=volume/float(w.sum()), comparison_operator=">=")
        strata = {}
        for tissue in range(4):
            use = (layer == tissue) & (w > 0)
            if np.any(use):
                strata[str(tissue)] = {key: weighted_statistics(scalars[key][use], w[use])
                                      for key in ("maxTIS", "fixedTIS", "RMS")}
        region_metrics[region] = dict(statistics=statistics, high_modulation_volume=high,
                                     tissue_volumes_m3={str(i): float(w[layer == i].sum()) for i in range(4)},
                                     tissue_statistics=strata)
    ratios = {}
    for metric in ("maxTIS", "fixedTIS", "RMS"):
        target = region_metrics["target"]["statistics"][metric]
        ratios[metric] = {}
        for region in ("surface_0_5", "subsurface_5_10", "remaining", "off_target"):
            other = region_metrics[region]["statistics"][metric]
            ratios[metric][region] = {
                "target_mean_over_off_p95": target["mean"]/other["p95"] if other["p95"] > 0 else None,
                "target_p10_over_off_p95": target["p10"]/other["p95"] if other["p95"] > 0 else None,
                "target_mean_over_off_max": target["mean"]/other["max"] if other["max"] > 0 else None}
    metrics = dict(schema_version=1, status="complete", geometry=geometry,
                   units=dict(E="V/m", volume="m3", GUI_E="V/cm = V/m×0.01"),
                   conventions=dict(phasor="peak, +jomega_t", same_frequency="input spectra already coherently summed",
                                    actual_RMS="sqrt(sum_f ||complex E_f||²/2), including actual harmonics",
                                    maxTIS="max over finite sampled n of 2min(|n·E_f0|,|n·E_f1|)",
                                    finite_direction_scope="lower bound on angular maximum at each native cell; not one axon path",
                                    fixedTIS="2min(|n_fixed·E_f0|,|n_fixed·E_f1|)",
                                    fixed_modulation_depth="min(carrier projection magnitudes)/max; undefined for two zero projections",
                                    weighted_quantile="first ascending value reaching requested cumulative volume (inverse ECDF)",
                                    biological_status="electrical proxies only, no recruitment/force/safety inference"),
                   frequencies_Hz=sorted(spectra_copy), fundamental_frequencies_Hz=[int(f) for f in pair],
                   fixed_direction=direction.tolist(), fibonacci_count=fibonacci_count,
                   total_sampled_directions=len(dirs), chunk_cells=chunk_cells,
                   thresholds=frozen, regions=region_metrics, ratios=ratios,
                   normal_current_interface_validation="separate source face-flux/phi-E gate, not inferred from volume E",
                   runtime_seconds=time.monotonic()-started,
                   source_provenance=dict(meta.get("source_provenance", {})))
    return dict(metrics=metrics, scalars=scalars, region_weights_m3=weights,
                spectra=spectra_copy, sampled_directions=dirs)
