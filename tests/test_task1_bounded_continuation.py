"""Synthetic coordinator failures and accounting; no research worker/data touched."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import task1_bounded_continuation as queue


CHILD = '''import json,pathlib,sys,time,subprocess
args=sys.argv[1:]
kind=args[args.index('--case')+1]
out=pathlib.Path(args[args.index('--output')+1])
if kind=='timeout':
 p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True)
 out.with_suffix('.child-pid').write_text(str(p.pid))
 time.sleep(60)
if kind=='failure': sys.exit(7)
if kind=='badstatus': status='unexpected'
else: status='computed_spatial_and_skinJ_audit'
ledger=pathlib.Path('runtime/task1-budget.json')
x=json.loads(ledger.read_text())
x['spent_seconds']+=0.005
x['runs'].append({'stage':'synthetic_child','seconds':0.005})
ledger.write_text(json.dumps(x))
out.write_text(json.dumps({'status':status}))
'''


class QueueFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for part in ('tools', 'runtime', 'docs', 'run'):
            (self.root/part).mkdir()
        self.tool = self.root/'tools/task1_spatial_audit.py'
        self.tool.write_text(CHILD)
        self.baseline = self.root/'baseline.json'
        self.baseline.write_text('{}')
        self.ledger = self.root/'runtime/task1-budget.json'
        self.initial = dict(limit_seconds=6600, spent_seconds=100., runs=[dict(stage='past', seconds=100.)])
        queue.write(self.ledger, self.initial)
        self.output = self.root/'docs/queue-test'

    def stage(self, kind='good', seconds=2.):
        result = self.root/'run'/('result-'+kind+'.json')
        return dict(id=kind, argv=[str(Path(sys.executable).resolve()), str(self.tool),
            '--run', str(self.root/'run'), '--case', kind, '--baseline-summary', str(self.baseline), '--output', str(result)],
            max_seconds=seconds, must_not_exist=str(result),
            completion=dict(path=str(result), statuses=['computed_spatial_and_skinJ_audit']))

    def plan(self, stages=None):
        stages = stages or [self.stage()]
        value = dict(schema=queue.SCHEMA, status='preregistered_not_executed', output_directory=str(self.output),
            max_total_seconds=sum(s['max_seconds'] for s in stages)+60,
            stages=stages, input_sha256={str(self.tool): queue.sha(self.tool), str(self.baseline): queue.sha(self.baseline)},
            resource_policy_limit_seconds=6600,
            caps=dict(CPU_count=1, concurrent_children=1, aggregate_RSS_bytes=3*queue.GIB, minimum_free_disk_bytes=2*queue.GIB))
        path = self.root/'docs/plan.json'
        queue.write(path, value)
        return path

    def run_queue(self, path):
        # Fixture must not change the test runner's CPU affinity.
        with mock.patch.object(queue.os, 'sched_setaffinity'):
            return queue.Coordinator(path, root=self.root).execute()

    def test_exact_argv_rejects_shell_python_switch_and_unknown_tool(self):
        self.assertEqual(queue.validate_stage(self.stage(), self.root), self.tool)
        for change in ({'argv': ['bash', '-c', 'true']},
                       {'argv': [str(Path(sys.executable).resolve()), '-c', 'pass', '--output', str(self.root/'a')]},
                       {'argv': self.stage()['argv']+['--install', 'anything']}):
            bad = self.stage(); bad.update(change)
            with self.assertRaises((ValueError, TypeError)):
                queue.validate_stage(bad, self.root)

    def test_lower_carrier_allows_only_exact_frozen_execute_output(self):
        tool = self.root/'tools/task1_lower_carrier.py'
        run = self.root/'run/lower-carrier'
        stage = dict(id='lower-carrier', argv=[str(Path(sys.executable).resolve()), str(tool),
            '--execute', '--output', str(run)], max_seconds=600,
            must_not_exist=str(run/'execution-attempt.json'),
            completion=dict(path=str(run/'summary.json'), statuses=['complete']))
        self.assertEqual(queue.validate_stage(stage, self.root), tool)
        for flags in (
                ['--prepare', '--output', str(run)],
                ['--output', str(run)],
                ['--execute', '--execute', '--output', str(run)],
                ['--output', str(run), '--execute'],
                ['--execute', '--output', str(run), '--case', 'extra'],
                ['--execute', '--output', '/outside-repository']):
            bad = copy.deepcopy(stage); bad['argv'] = stage['argv'][:2]+flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                queue.validate_stage(bad, self.root)
        bad = copy.deepcopy(stage); bad['max_seconds'] = 601
        with self.assertRaisesRegex(ValueError, 'Finite stage cap'):
            queue.validate_stage(bad, self.root)

    def test_recovery_allows_only_exact_frozen_execute_output(self):
        tool = self.root/'tools/task1_lower_carrier_recovery.py'
        run = self.root/'run/lower-carrier-recovery'
        stage = dict(id='recovery', argv=[str(Path(sys.executable).resolve()), str(tool),
            '--execute', '--output', str(run)], max_seconds=600,
            must_not_exist=str(run/'execution-attempt.json'),
            completion=dict(path=str(run/'summary.json'), statuses=['calculated_unadopted']))
        self.assertEqual(queue.validate_stage(stage, self.root), tool)
        for flags in (['--prepare', '--output', str(run)], ['--output', str(run)],
                      ['--execute', '--execute', '--output', str(run)],
                      ['--output', str(run), '--execute'],
                      ['--execute', '--output', str(run), '--case', 'extra'],
                      ['--execute', '--output', '/outside-repository']):
            bad = copy.deepcopy(stage); bad['argv'] = stage['argv'][:2]+flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                queue.validate_stage(bad, self.root)

    def test_mid_high_allows_only_exact_frozen_execute_output(self):
        tool = self.root/'tools/task1_mid_high_carrier.py'
        run = self.root/'run/mid-high-carrier'
        stage = dict(id='mid-high', argv=[str(Path(sys.executable).resolve()), str(tool),
            '--execute', '--output', str(run)], max_seconds=600,
            must_not_exist=str(run/'execution-attempt.json'),
            completion=dict(path=str(run/'summary.json'), statuses=['calculated_unadopted']))
        self.assertEqual(queue.validate_stage(stage, self.root), tool)
        for flags in (['--prepare', '--output', str(run)], ['--output', str(run)],
                      ['--execute', '--execute', '--output', str(run)],
                      ['--output', str(run), '--execute'],
                      ['--execute', '--output', str(run), '--case', 'extra'],
                      ['--execute', '--output', '/outside-repository']):
            bad = copy.deepcopy(stage); bad['argv'] = stage['argv'][:2]+flags
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                queue.validate_stage(bad, self.root)

    def test_long_grouped_stage_preserves_six_hundred_seconds_per_case(self):
        run = self.root/'run/grouped-fine'; run.mkdir()
        tool = self.root/'tools/task1_cloud_batch.py'
        cases = [dict(n_pads=n, n_outputs=2, channels=2, java_class='GroupedPadBasis',
            postprocessor='grouped', h_xy_mm=.625, sc_cells=2, bulk_counts=[14,14,40]) for n in (4,8,12,16)]
        pre = dict(schema='task1-cloud-finite-v1', status='prepared', batch_kind='grouped_fine_physical_pads',
                   limits=dict(per_condition_seconds=600), cases=cases)
        stage = dict(id='four-grouped-cases', argv=[str(Path(sys.executable).resolve()), str(tool),
            '--execute', '--output', str(run)], max_seconds=2400,
            must_not_exist=str(run/'execution-attempt.json'),
            completion=dict(path=str(run/'summary.json'), statuses=['complete']))
        queue.write(run/'preregistration.json', pre)
        self.assertEqual(queue.validate_stage(stage, self.root), tool)
        for changed in (dict(pre, cases=cases[:3]), dict(pre, batch_kind='other'),
                        dict(pre, limits=dict(per_condition_seconds=601)),
                        dict(pre, cases=[dict(cases[0], n_outputs=4), *cases[1:]])):
            queue.write(run/'preregistration.json', changed)
            with self.assertRaises(ValueError): queue.validate_stage(stage, self.root)
        queue.write(run/'preregistration.json', pre)
        bad = dict(stage, max_seconds=2401)
        with self.assertRaises(ValueError): queue.validate_stage(bad, self.root)
        bad = copy.deepcopy(stage); bad['completion']['path']=str(self.root/'run/fake.json')
        with self.assertRaises(ValueError): queue.validate_stage(bad, self.root)
        bad = self.stage(seconds=601)
        with self.assertRaises(ValueError): queue.validate_stage(bad, self.root)

    def test_fine_recovery_requires_exact_feedback_and_output(self):
        tool = self.root/'tools/task1_grouped_fine_volume_recovery_registration.py'
        output = self.root/'docs/volume-plan.json'
        flags = ['--feedback', str(self.baseline), '--output', str(output)]
        stage = dict(id='fine-recovery', argv=[str(Path(sys.executable).resolve()), str(tool), *flags],
            max_seconds=120, must_not_exist=str(output),
            completion=dict(path=str(output), statuses=['preregistered_not_executed']))
        self.assertEqual(queue.validate_stage(stage, self.root), tool)
        for bad_flags in (flags[2:], flags+flags[:2], flags+['--execute'],
                          ['--feedback','/outside-repository','--output',str(output)]):
            with self.subTest(flags=bad_flags), self.assertRaises(ValueError):
                queue.validate_stage(dict(stage,argv=stage['argv'][:2]+bad_flags),self.root)

    def test_adjacent_metadata_requires_feedback_decision_and_output(self):
        tool=self.root/'tools/task1_adjacent_source_volume_registration.py'
        output=self.root/'docs/adjacent-volume-plan.json'
        flags=['--feedback',str(self.baseline),'--decision',str(self.baseline),'--output',str(output)]
        stage=dict(id='adjacent-metadata',argv=[str(Path(sys.executable).resolve()),str(tool),*flags],
            max_seconds=120,must_not_exist=str(output),completion=dict(path=str(output),statuses=['preregistered_not_executed']))
        self.assertEqual(queue.validate_stage(stage,self.root),tool)
        for bad in (flags[2:],flags[:2]+flags[4:],flags+flags[:2],flags+['--execute']):
            with self.subTest(flags=bad),self.assertRaises(ValueError):
                queue.validate_stage(dict(stage,argv=stage['argv'][:2]+bad),self.root)

    def test_one_return_rotation_volume_requires_all_context_flags(self):
        tool=self.root/'tools/task1_one_return_rotation_volume_registration.py'
        output=self.root/'docs/rotation-volume-plan.json'
        flags=['--feedback',str(self.baseline),'--decision',str(self.baseline),'--output',str(output)]
        stage=dict(id='rotation-metadata',argv=[str(Path(sys.executable).resolve()),str(tool),*flags],
            max_seconds=60,must_not_exist=str(output),completion=dict(path=str(output),statuses=['preregistered_not_executed']))
        self.assertEqual(queue.validate_stage(stage,self.root),tool)
        for bad in (flags[2:],flags[:2]+flags[4:],flags+flags[:2],flags+['--execute']):
            with self.subTest(flags=bad),self.assertRaises(ValueError):
                queue.validate_stage(dict(stage,argv=stage['argv'][:2]+bad),self.root)

    def test_coherent_drive_allows_frozen_plan_and_output_only(self):
        tool=self.root/'tools/task1_coherent_drive_scout.py'
        output=self.root/'docs/coherent-result'
        flags=['--preregistration',str(self.baseline),'--output',str(output)]
        stage=dict(id='coherent-drive',argv=[str(Path(sys.executable).resolve()),str(tool),*flags],
            max_seconds=600,must_not_exist=str(output/'heartbeat.json'),
            completion=dict(path=str(output/'summary.json'),statuses=['calculated_unadopted']))
        self.assertEqual(queue.validate_stage(stage,self.root),tool)
        for bad in (flags[2:],flags+flags[:2],flags+['--prepare',str(self.baseline)]):
            with self.subTest(flags=bad),self.assertRaises(ValueError):
                queue.validate_stage(dict(stage,argv=stage['argv'][:2]+bad),self.root)
        with self.assertRaises(ValueError):queue.validate_stage(dict(stage,max_seconds=601),self.root)

    def test_return_current_and_single_pair_require_exact_frozen_plan(self):
        for name in ('task1_return_current_drive_scout.py', 'task1_coherent_single_pair.py',
                     'task1_return_rotation_operator_audit.py', 'task1_rotation_drive_ratio_scout.py'):
            tool = self.root/'tools'/name
            output = self.root/'docs'/name.removesuffix('.py')
            flags = ['--preregistration', str(self.baseline), '--output', str(output)]
            stage = dict(id=name.removesuffix('.py'), argv=[str(Path(sys.executable).resolve()), str(tool), *flags],
                max_seconds=120, must_not_exist=str(output/'heartbeat.json'),
                completion=dict(path=str(output/'summary.json'), statuses=['calculated_unadopted']))
            self.assertEqual(queue.validate_stage(stage, self.root), tool)
            for bad in (flags[2:], flags+flags[:2], flags+['--prepare', str(self.baseline)],
                        ['--preregistration', '/outside-repository', '--output', str(output)]):
                with self.subTest(tool=name, flags=bad), self.assertRaises(ValueError):
                    queue.validate_stage(dict(stage, argv=stage['argv'][:2]+bad), self.root)
            with self.assertRaises(ValueError):
                queue.validate_stage(dict(stage, max_seconds=601), self.root)

    def test_weak_coherent_drive_preserves_same_exact_execution_flags(self):
        tool=self.root/'tools/task1_coherent_drive_weak_scout.py'
        output=self.root/'docs/weak-coherent-result'
        flags=['--preregistration',str(self.baseline),'--output',str(output)]
        stage=dict(id='weak-coherent-drive',argv=[str(Path(sys.executable).resolve()),str(tool),*flags],
            max_seconds=600,must_not_exist=str(output/'heartbeat.json'),
            completion=dict(path=str(output/'summary.json'),statuses=['calculated_unadopted']))
        self.assertEqual(queue.validate_stage(stage,self.root),tool)
        for bad in (flags[2:],flags+flags[:2],flags+['--prepare',str(self.baseline)]):
            with self.subTest(flags=bad),self.assertRaises(ValueError):
                queue.validate_stage(dict(stage,argv=stage['argv'][:2]+bad),self.root)
        with self.assertRaises(ValueError):queue.validate_stage(dict(stage,max_seconds=601),self.root)

    def test_success_keeps_history_and_does_not_double_charge_child_debit(self):
        result = self.run_queue(self.plan())
        self.assertEqual(result['status'], 'completed_preregistered_queue')
        ledger = queue.read(self.ledger)
        self.assertEqual(ledger['runs'][0], self.initial['runs'][0])
        self.assertEqual(ledger['limit_seconds'], 6600)
        accounting = result['stages'][0]['accounting']
        self.assertAlmostEqual(accounting['child_ledger_delta_seconds'], .005)
        self.assertAlmostEqual(accounting['excluded_already_recorded_seconds'], .005)
        self.assertGreater(ledger['spent_seconds'], 100.)
        self.assertLess(ledger['spent_seconds']-100., result['elapsed_seconds']+.02)
        self.assertTrue((self.output/'summary.json').is_file())

    def test_nonzero_child_exit_records_failure_and_unrecorded_wall(self):
        with self.assertRaisesRegex(ValueError, 'Child exit failure: 7'):
            self.run_queue(self.plan([self.stage('failure')]))
        result = queue.read(self.output/'summary.json')
        self.assertEqual(result['status'], 'failed_preserved')
        self.assertIn('Child exit failure', result['stop_reason'])
        self.assertGreater(result['stages'][0]['accounting']['unrecorded_child_wall_seconds'], 0.)
        self.assertGreater(queue.read(self.ledger)['spent_seconds'], 100.)

    def test_wrong_terminal_status_stops_before_next_stage(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected child terminal status'):
            self.run_queue(self.plan([self.stage('badstatus'), self.stage('good')]))
        self.assertFalse(Path(self.stage('good')['completion']['path']).exists())
        self.assertEqual(len(queue.read(self.output/'summary.json')['stages']), 1)

    def test_timeout_terminates_owned_group_and_preserves_evidence(self):
        path = self.plan([self.stage('timeout', .15)])
        with self.assertRaisesRegex(ValueError, 'Finite stage deadline exceeded'):
            self.run_queue(path)
        pid = int(Path(self.stage('timeout')['completion']['path']).with_suffix('.child-pid').read_text())
        try:
            state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
            self.assertEqual(state, 'Z')
        except FileNotFoundError:
            pass
        self.assertEqual(queue.read(self.output/'summary.json')['status'], 'failed_preserved')
        self.assertTrue((self.output/'timeout.log').exists())

    def test_attempted_queue_and_child_outputs_never_retried(self):
        path = self.plan()
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'attempted queue'):
            self.run_queue(path)
        self.output.rmdir()
        Path(self.stage()['must_not_exist']).write_text('old evidence')
        with self.assertRaisesRegex(ValueError, 'Prior child attempt'):
            self.run_queue(path)
        self.assertEqual(Path(self.stage()['must_not_exist']).read_text(), 'old evidence')

    def test_plan_or_input_mutation_rejected_before_child(self):
        path = self.plan()
        owner = queue.Coordinator(path, root=self.root)
        self.tool.write_text(CHILD+'\n# drift\n')
        with self.assertRaisesRegex(ValueError, 'Pinned queue source changed'):
            with mock.patch.object(queue.os, 'sched_setaffinity'):
                owner.execute()
        self.assertFalse(Path(self.stage()['completion']['path']).exists())

    def test_duplicate_coordinator_lock_refuses_without_output_or_ledger_reset(self):
        path = self.plan()
        with queue.dual_lock(self.root/'.task1-loop.lock'):
            with self.assertRaises(BlockingIOError):
                self.run_queue(path)
        self.assertFalse(self.output.exists())
        self.assertEqual(queue.read(self.ledger), self.initial)

    def test_missing_or_exhausted_ledger_never_resets(self):
        path = self.plan()
        self.ledger.unlink()
        with self.assertRaisesRegex(ValueError, 'Regular policy file required'):
            queue.Coordinator(path, root=self.root)
        self.assertFalse(self.ledger.exists())
        queue.write(self.ledger, dict(self.initial, spent_seconds=6600))
        with self.assertRaisesRegex(ValueError, 'reservation exceeds'):
            self.run_queue(path)
        self.assertEqual(queue.read(self.ledger)['spent_seconds'], 6600)

    def test_append_only_reconciliation_refuses_changed_past_or_live_group(self):
        path = self.plan(); owner = queue.Coordinator(path, root=self.root)
        owner.current = mock.Mock(pid=999999999)
        owner.current.poll.return_value = 0
        bad = copy.deepcopy(self.initial); bad['runs'][0]['stage'] = 'rewritten'
        queue.write(self.ledger, bad)
        with self.assertRaisesRegex(ValueError, 'append-only'):
            owner.reconcile_child(self.initial, .1)

    def test_changed_total_caps_or_mutable_ledger_pin_rejected(self):
        path = self.plan(); plan = queue.read(path)
        plan['caps']['concurrent_children'] = 2
        queue.write(path, plan)
        with self.assertRaisesRegex(ValueError, 'resource caps'):
            queue.verify_plan(path, root=self.root)
        plan['caps']['concurrent_children'] = 1
        plan['input_sha256'][str(self.ledger)] = queue.sha(self.ledger)
        queue.write(path, plan)
        with self.assertRaisesRegex(ValueError, 'Mutable ledger'):
            queue.verify_plan(path, root=self.root)

    def test_controlled_signal_stops_owned_child_and_restores_handler(self):
        path = self.plan([self.stage('timeout', 2.)])
        original = signal.getsignal(signal.SIGTERM)
        timer = threading.Timer(.12, lambda: os.kill(os.getpid(), signal.SIGTERM))
        timer.start()
        try:
            with self.assertRaisesRegex(InterruptedError, 'Controlled coordinator signal'):
                self.run_queue(path)
        finally:
            timer.cancel(); timer.join()
        self.assertEqual(signal.getsignal(signal.SIGTERM), original)
        result = queue.read(self.output/'summary.json')
        self.assertIsNone(result['current_child'])
        self.assertEqual(result['status'], 'failed_preserved')

    def test_ten_stage_bound_accepts_ten_rejects_eleven_without_relaxing_caps(self):
        stages = []
        for i in range(10):
            stage = self.stage('case'+str(i)); stages.append(stage)
        path = self.plan(stages)
        self.assertEqual(len(queue.verify_plan(path, root=self.root)['stages']), 10)
        obj = queue.read(path); obj['stages'].append(self.stage('case10'))
        queue.write(path, obj)
        with self.assertRaisesRegex(ValueError, 'Distinct bounded stages'):
            queue.verify_plan(path, root=self.root)
        self.assertEqual(obj['caps']['concurrent_children'], 1)
        self.assertEqual(obj['caps']['aggregate_RSS_bytes'], 3*queue.GIB)

    def test_zombie_or_reused_identity_is_not_a_live_worker(self):
        row = ['0']*20; row[0] = 'Z'; row[19] = '12345'
        with mock.patch.object(queue.Path, 'read_text', return_value='42 (worker) '+' '.join(row)):
            self.assertFalse(queue.live(42, 12345))
        row[0] = 'R'
        with mock.patch.object(queue.Path, 'read_text', return_value='42 (worker) '+' '.join(row)):
            self.assertTrue(queue.live(42, 12345))
            self.assertFalse(queue.live(42, 12346))
        self.assertFalse(queue.live(999999999, 12345))


if __name__ == '__main__':
    unittest.main()
