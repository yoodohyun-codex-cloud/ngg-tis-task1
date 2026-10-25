"""Synthetic SC-only sensitivity contracts; no native fields, JVM or PDE."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_rounded_sc4_registration as r
import task1_rounded_fullface_registration as rounded


class RoundedSC4RegistrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline=next(d for d in json.loads((rounded.core.HIST/'inputs/designs.json').read_text())
            if d['id']=='baseline-square15')
        cls.design,cls.rows,cls.areas,cls.proof=rounded.rounded_design(baseline)
        cls.mask=rounded._mask_bytes(cls.rows)
        cls.source=dict(rounded.COMMON,id=rounded.CASE_ID,design=cls.design,expected_pad_areas_m2=cls.areas,
            mask_sha256=hashlib.sha256(cls.mask).hexdigest(),frequencies_Hz=[3000,3030,9000,9090],cells=351680,
            sc_cells=2,h_xy_mm=.625,bulk_counts=[14,14,40],channels=2,
            circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},
                source_Vpp_each=1.,source_peak_V=.5,source_resistance_ohm=50,return_topology='all_return_pads_ideal_common_GND',
                carrier_assignment_Hz=[3000,3030],inactive_source_at_other_frequencies='0 V through 50 ohm'))
        data=(rounded.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        cls.config,_=rounded.changed_rounded_config(data,cls.design,Path('/tmp/source-rounded.csv'),cls.source['mask_sha256'])

    def test_sc4_updates_only_discretization_and_identical_copy_path_not_physical_thickness(self):
        before=rounded._properties(self.config)
        output,changes=r.changed_sc4_config(self.config,Path('/tmp/sc4-rounded.csv'))
        after=rounded._properties(output)
        self.assertEqual({'validation.sc_cells','mask.path'},set(changes))
        self.assertEqual('2',before['validation.sc_cells']);self.assertEqual('4',after['validation.sc_cells'])
        self.assertEqual(set(before),set(after));self.assertEqual(before['mask.sha256'],after['mask.sha256'])
        self.assertEqual({k:v for k,v in before.items()if k not in changes},{k:v for k,v in after.items()if k not in changes})
        self.assertEqual('0.625',after['h_mm']);self.assertEqual('14,14,40',after['bulk.counts'])
        self.assertEqual('3000,3030,9000,9090',after['frequencies'])

    def test_source_must_be_original_sc2_grid_and_four_registered_frequencies(self):
        for key,value in [('h_mm','0.5'),('validation.sc_cells','4'),('bulk.counts','18,18,56'),('frequencies','3000,3030')]:
            text=self.config.decode();old=rounded._properties(self.config)[key]
            bad=text.replace(key+'='+old,key+'='+value)
            with self.subTest(key=key),self.assertRaises(ValueError):r.changed_sc4_config(bad.encode(),Path('/tmp/new.csv'))

    def test_frozen_rounded_contour_and_original_mask_bytes_are_accepted_without_mutation(self):
        before=copy.deepcopy(self.source);digest=hashlib.sha256(self.mask).hexdigest()
        receipt=r.validate_physical_identity(self.source,self.mask)
        self.assertTrue(receipt['physical_geometry_unchanged']);self.assertEqual(digest,receipt['mask_byte_SHA256'])
        self.assertEqual(900.,receipt['physical_total_contact_area_mm2'])
        self.assertEqual((2,4,.1),(receipt['old_SC_cells'],receipt['new_SC_cells'],receipt['physical_SC_thickness_mm']))
        self.assertEqual(before,self.source)
        self.assertEqual(digest,hashlib.sha256(self.mask).hexdigest())
        self.assertEqual(2304,len(self.rows));self.assertEqual([576]*4,self.proof['faces_per_pad'])
        self.assertTrue(self.proof['all_cutoff_ties_included']);self.assertEqual(16,self.proof['cutoff_tie_face_count'])

    def test_changed_area_shape_wiring_indices_or_partial_face_is_rejected(self):
        for change in ('area','shape','wire','index','partial'):
            source=copy.deepcopy(self.source);mask=self.mask
            if change=='area':source['design']['pads'][0]['analytic_area_mm2']=224.
            elif change=='shape':source['design']['pads'][1]['shape']='circle'
            elif change=='wire':source['design']['pads'][2]['source_output']=2
            elif change=='index':source['design']['pads'][3]['native_face_indices'][0][0]+=1
            else:
                rows=list(self.rows);p,i,j,a=rows[0];rows[0]=(p,i,j,a*.25);mask=rounded._mask_bytes(rows)
                source['mask_sha256']=hashlib.sha256(mask).hexdigest()
            with self.subTest(change=change),self.assertRaises(ValueError):r.validate_physical_identity(source,mask)

    def test_single_finite_sc_axis_case_preserves_geometry_and_native_resource_ceiling(self):
        self.assertEqual(361728,r.EXPECTED_CELLS);self.assertLessEqual(r.EXPECTED_CELLS,800000)
        self.assertEqual(217036800,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(r.EXPECTED_CELLS*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1320,r.MIN_REMAINING_SECONDS);self.assertEqual(120,r.PREPARATION_SECONDS)
        self.assertNotEqual(rounded.CASE_ID,r.CASE_ID)

    def test_actual_selected_condition_requires_terminal_matching_source_and_saved_finite_scale(self):
        ident='synthetic-actual-rounded-selection'
        caps={key:1. for key in ('surface_J_RMS_max_A_m2','surface_J_RMS_p95_A_m2','contact_voltage_RMS_max_V',
            'SC_power_W','contact_power_W','bulk_skin_J_vector_RMS_max_A_m2','bulk_skin_J_vector_RMS_p95_A_m2','skin_SC_plus_dermis_power_W')}
        summary=dict(schema='task1-rounded-drive-scout-v1',status='calculated_unadopted',inputs_unchanged=True,new_PDE=0,
            candidate_adopted=False,source_geometry=dict(source_case_id=r.SOURCE_ID,source_run_id=r.SOURCE_RUN),
            conditions=[dict(id=ident,status='calculated_unadopted',artifacts={'condition.json':dict(path='/tmp/actual-condition.json',SHA256='a'*64)})])
        condition=dict(schema='task1-rounded-drive-condition-v1',status='calculated_unadopted',id=ident,
            source_case_id=r.SOURCE_ID,source_run_id=r.SOURCE_RUN,configuration_sha256='b'*64,new_PDE=0,candidate_adopted=False,
            coefficient_vectors={'3000':dict(real=[0.,0.],imaginary=[-1.,0.]),'3030':dict(real=[0.,0.],imaginary=[0.,-1.]),
                '9000':dict(real=[0.,0.],imaginary=[0.,0.]),'9090':dict(real=[0.,0.],imaginary=[0.,0.])},
            active_frequencies_Hz=[3000,3030],actual_fundamental_Hz=[3000,3030],
            normalizations=dict(skin_contact_only=dict(amplitude_scale=.6,includes_source_power_cap=False,includes_1Vpp_ceiling=False,
                baseline_derived_numerical_limits=caps,actual_source_Vpp_intervals_V=[[.6,.6],[.6,.6]])),
            shared_original_square_cutoffs_V_m=dict(primary_mean=1.,primary_p10=.8),
            source_waveform=dict(source_Vpp_intervals_V=[[1.,1.],[1.,1.]]))
        before=copy.deepcopy((summary,condition));result=r.validate_selected_condition(summary,condition,ident)
        self.assertEqual(.6,result['SC2_skin8_amplitude_scale'])
        self.assertEqual([[.6,.6],[.6,.6]],result['SC2_skin8_source_Vpp_intervals_V'])
        self.assertTrue(result['coefficients_and_SC2_amplitude_frozen']);self.assertFalse(result['SC4_rematching_performed'])
        self.assertEqual(condition['coefficient_vectors'],result['raw_coefficient_vectors'])
        self.assertEqual(before,(summary,condition))
        for change in ('source','status','scale','selection'):
            s,c=copy.deepcopy(summary),copy.deepcopy(condition)
            if change=='source':c['source_case_id']='other-shape'
            elif change=='status':s['status']='running'
            elif change=='scale':c['normalizations']['skin_contact_only']['amplitude_scale']=float('nan')
            else:s['conditions'][0]['id']='not-selected'
            with self.subTest(change=change),self.assertRaises(ValueError):r.validate_selected_condition(s,c,ident)

    def test_failed_selection_context_preserves_evidence_and_charges_elapsed_without_jvm(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'data-native').mkdir();(root/'runtime').mkdir();run=root/'data-native/cloud-synthetic-rounded-sc4'
            ledger=dict(limit_seconds=13800,spent_seconds=7.,runs=[dict(stage='past',seconds=7.)])
            r.core.write(root/'runtime/task1-budget.json',ledger)
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r,'_caller_owns_execution_lock'),mock.patch.object(r.os,'sched_setaffinity'),\
                mock.patch.object(r.policy,'load_ledger',return_value=copy.deepcopy(ledger)),\
                mock.patch.object(r.policy,'effective_limit',return_value=13800),\
                mock.patch.object(r,'verify_context',side_effect=ValueError('synthetic selection drift')),mock.patch.object(r.subprocess,'Popen')as popen:
                with self.assertRaisesRegex(ValueError,'selection drift'):
                    r.prepare_rounded_sc4(run,root/'decision.json',root/'feedback.json')
            popen.assert_not_called();self.assertFalse(run.exists())
            self.assertTrue(run.with_name(run.name+'.preparation-failure.json').is_file())
            after=r.core.read(root/'runtime/task1-budget.json')
            self.assertGreater(after['spent_seconds'],7.);self.assertEqual(ledger['runs'],after['runs'][:1])


if __name__=='__main__':unittest.main()
