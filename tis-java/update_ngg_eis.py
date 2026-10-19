"""Read the three confirmed bare-NGG EIS workbooks without modifying them.

Uses only the Python standard library. Writes a measured-data JSON profile,
not a fitted dry-contact model or new TIS simulation results.
"""
from pathlib import Path
import bisect
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "NGG electrode EIS result" / "1015~1022"
OUTPUT = ROOT / "electrode-data" / "bare-ngg-eis.json"
SAMPLES = (("0 0.xlsx", 0), ("1d 0.xlsx", 1), ("2d 0.xlsx", 2))
NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
AREA_M2 = 1e-4


def impedance_values(frequency, real, imag):
    return {
        "frequency_Hz": frequency,
        "Z_real_ohm": real,
        "Z_imag_ohm": imag,
        "Z_magnitude_ohm": math.hypot(real, imag),
        "phase_deg": math.degrees(math.atan2(imag, real)),
        "measured_Z_times_area_real_ohm_m2": real * AREA_M2,
        "measured_Z_times_area_imag_ohm_m2": imag * AREA_M2,
    }


def read_spectrum(path):
    # These instrument exports declare dimension=A1 although rows 1:31 exist.
    # Read actual XML cells rather than trusting the declared used range.
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.findall("s:sheets/s:sheet", NS)
        if len(sheets) != 1 or sheets[0].get("name") != "Sheet1":
            raise ValueError(f"Unexpected sheet layout: {path.name}")
        xml = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        points = []
        for row in xml.findall("s:sheetData/s:row", NS):
            row_number = int(row.get("r"))
            if row_number == 1:
                continue
            cells = {}
            for cell in row.findall("s:c", NS):
                if cell.find("s:f", NS) is not None:
                    raise ValueError("Expected measured values, found a formula")
                value = cell.find("s:v", NS)
                if value is not None:
                    col = "".join(c for c in cell.get("r") if c.isalpha())
                    cells[col] = float(value.text)
            if not cells:
                continue
            if not all(k in cells for k in "ABCDEFG"):
                raise ValueError(f"Incomplete measured row {row_number}: {path.name}")
            if not all(math.isfinite(v) for v in cells.values()) or cells["B"] <= 0:
                raise ValueError("Non-finite data or nonpositive frequency")
            # The source exports -Z'' and -Phase. Store actual Im(Z) and phase.
            point = impedance_values(cells["B"], cells["C"], -cells["D"])
            if not math.isclose(point["Z_magnitude_ohm"], cells["E"], rel_tol=1e-9):
                raise ValueError(f"Magnitude mismatch: {path.name}, row {row_number}")
            if abs(point["phase_deg"] + cells["F"]) > 1e-7:
                raise ValueError(f"Phase mismatch: {path.name}, row {row_number}")
            point.update({
                "source_range": f"B{row_number}:G{row_number}",
                "source_index": cells["A"],
                "exported_minus_Z_imag_ohm": cells["D"],
                "exported_Z_magnitude_ohm": cells["E"],
                "exported_minus_phase_deg": cells["F"],
                "measurement_elapsed_time_s": cells["G"],
            })
            points.append(point)
    points.sort(key=lambda p: p["frequency_Hz"])
    frequencies = [p["frequency_Hz"] for p in points]
    if len(points) != 30 or len(set(frequencies)) != 30:
        raise ValueError(f"Expected 30 unique frequency points: {path.name}")
    if frequencies[0] != 1 or frequencies[-1] != 10000:
        raise ValueError(f"Unexpected frequency span: {path.name}")
    return points


def interpolate_complex(points, frequency):
    frequencies = [p["frequency_Hz"] for p in points]
    if frequency < frequencies[0] or frequency > frequencies[-1]:
        raise ValueError("No extrapolation outside the measured frequency range")
    index = bisect.bisect_left(frequencies, frequency)
    if frequencies[index] == frequency:
        low = high = points[index]
        weight = 0.0
    else:
        low, high = points[index - 1], points[index]
        weight = math.log(frequency / low["frequency_Hz"]) / math.log(
            high["frequency_Hz"] / low["frequency_Hz"]
        )
    real = low["Z_real_ohm"] + weight * (high["Z_real_ohm"] - low["Z_real_ohm"])
    imag = low["Z_imag_ohm"] + weight * (high["Z_imag_ohm"] - low["Z_imag_ohm"])
    result = impedance_values(frequency, real, imag)
    result.update({
        "value_kind": "measured" if low is high else "interpolated",
        "bracket_frequency_Hz": [low["frequency_Hz"], high["frequency_Hz"]],
        "source_ranges": list(dict.fromkeys([low["source_range"], high["source_range"]])),
        "log_frequency_weight": weight,
    })
    return result


def main():
    profile = {
        "schema_version": 1,
        "updated_date": "2026-10-17",
        "material": "bare Nano Gap Gold (NGG)",
        "PEDOT_PSS_deposition_thickness_nm": 0,
        "filename_convention": "[PBS swelling time] [PEDOT:PSS deposition thickness]",
        "filename_convention_status": "confirmed by user after correction",
        "reference_state": "initial",
        "measurement": {
            "system": "three-electrode EIS",
            "exposed_working_electrode_area_cm2": 1.0,
            "exposed_working_electrode_area_m2": AREA_M2,
            "electrolyte": {
                "stock": "1x PBS",
                "diluent": "DI water",
                "stock_to_DI_ratio": [8, 72],
                "ratio_basis": "assumed volume ratio",
                "nominal_final_PBS_strength_x": 8 / (8 + 72),
                "concentration_basis": "calculated dilution, not measured ionic concentration",
            },
            "reference_electrode": None,
            "counter_electrode": None,
            "AC_excitation_amplitude": None,
            "DC_bias_or_OCP": None,
            "temperature_C": None,
            "replicate_count_per_state": None,
            "same_specimen_followed_over_time": None,
        },
        "interpretation": {
            "complex_sign": "Z = exported Z' - j * exported (-Z''); phase = -exported (-Phase)",
            "interpolation": "linear interpolation of real and imaginary Z against ln(f); magnitude and phase recomputed from complex Z",
            "frequency_extrapolation": "prohibited",
            "area_normalization": "Z * exposed area, not Z / area; this is area-normalized measured total impedance",
            "solution_resistance_deembedded": False,
            "equivalent_circuit_fitted": False,
            "dry_skin_contact_validated": False,
            "gold_bulk_conductivity_or_sheet_resistance_inferred": False,
            "two_electrode_division_by_two_applied": False,
            "raw_measurement_applied_directly_to_solver": False,
            "derived_initial_boundary_profile": "bare-ngg-initial-fit.json (generated separately by fit_ngg_eis.py; applied in NggSweep.java)",
            "reason": "PBS three-electrode measured impedance may include uncompensated electrolyte resistance. It is not directly the dry NGG-SC contact boundary impedance.",
            "method_reference": "https://www.gamry.com/application-notes/eis/basics-of-electrochemical-impedance-spectroscopy",
        },
        "spectra": [],
    }
    for filename, day in SAMPLES:
        path = SOURCE / filename
        points = read_spectrum(path)
        state = "initial" if day == 0 else f"{day}d"
        profile["spectra"].append({
            "state": state,
            "PBS_swelling_days": day,
            "source_file": path.relative_to(ROOT.parent).as_posix(),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sheet": "Sheet1",
            "source_range": "A1:G31",
            "point_count": len(points),
            "frequency_range_Hz": [1, 10000],
            "points": points,
            "TIS_frequency_values": [interpolate_complex(points, f) for f in (2000, 2010)],
        })
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(profile, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT),
        "summary": [{"state": s["state"], "TIS_frequency_values": s["TIS_frequency_values"]} for s in profile["spectra"]],
        "checks": "90 measured complex values match exported magnitude/phase; 3 sources imported",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
