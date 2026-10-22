"""Synthetic policy tests; never touch the real budget or acquire its lock."""
import copy
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1]/'tools/task1_resource_policy.py'
spec = importlib.util.spec_from_file_location('resource_policy_under_test', MODULE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class ResourcePolicyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'runtime').mkdir()
        (self.root/'docs').mkdir()
        self.ledger = self.root/'runtime/task1-budget.json'
        self.lock = self.root/'.task1-execution.lock'
        self.lock.touch()
        self.approval = self.root/'docs/approval.json'
        self.amendment = self.root/'docs/amendment.json'
        self.old = dict(limit_seconds=6600, spent_seconds=5733.718985509018,
                        runs=[dict(id='existing', wall_seconds=42.125, status='failed'),
                              dict(id='preserve-unrelated-fields', nested={'evidence': [1, 2]})])
        self.authorization = dict(schema='task1-resource-policy-approval-v1', status='approved',
            previous_limit_seconds=6600, increment_seconds=7200, new_limit_seconds=13800,
            caps=copy.deepcopy(policy.CAPS), external_paid_resources=False,
            user_instruction=dict(id='local-test-record', id_kind='local_authorization_record',
                                  text='Explicit calculation-time extension authorization summary',
                                  source='current_user_thread'))
        self.write(self.ledger, self.old)
        self.write(self.approval, self.authorization)

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False)+'\n')

    def expand(self):
        return policy.expand_ledger(self.ledger, self.approval, self.amendment)

    def test_legacy_and_historical_receipts_remain_valid(self):
        self.assertEqual(policy.effective_limit(self.old), 6600)
        self.assertEqual(policy.policy_refs(self.old), {})
        self.assertAlmostEqual(policy.remaining_seconds(self.old), 866.281014490982)
        self.expand()
        self.assertEqual(policy.effective_limit(self.old), 6600)

    def test_expansion_preserves_spending_and_run_history(self):
        before = self.ledger.read_bytes()
        expanded = self.expand()
        self.assertEqual(expanded['spent_seconds'], self.old['spent_seconds'])
        self.assertEqual(expanded['runs'], self.old['runs'])
        self.assertEqual(policy.effective_limit(policy.load_ledger(self.ledger)), 13800)
        amendment = json.loads(self.amendment.read_text())
        self.assertEqual(amendment['previous_ledger_sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(len(policy.policy_refs(expanded)), 2)
        self.assertNotIn(str(self.ledger), policy.policy_refs(expanded))

    def test_future_debits_append_without_rewriting_baseline(self):
        ledger = self.expand()
        ledger['spent_seconds'] += 7
        ledger['runs'].append(dict(id='new-job', wall_seconds=7))
        self.assertEqual(policy.effective_limit(ledger), 13800)
        changed = copy.deepcopy(ledger)
        changed['runs'][0]['status'] = 'passed'
        with self.assertRaisesRegex(ValueError, 'prefix changed'):
            policy.effective_limit(changed)
        changed = copy.deepcopy(ledger)
        changed['spent_seconds'] = self.old['spent_seconds']-1
        with self.assertRaisesRegex(ValueError, 'reduce historical'):
            policy.effective_limit(changed)

    def test_expansion_only_once_and_no_amendment_overwrite(self):
        self.expand()
        before = self.ledger.read_bytes()
        with self.assertRaises(ValueError):
            self.expand()
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_missing_or_invalid_approval_rejects_before_ledger_mutation(self):
        for mutation in (lambda x: x.update(new_limit_seconds=13801),
                         lambda x: x.update(external_paid_resources=True),
                         lambda x: x['caps'].update(cpu=2),
                         lambda x: x['user_instruction'].update(source='inferred'),
                         lambda x: x['user_instruction'].update(text='')):
            with self.subTest(mutation=mutation):
                value = copy.deepcopy(self.authorization)
                mutation(value)
                self.write(self.approval, value)
                before = self.ledger.read_bytes()
                with self.assertRaises(ValueError):
                    self.expand()
                self.assertEqual(before, self.ledger.read_bytes())
                self.assertFalse(self.amendment.exists())

    def test_unsupported_limits_and_invalid_spending_rejected(self):
        for key, value in [('limit_seconds', 13800), ('limit_seconds', True),
                           ('limit_seconds', 6601), ('spent_seconds', -1),
                           ('spent_seconds', float('nan')), ('spent_seconds', True)]:
            ledger = copy.deepcopy(self.old)
            ledger[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                policy.effective_limit(ledger)
        overspent = copy.deepcopy(self.old)
        overspent['spent_seconds'] = 6601
        self.assertEqual(policy.remaining_seconds(overspent), -1)

    def test_approval_and_amendment_sha_drift_rejected(self):
        ledger = self.expand()
        original = self.approval.read_bytes()
        self.approval.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            policy.effective_limit(ledger)
        self.approval.write_bytes(original)
        self.amendment.write_bytes(self.amendment.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            policy.effective_limit(ledger)

    def test_wrong_global_lock_and_symlink_approval_rejected(self):
        wrong = self.root/'other.lock'
        wrong.touch()
        with self.assertRaisesRegex(ValueError, 'global execution lock'):
            policy.expand_ledger(self.ledger, self.approval, self.amendment, wrong)
        link = self.root/'docs/link.json'
        link.symlink_to(self.approval)
        with self.assertRaisesRegex(ValueError, 'canonical'):
            policy.expand_ledger(self.ledger, link, self.amendment)

    def test_missing_ledger_cannot_reset_budget(self):
        with self.assertRaises(ValueError):
            policy.load_ledger(self.root/'runtime/missing.json')

    def test_single_owned_lock_rejected_and_both_owned_locks_preserved(self):
        with self.lock.open('r+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, 'both execution lock'):
                self.expand()
            fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.expand()
            self.assertEqual(policy._owned_locks(self.lock), {'FLOCK', 'POSIX'})
            # A new process must still be excluded by BOTH namespaces afterwards.
            code = "import fcntl,sys; f=open(sys.argv[1],'r+'); failures=0\nfor lock in (fcntl.flock,fcntl.lockf):\n try: lock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)\n except BlockingIOError: failures+=1\nsys.exit(0 if failures==2 else 1)"
            result = subprocess.run([sys.executable, '-c', code, str(self.lock)], timeout=5)
            self.assertEqual(result.returncode, 0)

    def test_external_lock_in_either_namespace_blocks_mutation(self):
        for namespace in ('flock', 'lockf'):
            with self.subTest(namespace=namespace):
                code = "import fcntl,sys; f=open(sys.argv[1],'r+'); getattr(fcntl,sys.argv[2])(f,fcntl.LOCK_EX); print('locked',flush=True); sys.stdin.read()"
                process = subprocess.Popen([sys.executable, '-c', code, str(self.lock), namespace],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                try:
                    self.assertEqual(process.stdout.readline().strip(), 'locked')
                    with self.assertRaises(BlockingIOError):
                        self.expand()
                    self.assertFalse(self.amendment.exists())
                    self.assertEqual(policy.load_ledger(self.ledger), self.old)
                finally:
                    process.communicate('', timeout=5)

    def test_atomic_replace_failure_keeps_original_and_failure_evidence(self):
        before = self.ledger.read_bytes()
        with mock.patch.object(policy.os, 'replace', side_effect=OSError('synthetic failure')):
            with self.assertRaisesRegex(OSError, 'synthetic failure'):
                self.expand()
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertTrue(self.amendment.exists())
        self.assertEqual(len(list(self.ledger.parent.glob('*.partial'))), 1)


if __name__ == '__main__':
    unittest.main()
