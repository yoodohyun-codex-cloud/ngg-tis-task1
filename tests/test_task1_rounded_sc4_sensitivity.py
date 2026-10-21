"""Synthetic SC2/SC4 fixed-drive sensitivity contracts; no native arrays or PDE."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
PRIMARY='primary_r5_depth15_20'
REGIONS=('total',PRIMARY,'supplemental_wholeXY_depth15_20','surface_0_5','primary_complement','supplemental_complement')
J95=('surface_J_RMS_p95_A_m2','bulk_skin_J_vector_RMS_p95_A_m2')
POWERS=('SC_power_W','contact_power_W','skin_SC_plus_dermis_power_W','source_power_W')


def regions_fixture(cells=12):
    result={}
    for index,region in enumerate(REGIONS):
        stats=dict(mean=4.5,p10=4.,p95=18. if region=='surface_0_5'else 23.,volume_m3=(1e-5,1e-7,1e-6,2e-6,9.9e-6,9e-6)[index],
            positive_weight_native_cells=cells,
            fixed_baseline_threshold_volume={PRIMARY+'_mean':dict(cutoff_V_m=4.,volume_m3=.8e-7),
                PRIMARY+'_p10':dict(cutoff_V_m=3.5,volume_m3=1.8e-7)})
        result[region]={metric:copy.deepcopy(stats)for metric in('maxTIS','fixedTIS','RMS')}
    return result


def modes_fixture(burden_key='actual_burdens',cells=12):
    result={}
    for index,(name,scale)in enumerate(zip(MODES,(1.,.8,1.2,.75,.6))):
        burdens={key:80.+index for key in(*J95,*POWERS)}
        burdens.update(surface_J_RMS_max_A_m2=85.+index,contact_voltage_RMS_max_V=.1,
            bulk_skin_J_vector_RMS_max_A_m2=95.+index)
        result[name]=dict(amplitude_scale=scale,regions=regions_fixture(cells),**{burden_key:burdens})
    return result


def baseline_fixture():
    regions=regions_fixture()
    regions[PRIMARY]['maxTIS'].update(mean=4.,p10=3.5)
    for region,p95 in(('surface_0_5',20.),('primary_complement',25.)):
        regions[region]['maxTIS']['p95']=p95
        regions[region]['maxTIS']['fixed_baseline_threshold_volume'][PRIMARY+'_mean']['volume_m3']=1e-7
        regions[region]['maxTIS']['fixed_baseline_threshold_volume'][PRIMARY+'_p10']['volume_m3']=2e-7
    return dict(normalizations={'skin_contact_only':dict(regions=regions,
        baseline_derived_numerical_limits={key:100. for key in(*J95,*POWERS)})})


class RoundedSC4SensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rounded_sc4_sensitivity_tested',ROOT/'tools/task1_rounded_sc4_sensitivity.py')
        cls.tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cls.tool;spec.loader.exec_module(cls.tool)

    def condition(self):
        # These are already normalized actual commands. Their amplitude is
        # intentionally not reset to unity and their phases are not all equal.
        vectors={3000:np.array([-.2-.6j,.01+.04j]),3030:np.array([.005-.03j,-.5j]),
            9000:np.zeros(2,complex),9090:np.zeros(2,complex)}
        return dict(coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in vectors.items()},
            source_waveform=dict(global_normalization=True,global_scale=.73)),vectors

    def test_decode_uses_exact_saved_complex_coefficients_without_new_source_normalization(self):
        condition,vectors=self.condition();before=copy.deepcopy(condition)
        decoded=self.tool.decode_coefficients(condition)
        self.assertEqual(set(decoded),{3000,3030,9000,9090})
        for f,c in vectors.items():np.testing.assert_array_equal(decoded[f],c)
        self.assertNotEqual(abs(decoded[3000][0]),1.)
        decoded[3000][0]=77.;self.assertEqual(condition,before)

    def test_decode_rejects_missing_or_extra_frequency_harmonics_bad_shape_and_nonfinite(self):
        for mutation in('missing','extra','harmonic','dimension','nan','realimag'):
            condition,_=self.condition();rows=condition['coefficient_vectors']
            if mutation=='missing':rows.pop('9090')
            elif mutation=='extra':rows['2000']=copy.deepcopy(rows['3000'])
            elif mutation=='harmonic':rows['9000']['imaginary'][1]=.001
            elif mutation=='dimension':rows['3000']['real'].append(0.)
            elif mutation=='nan':rows['3030']['real'][0]=float('nan')
            else:rows['3030'].pop('imaginary')
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):
                self.tool.decode_coefficients(condition)

    def test_five_fixed_modes_keep_exact_saved_amplitude_and_label_historical_matching_only(self):
        saved=modes_fixture('normalized_burdens');before=copy.deepcopy(saved)
        fixed=self.tool.fixed_sc2_modes(saved)
        self.assertEqual(set(fixed),set(MODES));self.assertEqual(saved,before)
        for mode,row in fixed.items():
            self.assertEqual(row['amplitude_scale'],saved[mode]['amplitude_scale'])
            self.assertEqual(row['historical_SC2_mode_id'],mode)
            self.assertEqual(row['normalization_scope'],'frozen_SC2_amplitude_no_SC4_rematch')
            self.assertIs(row['matches_SC2_current_on_SC4'],False)
            self.assertIs(row['matches_SC2_power_on_SC4'],False)

    def test_fixed_modes_reject_missing_mode_or_nonpositive_nonfinite_scale(self):
        for mutation in('missing','zero','negative','nan'):
            saved=modes_fixture()
            if mutation=='missing':saved.pop('equal_total_power')
            elif mutation=='zero':saved['skin_contact_only']['amplitude_scale']=0.
            elif mutation=='negative':saved['skin_contact_only']['amplitude_scale']=-1.
            else:saved['skin_contact_only']['amplitude_scale']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):
                self.tool.fixed_sc2_modes(saved)

    def test_roi_volumes_match_despite_different_native_cell_counts_and_statistics(self):
        sc2=regions_fixture(12);sc4=regions_fixture(24);sc4[PRIMARY]['maxTIS']['mean']*=1.005
        before=copy.deepcopy((sc2,sc4));proof=self.tool.validate_roi_volumes(sc2,sc4)
        self.assertTrue(proof['all_passed']);self.assertEqual(before,(sc2,sc4))

    def test_roi_volume_or_mask_set_changes_are_rejected_for_every_metric(self):
        for mutation in('missing','primary','surface','complement','fixedTIS','nonfinite'):
            sc2=regions_fixture();sc4=regions_fixture(24)
            if mutation=='missing':sc4.pop('supplemental_complement')
            else:
                region={'primary':PRIMARY,'surface':'surface_0_5','complement':'primary_complement'}.get(mutation,PRIMARY)
                metric='fixedTIS'if mutation=='fixedTIS'else'maxTIS'
                sc4[region][metric]['volume_m3']*=1.001
                if mutation=='nonfinite':sc4[region][metric]['volume_m3']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):
                self.tool.validate_roi_volumes(sc2,sc4)

    def test_identical_fixed_drive_passes_sensitivity_without_changing_baseline_or_modes(self):
        sc2=modes_fixture('normalized_burdens');sc4=modes_fixture(cells=24);baseline=baseline_fixture()
        before=copy.deepcopy((sc2,sc4,baseline));result=self.tool.sensitivity_checks(sc2,sc4,baseline)
        self.assertTrue(result['all_passed']);self.assertTrue(result['screen_status_no_flip'])
        self.assertEqual(before,(sc2,sc4,baseline));self.assertTrue(result['checks'])
        self.assertTrue(all(row['passed']for row in result['checks']))

    def test_target_one_percent_gate_uses_absolute_change_in_both_raw_and_saved_skin_modes(self):
        for mode in('raw_1Vpp','skin_contact_only'):
            for metric in('mean','p10'):
                for direction in(-1,1):
                    sc2=modes_fixture();sc4=copy.deepcopy(sc2)
                    sc4[mode]['regions'][PRIMARY]['maxTIS'][metric]*=1+direction*.009
                    self.assertTrue(self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())['all_passed'])
                    sc4[mode]['regions'][PRIMARY]['maxTIS'][metric]=sc2[mode]['regions'][PRIMARY]['maxTIS'][metric]*(1+direction*.011)
                    with self.subTest(mode=mode,metric=metric,direction=direction):
                        self.assertFalse(self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())['all_passed'])

    def test_off_target_p95_two_percent_gate_is_symmetric_and_keeps_original_screen_separate(self):
        for mode in('raw_1Vpp','skin_contact_only'):
            for region in('surface_0_5','primary_complement'):
                for direction in(-1,1):
                    sc2=modes_fixture();sc4=copy.deepcopy(sc2)
                    sc4[mode]['regions'][region]['maxTIS']['p95']*=1+direction*.019
                    self.assertTrue(self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())['all_passed'])
                    sc4[mode]['regions'][region]['maxTIS']['p95']=sc2[mode]['regions'][region]['maxTIS']['p95']*(1+direction*.021)
                    result=self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())
                    with self.subTest(mode=mode,region=region,direction=direction):
                        self.assertFalse(result['all_passed']);self.assertTrue(result['screen_status_no_flip'])

    def test_j95_and_four_power_two_percent_gates_apply_even_when_below_original_caps(self):
        for mode in('raw_1Vpp','skin_contact_only'):
            for key in(*J95,*POWERS):
                for direction in(-1,1):
                    sc2=modes_fixture('normalized_burdens');sc4=modes_fixture()
                    sc4[mode]['actual_burdens'][key]*=1+direction*.019
                    self.assertTrue(self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())['all_passed'])
                    sc4[mode]['actual_burdens'][key]=sc2[mode]['normalized_burdens'][key]*(1+direction*.021)
                    self.assertLess(sc4[mode]['actual_burdens'][key],100.)
                    result=self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())
                    with self.subTest(mode=mode,key=key,direction=direction):self.assertFalse(result['all_passed'])

    def test_old_eight_screen_status_flip_fails_even_inside_sensitivity_percent_limits(self):
        for improvement in(False,True):
            sc2=modes_fixture();sc4=copy.deepcopy(sc2)
            for mode in('raw_1Vpp','skin_contact_only'):
                sc2[mode]['regions'][PRIMARY]['maxTIS']['mean']=4.0002 if not improvement else 3.9998
                sc4[mode]['regions'][PRIMARY]['maxTIS']['mean']=3.9998 if not improvement else 4.0002
            result=self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())
            with self.subTest(improvement=improvement):
                self.assertFalse(result['all_passed']);self.assertFalse(result['screen_status_no_flip'])

    def test_unchanged_old_screen_failure_is_not_relabelled_as_new_sensitivity_failure_or_adoption(self):
        sc2=modes_fixture();sc4=copy.deepcopy(sc2)
        for mode in('raw_1Vpp','skin_contact_only'):
            for record in(sc2,sc4):record[mode]['regions'][PRIMARY]['maxTIS'].update(mean=3.5,p10=3.)
        result=self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())
        self.assertTrue(result['all_passed']);self.assertTrue(result['screen_status_no_flip'])

    def test_nonselected_modes_are_historical_diagnostics_and_never_silently_rematched(self):
        sc2=modes_fixture();sc4=copy.deepcopy(sc2)
        for mode in('equal_total_source_output_RMS_sum','equal_total_power','legacy_composite_full_skin'):
            sc4[mode]['actual_burdens']['source_power_W']*=2
        self.assertTrue(self.tool.sensitivity_checks(sc2,sc4,baseline_fixture())['all_passed'])


if __name__=='__main__':unittest.main()
