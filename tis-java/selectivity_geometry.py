"""Read-only geometry preparation for a separate fixed D50 mm phantom study.

Coordinates are mm, +z points into the phantom and the contact plane is z=0.
In a TIS candidate the first two pads are signal outputs and the last two share
ideal common GND.  An explicitly registered C1 control contains exactly one
original indexed signal/return pair, renumbered0/1; it is a real two-pad domain.
This module performs no PDE, EIS fitting, field scoring or file writes.  The
1 mm pad gap is an unvalidated manufacturing assumption, not a safety limit.

Curved boundaries are inscribed, 4096-vertex convex polygons.  Their explicit
analytic-area error is separate from polygon-to-cell area conservation.  A
Cartesian top face is intersected with a polygon, without area renormalization.
Cells use the original cylinder's centre-in-disk rule; unsupported contact area
causes rejection rather than silently being removed or moved.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np


DIAMETER_MM = 50.0
RADIUS_MM = DIAMETER_MM / 2.0
MINIMUM_GAP_MM = 1.0
CURVE_VERTICES = 4096
CURVE_AREA_RELATIVE_TOLERANCE = 1e-6
CELL_AREA_RELATIVE_TOLERANCE = 1e-10
GEOMETRY_ROUNDOFF_MM = 1e-10
MAX_SURFACE_CELLS = 800_000


def polygon_area(polygon_mm: Any) -> float:
    """Signed shoelace area in mm², translated before summation for stability."""
    p = np.asarray(polygon_mm, dtype=float)
    if len(p) < 3:
        return 0.0
    q = p - p[0]
    return float(np.sum(q[:, 0] * np.roll(q[:, 1], -1)
                        - q[:, 1] * np.roll(q[:, 0], -1)) * 0.5)


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _validated_polygon(polygon_mm: Any) -> np.ndarray:
    p = np.asarray(polygon_mm, dtype=float)
    if p.ndim != 2 or p.shape[1:] != (2,) or len(p) < 3:
        raise ValueError("polygon_mm must contain at least three XY vertices")
    if not np.all(np.isfinite(p)):
        raise ValueError("polygon_mm contains a nonfinite coordinate")
    edges = np.roll(p, -1, axis=0) - p
    if np.any(np.linalg.norm(edges, axis=1) <= 1e-13):
        raise ValueError("polygon_mm contains a repeated consecutive vertex")
    if polygon_area(p) <= 0:
        raise ValueError("polygon_mm must have positive area and CCW winding")
    if np.any(_cross(edges, np.roll(edges, -1, axis=0)) < -1e-11):
        raise ValueError("polygon_mm must be convex")
    return p


def _pad(shape: str, center: tuple[float, float], width: float, height: float,
         rotation_deg: float = 0.0, corner_radius: float = 0.0) -> dict:
    if min(width, height) <= 0 or not all(map(math.isfinite, (*center, width, height, rotation_deg))):
        raise ValueError("pad dimensions and coordinates must be finite and positive")
    if shape == "rectangle":
        local = np.array([[-width/2, -height/2], [width/2, -height/2],
                          [width/2, height/2], [-width/2, height/2]])
        analytic_area = width * height
        hausdorff = 0.0
    elif shape in ("circle", "ellipse"):
        if shape == "circle" and width != height:
            raise ValueError("circle requires equal width and height")
        theta = np.arange(CURVE_VERTICES) * (2 * math.pi / CURVE_VERTICES)
        local = np.column_stack((width/2*np.cos(theta), height/2*np.sin(theta)))
        analytic_area = math.pi * width * height / 4
        hausdorff = max(width, height)/2 * (1 - math.cos(math.pi / CURVE_VERTICES))
    elif shape == "rounded_rectangle":
        r = float(corner_radius)
        if not 0 < r < min(width, height)/2:
            raise ValueError("rounded rectangle needs 0 < radius < min(width,height)/2")
        # Include both tangent endpoints of each arc.  Straight connections are
        # then exact, with no diagonal across an arc-to-straight transition.
        pieces = []
        for cx, cy, begin in ((width/2-r, -height/2+r, -math.pi/2),
                              (width/2-r, height/2-r, 0),
                              (-width/2+r, height/2-r, math.pi/2),
                              (-width/2+r, -height/2+r, math.pi)):
            theta = np.linspace(begin, begin+math.pi/2, CURVE_VERTICES//4)
            pieces.append(np.column_stack((cx+r*np.cos(theta), cy+r*np.sin(theta))))
        local = np.concatenate(pieces)
        analytic_area = width * height - (4-math.pi)*r*r
        hausdorff = r * (1-math.cos(math.pi/(4*(CURVE_VERTICES//4-1))))
    else:
        raise ValueError(f"unsupported pad shape: {shape}")
    a = math.radians(rotation_deg)
    rot = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    polygon = local @ rot.T + np.asarray(center)
    area = polygon_area(polygon)
    return {"shape": shape, "center_mm": list(center), "width_mm": width,
            "height_mm": height, "rotation_deg": rotation_deg,
            "corner_radius_mm": corner_radius, "polygon_mm": polygon.tolist(),
            "area_mm2": analytic_area, "analytic_area_mm2": analytic_area, "polygon_area_mm2": area,
            "curve_hausdorff_upper_mm": hausdorff,
            "curve_area_relative_error": abs(area/analytic_area-1)}


def _design(identifier: str, group: str, shape: str, width: float, height: float,
            radius: float = 10*math.sqrt(2), tangent: bool = False,
            corner_radius: float = 0.0, adjacent: bool = False,
            supersedes: str | None = None) -> dict:
    d = radius/math.sqrt(2)
    # Preserve the original square centres exactly, rather than sin/cos ulps.
    if radius == 10*math.sqrt(2):
        d = 10.0
    centers = [(-d, -d), (d, d), (d, -d), (-d, d)]
    if adjacent:
        centers = [(-d, -d), (d, -d), (d, d), (-d, d)]
    pads = []
    for k, center in enumerate(centers):
        angle = math.degrees(math.atan2(center[1], center[0]))+90 if tangent else 0.0
        pad = _pad(shape, center, width, height, angle, corner_radius)
        pad.update({"pad": k, "role": "signal" if k < 2 else "common_gnd_return",
                    "source_output": k if k < 2 else None,
                    "indexed_pair": k if k < 2 else k-2})
        pads.append(pad)
    result = {"id": identifier, "group": group, "pads": pads,
              "phantom_diameter_mm": DIAMETER_MM,
              "contact_plane_z_mm": 0.0,
              "source_outputs": 2, "total_pads": 4,
              "return_connection": "all_return_pads_ideal_common_GND",
              "minimum_gap_mm": MINIMUM_GAP_MM,
              "minimum_gap_status": "unvalidated_manufacturing_assumption_not_safety",
              "geometry_revision": "feasibility_revised_before_registration"}
    if supersedes:
        result["supersedes_rejected_proposal_id"] = supersedes
    return result


def designs() -> list[dict]:
    """Ten explicit candidates; feasibility changes remain separate proposals.

    These are geometry inputs, not executed or converged simulation results.
    All equal-area pads have ideal area225 mm² each.  Radius changes in free
    layouts are explicit variables and do not establish electrical improvement.
    """
    eh = 900/(math.pi*24)
    rh = (225+(4-math.pi)*9)/18
    return [
        _design("baseline-square15", "equal_area_225mm2", "rectangle", 15, 15),
        _design("equal-circle225", "equal_area_225mm2", "circle",
                2*math.sqrt(225/math.pi), 2*math.sqrt(225/math.pi)),
        _design("equal-ellipse24", "equal_area_225mm2", "ellipse", 24, eh, tangent=True),
        _design("equal-rectangle17p5", "equal_area_225mm2", "rectangle", 17.5, 225/17.5,
                supersedes="proposal-rectangle25x9-tangent"),
        _design("equal-rounded18-r3", "equal_area_225mm2", "rounded_rectangle", 18, rh,
                corner_radius=3, supersedes="proposal-rounded25-r3-tangent"),
        _design("free-ellipse24-r17", "free_area_and_position", "ellipse", 24, eh,
                radius=17, tangent=True),
        _design("free-square10-r12p5xy", "free_area_and_position", "rectangle", 10, 10,
                radius=12.5*math.sqrt(2)),
        _design("free-rectangle22x8-r17p5", "free_area_and_position", "rectangle", 22, 8,
                radius=17.5, tangent=True, supersedes="proposal-rectangle28x6-r17-tangent"),
        _design("free-circle12-r18p5", "free_area_and_position", "circle", 12, 12,
                radius=18.5),
        _design("adjacent-square15", "connection_control", "rectangle", 15, 15, adjacent=True),
    ]


def proposed_rejections() -> list[dict]:
    """Original unmodified proposals retained for explicit feasibility audit."""
    return [
        _design("proposal-rectangle25x9-tangent", "original_proposal_preserved", "rectangle",
                25, 9, tangent=True),
        _design("proposal-rounded25-r3-tangent", "original_proposal_preserved", "rounded_rectangle",
                25, (225+(4-math.pi)*9)/25, tangent=True, corner_radius=3),
        _design("proposal-rectangle28x6-r17-tangent", "original_proposal_preserved", "rectangle",
                28, 6, radius=17, tangent=True),
    ]


def clip_polygon_to_cell(polygon_mm: Any, x0: float, x1: float,
                         y0: float, y1: float) -> np.ndarray:
    """Convex polygon/axis-aligned closed-cell intersection in original mm.

    Sutherland-Hodgman clipping uses actual intersections, not raster sampling.
    Inputs from public mask() are already validated; this low-level helper also
    accepts an empty intermediate polygon.  No coordinate snapping is applied.
    """
    if not all(map(math.isfinite, (x0, x1, y0, y1))) or not (x0 < x1 and y0 < y1):
        raise ValueError("cell bounds must be finite and ordered")
    p = np.asarray(polygon_mm, dtype=float).reshape((-1, 2))
    for axis, bound, sign in ((0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1)):
        if len(p) == 0:
            break
        inside = sign*(p[:, axis]-bound) >= 0
        if np.all(inside):
            continue
        following = np.roll(p, -1, axis=0)
        crossing = inside != np.roll(inside, -1)
        counts = inside.astype(np.int64)+crossing.astype(np.int64)
        offsets = np.cumsum(counts)-counts
        result = np.empty((int(counts.sum()), 2))
        result[offsets[inside]] = p[inside]
        if np.any(crossing):
            start = p[crossing]
            diff = following[crossing]-start
            fractions = (bound-start[:, axis])/diff[:, axis]
            intersections = start+fractions[:, None]*diff
            intersections[:, axis] = bound
            result[offsets[crossing]+inside[crossing]] = intersections
        p = result
    return p


def _points_in_convex(polygon: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Vectorized fan search, O(points log vertices); strict roundoff goes to clip."""
    v = polygon-polygon[0]
    p = np.asarray(points)-polygon[0]
    support = (_cross(v[1], p) >= 0) & (_cross(v[-1], p) <= 0)
    lo = np.ones(len(p), dtype=np.int64)
    hi = np.full(len(p), len(v)-1, dtype=np.int64)
    while np.any(hi-lo > 1):
        mid = (hi+lo)//2
        left = _cross(v[mid], p) >= 0
        active = hi-lo > 1
        lo = np.where(active & left, mid, lo)
        hi = np.where(active & ~left, mid, hi)
    support &= _cross(v[hi]-v[lo], p-v[lo]) >= 0
    return support


def polygon_gap_mm(polygon_a: Any, polygon_b: Any) -> float:
    """Euclidean separation of convex polygons; overlaps/touches return zero.

    The origin's distance from A+(-B) gives the polygon distance.  Sorting the
    edge angles constructs the Minkowski boundary in O((n+m)log(n+m)), avoiding
    quadratic work on the 4096-vertex curved contacts.
    """
    a = _validated_polygon(polygon_a)
    b = -_validated_polygon(polygon_b)
    a = np.roll(a, -int(np.lexsort((a[:, 0], a[:, 1]))[0]), axis=0)
    b = np.roll(b, -int(np.lexsort((b[:, 0], b[:, 1]))[0]), axis=0)
    edges = np.concatenate((np.roll(a, -1, axis=0)-a, np.roll(b, -1, axis=0)-b))
    angles = np.mod(np.arctan2(edges[:, 1], edges[:, 0]), 2*math.pi)
    edges = edges[np.argsort(angles, kind="stable")]
    start = a[0]+b[0]
    vertices = np.vstack((start, start+np.cumsum(edges, axis=0)[:-1]))
    following = np.roll(vertices, -1, axis=0)
    edges = following-vertices
    lengths_sq = np.einsum("ij,ij->i", edges, edges)
    good = lengths_sq > 1e-26
    if np.all(_cross(edges[good], -vertices[good]) >= -1e-10):
        return 0.0
    t = np.clip(-np.einsum("ij,ij->i", vertices[good], edges[good])/lengths_sq[good], 0, 1)
    nearest = vertices[good]+t[:, None]*edges[good]
    return float(np.min(np.linalg.norm(nearest, axis=1)))


def _design_scope(design: dict) -> dict:
    """Restrict C1 geometry to an exact indexed subset of a registered candidate.

    The original pad's intrinsic geometry must match byte-representable values;
    only its local pad index/circuit/provenance labels may differ.  This does not
    create a four-pad model with an inactive output, or infer a return-current
    path in the original common-GND TIS circuit.
    """
    pads = design["pads"]
    count = len(pads)
    if count not in (2, 4):
        raise ValueError("finite geometry scope requires either four TIS pads or an exact two-pad C1 subset")
    channels = count//2
    if (design.get("source_outputs", channels) != channels
            or design.get("total_pads", count) != count
            or design.get("channels", channels) != channels):
        raise ValueError("source_outputs/channels/total_pads disagree with the physical pad count")
    if [pad.get("pad") for pad in pads] != list(range(count)):
        raise ValueError("physical pads must be renumbered consecutively from zero")
    if [pad.get("role") for pad in pads] != (["signal"]*channels+["common_gnd_return"]*channels):
        raise ValueError("pad roles must explicitly retain signal then common-GND return order")
    scope = {"source_outputs": channels, "total_pads": count,
             "physical_control_scope": "four_pad_TIS" if count == 4 else "actual_two_pad_single_output"}
    if count == 4:
        return scope
    source_id = design.get("control_for_design")
    pair = design.get("indexed_pair")
    if type(pair) is not int or pair not in (0, 1):
        raise ValueError("C1 indexed_pair must be exactly0 or1")
    originals = {d["id"]: d for d in designs()}
    if source_id not in originals:
        raise ValueError("C1 control_for_design must name an exact registered candidate")
    if design.get("id") != source_id+f"-C1pair{pair}":
        raise ValueError("C1 id must retain its source design and indexed pair")
    intrinsic = ("shape", "center_mm", "width_mm", "height_mm", "rotation_deg",
                 "corner_radius_mm", "polygon_mm", "area_mm2", "analytic_area_mm2",
                 "polygon_area_mm2", "curve_hausdorff_upper_mm", "curve_area_relative_error")
    selected_indices = (pair, pair+2)
    for actual, original_index in zip(pads, selected_indices):
        original = originals[source_id]["pads"][original_index]
        if any(actual.get(key) != original[key] for key in intrinsic):
            raise ValueError("C1 pads must remain an exact indexed signal/return geometry subset")
    scope.update(control_for_design=source_id, indexed_pair=pair,
                 original_pad_indices=list(selected_indices),
                 common_GND_pairing_rule="finite indexed comparison, not an original unique return-current path")
    return scope


def validate_design(design: dict) -> dict:
    """Return detailed feasibility without moving, resizing or deleting pads."""
    if float(design.get("phantom_diameter_mm", DIAMETER_MM)) != DIAMETER_MM:
        raise ValueError("fixed phantom must retain diameter50 mm")
    scope = _design_scope(design)
    pads = design["pads"]
    reasons: list[str] = []
    pad_info = []
    polygons = []
    for index, pad in enumerate(pads):
        p = _validated_polygon(pad["polygon_mm"])
        polygons.append(p)
        area = polygon_area(p)
        analytic = float(pad["analytic_area_mm2"])
        bound = float(pad["curve_hausdorff_upper_mm"])
        if not math.isfinite(analytic) or analytic <= 0 or not math.isfinite(bound) or bound < 0:
            raise ValueError("pad analytic area and curve bound must be finite and valid")
        area_error = abs(area/analytic-1)
        rmax = float(np.max(np.linalg.norm(p, axis=1)))
        rmax_upper = rmax+bound
        if area_error >= CURVE_AREA_RELATIVE_TOLERANCE:
            reasons.append(f"pad{index}: curve_area_relative_error_exceeds_1e-6")
        if rmax_upper > RADIUS_MM+GEOMETRY_ROUNDOFF_MM:
            reasons.append(f"pad{index}: entire_pad_not_inside_radius25mm")
        pad_info.append({"pad": index, "shape": pad["shape"],
                         "analytic_area_mm2": analytic, "polygon_area_mm2": area,
                         "curve_area_relative_error": area_error,
                         "vertices": len(p), "curve_hausdorff_upper_mm": bound,
                         "rmax_polygon_mm": rmax, "rmax_upper_mm": rmax_upper})
    gaps = []
    for a in range(len(pads)):
        for b in range(a+1, len(pads)):
            poly_gap = polygon_gap_mm(polygons[a], polygons[b])
            lower = max(0.0, poly_gap-pad_info[a]["curve_hausdorff_upper_mm"]
                        -pad_info[b]["curve_hausdorff_upper_mm"])
            gaps.append({"pads": [a, b], "polygon_gap_mm": poly_gap,
                         "ideal_curve_gap_lower_mm": lower,
                         "ideal_curve_gap_upper_mm": poly_gap})
            if lower < MINIMUM_GAP_MM-GEOMETRY_ROUNDOFF_MM:
                reasons.append(f"pads{a},{b}: minimum_gap_below_1mm")
    return {"id": design["id"], **scope, "status": "valid_geometry" if not reasons else "rejected_geometry",
            "rejection_reasons": reasons, "pads": pad_info, "gaps": gaps,
            "minimum_gap_lower_mm": min(g["ideal_curve_gap_lower_mm"] for g in gaps),
            "rmax_upper_mm": max(p["rmax_upper_mm"] for p in pad_info),
            "minimum_gap_assumption": "1mm_unvalidated_manufacturing_assumption_not_safety",
            "curve_polygon_vertices": CURVE_VERTICES,
            "curve_area_relative_tolerance": CURVE_AREA_RELATIVE_TOLERANCE,
            "no_PDE_or_electrical_validation": True}


def mask(design: dict, h: float) -> dict:
    """Clip every pad to supported top faces at spacing h (mm).

    Returns contacts sorted by pad,j,i, with area_m2.  Grid origin is (-25,-25)
    mm; i is x, j is y; cylinder support uses cell centres x²+y²<25², as in the
    original solver.  The caller must separately enforce the actual 3D800k cap.
    Invalid geometry is retained as rejected metadata, with no contacts.
    """
    h = float(h)
    if not math.isfinite(h) or h <= 0:
        raise ValueError("h must be finite positive millimetres")
    nx = round(DIAMETER_MM/h)
    if nx < 1 or abs(nx*h-DIAMETER_MM) > 1e-10 or nx*nx > MAX_SURFACE_CELLS:
        raise ValueError("h must tile fixed50mm width within the surface allocation cap")
    checked = validate_design(design)
    result = {**checked, "h_mm": h, "nx": nx, "ny": nx,
              "grid_origin_mm": [-RADIUS_MM, -RADIUS_MM],
              "cell_support_rule": "centre_x_squared_plus_y_squared_strictly_less_than_25mm_squared",
              "contact_area_rule": "convex_polygon_intersection_with_full_top_face_no_renormalization",
              "contact_order": "pad_then_j_then_i", "contacts": [], "areas": [],
              "expected_pad_areas_m2": [polygon_area(p["polygon_mm"])*1e-6 for p in design["pads"]],
              "analytic_pad_areas_m2": [float(p["analytic_area_mm2"])*1e-6 for p in design["pads"]],
              "cell_area_relative_tolerance": CELL_AREA_RELATIVE_TOLERANCE,
              "actual_3D_cell_cap_checked": False}
    axis = -RADIUS_MM+(np.arange(nx)+0.5)*h
    result["active_surface_cells"] = int(np.count_nonzero(axis[:, None]**2+axis[None, :]**2 < RADIUS_MM**2))
    if checked["status"] != "valid_geometry":
        return result
    contacts = []
    for k, pad in enumerate(design["pads"]):
        p = _validated_polygon(pad["polygon_mm"])
        imin = max(0, math.floor((float(p[:, 0].min())+RADIUS_MM)/h))
        imax = min(nx-1, math.floor((float(p[:, 0].max())+RADIUS_MM)/h))
        jmin = max(0, math.floor((float(p[:, 1].min())+RADIUS_MM)/h))
        jmax = min(nx-1, math.floor((float(p[:, 1].max())+RADIUS_MM)/h))
        ij = [(i, j) for j in range(jmin, jmax+1) for i in range(imin, imax+1)]
        corners = np.asarray([[-RADIUS_MM+i*h, -RADIUS_MM+j*h] for i, j in ij])
        quads = corners[:, None, :]+np.asarray([[0, 0], [h, 0], [h, h], [0, h]])
        full = _points_in_convex(p, quads.reshape((-1, 2))).reshape((-1, 4)).all(axis=1)
        areas = []
        unsupported = []
        for index, (i, j) in enumerate(ij):
            if full[index]:
                area = h*h
            else:
                x, y = corners[index]
                area = max(0.0, polygon_area(clip_polygon_to_cell(p, x, x+h, y, y+h)))
            if area == 0:
                continue
            if axis[i]**2+axis[j]**2 >= RADIUS_MM**2:
                unsupported.append(area)
                continue
            areas.append(area)
            contacts.append({"pad": k, "i": i, "j": j, "area_m2": area*1e-6})
        polygon_expected = polygon_area(p)
        total = math.fsum(areas)
        unsupported_area = math.fsum(unsupported)
        err = abs(total/polygon_expected-1)
        idealerr = abs(total/float(pad["analytic_area_mm2"])-1)
        result["areas"].append({"pad": k, "polygon_area_mm2": polygon_expected,
                                "analytic_area_mm2": pad["analytic_area_mm2"],
                                "represented_area_mm2": total,
                                "represented_area_m2": total*1e-6,
                                "unsupported_area_mm2": unsupported_area,
                                "relative_error_to_polygon": err,
                                "relative_error_to_analytic": idealerr})
        if err > CELL_AREA_RELATIVE_TOLERANCE:
            result["rejection_reasons"].append(f"pad{k}: contact_mask_area_not_conserved")
    result["contacts"] = contacts
    result["total_contact_area_m2"] = math.fsum(row["area_m2"] for row in contacts)
    result["status"] = "valid_contact_mask" if not result["rejection_reasons"] else "rejected_geometry"
    return result
