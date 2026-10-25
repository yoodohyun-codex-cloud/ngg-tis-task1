#!/usr/bin/env python3
"""Merge two current volume reports with a historical GUI; show saved gates.

JSON-only display. No native arrays, new normalization, field calculation,
scientific gate recomputation or physical-map generation occurs here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import html
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import time

import task1_volume_snapshot_merge_view as merge

ROOT=Path(__file__).resolve().parents[1]


def validate_screen(path, final_audit):
    path=Path(path).resolve();before=merge.view.sha(path);screen=merge.view.read(path);merge.view.finite_tree(screen)
    merge.view.require(screen['schema']=='task1-candidate-screen-v1' and screen['status']=='screen_complete_not_adopted' and
        screen['normalization']=='skin_contact_only' and screen['candidate_adopted'] is False and
        screen['input_volume_report']['path']==final_audit['path'] and
        screen['input_volume_report']['SHA256']==final_audit['SHA256'],'Saved screen must bind the final current volume report')
    by_id={case['case_id']:case for case in final_audit['report']['cases']}
    expected=set(by_id)-{screen['baseline_case_id']}
    merge.view.require({row['case_id']for row in screen['cases']}==expected,'Screen/volume candidate inventory differs')
    compact=[]
    for row in screen['cases']:
        checks=row['checks'];failed=[c['name']for c in checks if c['passed'] is False]
        merge.view.require(len(checks)==8 and all(type(c['passed']) is bool for c in checks) and
            type(row['all_screen_checks_passed']) is bool and row['all_screen_checks_passed']==(not failed) and
            set(failed)==set(row['failed_checks']),'Saved eight-gate conclusions are inconsistent')
        case=by_id[row['case_id']]
        merge.view.require(merge.view.digest(row['all_five_normalizations'])==merge.view.digest(case['normalizations']),
                           'Screen normalization values differ from the bound volume report')
        compact.append({key:row[key]for key in ('case_id','checks','all_screen_checks_passed','failed_checks','decision')})
    prereg=screen['preregistration'];merge.view.require(merge.view.sha(prereg['path'])==prereg['SHA256'],'Screen plan SHA changed')
    merge.view.require(merge.view.sha(path)==before,'Screen JSON changed during read')
    return dict(path=str(path),SHA256=before,normalization=screen['normalization'],baseline_case_id=screen['baseline_case_id'],
        cases=compact,preregistration=prereg,scope='Stored gate conclusions displayed, not recomputed; no adoption/mesh/experiment promotion')


def build_model(snapshot_html,snapshot_receipt,audit_paths,screen_path):
    model,snapshot=merge.load_snapshot(snapshot_html,snapshot_receipt)
    original_count=len(model['cases']);audits=[];additions=[]
    for path in audit_paths:
        audit=merge.validate_new_audit(path);before=len(model['cases']);model=merge.merge_model(model,audit)
        additions.append(len(model['cases'])-before);audits.append(audit)
    merge.view.require(audits,'At least one new report required')
    screen=validate_screen(screen_path,audits[-1])
    model['snapshot_merge']=dict(historical_cases=original_count,new_cases=len(model['cases'])-original_count,
        staged_additions=additions,current_report_count=len(audits),historical_validation_scope='immutable historical snapshot',
        new_validation_scope='Current small-source SHA verification; native arrays not opened')
    model['historical_snapshot']=snapshot;model['saved_candidate_screen']=screen
    return model,snapshot,audits,screen


def screen_section(model,screen,output):
    esc=lambda x:html.escape(str(x));by_id={c['case_id']:c for c in model['cases']}
    summaries=[];details=[]
    for row in screen['cases']:
        mode=by_id[row['case_id']]['normalizations']['skin_contact_only'];r=mode['regions'];b=mode['normalized_burdens']
        summaries.append('<tr>'+''.join('<td>'+esc(value)+'</td>'for value in (
            row['case_id'],'PASS'if row['all_screen_checks_passed']else'FAIL / not nominated',
            r[merge.view.PRIMARY]['maxTIS']['mean'],r[merge.view.PRIMARY]['maxTIS']['p10'],
            r['surface_0_5']['maxTIS']['p95'],r['primary_complement']['maxTIS']['p95'],
            mode['source_Vpp_per_output'],b['bulk_skin_J_vector_RMS_p95_A_m2'],b['source_power_W'],
            ', '.join(mode['active_skin_contact_caps']),', '.join(row['failed_checks'])))+'</tr>')
        checks=''.join('<tr>'+''.join('<td>'+esc(check[key])+'</td>'for key in
            ('name','unit','required_direction','baseline','candidate','relative_change_percent','passed'))+'</tr>'for check in row['checks'])
        details.append('<details><summary>'+esc(row['case_id'])+' · stored8-gate evidence</summary><table><tr>'+\
            ''.join('<th>'+x+'</th>'for x in ('Gate','unit','direction','baseline','candidate','change %','pass'))+'</tr>'+checks+'</table></details>')
    headers=('Candidate','saved screen','ROI mean V/m','ROI P10 V/m','surfaceP95 V/m','non-targetP95 V/m',
             'Vpp/output','skin-volumeJ95 A/m²','source W','active skin/contact caps','failed checks')
    return '<section><h2>Newest allocation family · saved selection gates</h2><p>All rows below use stored skin_contact_only values. '+\
        'Target gain and non-target burden are separate requirements; a lower surface value alone is insufficient. '+\
        'PASS here would mean only the fixed numerical screen, not adoption or convergence. '+\
        '<a href="'+merge.view.relative(screen['path'],output)+'">Original saved screen</a>.</p><table><tr>'+\
        ''.join('<th>'+h+'</th>'for h in headers)+'</tr>'+''.join(summaries)+'</table>'+''.join(details)+\
        '<p>This screen adds scalar tables and shared-ROI controls. It generates no new physical XY/XZ maps; the linked historical maps retain their original conditions, units and color ranges.</p></section>'


def document(model,snapshot,screen,output,common_maps):
    model=dict(model,common_maps_path=str(Path(common_maps).resolve()))
    text=merge.document(model,snapshot,output)
    return text.replace('<div><label>Same-grid cohort',screen_section(model,screen,output)+'<div><label>Same-grid cohort',1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot-html','snapshot-receipt','screen','common-maps','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--audit',type=Path,action='append',required=True);a=p.parse_args();output=a.output.resolve();receipt_path=output.with_suffix('.receipt.json')
    merge.view.require(0<len(a.audit)<=2 and output.parent.is_dir() and not output.exists() and not receipt_path.exists() and
        not output.with_suffix('.failure.json').exists(),'Fresh output and at most2 current report paths required')
    with (ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=merge.view.read(ledger_path);limit=merge.effective_limit(ledger)
        seconds=min(120.,limit-ledger['spent_seconds']);merge.view.require(seconds>0,'Validated budget exhausted')
        merge.view.require(shutil.disk_usage(output.parent).free>=2*merge.view.GIB+50*1024**2,'Keep2GiB reserve plus50MiB allowance')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});started=time.monotonic();status='failed'
        def timeout(signum,frame):raise TimeoutError('Finite snapshot/gate JSON-render deadline exceeded')
        signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,seconds)
        try:
            model,snapshot,audits,screen=build_model(a.snapshot_html,a.snapshot_receipt,a.audit,a.screen)
            text=document(model,snapshot,screen,output,a.common_maps)
            merge.view.require(len(text.encode())<=49*1024**2 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=3*merge.view.GIB,
                'Unchanged output/RSS cap exceeded')
            merge.load_snapshot(a.snapshot_html,a.snapshot_receipt)
            for audit in audits:
                merge.view.require(merge.view.sha(audit['path'])==audit['SHA256'] and all(merge.view.sha(path)==sha
                    for path,sha in audit['verified_small_inputs'].items()),'Current report/source changed during display assembly')
            merge.view.require(merge.view.sha(screen['path'])==screen['SHA256'],'Saved screen changed')
            with output.open('x')as stream:stream.write(text)
            result=dict(schema='task1-volume-two-report-merge-receipt-v1',status='rendered_precomputed_JSON_only',
                created_utc=datetime.now(timezone.utc).isoformat(),output=dict(path=str(output),SHA256=merge.view.sha(output),bytes=output.stat().st_size),
                implementation=dict(path=str(Path(__file__).resolve()),SHA256=merge.view.sha(__file__),merge_helper_SHA256=merge.view.sha(merge.__file__)),
                historical_snapshot=snapshot,current_audits=[{k:v for k,v in au.items()if k!='report'}for au in audits],
                saved_screen=screen,snapshot_merge=model['snapshot_merge'],case_count=len(model['cases']),cohort_count=len(model['cohorts']),
                new_PDE=0,new_volume_analysis=0,new_physical_maps=0,native_arrays_opened=False,
                resources=dict(wall_seconds=time.monotonic()-started,max_seconds=seconds,global_limit_seconds=limit,CPU_count=1))
            payload=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
            merge.view.require(output.stat().st_size+len(payload.encode())<=50*1024**2 and
                shutil.disk_usage(output.parent).free>=2*merge.view.GIB+len(payload.encode()),'Unchanged storage reserve/cap violated')
            with receipt_path.open('x')as stream:stream.write(payload)
            status=result['status'];print(json.dumps(dict(status=status,case_count=len(model['cases']),output=str(output))))
        except BaseException as error:
            with output.with_suffix('.failure.json').open('x')as stream:json.dump(dict(status='failed',error=str(error),partial_evidence_preserved=True),stream)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-started;ledger['spent_seconds']+=elapsed
            ledger['runs'].append(dict(run_id=output.stem,stage='two_report_snapshot_gate_JSON_view',status=status,seconds=elapsed))
            tmp=ledger_path.with_name(ledger_path.name+'.partial');tmp.write_text(json.dumps(ledger,indent=2)+'\n');tmp.replace(ledger_path)


if __name__=='__main__':main()
