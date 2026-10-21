#!/usr/bin/env python3
"""Append current JSON evidence to an immutable historical volume-GUI snapshot.

Historical source verification remains historical. Old live implementation
paths are not revalidated or silently accepted as their old source versions.
No native-array read, rescaling, numerical postprocessing or PDE is performed.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import fcntl
from html.parser import HTMLParser
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
from task1_resource_policy import effective_limit

ROOT = Path(__file__).resolve().parents[1]
VIEWER_FIELDS = {'viewer_id', 'viewer_holds', 'baseline_present', 'links'}


class SnapshotParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.collect = False; self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('id') == 'report-data':
            view.require(not self.parts, 'Duplicate embedded model')
            self.collect = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.collect = False

    def handle_data(self, data):
        if self.collect:
            self.parts.append(data)


def raw_case(case):
    return {key: copy.deepcopy(value) for key, value in case.items() if key not in VIEWER_FIELDS}


def validate_new_audit(path):
    """Current source verification, with explicit empty native-completion markers."""
    path=Path(path).resolve();before=view.sha(path);report=view.read(path);view.finite_tree(report)
    view.require(report['schema']=='task1-volume-selectivity-v1' and report['status']=='calculated_unadopted' and
        report['new_PDE_solves']==0 and report['inputs_unchanged'] is True and report['selected_for_adoption']==[] and
        0<len(report['cases'])<=12,'Completed unadopted cached audit required')
    scope=report['scope'];view.require(set(scope['metrics'])==set(view.METRICS) and
        'volume-weighted' in scope['quantiles'] and 'side=left' in scope['quantiles'] and
        'unchanged' in scope['primary_ROI'],'Original weighted metric definitions required')
    pins=report['inputs_sha256'];prereg=report['preregistration']
    view.require(prereg['verified_before_and_after'] is True and
        pins.get(str(Path(prereg['path']).resolve()))==prereg['SHA256'],'Bound preregistration required')
    small,native={},{}
    for name,expected in pins.items():
        source=Path(name).resolve();view.require(len(expected)==64 and all(c in '0123456789abcdef'for c in expected),'SHA256 required')
        if source.suffix in ('.npz','.bin','.gz') or source.name=='grid.csv':
            native[str(source)]=expected;continue
        marker=source.name=='BASIS_COMPLETE' and source.parent.parent.name=='bases'
        view.require(source.suffix in ('.json','.properties','.csv','.py','.java') or marker,'Unsupported small input type')
        view.require(source.is_file() and view.sha(source)==expected,'Current small source SHA mismatch: '+str(source))
        if marker:view.require(source.stat().st_size==0,'Native completion marker must remain empty')
        small[str(source)]=expected
    for case in report['cases']:
        view.check_case(case);probe=case['raw_probe_artifact_reference']
        view.require(str(Path(case['summary_path']).resolve())in small and
            pins.get(str(Path(probe['path']).resolve()))==probe['SHA256'],'Case summary/probe binding required')
    view.require(view.sha(path)==before,'New audit changed during verification')
    return dict(path=str(path),SHA256=before,report=report,verified_small_inputs=small,
        native_inputs_declared_not_opened=native,source_verification_performed=True)


def load_snapshot(html_path, receipt_path):
    html_path, receipt_path = Path(html_path).resolve(), Path(receipt_path).resolve()
    receipt_sha = view.sha(receipt_path); receipt = view.read(receipt_path)
    view.require(receipt['schema'] == 'task1-volume-audit-view-receipt-v1' and
        receipt['status'] == 'rendered_precomputed_JSON_only' and
        receipt['output']['SHA256'] == view.sha(html_path) and
        receipt['output']['bytes'] == html_path.stat().st_size,
        'Exact successfully completed prior HTML/receipt required')
    parser = SnapshotParser(); parser.feed(html_path.read_text())
    model = json.loads(''.join(parser.parts)); view.finite_tree(model)
    view.require(model['schema'] == 'task1-volume-audit-view-model-v1' and
        len(model['cases']) == receipt['case_count'], 'Snapshot case count/schema differs')
    original_cases = {}
    for proof in receipt['audit_inputs']:
        view.require(view.sha(proof['path']) == proof['SHA256'], 'Historical audit JSON artifact changed')
        report = view.read(proof['path'])
        for case in report['cases']:
            key = str(Path(case['summary_path']).resolve())
            if key in original_cases:
                view.require(view.digest(original_cases[key]) == view.digest(case), 'Conflicting historical report cases')
            original_cases[key] = case
    for case in model['cases']:
        key = str(Path(case['summary_path']).resolve())
        view.require(key in original_cases and view.digest(raw_case(case)) == view.digest(original_cases[key]),
                     'Embedded historical scalar data differs from its original report')
    view.require(len(original_cases) == len(model['cases']), 'Historical report/model inventory differs')
    view.require(view.sha(receipt_path) == receipt_sha and receipt['output']['SHA256'] == view.sha(html_path),
                 'Historical snapshot changed during metadata verification')
    proof = dict(html_path=str(html_path), HTML_SHA256=receipt['output']['SHA256'],
        receipt_path=str(receipt_path), receipt_SHA256=receipt_sha, case_count=len(model['cases']),
        historical_viewer_source_commit=receipt['source_commit'],
        historical_implementation_SHA256=receipt['implementation_SHA256'],
        historical_input_artifact_proofs=[dict(path=x['path'], SHA256=x['SHA256']) for x in receipt['audit_inputs']],
        scope='Old report/HTML/receipt bytes checked now; small source-input verification belongs to the original successful snapshot, not current live helper files')
    return model, proof


def merge_model(old_model, validated_new):
    cases = {str(Path(c['summary_path']).resolve()): raw_case(c) for c in old_model['cases']}
    previous_count = len(cases)
    for case in validated_new['report']['cases']:
        key = str(Path(case['summary_path']).resolve())
        if key in cases:
            view.require(view.digest(cases[key]) == view.digest(case), 'Shared historical/new case differs; do not average or overwrite')
        else:
            cases[key] = copy.deepcopy(case)
    model = copy.deepcopy(old_model); model['cases'] = list(cases.values()); model['cohorts'] = []; model['holds'] = []
    grouped = {}
    for case in model['cases']:
        case['viewer_id'] = case['run_id']+'/'+case['case_id']
        grouped.setdefault(case['comparison_signature'], []).append(case)
    for signature, members in grouped.items():
        by_path = {str(Path(c['summary_path']).resolve()): c for c in members}
        references = {str(Path(c['baseline_summary']).resolve()) for c in members}
        view.require(len(references) == 1, 'Ambiguous same-grid baseline')
        baseline = by_path.get(next(iter(references)))
        view.require(baseline is not None and baseline['circuit']['n_pads'] == 4 and
            baseline['circuit']['n_outputs'] == 2, 'Original same-grid four-pad baseline must remain present')
        for case in members:
            case['baseline_present'] = True; case['viewer_holds'] = []
        model['cohorts'].append(dict(signature=signature, baseline_id=baseline['viewer_id'],
            case_ids=[c['viewer_id'] for c in members], mesh=members[0]['mesh']))
    model['audits'].extend(view.build_model([validated_new])['audits'])
    model['snapshot_merge'] = dict(historical_cases=previous_count, new_cases=len(cases)-previous_count,
        historical_validation_scope='original successful snapshot; not current live-helper verification',
        new_validation_scope='new report and currently matching small source input SHA256; native arrays not opened')
    return model


def document(model, snapshot, output):
    rendered = view.render_html(model, output, model['common_maps_path'])
    old = 'Only reports and small input hashes were checked by this viewer. Native NPZ/grid/E/phi bytes were not opened; their hashes retain the original audit provenance. Mesh convergence, experiment and adoption remain unvalidated.'
    replacement = 'Historical cases retain the source-version verification of their original successful GUI snapshot. Their original report/HTML/receipt SHA256 artifacts were checked again; changed live helper files are not treated as old source versions. Only the newly appended report received current small-input SHA verification. Native arrays were not opened. Convergence, experiment and adoption remain unvalidated.'
    view.require(old in rendered, 'Underlying renderer verification wording changed; review required')
    rendered = rendered.replace(old, replacement, 1)
    commit = snapshot['historical_viewer_source_commit']
    view.require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'Historical Git commit required')
    note = '<section><b>Versioned snapshot merge:</b> '+str(model['snapshot_merge']['historical_cases'])+' historical cases + '+str(model['snapshot_merge']['new_cases'])+' new cases. '+\
        '<a href="'+view.relative(snapshot['html_path'], output)+'">Original GUI</a> · '+\
        '<a href="'+view.relative(snapshot['receipt_path'], output)+'">Original receipt</a> · '+\
        '<a href="https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/commit/'+commit+'">Historical viewer source '+html.escape(commit)+'</a>. '+\
        'Source commits,config hashes,ROI definitions and units remain attached to each row. All candidates remain unadopted.</section>'
    return rendered.replace('<div><label>Same-grid cohort', note+'<div><label>Same-grid cohort', 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot-html', type=Path, required=True)
    parser.add_argument('--snapshot-receipt', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--common-maps', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = args.output.resolve(); receipt_path = output.with_suffix('.receipt.json')
    view.require(output.suffix == '.html' and output.parent.is_dir() and not output.exists() and
        not receipt_path.exists() and not output.with_suffix('.failure.json').exists(), 'Fresh output/receipt paths required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = ROOT/'runtime/task1-budget.json'; ledger = view.read(ledger_path); limit = effective_limit(ledger)
        seconds = min(120., limit-ledger['spent_seconds']); view.require(seconds > 0, 'Validated budget exhausted')
        view.require(shutil.disk_usage(output.parent).free >= 2*view.GIB+50*1024**2, 'Keep2GiB reserve plus50MiB allowance')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))}); started = time.monotonic(); status = 'failed'
        def timeout(signum, frame): raise TimeoutError('Finite JSON-only snapshot-merge deadline exceeded')
        signal.signal(signal.SIGALRM, timeout); signal.setitimer(signal.ITIMER_REAL, seconds)
        try:
            old_model, snapshot = load_snapshot(args.snapshot_html, args.snapshot_receipt)
            new = validate_new_audit(args.audit)
            model = merge_model(old_model, new); model['historical_snapshot'] = snapshot
            model['common_maps_path'] = str(args.common_maps.resolve())
            text = document(model, snapshot, output)
            view.require(len(text.encode()) <= 49*1024**2 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 <= 3*view.GIB,
                         'JSON view exceeds unchanged storage/RSS cap')
            load_snapshot(args.snapshot_html, args.snapshot_receipt)
            view.require(view.sha(new['path']) == new['SHA256'] and all(view.sha(p) == sha
                for p, sha in new['verified_small_inputs'].items()), 'New report/source JSON changed')
            with output.open('x') as stream: stream.write(text)
            receipt = dict(schema='task1-volume-snapshot-merge-receipt-v1', status='rendered_precomputed_JSON_only',
                created_utc=datetime.now(timezone.utc).isoformat(), output=dict(path=str(output), SHA256=view.sha(output), bytes=output.stat().st_size),
                implementation=dict(path=str(Path(__file__).resolve()), SHA256=view.sha(__file__),
                    renderer_path=str(Path(view.__file__).resolve()), renderer_SHA256=view.sha(view.__file__),
                    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()),
                historical_snapshot=snapshot, new_audit={k:v for k,v in new.items() if k!='report'},
                case_count=len(model['cases']), cohort_count=len(model['cohorts']), snapshot_merge=model['snapshot_merge'],
                new_PDE=0,new_volume_analysis=0,native_arrays_opened=False,
                resources=dict(wall_seconds=time.monotonic()-started,max_seconds=seconds,global_limit_seconds=limit,CPU_count=1))
            payload = json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
            view.require(output.stat().st_size+len(payload.encode()) <= 50*1024**2 and
                shutil.disk_usage(output.parent).free >= 2*view.GIB+len(payload.encode()), 'Output violates unchanged storage reserve/cap')
            with receipt_path.open('x') as stream: stream.write(payload)
            status = receipt['status']; print(json.dumps(dict(status=status,cases=len(model['cases']),output=str(output))))
        except BaseException as error:
            with output.with_suffix('.failure.json').open('x') as stream:
                json.dump(dict(status='failed',error_type=type(error).__name__,error=str(error),partial_evidence_preserved=True),stream,indent=2)
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0); elapsed=time.monotonic()-started
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem,stage='JSON_only_volume_snapshot_merge',status=status,seconds=elapsed))
            temporary=ledger_path.with_name(ledger_path.name+'.partial');temporary.write_text(json.dumps(ledger,indent=2)+'\n');temporary.replace(ledger_path)


if __name__ == '__main__': main()
