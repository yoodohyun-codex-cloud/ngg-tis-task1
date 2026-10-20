#!/usr/bin/env python3
"""Rank cached Task 1 evidence for finite diagnostics; never adopt or solve.

Only source-bound JSON/configuration caches are read through results_view.
No native field, potential, volume array, plotting or research-module import.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import time

import task1_results_view as view

ROOT = Path(__file__).resolve().parents[1]
MAX_ROWS = 12
MAX_BASELINE_DISCOVERY = 128
BURDEN_KEYS = ('Jmax_mA_cm2', 'J95_mA_cm2', 'contact_V_RMS_mV', 'SC_loss_uW',
    'contact_loss_uW', 'source_power_uW', 'bulk_skin_Jmax_mA_cm2',
    'bulk_skin_J95_mA_cm2', 'skin_SC_plus_dermis_loss_uW')
REQUIRED_VALUES = ('ROI_mean_V_cm', 'ROI_P10_V_cm', 'superficial_P95_V_cm',
                   'off_target_P95_V_cm', 'global_max_V_cm', *BURDEN_KEYS)


def baseline_identity(item):
    return item['circuit']['n_pads'] == 4 and item['circuit']['n_outputs'] == 2 and (
        item['case'].get('design_id') == 'baseline-square15'
        or item['case'].get('control') == 'original_four_square')


def condition(item):
    rows = item['conditions']
    if (len(rows) != 1 or item['circuit']['n_outputs'] != 2
            or item['circuit']['n_pads'] not in (4, 8, 12, 16)):
        raise ValueError('One explicit two-output TIS square condition required; C1/diagnostics cannot be ranked')
    row = rows[0]
    if (row['waveform'] != 'square_3h' or row['actual_fundamental_Hz'] != [3000, 3030]
            or row['phase_deg'] != [0., 0.] or row['source_Vpp_per_output'] != 1.):
        raise ValueError('Retain registered later 3000/3030Hz square_3h phase0/0 1Vpp conditions')
    return row


def finite_values(values):
    return values is not None and all(isinstance(values.get(key), (int, float))
        and math.isfinite(values[key]) and values[key] >= 0 for key in REQUIRED_VALUES)


def high_volume_status(row, baseline):
    values = row['values']['composite_full_skin']
    raw = (row.get('spatial') or {}).get('high_modulation', {})
    if values is None or values['amplitude_scale'] != 1.:
        return dict(status='held_high_modulation_normalization_missing',
            reason='Raw aggregate volumes cannot be rescaled into thresholded volumes at matched burden',
            raw_unscaled_only=raw, matched_burden_volume=None, adoption_allowed=False)
    ref = baseline['values']['raw']
    cutoffs = dict(baseline_ROI_P10=ref['ROI_P10_V_cm']*100,
                   half_baseline_ROI_mean=.5*ref['ROI_mean_V_cm']*100)
    if not all(key in raw and math.isclose(raw[key].get('cutoff_V_m', -1), value,
            rel_tol=1e-12, abs_tol=1e-15) for key, value in cutoffs.items()):
        return dict(status='held_high_modulation_normalization_missing',
            reason='Unit-scale raw high-volume cutoffs do not match this selected same-grid baseline',
            matched_burden_volume=None, adoption_allowed=False)
    return dict(status='available_at_exact_unit_scale', matched_burden_volume=raw,
                frozen_cutoffs_V_m=cutoffs, adoption_allowed=False)


def evaluate(row, reference):
    values, base = row['values']['composite_full_skin'], reference['values']['composite_full_skin']
    result = dict(numerically_promising=False, ranking_eligible_for_diagnostic=False,
        gains=None, checks={}, burden_absolute={}, holds=[], score=None,
        high_modulation=high_volume_status(row, reference), adopted=False)
    if not finite_values(values) or not finite_values(base):
        result['holds'].append('held_required_source_bound_full_skin_audit_or_finite_metrics_missing')
        return result
    if (base['amplitude_scale'] != 1. or not 0 < values['amplitude_scale'] <= 1.
            or min(base['ROI_mean_V_cm'], base['ROI_P10_V_cm'], base['superficial_P95_V_cm'],
                   base['off_target_P95_V_cm'], base['global_max_V_cm'],
                   values['superficial_P95_V_cm'], values['off_target_P95_V_cm']) <= 0):
        result['holds'].append('held_nonpositive_comparator_or_inconsistent_composite_scale')
        return result
    mean = values['ROI_mean_V_cm']/base['ROI_mean_V_cm']
    p10 = values['ROI_P10_V_cm']/base['ROI_P10_V_cm']
    superficial = (values['ROI_mean_V_cm']/values['superficial_P95_V_cm'])/(base['ROI_mean_V_cm']/base['superficial_P95_V_cm'])
    off = (values['ROI_mean_V_cm']/values['off_target_P95_V_cm'])/(base['ROI_mean_V_cm']/base['off_target_P95_V_cm'])
    global_ratio = values['global_max_V_cm']/base['global_max_V_cm']
    burden = {key: dict(candidate=values[key], baseline=base[key],
        ratio=values[key]/base[key] if base[key] else (1. if values[key] == 0 else None),
        within_registered_composite_cap=values[key] <= base[key]*(1+1e-12)+1e-15) for key in BURDEN_KEYS}
    checks = dict(both_absolute_ROI_mean_P10_nonworse=mean >= 1 and p10 >= 1,
        at_least_one_absolute_gain_strictly_exceeds_1percent=max(mean, p10) > 1.01,
        target_mean_over_superficial_P95_nonworse=superficial >= 1,
        target_mean_over_all_offtarget_P95_nonworse=off >= 1,
        matched_global_maximum_not_increased=global_ratio <= 1,
        all_registered_full_skin_composite_caps_satisfied=all(value['within_registered_composite_cap'] for value in burden.values()))
    result.update(numerically_promising=all(checks.values()), ranking_eligible_for_diagnostic=True,
        gains=dict(ROI_mean=mean, ROI_P10=p10, target_mean_over_superficial_P95=superficial,
                   target_mean_over_all_offtarget_P95=off, global_max_relative_to_baseline=global_ratio),
        checks=checks, burden_absolute=burden,
        score=dict(balanced_absolute_gain_floor=min(mean, p10), geometric_mean_absolute_gain=math.sqrt(mean*p10),
                   minimum_selectivity_gain=min(superficial, off), global_max_relative_to_baseline=global_ratio))
    if not checks['all_registered_full_skin_composite_caps_satisfied']:
        result['ranking_eligible_for_diagnostic'] = False
        result['holds'].append('held_cached_composite_normalization_exceeds_registered_burden_cap')
    if result['high_modulation']['status'].startswith('held_'):
        result['holds'].append('held_high_modulation_normalization_missing')
    result['holds'].extend(['mesh_edge_contact_convergence_not_established', 'experimental_validation_not_established'])
    return result


def input_refs(item):
    paths = [item['path'], item['run']/'preregistration.json', Path(item['case']['config_file'])]
    if item.get('eligibility', {}).get('case_record_path'):
        paths.append(Path(item['eligibility']['case_record_path']))
    paths.extend(item.get('audit_paths', []))
    for skin in item.get('full_skin', {}).values():
        audit = skin['audit']
        path = Path(audit['path'])
        if view.sha(path) != audit['SHA256'] or audit['summary_sha256'] != view.sha(item['path']):
            raise ValueError('Full-skin audit reference changed or points to another summary')
        paths.append(path)
    return {str(Path(path).resolve()): view.sha(path) for path in paths}


def build_ranking(baseline_paths, summary_paths, select_max=2, *, loader=None, row_builder=None,
                  discovery_paths=None, deadline=None):
    loader, row_builder = loader or view.load_case, row_builder or view.row_data
    baseline_paths = list(dict.fromkeys(Path(path).resolve() for path in baseline_paths))
    summary_paths = [Path(path).resolve() for path in summary_paths]
    if (not baseline_paths or not summary_paths or len(summary_paths) > MAX_ROWS
            or len(set(summary_paths)) != len(summary_paths) or select_max not in (0, 1, 2)
            or len(baseline_paths) > MAX_ROWS):
        raise ValueError('Require explicit baseline(s), 1..12 unique candidate summaries and select-max0/1/2')
    loaded, references, all_refs = {}, {}, {}
    def load(path):
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError('Finite cached-ranking deadline exceeded')
        if path not in loaded:
            loaded[path] = loader(path)
            condition(loaded[path])
            all_refs.update(input_refs(loaded[path]))
        return loaded[path]
    for path in baseline_paths:
        item = load(path)
        if not baseline_identity(item):
            raise ValueError('Explicit baseline must be an unchanged original four-square/four-pad two-output reference')
        references.setdefault(item['signature'], item)
    candidates = [load(path) for path in summary_paths]
    missing = {item['signature'] for item in candidates}-set(references)
    discovery = dict(examined=0, max_cached_paths=MAX_BASELINE_DISCOVERY, rejected=[], truncated=False)
    if missing:
        paths = discovery_paths if discovery_paths is not None else sorted(ROOT.glob('data-native/cloud-*/postprocess/*/summary.json'))
        for index, path in enumerate(paths):
            if index >= MAX_BASELINE_DISCOVERY:
                discovery['truncated'] = True
                break
            discovery['examined'] += 1
            path = Path(path).resolve()
            try:
                item = load(path)
                if item['signature'] in missing and baseline_identity(item):
                    references[item['signature']] = item
                    missing.remove(item['signature'])
            except (ValueError, KeyError, FileNotFoundError) as error:
                discovery['rejected'].append(dict(path=str(path), reason=str(error)))
            if not missing:
                break
    rows = []
    for item in candidates:
        current = condition(item)
        reference = references.get(item['signature'])
        if reference is None:
            rows.append(dict(case_id=item['summary']['id'], design_id=item['case'].get('design_id', item['summary']['id']),
                run_id=item['run'].name, condition_id=current['id'], source_summary_path=str(item['path']),
                comparison_signature=item['signature'], mesh=item['summary']['mesh_metadata'],
                numerically_promising=False, ranking_eligible_for_diagnostic=False, score=None,
                status='held_matching_same_grid_baseline_missing', holds=['held_matching_same_grid_baseline_missing'], adopted=False))
            continue
        anchor = condition(reference)
        row = row_builder(item, current, anchor, reference)
        baseline = row_builder(reference, anchor, anchor, reference)
        judgment = evaluate(row, baseline)
        if baseline_identity(item):
            judgment['ranking_eligible_for_diagnostic'] = False
            judgment['holds'].append('original_four_square_control_is_reference_only')
        scale = row['values']['composite_full_skin']['amplitude_scale'] if row['values']['composite_full_skin'] else None
        losses = row.get('layer_contact_source_losses') or {}
        extra = {key: value*scale**2 for key, value in losses.get('metrics', {}).items()
                 if key.endswith('_power_W') and isinstance(value, (int, float))} if scale is not None else {}
        rows.append(dict(**row, **judgment, design_id=item['case'].get('design_id', item['summary']['id']),
            source_summary_path=str(item['path']), baseline_summary_path=str(reference['path']),
            baseline_summary_sha256=view.sha(reference['path']), baseline_config_sha256=reference['case']['config_sha256'],
            absolute_all_available_layer_losses_W_at_matched_burden=extra,
            max_source_current_RMS_mA_at_matched_burden=(row['values']['composite_full_skin'] or {}).get('max_source_current_RMS_mA'),
            extra_metric_scope='Layer losses/current are reported; unregistered individual fat/muscle/current caps are not invented'))
    def order(row):
        score = row.get('score') or {}
        return (-int(row['ranking_eligible_for_diagnostic']), -int(row['numerically_promising']),
            -score.get('balanced_absolute_gain_floor', -1), -score.get('geometric_mean_absolute_gain', -1),
            -score.get('minimum_selectivity_gain', -1), score.get('global_max_relative_to_baseline', math.inf), row['case_id'])
    rows.sort(key=order)
    selected = [row for row in rows if row['ranking_eligible_for_diagnostic']][:select_max]
    if any(view.sha(path) != expected for path, expected in all_refs.items()):
        raise ValueError('Cached source/config/registration/audit changed during ranking')
    return dict(schema='task1-candidate-ranking-v1', status='calculated_unadopted',
        created_utc=datetime.now(timezone.utc).isoformat(), code_sha256=view.sha(__file__),
        cached_reader_sha256=view.sha(ROOT/'tools/task1_results_view.py'),
        primary_baseline_summary_path=str(baseline_paths[0]),
        baselines_by_comparison_signature={signature: dict(case_id=item['summary']['id'], path=str(item['path']),
            SHA256=view.sha(item['path']), config_sha256=item['case']['config_sha256']) for signature, item in references.items()},
        input_sha256=all_refs, baseline_discovery=discovery, rows=rows,
        sorted_all_cases=[row['case_id'] for row in rows], selected_case_ids=[row['case_id'] for row in selected],
        selected_for_followup=[{key: row[key] for key in ('case_id', 'design_id', 'run_id', 'comparison_signature', 'source_summary_path')}
                               for row in selected],
        selection=dict(max_candidates=select_max, selected_case_ids=[row['case_id'] for row in selected],
            purpose='next finite diagnostic only, even if none is numerically promising', automatic_execution=False, adopted=False),
        definitions=dict(primary='Both full-skin-cap ROI mean and P10 gain>=1, with at least one strictly>1.01',
            spatial='ROImean/superficialP95 and ROImean/all-offtargetP95 nondecreasing; matched global max not increased',
            full_skin_burden_caps=list(BURDEN_KEYS), burden_arithmetic_roundoff_relative=1e-12,
            high_volume='Unavailable after non-unit amplitude scaling without native threshold-volume re-evaluation',
            diagnostic_order='eligible, numerical promise, balanced absolute gain, geometric gain, selectivity, lower global max, case ID',
            units='Cached row values retain V/cm, mA/cm2, mV, uW; additional native layer losses are W'),
        latest_baseline_unchanged=True, baseline_update_performed=False, adopted=False,
        new_PDE=0, native_array_reads=0, scientific_or_experimental_validation_claimed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-summary', type=Path, action='append', required=True)
    parser.add_argument('--summary', type=Path, action='append', required=True)
    parser.add_argument('--select-max', type=int, choices=[0, 1, 2], default=2)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Never overwrite ranking evidence')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = ROOT/'runtime/task1-budget.json'
        ledger = view.read(ledger_path)
        if ledger['limit_seconds'] != 6600 or ledger['spent_seconds'] >= 6600:
            raise ValueError('Preserve existing 6600s budget; no remaining ranking allocation')
        seconds = min(180., 6600-ledger['spent_seconds'])
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        output.parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(output.parent).free < 2*1024**3:
            raise ValueError('Unchanged2GiB disk reserve unavailable')
        start, status = time.monotonic(), 'failed'
        def timeout(signum, frame):
            raise TimeoutError('Ranking exceeded finite180s/remaining6600s allocation')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            result = build_ranking(args.baseline_summary, args.summary, args.select_max, deadline=start+seconds)
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak >= 3*1024**3:
                raise MemoryError('Ranking exceeded existing3GiB RSS budget')
            result['resources'] = dict(wall_seconds=time.monotonic()-start, max_seconds=seconds,
                peak_process_RSS_bytes=peak, CPU_count=1, simultaneous_jobs=1)
            payload = json.dumps(result, indent=2, allow_nan=False)+'\n'
            if shutil.disk_usage(output.parent).free < 2*1024**3+len(payload.encode()):
                raise ValueError('Output plus unchanged2GiB reserve unavailable')
            with output.open('x') as stream:
                stream.write(payload)
            status = result['status']
            print(json.dumps(dict(status=status, output=str(output), selected_case_ids=result['selected_case_ids'])))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-start
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id='cached-candidate-ranking', stage='candidate_ranking',
                seconds=elapsed, status=status, finished_utc=datetime.now(timezone.utc).isoformat()))
            temporary = ledger_path.with_name('task1-budget.json.partial')
            temporary.write_text(json.dumps(ledger, indent=2)+'\n')
            temporary.replace(ledger_path)


if __name__ == '__main__':
    main()
