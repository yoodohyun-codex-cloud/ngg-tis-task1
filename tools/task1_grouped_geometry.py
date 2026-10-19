#!/usr/bin/env python3
"""Prepare a finite grouped-pad geometry family; no solver or research imports.

Original four-square geometry is a separate control. The strip family has an
additional four-rectangle control, avoiding attribution of a geometry change to
pad count alone. Each of four electrical parent groups retains225mm2 contact.
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE_CONFIG = ROOT / "tis-java/runs/selectivity-design-20261019T155933Z/configs/baseline-square15-xy80.properties"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rectangles(n_pads, *, center_x_mm=10.7, center_y_mm=7.0, height_mm=13.0, gap_mm=1.0):
    if n_pads not in (4, 8, 12, 16):
        raise ValueError("physical pads must be4/8/12/16; independent outputs stay2")
    if min(center_x_mm, center_y_mm, height_mm) <= 0 or gap_mm < 0:
        raise ValueError("positive dimensions and nonnegative strip gap required")
    count = n_pads // 4
    width = 225 / height_mm / count
    total_width = count * width + (count - 1) * gap_mm
    parents = ((-center_x_mm, -center_y_mm, 0), (center_x_mm, center_y_mm, 1),
               (center_x_mm, -center_y_mm, -1), (-center_x_mm, center_y_mm, -1))
    result = []
    for group, (x, y, node) in enumerate(parents):
        for strip in range(count):
            result.append(dict(pad_id=group * count + strip, parent_group=group, node=node,
                shape="rectangle", width_mm=width, height_mm=height_mm,
                x_mm=x - total_width / 2 + width / 2 + strip * (width + gap_mm),
                y_mm=y, rotation_deg=0.0, attachment="top_z0", area_mm2=225 / count))
    return result


def geometry_receipt(pads, minimum_gap_mm=1.0):
    farthest = max(math.hypot(p["x_mm"] + sx * p["width_mm"] / 2,
                              p["y_mm"] + sy * p["height_mm"] / 2)
                   for p in pads for sx, sy in itertools.product((-1, 1), repeat=2))
    gap = math.inf
    for a, b in itertools.combinations(pads, 2):
        dx = abs(a["x_mm"] - b["x_mm"]) - (a["width_mm"] + b["width_mm"]) / 2
        dy = abs(a["y_mm"] - b["y_mm"]) - (a["height_mm"] + b["height_mm"]) / 2
        if dx < -1e-12 and dy < -1e-12:
            raise ValueError("physical pad rectangles overlap")
        gap = min(gap, math.hypot(max(0, dx), max(0, dy)))
    if farthest > 25 + 1e-10:
        raise ValueError(f"physical rectangle outside D50: farthest corner{farthest:.9f}mm")
    if gap < minimum_gap_mm - 1e-10:
        raise ValueError(f"minimum physical gap{gap:.9f}mm below{minimum_gap_mm}mm")
    return dict(analytic_total_area_mm2=sum(p["area_mm2"] for p in pads),
                farthest_corner_radius_mm=farthest, minimum_pad_gap_mm=gap,
                geometry_status="analytic_rectangles_inside_D50_nonoverlapping",
                convergence_status="not_tested")


def mask_rows(pads, h_mm):
    if not math.isfinite(h_mm) or h_mm <= 0 or abs(round(50 / h_mm) * h_mm - 50) > 1e-10:
        raise ValueError("XY spacing must tile50mm exactly")
    count = round(50 / h_mm)
    if count > 120:
        raise ValueError("unregistered XY grid above120 cells across diameter")
    rows, represented, covered = [], [0.0] * len(pads), {}
    for pad in pads:
        for j in range(count):
            y = -25 + (j + .5) * h_mm
            overlap_y = max(0, min(y + h_mm / 2, pad["y_mm"] + pad["height_mm"] / 2) -
                                  max(y - h_mm / 2, pad["y_mm"] - pad["height_mm"] / 2))
            if not overlap_y:
                continue
            for i in range(count):
                x = -25 + (i + .5) * h_mm
                if x*x + y*y >= 625:
                    continue
                overlap_x = max(0, min(x + h_mm / 2, pad["x_mm"] + pad["width_mm"] / 2) -
                                      max(x - h_mm / 2, pad["x_mm"] - pad["width_mm"] / 2))
                area = overlap_x * overlap_y * 1e-6
                if area <= 1e-18:
                    continue
                key = (i, j)
                covered[key] = covered.get(key, 0) + area
                if covered[key] > h_mm * h_mm * 1e-6 * (1 + 1e-10):
                    raise ValueError("mask exceeds cell-face area")
                represented[pad["pad_id"]] += area
                rows.append((pad["pad_id"], i, j, area))
    for pad, actual in zip(pads, represented):
        if abs(actual / (pad["area_mm2"] * 1e-6) - 1) > 1e-10:
            raise ValueError(f"D50 staircase mesh clipped pad{pad['pad_id']} at h={h_mm}mm: "
                             f"represented={actual*1e6:.9f}mm2 expected={pad['area_mm2']:.9f}mm2")
    return rows, represented


def read_properties(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith(("#", "!")):
            continue
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError("duplicate source property: " + key)
        result[key] = value
    return result


def generate_family(output, h_mm=1.25):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("new output directory required; preserve prior evidence")
    parent = output.parent
    if not parent.is_dir():
        raise ValueError("output parent must already exist for explicit storage accounting")
    if shutil.disk_usage(parent).free < 2 * 1024**3 + 10 * 1024**2:
        raise ValueError("2GiB reserve plus10MiB preparation allowance unavailable")
    source = read_properties(SOURCE_CONFIG)
    designs = [("historical-square15", rectangles(4, center_x_mm=10, center_y_mm=10, height_mm=15))]
    designs += [(f"strip225-gap1-p{n:02d}", rectangles(n)) for n in (4, 8, 12, 16)]
    prepared = []
    # Validate every geometry/mask before creating a new persistent directory.
    for name, pads in designs:
        receipt = geometry_receipt(pads)
        rows, areas = mask_rows(pads, h_mm)
        prepared.append((name, pads, rows, areas, receipt))
    output.mkdir()
    (output / "configs").mkdir()
    (output / "masks").mkdir()
    cases = []
    for name, pads, rows, areas, receipt in prepared:
        ident = f"grouped-{name}-xy{round(50 / h_mm)}"
        mask = output / "masks" / (ident + ".csv")
        mask.write_text("pad,i,j,area_m2\n" + "".join(f"{e},{i},{j},{a:.17g}\n" for e, i, j, a in rows))
        config = {k: v for k, v in source.items() if not k.startswith("pad.")}
        config.update({"h_mm": str(h_mm), "channels": "2", "n_outputs": "2", "n_pads": str(len(pads)),
            "n_return_nodes": "1", "return_topology": "common_GND", "mask.path": str(mask),
            "mask.sha256": sha(mask), "grouped.geometry.version": "strip225-gap1-v1"})
        for p, area in zip(pads, areas):
            e = p["pad_id"]
            config[f"pad.node.{e}"] = str(p["node"])
            config[f"pad.{e}.represented_area_m2"] = format(area, ".17g")
            for key in ("shape", "width_mm", "height_mm", "rotation_deg", "x_mm", "y_mm"):
                config[f"pad.{e}.{key}"] = str(p[key])
            config[f"pad.{e}.analytic_area_mm2"] = str(p["area_mm2"])
        config_path = output / "configs" / (ident + ".properties")
        config_path.write_text("".join(f"{k}={config[k]}\n" for k in sorted(config)))
        cases.append(dict(id=ident, n_pads=len(pads), n_outputs=2, n_return_nodes=1,
            pad_node_ids=[p["node"] for p in pads], pads=pads, geometry=receipt,
            config_file=str(config_path), config_sha256=sha(config_path), mask_file=str(mask),
            mask_sha256=sha(mask), expected_pad_areas_m2=areas, h_xy_mm=h_mm, sc_cells=2,
            bulk_counts=[14, 14, 40], exporter_class="GroupedPadBasis", status="prepared_not_executed",
            waveform_branch="later_3000_3030_square_3h", frequencies_Hz=[3000, 3030, 9000, 9090],
            source_command_Vpp=[1, 1], source_resistance_ohm=[50, 50],
            inactive_output_termination="0V through50ohm", area_mode="equal_total_area_900mm2",
            control="original_four_square" if name.startswith("historical") else
                    ("new_four_rectangle_geometry_control" if len(pads) == 4 else "physical_strip_count"),
            roi=dict(radius_mm=5, depth_mm=[15, 20]), results=None))
    manifest = dict(schema="task1_grouped_geometry_v1", status="prepared_not_executed", pde_jobs=0,
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        input_source_config=str(SOURCE_CONFIG), input_source_config_sha256=sha(SOURCE_CONFIG),
        generator_sha256=sha(__file__), cases=cases,
        requested_legacy_15mm_height_centers_10mm="8/12/16 fail D50 corner bound at1mm physical gaps",
        rejected_h13p5_cx10p4_cy7p3="16pad h1.25mm staircase clips pad0:56.18vs56.25mm2",
        known_convergence_grid_blocker="H13,cx10.7,cy7:16pad h50/120mm clips pad0:56.246581197vs56.25mm2; h1.25/.625/.5 pass area checks; no renormalization allowed",
        execution_allowed=False, execution_blockers=["root_baseline_gate", "grouped_postprocessor_required",
                                                   "finite_PDE_preregistration_required"],
        preparation_budget=dict(max_wall_seconds=30, max_added_MiB=10, reserve_GiB=2, pde_jobs=0),
        limits=["analytic and cell-area checks are not mesh or experimental validation",
                "grouped four-rectangle control separates changed placement/shape from pad subdivision",
                "all GND return pads participate at every frequency; currents require solve"])
    path = output / "geometry-plan.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--h-mm", type=float, default=1.25)
    args = parser.parse_args()
    result = generate_family(args.output, args.h_mm)
    print(f"prepared{len(result['cases'])} geometries; no PDE; {Path(args.output).resolve() / 'geometry-plan.json'}")


if __name__ == "__main__":
    main()
