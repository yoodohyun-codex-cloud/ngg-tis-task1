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

