#!/usr/bin/env python3
"""One locked, finite cache-only contact-edge audit. No PDE or research imports."""
import argparse
import ast
import bisect
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import struct
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = (("cloud-mesh-c1-20261019T190000Z", "baseline-square15-xy80"),
         ("cloud-reference-20261019T192000Z", "baseline-square15-xy100"),
         ("cloud-reference-20261019T192000Z", "best1-square15-xy120"))
FREQUENCIES = (3000, 3030, 9000, 9090)
EDGE_BINS_MM = (0, .25, .5, 1, 2, 4, 7.5)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def pin(path, expected, used):
    path = Path(path)
    require(path.is_absolute() and path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink(),
            "Regular repository input required: " + str(path))
    require(path.stat().st_size <= 32 * 1024**2, "Audit excludes large E/phi/grid input: " + str(path))
    actual = sha(path)
    require(expected is None or actual == expected, "Pinned input SHA differs: " + str(path))
    used[str(path)] = actual
    return path


def scalar_expression(node):
    """Evaluate only literal arithmetic and math.sqrt from the frozen WAVES AST."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
        a, b = scalar_expression(node.left), scalar_expression(node.right)
        return {ast.Add: lambda: a+b, ast.Sub: lambda: a-b,
                ast.Mult: lambda: a*b, ast.Div: lambda: a/b}[type(node.op)]()
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and
            isinstance(node.func.value, ast.Name) and node.func.value.id == "math" and
            node.func.attr == "sqrt" and len(node.args) == 1 and not node.keywords):
        return math.sqrt(scalar_expression(node.args[0]))
    raise ValueError("Unrecognized frozen waveform arithmetic")


def frozen_square_coefficients(run, registration, used):
    source = run / "frozen-source/tis-java/explore_tis.py"
    expected = registration["source_and_input_sha256"][str(ROOT / "tis-java/explore_tis.py")]
    pin(source, expected, used)
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WAVES" for t in node.targets):
            require(isinstance(node.value, ast.Dict), "Frozen WAVES must be a literal dict")
            for key, value in zip(node.value.keys, node.value.values):
                if isinstance(key, ast.Constant) and key.value == "square_3h":
                    require(isinstance(value, ast.Tuple) and len(value.elts) == 2, "Two harmonic coefficients required")
                    return [scalar_expression(x) for x in value.elts]
    raise ValueError("Frozen square_3h coefficients unavailable")


def complex_array(path, count):
    data = Path(path).read_bytes()
    require(len(data) == 16 * count, "Complex128 raw shape mismatch: " + str(path))
    values = [complex(a, b) for a, b in struct.iter_unpack("<dd", data)]
    require(all(math.isfinite(x.real) and math.isfinite(x.imag) for x in values), "Nonfinite complex input")
    return values


def weighted_stats(values, areas):
    if not values:
        return None
    order = sorted(range(len(values)), key=lambda i: values[i])
    total, cumulative, prefixes = sum(areas), 0., []
    for i in order:
        cumulative += areas[i]
        prefixes.append(cumulative)
    # Match frozen np.cumsum(...)[-1], not Python3.12+ compensated sum().
    # An exact95% rank tie can move by one patch if the denominator changes.
    rank = min(bisect.bisect_left(prefixes, .95 * prefixes[-1]), len(order)-1)
    p95 = values[order[rank]]
    return dict(mean_A_m2=sum(v*a for v, a in zip(values, areas))/total,
                p95_A_m2=p95, max_A_m2=max(values), contact_area_mm2=total*1e6,
                p95_definition="nearest sequential cumulative area; threshold=.95*cumulative[-1]; no interpolation")


def audit_case(run_id, ident, used):
    run = ROOT / "data-native" / run_id
    registration_path = pin(run / "preregistration.json", None, used)
    registration = read(registration_path)
    case = next(c for c in registration["cases"] if c["id"] == ident)
    summary_path = run / "postprocess" / ident / "summary.json"
    receipt = run / "cases" / (ident + ".json")
    expected_summary_sha = None
    if receipt.exists():
        record = read(pin(receipt, None, used))
        require(record["status"] == "complete", "Completed case receipt required")
        expected_summary_sha = record["postprocess_sha256"]
    else:
        require(ident == "best1-square15-xy120", "Only explicitly held exact reference may lack complete receipt")
        comparison = read(pin(run / "reference-comparison.json", None, used))
        require(comparison["status"] == "failed", "Held strict reference failure must remain preserved")
    post = read(pin(summary_path, expected_summary_sha, used))
    require(post["status"] == "complete" and post["id"] == ident, "Complete native postprocess required")
    inputs = post["input_sha256"]
    manifest_digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    require(manifest_digest == post["input_manifest_sha256"], "Native input manifest digest differs")
    config_path = pin(Path(case["config_file"]), case["config_sha256"], used)
    require(inputs[str(config_path)] == case["config_sha256"], "Postprocess/config pin differs")
    config = dict(line.split("=", 1) for line in config_path.read_text().splitlines() if "=" in line)
    pin(Path(case["mask_file"]), case["mask_sha256"], used)
    basis = run / "bases" / ident
    for filename in ("BASIS_COMPLETE", "mesh-metadata.json", "validation.json"):
        pin(basis / filename, inputs[str(basis / filename)], used)
    metadata, validation = read(basis / "mesh-metadata.json"), read(basis / "validation.json")
    require(metadata == post["mesh_metadata"] and metadata["config_sha256"] == case["config_sha256"], "Mesh/config/summary disagree")
    require(metadata["channels"] == 2 and metadata["sc_cells"] == 2 and metadata["bulk_layer_counts"] == [14,14,40] and
            metadata["radius_mm"] == 25 and metadata["cells"] <= 800000 and
            metadata["total_depth_mm"] == 25.1 and metadata["tissue_boundaries_mm"] == [0,.1,5.1,10.1,25.1] and
            metadata["h_xy_mm"] == case["h_xy_mm"] == float(config["h_mm"]) and
            metadata["source_peak_V"] == .5 and metadata["source_resistance_ohm"] == 50 and
            metadata["phasor_convention"] == "peak,+jomega_t" and metadata["frequencies_Hz"] == list(FREQUENCIES), "Fixed four-pad native contract required")
    a1, a3 = frozen_square_coefficients(run, registration, used)
    contacts, squared_j, squared_v, source3000, loss3000 = None, None, None, None, None
    for frequency in FREQUENCIES:
        paths = {kind: pin(basis / f"{kind}-{frequency}.{suffix}", inputs[str(basis / f"{kind}-{frequency}.{suffix}")], used)
                 for kind, suffix in (("contacts", "csv"), ("density", "bin"), ("source", "bin"), ("loss", "bin"))}
        with paths["contacts"].open() as stream:
            rows = [(int(r["pad"]), float(r["x_mm"]), float(r["y_mm"]), float(r["area_m2"])) for r in csv.DictReader(stream)]
        if contacts is None:
            contacts, squared_j, squared_v = rows, [0.] * len(rows), [0.] * len(rows)
        require(rows == contacts, "Physical contact ordering differs across frequencies")
        density = complex_array(paths["density"], 2 * len(rows))
        source, loss = complex_array(paths["source"], 4), complex_array(paths["loss"], 24)
        if frequency == 3000:
            source3000, loss3000 = source, loss
        amplitude = a1 if frequency < 9000 else a3
        c = (-1j * amplitude, 0j) if frequency in (3000,9000) else (0j, -1j * amplitude)
        za = complex(float(config[f"z.{frequency}.re"]), float(config[f"z.{frequency}.im"]))
        for i in range(len(rows)):
            j = c[0] * density[i] + c[1] * density[len(rows)+i]
            squared_j[i] += abs(j)**2 / 2
            squared_v[i] += abs(j*za)**2 / 2
    h = metadata["h_xy_mm"]
    coordinates, areas = [], []
    for pad, x, y, area in contacts:
        require(pad in range(4) and area > 0 and abs(area / (h*h*1e-6)-1) <= 1e-10, "Full positive h² contact faces required")
        cx, cy = float(config[f"pad.{pad}.x_mm"]), float(config[f"pad.{pad}.y_mm"])
        require(config[f"pad.{pad}.shape"] == "rectangle" and float(config[f"pad.{pad}.width_mm"]) == 15 and
                float(config[f"pad.{pad}.height_mm"]) == 15 and float(config[f"pad.{pad}.rotation_deg"]) == 0,
                "Exact unrotated square15 geometry required")
        dx, dy = 7.5-abs(x-cx), 7.5-abs(y-cy)
        require(min(dx,dy) >= h/2-1e-8, "Contact centroid/full-face square boundary mismatch")
        areas.append(area)
        coordinates.append(dict(pad=pad, x_mm=x, y_mm=y, z_mm=0., edge_distance_mm=min(dx,dy),
                                edge_distance_over_h=min(dx,dy)/h, nearest_corner_distance_mm=math.hypot(dx,dy)))
    require(set(r[0] for r in contacts) == set(range(4)) and
            all(abs(sum(a for (pad, _, _, a) in contacts if pad == p)/.000225-1) <= 1e-10 for p in range(4)), "Every physical pad must preserve225mm²")
    values = [math.sqrt(j) for j in squared_j]
    stats = weighted_stats(values, areas)
    condition = next(c for c in post["conditions"] if c["waveform"] == "square_3h")
    require(condition["actual_fundamental_Hz"] == [3000,3030] and condition["phase_deg"] == [0.,0.] and
            condition["carrier_group"] == [0,1] and condition["source_Vpp_per_output"] == 1., "Fixed actual square_3h source definition required")
    metrics = condition["metrics"]
    checks = {"Jmax": (stats["max_A_m2"], metrics["surface_J_RMS_max_A_m2"]),
              "J95": (stats["p95_A_m2"], metrics["surface_J_RMS_p95_A_m2"]),
              "contact_voltage": (math.sqrt(max(squared_v)), metrics["contact_voltage_RMS_max_V"])}
    require(all(abs(a-b) <= 1e-10*abs(b)+1e-14 for a,b in checks.values()),
            "Independent small-array electrical metrics disagree with published summary: " + json.dumps(checks))
    bins = []
    for lo, hi in zip(EDGE_BINS_MM, EDGE_BINS_MM[1:]):
        chosen = [i for i,c in enumerate(coordinates) if lo <= c["edge_distance_mm"] < hi or
                  (hi == EDGE_BINS_MM[-1] and c["edge_distance_mm"] == hi)]
        bins.append(dict(edge_distance_mm=[lo,hi], interval="left_closed_right_open; final inclusive", patches=len(chosen),
                         statistics=weighted_stats([values[i] for i in chosen], [areas[i] for i in chosen])))
    qsum = [sum(loss3000[4*k+i] for k in range(6)) for i in range(4)]
    hermitian_source = [(source3000[2*i+j]+source3000[2*j+i].conjugate())/2 for i in range(2) for j in range(2)]
    power_defect = max(abs(q-.25*s) for q,s in zip(qsum,hermitian_source))
    return dict(run_id=run_id, candidate_id=ident, h_xy_mm=h, n_pads=4, n_outputs=2, pad_node_ids=[0,1,-1,-1],
        source_commit=registration["source_commit"], config_sha256=case["config_sha256"], mask_sha256=case["mask_sha256"],
        return_topology="common_GND", source_Vpp=1., waveform="square_3h", source_coefficients=[a1,a3],
        contact_normal_J_RMS=stats, Jmax_mA_cm2=stats["max_A_m2"]*.1, J95_mA_cm2=stats["p95_A_m2"]*.1,
        contact_voltage_RMS_max_V=checks["contact_voltage"][0], fixed_edge_distance_bins=bins,
        hottest_patches=[dict(coordinates[i], J_RMS_A_m2=values[i]) for i in sorted(range(len(values)), key=lambda i: values[i], reverse=True)[:8]],
        summary_metric_verification={k:dict(independent=a,published=b,relative_difference=abs(a-b)/abs(b)) for k,(a,b) in checks.items()},
        frequency3000_diagnostics=dict(source_reciprocity_defect_A=abs(source3000[1]-source3000[2]),
            loss_Hermitian_max_defect_W=max(abs(loss3000[4*k+2*i+j]-loss3000[4*k+2*j+i].conjugate()) for k in range(6) for i in range(2) for j in range(2)),
            power_operator_max_absolute_defect_W=power_defect,
            power_identity="sum six loss matrices = 0.25*HermitianPart(source transfer matrix)",
            native_validation_reported=validation, residual_independently_recomputed=False, rigorous_forward_error_bound=False),
        strict_reference_status="held_failed_2_of_8_matrix_gates; diagnostic_only" if not receipt.exists() else "original_case_complete",
        physics_config={k:v for k,v in config.items() if k not in ("h_mm","mask.path","mask.sha256")})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.absolute()
    require(output == args.output.resolve() and output.parent == ROOT/"docs/cloud-restart-20261020" and
            output.suffix == ".json" and not output.exists(), "Unique canonical JSON output in restart evidence directory required")
    with (ROOT/".task1-execution.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        started, used = time.monotonic(), {}
        budget_path = ROOT/"runtime/task1-budget.json"
        budget = read(budget_path)
        require(budget["limit_seconds"] == 6600 and budget["spent_seconds"]+180 <= 6600, "Remaining finite budget below180s")
        require(shutil.disk_usage(ROOT).free >= 2*1024**3+16*1024**2, "2GiB reserve plus16MiB audit allowance required")
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        def expired(signum, frame):
            raise TimeoutError("180second cache audit limit")
        signal.signal(signal.SIGALRM,expired)
        signal.setitimer(signal.ITIMER_REAL,180)
        result = dict(schema="task1-contact-edge-cache-audit-v1", started_utc=now(), status="running", new_PDE=0,
                      audit_code_sha256=sha(__file__),
                      new_workers=0, full_E_phi_or_grid_read=False, numerical_validation_promoted=False,
                      experimental_validation=False, safety_validation=False, edge_bins_mm=list(EDGE_BINS_MM))
        try:
            rows = [audit_case(run, ident, used) for run,ident in CASES]
            require(all(row["physics_config"] == rows[0]["physics_config"] for row in rows), "Physics differs beyond mask paths/hash and XY spacing")
            for row in rows:
                row.pop("physics_config")
            changes = [dict(before=a["candidate_id"],after=b["candidate_id"],
                Jmax_change_percent=100*(b["contact_normal_J_RMS"]["max_A_m2"]/a["contact_normal_J_RMS"]["max_A_m2"]-1),
                J95_change_percent=100*(b["contact_normal_J_RMS"]["p95_A_m2"]/a["contact_normal_J_RMS"]["p95_A_m2"]-1),
                contact_voltage_change_percent=100*(b["contact_voltage_RMS_max_V"]/a["contact_voltage_RMS_max_V"]-1))
                for a,b in zip(rows,rows[1:])]
            require(all(sha(path)==expected for path,expected in used.items()), "Audit input changed during read")
            result.update(status="complete_diagnostic_only", cases=rows, adjacent_XY_changes=changes,
                input_sha256=used, inputs_unchanged=True,
                interpretation="Edge growth and finite-grid sensitivity only; existing Jmax/contactV5% failures remain failures. Near-zero matrix diagnostics do not clear strict held reproduction or establish solver forward error.",
                limitations=["Contact-normal current density on electrode patches is not full skin-vector current density",
                    "Nearest area-CDF P95 has a one-patch rank sensitivity at exact95% boundaries; frozen sequential-prefix denominator is preserved without interpolation",
                    "Ideal sharp-edge Jmax may remain grid-sensitive; no threshold substitution or relaxation",
                    "PBS-derived area-specific impedance is an uncertain skin contact hypothesis; separate future Rs/area-once sensitivity required"])
        except BaseException as error:
            result.update(status="failed_preserved", error_type=type(error).__name__, error=str(error), input_sha256=used)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            elapsed = time.monotonic()-started
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak > 3*1024**3:
                result.update(status="failed_preserved",error="3GiB RSS cap exceeded")
            result.update(wall_seconds=elapsed, peak_RSS_bytes=peak, finished_utc=now(),
                          resource_limits=dict(cpu=1,wall_seconds=180,RSS_bytes=3*1024**3,reserve_bytes=2*1024**3))
            budget["spent_seconds"] += elapsed
            budget["runs"].append(dict(run_id=output.stem,stage="cache_contact_edge_audit",seconds=elapsed,status=result["status"]))
            temporary = budget_path.with_suffix(".json.partial")
            temporary.write_text(json.dumps(budget,indent=2)+"\n")
            temporary.replace(budget_path)
            write_new(output,result)
        print(json.dumps(dict(status=result["status"],output=str(output),new_PDE=0)))


if __name__ == "__main__":
    main()
