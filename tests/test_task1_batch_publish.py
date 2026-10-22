"""Publication fixtures mock all git/GitHub calls and use a temporary ledger."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_batch_publish as pub
import task1_bounded_continuation as bounded


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for d in ('docs', 'runtime'): (self.root/d).mkdir()
        self.source = self.root/'docs/input.json'; self.source.write_text('{}')
        self.report = self.root/'docs/result.json'
        bounded.write(self.report, dict(status='calculated_unadopted', inputs_unchanged=True,
            inputs_sha256={str(self.source): bounded.sha(self.source)}))
        self.body = self.root/'docs/public-body.md'; self.body.write_text('Completed finite comparison; convergence remains held.\n')
        self.spec = dict(schema='task1-batch-publication-spec-v1', repository=pub.REPOSITORY,
            branch=pub.BRANCH, comment_id=pub.COMMENT, parent_admission_commit='a'*40,
            files=[dict(path=str(self.report))], input_sha256={str(self.source): bounded.sha(self.source)},
            body_file=str(self.body), body_sha256=bounded.sha(self.body),
            required_completed_artifacts=[dict(path=str(self.report), statuses=['calculated_unadopted'], source_hashes_field='inputs_sha256')])
        self.specpath = self.root/'docs/spec.json'; bounded.write(self.specpath, self.spec)
        self.receipt = self.root/'docs/publication.json'
        self.ledger = self.root/'runtime/task1-budget.json'
        bounded.write(self.ledger, dict(limit_seconds=13800, spent_seconds=100., runs=[dict(stage='prior', seconds=100.)]))
        self.calls = []; self.staged = False; self.committed = False; self.fail = None

    def runner(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[0] == 'git':
            args = argv[3:]
            if args[:2] == ['branch', '--show-current']: return pub.BRANCH
            if args[:3] == ['remote', 'get-url', 'origin']: return 'https://github.com/'+pub.REPOSITORY+'.git'
            if args[:3] == ['diff', '--cached', '--name-only']:
                return 'docs/result.json\0' if self.staged else ''
            if args[:2] == ['rev-parse', 'HEAD']: return ('b' if self.committed else 'a')*40
            if args[:2] == ['diff', '--name-only']: return 'docs/result.json\n' if self.committed else ''
            if args[0] == 'add': self.staged = True
            if args[0] == 'commit': self.committed = True
            if args[0] == 'push' and self.fail == 'push': raise RuntimeError('synthetic push failure')
            return ''
        if argv[:4] == ['gh', 'api', '-X', 'PATCH']:
            if self.fail == 'patch': raise RuntimeError('synthetic comment failure')
            return json.dumps(dict(id=pub.COMMENT, html_url='https://github.com/'+pub.REPOSITORY+'/pull/2#issuecomment-'+str(pub.COMMENT)))
        return json.dumps(dict(id=pub.COMMENT, user=dict(login='yoodohyun-codex-cloud'), issue_url='https://api.github.com/repos/'+pub.REPOSITORY+'/issues/2'))

    def execute(self):
        bounded.write(self.specpath, self.spec)
        with mock.patch.object(pub.policy, 'load_ledger', side_effect=lambda p: bounded.read(p)), \
             mock.patch.object(pub.policy, 'effective_limit', return_value=13800), \
             mock.patch.object(pub.os, 'sched_setaffinity'):
            return pub.publish(self.specpath, self.receipt, root=self.root, runner=self.runner)

    def test_success_stages_only_whitelist_pushes_fixed_branch_patches_fixed_comment(self):
        result = self.execute()
        self.assertEqual(result['status'], 'published_completed_batch')
        self.assertTrue(result['push_succeeded']); self.assertTrue(result['comment_updated'])
        add = next(a for a in self.calls if a[0] == 'git' and a[3] == 'add')
        self.assertEqual(add[4:], ['--', 'docs/result.json'])
        push = next(a for a in self.calls if a[0] == 'git' and a[3] == 'push')
        self.assertEqual(push[-1], 'b'*40+':refs/heads/'+pub.BRANCH)
        self.assertFalse(any('--force' in a or 'main' in a for a in self.calls))
        ledger = bounded.read(self.ledger)
        self.assertEqual(ledger['runs'][0], dict(stage='prior', seconds=100.))
        self.assertGreater(ledger['spent_seconds'], 100.)
        self.assertEqual(ledger['runs'][-1]['stage'], 'completed_batch_publication')

    def test_successful_push_failed_comment_is_not_labeled_published(self):
        self.fail = 'patch'
        with self.assertRaisesRegex(RuntimeError, 'comment failure'): self.execute()
        r = bounded.read(self.receipt)
        self.assertTrue(r['push_succeeded']); self.assertFalse(r['comment_updated'])
        self.assertEqual(r['status'], 'failed_preserved')
        self.assertIn('gh api -X PATCH', r['next_command'])
        self.assertEqual(sum(a[0] == 'git' and a[3] == 'push' for a in self.calls), 1)

    def test_failed_push_preserves_local_commit_without_posting_comment(self):
        self.fail = 'push'
        with self.assertRaisesRegex(RuntimeError, 'push failure'): self.execute()
        r = bounded.read(self.receipt)
        self.assertTrue(r['commit_created']); self.assertFalse(r['push_succeeded'])
        self.assertFalse(any(a[0] == 'gh' for a in self.calls))
        self.assertIn('git push origin', r['next_command'])

    def test_no_retry_or_overwrite_after_attempt(self):
        self.execute()
        with self.assertRaisesRegex(ValueError, 'New publication receipt'): self.execute()

    def test_rejects_nonapproved_repo_branch_comment_and_private_paths(self):
        for key, value in [('repository', 'other/repo'), ('branch', 'main'), ('comment_id', 1)]:
            bad = copy.deepcopy(self.spec); bad[key] = value
            with self.assertRaisesRegex(ValueError, 'Exact approved'): pub.verify_spec(bad, self.root)
        bad = copy.deepcopy(self.spec); bad['files'] = [dict(path=str(self.ledger))]
        with self.assertRaisesRegex(ValueError, 'Approved docs'): pub.verify_spec(bad, self.root)
        p = self.root/'docs/private-chat-log.json'; p.write_text('{}')
        bad['files'] = [dict(path=str(p))]
        with self.assertRaisesRegex(ValueError, 'Private or credential'): pub.verify_spec(bad, self.root)

    def test_secret_symlink_missing_proof_and_drift_are_blockers(self):
        p = self.root/'docs/link.json'; p.symlink_to(self.report)
        bad = copy.deepcopy(self.spec); bad['files'] = [dict(path=str(p))]
        with self.assertRaisesRegex(ValueError, 'Canonical'): pub.verify_spec(bad, self.root)
        self.report.write_text('github_'+'pat_'+'a'*30)
        with self.assertRaisesRegex(ValueError, 'Secret signature'): pub.verify_spec(self.spec, self.root)
        self.setUp_report()
        bad = copy.deepcopy(self.spec); del bad['required_completed_artifacts'][0]['source_hashes_field']
        with self.assertRaisesRegex(ValueError, 'requires hash'): pub.verify_spec(bad, self.root)
        self.source.write_text('{"drift":true}')
        with self.assertRaisesRegex(ValueError, 'input drift'): pub.verify_spec(self.spec, self.root)

    def setUp_report(self):
        bounded.write(self.report, dict(status='calculated_unadopted', inputs_unchanged=True, inputs_sha256={str(self.source): bounded.sha(self.source)}))

    def test_incomplete_or_unverified_report_is_not_published(self):
        obj = bounded.read(self.report); obj['status'] = 'running'; bounded.write(self.report, obj)
        with self.assertRaisesRegex(ValueError, 'not complete'): self.execute()
        self.assertFalse(self.calls)

    def test_unrelated_staged_changes_block_before_git_add(self):
        original = self.runner
        def runner(argv, **kw):
            if argv[0] == 'git' and argv[3:6] == ['diff', '--cached', '--name-only']: return 'tools/unrelated.py\0'
            return original(argv, **kw)
        self.runner = runner
        with self.assertRaisesRegex(ValueError, 'Existing staged changes'): self.execute()
        self.assertFalse(any(a[0] == 'git' and a[3] == 'add' for a in self.calls))


if __name__ == '__main__': unittest.main()
