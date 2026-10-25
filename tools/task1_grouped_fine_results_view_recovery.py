#!/usr/bin/env python3
"""Bounded JSON-only GUI for five completed same-grid grouped-pad rows.

No native arrays, field reconstruction, rescaling, gate calculation or PDE.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
import html
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

import task1_volume_audit_view as view
import task1_resource_policy as policy

ROOT=Path(__file__).resolve().parents[1]
BASELINE='baseline-square15-xy80'
BASELINE_RUN='cloud-mesh-c1-20261019T190000Z'
GROUPED_RUN='cloud-grouped-fine-20261021T160000Z'
GROUPED=tuple(f'grouped-strip225-gap1-p{count:02d}-xy80'for count in (4,8,12,16))
GATES=[dict(name='primary_maxTIS_'+stat,unit='V/m',required_direction='greater')for stat in ('mean','p10')]
for _region in ('surface_0_5','primary_complement'):
    GATES.append(dict(name=_region+'_maxTIS_p95',unit='V/m',required_direction='less'))
    GATES.extend(dict(name=_region+'_high_volume_at_'+view.PRIMARY+'_'+stat,unit='m3',required_direction='less')for stat in ('mean','p10'))


def checked_json(path):
    path=Path(path).resolve();view.require(path.suffix=='.json'and path.is_file()and path.stat().st_size<=25*1024**2,'Existing JSON <=25MiB required')
    before=view.sha(path);value=view.read(path);view.finite_tree(value)
    view.require(view.sha(path)==before,'JSON changed while reading')
    return value,dict(path=str(path),SHA256=before)


def validate_audit(path):
    """Source-bound audit, with exactly two approved decision-document paths."""
    report,pin=checked_json(path)
    view.require(report['schema']=='task1-volume-selectivity-v1'and report['status']=='calculated_unadopted'and
        report['new_PDE_solves']==0 and report['inputs_unchanged']is True and report['selected_for_adoption']==[]and
        0<len(report['cases'])<=12,'Completed unadopted cached audit required')
    scope=report['scope']
    view.require(set(scope['metrics'])==set(view.METRICS)and 'volume-weighted'in scope['quantiles']and
        'side=left'in scope['quantiles']and 'unchanged'in scope['primary_ROI'],'Original weighted definitions required')
    pins=report['inputs_sha256'];prereg=report['preregistration']
    view.require(isinstance(pins,dict)and pins and prereg['verified_before_and_after']is True and
        pins.get(str(Path(prereg['path']).resolve()))==prereg['SHA256'],'Bound before/after preregistration required')
    allowed_documents={ROOT/'docs/LOWER_CARRIER_RESULTS_20261021.md',ROOT/'docs/MID_HIGH_CARRIER_RESULTS_20261021.md'}
    small,native={},{}
    for name,expected in pins.items():
        source=Path(name).resolve()
        view.require(isinstance(expected,str)and len(expected)==64 and all(c in '0123456789abcdef'for c in expected),'SHA256 required')
        if source.suffix in ('.npz','.bin','.gz')or source.name=='grid.csv':
            native[str(source)]=expected;continue
        marker=source.name=='BASIS_COMPLETE'and source.parent.parent.name=='bases'
        approved_document=source in allowed_documents and source.suffix=='.md'
        view.require(source.suffix in ('.json','.properties','.csv','.py','.java')or marker or approved_document,
            'Unsupported small input type; only the two exact approved decision Markdown paths are added')
        view.require(source.is_file()and view.sha(source)==expected,'Current small source SHA mismatch: '+str(source))
        if marker:view.require(source.stat().st_size==0 and expected=='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
            'Native completion marker must be canonical empty hashed metadata')
        small[str(source)]=expected
    for case in report['cases']:
        view.check_case(case);probe=case['raw_probe_artifact_reference']
        view.require(str(Path(case['summary_path']).resolve())in small and
            pins.get(str(Path(probe['path']).resolve()))==probe['SHA256'],'Case summary/probe binding required')
    view.require(view.sha(pin['path'])==pin['SHA256'],'Audit changed during source verification')
    return dict(**pin,report=report,verified_small_inputs=small,native_inputs_declared_not_opened=native,source_verification_performed=True)


def load_model(audit_path,screen_path,previous_gui_path):
    audit=validate_audit(audit_path)
    # The reused validator admits only an empty, hashed bases/<case> marker.
    for name,expected in audit['verified_small_inputs'].items():
        path=Path(name)
        if path.name=='BASIS_COMPLETE':
            view.require(path.parent.parent.name=='bases'and path.stat().st_size==0 and
                expected=='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
                'Only canonical empty BASIS_COMPLETE metadata is permitted')
    cases=audit['report']['cases'];by_id={row['case_id']:row for row in cases}
    view.require(len(cases)==len(by_id)==5 and set(by_id)=={BASELINE,*GROUPED},'Exactly original square plus four registered grouped-strip rows required')
    baseline=by_id[BASELINE]
    view.require(baseline['run_id']==BASELINE_RUN,'Original cached fine square baseline required')
    for identifier,row in by_id.items():
        mesh=row['mesh'];expected_pads=4 if identifier==BASELINE else (4,8,12,16)[GROUPED.index(identifier)]
        view.require(mesh['h_xy_mm']==.625 and mesh['sc_cells']==2 and mesh['bulk_layer_counts']==[14,14,40]and
            mesh['cells']==351680 and row['circuit']['n_pads']==expected_pads and
            row['circuit']['return_topology']=='all_return_pads_ideal_common_GND'and
            row['circuit']['carrier_assignment_Hz']==[3000,3030]and
            row['baseline_summary']==baseline['summary_path']and
            (identifier==BASELINE or row['run_id']==GROUPED_RUN),'Fixed fine grid, original baseline and physical-pad wiring required')
    model=view.build_model([audit])
    view.require(len(model['cohorts'])==1 and model['cohorts'][0]['baseline_id']==baseline['run_id']+'/'+BASELINE and not model['holds'],
        'One same-grid cohort with always-visible original four-square baseline required')
    screen,screen_pin=checked_json(screen_path)
    view.require(screen['schema']=='task1-candidate-screen-v1'and screen['status']=='screen_complete_not_adopted'and
        screen['input_volume_report']==dict(path=audit['path'],SHA256=audit['SHA256'])and
        screen['normalization']=='skin_contact_only'and screen['baseline_case_id']==BASELINE and
        screen['fixed_baseline_cutoffs_V_m']==baseline['fixed_same_grid_baseline_cutoffs_V_m']and
        screen['candidate_adopted']is False and screen['full_convergence_validated']is False and
        screen['experimentally_validated']is False,'Stored unadopted screen must bind the exact volume report and original cutoffs')
    screen_rows=screen['cases']
    view.require(len(screen_rows)==4 and {row['case_id']for row in screen_rows}==set(GROUPED),'Four exact grouped screen rows required')
    display=[]
    for row in screen_rows:
        checks=row['checks'];case=by_id[row['case_id']]
        view.require([{key:check[key]for key in ('name','unit','required_direction')}for check in checks]==GATES and
            all(type(check['passed'])is bool for check in checks)and type(row['all_screen_checks_passed'])is bool and
            row['all_screen_checks_passed']==all(check['passed']for check in checks)and
            row['failed_checks']==[check['name']for check in checks if not check['passed']]and
            row['run_id']==case['run_id']and row['candidate_adopted']is False and
            row['all_five_normalizations']==case['normalizations']and row['circuit']==case['circuit']and
            row['mesh']==case['mesh']and row['raw_probe_artifact_reference']==case['raw_probe_artifact_reference'],
            'Screen flags, eight frozen definitions and stored case values must agree; this viewer calculates no gates')
        display.append({key:copy.deepcopy(row[key])for key in ('case_id','run_id','checks','all_screen_checks_passed','failed_checks','decision')})
    previous=Path(previous_gui_path).resolve();previous_receipt,receipt_pin=checked_json(previous.with_suffix('.receipt.json'))
    view.require(previous_receipt['schema']=='task1-volume-two-report-merge-receipt-v1'and
        previous_receipt['status']=='rendered_precomputed_JSON_only'and previous_receipt['case_count']==44 and
        previous_receipt['output']['SHA256']==view.sha(previous),'Exact successful historical44-case GUI artifact required')
    model['fine_grouped_screen']=dict(path=screen_pin['path'],SHA256=screen_pin['SHA256'],normalization='skin_contact_only',cases=display)
    model['historical_GUI']=dict(path=str(previous),SHA256=previous_receipt['output']['SHA256'],receipt=receipt_pin,
        case_count=44,scope='Historical artifact SHA only; old live source inputs are not revalidated here; coarse grouped-pad family is not fine validation')
    return model


def render_html(model,output_path,common_maps_path,previous_gui_path):
    text=view.render_html(model,output_path,common_maps_path);esc=lambda value:html.escape(str(value))
    sections=[]
    for row in model['fine_grouped_screen']['cases']:
        body=''.join('<tr>'+''.join('<td>'+esc(check.get(key,'unavailable'))+'</td>'for key in
            ('name','unit','required_direction','baseline','candidate','relative_change_percent','passed'))+'</tr>'for check in row['checks'])
        sections.append('<details><summary>'+esc(row['case_id'])+' · '+('all8 PASS; unadopted'if row['all_screen_checks_passed']else'FAIL; not nominated')+'</summary>'+\
            '<table><tr>'+''.join('<th>'+label+'</th>'for label in ('Gate','unit','direction','baseline','candidate','change %','pass'))+'</tr>'+body+'</table></details>')
    note='<section><h2>Fine grouped physical-pad comparison</h2><p>Five rows: cached original4-square baseline, NEW4-strip geometry control,8/12/16-strip conditions. '+\
        'Every condition has exactly2 independent outputs, commonGND and50Ω inactive-frequency termination. Fine XY0.625mm /SC2 /bulk14,14,40 is shared. '+\
        'Total physical area stays900mm², with225mm² per electrical parent group. Original4-square versus4-strip also changes outline and placement; subdivision comparisons use the strip family.</p>'+\
        '<p><a href="'+view.relative(previous_gui_path,output_path)+'">Historical44-case GUI, including the coarse grouped-pad family</a>. '+\
        'Its artifact SHA and receipt are checked; its historical source-input validation is not claimed current. No old physical map is relabeled as a new fine-pad map. '+\
        'The controls below select stored values only, with unchanged units and ROI. Existing map links retain their original scales.</p>'+\
        '<h2>Stored eight-gate screen</h2><p><a href="'+view.relative(model['fine_grouped_screen']['path'],output_path)+'">Source screen JSON</a> SHA256 '+esc(model['fine_grouped_screen']['SHA256'])+\
        '. Fixed primary ROI and skin_contact_only; these verdicts remain fixed when display selectors change. A pass permits separately registered validation, not adoption. '+\
        'Convergence, experimental loading and physiology remain unvalidated.</p>'+''.join(sections)+'</section>'
    return text.replace('<title>Task1 cached volume audit</title>','<title>Task1 fine grouped-pad comparison</title>',1).replace('<div><label>Same-grid cohort',note+'<div><label>Same-grid cohort',1)


def source_identity():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,timeout=5).strip()
    paths=(Path(__file__).resolve(),ROOT/'tests/test_task1_grouped_fine_results_view_recovery.py',Path(view.__file__).resolve(),Path(policy.__file__).resolve())
    pins={str(path):view.sha(path)for path in paths}
    for path in paths:
        view.require(subprocess.check_output(['git','show',commit+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT,timeout=5)==path.read_bytes(),
            'Commit reviewed display source/tests before rendering')
    return dict(source_commit=commit,implementation_sha256=pins)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('audit','screen','previous','output'):parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--common-maps',type=Path,default=ROOT/'docs/CLOUD_RESULTS.html')
    args=parser.parse_args();output=args.output.resolve();receipt_path=output.with_suffix('.receipt.json');failure_path=output.with_suffix('.failure.json')
    view.require(output.suffix=='.html'and output.parent.is_dir()and not any(path.exists()for path in (output,receipt_path,failure_path)),
        'Fresh HTML/receipt/failure paths in an existing directory required')
    identity=source_identity()
    with (ROOT/'.task1-execution.lock').open('a+')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.lockf(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path=ROOT/'runtime/task1-budget.json';ledger=view.read(ledger_path);limit=policy.effective_limit(ledger)
        seconds=min(120.,limit-ledger['spent_seconds']);view.require(seconds>0,'Validated cumulative budget exhausted')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        soft,hard=resource.getrlimit(resource.RLIMIT_AS);cap=min(3*view.GIB,hard)if hard!=resource.RLIM_INFINITY else 3*view.GIB
        resource.setrlimit(resource.RLIMIT_AS,(cap,hard))
        view.require(shutil.disk_usage(output.parent).free>=2*view.GIB+50*1024**2,'Keep2GiB reserve plus50MiB display allowance')
        started=time.monotonic();status='failed'
        def timeout(signum,frame):raise TimeoutError('Finite120s/remaining JSON-view deadline exceeded')
        signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,seconds)
        try:
            model=load_model(args.audit,args.screen,args.previous);text=render_html(model,output,args.common_maps,args.previous)
            view.require(len(text.encode())<=49*1024**2 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=3*view.GIB,'Unchanged display storage/RSS cap exceeded')
            view.require(source_identity()==identity,'Display source/HEAD changed')
            audit=model['audits'][0]
            view.require(view.sha(audit['path'])==audit['SHA256']and all(view.sha(path)==expected for path,expected in audit['verified_small_inputs'].items())and
                view.sha(model['fine_grouped_screen']['path'])==model['fine_grouped_screen']['SHA256']and
                view.sha(model['historical_GUI']['path'])==model['historical_GUI']['SHA256']and
                view.sha(model['historical_GUI']['receipt']['path'])==model['historical_GUI']['receipt']['SHA256'],'Display input changed during assembly')
            with output.open('x')as stream:stream.write(text)
            receipt=dict(schema='task1-grouped-fine-results-view-recovery-receipt-v1',status='rendered_precomputed_JSON_only',
                created_utc=datetime.now(timezone.utc).isoformat(),**identity,output=dict(path=str(output),SHA256=view.sha(output),bytes=output.stat().st_size),
                audit_inputs=model['audits'],screen_input=model['fine_grouped_screen'],historical_GUI=model['historical_GUI'],
                case_count=5,cohort_count=1,new_PDE=0,new_volume_analysis=0,native_arrays_opened=False,
                resources=dict(wall_seconds=time.monotonic()-started,max_seconds=seconds,global_limit_seconds=limit,CPU_count=1,
                    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,output_limit_bytes=50*1024**2,minimum_reserve_bytes=2*view.GIB))
            payload=json.dumps(receipt,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
            view.require(output.stat().st_size+len(payload.encode())<=50*1024**2 and shutil.disk_usage(output.parent).free>=2*view.GIB+len(payload.encode()),'Receipt would exceed unchanged storage cap/reserve')
            with receipt_path.open('x')as stream:stream.write(payload)
            status=receipt['status'];print(json.dumps(dict(status=status,cases=5,output=str(output))))
        except BaseException as error:
            with failure_path.open('x')as stream:json.dump(dict(status='failed',error_type=type(error).__name__,error=str(error),partial_evidence_preserved=True),stream,indent=2)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);elapsed=time.monotonic()-started
            ledger['spent_seconds']+=elapsed;ledger['runs'].append(dict(run_id=output.stem,stage='JSON_only_grouped_fine_view',status=status,seconds=elapsed))
            temporary=ledger_path.with_name(ledger_path.name+'.partial');temporary.write_text(json.dumps(ledger,indent=2)+'\n');temporary.replace(ledger_path)


if __name__=='__main__':main()
