#!/usr/bin/env python3
"""Publish the completed compact GUI through Git Database without local blob copies.

Explicit root execution only. One immutable attempt, no automatic retries/fetch,
force push, cleanup, reserve relaxation, or public comment mutation.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time

import task1_batch_publish as publication
import task1_bounded_continuation as bounded
import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = publication.REPOSITORY
BRANCH = publication.BRANCH
DIRECTORY = 'docs/TASK1_TOP5_20261022_compact'
GIB = 1024**3
require = publication.require


def validate_bundle(directory, final_validation, *, root=ROOT):
    directory, final_validation = Path(directory), Path(final_validation)
    require(directory == root/DIRECTORY and directory == directory.resolve() and not directory.is_symlink(), 'Exact compact directory required')
    files = [directory/name for name in ('index.html', 'manifest.json', 'preview.png', 'README.md')]
    for p in files:
        publication.path(str(p), root, docs=True); publication.scan(p)
    manifest = bounded.read(directory/'manifest.json')
    require(manifest.get('status') == 'compact_dashboard_complete_unadopted' and manifest.get('native_inputs_unchanged') is True, 'Completed source-bound compact GUI required')
    for name in ('index.html', 'preview.png'):
        proof = manifest['artifacts'][name]; p = directory/name
        require(bounded.sha(p) == proof['SHA256'] and p.stat().st_size == proof['bytes'], 'Manifest artifact byte/SHA mismatch: '+name)
    publication.path(str(final_validation), root, docs=True); publication.scan(final_validation)
    validation = bounded.read(final_validation)
    require(validation.get('status') == 'existing_compact_GUI_verified_unadopted', 'Passed existing-compact final validation required')
    pins = validation.get('input_sha256', {})
    for name in ('manifest.json','index.html'):
        require(pins.get(str(directory/name)) == bounded.sha(directory/name), 'Final validation input SHA mismatch: '+name)
    if final_validation == directory/'final_validation.json': files.append(final_validation)
    require(sum(p.stat().st_size for p in files) <= 8*1024**2, 'Compact publication bounded to8MiB')
    return files


def remote_update(head, files, run, *, root=ROOT, receipt=None):
    """Only called by publish; run is replaceable for fully synthetic tests."""
    receipt = receipt if receipt is not None else {}
    require(re.fullmatch('[0-9a-f]{40}', head) is not None, 'Exact local parent commit required')
    prefix = 'repos/'+REPOSITORY+'/'
    def api(endpoint, payload=None, method='GET'):
        argv = ['gh','api',prefix+endpoint,'-X',method]
        body = None
        if payload is not None:
            argv += ['--input','-']; body = json.dumps(payload,separators=(',',':')).encode()
        return json.loads(run(argv,input_bytes=body))
    ref = 'git/ref/heads/'+BRANCH
    require(api(ref)['object']['sha'] == head, 'Remote HEAD advanced or local parent not pushed; abort')
    base_tree = api('git/commits/'+head)['tree']['sha']
    entries = []
    receipt['uploaded_blobs'] = []
    for p in files:
        data = p.read_bytes(); content_sha = hashlib.sha256(data).hexdigest()
        if 'source_SHA256' in receipt:
            require(receipt['source_SHA256'].get(str(p)) == content_sha, 'Pinned local publication bytes changed before upload')
        expected = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        result = api('git/blobs',dict(content=base64.b64encode(data).decode(),encoding='base64'),'POST')
        require(result['sha'] == expected, 'Remote blob Git SHA differs from exact local bytes')
        row = dict(path=p.relative_to(root).as_posix(),mode='100644',type='blob',sha=expected)
        entries.append(row); receipt['uploaded_blobs'].append(dict(**row,SHA256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
    tree = api('git/trees',dict(base_tree=base_tree,tree=entries),'POST')['sha']
    commit = api('git/commits',dict(message='Publish completed compact Task1 top5 GUI without local blob duplication',tree=tree,parents=[head]),'POST')['sha']
    receipt.update(remote_commit_created=commit,remote_tree_sha=tree,parent_tree_sha=base_tree)
    require(api(ref)['object']['sha'] == head, 'Concurrent remote advance; immutable orphan objects preserved, ref unchanged')
    api('git/refs/heads/'+BRANCH,dict(sha=commit,force=False),'PATCH')
    receipt['remote_ref_updated'] = True
    require(api(ref)['object']['sha'] == commit, 'Remote ref verification differs')
    created = api('git/commits/'+commit)
    require(created['tree']['sha'] == tree and [p['sha'] for p in created['parents']] == [head], 'Remote commit parent/tree differs')
    # Inspect only small tree metadata; do not fetch HTML/PNG blobs or a full tree.
    cursor = tree
    for name in ('docs',Path(DIRECTORY).name):
        listing = api('git/trees/'+cursor)
        require(not listing.get('truncated'), 'Tree metadata truncated')
        matches = [r for r in listing['tree'] if r['path'] == name and r['type'] == 'tree']
        require(len(matches) == 1, 'Missing exact remote directory tree'); cursor = matches[0]['sha']
    listing = api('git/trees/'+cursor)
    require(not listing.get('truncated'), 'Artifact tree metadata truncated')
    for expected in entries:
        actual = [r for r in listing['tree'] if r['path'] == Path(expected['path']).name]
        require(len(actual) == 1 and all(actual[0][k] == expected[k] for k in ('mode','type','sha')), 'Remote asset tree SHA/mode differs')
    receipt['remote_tree_entries_verified'] = True
    return commit


def guarded_command(argv, *, root, deadline, input_bytes=None):
    """RAM-only stdin/stdout,8MiB output cap; same original live resource caps."""
    child = subprocess.Popen(argv,cwd=root,stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
    known, output = {}, bytearray(); tick = bounded.ticks(child.pid)
    poll = selectors.DefaultSelector(); os.set_blocking(child.stdout.fileno(),False)
    poll.register(child.stdout,selectors.EVENT_READ)
    data = memoryview(input_bytes or b''); offset = 0
    if child.stdin:
        os.set_blocking(child.stdin.fileno(),False); poll.register(child.stdin,selectors.EVENT_WRITE)
    try:
        while poll.get_map():
            known.update(bounded.owned_descendants(child.pid,tick,known))
            require(time.monotonic() < deadline,'Publication180s deadline exceeded')
            require(shutil.disk_usage(root).free >= 2*GIB,'Preserve original2GiB disk reserve')
            require(bounded.rss(os.getpid())+sum(bounded.rss(p) for p in known) < 3*GIB,'Publication aggregate3GiB RSS exceeded')
            for key, event in poll.select(.1):
                if key.fileobj is child.stdin:
                    try: offset += os.write(key.fd,data[offset:offset+65536])
                    except BrokenPipeError: offset = len(data)
                    if offset == len(data): poll.unregister(child.stdin); child.stdin.close()
                else:
                    block = os.read(key.fd,65536)
                    if not block: poll.unregister(child.stdout)
                    else: output.extend(block); require(len(output) <= 8*1024**2,'Bounded API stdout exceeded8MiB')
        child.wait(timeout=max(.01,deadline-time.monotonic()))
        require(child.returncode == 0,argv[0]+' command failed exit '+str(child.returncode)+'; stderr withheld')
        return output.decode()
    finally:
        poll.close()
        if child.poll() is None:
            known.update(bounded.owned_descendants(child.pid,tick,known))
            for p,t in known.items():
                if bounded.live(p,t):
                    try: os.kill(p,signal.SIGKILL)
                    except ProcessLookupError: pass
            child.wait(timeout=3)


def publish(output, final_validation, *, root=ROOT, runner=guarded_command):
    output = publication.path(str(output),root,exists=False,docs=True)
    marker = output.with_name(output.stem+'.attempt.json')
    require(not output.exists() and not marker.exists(),'New immutable publication attempt required')
    with bounded.dual_lock(root/'.task1-loop.lock'), bounded.dual_lock(root/'.task1-execution.lock'):
        ledger = policy.load_ledger(root/'runtime/task1-budget.json')
        require(policy.effective_limit(ledger) == 13800 and policy.remaining_seconds(ledger) >= 180,'Reserve180s within existing13800s budget')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
        started = time.monotonic(); deadline = started+180
        receipt = dict(schema='task1-compact-remote-publication-v1',status='failed_preserved',started_utc=bounded.now(),repository=REPOSITORY,
            branch=BRANCH,remote_ref_updated=False,no_automatic_retry=True,new_PDE=0,existing_originals_deleted=False,disk_reserve_bytes=2*GIB)
        def run(argv,input_bytes=None): return runner(argv,root=root,deadline=deadline,input_bytes=input_bytes)
        def git(*args): return run(['git','-c','gc.auto=0','-c','pack.threads=1',*args]).strip()
        old = {s:signal.getsignal(s) for s in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        def interrupted(signum, frame): raise TimeoutError('Controlled bounded publication signal '+str(signum))
        for s in old: signal.signal(s,interrupted)
        signal.setitimer(signal.ITIMER_REAL,180)
        try:
            require(shutil.disk_usage(root).free >= 2*GIB+2*(root/'runtime/task1-budget.json').stat().st_size+65536,'Preserve2GiB plus atomic ledger/receipt write headroom')
            bounded.write(marker,dict(pid=os.getpid(),proc_start_ticks=bounded.ticks(os.getpid()),started_utc=receipt['started_utc']))
            files = validate_bundle(root/DIRECTORY,final_validation,root=root)
            require(git('branch','--show-current') == BRANCH,'Exact approved topic branch required')
            require(git('remote','get-url','origin') in ['https://github.com/'+REPOSITORY+'.git','https://github.com/'+REPOSITORY,'git@github.com:'+REPOSITORY+'.git'],'Exact repository origin required')
            require(not git('diff','--cached','--name-only'),'Existing staged changes require root review')
            head = git('rev-parse','HEAD'); receipt['local_HEAD'] = head
            receipt['publication_source_commit'] = head
            receipt['publication_source_SHA256'] = {str(p):bounded.sha(p) for p in (
                root/'tools/task1_top5_remote_publish.py',root/'tests/test_task1_top5_remote_publish.py')}
            pins = {str(p):bounded.sha(p) for p in files}; receipt['source_SHA256'] = pins
            receipt['final_validation_SHA256'] = bounded.sha(final_validation)
            git('push','origin',head+':refs/heads/'+BRANCH)
            require(all(bounded.sha(p) == h for p,h in ((Path(k),v) for k,v in pins.items())),'Local artifact drift before upload')
            commit = remote_update(head,files,run,root=root,receipt=receipt)
            require(git('rev-parse','HEAD') == head,'Local HEAD changed during remote publication')
            require(all(bounded.sha(Path(k)) == v for k,v in pins.items()),'Published local evidence changed')
            receipt.update(status='published_remote_only_commit',published_commit=commit,local_HEAD=head,remote_HEAD=commit,
                local_branch_intentionally_behind_commits=1,local_git_blob_copies_created=False,
                next_step='Keep local HEAD unchanged. Do not force-push or use the old local publisher; no large-blob fetch until sufficient disk headroom above2GiB reserve.')
        except BaseException as error:
            receipt.update(error_type=type(error).__name__,error=str(error),next_step='Inspect preserved attempt and remote objects/ref; no automatic retry or overwrite.')
        finally:
            signal.setitimer(signal.ITIMER_REAL,0)
            elapsed = time.monotonic()-started
            receipt.update(finished_utc=bounded.now(),resources=dict(wall_seconds=elapsed,maximum_seconds=180,CPU_count=1,aggregate_RSS_limit_bytes=3*GIB))
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem,stage='compact_GUI_remote_publication',status=receipt['status'],seconds=elapsed,error=receipt.get('error'),finished_utc=receipt['finished_utc']))
            try:
                for p,value in ((root/'runtime/task1-budget.json',ledger),(output,receipt)):
                    size = len((json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode())
                    require(shutil.disk_usage(root).free >= 2*GIB+size,'Preserve2GiB reserve for final ledger/receipt bytes')
                    bounded.write(p,value)
            finally:
                for s,handler in old.items(): signal.signal(s,handler)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--final-validation',type=Path,default=ROOT/DIRECTORY/'final_validation.json')
    args = parser.parse_args(); result = publish(args.output.resolve(),args.final_validation.resolve())
    print(json.dumps({k:result.get(k) for k in ('status','published_commit','local_HEAD','remote_HEAD','error')}))
    if result['status'] != 'published_remote_only_commit': raise SystemExit(1)


if __name__ == '__main__': main()
