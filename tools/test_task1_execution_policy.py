"""Mocked contract source; no native data, worker, benchmark or NumPy needed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import task1_execution_policy as ep


def policy_fixture():
    return dict(schema=ep.POLICY_SCHEMA,requested_cpu_limit=4,
        requested_total_memory_bytes=8_000_000_000,max_cells=800000,
        concurrent_solves=1,numerical_owners=1,java_heap_bytes=2_147_483_648,
        blas_threads=4,java_active_processor_count=4,cumulative_time_unlimited=True,
        finite_batch_timeouts_required=True)


def environment_fixture():
    return dict(schema=ep.SNAPSHOT_SCHEMA,affinity_cpus=[0,1,2,3,4],
        visible_cpuset_cpus=[0,1,2,3,4],visible_cpu_quota_cores=4.,
        visible_cgroup_memory_limit_bytes=16*1024**3,
        visible_cgroup_memory_headroom_bytes=7_000_000_000,
        host_MemAvailable_bytes=12_000_000_000,
        hidden_ancestor_limits_verified=False,capacity_guaranteed=False)


class ExecutionPolicyContracts(unittest.TestCase):
    def test_import_has_no_file_read_or_configuration(self):
        spec=importlib.util.spec_from_file_location('isolated_execution_policy',ep.__file__)
        module=importlib.util.module_from_spec(spec)
        with patch.object(Path,'read_text',side_effect=AssertionError('import read')), patch.object(Path,'read_bytes',side_effect=AssertionError('import read')):
            spec.loader.exec_module(module)
        self.assertEqual(module.REQUESTED_MEMORY,8_000_000_000)

    def test_decimal_memory_and_visible_caps(self):
        policy={**policy_fixture(),'_immutable_refs':{'/immutable':'a'*64}}
        environment=environment_fixture()
        with patch.object(ep,'_validated_policy',return_value=policy),patch.object(ep,'inspect_environment',return_value=environment):
            limits=ep.resolve_limits(policy)
        self.assertEqual(limits['cpu_limit'],4)
        self.assertEqual(limits['total_memory_bytes'],8_000_000_000)
        self.assertEqual(limits['java_heap_bytes'],2_147_483_648)
        self.assertAlmostEqual(limits['requested_total_memory_GiB'],7.450580596923828)
        self.assertFalse(limits['capacity_guaranteed'])
        self.assertEqual(limits['visible_cgroup_memory_headroom_bytes'],7_000_000_000)

    def test_tighter_quota_and_memory_limit_win(self):
        policy={**policy_fixture(),'_immutable_refs':{}}
        environment={**environment_fixture(),'visible_cpu_quota_cores':2.5,
                     'visible_cgroup_memory_limit_bytes':6_000_000_000}
        with patch.object(ep,'_validated_policy',return_value=policy),patch.object(ep,'inspect_environment',return_value=environment):
            limits=ep.resolve_limits(policy)
        self.assertEqual(limits['cpu_limit'],2)
        self.assertEqual(limits['affinity_cpus'],[0,1])
        self.assertEqual(limits['total_memory_bytes'],6_000_000_000)

    def test_hash_bound_approval_and_snapshot(self):
        approval=dict(schema=ep.APPROVAL_SCHEMA,status='approved',source='explicit_current_user_instruction',
            cpu_limit=4,total_memory_bytes=8_000_000_000,max_cells=800000,concurrent_solves=1,
            numerical_owners=1,finite_batch_timeouts_required=True,external_paid_resources_authorized=False,
            security_installation_merge_permissions_changed=False,service_limits_bypass_authorized=False)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder).resolve();policy=policy_fixture()
            for label,document in (('approval',approval),('environment_snapshot',environment_fixture())):
                path=folder/(label+'.json');raw=json.dumps(document).encode();path.write_bytes(raw)
                policy[label+'_path']=str(path);policy[label+'_sha256']=hashlib.sha256(raw).hexdigest()
            active=folder/'policy.json';active.write_text(json.dumps(policy))
            loaded=ep.load_active_policy(active)
            self.assertEqual(len(ep.execution_policy_refs(loaded)),3)
            (folder/'approval.json').write_text(json.dumps({**approval,'cpu_limit':8}))
            with self.assertRaisesRegex(ValueError,'SHA256'):
                ep.load_active_policy(active)

    def test_numpy_import_prevents_late_configuration(self):
        with patch.dict(sys.modules,{'numpy':object()}):
            with self.assertRaisesRegex(ValueError,'before NumPy'):
                ep.configure_process({'schema':'task1-resolved-execution-limits-v2'})


if __name__=='__main__':
    unittest.main()
