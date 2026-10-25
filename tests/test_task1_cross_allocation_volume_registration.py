"""Synthetic cached metadata registration; no actual basis/NPZ decoding."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
reg=load('allocation_volume_under_test',ROOT/'tools/task1_cross_allocation_volume_registration.py')
fixtures=load('allocation_metadata_fixtures',ROOT/'tests/test_task1_return_position_volume_registration.py')


class CrossAllocationVolumeRegistrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReturnPositionVolumeRegistrationTest()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.output=self.root/'docs/cross-allocation-plan.json'
        for ident in reg.CASE_IDS:self.fixture.case_fixture(reg.NEW_RUN,ident)
        path=self.root/'data-native'/reg.NEW_RUN/'preregistration.json';pre=json.loads(path.read_text())
        for case,area in zip(pre['cases'],reg.ALLOCATIONS_MM2):
            case['expected_pad_areas_m2']=[area*1e-6]*2+[(450-area)*1e-6]*2
        self.fixture.write(path,pre)
        for audit in (path.parent/'audit').glob('*.json'):
            obj=json.loads(audit.read_text());obj['registration_sha256']=reg.inherited.sha(path);self.fixture.write(audit,obj)

    def generate(self):
        with mock.patch.object(reg,'_committed_sources',return_value=('implementation-commit',{})), \
             mock.patch.object(reg.inherited.policy,'load_ledger',return_value=self.fixture.expanded), \
             mock.patch.object(reg.inherited.policy,'effective_limit',return_value=13800), \
             mock.patch.object(reg.inherited.policy,'remaining_seconds',return_value=7800), \
             mock.patch.object(reg.inherited.policy,'policy_refs',return_value={}):
            return reg.make_preregistration(self.output,root=self.root)

    def test_fixed_four_rows_baseline_and_no_array_reads(self):
        original=Path.read_bytes
        def guarded(path):
            if path.name=='volume.npz' or path.name.startswith(('grid.','field-')):raise AssertionError('Array read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):plan=self.generate()
        self.assertEqual([c['case_id']for c in plan['cases']],[i for _,i in reg.CASE_TABLE])
        self.assertEqual(plan['initial_case_count'],4)
        self.assertEqual(plan['baseline_summary_paths'],[plan['cases'][0]['summary']])
        self.assertEqual(plan['feedback_id'],'T1-F010-S1-GH6297472037')
        self.assertIn('tools/task1_cross_allocation_volume_registration.py',reg.SOURCES)
        self.assertIn('tests/test_task1_cross_allocation_volume_registration.py',reg.SOURCES)
        self.assertFalse(plan['geometry_comparison_contract']['isolated_area_effect_claimed'])

    def test_wait_for_all_three_controller_receipts(self):
        path=self.root/'data-native'/reg.NEW_RUN/'cases'/(reg.CASE_IDS[-1]+'.json')
        path.unlink()
        with self.assertRaisesRegex(ValueError,'regular input'):self.generate()
        self.assertFalse(self.output.exists())

    def test_wait_for_all_three_full_skin_audits(self):
        path=self.root/'data-native'/reg.NEW_RUN/'audit'/('full-skin-'+reg.CASE_IDS[-1]+'.json')
        path.unlink()
        with self.assertRaisesRegex(ValueError,'source-bound completed full-skin'):self.generate()

    def test_mixed_model_cohort_rejected(self):
        with mock.patch.object(reg.inherited,'_signature',side_effect=['same']*3+['different']):
            with self.assertRaisesRegex(ValueError,'same grid/material/contact/ROI'):self.generate()

    def test_wrong_allocation_cannot_use_a_valid_case_id(self):
        path=self.root/'data-native'/reg.NEW_RUN/'preregistration.json';pre=json.loads(path.read_text())
        pre['cases'][-1]['expected_pad_areas_m2']=[.000225]*4;self.fixture.write(path,pre)
        for audit in (path.parent/'audit').glob('*.json'):
            obj=json.loads(audit.read_text());obj['registration_sha256']=reg.inherited.sha(path);self.fixture.write(audit,obj)
        with self.assertRaisesRegex(ValueError,'Fixed per-pad allocation'):self.generate()

    def test_no_overwrite(self):
        self.output.write_text('evidence')
        with self.assertRaisesRegex(ValueError,'New canonical docs'):self.generate()
        self.assertEqual(self.output.read_text(),'evidence')


if __name__=='__main__':unittest.main()
