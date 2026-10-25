#!/usr/bin/env python3
"""Finite metadata-only M/T finalizer, called AFTER one completed batch owner.

No numerical imports, native-array access or locks. The caller owns overall
runtime and aggregate RSS+all-task-tmpfs supervision. Each standalone r3
publication owns its normal locks and is bounded by a 330-second outer timeout.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from frozen_manifest_validation import safe_path, validate_manifest
from incremental_transfer import merge_files, merge_manifest, read_json_metadata, receipt_entries
from metadata_plan import metadata_publication_plan

PUBLISHER = Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
REPOSITORY = 'yoodohyun-codex-cloud/ngg-tis-task1'
BRANCH = 'codex/task1-cloud-restart-20261020'
PUBLIC_ROOT = 'docs/TASK1_CONTACT_EDGE_20261025'
PUBLICATION_TIMEOUT = 330


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def metadata_identity(path):
    doc, digest, size = read_json_metadata(path)
    return doc, {'SHA256': digest, 'bytes': size}


def new_json(path, obj):
    path = Path(path)
    raw = (json.dumps(obj, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {'SHA256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def same_or_create(path, obj):
    path = Path(path)
    if path.exists():
        old, _, _ = read_json_metadata(path)
        require(old == obj, 'Existing immutable metadata differs; preserve it and inspect')
        return
    new_json(path, obj)


def verified_publication(path, expected_plan):
    receipt, _, _ = read_json_metadata(path)
    receipt_entries(receipt)
    require(receipt.get('expected_parent') == expected_plan['expected_parent'],
            'Existing publication receipt belongs to another frozen parent')
    files = expected_plan['files']
    require(set(receipt['files']) == set(files), 'Publication file set differs from frozen plan')
    for target, item in files.items():
        proof = receipt['files'][target]
        require(proof['SHA256'] == item['SHA256'] and proof['bytes'] == item['bytes'],
                'Publication proof differs from planned metadata bytes')
    return receipt


def publish_stage(stage, plan, directory, run_token):
    """Resume the exact r3 plan/output. No finalizer lock or blind duplicate push."""
    directory.mkdir(exist_ok=True)
    require(directory.is_dir() and directory == directory.resolve() and not directory.is_symlink(),
            'Publication stage directory must be canonical and not a symlink')
    plan_path = directory / 'private-plan.json'
    same_or_create(plan_path, plan)
    # Original plan input files must still have exactly their frozen JSON bytes.
    for item in plan['files'].values():
        _, digest, size = read_json_metadata(item['local_path'])
        require(digest == item['SHA256'] and size == item['bytes'],
                'Frozen publication metadata changed')
    receipt_path = Path(plan['required_result_receipt'])
    if receipt_path.exists():
        return verified_publication(receipt_path, plan), 'verified_existing_publication_reused'
    output = Path('/dev/shm') / ('task1-auto-transfer-' + run_token + '-' + stage.lower())
    # The publisher requires its work directory directly under /dev/shm.
    # Its own receipt target and every local finalizer checkpoint remain in run/auto-transfer.
    log_path = directory / ('publisher-' + str(time.time_ns()) + '.log')
    with log_path.open('xb') as log:
        child = subprocess.Popen([sys.executable, str(PUBLISHER), '--plan', str(plan_path),
                                  '--output', str(output)], stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = child.wait(timeout=PUBLICATION_TIMEOUT)
        except subprocess.TimeoutExpired:
            # r3 has its own 300s watchdog and descendant cleanup. Request that
            # cleanup first; do not touch unrelated owners or process groups.
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            if receipt_path.exists():
                return verified_publication(receipt_path, plan), 'publication_verified_before_outer_timeout'
            raise TimeoutError(stage + ' publication exceeded330s; original plan/checkpoints preserved')
    # A successful scientific publication receipt takes precedence over an
    # ancillary process exit, and prevents a second commit/push on resume.
    if receipt_path.exists():
        return verified_publication(receipt_path, plan), 'published_readback_verified'
    require(returncode == 0, stage + ' publisher failed; preserved log/checkpoints require exact resume')
    raise RuntimeError(stage + ' publisher exited without a standard verified receipt')


def file_plan(path):
    _, digest, size = read_json_metadata(path)
    return {'local_path': str(Path(path).resolve()), 'SHA256': digest, 'bytes': size}


def finalize(args):
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', args.package_id) is not None,
            'Safe unique package ID required')
    require(re.fullmatch(r'[0-9a-f]{64}', args.expected_previous_sha256) is not None,
            'Full previous-manifest SHA256 required')
    run = Path(args.run)
    require(run.is_absolute() and run == run.resolve() and run.is_dir() and not run.is_symlink(),
            'Canonical completed owner run required')
    previous, old_identity = metadata_identity(args.previous)
    require(old_identity['SHA256'] == args.expected_previous_sha256, 'Previous manifest hash mismatch')
    validate_manifest(previous)
    source_path = run / 'source-publication' / 'result-publication.json'
    result_path = run / 'result-publication' / 'result-publication.json'
    owner_path = run / 'receipt.json'
    prereg_path = run / 'preregistration.json'
    source, source_identity = metadata_identity(source_path)
    result, result_identity = metadata_identity(result_path)
    owner, owner_identity = metadata_identity(owner_path)
    _, prereg_identity = metadata_identity(prereg_path)
    decision_path = run / 'continuation-decision.json'
    decision_identity = metadata_identity(decision_path)[1] if decision_path.exists() else None
    required_originals = {'owner': owner_path, 'preregistration': prereg_path}
    if decision_identity is not None:
        required_originals['continuation-decision'] = decision_path
    receipt_entries(source); receipt_entries(result)
    status = owner.get('status', '')
    require(isinstance(status, str) and re.search(r'(^|_)published($|_)', status) is not None and
            not any(x in status.lower() for x in ('not_published', 'failed', 'error', 'running', 'pending', 'interrupted', 'timeout')),
            'Owner is not in an explicitly completed published state')
    require(owner.get('source_commit') == source['commit'] and owner.get('result_commit') == result['commit'],
            'Owner source/result commits do not match verified original receipts')
    require(PUBLISHER.is_file() and not PUBLISHER.is_symlink(), 'Existing approved r3 publisher unavailable')
    auto = run / 'auto-transfer'
    if auto.exists():
        require(auto.is_dir() and auto == auto.resolve() and not auto.is_symlink(), 'Unsafe existing finalizer directory')
    else:
        auto.mkdir()
    for stage in ('M', 'T'):
        (auto / stage).mkdir(exist_ok=True)
    attempt = auto / ('attempt-' + str(time.time_ns()) + '.json')
    started = time.monotonic()
    record = {'schema': 'task1-after-batch-transfer-attempt-v1', 'package_id': args.package_id,
              'started_UTC': now(), 'status': 'failed_preserved', 'new_PDE': 0,
              'Windows_backup_complete': False, 'OneDrive_sync_verified': False,
              'source_commit': source['commit'], 'result_commit': result['commit'],
              'stage_timeout_seconds': PUBLICATION_TIMEOUT}
    run_token = args.package_id + '-' + hashlib.sha256(str(run).encode()).hexdigest()[:12]
    pins = {}
    for name in ('finalize_transfer.py', 'metadata_plan.py', 'incremental_transfer.py', 'frozen_manifest_validation.py'):
        pins[name] = hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
    pins['approved-r3-publisher'] = hashlib.sha256(PUBLISHER.read_bytes()).hexdigest()
    registration = {'schema': 'task1-after-batch-transfer-registration-v1',
                    'package_id': args.package_id, 'source_commit': source['commit'],
                    'result_commit': result['commit'], 'previous_manifest': old_identity,
                    'source_receipt': source_identity, 'result_receipt': result_identity,
                    'owner_receipt': owner_identity, 'preregistration': prereg_identity,
                    'continuation_decision': decision_identity,
                    'source_SHA256': pins, 'new_PDE': 0, 'Windows_saved_verified': False}
    same_or_create(auto / 'registration.json', registration)
    try:
        prefix = PUBLIC_ROOT + '/' + args.package_id + '-metadata'
        safe_path(prefix)
        mreceipt_path = auto / 'M' / 'result-publication.json'
        mplan = metadata_publication_plan(source_receipt_path=source_path,
            result_receipt_path=result_path, owner_receipt_path=owner_path,
            preregistration_path=prereg_path, repo_prefix=prefix,
            expected_parent=result['commit'], required_result_receipt=mreceipt_path,
            package_id=args.package_id,
            extra_metadata={'continuation-decision.json': decision_path} if decision_identity is not None else None)
        metadata, mstatus = publish_stage('M', mplan, auto / 'M', run_token)
        record.update(M_status=mstatus, metadata_commit=metadata['commit'])
        manifest_path = auto / (args.package_id + '-transfer-manifest.json')
        if not manifest_path.exists():
            manifest_proof = merge_files(args.previous, source_path, result_path,
                mreceipt_path, manifest_path, package_id=args.package_id,
                expected_previous_sha256=args.expected_previous_sha256,
                extra_original_metadata=required_originals)
        else:
            existing, digest, size = read_json_metadata(manifest_path)
            _, metadata_sha, _ = read_json_metadata(mreceipt_path)
            required_hashes = {'source-publication-receipt': source_identity['SHA256'],
                'result-publication-receipt': result_identity['SHA256'],
                'owner': owner_identity['SHA256'], 'preregistration': prereg_identity['SHA256']}
            if decision_identity is not None:
                required_hashes['continuation-decision'] = decision_identity['SHA256']
            expected = merge_manifest(previous, source, result, metadata,
                package_id=args.package_id, previous_manifest_sha256=args.expected_previous_sha256,
                original_receipt_hashes=required_hashes,
                metadata_receipt_sha256=metadata_sha)
            expected['created_UTC'] = existing['created_UTC']
            require(existing == expected, 'Existing merged manifest differs; do not overwrite')
            manifest_proof = {'manifest_SHA256': digest, 'manifest_bytes': size,
                'files': len(existing['files']), 'aliases': len(existing['logical_file_aliases'])}
        public_manifest = PUBLIC_ROOT + '/' + manifest_path.name
        identity = {'schema': 'task1-contact-transfer-identity-v1', 'package_id': args.package_id,
            'source_commit': source['commit'], 'result_commit': result['commit'],
            'metadata_commit': metadata['commit'], 'previous_manifest_SHA256': args.expected_previous_sha256,
            'manifest_repo_relative_path': public_manifest,
            'manifest_SHA256': manifest_proof['manifest_SHA256'], 'manifest_bytes': manifest_proof['manifest_bytes'],
            'objects': manifest_proof['files'], 'aliases': manifest_proof['aliases'],
            'Windows_backup_complete': False, 'OneDrive_sync_verified': False,
            'new_PDE_in_transfer': 0, 'experimental_validation_inferred': False,
            'scope': 'Preserved previous scope plus this completed finite diagnostic; no actual4pad interpretation or physiological/safety claim is added by transfer.'}
        identity_path = auto / (args.package_id + '-transfer-identity.json')
        same_or_create(identity_path, identity)
        tplan = {'schema': 'task1-supported-Git-transport-plan-v1',
            'repository': REPOSITORY, 'branch': BRANCH, 'expected_parent': metadata['commit'],
            'new_PDE_required': False, 'message': 'Preserve additive transfer manifest ' + args.package_id,
            'required_result_receipt': str(auto / 'T' / 'result-publication.json'),
            'files': {public_manifest: file_plan(manifest_path),
                      PUBLIC_ROOT + '/' + identity_path.name: file_plan(identity_path)}}
        transfer, tstatus = publish_stage('T', tplan, auto / 'T', run_token)
        record.update(status='metadata_and_additive_manifest_published_readback_verified',
            T_status=tstatus, transfer_commit=transfer['commit'], manifest_SHA256=identity['manifest_SHA256'],
            manifest_bytes=identity['manifest_bytes'], objects=identity['objects'], aliases=identity['aliases'],
            manifest_repo_relative_path=public_manifest,
            manifest_URL='https://github.com/' + REPOSITORY + '/raw/' + transfer['commit'] + '/' + public_manifest,
            receipt_closure='T publication receipt retained separately; no self-referential manifest requirement')
        same_or_create(auto / 'completed-transfer-identity.json', {
            key: record[key] for key in ('package_id', 'source_commit', 'result_commit',
                'metadata_commit', 'transfer_commit', 'manifest_SHA256', 'manifest_bytes',
                'objects', 'aliases', 'manifest_repo_relative_path', 'Windows_backup_complete', 'OneDrive_sync_verified')})
        return record
    except BaseException as error:
        record.update(error_type=type(error).__name__, error=str(error),
            blocker='Preserved exact plans/publication checkpoints; no native recomputation or duplicate push authorized',
            resume_condition='Completed owner and unchanged original metadata/source pins; rerun this exact finalizer command after resolving the recorded publication/environment blocker')
        raise
    finally:
        record.update(finished_UTC=now(), elapsed_seconds=time.monotonic() - started)
        new_json(attempt, record)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True)
    ap.add_argument('--previous', required=True)
    ap.add_argument('--expected-previous-sha256', required=True)
    ap.add_argument('--package-id', required=True)
    args = ap.parse_args()
    result = finalize(args)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
