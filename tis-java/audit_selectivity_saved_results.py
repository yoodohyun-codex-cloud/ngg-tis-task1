"""One-shot independent audit of terminal fixed-phantom saved results.

Only small source/loss complex circuit matrices and saved JSON scalar metadata
are decoded. No E, phi, density, grid, volume archive or waveform is loaded.
This module deliberately imports no production postprocessor or numerical helper.
"""
from __future__ import annotations

import argparse
import cmath
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import struct
import tempfile
import time

FREQUENCIES = (3000, 3030, 9000, 9090)
WAVES = {"sine": (1., 0.), "square_3h": (3/(2*math.sqrt(2)), 1/(2*math.sqrt(2))),
         "triangle_3h": (.9, -.1)}
REGIONS = ("total", "target", "surface_0_5", "subsurface_5_10", "remaining", "off_target")
TOLERANCE = 2e-7
MAX_JSON = 64*1024**2
MAX_RSS = 3*1024**3
MIN_DISK = 2*1024**3
REFERENCE_KEYS = ("target20_modulation_V_m", "target20_total_E_RMS_V_m",
                  "surface_J_RMS_max_A_m2", "surface_J_RMS_p95_A_m2",
                  "contact_voltage_RMS_max_V", "SC_power_W", "contact_power_W", "source_power_W")
LINEAR_CHECKS = ("target20_modulation_V_m", "target20_total_E_RMS_V_m",
                 "surface_J_RMS_max_A_m2", "surface_J_RMS_p95_A_m2",
                 "contact_voltage_RMS_max_V", "max_source_current_RMS_mA")
QUADRATIC_CHECKS = ("SC_power_W", "contact_power_W", "source_power_W")
NORMALIZATION = dict(source_peak_V=.5, source_Vpp=1., source_resistance_ohm=50., phasor_exponent="+jomega_t")


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def digest(value):
    # The frozen postprocessor's canonical namespace uses ensure_ascii=True.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def relative_error(actual, expected):
    require(finite(actual) and finite(expected), "Nonfinite scalar comparison")
    if expected == 0:
        return 0. if actual == 0 else None
    return abs(actual-expected)/abs(expected)


class Budget:
    def __init__(self, run, seconds=600., started=None):
        self.run = Path(run)
        self.started = time.monotonic() if started is None else started
        self.deadline = self.started+seconds

    def check(self):
        require(time.monotonic() < self.deadline, "Audit time limit exceeded")
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= MAX_RSS, "Audit RSS limit exceeded")
        require(shutil.disk_usage(self.run).free >= MIN_DISK, "Audit disk reserve below2GiB")
        for name in ("STOP", "needs_attention", "needs_physical_validation"):
            require(not (self.run/name).exists(), "Audit blocked by source marker: "+name)


class Audit:
    def __init__(self, run, budget):
        self.run, self.budget = Path(run), budget
        self.pins, self.checks, self.held = {}, [], []

    def check(self, name, ok, **detail):
        self.budget.check()
        self.checks.append(dict(name=name, passed=bool(ok), **detail))

    def compare(self, name, actual, expected, tolerance=TOLERANCE):
        error = relative_error(actual, expected)
        self.check(name, error is not None and error <= tolerance, actual=actual, expected=expected,
                   relative_error=error, relative_tolerance=tolerance,
                   zero_reference_mismatch=expected == 0 and actual != 0)

    def hold(self, name, reason):
        self.held.append(dict(name=name, status="not_independently_recomputed", reason=reason))

    def pin(self, path, expected=None):
        self.budget.check()
        path = Path(path).resolve()
        actual = sha(path)
        require(str(path) not in self.pins or self.pins[str(path)] == actual, "Source changed during audit read")
        require(expected is None or valid_sha(expected) and actual == expected, "File SHA mismatch: "+str(path))
        self.pins[str(path)] = actual
        return actual

    def read(self, path, expected=None):
        self.budget.check()
        path = Path(path).resolve()
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON+1)
        require(len(raw) <= MAX_JSON, "JSON exceeds bounded64MiB metadata read")
        value = json.loads(raw)
        digest(value)
        actual = hashlib.sha256(raw).hexdigest()
        require(str(path) not in self.pins or self.pins[str(path)] == actual, "Metadata changed during read")
        require(expected is None or valid_sha(expected) and actual == expected, "Metadata SHA mismatch: "+str(path))
        self.pins[str(path)] = actual
        return value

    def recheck(self):
        for path, expected in self.pins.items():
            self.budget.check()
            require(sha(path) == expected, "Audited input changed: "+path)


def coefficients(channels, waveform, carrier=None, phases_deg=None):
    """Dimensionless coefficients multiplying transfers solved at0.5V peak.

    Sine convention is -j, with the third harmonic receiving3*phase. The signed
    triangle third coefficient is preserved. Frequencies remain separate.
    """
    require(channels in (1, 2) and waveform in WAVES, "Unsupported carrier/waveform")
    require(channels == 2 and carrier is None or channels == 1 and carrier in (3000,3030), "Invalid carrier scope")
    phases_deg = [0.]*channels if phases_deg is None else phases_deg
    require(len(phases_deg) == channels and all(finite(p) for p in phases_deg), "Invalid source phase")
    groups = [0,1] if channels == 2 else [0 if carrier == 3000 else 1]
    result = {}
    for frequency in FREQUENCIES:
        group = 0 if frequency in (3000,9000) else 1
        harmonic = 1 if frequency in (3000,3030) else 3
        amplitude = WAVES[waveform][0 if harmonic == 1 else 1]
        result[frequency] = [(-1j*amplitude*cmath.exp(1j*harmonic*math.radians(phases_deg[i])))
                             if groups[i] == group else 0j for i in range(channels)]
    return result


def matrix_vector(matrix, vector):
    return [sum(a*b for a,b in zip(row, vector)) for row in matrix]


def independent_circuit(matrices, channels, waveform, carrier=None, phases_deg=None):
    """Independent complex network identities; no production helper is used."""
    coeff = coefficients(channels, waveform, carrier, phases_deg)
    current_square = [0.]*channels
    losses = [0.]*6
    source_power = 0.
    spectra, loaded = {}, {}
    for f in FREQUENCIES:
        c = coeff[f]
        transfer, blocks = matrices[f]
        require(len(transfer) == channels and len(blocks) == 6, "Circuit matrix dimensions differ")
        current = matrix_vector(transfer, c)
        source_voltage = [.5*v for v in c]
        source_power += .5*sum((v*i.conjugate()).real for v,i in zip(source_voltage,current))
        spectra[f] = current
        loaded[f] = [v-50*i for v,i in zip(source_voltage,current)]
        for i,value in enumerate(current):
            current_square[i] += abs(value)**2/2
        for k,matrix in enumerate(blocks):
            quadratic = sum(c[a].conjugate()*matrix[a][b]*c[b]
                            for a in range(channels) for b in range(channels))
            require(abs(quadratic.imag) <= 1e-12+abs(quadratic.real)*TOLERANCE, "Non-real circuit dissipation")
            losses[k] += quadratic.real
    output = dict(max_source_current_RMS_mA=math.sqrt(max(current_square))*1000,
                  source_current_RMS_by_output_mA=[math.sqrt(v)*1000 for v in current_square],
                  SC_power_W=losses[0], contact_power_W=losses[4], skin_power_W=losses[0]+losses[4],
                  tissue_contact_power_W=sum(losses[:5]), source_power_W=source_power,
                  source_resistor_power_W=50*sum(current_square))
    return output, spectra, loaded, losses


def read_small_matrix(path, count):
    """Only source<=64B and loss<=384B uncompressed; hard exact byte bound."""
    path = Path(path)
    require(path.name.startswith(("source-", "loss-")) and path.name.endswith((".bin", ".bin.gz")),
            "Only small source/loss matrices may be decoded")
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        data = stream.read(count*16+1)
    require(len(data) == count*16, "Small circuit matrix byte length differs")
    values = [complex(*pair) for pair in struct.iter_unpack("<dd", data)]
    require(all(math.isfinite(v.real) and math.isfinite(v.imag) for v in values), "Nonfinite circuit matrix")
    return values


def load_circuits(audit, folder, channels, declared):
    result = {}
    for frequency in FREQUENCIES:
        arrays = []
        for name, blocks in (("source",1), ("loss",6)):
            basename = f"{name}-{frequency}.bin"
            candidates = [folder/basename, folder/(basename+".gz")]
            found = [p for p in candidates if p.is_file()]
            require(len(found) == 1 and found[0].name in declared, "Unique declared small circuit file required")
            path = found[0]
            audit.pin(path, declared[path.name])
            values = read_small_matrix(path, blocks*channels*channels)
            rows = [values[i:i+channels] for i in range(0,len(values),channels)]
            arrays.append(rows if blocks == 1 else [rows[i:i+channels] for i in range(0,len(rows),channels)])
        result[frequency] = tuple(arrays)
        for k, matrix in enumerate(arrays[1]):
            audit.check(f"{folder.name}:{frequency}:Hermitian_loss{k}", all(
                abs(matrix[a][b]-matrix[b][a].conjugate()) <= 1e-12+1e-10*abs(matrix[a][b])
                for a in range(channels) for b in range(channels)))
    return result


def statistics_checks(audit, name, stats, expected_volume):
    keys = ("min", "p10", "p50", "p95", "max", "mean", "volume_m3")
    audit.check(name+":finite_statistics", all(finite(stats.get(k)) for k in keys))
    if not all(finite(stats.get(k)) for k in keys):
        return
    values = [stats[k] for k in ("min", "p10", "p50", "p95", "max")]
    roundoff = 1e-12*max(1.,abs(values[-1]))
    audit.check(name+":nonnegative_order", values[0] >= -roundoff and all(a <= b+roundoff for a,b in zip(values,values[1:])))
    audit.check(name+":mean_bounds", values[0]-roundoff <= stats["mean"] <= values[-1]+roundoff)
    audit.compare(name+":weight_volume", stats["volume_m3"], expected_volume)
    audit.check(name+":positive_native_samples", type(stats.get("positive_weight_cells")) is int and stats["positive_weight_cells"] > 0)


def volume_checks(audit, identity, volume, expected_domain_tolerance=.002):
    audit.check(identity+":native_volume_complete", volume.get("status") == "complete" and volume.get("total_sampled_directions") == 2074)
    geometry = volume["geometry"]
    audit.check(identity+":fixed_geometry", geometry.get("layer_faces_mm") == [0.,.1,5.1,10.1,25.1]
                and geometry.get("renormalized_to_analytic_volume") is False)
    for prefix, expected_tolerance in (("domain",expected_domain_tolerance), ("target",.001)):
        value, limit = geometry[prefix+"_relative_volume_deviation"], geometry[prefix+"_relative_volume_tolerance"]
        audit.check(identity+":"+prefix+"_volume_gate", finite(value) and limit == expected_tolerance and abs(value) <= limit)
    audit.check(identity+":partition_roundoff", finite(geometry.get("max_relative_partition_roundoff")) and 0 <= geometry["max_relative_partition_roundoff"] <= 128*math.ulp(1.))
    volumes = geometry["region_volumes_m3"]
    audit.check(identity+":positive_region_volumes",set(volumes) == set(REGIONS) and all(finite(v) and v > 0 for v in volumes.values()))
    audit.compare(identity+":domain_analytic_cylinder",geometry["analytic_cylinder_volume_m3"],math.pi*25**2*25.1*1e-9,1e-12)
    audit.compare(identity+":domain_represented_volume",geometry["represented_domain_volume_m3"],volumes["total"])
    audit.compare(identity+":target_analytic_cylinder", geometry["analytic_target_volume_m3"], math.pi*5**2*5*1e-9, 1e-12)
    audit.compare(identity+":target_represented_volume", geometry["represented_target_volume_m3"], volumes["target"])
    for name,represented,analytic in (("domain",geometry["represented_domain_volume_m3"],geometry["analytic_cylinder_volume_m3"]),
                                     ("target",geometry["represented_target_volume_m3"],geometry["analytic_target_volume_m3"])):
        saved = geometry[name+"_relative_volume_deviation"]
        derived = represented/analytic-1
        # An absolute bound is appropriate for a deviation which may be zero.
        audit.check(identity+":"+name+":deviation_scalar_join",abs(saved-derived) <= 2e-12,saved=saved,derived=derived)
    audit.compare(identity+":region_partition", sum(volumes[k] for k in ("target","surface_0_5","subsurface_5_10","remaining")), volumes["total"])
    audit.compare(identity+":off_target_partition", volumes["target"]+volumes["off_target"], volumes["total"])
    for region in REGIONS:
        data = volume["regions"][region]
        for metric in ("maxTIS", "fixedTIS", "RMS", "X_TIS", "Y_TIS", "Z_TIS"):
            statistics_checks(audit, identity+":"+region+":"+metric, data["statistics"][metric], volumes[region])
        for quantile in ("min","p10","p50","p95","max","mean"):
            stats = data["statistics"]
            audit.check(identity+":"+region+":"+quantile+"_direction_bounds",
                        all(stats[k][quantile] <= stats["maxTIS"][quantile]+1e-10 for k in ("fixedTIS","X_TIS","Y_TIS","Z_TIS"))
                        and stats["maxTIS"][quantile] <= 2*stats["RMS"][quantile]+1e-10)
        tissue = data.get("tissue_volumes_m3", {})
        audit.check(identity+":"+region+":nonnegative_tissue_volumes",set(tissue) == {"0","1","2","3"} and all(finite(v) and v >= 0 for v in tissue.values()))
        audit.compare(identity+":"+region+":tissue_partition", sum(tissue.values()), volumes[region])
        total = volumes["total"]
        tissue_total = [total*d/25.1 for d in (.1,5.,5.,15.)]
        if region == "total": expected_tissue = tissue_total
        elif region == "target": expected_tissue = [0.,0.,0.,volumes["target"]]
        elif region == "surface_0_5": expected_tissue = [total*.1/25.1,total*4.9/25.1,0.,0.]
        elif region == "subsurface_5_10": expected_tissue = [0.,total*.1/25.1,total*4.9/25.1,0.]
        elif region == "remaining": expected_tissue = [0.,0.,total*.1/25.1,tissue_total[3]-volumes["target"]]
        else: expected_tissue = [*tissue_total[:3],tissue_total[3]-volumes["target"]]
        for i,value in enumerate(expected_tissue):
            if value == 0:
                # This is the producer's declared partition roundoff contract,
                # not a near-zero ratio floor. Tiny positive remainders may
                # survive its bounded native total-slab subtraction.
                absolute_roundoff = 128*math.ulp(1.)*volumes["total"]
                audit.check(identity+":"+region+":tissue_layer"+str(i),abs(tissue[str(i)]) <= absolute_roundoff,
                            actual=tissue[str(i)],expected=0.,absolute_roundoff_m3=absolute_roundoff,
                            definition="native partition128eps times represented domain volume; no relative ratio for zero")
            else:
                audit.compare(identity+":"+region+":tissue_layer"+str(i),tissue[str(i)],value)
        for metric, threshold in data.get("high_modulation_volume", {}).items():
            require(metric in volume["thresholds"], "Undeclared high-modulation threshold")
            for value in threshold.values():
                audit.check(identity+":"+region+":threshold_fraction", finite(value.get("fraction")) and 0 <= value["fraction"] <= 1+1e-12)
                audit.compare(identity+":"+region+":threshold_volume_fraction", value["volume_m3"], value["fraction"]*volumes[region])
                audit.compare(identity+":"+region+":threshold_mm3", value["volume_mm3"], value["volume_m3"]*1e9)
                audit.check(identity+":"+region+":threshold_operator", value.get("comparison_operator") == ">=")
        high = data.get("high_modulation_volume",{})
        audit.check(identity+":"+region+":threshold_coverage",set(high) == set(volume.get("thresholds",{})) and all(set(entry) == {"maxTIS","fixedTIS"} for entry in high.values()))
        for key in ("maxTIS","fixedTIS"):
            ordered = sorted(volume.get("thresholds",{}),key=lambda name:volume["thresholds"][name]["value_V_m"])
            values = [high[name][key]["volume_m3"] for name in ordered]
            audit.check(identity+":"+region+":"+key+":higher_threshold_nonincreasing",all(a >= b-1e-20 for a,b in zip(values,values[1:])))
    for metric in ("maxTIS","fixedTIS","RMS"):
        target = volume["regions"]["target"]["statistics"][metric]
        for region in ("surface_0_5","subsurface_5_10","remaining","off_target"):
            off = volume["regions"][region]["statistics"][metric]
            for key, numerator, denominator in (("target_mean_over_off_p95",target["mean"],off["p95"]),
                                               ("target_p10_over_off_p95",target["p10"],off["p95"]),
                                               ("target_mean_over_off_max",target["mean"],off["max"])):
                saved = volume["ratios"][metric][region][key]
                if denominator:
                    audit.compare(identity+":"+metric+":"+region+":"+key,saved,numerator/denominator)
                else:
                    audit.check(identity+":"+metric+":"+region+":"+key+":undefined",saved is None)
    if not volume.get("thresholds"):
        audit.hold(identity+":high_modulation_volume", "No frozen thresholds in saved result; no zero or passing threshold score is fabricated.")
    audit.hold(identity+":native_ROI_reprojection", "Stored statistics/partition metadata only; native E/volume arrays are never decoded or reprojected.")


def stored_scaling_checks(audit, post, channels):
    items = post.get("actual_transfer_amplitude_scaling_checks", [])
    carriers = [None] if channels == 2 else [3000,3030]
    audit.check(post["id"]+":scaling_carrier_scope", len(items) == len(carriers) and {v.get("actual_carrier_Hz") for v in items} == set(carriers))
    for item in items:
        label = post["id"]+":scaling:"+str(item.get("actual_carrier_Hz"))
        audit.check(label+":actual_transfer_test", item.get("amplitude") == .73 and item.get("source_transfer_re_evaluated") is True and item.get("new_PDE") == 0)
        tests = item.get("checks", {})
        audit.check(label+":nine_metrics", set(tests) == set((*LINEAR_CHECKS,*QUADRATIC_CHECKS)))
        for key, row in tests.items():
            error = row.get("relative_error")
            audit.check(label+":"+key+":saved_pass", row.get("passed") is True and finite(error) and 0 <= error <= 2e-12)
            audit.compare(label+":"+key+":actual_expected", row["actual"], row["expected"], 2e-12)
            carrier = item.get("actual_carrier_Hz")
            primaries = [c for c in post["conditions"] if c["waveform"] == "square_3h" and c["actual_fundamental_Hz"] == ([3000,3030] if carrier is None else [carrier])]
            require(len(primaries) == 1, "Scaling primary carrier is ambiguous")
            amplitude = .73 if key in LINEAR_CHECKS else .73**2
            audit.compare(label+":"+key+":primary_scalar_join",row["expected"],primaries[0]["metrics"][key]*amplitude,2e-12)


def audit_probes(audit, post, case, conditions):
    file_info = post["artifacts"]["files"]["probes.json"]
    probes = audit.read(Path(case["postprocess"]["path"]).parent/"probes.json", file_info["SHA256"])
    audit.check(case["id"]+":probe_artifact_complete", probes.get("status") == "complete")
    by_id = {p["id"]:p for p in probes["conditions"]}
    audit.check(case["id"]+":probe_condition_identity", len(by_id) == len(probes["conditions"]) == len(conditions) and set(by_id) == {c["id"] for c in conditions})
    for condition in conditions:
        primary = by_id[condition["id"]]
        probe = primary["probe40"]
        name = condition["id"]+":probe40"
        audit.check(name+":complete", primary["waveform"] == condition["waveform"] and probe.get("status") == "complete" and probe.get("expected_waveform_count") == 40 and probe.get("counts") == dict(complete=40,held_data_missing=0,validation_failed=0))
        audit.check(name+":stored_phi_E_gate", probe.get("numerical_checks", {}).get("all_passed") is True)
        measurements = probe.get("measurements", [])
        audit.check(name+":all_statuses", len(measurements) == 40 and all(r.get("status") == "complete" for r in measurements))
        centres = {"centre":(0.,0.),"x_plus":(5.,0.),"x_minus":(-5.,0.),"y_plus":(0.,5.),"y_minus":(0.,-5.)}
        expected = {f"d{depth:g}-{position}-{axis}" for depth in (5.,10.,15.,20.) for position in centres for axis in ("X","Y")}
        audit.check(name+":unique_user_grid",len({r.get("id") for r in measurements}) == 40 and {r.get("id") for r in measurements} == expected
                    and probe.get("measurement_grid") == dict(depths_mm=[5.,10.,15.,20.],plus_centre_pitch_mm=5.,tip_gap_mm=5.,centres_per_depth=5,directions_per_centre=2))
        for row in measurements:
            x,y = centres[row["position"]]
            depth,axis = row["depth_from_skin_surface_mm"],row["axis"]
            dx,dy = (2.5,0.) if axis == "X" else (0.,2.5)
            audit.check(name+":"+row["id"]+":endpoints",depth in (5.,10.,15.,20.) and axis in ("X","Y") and row["id"] == f"d{depth:g}-{row['position']}-{axis}" and row["centre_mm"] == [x,y,depth] and row["plus_mm"] == [x+dx,y+dy,depth] and row["minus_mm"] == [x-dx,y-dy,depth] and row["tip_gap_mm"] == 5. and row["plus_centre_pitch_mm"] == 5.)
        for frequency, gate in probe.get("numerical_checks",{}).get("per_frequency",{}).items():
            indices = gate.get("checked_cell_indices",[])
            audit.check(name+":"+str(frequency)+":saved_native_gate",gate.get("passed") is True
                        and gate.get("checked_cell_count",0) == len(indices) > 0 and len(set(indices)) == len(indices)
                        and not gate.get("unsupported_cell_indices") and not gate.get("failed_cell_indices")
                        and sum(gate.get("checked_cells_by_layer",{}).values()) == len(indices)
                        and gate.get("relative_tolerance") == 2e-10 and gate.get("absolute_tolerance_V_m") == 1e-10
                        and finite(gate.get("max_absolute_error_V_m")))
        gate_frequencies = FREQUENCIES if case["channels"] == 2 else (condition["actual_fundamental_Hz"][0],3*condition["actual_fundamental_Hz"][0])
        audit.check(name+":native_gate_frequency_scope",set(probe.get("numerical_checks",{}).get("per_frequency",{})) == {str(f) for f in gate_frequencies})
        provenance = probe["provenance"]
        suffix = "" if case["channels"] == 2 else f"-C1-{condition['actual_fundamental_Hz'][0]}Hz"
        audit.check(name+":primary_native_provenance", provenance.get("source_run_id") == audit.run.name and provenance.get("source_condition_id") == case["id"]
                    and provenance.get("source_candidate_id") == case["id"]+suffix+"-square_3h"
                    and provenance.get("input_sha256") == post["input_manifest_sha256"]
                    and provenance.get("code_sha256") == post["postprocessor_sha256"]
                    and provenance.get("result_sha256") == digest(post["validation"]))
    audit.hold(case["id"]+":native_phi_E_recalculation", "Verify saved gate/status/provenance only; no tissue potential, E, probe spectrum or waveform is decoded/recomputed.")


def compare_circuit_condition(audit, condition, case, matrices):
    channels = case["channels"]
    wave, actual_f = condition["waveform"], condition["actual_fundamental_Hz"]
    carrier = None if channels == 2 else actual_f[0]
    suffix = "" if channels == 2 else f"-C1-{carrier}Hz"
    audit.check(condition["id"]+":identity_source_phase", condition["id"] == case["id"]+suffix+"-"+wave and actual_f == ([3000,3030] if channels == 2 else [carrier]) and condition.get("source_Vpp_per_output") == 1. and condition.get("phase_deg") == [0.]*channels)
    expected, spectra, loaded, losses = independent_circuit(matrices, channels, wave, carrier, condition["phase_deg"])
    stored = condition["metrics"]
    for key, value in expected.items():
        if isinstance(value,list):
            require(len(stored[key]) == channels, "Stored per-output current count differs")
            for i,item in enumerate(value):
                audit.compare(condition["id"]+":"+key+":"+str(i), stored[key][i], item)
        else:
            audit.compare(condition["id"]+":"+key, stored[key], value)
    audit.compare(condition["id"]+":all_losses_vs_source", sum(losses), expected["source_power_W"])
    audit.compare(condition["id"]+":matrix_source_resistor_vs_50ohm", losses[5], expected["source_resistor_power_W"])
    for field, values in (("source_current_spectrum",spectra),("loaded_metal_voltage_spectrum",loaded)):
        rows = stored[field]
        audit.check(condition["id"]+":"+field+":frequencies", len(rows) == 4 and {r["frequency_Hz"] for r in rows} == set(FREQUENCIES))
        for row in rows:
            f = row["frequency_Hz"]
            unit = "A" if field == "source_current_spectrum" else "V"
            for axis in ("real","imaginary"):
                require(len(row[axis+"_"+unit]) == channels, "Stored spectrum channel count differs")
                for i, value in enumerate(values[f]):
                    actual = row[axis+"_"+unit][i]
                    target = value.real if axis == "real" else value.imag
                    # Components may be exactly zero; use complex magnitude as
                    # the denominator rather than a spurious tiny-component error.
                    error = abs(actual-target)/abs(value) if value != 0 else (0. if actual == target else None)
                    audit.check(condition["id"]+":"+field+":"+str(f)+":"+axis+":"+str(i), finite(actual) and error is not None and error <= TOLERANCE,
                                relative_error=error,zero_reference_mismatch=value == 0 and actual != target,
                                denominator_definition="magnitude of exact expected complex current/voltage for componentwise vector-norm comparison; zero vector requires exact zero")
    if channels == 1:
        audit.check(condition["id"]+":C1_not_TIS", stored["target20_modulation_V_m"] == 0. and condition.get("C1_two_carrier_TIS") == 0.)
    for key in ("surface_J_RMS_max_A_m2","surface_J_RMS_p95_A_m2","contact_voltage_RMS_max_V","target20_modulation_V_m","target20_total_E_RMS_V_m"):
        audit.hold(condition["id"]+":"+key, "Source/loss matrices do not contain contact density or spatial E; scalar finiteness/metadata may be checked, but no independent spatial recalculation is claimed.")


def terminal(controller, summary):
    require(controller.get("status") not in (None,"prepared","running") and controller.get("status") == summary.get("status") and controller.get("phase") in ("finished","stopped"), "Source is not terminal")
    pid, ticks = controller.get("pid"), controller.get("proc_start_ticks")
    if type(pid) is int and type(ticks) is int and pid > 0:
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")",1)[1].split()
        except FileNotFoundError:
            fields = None
        require(fields is None or fields[0] == "Z" or int(fields[19]) != ticks, "Exact source PID/startticks still alive")


def condition_namespace(ident, channels, conditions):
    suffixes = ("",) if channels == 2 else ("-C1-3000Hz","-C1-3030Hz")
    expected = {ident+suffix+"-"+wave for suffix in suffixes for wave in WAVES}
    require(len(conditions) == len(expected) and {c["id"] for c in conditions} == expected,
            "Wrong or duplicated saved waveform/carrier condition namespace")


def audit_run(run, output):
    entry_started = time.monotonic()
    run, output = Path(run).resolve(), Path(output).resolve()
    require(run.name.startswith("selectivity-design-") and run.parent.name == "runs", "Unexpected source owner")
    require(output.parent == run/"audit" and not output.exists(), "New audit output must be in source audit directory; preserve existing output")
    # Read-only terminal preflight, before any output or circuit matrix access.
    controller = json.loads((run/"controller.json").read_text())
    summary = json.loads((run/"summary.json").read_text())
    terminal(controller,summary)
    source_seconds = summary.get("wall_seconds")
    prep_seconds = summary.get("preparation_wall_seconds")
    require(finite(source_seconds) and finite(prep_seconds) and source_seconds >= 0 and prep_seconds >= 0, "Missing saved source time budget")
    remaining = 6600-source_seconds-prep_seconds
    require(remaining > 0, "Original6600s budget exhausted; no audit launched")
    budget = Budget(run,min(600.,remaining),entry_started)
    audit = Audit(run,budget)
    lock_path = Path(tempfile.gettempdir())/f"ngg-mesh-validation-{os.getuid()}.lock"
    with ExitStack() as stack:
        for path in (lock_path,run/".execution.lock",run/".saved-results-audit.lock"):
            handle = stack.enter_context(path.open("a+"))
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.lockf(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        audit.pin(Path(__file__))
        summary = audit.read(run/"summary.json")
        controller = audit.read(run/"controller.json")
        terminal(controller,summary)
        budget.check()
        old_handlers = {s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGINT,signal.SIGTERM)}
        def stop(*_):
            raise TimeoutError("Audit interrupted or time/resource budget exceeded")
        for sig in old_handlers:
            signal.signal(sig,stop)
        signal.setitimer(signal.ITIMER_REAL,max(.001,budget.deadline-time.monotonic()))
        result = dict(schema="independent-selectivity-saved-circuit-audit-v1",source_run_id=run.name,
                      started_utc=now(),source_status=summary["status"],source_complete=summary["status"] == "complete",
                      resource_limits=dict(audit_seconds=min(600.,remaining),original_total_seconds=6600,source_plus_preparation_seconds=source_seconds+prep_seconds,max_RSS_bytes=MAX_RSS,simultaneous_jobs=1),
                      original_source_results_unchanged=True,new_PDE=0,new_Java=0,production_postprocessor_imports=0,
                      E_phi_density_grid_volume_waveform_decodes=0,source_loss_circuit_matrix_decode_only=True)
        try:
            manifest = audit.read(run/"manifest.json")
            pre = audit.read(run/"preregistration.json",manifest["preregistration_sha256"])
            audit.check("manifest_owner_schema",manifest.get("schema") == "fixed-phantom-selectivity-execution-v1" and manifest.get("status") == "prepared" and manifest.get("output_run") == str(run))
            for path, expected in pre["code_sha256"].items():
                require(manifest["guard_hashes"].get(path) == expected,"Code/manifest SHA namespace differs")
                audit.pin(path,expected)
            publication = audit.read(run/"execution-publication.json")
            commit = publication.get("commit_sha","")
            audit.check("publication_manifest_prereg", publication.get("status") == "published_verified" and publication.get("remote_ref_verified") is True
                        and isinstance(commit,str) and len(commit) == 40 and all(c in "0123456789abcdef" for c in commit)
                        and publication.get("manifest_sha256") == audit.pins[str(run/"manifest.json")]
                        and publication.get("preregistration_sha256") == audit.pins[str(run/"preregistration.json")])
            versions = {v["case_id"]:v for v in summary["source_result_versions"]}
            require(len(versions) == len(summary["source_result_versions"]), "Duplicate source result versions")
            cases = summary["cases"]
            require(len({r["id"] for r in cases}) == len(cases) and set(versions) == {r["id"] for r in cases}, "Completed case/version scope differs")
            new_complete = [r for r in cases if not pre["case_pool"][r["id"]].get("existing_reference")]
            jobs = summary.get("new_PDE_jobs")
            audit.check("registered_execution_count_caps",type(jobs) is int and len(new_complete) <= jobs <= 25 and len(cases) <= 26
                        and sum(r["channels"] == 2 for r in new_complete) <= 19 and sum(r["channels"] == 1 for r in new_complete) <= 6)
            if summary["status"] == "complete":
                audit.check("completed_new_case_job_join",jobs == len(new_complete))
            result["completed_cases_audited"] = []
            result["preserved_incomplete_cases"] = []
            for item in cases:
                ident = item["id"]
                case = audit.read(run/"cases"/(ident+".json"),versions[ident]["result_sha256"])
                plan = pre["case_pool"][ident]
                require(case.get("status") == "complete" and all(case.get(k) == v for k,v in plan.items()), "Incomplete/unplanned source case")
                audit.pin(case["config_file"],plan["config_sha256"])
                require(versions[ident]["config_sha256"] == plan["config_sha256"], "Version/config SHA mismatch")
                postpath = run/"postprocess"/ident/"summary.json"
                require(Path(case["postprocess"]["path"]).resolve() == postpath and item["postprocess"] == case["postprocess"], "Case/ledger/post pointer mismatch")
                post = audit.read(postpath,case["postprocess"]["sha256"])
                audit.check(ident+":post_complete_normalization", post.get("status") == "complete" and post.get("id") == ident and post.get("source_normalization") == NORMALIZATION and post.get("source_inputs_unchanged") is True)
                audit.check(ident+":frozen_postprocessor_SHA", post["postprocessor_sha256"] == pre["code_sha256"][str(Path(__file__).parent/"selectivity_postprocess.py")])
                audit.check(ident+":canonical_input_join", digest(post["input_sha256"]) == post["input_manifest_sha256"])
                audit.check(ident+":case_validation_join", case["validation"] == post["validation"])
                for key,limit in dict(max_residual=2e-7,max_power_error=2e-7,max_current_error=2e-6,max_area_relative_error=1e-10,max_interface_normal_current_relative_error=2e-7).items():
                    if key not in post["validation"] and case.get("existing_reference"):
                        audit.check(ident+":"+key+":unavailable_preserved",post["validation_gate_status"].get(key,{}).get("status") == "not_available_original")
                        audit.hold(ident+":"+key,"Original Best1 exporter did not save this gate; no pass value is fabricated.")
                    else:
                        value = post["validation"].get(key)
                        audit.check(ident+":"+key,finite(value) and 0 <= value <= limit)
                audit.check(ident+":source_case_resource_limits",finite(case["resources"].get("wall_seconds")) and 0 <= case["resources"]["wall_seconds"] <= 600 and 0 <= case["resources"].get("peak_sampled_aggregate_rss_bytes",-1) <= MAX_RSS)
                folder = Path(case["source_basis_dir"]).resolve() if case.get("existing_reference") else run/"bases"/ident
                declared = case["basis_file_sha256"]
                audit.check(ident+":raw_manifest_declarations", all(post["input_sha256"].get(str(folder/name)) == value for name,value in declared.items()))
                raw_meta = audit.read(folder/"mesh-metadata.json",declared["mesh-metadata.json"])
                raw_validation = audit.read(folder/"validation.json",declared["validation.json"])
                audit.check(ident+":actual_raw_metadata_validation_join",raw_meta == post["mesh_metadata"] and raw_validation == post["validation"])
                expected_exporter = "RsWindowTisBasis" if case.get("existing_reference") else "SelectivityShapeBasis"
                audit.check(ident+":actual_producer_config_frequency",raw_meta.get("exporter_class") == expected_exporter and raw_meta.get("channels") == case["channels"]
                            and raw_meta.get("config_sha256") == plan["config_sha256"] and raw_meta.get("frequencies_Hz") == list(FREQUENCIES)
                            and raw_meta.get("h_xy_mm") == case["h_xy_mm"] and raw_meta.get("sc_cells") == case["sc_cells"])
                raw_normalization = raw_meta.get("basis_normalization") if case.get("existing_reference") else dict(
                    source_peak_V=raw_meta.get("source_peak_V"),source_Vpp=2*raw_meta.get("source_peak_V",-1),
                    source_resistance_ohm=raw_meta.get("source_resistance_ohm"),phasor_exponent="+jomega_t" if raw_meta.get("phasor_convention") == "peak,+jomega_t" else None)
                audit.check(ident+":actual_raw_normalization",raw_normalization == NORMALIZATION)
                # Large field/phi/density/grid/archive hashes are declaration
                # joins only here; their bytes are neither opened nor decoded.
                matrices = load_circuits(audit,folder,case["channels"],declared)
                conditions = post["conditions"]
                condition_namespace(ident,case["channels"],conditions)
                stored_scaling_checks(audit,post,case["channels"])
                audit_probes(audit,post,case,conditions)
                for condition in conditions:
                    compare_circuit_condition(audit,condition,case,matrices)
                    volume_checks(audit,condition["id"],condition["volume_metrics"],case["volume_metadata"]["geometry_volume_tolerance_relative"])
                if case.get("existing_reference"):
                    reference = plan["existing_reference_pins"]
                    original = audit.read(reference["source_case_path"],reference["source_case_sha256"])
                    old = {m["waveform"]:m for m in original["metrics"]}
                    for condition in conditions:
                        for key in REFERENCE_KEYS:
                            audit.check("reference24:"+condition["waveform"]+":"+key,condition["metrics"][key] == old[condition["waveform"]][key])
                result["completed_cases_audited"].append(dict(id=ident,channels=case["channels"],conditions=len(conditions),circuit_scalars_per_condition=7+case["channels"],existing_reference=bool(case.get("existing_reference"))))
            for ident in pre["case_pool"]:
                if ident not in versions:
                    path = run/"cases"/(ident+".json")
                    value = audit.read(path) if path.exists() else {}
                    result["preserved_incomplete_cases"].append(dict(id=ident,status=value.get("status","not_run"),promoted_to_complete=False))
            audit.recheck()
            budget.check()
            failed = sum(not row["passed"] for row in audit.checks)
            result.update(status="passed" if failed == 0 else "failed_saved_checks",check_count=len(audit.checks),failed_checks=failed)
        except BaseException as error:
            signal.setitimer(signal.ITIMER_REAL,0)
            result.update(status="audit_failed",error_type=type(error).__name__,error=str(error),source_status_preserved=summary["status"])
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            for sig,handler in old_handlers.items():
                signal.signal(sig,handler)
        result.update(finished_utc=now(),wall_seconds=time.monotonic()-budget.started,
                      peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                      input_file_SHA256=audit.pins,checks=audit.checks,held=audit.held,
                      limitations=["Source/loss independent circuit identities only; no spatial E/J/contact voltage or native ROI/waveform recomputation.",
                                   "Stored phi-E/probe/ROI statuses and hashes are metadata evidence, not independent field convergence.",
                                   "Uncompleted source cases remain incomplete; this audit cannot promote source execution status.",
                                   "Independent SC/XY/whole3D/contact/instrumentation/physiology/force/safety holds remain unchanged."])
        if result["wall_seconds"] > min(600.,remaining) or result["peak_RSS_bytes"] > MAX_RSS:
            result.update(status="audit_resource_limit_exceeded",resource_failure_preserved=True)
        output.parent.mkdir(exist_ok=True)
        with output.open("x") as stream:
            json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
            stream.write("\n")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    receipt = audit_run(args.run,args.output)
    print(json.dumps(dict(status=receipt["status"],output=str(args.output),checks=receipt.get("check_count"),new_PDE=0)))
    raise SystemExit(0 if receipt["status"] == "passed" else 2)
