"""Synthetic integration for the authorized cumulative-only budget extension."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tools'
sys.path.insert(0, str(TOOLS))
import task1_cloud_batch as core
import task1_resource_policy as policy

SPEC=importlib.util.spec_from_file_location('expanded_budget_policy_fixture', ROOT/'tests/test_task1_resource_policy.py')
POLICY_TESTS=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY_TESTS)

CLI_CAPS={'task1_spatial_audit.py':180., 'task1_volume_selectivity.py':600.,
          'task1_results_view.py':120., 'task1_volume_audit_view.py':120.}


def live_budget_arithmetic(filename, ledger):
    """Execute only each CLI's actual validation/deadline expressions, never main."""
    tree=ast.parse((TOOLS/filename).read_text())
    main=next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name=='main')
    assignments=sorted((node for node in ast.walk(main) if isinstance(node, ast.Assign)),
                       key=lambda node:node.lineno)
    selected=[]
    for name in ('global_limit', 'remaining'):
        matches=[node for node in assignments if any(isinstance(target, ast.Name) and target.id==name
                                                     for target in node.targets)]
        if matches:
            selected.append(copy.deepcopy(matches[0]))
        elif name=='global_limit':
            raise AssertionError(filename+' must validate its global budget')
    cap=CLI_CAPS[filename]
    deadline_calls=[node for node in ast.walk(main) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id=='min' and node.args
        and isinstance(node.args[0], ast.Constant) and node.args[0].value==cap]
    if not deadline_calls or len({ast.dump(node, include_attributes=False) for node in deadline_calls})!=1:
        raise AssertionError(filename+' must use the same fixed stage-cap expression everywhere')
    selected.append(ast.Assign(targets=[ast.Name(id='test_seconds', ctx=ast.Store())],
                               value=copy.deepcopy(deadline_calls[0])))
    program=ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    namespace={'effective_limit':policy.effective_limit, 'budget':ledger, 'ledger':ledger}
    exec(compile(program, filename+'[budget-only]', 'exec'), namespace)
    return namespace['global_limit'], namespace['test_seconds']


class ExpandedBudgetIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=POLICY_TESTS.ResourcePolicyTest('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.expanded=self.fixture.expand()
        self.legacy=copy.deepcopy(self.fixture.old)

    def test_legacy_limits_are_unchanged_and_return_a_fresh_dictionary(self):
        before=copy.deepcopy(core.LIMITS)
        actual=core.effective_limits(self.legacy)
        self.assertEqual(actual, before)
        actual['cpu']=99
        self.assertEqual(core.LIMITS, before)

    def test_valid_expansion_changes_only_cumulative_seconds_and_preserves_per_job_caps(self):
        actual=core.effective_limits(self.expanded)
        self.assertEqual(actual['cumulative_seconds'],13800)
        self.assertEqual({key:value for key,value in actual.items() if key!='cumulative_seconds'},
                         {key:value for key,value in core.LIMITS.items() if key!='cumulative_seconds'})
        self.assertEqual(core.LIMITS['cumulative_seconds'],6600)
        self.assertEqual(actual['cpu'],1)
        self.assertEqual(actual['concurrent_solves'],1)
        self.assertEqual(actual['per_condition_seconds'],600)
        self.assertEqual(actual['aggregate_rss_bytes'],3*1024**3)

    def test_invalid_expanded_ledger_cannot_reach_effective_core_limits(self):
        forged=copy.deepcopy(self.legacy);forged['limit_seconds']=13800
        with self.assertRaises(ValueError):
            core.effective_limits(forged)

    def source_tree(self):
        source=self.fixture.root/'tis-java';source.mkdir()
        for filename in ('TisSweep.java','ExploreBasis.java','SelectivityShapeBasis.java','fixture.py'):
            (source/filename).write_text('synthetic source '+filename)
        cloud=self.fixture.root/'tools/java/CloudShapeBasis.java'
        cloud.parent.mkdir(parents=True)
        cloud.write_text('synthetic cloud producer')
        return source

    def test_source_pins_bind_helper_and_immutable_policy_but_never_mutable_ledger(self):
        source=self.source_tree()
        with patch.object(core,'REPO',self.fixture.root),patch.object(core,'SOURCE',source):
            pins=core.source_pins(self.expanded)
            self.assertEqual(pins[str(Path(policy.__file__).resolve())],core.sha(Path(policy.__file__).resolve()))
            for path,digest in policy.policy_refs(self.expanded).items():
                self.assertEqual(pins[path],digest)
            self.assertNotIn(str(self.fixture.ledger),pins)
            future=copy.deepcopy(self.expanded)
            future['spent_seconds']+=5
            future['runs'].append(dict(id='new-debit',seconds=5))
            self.fixture.write(self.fixture.ledger,future)
            self.assertEqual(core.source_pins(),pins)

    def test_source_pins_reject_policy_hash_drift_before_registration(self):
        source=self.source_tree()
        self.fixture.approval.write_bytes(self.fixture.approval.read_bytes()+b' ')
        with patch.object(core,'REPO',self.fixture.root),patch.object(core,'SOURCE',source),self.assertRaises(ValueError):
            core.source_pins(self.expanded)

    def pre(self, limits):
        return dict(status='prepared',gates=copy.deepcopy(core.GATES),limits=limits,
                    source_and_input_sha256={})

    def test_execute_rejects_legacy_registration_under_expanded_policy_before_delegating(self):
        run=self.fixture.root/'data-native/cloud-synthetic';run.mkdir(parents=True)
        self.fixture.write(run/'preregistration.json',self.pre(dict(core.LIMITS)))
        with patch.object(core,'REPO',self.fixture.root),patch.object(core,'execute_locked') as execute_locked:
            with self.assertRaisesRegex(ValueError,'Registration limits unsupported'):
                core.execute(run)
            execute_locked.assert_not_called()
        self.assertFalse((run/'execution-attempt.json').exists())

    def test_execute_locked_independently_rejects_old_limits_before_integrity_outputs_or_child(self):
        run=self.fixture.root/'data-native/cloud-synthetic'
        with patch.object(core,'REPO',self.fixture.root),patch.object(core,'original_integrity') as integrity, \
             patch.object(core,'write') as write,patch.object(core.subprocess,'Popen') as child:
            with self.assertRaisesRegex(ValueError,'Registration limits/gates unsupported'):
                core.execute_locked(run,self.pre(dict(core.LIMITS)))
            integrity.assert_not_called();write.assert_not_called();child.assert_not_called()

    def test_execute_rechecks_attempt_marker_created_during_global_lock_acquisition(self):
        run=self.fixture.root/'data-native/cloud-race-fixture';run.mkdir(parents=True)
        self.fixture.write(run/'preregistration.json',self.pre(core.effective_limits(self.expanded)))
        marker=run/'execution-attempt.json'
        ledger_before=self.fixture.ledger.read_bytes()
        def race(*args,**kwargs):
            marker.write_text('{"status":"other-worker-attempt"}\n')
        with patch.object(core,'REPO',self.fixture.root),patch.object(core.fcntl,'flock',side_effect=race), \
             patch.object(core,'read',wraps=core.read) as read,patch.object(core,'execute_locked') as execute_locked:
            with self.assertRaises(ValueError):
                core.execute(run)
            execute_locked.assert_not_called()
            self.assertNotIn(self.fixture.ledger,[call.args[0] for call in read.call_args_list])
        self.assertTrue(marker.exists())
        self.assertEqual(marker.read_text(),'{"status":"other-worker-attempt"}\n')
        self.assertEqual(self.fixture.ledger.read_bytes(),ledger_before)

    def test_current_expanded_registration_passes_budget_gate_before_intercepted_integrity(self):
        class ReachedValidatedAdmission(Exception):
            pass
        run=self.fixture.root/'data-native/cloud-synthetic'
        pre=self.pre(core.effective_limits(self.expanded))
        with patch.object(core,'REPO',self.fixture.root), \
             patch.object(core,'original_integrity',side_effect=ReachedValidatedAdmission) as integrity, \
             patch.object(core,'write') as write,patch.object(core.subprocess,'Popen') as child:
            with self.assertRaises(ReachedValidatedAdmission):
                core.execute_locked(run,pre)
            integrity.assert_called_once();write.assert_not_called();child.assert_not_called()

    def test_each_live_CLI_uses_validated_limit_and_keeps_its_original_stage_cap(self):
        for filename,cap in CLI_CAPS.items():
            for kind,spent,expected in (('legacy',6590.,10.),('expanded',13790.,10.),
                                        ('expanded',6500.,cap)):
                ledger=copy.deepcopy(self.legacy if kind=='legacy' else self.expanded)
                ledger['spent_seconds']=spent
                with self.subTest(filename=filename,kind=kind,spent=spent):
                    limit,seconds=live_budget_arithmetic(filename,ledger)
                    self.assertEqual(limit,6600 if kind=='legacy' else 13800)
                    self.assertEqual(seconds,expected)

    def test_each_live_CLI_propagates_invalid_policy_rejection_before_deadline_allocation(self):
        invalid=copy.deepcopy(self.legacy);invalid['limit_seconds']=13800
        for filename in CLI_CAPS:
            with self.subTest(filename=filename),self.assertRaises(ValueError):
                live_budget_arithmetic(filename,invalid)


if __name__=='__main__':
    unittest.main()
