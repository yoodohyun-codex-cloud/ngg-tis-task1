"""Saved-screen joins and staged-count tests; no native arrays/render jobs."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
SPEC=importlib.util.spec_from_file_location('cross_view_tested',ROOT/'tools/task1_volume_cross_allocation_view.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class CrossAllocationViewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        mode=dict(source_Vpp_per_output=.9,active_skin_contact_caps=['skinJ95'],
            normalized_burdens=dict(bulk_skin_J_vector_RMS_p95_A_m2=7.,source_power_W=.001),regions={
                M.merge.view.PRIMARY:dict(maxTIS=dict(mean=3.,p10=2.)),
                'surface_0_5':dict(maxTIS=dict(p95=20.)), 'primary_complement':dict(maxTIS=dict(p95=19.))})
        self.candidate=dict(case_id='candidate',normalizations=dict(skin_contact_only=mode))
        self.volume=self.root/'volume.json';self.volume.write_text(json.dumps(dict(cases=[dict(case_id='baseline'),self.candidate])))
        self.audit=dict(path=str(self.volume),SHA256=M.merge.view.sha(self.volume),report=json.loads(self.volume.read_text()))
        self.plan=self.root/'plan.json';self.plan.write_text('{}')
        checks=[dict(name='target_mean'if i==0 else'gate'+str(i),unit='V/m',required_direction='greater'if i<2 else'less',
            baseline=4.,candidate=3.,relative_change_percent=-25.,passed=i>=2)for i in range(8)]
        self.screen=dict(schema='task1-candidate-screen-v1',status='screen_complete_not_adopted',normalization='skin_contact_only',
            candidate_adopted=False,input_volume_report=dict(path=str(self.volume),SHA256=self.audit['SHA256']),
            baseline_case_id='baseline',preregistration=dict(path=str(self.plan),SHA256=M.merge.view.sha(self.plan)),
            cases=[dict(case_id='candidate',checks=checks,all_screen_checks_passed=False,failed_checks=['target_mean','gate1'],
                decision='not nominated',all_five_normalizations=copy.deepcopy(self.candidate['normalizations']))])
        self.path=self.root/'screen.json';self.write()

    def write(self):self.path.write_text(json.dumps(self.screen))

    def test_saved_screen_is_bound_to_exact_report_and_values_unchanged(self):
        before=copy.deepcopy(self.screen);result=M.validate_screen(self.path,self.audit)
        self.assertEqual(result['cases'][0]['checks'],before['cases'][0]['checks'])
        self.assertFalse(result['cases'][0]['all_screen_checks_passed'])
        self.screen['input_volume_report']['SHA256']='0'*64;self.write()
        with self.assertRaises(ValueError):M.validate_screen(self.path,self.audit)

    def test_stored_pass_flags_and_normalization_joins_must_be_consistent(self):
        original=copy.deepcopy(self.screen)
        self.screen['cases'][0]['all_screen_checks_passed']=True;self.write()
        with self.assertRaises(ValueError):M.validate_screen(self.path,self.audit)
        self.screen=copy.deepcopy(original);self.screen['cases'][0]['all_five_normalizations']['skin_contact_only']['source_Vpp_per_output']=10.;self.write()
        with self.assertRaises(ValueError):M.validate_screen(self.path,self.audit)

    def test_screen_display_keeps_target_and_non_target_values_separate(self):
        screen=M.validate_screen(self.path,self.audit)
        text=M.screen_section(dict(cases=[self.candidate]),screen,self.root/'v8.html')
        self.assertIn('ROI mean V/m',text);self.assertIn('surfaceP95 V/m',text);self.assertIn('source W',text)
        self.assertIn('FAIL / not nominated',text);self.assertIn('generates no new physical XY/XZ maps',text)
        self.assertIn('stored8-gate evidence',text)

    def test_staged_merge_retains_original37_plus4_plus3_counts(self):
        old=dict(cases=[{}]*37);stage1=dict(cases=[{}]*41);stage2=dict(cases=[{}]*44)
        with patch.object(M.merge,'load_snapshot',return_value=(old,dict(case_count=37))),\
             patch.object(M.merge,'validate_new_audit',side_effect=[{'stage':1},{'stage':2}]),\
             patch.object(M.merge,'merge_model',side_effect=[stage1,stage2]),\
             patch.object(M,'validate_screen',return_value={'cases':[]}):
            model,_,audits,_=M.build_model('old.html','old.receipt',['source','allocation'],'screen')
        self.assertEqual(model['snapshot_merge']['historical_cases'],37)
        self.assertEqual(model['snapshot_merge']['new_cases'],7)
        self.assertEqual(model['snapshot_merge']['staged_additions'],[4,3])
        self.assertEqual(len(audits),2)


if __name__=='__main__':unittest.main()
