"""Finite-loop orchestration fixtures only; no actual prepare, PDE or worker.

The lock child holds only a temporary test file and exits when stdin closes.
All case pools and budget files are synthetic, independent of research data.
"""
from __future__ import annotations

import ast
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('finite_loop_test_target', ROOT/'tools/task1_finite_loop.py')
loop = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = loop
SPEC.loader.exec_module(loop)


class CaseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.pool = {
            'circle-coarse': {'design_id':'circle', 'mesh_id':'coarse'},
            'circle-xy80': {'design_id':'circle', 'mesh_id':'xy80'},
            'circle-xy100': {'design_id':'circle', 'mesh_id':'xy100'},
            'rounded-coarse': {'design_id':'rounded', 'mesh_id':'coarse'},
            'rounded-xy80': {'design_id':'rounded', 'mesh_id':'xy80'},
            'rounded-xy100': {'design_id':'rounded', 'mesh_id':'xy100'},
            'ellipse-coarse': {'design_id':'ellipse', 'mesh_id':'coarse'},
            'ellipse-xy80': {'design_id':'ellipse', 'mesh_id':'xy80'},
            'outside-xy80': {'design_id':'outside', 'mesh_id':'xy80'},
        }
        self.coarse = ['circle-coarse', 'rounded-coarse', 'ellipse-coarse']
        for case in self.pool.values():
            case['channels'] = 2

    def choose(self, designs, meshes=('xy80','xy100'), maximum=2):
        return loop.choose_cases(self.pool, self.coarse, designs, list(meshes), maximum)

    def test_two_selected_designs_expand_only_exact_packaged_cases(self):
        self.assertEqual(set(self.choose(['circle','rounded'])),
                         {'circle-xy80','circle-xy100','rounded-xy80','rounded-xy100'})

    def test_unknown_pool_case_and_missing_mesh_are_rejected(self):
        with self.assertRaises((ValueError, KeyError)):
            loop.choose_cases(self.pool, self.coarse+['absent-coarse'], ['circle'], ['xy80'], 2)
        with self.assertRaises((ValueError, KeyError)):
            self.choose(['ellipse'])  # xy100 is absent; never invent an ID.

    def test_design_outside_registered_coarse_pool_is_rejected(self):
        with self.assertRaises(ValueError):
            self.choose(['outside'], meshes=('xy80',))

    def test_more_than_two_selected_designs_and_duplicates_are_rejected(self):
        with self.assertRaises(ValueError):
            self.choose(['circle','rounded','ellipse'], meshes=('xy80',))
        with self.assertRaises(ValueError):
            self.choose(['circle','circle'], meshes=('xy80',))

    def test_two_design_cap_cannot_be_silently_expanded(self):
        with self.assertRaises(ValueError):
            self.choose(['circle','rounded','ellipse'], meshes=('xy80',), maximum=3)

    def test_existing_reference_or_single_output_cannot_enter_new_TIS_queue(self):
        for change in ({'existing_reference':True}, {'channels':1}):
            with self.subTest(change=change):
                pool = {key:dict(value) for key,value in self.pool.items()}
                pool['circle-xy80'].update(change)
                with self.assertRaises(ValueError):
                    loop.choose_cases(pool,self.coarse,['circle'],['xy80'],2)

    def test_duplicate_mesh_and_noncoarse_source_cannot_duplicate_conditions(self):
        with self.assertRaises(ValueError):
            self.choose(['circle'], meshes=('xy80', 'xy80'))
        with self.assertRaises(ValueError):
            loop.choose_cases(self.pool, ['circle-xy80'], ['circle'], ['xy100'], 1)

    def test_one_three_and_six_coarse_cases_have_exact_overall_bound(self):
        for count in (1, 3, 6):
            pool = {f'd{i}': dict(design_id=f'd{i}', mesh_id='coarse', channels=2) for i in range(count)}
            cases = [dict(id=key, **case) for key, case in pool.items()]
            self.assertEqual(loop.validate_coarse_cases(pool, cases), list(pool))
            self.assertLessEqual(len(cases)+5, 11)
        for count in (0, 7):
            pool = {f'd{i}': dict(design_id=f'd{i}', mesh_id='coarse', channels=2) for i in range(count)}
            with self.assertRaises(ValueError):
                loop.validate_coarse_cases(pool, [dict(id=key, **case) for key, case in pool.items()])

    def test_actual_coarse_registration_must_match_packaged_id_design_mesh_channels(self):
        pool = {'d': dict(design_id='d', mesh_id='coarse', channels=2)}
        case = dict(id='d', **pool['d'])
        for change in ({'id':'unknown'}, {'design_id':'other'}, {'mesh_id':'xy80'}, {'channels':1},
                       {'existing_reference':True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                loop.validate_coarse_cases(pool, [dict(case, **change)])
        with self.assertRaises(ValueError):
            loop.validate_coarse_cases(pool, [case, case])


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'budget.json'

    def write_budget(self, spent, limit=6600):
        self.path.write_text(json.dumps({'spent_seconds':spent,'limit_seconds':limit,'runs':[]}))

    def test_remaining_budget_uses_existing_cumulative_spend(self):
        self.write_budget(1871.0959264469986)
        self.assertAlmostEqual(loop.remaining_budget(self.path), 4728.904073553002)
        self.assertEqual(json.loads(self.path.read_text())['spent_seconds'],1871.0959264469986)

    def test_budget_limit_expansion_and_negative_or_nonfinite_spend_rejected(self):
        for spent, limit in [(1.,6601), (-1.,6600), (float('nan'),6600), (float('inf'),6600)]:
            with self.subTest(spent=spent,limit=limit):
                self.write_budget(spent,limit)
                with self.assertRaises(ValueError):
                    loop.remaining_budget(self.path)

    def test_exhausted_budget_cannot_restart_from_zero(self):
        for spent in (6600,6601):
            with self.subTest(spent=spent):
                self.write_budget(spent)
                try:
                    remaining = loop.remaining_budget(self.path)
                except ValueError:
                    continue
                self.assertLessEqual(remaining,0)

    def test_missing_cumulative_ledger_is_not_treated_as_fresh_budget(self):
        with self.assertRaises((FileNotFoundError,ValueError)):
            loop.remaining_budget(self.path)


class IdentityAndLockTests(unittest.TestCase):
    def test_pid_identity_requires_matching_start_ticks(self):
        pid = os.getpid()
        ticks = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
        self.assertTrue(loop.live_pid(pid,ticks))
        self.assertFalse(loop.live_pid(pid,ticks+1))
        self.assertFalse(loop.live_pid(999999999,ticks))

    def test_duplicate_flock_and_posix_lock_are_each_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'fixture-execution.lock'
            script = '''import fcntl,sys
with open(sys.argv[1],"a+") as stream:
    if sys.argv[2]=="flock": fcntl.flock(stream,fcntl.LOCK_EX)
    else: fcntl.lockf(stream,fcntl.LOCK_EX)
    print("READY",flush=True)
    sys.stdin.readline()
'''
            for kind in ('flock','posix'):
                with self.subTest(kind=kind):
                    process = subprocess.Popen([sys.executable,'-c',script,str(path),kind],
                                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,text=True)
                    try:
                        self.assertEqual(process.stdout.readline().strip(),'READY')
                        with self.assertRaises((BlockingIOError,RuntimeError)):
                            with loop.LockKeeper(path):
                                self.fail('A second finite coordinator acquired an occupied lock')
                    finally:
                        process.communicate(input='exit\n',timeout=5)
                    self.assertEqual(process.returncode,0)
                    # A failed second lock must not leak the first lock namespace.
                    with path.open('a+') as stream:
                        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                        fcntl.lockf(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)


class SnapshotAndCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()

    def test_snapshot_captures_HEAD_code_and_explicit_plan_hashes(self):
        code = self.repo/'tools/task1_fixture.py'
        code.parent.mkdir()
        code.write_text('frozen numerical adapter fixture\n')
        plan = self.repo/'plan.json'
        plan.write_text('{"selected":["circle"]}')
        with patch.object(loop.subprocess,'check_output',return_value='a'*40+'\n'):
            first = loop.source_snapshot(self.repo,(plan,))
            self.assertEqual(first['source_commit'],'a'*40)
            self.assertEqual(first['files'][str(plan)],loop.sha(plan))
            code.write_text('changed numerical adapter fixture\n')
            changed_code = loop.source_snapshot(self.repo,(plan,))
        self.assertNotEqual(first['files'][str(code)],changed_code['files'][str(code)])
        with patch.object(loop.subprocess,'check_output',return_value='b'*40+'\n'):
            changed_HEAD = loop.source_snapshot(self.repo,(plan,))
        self.assertNotEqual(changed_HEAD['source_commit'],changed_code['source_commit'])
        self.assertEqual(changed_HEAD['files'],changed_code['files'])

    def test_checkpoint_write_preserves_unicode_and_finishes_without_partial(self):
        path = self.repo/'checkpoint.json'
        path.write_text('{"status":"old"}')
        loop.checkpoint(path,{'status':'준비','complete':False})
        self.assertEqual(json.loads(path.read_text()),{'status':'준비','complete':False})
        self.assertFalse(path.with_name('checkpoint.json.partial').exists())

    def test_failed_atomic_replace_preserves_previous_checkpoint(self):
        path = self.repo/'checkpoint.json'
        old = b'{"status":"old_failure_evidence"}\n'
        path.write_bytes(old)
        with patch.object(loop.Path,'replace',side_effect=OSError('fixture replace failure')):
            with self.assertRaisesRegex(OSError,'fixture replace failure'):
                loop.checkpoint(path,{'status':'new'})
        self.assertEqual(path.read_bytes(),old)
        self.assertEqual(json.loads(path.with_name('checkpoint.json.partial').read_text()),{'status':'new'})

    def test_nonfinite_checkpoint_cannot_replace_saved_state(self):
        path = self.repo/'checkpoint.json'
        old = b'{"status":"saved"}\n'
        path.write_bytes(old)
        with self.assertRaises(ValueError):
            loop.checkpoint(path,{'seconds':float('nan')})
        self.assertEqual(path.read_bytes(),old)


class CoreCommandTests(unittest.TestCase):
    def test_prepare_argv_uses_actual_core_flag_contract(self):
        run = ROOT/'data-native/cloud-fixture-followup'
        actual = list(map(str,loop.core_command('prepare',run,['circle-xy80','rounded-xy80'])))
        self.assertEqual(actual,[loop.PYTHON,str(ROOT/'tools/task1_cloud_batch.py'),
                                 '--prepare','--output',str(run),
                                 '--case','circle-xy80','--case','rounded-xy80'])

    def test_execute_argv_uses_flags_without_positional_mode_or_run_alias(self):
        run = ROOT/'data-native/cloud-fixture-followup'
        actual = list(map(str,loop.core_command('execute',run)))
        self.assertEqual(actual,[loop.PYTHON,str(ROOT/'tools/task1_cloud_batch.py'),
                                 '--execute','--output',str(run)])
        self.assertNotIn('--run',actual)
        self.assertNotIn('execute',actual)

    def test_used_flags_exist_in_actual_core_parser_without_executing_main(self):
        tree = ast.parse((ROOT/'tools/task1_cloud_batch.py').read_text())
        main = next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
        flags = {argument.value for node in ast.walk(main)
                 if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
                 and node.func.attr=='add_argument'
                 for argument in node.args if isinstance(argument,ast.Constant)
                 and isinstance(argument.value,str) and argument.value.startswith('--')}
        self.assertTrue({'--prepare','--execute','--output','--case'} <= flags)
        self.assertNotIn('--run',flags)
        for mode in ('prepare','execute'):
            command = list(map(str,loop.core_command(mode,ROOT/'data-native/cloud-fixture')))
            self.assertTrue(set(part for part in command if part.startswith('--')) <= flags)

    def test_execute_cannot_carry_prepare_cases_or_unknown_mode(self):
        with self.assertRaises(ValueError):
            loop.core_command('execute',ROOT/'data-native/cloud-fixture',['circle-xy80'])
        with self.assertRaises(ValueError):
            loop.core_command('launch',ROOT/'data-native/cloud-fixture')


class PeerGateTests(unittest.TestCase):
    def make_loop(self, initial=None):
        instance = object.__new__(loop.FiniteLoop)
        instance.state = {'peer_before':initial if initial is not None else self.snapshot()}
        instance.deadline = float('inf')
        instance.output = Path('/unused-fixture/finite-loop-test')
        instance.check = Mock()
        instance.save = Mock()
        instance.child = Mock()
        return instance

    def snapshot(self):
        return {'status':'read_only_GitHub_GET_verified',
                'evidence':{'head':{'head_sha':'a'*40},'comments':[],'reviews':[]}}

    def test_stable_verified_feedback_allows_gate_without_running_child(self):
        instance = self.make_loop()
        with patch.object(loop,'peer_snapshot',return_value=self.snapshot()):
            instance.peer_gate('fine')
        instance.check.assert_called_once()
        instance.save.assert_called_once()
        instance.child.assert_not_called()
        self.assertEqual(instance.state['peer_phase_checks'][0]['phase'],'fine')

    def test_changed_or_unavailable_feedback_blocks_before_any_prepare_child(self):
        changed_head = self.snapshot()
        changed_head['evidence']['head']['head_sha'] = 'b'*40
        changed_comments = self.snapshot()
        changed_comments['evidence']['comments'] = [{'id':1,'body_sha256':'new'}]
        for label in ('fine','confirm'):
            for changed in (changed_head,changed_comments,{'status':'unavailable','evidence':None}):
                with self.subTest(label=label,status=changed['status'],evidence=changed['evidence']):
                    instance = self.make_loop()
                    with patch.object(loop,'peer_snapshot',return_value=changed):
                        with self.assertRaises(loop.PeerReview):
                            instance.execute_phase(label,['circle-xy80'])
                    instance.child.assert_not_called()
                    self.assertEqual(instance.state['peer_phase_checks'][0]['phase'],label)

    def test_unverified_initial_snapshot_cannot_be_retroactively_treated_as_stable(self):
        instance = self.make_loop({'status':'fallback_remote_HEAD_only','evidence':'a'*40})
        with patch.object(loop,'peer_snapshot',return_value=self.snapshot()):
            with self.assertRaises(loop.PeerReview):
                instance.execute_phase('fine',['circle-xy80'])
        instance.child.assert_not_called()

    def test_phase_reserve_failure_blocks_child_even_after_peer_gate_passes(self):
        instance = self.make_loop()
        instance.peer_gate = Mock()
        with patch.object(loop,'remaining_budget',return_value=599):
            with self.assertRaisesRegex(RuntimeError,'resource_shortage'):
                instance.execute_phase('fine',['circle-xy80'])
        instance.peer_gate.assert_called_once_with('fine')
        instance.child.assert_not_called()


class PipelineFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.run = self.repo/'coarse'
        self.output = self.repo/'finite-loop-fixture'
        self.output.mkdir()
        self.hist = self.repo/'history'
        self.hist.mkdir()
        self.pool = {}
        self.paths = {}
        for index in range(6):
            for mesh in ('coarse','xy80','xy100','sc4','bulk'):
                ident = f'd{index}-{mesh}'
                self.pool[ident] = {'design_id':f'd{index}','mesh_id':mesh,'channels':2}
                path = self.repo/'summaries'/(ident+'.json')
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'id':ident,'status':'complete'}))
                self.paths[ident] = path
        (self.hist/'preregistration.json').write_text(json.dumps({'case_pool':self.pool}))
        self.pre = {'cases':[{'id':f'd{i}-coarse','config_sha256':'0'*64,
                             'design_id':f'd{i}','mesh_id':'coarse','channels':2,
                             'config_file':str(self.repo/f'config-{i}.properties'),
                             'mask_file':str(self.repo/f'mask-{i}.csv')} for i in range(6)]}
        self.budget = self.repo/'budget.json'
        self.budget.write_text(json.dumps(dict(limit_seconds=6600, spent_seconds=1234., runs=[])))
        self.budget_patch = patch.object(loop, 'BUDGET', self.budget)
        self.budget_patch.start()
        self.addCleanup(self.budget_patch.stop)

    def instance(self):
        instance = object.__new__(loop.FiniteLoop)
        instance.coarse = self.run
        instance.output = self.output
        instance.state = {'stages':[]}
        instance.deadline = float('inf')
        instance.save,instance.check,instance.child,instance.debit_overhead = Mock(),Mock(),Mock(),Mock()
        return instance

    def test_mocked_pipeline_advances_two_fine_then_one_design_three_confirm_cases(self):
        instance = self.instance()
        coarse = [self.paths[f'd{i}-coarse'] for i in range(6)]
        fine = [self.paths['d0-xy80'],self.paths['d1-xy80']]
        confirm = [self.paths[f'd1-{mesh}'] for mesh in ('xy100','sc4','bulk')]
        instance.audit = Mock(return_value=coarse)
        instance.rank = Mock(side_effect=[['d0-coarse','d1-coarse'],['d1-xy80'],[]])
        instance.execute_phase = Mock(side_effect=[fine,confirm])
        peer = {'status':'read_only_GitHub_GET_verified','evidence':{'head':'same','comments':[],'reviews':[]}}
        with patch.object(loop,'HIST',self.hist), patch.object(loop,'BASELINES',{}), \
                patch.object(loop,'source_snapshot',return_value={'source_commit':'a'*40,'files':{}}), \
                patch.object(loop,'completed_run',return_value=self.pre), \
                patch.object(loop,'peer_snapshot',return_value=peer), \
                patch.object(loop,'remaining_budget',return_value=6600), \
                patch.object(loop,'candidate_mesh_validation',return_value={'status':'failed_gates_preserved'}):
            instance.execute()
        self.assertEqual(instance.execute_phase.call_args_list,
                         [call('fine',['d0-xy80','d1-xy80']),
                          call('confirm',['d1-xy100','d1-sc4','d1-bulk'])])
        for invocation in instance.execute_phase.call_args_list:
            self.assertTrue(all(ident in self.pool for ident in invocation.args[1]))
        self.assertEqual(instance.rank.call_args_list[-1],call('rank-final',coarse+fine+confirm,1))
        self.assertEqual(instance.state['candidate_mesh_validation']['status'],'failed_gates_preserved')
        # Only a mocked final renderer is reached; no prepare/PDE child is invoked.
        self.assertEqual([c.args[0] for c in instance.child.call_args_list],['render-final'])
        self.assertEqual(instance.state['status'], 'completed_predefined_queue_pending_root_selection')
        self.assertEqual(instance.state['maximum_PDE_conditions'], 11)
        self.assertFalse(instance.state['actual_started'])
        self.assertIsNone(instance.state['pde_owner'])
        self.assertIsNone(instance.state['next_PDE_command'])
        self.assertIsNone(instance.state['next_command'])
        self.assertEqual(instance.state['next_registration'], 'not_prepared')
        self.assertEqual(instance.state['scientific_blocker']['owner'], 'root')
        self.assertEqual(instance.state['scientific_blocker']['classification'],'adoption_blocked_by_unresolved_convergence')
        self.assertIsNone(instance.state['execution_blocker'])
        self.assertEqual(instance.state['idle_reason'],'no_further_preregistered_cases_in_this_finite_queue')
        self.assertEqual(instance.state['budget'],dict(limit_seconds=6600,spent_seconds=1234.,remaining_seconds=5366.))

    def test_three_case_queue_and_failed_render_preserve_complete_numerics_and_truthful_stop(self):
        instance = self.instance()
        pre = {'cases': self.pre['cases'][:3]}
        coarse = [self.paths[f'd{i}-coarse'] for i in range(3)]
        instance.audit = Mock(return_value=coarse)
        instance.rank = Mock(side_effect=[[], []])
        instance.execute_phase = Mock()
        instance.child.side_effect = RuntimeError('child_error: render-final exit1')
        peer = {'status':'read_only_GitHub_GET_verified','evidence':{}}
        with patch.object(loop,'HIST',self.hist), patch.object(loop,'BASELINES',{}), \
                patch.object(loop,'source_snapshot',return_value={'source_commit':'a'*40,'files':{}}), \
                patch.object(loop,'completed_run',return_value=pre), \
                patch.object(loop,'peer_snapshot',return_value=peer), \
                patch.object(loop,'remaining_budget',return_value=5366):
            instance.execute()
        instance.execute_phase.assert_not_called()
        self.assertEqual(instance.state['maximum_PDE_conditions'],8)
        self.assertEqual(instance.state['numerical_execution_status'],'complete')
        self.assertTrue(instance.state['all_predefined_PDE_steps_finished'])
        self.assertEqual(instance.state['ui_render_status'],'failed_preserved')
        self.assertEqual(instance.state['status'],'completed_predefined_queue_pending_root_selection')
        self.assertIsNone(instance.state['execution_blocker'])
        self.assertEqual(instance.state['scientific_blocker']['classification'],'adoption_blocked_by_unresolved_convergence')
        self.assertIsNone(instance.state['next_PDE_command'])
        self.assertFalse(instance.state['actual_started'])

    def test_phase_cannot_expand_five_new_conditions_or_duplicate_ids(self):
        instance = self.instance()
        instance.state['planned_new_PDE_conditions'] = 4
        instance.peer_gate = Mock()
        for label, ids in [('fine',['d0-xy80','d1-xy80']), ('confirm',['d0-sc4','d0-sc4']),
                           ('confirm',['a','b','c','d']), ('other',['d0-xy80'])]:
            with self.subTest(label=label,ids=ids), self.assertRaises(ValueError):
                instance.execute_phase(label,ids)
        instance.peer_gate.assert_not_called()
        instance.child.assert_not_called()

    def test_unknown_ranking_selection_is_rejected_without_phase_or_PDE(self):
        instance = self.instance()
        output = self.output/'rank-fixture.json'
        def fake_rank_child(stage,command):
            self.assertEqual(stage,'rank-fixture')
            output.write_text(json.dumps({'status':'calculated_unadopted','selected_case_ids':['not-in-inputs']}))
        instance.child.side_effect = fake_rank_child
        instance.execute_phase = Mock()
        with self.assertRaisesRegex(RuntimeError,'outside bounded phase inputs'):
            instance.rank('rank-fixture',[self.paths['d0-coarse']],2)
        instance.execute_phase.assert_not_called()
        self.assertEqual(instance.child.call_count,1)

    def test_completed_run_rejects_live_batch_and_missing_or_changed_case_evidence(self):
        self.run.mkdir()
        (self.run/'cases').mkdir()
        (self.run/'preregistration.json').write_text(json.dumps(self.pre))
        for case in self.pre['cases']:
            target = self.run/'postprocess'/case['id']/'summary.json'
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({'id':case['id'],'status':'complete'}))
            (self.run/'cases'/(case['id']+'.json')).write_text(json.dumps({
                'status':'complete','config_sha256':case['config_sha256'],
                'postprocess_sha256':loop.sha(target)}))
        state = {'status':'complete','registration_sha256':loop.sha(self.run/'preregistration.json')}
        (self.run/'summary.json').write_text(json.dumps(state))
        self.assertEqual(loop.completed_run(self.run),self.pre)
        (self.run/'summary.json').write_text(json.dumps(dict(state,status='running')))
        with self.assertRaisesRegex(RuntimeError,'not complete'):
            loop.completed_run(self.run)
        (self.run/'summary.json').write_text(json.dumps(state))
        (self.run/'postprocess/d5-coarse/summary.json').write_text('{"changed":true}')
        with self.assertRaisesRegex(RuntimeError,'provenance mismatch'):
            loop.completed_run(self.run)


class PaginatedArrayDecodeTests(unittest.TestCase):
    def test_empty_array_is_valid_but_empty_response_is_not(self):
        self.assertEqual(loop.decode_paginated_arrays('[]'),[])
        for text in ('',' \t\r\n'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                loop.decode_paginated_arrays(text)

    def test_whitespace_separated_pages_flatten_in_page_order(self):
        text = ' \n [{"id":1},{"id":2}]\t\r\n[]\n [{"id":3}] \n'
        self.assertEqual(loop.decode_paginated_arrays(text),[{'id':1},{'id':2},{'id':3}])

    def test_invalid_trailing_text_cannot_be_silently_ignored(self):
        for text in ('[] trailing','[{"id":1}]\n[','[]\ntrue','[]\nnull'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                loop.decode_paginated_arrays(text)

    def test_nonarray_page_is_rejected_including_after_a_valid_page(self):
        for text in ('{}','{"items":[]}','1','"list"','[]\n{"id":2}'):
            with self.subTest(text=text),self.assertRaises(ValueError):
                loop.decode_paginated_arrays(text)

    def test_page_limit_counts_empty_pages_too(self):
        self.assertEqual(loop.decode_paginated_arrays('[]\n'*100),[])
        with self.assertRaises(ValueError):
            loop.decode_paginated_arrays('[]\n'*101)

    def test_four_MiB_limit_uses_UTF8_bytes_not_character_count(self):
        limit = 4*1024**2
        text = '["'+('가'*(limit//3+1))+'"]'
        self.assertLess(len(text),limit)
        self.assertGreater(len(text.encode('utf-8')),limit)
        with self.assertRaises(ValueError):
            loop.decode_paginated_arrays(text)


if __name__ == '__main__':
    unittest.main()
