"""Read-only, finite verification of an already-pushed GUI partial result."""
import hashlib, importlib.util, json, os, signal, subprocess, sys, threading, time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path('/workspace/ngg-tis-task1')
OLD = ROOT/'runtime/native-GUI-lite-r5-20261025-run'
OUT = ROOT/'runtime/gui5-readback-recovery-20261025-run'
TRANSPORT = Path('/dev/shm/task1-git-native-GUI-lite-r5-result-20261025')
PUB = Path('/dev/shm/task1-git-verified-20261025-r3/source/git_publish_verified.py')
OBSERVER = Path('/dev/shm/task1-floating-synthetic-owner-20261025/source/resource_scope.py')
CHECKPOINT = Path('/dev/shm/task1-verified-transport-retirement-20261025-seventh.py')
COMMIT = 'e16ec548ec8caa5f4557aa70965d26067b70aaf5'
PARENT = '23316b1781fc3f092a4091ab06e7b57a77b99075'
URL = 'https://github.com/yoodohyun-codex-cloud/ngg-tis-task1.git'
BRANCH = 'codex/task1-cloud-restart-20261020'
CAP = 900
sys.path[:0] = [str(ROOT/'tools'), str(OBSERVER.parent)]
import task1_bounded_continuation as b
import task1_execution_policy as ep
import task1_resource_policy as budget
import resource_scope

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''): h.update(chunk)
    return h.hexdigest()

def new(p, data):
    with Path(p).open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, allow_nan=False, indent=2)

def size(p):
    try:
        if p.is_file(): return p.stat().st_size
    except FileNotFoundError: return 0
    total = 0
    for item in p.rglob('*'):
        try:
            if item.is_file(): total += item.stat().st_size
        except FileNotFoundError: continue
    return total

def main():
    assert sha(PUB) == 'e29f03472c430598d9b7599eee28416b3453653b977a00c3d1999fa363f75f45'
    assert sha(OBSERVER) == '6c09a7cd06fed12a2e9950cc921242ef12c2a4ae999e9645ae7953d732d7873e'
    assert sha(CHECKPOINT) == '9267e662044297da1b92e4201339a930209f07a34270995b4f4724af9bc4dae5'
    spec = importlib.util.spec_from_file_location('checkpoint', CHECKPOINT)
    sampler = importlib.util.module_from_spec(spec); spec.loader.exec_module(sampler)
    with b.dual_lock(ROOT/'.task1-queue-owner.lock'), b.dual_lock(ROOT/'.task1-loop.lock'), b.dual_lock(ROOT/'.task1-execution.lock'):
        assert not OUT.exists(); OUT.mkdir(); (OUT/'tmp').mkdir()
        limits = ep.resolve_limits(); ep.configure_process(limits)
        assert limits['cpu_limit'] == 4 and limits['total_memory_bytes'] == 8000000000
        old = json.loads((OLD/'receipt.json').read_text())
        assert old['status'] == 'failed_preserved' and old['failed_phase'] == 'result-publication'
        assert not b.live(old['pid'], old['proc_start_ticks'])
        attempt = json.loads((TRANSPORT/'attempt-1.json').read_text())
        state = json.loads((TRANSPORT/'transport-state.json').read_text())
        plan = json.loads((OLD/'result-plan.json').read_text())
        assert attempt['push_confirmed'] is True and attempt['recorded_commit'] == COMMIT
        assert state['commit'] == COMMIT and state['push_confirmed'] is True and plan['expected_parent'] == PARENT
        assert not (OLD/'result-publication/result-publication.json').exists()
        pid = os.getpid(); ticks = b.ticks(pid); started = time.monotonic()
        owned = {pid: ticks}; remembered = {}; cache = {}; mutex = threading.RLock(); stop = threading.Event()
        record = dict(schema='task1-GUI5-readback-recovery-v1', status='failed_preserved', pid=pid,
                      proc_start_ticks=ticks, source_commit=PARENT, result_commit=COMMIT,
                      original_GUI_owner_status=old['status'], original_GUI_owner_receipt_SHA256=sha(OLD/'receipt.json'),
                      new_PDE=0, new_native_array_decodes=0, GUI_generated=False,
                      original_GUI_worker_failure_retained=True, old_owner_rewritten=False,
                      Windows_saved_verified=False, branch_mutations=0, cap_seconds=CAP)
        new(OUT/'preregistration.json', dict(schema='task1-GUI5-readback-recovery-plan-v1', fixed_commit=COMMIT,
            expected_parent=PARENT, plan_SHA256=sha(OLD/'result-plan.json'), original_failed_owner=old,
            original_failed_publisher=attempt, verifier_source_UTF8=Path(__file__).read_text(),
            verifier_source_SHA256=sha(__file__), new_PDE=0, branch_mutations=0))
        def measure():
            live = b.owned_descendants(pid, ticks, dict(owned)); owned.update(live)
            obs = resource_scope.observe(live, b.ticks, remembered); remembered.update(obs['members'])
            return obs, dict(total_bytes=sum(size(p) for base in ('/dev/shm','/tmp') for p in Path(base).glob('task1-*')))
        def guard(force=False):
            with mutex:
                # The audited sampler's600s finite accounting deadline is stricter than the outer900s watchdog.
                return sampler.resource_checkpoint(cache, time.monotonic, started, measure, 8000000000, force)
        def interrupted(*_): raise TimeoutError('Finite readback watchdog or actual resource guard')
        def monitor():
            while not stop.wait(.25):
                try: guard()
                except BaseException as error:
                    record['monitor_error'] = str(error); os.kill(pid, signal.SIGTERM); return
        handlers = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
        for s in handlers: signal.signal(s, interrupted)
        signal.alarm(CAP); thread = threading.Thread(target=monitor, daemon=True); thread.start()
        gitdir = OUT/'verify.git'; env = dict(os.environ, TMPDIR=str(OUT/'tmp'), GIT_OPTIONAL_LOCKS='0')
        def git(args, body=None, optional=False):
            guard()
            command = ['git','-c','credential.helper=!gh auth git-credential','-c','gc.auto=0','-c','pack.threads=4','--git-dir='+str(gitdir)] + args
            result = subprocess.run(command, input=body, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=env, timeout=min(180, max(.01, 590-(time.monotonic()-started))))
            if result.returncode and not optional: raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
            return result
        try:
            guard(True)
            subprocess.run(['git','init','--bare',str(gitdir)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
            git(['remote','add','origin',URL]); git(['fetch','--no-tags','--depth=1','--filter=blob:none','origin',COMMIT])
            assert not (gitdir/'objects/info/alternates').exists()
            headers = git(['cat-file','-p',COMMIT]).stdout.split(b'\n\n',1)[0].decode().splitlines()
            assert [s[7:] for s in headers if s.startswith('parent ')] == [PARENT]
            tree = git(['rev-parse',COMMIT+'^{tree}']).stdout.decode().strip(); assert tree == state['tree']
            entries = {}
            for row in git(['ls-tree','-r','-z',COMMIT]).stdout.split(b'\0'):
                if row:
                    info, name = row.split(b'\t',1); entries[name.decode()] = tuple(info.decode().split())
            records = state['records']; assert {r['target'] for r in records} == set(plan['files'])
            for row in records: assert entries[row['target']] == ('100644','blob',row['Git_blob_SHA'])
            # One remote request for all explicitly wanted blobs avoids repeated lazy-fetch latency.
            wanted = '\n'.join(sorted({r['Git_blob_SHA'] for r in records}))+'\n'
            prefetched = git(['fetch','--no-tags','--stdin','origin'], wanted.encode(), optional=True)
            new(OUT/'batch-prefetch.json', dict(returncode=prefetched.returncode, blobs=len(wanted.splitlines()),
                fallback='Normal remote promisor lazy fetch if batch wants are unsupported'))
            proof = {}
            for index, row in enumerate(records):
                raw = git(['cat-file','blob',row['Git_blob_SHA']]).stdout; expected = plan['files'][row['target']]
                assert len(raw) == row['bytes'] == expected['bytes']
                assert hashlib.sha256(raw).hexdigest() == row['SHA256'] == expected['SHA256']
                proof[row['target']] = dict(SHA256=row['SHA256'], bytes=row['bytes'], Git_blob_SHA=row['Git_blob_SHA'],
                    readback_passed=True, proof_kind='fresh_separate_remote_Git_readback_recovery_full_blob')
                del raw
            observed = git(['ls-remote','origin','refs/heads/'+BRANCH]).stdout.decode().split()[0]
            if observed != COMMIT:
                git(['fetch','--no-tags','--depth=64','--filter=blob:none','origin','refs/heads/'+BRANCH])
                assert git(['merge-base','--is-ancestor',COMMIT,observed], optional=True).returncode == 0
            result = dict(status='published_readback_verified', commit=COMMIT, files=proof,
                expected_parent=PARENT, tree=tree, remote_branch_head_verified=observed, new_PDE=0,
                transport='supported_Git_HTTPS_readback_only_recovery', verification_source_SHA256=sha(__file__),
                original_publisher_attempt_preserved=True, no_new_commit_or_push=True)
            new(OLD/'result-publication/result-publication.json', result)
            new(OUT/'result-publication.json', result)
            guard(True); record.update(status='GUI5_partial_result_readback_recovered', files_verified=len(proof),
                result_publication_receipt_SHA256=sha(OLD/'result-publication/result-publication.json'))
        except BaseException as error:
            record.update(error_type=type(error).__name__, error=str(error)); raise
        finally:
            signal.alarm(0); stop.set(); thread.join(timeout=2)
            for child, tick in b.owned_descendants(pid,ticks,dict(owned)).items():
                if child != pid and b.live(child,tick):
                    try: os.kill(child,signal.SIGKILL)
                    except ProcessLookupError: pass
            elapsed = time.monotonic()-started; ledger = budget.load_ledger(); ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=OUT.name, stage='read_only_partial_GUI_result_recovery', seconds=elapsed, status=record['status'], new_PDE=0))
            tmp = ROOT/'runtime'/('budget-GUI5-readback-'+str(pid)+'.tmp'); new(tmp,ledger); os.replace(tmp,ROOT/'runtime/task1-budget.json')
            record.update(elapsed_seconds=elapsed, finished_utc=b.now())
            new(OUT/'receipt.json',record)
            for s,h in handlers.items(): signal.signal(s,h)
            print(json.dumps({k:v for k,v in record.items() if k not in ('limits',)}))

if __name__ == '__main__': main()
