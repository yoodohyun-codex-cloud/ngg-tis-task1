"""Synthetic metadata checks; inherit the already reviewed native fixture."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
reg=load('source_volume_under_test',ROOT/'tools/task1_source_position_volume_registration.py')
fixtures=load('return_volume_fixtures',ROOT/'tests/test_task1_return_position_volume_registration.py')


class SourcePositionVolumeRegistrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReturnPositionVolumeRegistrationTest()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.output=self.root/'docs/source-position-plan.json'
        for run, ident in reg.CASE_TABLE[-2:]:self.fixture.case_fixture(run,ident)
        rows=[];pins={}
        for run,ident in reg.CASE_TABLE[2:4]:
            path=self.root/'data-native'/run/'postprocess'/ident/'summary.json'
            rows.append(dict(case_id=ident,summary_path=str(path)));pins[str(path)]=reg.inherited.sha(path)
        self.fixture.write(self.root/reg.RETURN_REPORT,dict(status='calculated_unadopted',inputs_unchanged=True,cases=rows,inputs_sha256=pins))

    def generate(self):
        with mock.patch.object(reg,'_committed_sources',return_value=('implementation-commit',{})), \
             mock.patch.object(reg.inherited.policy,'load_ledger',return_value=self.fixture.expanded), \
             mock.patch.object(reg.inherited.policy,'effective_limit',return_value=13800), \
             mock.patch.object(reg.inherited.policy,'remaining_seconds',return_value=7800), \
             mock.patch.object(reg.inherited.policy,'policy_refs',return_value={}):
            return reg.make_preregistration(self.output,root=self.root)

    def test_six_ordered_cases_same_baseline_no_array_reads_and_new_source_pins(self):
        original=Path.read_bytes
        def guarded(path):
            if path.name=='volume.npz' or path.name.startswith(('grid.','field-')):raise AssertionError('Array read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):plan=self.generate()
        self.assertEqual([c['case_id']for c in plan['cases']],[i for _,i in reg.CASE_TABLE])
        self.assertEqual(plan['initial_case_count'],6)
        self.assertEqual(plan['baseline_summary_paths'],[plan['cases'][0]['summary']])
        self.assertIn('tools/task1_source_position_volume_registration.py',reg.SOURCES)
        self.assertIn('tests/test_task1_source_position_volume_registration.py',reg.SOURCES)
        self.assertEqual(plan['feedback_id'],'T1-F010-S1-GH6297472037')
        self.assertFalse(plan['geometry_comparison_contract']['joint_source_and_return_shift_tested'])

    def test_source_case_with_different_cohort_is_rejected(self):
        with mock.patch.object(reg.inherited,'_signature',side_effect=['same']*5+['different']):
            with self.assertRaisesRegex(ValueError,'same grid/material/contact/ROI'):self.generate()

    def test_repo_relative_frozen_paths_remain_supported(self):
        for run,_ in reg.CASE_TABLE:
            path=self.root/'data-native'/run/'frozen-source-manifest.json'
            obj=json.loads(path.read_text())
            for item in obj['files'].values():
                if Path(item['path']).is_absolute():item['path']=str(Path(item['path']).relative_to(self.root))
            self.fixture.write(path,obj)
        self.assertEqual(self.generate()['initial_case_count'],6)

    def test_no_overwrite(self):
        self.output.write_text('evidence')
        with self.assertRaisesRegex(ValueError,'New canonical docs'):self.generate()
        self.assertEqual(self.output.read_text(),'evidence')

    def test_stale_return_source_binding_is_rejected(self):
        path=self.root/reg.RETURN_REPORT;obj=json.loads(path.read_text());obj['inputs_sha256']={}
        self.fixture.write(path,obj)
        with self.assertRaisesRegex(ValueError,'bind the selected return'):self.generate()


if __name__=='__main__':unittest.main()
