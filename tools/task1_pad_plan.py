#!/usr/bin/env python3
"""Generate/validate a plan, never run a solver or import research modules.

Pad count and source count are independent. The frozen ShapeNet cannot consume
this format or represent its >4-pad grouping. No result fields may be populated
until an explicit result importer and a validated grouped-pad solver exist.
"""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PAD_COUNTS = (4, 8, 12, 16)
AREA_MODES = ("equal_total_area", "equal_per_pad_area")
METRICS = {
    "target_tis_mean_V_per_cm": None, "target_tis_P10_V_per_cm": None,
    "target_tis_max_V_per_cm": None, "target_E_rms_V_per_cm": None,
    "superficial_tis_P95_V_per_cm": None, "superficial_tis_max_V_per_cm": None,
    "all_nontarget_tis_P95_V_per_cm": None, "all_nontarget_tis_max_V_per_cm": None,
    "global_tis_max_V_per_cm": None, "global_tis_max_xyz_mm": None,
    "outside_target_high_modulation_volume_mm3": None,
    "skin_Jmax_mA_per_cm2": None, "skin_J95_mA_per_cm2": None,
    "contact_voltage_max_mV": None, "skin_loss_uW": None,
    "contact_loss_uW": None, "source_resistor_loss_uW": None,
    "total_source_power_uW": None, "source_current_rms_mA": None,
}
BRANCHES = {
    "initial_2000_2010_sine": {"carrier_Hz": [2000, 2010], "waveform": "sine",
                                "harmonic_numbers": [1]},
    "later_3000_3030_square_3h": {"carrier_Hz": [3000, 3030],
        "waveform": "square_3h", "harmonic_numbers": [1, 3]},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def seal(value, key):
    value[key] = digest({k: v for k, v in value.items() if k != key})
    return value


def topology(n_pads):
    """Proposed equal split into S0, S1, R0 and R1 physical pad groups.

    R0/R1 are wiring labels only: every return pad is one electrical GND node.
    The groups are proposals, not an inference from an existing mask file.
    """
    group_size = n_pads // 4
    pads = []
    for group, node in enumerate(("OUT0", "OUT1", "GND", "GND")):
        for index in range(group_size):
            pad_id = f"P{group * group_size + index:02d}"
            pads.append({"pad_id": pad_id, "role": "signal" if group < 2 else "return",
                         "group": ("S0", "S1", "R0", "R1")[group], "node": node})
    return pads


def source_definitions(branch):
    sources = []
    coefficients = ([1.0] if BRANCHES[branch]["waveform"] == "sine" else
                    [3 / (2 * math.sqrt(2)), 1 / (2 * math.sqrt(2))])
    for index, carrier in enumerate(BRANCHES[branch]["carrier_Hz"]):
        sources.append({"output_id": f"OUT{index}", "reference_node": "GND",
            "carrier_Hz": carrier, "source_phase_deg": 0.0,
            "source_Vpp": 1.0, "Vpp_definition": "open_circuit_High_Z",
            "source_resistance_ohm": 50.0,
            "phasor_convention": "peak_exp_plus_j_omega_t",
            "inactive_frequency_termination": {"source_peak_V": 0.0,
                                                 "resistance_ohm": 50.0},
            "waveform": BRANCHES[branch]["waveform"],
            "harmonic_frequencies_Hz": [carrier * h for h in
                                        BRANCHES[branch]["harmonic_numbers"]],
            "dimensionless_harmonic_coefficients": coefficients,
            "coefficient_convention": "-j * coefficient * exp(j * harmonic * phase); multiply 0.5Vpeak basis",
            "waveform_coefficient_source": "tis-java/explore_tis.py WAVES; tis-java/single_vs_tis.py _coefficients",
            "Vpp_scope": "entire bandlimited open-circuit source waveform, not every harmonic"})
    return sources


def frequency_connections(sources):
    rows = []
    for driven in sources:
        for frequency, factor in zip(driven["harmonic_frequencies_Hz"],
                                     driven["dimensionless_harmonic_coefficients"]):
            rows.append({"frequency_Hz": frequency,
                "outputs": {source["output_id"]: {
                    "state": "driven" if source is driven else "terminated",
                    "ideal_peak_phasor_V": {"real": 0.0, "imag": -.5 * factor if source is driven else 0.0},
                    "series_resistance_ohm": 50.0, "reference_node": "GND"}
                    for source in sources}})
    return sorted(rows, key=lambda row: row["frequency_Hz"])


def make_case(n_pads, area_mode, branch, source_commit):
    pads = topology(n_pads)
    per_pad = 900.0 / n_pads if area_mode == "equal_total_area" else 225.0
    total_area = per_pad * n_pads
    impossible_area = total_area > math.pi * 25.0 ** 2
    for pad in pads:
        pad["requested_area_mm2"] = per_pad
        pad["attachment_surface"] = "top_z0"
        pad["geometry"] = None
    if n_pads == 4:
        for pad, (x, y) in zip(pads, ((-10, -10), (10, 10), (10, -10), (-10, 10))):
            pad["geometry"] = {"shape": "rectangle", "width_mm": 15.0,
                "height_mm": 15.0, "x_mm": x, "y_mm": y, "rotation_deg": 0.0}
    ident = f"padplan-v1-p{n_pads:02d}-{area_mode}-{branch}"
    sources = source_definitions(branch)
    case = {"candidate_id": ident, "n_pads": n_pads, "n_outputs": 2,
        "n_signal_pads": n_pads // 2, "n_return_pads": n_pads // 2,
        "n_return_nodes": 1, "return_topology": "common_GND",
        "pads": pads,
        "pad_to_source_node": {p["pad_id"]: p["node"] for p in pads if p["role"] == "signal"},
        "pad_to_return_node": {p["pad_id"]: "GND" for p in pads if p["role"] == "return"},
        "sources": sources, "waveform_branch": branch,
        "carrier_assignment": {s["output_id"]: s["harmonic_frequencies_Hz"] for s in sources},
        "source_phase": {s["output_id"]: s["source_phase_deg"] for s in sources},
        "frequency_connections": frequency_connections(sources),
        "return_frequency_behavior": "all GND pads participate at every frequency; return-current division requires circuit solve",
        "area_comparison": {"mode": area_mode, "per_pad_area_mm2": per_pad,
                            "total_contact_area_mm2": total_area,
                            "top_surface_area_mm2": math.pi * 25.0 ** 2},
        "geometry_status": "necessary_area_bound_failed" if impossible_area else
                           ("historical_baseline_geometry_only" if n_pads == 4 else "unregistered"),
        "minimum_gap_mm": None,
        "hardware_scope": "four_pad_experimental_reference" if n_pads == 4 else "virtual_expansion",
        "solver_support": "frozen_4pad_mapping_only" if n_pads == 4 else "grouped_pad_solver_required",
        "execution_allowed": False,
        "execution_blockers": ["plan_only_no_execution_budget", "baseline_clean_reproduction_required"] +
            (["total_contact_area_exceeds_D50_top_surface"] if impossible_area else []) +
            (["geometry_mask_and_grouped_pad_solver_not_registered"] if n_pads > 4 else []),
        "budget_reference": "padplan-v1-topology-only",
        "provenance": {"source_commit": source_commit, "run_id": None,
                       "material_model_version": None, "contact_model_version": None,
                       "mesh_id": None, "raw_field_manifest_sha256": None},
        "execution_status": "not_executed", "numerical_validation": "not_started",
        "experimental_validation": "not_performed",
        "normalizations": {mode: {"status": "not_evaluated", "scale": None,
                                  "reference_candidate_id": f"padplan-v1-p04-{area_mode}-{branch}",
                                  "reference_limits": None, "metrics": dict(METRICS)}
                           for mode in ("equal_applied_voltage", "equal_total_power", "equal_surface_burden")}}
    return seal(case, "config_sha256")


def make_plan(source_commit, exporter_sha256):
    plan = {"schema": "task1_pad_plan_v1", "scope": "task1_only_topology_plan",
        "source_commit": source_commit, "frozen_exporter_sha256": exporter_sha256,
        "phantom": {"diameter_mm": 50.0, "layer_thickness_mm": [0.1, 5.0, 5.0, 15.0],
                    "z0": "top_surface", "positive_z": "depth",
                    "side_bottom_boundary": "insulating", "attachment": "top_only"},
        "roi": {"target": {"radial_max_mm": 5.0, "depth_mm": [15.0, 20.0]},
                "superficial_nontarget": {"depth_mm": [0.0, 5.0]},
                "all_nontarget": "phantom_volume_excluding_target",
                "sample_weighting": "cell_volume", "boundary_policy": "volume_intersection",
                "high_modulation_threshold": None},
        "comparison": {"baseline_pad_count_always_visible": 4,
            "pad_counts": list(PAD_COUNTS), "common_linear_color_range": None,
            "color_range_status": "requires_same_grid_validated_absolute_results",
            "color_range_rule": "one shared min/max per metric across displayed pad counts",
            "separate_area_and_waveform_branches": True,
            "modulation_definition": "requires_actual_waveform_validation; no two-tone extrapolation",
            "constraint_limits": None, "constraint_meaning": "numerical_comparison_not_human_safety"},
        "planning_budget": {"budget_id": "padplan-v1-topology-only", "pde_jobs": 0,
            "workers": 0, "max_cpu_threads": 1, "max_wall_seconds": 30,
            "max_rss_MiB": 128, "max_added_disk_MiB": 10, "disk_reserve_GiB": 2,
            "scope": "JSON validation and local static preview only"},
        "expansion_gate": ["reproduce_4pad_baseline", "register_gap_geometry_masks_and_mapping",
            "implement_grouped_pad_operator_and_exporter", "analytic_and_4pad_operator_regression",
            "fixed_mesh_area_and_power_conservation", "actual_composite_waveform_modulation_check",
            "SC_XY_bulk_edge_contact_convergence_and_sensitivity", "preregister_finite_PDE_budget"],
        "cases": [make_case(n, area, branch, source_commit) for area in AREA_MODES
                  for branch in BRANCHES for n in PAD_COUNTS]}
    return seal(plan, "plan_sha256")


def validate_plan(plan):
    """Strict plan-only format: a result or hardware expansion needs a new schema."""
    if not isinstance(plan, dict):
        return ["plan must be a JSON object"]
    commit, exporter = plan.get("source_commit"), plan.get("frozen_exporter_sha256")
    errors = []
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("source_commit must be an exact 40-character Git SHA")
    if not isinstance(exporter, str) or not re.fullmatch(r"[0-9a-f]{64}", exporter):
        errors.append("frozen_exporter_sha256 must be an exact SHA256")
    if errors:
        return errors
    expected = make_plan(commit, exporter)
    # Exact canonical comparison rejects silently inserted result values, altered
    # circuit/geometry/ROI/budget definitions and checksum-only re-sealing attacks.
    try:
        if canonical(plan) != canonical(expected):
            for field in sorted(set(plan) | set(expected)):
                if canonical(plan.get(field)) != canonical(expected.get(field)):
                    errors.append(f"field differs from plan-only contract: {field}")
    except (ValueError, TypeError):
        errors.append("plan contains unsupported or nonfinite JSON values")
    return errors


def render_preview(plan):
    errors = validate_plan(plan)
    if errors:
        raise ValueError("; ".join(errors))
    rows = []
    for area in AREA_MODES:
        for branch in BRANCHES:
            cases = [c for c in plan["cases"] if c["area_comparison"]["mode"] == area
                     and c["waveform_branch"] == branch]
            rows.append(f"<h2>{html.escape(area)} · {html.escape(branch)}</h2><table><thead><tr><th>항목</th>" +
                        "".join(f"<th>{c['n_pads']} 패드 / 2 출력</th>" for c in cases) + "</tr></thead><tbody>")
            for title, values in (
                ("총 접촉 면적 (mm²)", [str(c["area_comparison"]["total_contact_area_mm2"]) for c in cases]),
                ("형상 상태", [c["geometry_status"] for c in cases]),
                ("구동 / 귀환", ["1 Vpp High Z × 2 / 50 Ω / common GND"] * 4),
                ("계산 / 수치 / 실험 검증", ["미실행 / 미시작 / 미수행"] * 4),
                ("동일 전압 ROI mean / P10 (V/cm)", ["— / —"] * 4),
                ("동일 총 전력 ROI mean / P10 (V/cm)", ["— / —"] * 4),
                ("동일 표면 부담 ROI 절대 mean / P10 (V/cm)", ["— / —"] * 4),
                ("피부 Jmax / J95 (mA/cm²)", ["— / —"] * 4),
                ("접촉 전압 (mV) / 총 전력 (µW)", ["— / —"] * 4),
                ("전역 최대 위치 / 비표적 고변조 부피", ["— / —"] * 4),
                ("후보 ID", [c["candidate_id"] for c in cases]),
                ("설정 SHA256", [c["config_sha256"] for c in cases]),
            ):
                rows.append("<tr><th>" + html.escape(title) + "</th>" +
                            "".join("<td>" + html.escape(v) + "</td>" for v in values) + "</tr>")
            rows.append("</tbody></table>")
    return """<!doctype html><html lang="ko"><meta charset="utf-8"><title>작업 1 패드 비교 계획</title>
<style>body{font:15px sans-serif;margin:24px;color:#18202b}table{border-collapse:collapse;width:100%;table-layout:fixed;margin:20px 0 40px}th,td{border:1px solid #c9d0da;padding:10px;overflow-wrap:anywhere;vertical-align:top}thead th{background:#eaf0f7}td:nth-child(2),thead th:nth-child(2){background:#e6f3e8}th:first-child{width:20%}h2{font-size:18px}.notice{padding:15px;background:#fff5ce}</style>
<h1>작업 1 · 4 / 8 / 12 / 16 패드 비교 계획</h1>
<p class="notice">계산 결과 화면이 아닌 계획 미리보기입니다. —는 미계산이며 0이 아닙니다. 현재 코드의 임의 다중 패드 배선 지원은 미구현입니다. 4패드 열은 모든 표에 고정됩니다.</p>
<p>D50 mm · SC / dermis / fat / muscle = 0.1 / 5 / 5 / 15 mm · 상부 부착 · z=0 표면, +z 깊이.
목표 ROI r≤5 mm, 깊이 15–20 mm. 비표적 표층 0–5 mm 및 전체 비표적을 분리합니다.</p>
<p>지도와 색 범위는 아직 생성되지 않았습니다. 같은 격자·ROI·단위의 검증 결과를 확보한 뒤 지표마다 모든 패드 수에 하나의 선형 범위를 적용합니다.
표면 부담 제한값은 미등록 상태이며 인체 안전 한계가 아닙니다. 총 면적 고정과 패드별 면적 고정은 별도 조건입니다.
12·16패드의 패드당 225 mm² 조건은 총 면적이 상면을 초과하므로 실행할 수 없습니다.</p>
""" + "\n".join(rows) + "<p>Plan SHA256: " + plan["plan_sha256"] + "</p></html>\n"


def write_new(path, contents):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("generate")
    gen.add_argument("--output", required=True)
    gen.add_argument("--preview")
    check = commands.add_parser("validate")
    check.add_argument("path")
    args = parser.parse_args()
    if args.command == "generate":
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        exporter = hashlib.sha256((ROOT / "tis-java/SelectivityShapeBasis.java").read_bytes()).hexdigest()
        plan = make_plan(commit, exporter)
        write_new(args.output, json.dumps(plan, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
        if args.preview:
            write_new(args.preview, render_preview(plan))
        print(f"16 topology plans generated; PDE jobs 0; plan SHA256 {plan['plan_sha256']}")
    else:
        try:
            plan = json.loads(Path(args.path).read_text(encoding="utf-8"))
            errors = validate_plan(plan)
        except (OSError, ValueError) as exc:
            parser.exit(1, f"INVALID: {exc}\n")
        if errors:
            parser.exit(1, "INVALID: " + "; ".join(errors) + "\n")
        print("VALID plan-only contract; no numerical or experimental validation claimed")


if __name__ == "__main__":
    main()
