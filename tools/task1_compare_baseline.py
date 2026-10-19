"""Compare freshly computed same-grid scalars and released circuit matrices."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT/'tis-java/runs/selectivity-design-20261019T155933Z'


def compare(run, case_id):
    post = json.loads((run/'postprocess'/case_id/'summary.json').read_text())
    rows = list(csv.DictReader((HIST/'analysis-rows-cm.csv').open()))
    comparisons = []
    for condition in post['conditions']:
        matches = [r for r in rows if r['condition_id']==condition['id'] and
                   r['normalization']=='raw_1Vpp' and r['reference']=='latest_coated_same_mesh']
        if not matches:
            continue
        if len(matches)!=1:
            raise ValueError('Ambiguous historical row')
        old = matches[0]
        m = condition['metrics']
        target = condition['volume_metrics']['regions']['target']['statistics']
        surface = condition['volume_metrics']['regions']['surface_0_5']['statistics']
        values = dict(roi_mean_TIS_V_cm=target['maxTIS']['mean']/100,
                      roi_P10_TIS_V_cm=target['maxTIS']['p10']/100,
                      roi_mean_E_RMS_V_cm=target['RMS']['mean']/100,
                      central20_TIS_V_cm=m['target20_modulation_V_m']/100,
                      central20_E_RMS_V_cm=m['target20_total_E_RMS_V_m']/100,
                      Jmax_mA_cm2=m['surface_J_RMS_max_A_m2']*.1,
                      J95_area_weighted_mA_cm2=m['surface_J_RMS_p95_A_m2']*.1,
                      contact_voltage_RMS_mV=m['contact_voltage_RMS_max_V']*1000,
                      SC_power_uW=m['SC_power_W']*1e6,
                      contact_power_uW=m['contact_power_W']*1e6,
                      source_power_uW=m['source_power_W']*1e6,
                      surface_0_5_P95_TIS_V_cm=surface['maxTIS']['p95']/100,
                      surface_0_5_max_TIS_V_cm=surface['maxTIS']['max']/100)
        for key, actual in values.items():
            expected = float(old[key])
            error = abs(actual-expected)
            comparisons.append(dict(condition_id=condition['id'], metric=key, expected=expected,
                actual=actual, relative_error=error/max(abs(expected), 1e-30),
                passed=error <= 1e-14+1e-8*abs(expected)))
    matrix = []
    folder = HIST/'released-circuits'/case_id
    for path in sorted(folder.glob('*.bin')):
        new = run/'bases'/case_id/path.name
        a, b = np.fromfile(path, '<f8'), np.fromfile(new, '<f8')
        if a.shape!=b.shape:
            raise ValueError('Matrix shape mismatch')
        relative = float(np.max(abs(a-b))/max(float(np.max(abs(a))), 1e-30))
        matrix.append(dict(name=path.name, historical_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            recomputed_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
            byte_equal=path.read_bytes()==new.read_bytes(),
            relative_max_error=relative, passed=bool(np.all(abs(a-b)<=1e-14+1e-8*abs(a)))))
    if len(comparisons)!=39 or len(matrix)!=8:
        raise ValueError(f'Expected 39 scalar comparisons and 8 matrices, got {len(comparisons)}, {len(matrix)}')
    return dict(schema='task1-same-grid-reproduction-v1', run_id=run.name, case_id=case_id,
        status='passed' if all(r['passed'] for r in comparisons+matrix) else 'failed',
        source_commit=json.loads((run/'preregistration.json').read_text())['source_commit'],
        relative_tolerance=1e-8, absolute_tolerance=1e-14,
        scalar_comparisons=comparisons, circuit_comparisons=matrix,
        scope='New recomputation against released scalar and source/loss evidence; missing old E/phi not recovered',
        independent_solver_validation=False, mesh_convergence_validated=False, experimental_validation=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--case', default='baseline-square15-coarse')
    p.add_argument('--output', required=True, type=Path)
    args=p.parse_args()
    result=compare(args.run.resolve(), args.case)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False);stream.write('\n')
    print(json.dumps(dict(status=result['status'], scalars=len(result['scalar_comparisons']),
                         matrices=len(result['circuit_comparisons']))))
    raise SystemExit(0 if result['status']=='passed' else 2)
