#!/usr/bin/env python3
"""Publish only an explicit Task 1 result whitelist to the approved topic branch."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shlex
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import quote

import task1_bounded_continuation as bounded
import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'yoodohyun-codex-cloud/ngg-tis-task1'
BRANCH = 'codex/task1-cloud-restart-20261020'
COMMENT = 6314015870
GIB = 1024**3
EXTENSIONS = {'.json', '.md', '.html', '.png', '.csv', '.npz'}
SECRET = re.compile(rb'github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[Aa]uthorization\s*:\s*[Bb]earer\s+\S+')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def path(value, root=ROOT, *, exists=True, docs=False):
    p = Path(value)
    require(p.is_absolute() and p == p.resolve() and p.is_relative_to(root), 'Canonical repository path required')
    require(not p.is_symlink() and (not exists or p.is_file()), 'Regular nonsymlink file required: '+str(p))
    if docs:
        require(p.is_relative_to(root/'docs') and p.suffix.lower() in EXTENSIONS, 'Approved docs result type required')
    require(not any(re.search(r'(^\.env$|credential|private|secret|conversation|chat[-_]?log)', part, re.I) for part in p.relative_to(root).parts),
            'Private or credential path rejected')
    return p


def field(obj, dotted):
    for key in dotted.split('.'):
        obj = obj[key]
    return obj


def scan(p):
    require(p.stat().st_size <= 50*1024**2, 'Individual public artifact exceeds50MiB')
    with p.open('rb') as stream:
        tail = b''
        for block in iter(lambda: stream.read(1024**2), b''):
            require(SECRET.search(tail+block) is None, 'Secret signature rejected: '+str(p))
            tail = block[-512:]


def command(argv, *, root, deadline):
    """One bounded subprocess with inherited one-CPU affinity and tree RSS guard."""
    child = subprocess.Popen(argv, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    start = bounded.ticks(child.pid)
    known = {}
    try:
        while True:
            known.update(bounded.owned_descendants(child.pid, start, known))
            require(time.monotonic() < deadline, 'Publication120s deadline exceeded')
            require(bounded.rss(os.getpid())+sum(bounded.rss(pid) for pid in known) < 3*GIB, 'Publication aggregate3GiB RSS exceeded')
            require(shutil.disk_usage(root).free >= 2*GIB, 'Preserve2GiB disk reserve')
            try:
                output, _ = child.communicate(timeout=min(.25, max(.001, deadline-time.monotonic())))
                require(child.returncode == 0, argv[0]+' command failed with exit '+str(child.returncode))
                return output.decode()
            except subprocess.TimeoutExpired:
                continue
    finally:
        if child.poll() is None:
            known.update(bounded.owned_descendants(child.pid, start, known))
            for pid, tick in known.items():
                if bounded.live(pid, tick):
                    try: os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError: pass
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                for pid, tick in known.items():
                    if bounded.live(pid, tick):
                        try: os.kill(pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                child.wait(timeout=3)


def verify_spec(spec, root=ROOT):
    require(spec.get('schema') == 'task1-batch-publication-spec-v1' and spec.get('repository') == REPOSITORY
            and spec.get('branch') == BRANCH and spec.get('comment_id') == COMMENT, 'Exact approved repository/branch/comment required')
    require(re.fullmatch('[0-9a-f]{40}', spec.get('parent_admission_commit', '')) is not None, 'Full parent admission commit required')
    files = [path(row['path'], root, docs=True) for row in spec['files']]
    require(1 <= len(files) <= 256 and len(set(files)) == len(files), 'Distinct explicit publish files required')
    require(sum(p.stat().st_size for p in files) <= 512*1024**2, 'Bounded512MiB publication maximum')
    for row, p in zip(spec['files'], files):
        scan(p)
        expected = row.get('sha256')
        if 'sha256_from' in row:
            ref = row['sha256_from']; expected = field(bounded.read(path(ref['path'], root)), ref['field'])
        require(expected is None or bounded.sha(p) == expected, 'Approved file hash differs')
    for name, digest in spec.get('input_sha256', {}).items():
        require(bounded.sha(path(name, root)) == digest, 'Immutable publisher input drift: '+name)
    body = path(spec['body_file'], root, docs=True)
    require(body.suffix.lower() == '.md' and bounded.sha(body) == spec['body_sha256'], 'Pinned preapproved public Markdown body required')
    scan(body)
    require(body.stat().st_size <= 32000, 'Comment body maximum32kB')
    artifacts = []
    require(spec.get('required_completed_artifacts'), 'Actual completed artifacts required')
    for row in spec['required_completed_artifacts']:
        p = path(row['path'], root); obj = bounded.read(p)
        require(obj.get('status') in row['statuses'], 'Required calculation is not complete: '+str(p))
        proof = False
        if 'sha256' in row:
            require(bounded.sha(p) == row['sha256'], 'Completed artifact hash mismatch'); proof = True
        if 'hash_proof' in row:
            ref = row['hash_proof']
            require(bounded.sha(p) == field(bounded.read(path(ref['path'], root)), ref['field']), 'Artifact receipt hash mismatch'); proof = True
        if 'source_hashes_field' in row:
            refs = field(obj, row['source_hashes_field'])
            require(isinstance(refs, dict) and refs and obj.get('inputs_unchanged', obj.get('native_inputs_unchanged')) is True,
                    'Completed source-bound report required')
            for name, digest in refs.items():
                require(bounded.sha(path(name, root)) == digest, 'Completed report source hash drift')
            proof = True
        for name, sha_field in row.get('source_files', {}).items():
            require(bounded.sha(path(name, root)) == field(obj, sha_field), 'Completed native provenance mismatch'); proof = True
        require(proof, 'Each completion requires hash or consumed-source proof')
        artifacts.append(dict(path=str(p), SHA256=bounded.sha(p), status=obj['status']))
    return files, body, artifacts


def publish(spec_path, output, *, root=ROOT, runner=command):
    spec_path = path(spec_path, root); spec_sha = bounded.sha(spec_path)
    output = path(output, root, exists=False, docs=True)
    require(output.suffix == '.json' and not output.exists(), 'New publication receipt required; no retries')
    marker = output.with_name(output.stem+'.attempt.json')
    require(not marker.exists(), 'Prior publication attempt preserved')
    with bounded.dual_lock(root/'.task1-execution.lock'):
        ledger = policy.load_ledger(root/'runtime/task1-budget.json')
        require(policy.effective_limit(ledger) == 13800 and policy.remaining_seconds(ledger) >= 120, 'Reserve120s inside approved13800s policy')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        started = time.monotonic(); deadline = started+120
        receipt = dict(schema='task1-batch-publication-v1', status='failed_preserved', phase='validation', started_utc=bounded.now(),
            spec_path=str(spec_path), spec_sha256=spec_sha, repository=REPOSITORY, branch=BRANCH, comment_id=COMMENT,
            commit_created=False, push_succeeded=False, comment_updated=False, no_automatic_retry=True)
        with marker.open('x') as stream: json.dump(dict(pid=os.getpid(), proc_start_ticks=bounded.ticks(os.getpid()), started_utc=bounded.now()), stream)
        def run(args):
            return runner(args, root=root, deadline=deadline).strip()
        def git(*args):
            return run(['git', '-c', 'pack.threads=1', *args])
        def checkpoint(phase):
            receipt.update(phase=phase, updated_utc=bounded.now()); bounded.write(output, receipt)
        old = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
        def interrupted(signum, frame): raise TimeoutError('Controlled publication signal '+str(signum))
        for sig in old: signal.signal(sig, interrupted)
        signal.setitimer(signal.ITIMER_REAL, 120)
        try:
            spec = bounded.read(spec_path); files, body_file, artifacts = verify_spec(spec, root)
            require(output not in files and marker not in files, 'Mutable publication receipt must not be staged')
            require(git('branch', '--show-current') == BRANCH, 'Current branch differs from approved topic branch')
            require(git('remote', 'get-url', 'origin') in ['https://github.com/'+REPOSITORY+'.git', 'https://github.com/'+REPOSITORY, 'git@github.com:'+REPOSITORY+'.git'], 'Origin repository differs')
            require(not git('diff', '--cached', '--name-only', '-z'), 'Existing staged changes require root review')
            git('merge-base', '--is-ancestor', spec['parent_admission_commit'], 'HEAD')
            before = git('rev-parse', 'HEAD')
            hashes = {str(p): bounded.sha(p) for p in files}
            receipt.update(source_commit_before=before, approved_file_sha256=hashes, completed_artifacts=artifacts)
            rel = [p.relative_to(root).as_posix() for p in files]
            checkpoint('stage_explicit_whitelist'); git('add', '--', *rel)
            staged = git('diff', '--cached', '--name-only', '-z').split('\0')
            require(set(filter(None, staged)) <= set(rel), 'Unlisted staged changes detected')
            require(all(bounded.sha(p) == hashes[str(p)] for p in files), 'Files changed before commit')
            if any(staged):
                checkpoint('commit_explicit_whitelist')
                message = spec.get('commit_message', 'Publish completed Task 1 finite batch results')
                require(isinstance(message, str) and 1 <= len(message) <= 200 and '\n' not in message, 'Single-line publication commit message required')
                git('commit', '--only', '-m', message, '--', *rel); receipt['commit_created'] = True
            commit = git('rev-parse', 'HEAD'); receipt['published_commit'] = commit
            require(set(filter(None, git('diff', '--name-only', before, commit, '--').splitlines())) <= set(rel), 'Publication commit changed unlisted paths')
            require(all(bounded.sha(p) == hashes[str(p)] for p in files) and bounded.sha(spec_path) == spec_sha, 'Publication input drift')
            checkpoint('push_topic_branch'); git('push', 'origin', commit+':refs/heads/'+BRANCH); receipt['push_succeeded'] = True
            checkpoint('verify_fixed_comment')
            endpoint = 'repos/'+REPOSITORY+'/issues/comments/'+str(COMMENT)
            comment = json.loads(run(['gh', 'api', endpoint]))
            require(comment.get('id') == COMMENT and comment.get('user', {}).get('login') == 'yoodohyun-codex-cloud'
                    and comment.get('issue_url', '').endswith('/issues/2'), 'Fixed approved progress comment ownership mismatch')
            text = body_file.read_text()+'\n\n실제 게시 commit: ['+commit[:12]+'](https://github.com/'+REPOSITORY+'/commit/'+commit+')\n'
            for p in files:
                text += '\n- ['+p.name+'](https://github.com/'+REPOSITORY+'/blob/'+commit+'/'+quote(p.relative_to(root).as_posix())+')'
            text += '\n\n계산 완료·수치 수렴·실험 검증 상태는 각 결과의 독립 상태를 따릅니다. 자동 후보 채택이나 무기한 실행을 뜻하지 않습니다.\n'
            require(len(text.encode()) <= 60000, 'Rendered public comment exceeds60kB')
            body_path = root/'runtime'/('publication-'+output.stem+'-body.md')
            with body_path.open('x') as stream: stream.write(text)
            receipt['comment_body_path'] = str(body_path)
            checkpoint('patch_fixed_progress_comment')
            patched = json.loads(run(['gh', 'api', '-X', 'PATCH', endpoint, '-F', 'body=@'+str(body_path)]))
            require(patched.get('id') == COMMENT, 'Unexpected patched comment receipt')
            receipt.update(status='published_completed_batch', comment_updated=True, comment_url=patched.get('html_url'),
                stop_reason='Completed finite result publication', resume_condition=spec.get('resume_condition', 'Root reviews saved results and preregisters next finite batch'))
        except BaseException as error:
            receipt.update(error_type=type(error).__name__, error=str(error), failed_phase=receipt['phase'],
                resume_condition='Inspect partial receipt; do not rerun attempted publication or overwrite evidence')
            if receipt['push_succeeded'] and receipt.get('comment_body_path'):
                receipt['next_command'] = shlex.join(['gh', 'api', '-X', 'PATCH', 'repos/'+REPOSITORY+'/issues/comments/'+str(COMMENT), '-F', 'body=@'+receipt['comment_body_path']])
            elif receipt['push_succeeded']:
                receipt['next_command'] = shlex.join(['gh', 'api', 'repos/'+REPOSITORY+'/issues/comments/'+str(COMMENT)])
            elif receipt.get('published_commit'):
                receipt['next_command'] = shlex.join(['git', 'push', 'origin', receipt['published_commit']+':refs/heads/'+BRANCH])
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            elapsed = time.monotonic()-started
            receipt.update(finished_utc=bounded.now(), resources=dict(wall_seconds=elapsed, maximum_seconds=120, CPU_count=1,
                process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
            bounded.write(output, receipt)
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem, stage='completed_batch_publication', status=receipt['status'], seconds=elapsed,
                error=receipt.get('error'), finished_utc=bounded.now()))
            bounded.write(root/'runtime/task1-budget.json', ledger)
            for sig, handler in old.items(): signal.signal(sig, handler)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--spec', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); result = publish(args.spec, args.output); print(json.dumps(dict(status=result['status'], commit=result.get('published_commit'))))


if __name__ == '__main__': main()
