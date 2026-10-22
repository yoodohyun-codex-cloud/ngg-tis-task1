#!/usr/bin/env python3
"""Finite small-contact-operator audit; rank deficiency is a valid result.

Reads density/source/contact arrays at3000/3030Hz only. It never opens native
E, phi, grid or scalar archives and never constructs drive weights or a candidate.
"""
from __future__ import annotations
import argparse
import csv
import fcntl
import gzip
import hashlib
import io
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import threading
import time
for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'
import numpy as np
import task1_cloud_batch as core
import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
RESOLUTION = 2e-6
FREQUENCIES = (3000, 3030)
SOURCE_CASES = (
    dict(geometry='opposite-square', run_id='cloud-mesh-c1-20261019T190000Z', case_id='baseline-square15-xy80'),
    dict(geometry='opposite-asymmetric', run_id='cloud-asymmetric-20261021T051000Z', case_id='asym-cross281p25-return168p75-xy80'),
    dict(geometry='one-return-rot90', run_id='cloud-one-return-rotation-20261021T174000Z', case_id='asym-return2-rot90-xy80'))
SCHEMA = 'task1-return-rotation-operator-preregistration-v1'
MAX_SMALL_BYTES = 16*1024**2


def require(ok, message):
    if not ok: raise ValueError(message)


def canonical(value):
    p = Path(value)
    require(p.is_absolute() and p == p.resolve() and p.is_relative_to(ROOT) and p.is_file() and
            not p.is_symlink() and p.stat().st_size <= MAX_SMALL_BYTES, 'Canonical bounded small source required: '+str(p))
    return p


def pin(value, refs, expected=None):
    p = canonical(value); digest = core.sha(p)
    require(expected is None or digest == expected, 'Pinned small source changed: '+str(p))
    refs[str(p)] = digest
    return p


def read_json(value, refs, expected=None):
    p = pin(value, refs, expected); obj = core.read(p)
    require(core.sha(p) == refs[str(p)], 'JSON changed while reading')
    return obj


def properties(p):
    obj = {}
    for line in Path(p).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '!')): continue
        require('=' in line, 'Malformed property')
        key, value = (v.strip() for v in line.split('=', 1)); require(key not in obj, 'Duplicate property')
        obj[key] = value
    return obj


def response_diagnostics(density, contacts, source, expected_areas, frequency):
    """Pure coherent area integration and observed SVD; never a weight design."""
    require(frequency in FREQUENCIES, 'Only actual3000/3030Hz responses registered')
    d, s = np.asarray(density, complex), np.asarray(source, complex)
    require(getattr(contacts.dtype, 'names', None) and {'pad', 'area_m2'} <= set(contacts.dtype.names), 'Physical contact fields required')
    pad, area = np.asarray(contacts['pad'], float), np.asarray(contacts['area_m2'], float)
    require(d.shape == (2, len(area)) and s.shape == (2, 2) and np.isfinite(d).all() and np.isfinite(s).all() and
        np.isfinite(pad).all() and np.all(pad == np.round(pad)) and set(pad.astype(int)) == set(range(4)) and
        np.isfinite(area).all() and np.all(area > 0), 'Finite channel-major contact density/source and physical4pads required')
    target = np.asarray(expected_areas, float)
    require(target.shape == (4,) and np.isfinite(target).all() and np.all(target > 0), 'Four positive represented pad areas required')
    actual_areas = np.asarray([area[pad == p].sum() for p in range(4)])
    area_error = float(np.max(abs(actual_areas/target-1)))
    require(area_error <= 1e-10, 'Actual native patch areas disagree with physical pad areas')
    r = np.asarray([np.sum(d[:, pad == p]*area[pad == p], axis=1) for p in range(4)])
    scale = max(float(np.max(abs(r))), float(np.max(abs(s))), 1e-30)
    source_error = float(np.max(abs(r[:2]-s))/scale)
    kcl_error = float(np.max(abs(r.sum(axis=0)))/scale)
    require(max(source_error, kcl_error) <= RESOLUTION, 'Actual net-pad/source/KCL gate exceeds2e-6')
    singular = np.linalg.svd(r[2:4], compute_uv=False)
    strongest, weakest = map(float, singular)
    relative = weakest/strongest if strongest > 0 else 0.
    rank = int(np.count_nonzero(singular > RESOLUTION*strongest)) if strongest > 0 else 0
    raw_condition = strongest/weakest if weakest > 0 else None
    if raw_condition is not None and not math.isfinite(raw_condition): raw_condition = None
    return_scale = max(float(np.max(abs(r[2:4]))), 1e-30)
    equal_rows_error = float(np.max(abs(r[2]-r[3]))/return_scale)
    denominator = r[2, 1] if frequency == 3000 else r[3, 0]
    return dict(frequency_Hz=frequency, status='measured_operator_rank2_at_native_resolution' if rank == 2 else
        'measured_operator_rank_deficient_at_native_resolution', physical_pad_response_peak_real_A=r.real.tolist(),
        physical_pad_response_peak_imaginary_A=r.imag.tolist(), source_matrix_peak_real_A=s.real.tolist(),
        source_matrix_peak_imaginary_A=s.imag.tolist(),
        response_definition='Ipad_peak_A = R[pad,source_basis] @ dimensionless command coefficients; each native basis is0.5Vpeak before50ohm,+jwt',
        physical_pad_areas_m2=actual_areas.tolist(), max_area_relative_error=area_error,
        signal_source_relative_error=source_error, full_pad_KCL_relative_error=kcl_error,
        return_singular_values_A=singular.tolist(), return_weakest_over_strongest=relative,
        return_rank_at_native_resolution=rank, native_relative_resolution=RESOLUTION,
        return_condition_number_raw=raw_condition,
        return_condition_number_at_native_resolution=raw_condition if rank == 2 else None,
        return_rows_difference_over_max_return_entry=equal_rows_error,
        return_rows_equal_within_native_resolution=equal_rows_error <= RESOLUTION,
        future_q_denominator=dict(row=2 if frequency == 3000 else 3, column=1 if frequency == 3000 else 0,
            absolute_A=float(abs(denominator)), relative_to_max_return_entry=float(abs(denominator)/return_scale),
            resolved=bool(abs(denominator)/return_scale > RESOLUTION)),
        rank_deficiency_is_valid_result=True, drive_weights_constructed=False,
        independent_return_nodes=0, common_GND_nodes=1, local_J_cancellation_inferred=False,
        physical_symmetry_inferred_from_rank=False, candidate_adopted=False)


def _small_bytes(path, maximum):
    require(maximum <= MAX_SMALL_BYTES, 'Declared small-array bound exceeded')
    opener = gzip.open if Path(path).suffix == '.gz' else open
    with opener(path, 'rb') as stream:
        raw = stream.read(maximum+1)
    require(len(raw) <= maximum, 'Small native file exceeds declared byte bound')
    return raw


def complex_array(path, shape):
    count = math.prod(shape); raw = _small_bytes(path, count*16)
    require(len(raw) == count*16, 'Truncated or oversized little-endian complex native array')
    result = np.frombuffer(raw, dtype='<c16').reshape(shape)
    require(np.isfinite(result).all(), 'Nonfinite native small array')
    return result


def load_contacts(path):
    raw = _small_bytes(path, 4*1024**2)
    reader = csv.DictReader(io.StringIO(raw.decode()))
    require(set(reader.fieldnames or []) == {'pad', 'x_mm', 'y_mm', 'area_m2'}, 'Exact native contact CSV columns required')
    rows = []
    for row in reader:
        require(len(rows) < 20000, 'Bounded20000 contact rows maximum')
        require(set(row) == set(reader.fieldnames), 'Malformed extra contact CSV columns')
        values = [float(row[name]) for name in ('pad', 'x_mm', 'y_mm', 'area_m2')]
        require(all(math.isfinite(v) for v in values), 'Nonfinite contact CSV')
        rows.append(tuple(values))
    return np.asarray(rows, dtype=[('pad', '<f8'), ('x_mm', '<f8'), ('y_mm', '<f8'), ('area_m2', '<f8')])


def implementation_receipt():
    paths = (Path(__file__).resolve(), ROOT/'tests/test_task1_return_rotation_operator_audit.py',
             Path(core.__file__).resolve(), Path(policy.__file__).resolve())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for p in paths:
        require(subprocess.check_output(['git', 'show', commit+':'+p.relative_to(ROOT).as_posix()], cwd=ROOT) == p.read_bytes(),
                'Commit all audit implementation sources/tests before preparation')
    return dict(implementation_git_commit=commit, implementation_files_sha256={str(p):core.sha(p) for p in paths})


def context_metadata(decision_path, feedback_path, refs):
    decision = read_json(decision_path, refs); feedback = read_json(feedback_path, refs)
    require(decision.get('schema') == 'task1-return-rotation-operator-root-decision-v1' and
        decision.get('status') == 'selected_not_executed' and decision.get('root_selected') is True and
        decision.get('peer_endorsed') is False and decision.get('new_PDE') == 0 and
        decision.get('source_cases') == list(SOURCE_CASES) and isinstance(decision.get('question'), str) and
        decision['question'].strip(), 'Explicit root-selected exact3-operator decision required')
    require(decision.get('feedback') == dict(path=str(Path(feedback_path)), SHA256=refs[str(Path(feedback_path))]), 'Feedback must match root decision pin')
    require(isinstance(decision.get('input_sha256'), dict) and decision['input_sha256'], 'Completed scientific metadata context required')
    for name, digest in decision['input_sha256'].items():
        require(Path(name).suffix == '.json', 'Root evidence context must be JSON, never native fields')
        pin(name, refs, digest)
    require(feedback.get('schema') == 'task1-queue-feedback-v1' and feedback.get('status') == 'read_only_feedback_checked'
        and feedback.get('error') is None and feedback.get('public_GitHub_only') is True and feedback.get('messages_sent') == 0
        and feedback.get('new_PDE') == 0 and feedback.get('peer_agreement_inferred') is False,
        'Actual public read-only feedback receipt required')
    count = 0
    for receipt in feedback.get('receipts', []):
        if receipt.get('kind') == 'comments':
            for row in receipt.get('evidence', []):
                require(hashlib.sha256(row['body'].encode()).hexdigest() == row['body_sha256'], 'Public feedback body SHA differs')
                count += 1
    require(count > 0, 'Actual public feedback comment evidence required')
    return dict(root_selected=True, peer_endorsed=False,
        decision=dict(path=str(Path(decision_path)), SHA256=refs[str(Path(decision_path))]),
        feedback=dict(path=str(Path(feedback_path)), SHA256=refs[str(Path(feedback_path))]))


def source_metadata(declared, refs):
    run = ROOT/'data-native'/declared['run_id']; ident = declared['case_id']
    pre_path, record_path = run/'preregistration.json', run/'cases'/(ident+'.json')
    pre = read_json(pre_path, refs); record = read_json(record_path, refs); terminal = read_json(run/'summary.json', refs)
    require(pre['status'] == 'prepared' and record['status'] == terminal['status'] == 'complete' and
            terminal['registration_sha256'] == refs[str(pre_path)], 'Actual completed source case/run required')
    matches = [c for c in pre['cases'] if c['id'] == ident]
    require(len(matches) == 1, 'Unique exact source case required'); case = matches[0]
    config_path = pin(case['config_file'], refs, case['config_sha256']); pin(case['mask_file'], refs, case['mask_sha256'])
    require(record['config_sha256'] == case['config_sha256'], 'Completed source configuration differs')
    summary_path = canonical(record['postprocess_path']); summary = read_json(summary_path, refs, record['postprocess_sha256'])
    require(summary['status'] == 'complete' and summary['id'] == ident, 'Actual completed producer summary required')
    basis = run/'bases'/ident; manifest = record['native_files']; arrays = {}
    def native(name):
        found = [basis/n for n in (name, name+'.gz') if (basis/n).is_file()]
        require(len(found) == 1, 'One unambiguous small native artifact required: '+name)
        p = found[0]; require(p.name in manifest, 'Small native file absent from completed source manifest')
        pin(p, refs, manifest[p.name]['sha256']); return str(p)
    complete = native('BASIS_COMPLETE'); validation_path = native('validation.json'); metadata_path = native('mesh-metadata.json')
    validation, metadata = core.read(validation_path), core.read(metadata_path)
    require(Path(complete).stat().st_size == 0, 'Native completion marker must be empty')
    for key, cap in core.GATES.items():
        require(type(validation.get(key)) in (int, float) and math.isfinite(validation[key]) and
                0 <= validation[key] <= cap, 'Completed native numerical gate failed: '+key)
    c = case['circuit']; config = properties(config_path)
    require(c['n_pads'] == 4 and c['n_outputs'] == 2 and c['n_return_nodes'] == 1 and
        c['pad_to_node'] == {'0':'out0', '1':'out1', '2':'GND', '3':'GND'} and c['source_resistance_ohm'] == 50,
        'Physical4pads/twooutputs/commonGND/50ohm required')
    require(metadata['exporter_class'] == 'SelectivityShapeBasis' and metadata['source_peak_V'] == .5 and
        metadata['source_resistance_ohm'] == 50 and metadata['phasor_convention'] == 'peak,+jomega_t' and
        metadata['channels'] == 2 and validation['channels'] == 2 and metadata['h_xy_mm'] == .625 and
        metadata['sc_cells'] == 2 and metadata['bulk_layer_counts'] == [14, 14, 40] and
        metadata['frequencies_Hz'] == [3000, 3030, 9000, 9090] and validation['cells'] == 351680 and
        metadata['radius_mm'] == 25 and metadata['total_depth_mm'] == 25.1 and
        metadata['tissue_boundaries_mm'] == [0, .1, 5.1, 10.1, 25.1] and
        metadata['config_sha256'] == case['config_sha256'], 'Same fine native producer/circuit/config ABI required')
    centres = [[-10.,-10.], [10.,10.], [10.,-10.], [-10.,10.]]
    require(all([float(config[f'pad.{i}.x_mm']), float(config[f'pad.{i}.y_mm'])] == xy for i, xy in enumerate(centres)),
            'Physical diagonal-source/return ordering differs')
    expected_areas = [.000225]*4 if declared['geometry'] == 'opposite-square' else [.00028125, .00028125, .00016875, .00016875]
    require(len(case['expected_pad_areas_m2']) == 4 and all(abs(a/b-1) <= 1e-10 for a,b in
        zip(case['expected_pad_areas_m2'], expected_areas)), 'Fixed900mm2 physical area allocation differs')
    require(all(abs(float(config[f'pad.{i}.represented_area_m2'])/a-1) <= 1e-10 for i,a in enumerate(expected_areas)),
            'Native config and physical area allocation disagree')
    for f in FREQUENCIES:
        arrays[str(f)] = {kind:native(f'{kind}-{f}.{suffix}') for kind, suffix in (('density','bin'), ('source','bin'), ('contacts','csv'))}
    return dict(**declared, source_commit=pre['source_commit'], configuration_sha256=case['config_sha256'],
        expected_pad_areas_m2=case['expected_pad_areas_m2'], physical_pad_centres_mm=centres, circuit=c,
        fixed_tissue_contact_properties={k:v for k,v in config.items() if k.startswith('z.') or k.endswith(('.sigma','.epsilon_r'))},
        registration_path=str(pre_path), source_case_receipt_path=str(record_path), source_summary_path=str(summary_path),
        native_validation=validation, actual_mesh_metadata_path=metadata_path, native_small_arrays=arrays,
        raw_E_phi_grid_volume_files_opened=False)


def make_preregistration(output, decision_path, feedback_path):
    refs = {}; selection = context_metadata(decision_path, feedback_path, refs)
    sources = [source_metadata(row, refs) for row in SOURCE_CASES]
    require(all(s['fixed_tissue_contact_properties'] == sources[0]['fixed_tissue_contact_properties'] for s in sources)
        and bool(sources[0]['fixed_tissue_contact_properties']), 'Matched tissue/contact electrical properties required across three cases')
    receipt = implementation_receipt(); refs.update(receipt['implementation_files_sha256'])
    ledger = policy.load_ledger(); refs.update(policy.policy_refs(ledger))
    return dict(schema=SCHEMA, status='preregistered_not_executed', created_utc=core.now(), output_directory=str(output),
        sources=sources, root_selection_context=selection, input_sha256=refs,
        frequencies_Hz=list(FREQUENCIES), native_relative_resolution=RESOLUTION, new_PDE=0, drive_weights_constructed=False,
        resource_limits=dict(CPU_count=1, total_seconds=60, RSS_bytes=3*GIB, free_disk_bytes=2*GIB,
            max_added_bytes=10*1024**2, cumulative_budget_seconds=policy.effective_limit(ledger)),
        read_scope='Only bounded JSON/config/mask and native density/source/contact3000/3030 bytes; never E,phi,grid orNPZ',
        holds=['Rank is an observed algebraic property at native2e-6 resolution, not independent-ground isolation or hardware validation',
               'No q/drive weights, candidate or localJ-zero inference; no mesh/contact/experimental/physiological validation'], **receipt)


def verify_plan(path, output, expected=None):
    p = canonical(path); digest = core.sha(p); plan = core.read(p)
    require(expected is None or digest == expected, 'Operator preregistration changed')
    require(plan['schema'] == SCHEMA and plan['status'] == 'preregistered_not_executed' and plan['output_directory'] == str(output)
        and plan['new_PDE'] == 0 and plan['drive_weights_constructed'] is False and plan['frequencies_Hz'] == list(FREQUENCIES)
        and plan['native_relative_resolution'] == RESOLUTION and
        [{k:s[k] for k in ('geometry','run_id','case_id')} for s in plan['sources']] == list(SOURCE_CASES),
        'Exact three-case small-operator scope required')
    for name, digest0 in plan['input_sha256'].items(): require(core.sha(canonical(name)) == digest0, 'Operator pinned source drift')
    require(implementation_receipt()['implementation_files_sha256'] == plan['implementation_files_sha256'], 'Audit implementation changed')
    return plan, digest


def execute(plan, output, checkpoint):
    results = []
    for source in plan['sources']:
        checkpoint('source_start', geometry=source['geometry']); rows = []; identity = None
        for f in FREQUENCIES:
            paths = source['native_small_arrays'][str(f)]; contacts = load_contacts(paths['contacts'])
            require(identity is None or np.array_equal(identity, contacts), 'Physical contact identity/order differs across frequencies')
            identity = contacts
            rows.append(response_diagnostics(complex_array(paths['density'], (2,len(contacts))), contacts,
                complex_array(paths['source'], (2,2)), source['expected_pad_areas_m2'], f))
        result = dict(**{k:source[k] for k in ('geometry','run_id','case_id','source_commit','configuration_sha256','circuit')},
            frequencies=rows, native_numerical_gates=source['native_validation'],
            hypothesis_status='Actual response measured; any equality/rank1 classification uses these values, never geometry alone',
            independent_return_control_resolved_at_both_frequencies=all(r['return_rank_at_native_resolution'] == 2 for r in rows),
            candidate_adopted=False, new_PDE=0)
        core.write(output/(source['geometry']+'.json'), result); results.append(result)
        checkpoint('source_complete', geometry=source['geometry'])
    return dict(schema='task1-return-rotation-operator-audit-v1', status='completed_operator_diagnostic', cases=results,
        new_PDE=0, drive_weights_constructed=False, candidate_adopted=False, independent_field_recalculation=False,
        symmetry_hypothesis='One Y return and one X return may restore x=y reflection for opposite symmetric cross sources; this is a hypothesis compared with measured R rows, not assumed a result',
        root_selection_context=plan['root_selection_context'], holds=plan['holds'])


def main():
    parser = argparse.ArgumentParser(description=__doc__); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path); group.add_argument('--preregistration', type=Path)
    parser.add_argument('--decision', type=Path); parser.add_argument('--feedback', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = args.output
    require(output.is_absolute() and output == output.resolve() and output.is_relative_to(ROOT/'docs') and
            output.parent.is_dir() and not output.exists(), 'New canonical docs output under existing parent required')
    with (ROOT/'.task1-execution.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB); fcntl.lockf(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        ledger_path = ROOT/'runtime/task1-budget.json'; ledger = policy.load_ledger(ledger_path)
        require(policy.remaining_seconds(ledger) >= 60 and shutil.disk_usage(output.parent).free >= 2*GIB+20*1024**2,
                'Reserve finite60s and2GiB free+20MiB allowance')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))}); started = time.monotonic()
        status, failure = 'failed_preserved', None; state = {}; count = 0; stop = threading.Event(); mutex = threading.RLock(); thread = None
        def guard():
            require(core.rss(os.getpid()) < 3*GIB and shutil.disk_usage(output.parent).free >= 2*GIB, 'Operator RSS/free disk cap exceeded')
            if output.exists(): require(sum(p.stat().st_size for p in output.rglob('*') if p.is_file()) <= 10*1024**2, 'Operator output10MiB cap exceeded')
        def checkpoint(phase, **extra):
            nonlocal count
            with mutex:
                guard(); count += 1; state.update(phase=phase,status=status if phase == 'complete' else 'running',pid=os.getpid(),proc_start_ticks=core.ticks(os.getpid()),updated_utc=core.now(),elapsed_seconds=time.monotonic()-started,**extra)
                core.write(output/f'checkpoint-{count:03d}-{phase}.json',dict(state)); core.write(output/'heartbeat.json',state)
        def heartbeat():
            while not stop.wait(5):
                try:
                    with mutex: guard(); core.write(output/'heartbeat.json',dict(state,updated_utc=core.now(),elapsed_seconds=time.monotonic()-started))
                except BaseException as error: state['resource_guard_failure'] = str(error); os.kill(os.getpid(),signal.SIGTERM); return
        def interrupted(signum,frame): raise TimeoutError('Finite60s operator diagnostic interrupted '+str(signum))
        old = {s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        for sig in old: signal.signal(sig,interrupted)
        signal.setitimer(signal.ITIMER_REAL,60)
        try:
            if args.prepare:
                require(args.prepare.is_absolute() and args.prepare == args.prepare.resolve() and
                    args.prepare.is_relative_to(ROOT/'docs') and not args.prepare.exists() and
                    not args.prepare.resolve().is_relative_to(output), 'New external canonical docs preregistration required')
                plan = make_preregistration(output,args.decision,args.feedback); args.prepare.parent.mkdir(parents=True,exist_ok=True)
                with args.prepare.open('x') as stream: stream.write(__import__('json').dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
                status = 'preregistered_not_executed'
            else:
                require(args.decision is None and args.feedback is None, 'Execution consumes frozen selection context only')
                output.mkdir(); thread = threading.Thread(target=heartbeat,daemon=True); thread.start(); checkpoint('verify_plan')
                plan, digest = verify_plan(args.preregistration,output); result = execute(plan,output,checkpoint)
                verify_plan(args.preregistration,output,digest); guard()
                result.update(implementation_receipt(),inputs_unchanged=True,input_sha256=plan['input_sha256'],
                    preregistration=dict(path=str(args.preregistration),SHA256=digest), resources=dict(wall_seconds=time.monotonic()-started,max_seconds=60,CPU_count=1,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
                core.write(output/'summary.json',result); status = result['status']; checkpoint('complete')
        except BaseException as error:
            failure = type(error).__name__+': '+str(error)
            if output.exists(): core.write(output/'failure.json',dict(status=status,error=failure,phase=state.get('phase'),new_PDE=0,partial_evidence_preserved=True,automatic_retry=False))
            elif args.prepare:
                failure_path = args.prepare.with_name(args.prepare.stem+'.failure.json')
                if failure_path.parent.is_dir() and not failure_path.exists(): core.write(failure_path,dict(status=status,error=failure,new_PDE=0,partial_evidence_preserved=True,automatic_retry=False))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL,0); stop.set()
            if thread is not None: thread.join(timeout=1)
            elapsed = time.monotonic()-started; ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.name,stage='return_rotation_operator_prepare' if args.prepare else 'return_rotation_operator_audit',seconds=elapsed,status=status,error=failure,finished_utc=core.now()))
            core.write(ledger_path,ledger)
            if output.exists(): core.write(output/'heartbeat.json',dict(state,status=status,error=failure,updated_utc=core.now(),elapsed_seconds=elapsed))
            for sig, handler in old.items(): signal.signal(sig,handler)
        print(__import__('json').dumps(dict(status=status,output=str(output),new_PDE=0)))


if __name__ == '__main__': main()
