"""Apply preregistered adjacent-grid gates to completed four-pad results."""
import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def metrics(condition):
    m=condition['metrics']
    target=condition['volume_metrics']['regions']['target']['statistics']
    surface=condition['volume_metrics']['regions']['surface_0_5']['statistics']
    return {**{key:m[key] for key in ('target20_modulation_V_m','target20_total_E_RMS_V_m',
        'surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V',
        'SC_power_W','contact_power_W','source_power_W')},
        'roi_mean_TIS_V_m':target['maxTIS']['mean'],
        'roi_p10_TIS_V_m':target['maxTIS']['p10'],
        'roi_mean_RMS_V_m':target['RMS']['mean'],
        'target_superficial_p95_ratio':target['maxTIS']['mean']/surface['maxTIS']['p95']}


def evaluate(paths):
    summaries={key:read(path) for key,path in paths.items()}
    require_keys=('source_peak_V','source_resistance_ohm','phasor_convention','radius_mm',
                  'total_depth_mm','frequencies_Hz','field_reconstruction')
    baseline=summaries['xy80']
    for name,summary in summaries.items():
        if summary['status']!='complete' or summary['mesh_metadata']['channels']!=2:
            raise ValueError('Completed four-pad results required')
        if any(summary['mesh_metadata'][key]!=baseline['mesh_metadata'][key] for key in require_keys):
            raise ValueError('Source/normalization/geometry mismatch')
    gates={key:(5. if key.startswith('surface_J_') or key=='contact_voltage_RMS_max_V'
                      else 2. if key.endswith('_power_W') else 1.)
           for key in metrics(baseline['conditions'][0])}
    comparisons=[]
    for axis,before,after in [('XY','coarse','xy80'),('SC','xy80','sc4'),('bulk','xy80','bulk')]:
        bywave=[{c['waveform']:c for c in summaries[k]['conditions']} for k in (before,after)]
        for wave in ('square_3h','sine','triangle_3h'):
            a,b=map(metrics,(bywave[0][wave],bywave[1][wave]))
            rows=[]
            for key,limit in gates.items():
                if a[key]<=0:
                    raise ValueError('Positive convergence reference required')
                change=100*(b[key]/a[key]-1)
                rows.append(dict(metric=key,before=a[key],after=b[key],signed_change_percent=change,
                                 limit_percent=limit,passed=abs(change)<=limit))
            comparisons.append(dict(axis=axis,before=before,after=after,waveform=wave,
                                    passed=all(r['passed'] for r in rows),checks=rows))
    return dict(schema='task1-adjacent-grid-gates-v1',
        status='passed_for_registered_pairs' if all(c['passed'] for c in comparisons) else 'failed_gates_preserved',
        comparisons=comparisons,passed_pair_wave=sum(c['passed'] for c in comparisons),
        total_pair_wave=len(comparisons), scalar_checks=sum(len(c['checks']) for c in comparisons),
        gates_percent=gates,
        source_summaries={key:dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for key,path in paths.items()},
        interpretation='Adjacent registered axes only; no joint whole-3D convergence or continuum edge maximum certification',
        safety_limits=False,experimental_validation=False,
        decision='Do not adopt a new optimum on these coarse grids; investigate XY/contact edges and preserve failures')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--coarse-run',type=Path,required=True)
    p.add_argument('--mesh-run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    paths={'coarse':a.coarse_run/'postprocess/baseline-square15-coarse/summary.json'}
    paths.update({k:a.mesh_run/f'postprocess/baseline-square15-{k}/summary.json' for k in ('xy80','sc4','bulk')})
    report=evaluate(paths)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps({k:report[k] for k in ('status','passed_pair_wave','total_pair_wave','scalar_checks')}))
