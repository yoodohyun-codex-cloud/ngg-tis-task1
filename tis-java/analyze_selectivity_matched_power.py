"""Pairwise equal actual source power, retaining the original 1 Vpp cap.

Scalar metadata only; the frozen first analysis, fields, waveforms and volume
archives are never rewritten or decoded. The common power is the smaller raw
power of each same-mesh/same-wave pair, not a new objective or safety limit.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, csv, hashlib, json, math, os, time


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def reuse_existing(run, source):
    names = ('matched-power-analysis.json', 'matched-power-rows-cm.csv')
    receipt = run / 'matched-power-receipt.json'
    if not any((run / n).exists() for n in (*names, receipt.name)):
        return False
    if not receipt.is_file() or not all((run / n).is_file() for n in names):
        raise FileExistsError('Incomplete prior metadata outputs preserved; use a new immutable version')
    r = read(receipt)
    old = r.get('source_sha256', {})
    if (r.get('schema') != 'selectivity-matched-power-receipt-v1' or
            r.get('status') != 'complete' or r.get('source_run_id') != run.name or
            not all(old.get(p) == v for p, v in source.items()) or
            not all(sha(p) == v for p, v in old.items()) or
            set(r.get('output_sha256', {})) != set(names) or
            not all(sha(run / n) == r['output_sha256'][n] for n in names)):
        raise ValueError('Stored metadata receipt/source/output mismatch; preserve prior version')
    a = read(run / names[0])
    if a.get('source_run_id') != run.name or a.get('status') != 'complete_scalar_metadata' or a.get('source_sha256') != old:
        raise ValueError('Stored metadata owner/status differs')
    return True


LINEAR = ('roi_mean_TIS_V_cm', 'roi_P10_TIS_V_cm',
          'roi_mean_fixed_TIS_V_cm', 'roi_P10_fixed_TIS_V_cm',
          'roi_mean_E_RMS_V_cm', 'central20_TIS_V_cm',
          'central20_E_RMS_V_cm', 'Jmax_mA_cm2',
          'J95_area_weighted_mA_cm2', 'contact_voltage_RMS_mV')
POWER = ('SC_power_uW', 'contact_power_uW', 'source_power_uW')


def pair(a, b):
    pa, pb = a['source_power_uW'], b['source_power_uW']
    if not all(math.isfinite(v) and v > 0 for v in (pa, pb)):
        raise ValueError('Invalid actual source power')
    common = min(pa, pb)
    ca, cb = math.sqrt(common / pa), math.sqrt(common / pb)
    out = dict(common_source_power_uW=common,
               candidate_source_Vpp_each=ca, baseline_source_Vpp_each=cb,
               both_within_original_1Vpp_cap=ca <= 1 and cb <= 1,
               match_relative_error=abs(pa * ca * ca - pb * cb * cb) / common)
    for k in (*LINEAR, *POWER):
        av, bv = a[k] * ca ** (2 if k in POWER else 1), b[k] * cb ** (2 if k in POWER else 1)
        out['candidate_' + k], out['baseline_' + k] = av, bv
        out[k + '_gain_percent'] = 100 * (av / bv - 1) if bv else None
    out['candidate_target_mean_over_surface_P95'] = a['target_mean_over_surface_P95']
    out['baseline_target_mean_over_surface_P95'] = b['target_mean_over_surface_P95']
    out['surface_selectivity_gain_percent'] = 100 * (a['target_mean_over_surface_P95'] / b['target_mean_over_surface_P95'] - 1)
    if out['match_relative_error'] > 2e-12:
        raise ValueError('Pairwise power equality failed')
    return out


def main(run):
    started = time.monotonic()
    run = Path(run).resolve()
    if read(run / 'summary.json')['status'] == 'running':
        raise ValueError('Mutable source run')
    path = run / 'analysis.json'
    analysis = read(path)
    if (analysis.get('source_run_id') != run.name or
            analysis.get('schema') != 'fixed-phantom-selectivity-analysis-v1' or
            analysis.get('status') != 'complete_existing_results_analysis'):
        raise ValueError('Exact completed analysis/run namespace required')
    if analysis['source_summary_sha256'] != sha(run / 'summary.json'):
        raise ValueError('Stale frozen analysis')
    source = {str(path): sha(path), str(run / 'summary.json'): sha(run / 'summary.json'),
              str(run / 'audit/matched-power-interpretation.json'): sha(run / 'audit/matched-power-interpretation.json'),
              str(Path(__file__).resolve()): sha(__file__)}
    target = run / 'matched-power-analysis.json'
    if reuse_existing(run, source):
        print('unchanged matched-power metadata reused')
        return
    raw = [r for r in analysis['rows_cm'] if r['reference'] == 'latest_coated_same_mesh' and r['normalization'] == 'raw_1Vpp']
    baselines = {(r['mesh_id'], r['waveform']): r for r in raw if r['design_id'] == 'baseline-square15'}
    rows = []
    for a in raw:
        b = baselines.get((a['mesh_id'], a['waveform']))
        if b is None:
            continue
        rows.append(dict(condition_id=a['condition_id'], case_id=a['case_id'],
                         design_id=a['design_id'], mesh_id=a['mesh_id'], waveform=a['waveform'],
                         reference='latest_coated_same_mesh', baseline_condition_id=b['condition_id'], **pair(a, b)))
    # Bare entries are read from the original frozen analysis' already pinned
    # case summaries; no raw fields, arrays, or historical row bodies are read.
    for p, expected in analysis['source_inputs_sha256'].items():
        pp = Path(p)
        if pp.parent.name != 'cases' or pp.parent.parent.name != 'leader-validation-3k-20261019T030136Z':
            continue
        if sha(pp) != expected:
            raise ValueError('Bare source summary changed')
        bare = read(pp)
        for a in raw:
            if a['h_xy_mm'] != bare.get('h_xy_mm') or a['SC_cells'] != bare.get('sc_cells'):
                continue
            # Full grid identity is determined by the frozen baseline mapping;
            # do not assign the xy80 bare to a different bulk subdivision.
            mapping = {'baseline-leader': 'xy80', 'xy100-leader': 'xy100', 'sc4-leader': 'sc4', 'xy120-leader': 'original_xy120'}
            if a['mesh_id'] != mapping.get(pp.stem):
                continue
            bb = next(z for z in bare['metrics'] if z['waveform'] == a['waveform'])
            common = min(a['source_power_uW'], bb['source_power_W'] * 1e6)
            ca = math.sqrt(common / a['source_power_uW'])
            cb = math.sqrt(common / (bb['source_power_W'] * 1e6))
            rows.append(dict(condition_id=a['condition_id'], case_id=a['case_id'], design_id=a['design_id'],
                             mesh_id=a['mesh_id'], waveform=a['waveform'], reference='original_bare_1k_same_mesh',
                             baseline_condition_id=pp.stem, baseline_source_case=str(pp), baseline_source_case_sha256=expected,
                             common_source_power_uW=common, candidate_source_Vpp_each=ca, baseline_source_Vpp_each=cb,
                             both_within_original_1Vpp_cap=ca <= 1 and cb <= 1,
                             candidate_central20_TIS_V_cm=a['central20_TIS_V_cm'] * ca,
                             baseline_central20_TIS_V_cm=bb['target20_modulation_V_m'] * .01 * cb,
                             candidate_central20_E_RMS_V_cm=a['central20_E_RMS_V_cm'] * ca,
                             baseline_central20_E_RMS_V_cm=bb['target20_total_E_RMS_V_m'] * .01 * cb,
                             bare_volume_selectivity='held: no identical ROI product in the original bare summary'))
            source[str(pp)] = expected
    output = dict(schema='fixed-phantom-selectivity-matched-power-v1', status='complete_scalar_metadata',
                  source_run_id=run.name, source_summary_sha256=sha(run / 'summary.json'),
                  original_analysis_sha256=sha(path), created_utc=datetime.now(timezone.utc).isoformat(),
                  source_sha256=source, rows=rows,
                  rule='Pcommon=min(raw candidate,raw baseline); independently scale both down; E/J/V/I linear and power quadratic.',
                  distinction='Original power-cap and unclipped equal-power products remain unchanged. These pairwise absolute values respect both1Vpp caps.',
                  volume_and_waveform_recalculation=0, new_PDE=0, original_row_body_processing=0,
                  limitations=['Engineering electrical matching, not activation or safety matching.',
                               'Sampled edge/Jmax and mesh/contact holds are retained.',
                               'Each pair has its own common power; this is not one common-power ranking across all designs.'],
                  wall_seconds=time.monotonic() - started)
    for p, v in source.items():
        if sha(p) != v:
            raise ValueError('Input changed during metadata analysis')
    with target.open('x') as f:
        f.write(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with (run / 'matched-power-rows-cm.csv').open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    receipt = dict(schema='selectivity-matched-power-receipt-v1', status='complete',
                   source_run_id=run.name, source_sha256=source,
                   output_sha256={p.name: sha(p) for p in (target, run / 'matched-power-rows-cm.csv')},
                   created_utc=datetime.now(timezone.utc).isoformat(), new_PDE=0)
    with (run / 'matched-power-receipt.json').open('x') as f:
        f.write(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(status=output['status'], rows=len(rows), new_PDE=0)))


if __name__ == '__main__':
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    main(parser.parse_args().run)
