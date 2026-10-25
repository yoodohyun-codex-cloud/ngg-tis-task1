"""Pure complex-contact uncertainty contracts; no native arrays or research runs."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
FREQUENCIES=(3000,3030,9000,9090)
MODES=('raw_1Vpp','equal_total_source_output_RMS_sum','equal_total_power','skin_contact_only','legacy_composite_full_skin')
PRIMARY='primary_r5_depth15_20'
REGIONS=('total',PRIMARY,'supplemental_wholeXY_depth15_20','surface_0_5','primary_complement','supplemental_complement')


def config_fixture():
    result={'mask.path':'/synthetic/old-mask.csv','mask.sha256':'a'*64,'h_mm':'0.625','validation.sc_cells':'4',
        'bulk.counts':'14,14,40','channels':'2','frequencies':'3000,3030,9000,9090',
        'muscle.sigma':'.4','dermis.epsilon_r':'1000','pad.0.shape':'masked_face_union',
        'pad.0.x_mm':'-10','pad.0.y_mm':'-10','pad.0.width_mm':'17.5','pad.0.analytic_area_mm2':'225',
        'source.resistance_ohm':'50','Rs_subtracted_once':'true','specific_Z_area_unit':'ohm_m2'}
    for index,f in enumerate(FREQUENCIES):
        result[f'z.{f}.re']=format(.001*(index+1),'.17g')
        result[f'z.{f}.im']=format(-.0002*(index+1),'.17g')
    return result


def scaled_config(before,factor):
    result=copy.deepcopy(before)
    for f in FREQUENCIES:
        for component in('re','im'):result[f'z.{f}.{component}']=format(float(before[f'z.{f}.{component}'])*factor,'.17g')
    return result


def regions_fixture(cells=16):
    result={}
    for index,region in enumerate(REGIONS):
        stats=dict(mean=4.5,p10=4.,p95=18. if region=='surface_0_5'else 23.,p99=24.,max=30.,min=3.,std=.5,CV=.2,
            volume_m3=(1e-5,1e-7,1e-6,2e-6,9.9e-6,9e-6)[index],positive_weight_native_cells=cells,
            fixed_baseline_threshold_volume={PRIMARY+'_mean':dict(cutoff_V_m=4.,volume_m3=.8e-7),
                PRIMARY+'_p10':dict(cutoff_V_m=3.5,volume_m3=1.8e-7)})
        result[region]={metric:copy.deepcopy(stats)for metric in('maxTIS','fixedTIS','RMS')}
    return result


def modes_fixture():
    result={}
    for index,(name,scale)in enumerate(zip(MODES,(1.,.8,1.2,.75,.6))):
        result[name]=dict(amplitude_scale=scale,regions=regions_fixture(),
            actual_burdens={'surface_J_RMS_max_A_m2':80.+index,'surface_J_RMS_p95_A_m2':70.+index,
                'contact_voltage_RMS_max_V':.1,'SC_power_W':.01,'contact_power_W':.02,
                'skin_SC_plus_dermis_power_W':.03,'source_power_W':.1,
                'bulk_skin_J_vector_RMS_max_A_m2':90.+index,'bulk_skin_J_vector_RMS_p95_A_m2':60.+index})
    return result


def baseline_fixture():
    regions=regions_fixture()
    regions[PRIMARY]['maxTIS'].update(mean=4.,p10=3.5)
    for region,p95 in(('surface_0_5',20.),('primary_complement',25.)):
        regions[region]['maxTIS']['p95']=p95
        regions[region]['maxTIS']['fixed_baseline_threshold_volume'][PRIMARY+'_mean']['volume_m3']=1e-7
        regions[region]['maxTIS']['fixed_baseline_threshold_volume'][PRIMARY+'_p10']['volume_m3']=2e-7
    return dict(normalizations={'skin_contact_only':dict(regions=regions)})


class RoundedContactSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rounded_contact_sensitivity_tested',ROOT/'tools/task1_rounded_contact_sensitivity.py')
        cls.tool=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cls.tool;spec.loader.exec_module(cls.tool)

    def test_both_specific_impedance_components_at_every_frequency_are_scaled_once(self):
        before=config_fixture()
        for factor in(.5,2.):
            after=scaled_config(before,factor);original=copy.deepcopy((before,after))
            self.tool.validate_contact_config(before,after,factor)
            self.assertEqual(original,(before,after))
            for f in FREQUENCIES:
                old=complex(float(before[f'z.{f}.re']),float(before[f'z.{f}.im']))
                new=complex(float(after[f'z.{f}.re']),float(after[f'z.{f}.im']))
                self.assertAlmostEqual(new.real/old.real,factor)
                self.assertAlmostEqual(new.imag/old.imag,factor)
                self.assertAlmostEqual((new/old).imag,0.)
            self.assertEqual(before['Rs_subtracted_once'],after['Rs_subtracted_once'])
            self.assertEqual(before['specific_Z_area_unit'],after['specific_Z_area_unit'])

    def test_mask_path_alias_is_permitted_only_with_identical_physical_mask_sha(self):
        before=config_fixture();after=scaled_config(before,.5);after['mask.path']='/synthetic/portable-copy.csv'
        self.tool.validate_contact_config(before,after,.5)
        after['mask.sha256']='b'*64
        with self.assertRaises(ValueError):self.tool.validate_contact_config(before,after,.5)

    def test_no_second_rs_subtraction_area_conversion_or_single_component_rescaling_is_allowed(self):
        for mutation in('real_only','imag_only','Rs','area_conversion','missing','extra'):
            before=config_fixture();after=scaled_config(before,.5)
            if mutation=='real_only':after['z.3030.im']=before['z.3030.im']
            elif mutation=='imag_only':after['z.3030.re']=before['z.3030.re']
            elif mutation=='Rs':after['z.3000.re']=str(float(after['z.3000.re'])-.0001)
            elif mutation=='area_conversion':after['z.9000.re']=str(float(after['z.9000.re'])*225)
            elif mutation=='missing':after.pop('z.9090.im')
            else:after['z.2000.re']='.001'
            with self.subTest(mutation=mutation),self.assertRaises((ValueError,KeyError)):
                self.tool.validate_contact_config(before,after,.5)

    def test_sc4_mesh_physics_shapes_positions_sources_and_units_cannot_change_with_contact_factor(self):
        for key,value in(('h_mm','1.25'),('validation.sc_cells','2'),('channels','4'),('frequencies','2000,2010'),
                ('bulk.counts','14,14,41'),('muscle.sigma','.8'),('dermis.epsilon_r','1100'),
                ('pad.0.x_mm','-9.375'),('pad.0.shape','rectangle'),('pad.0.width_mm','15'),
                ('pad.0.analytic_area_mm2','224'),('source.resistance_ohm','0'),
                ('Rs_subtracted_once','twice'),('specific_Z_area_unit','ohm_cm2')):
            before=config_fixture();after=scaled_config(before,2.);after[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.tool.validate_contact_config(before,after,2.)
        for factor in(0.,-.5,1.,1.5,float('nan'),float('inf'),True):
            with self.subTest(factor=factor),self.assertRaises(ValueError):
                self.tool.validate_contact_config(config_fixture(),scaled_config(config_fixture(),.5),factor)

    def test_selected_actual_source_coefficients_keep_phase_and_common_scale_without_new_normalization(self):
        coefficients={3000:np.array([-.2-.6j,.01+.04j]),3030:np.array([.005-.03j,-.5j]),
            9000:np.zeros(2,complex),9090:np.zeros(2,complex)}
        condition=dict(coefficient_vectors={str(f):dict(real=c.real.tolist(),imaginary=c.imag.tolist())for f,c in coefficients.items()})
        before=copy.deepcopy(condition);decoded=self.tool.decode_coefficients(condition)
        for f,c in coefficients.items():np.testing.assert_array_equal(decoded[f],c)
        self.assertNotEqual(abs(decoded[3000][0]),1.);decoded[3030][0]=77j;self.assertEqual(before,condition)

    def test_all_five_frozen_sc2_amplitudes_stay_historical_and_no_longer_assert_current_power_matches(self):
        saved=modes_fixture();before=copy.deepcopy(saved);fixed=self.tool.fixed_sc2_modes(saved)
        self.assertEqual(set(fixed),set(MODES));self.assertEqual(before,saved)
        for name,row in fixed.items():
            self.assertEqual(row['amplitude_scale'],saved[name]['amplitude_scale'])
            self.assertEqual(row['historical_SC2_mode_id'],name)
            self.assertEqual(row['normalization_scope'],'frozen_SC2_amplitude_no_SC4_rematch')
            self.assertFalse(row['matches_SC2_current_on_SC4']);self.assertFalse(row['matches_SC2_power_on_SC4'])

    def test_all_physical_roi_volumes_remain_equal_without_requiring_same_native_cell_counts(self):
        nominal=regions_fixture(16);changed=regions_fixture(32)
        self.assertTrue(self.tool.validate_roi_volumes(nominal,changed)['all_passed'])
        changed[PRIMARY]['RMS']['volume_m3']*=1.001
        with self.assertRaises(ValueError):self.tool.validate_roi_volumes(nominal,changed)



    def comparison_rows(self,result):
        return {row['historical_SC2_mode_id']:row for row in result['mode_comparisons']}

    def test_large_contact_changes_are_reported_without_an_invented_percent_pass_gate_or_adoption(self):
        nominal=modes_fixture();condition=copy.deepcopy(nominal);baseline=baseline_fixture()
        for mode in MODES:
            condition[mode]['regions'][PRIMARY]['maxTIS']['mean']*=1.5
            condition[mode]['regions']['surface_0_5']['maxTIS']['p95']*=1.5
            condition[mode]['actual_burdens']['SC_power_W']*=1.5
            condition[mode]['actual_burdens']['contact_power_W']*=.4
        before=copy.deepcopy((nominal,condition,baseline));result=self.tool.contact_comparisons(nominal,condition,baseline)
        self.assertEqual(result['status'],'contact_uncertainty_comparison_not_validation')
        self.assertNotIn('all_passed',result);self.assertNotIn('candidate_adopted',result);self.assertNotIn('adopted',result)
        rows=self.comparison_rows(result);self.assertEqual(set(rows),set(MODES))
        for mode,row in rows.items():
            self.assertEqual(row['amplitude_scale'],nominal[mode]['amplitude_scale'])
            metrics={m['name']:m for m in row['metrics']}
            power=metrics['SC_power_W'];self.assertAlmostEqual(power['signed_delta'],.005)
            self.assertAlmostEqual(power['relative_change'],.5);self.assertAlmostEqual(power['absolute_relative_change'],.5)
            contact=metrics['contact_power_W'];self.assertAlmostEqual(contact['relative_change'],-.6)
            self.assertAlmostEqual(contact['absolute_relative_change'],.6)
            for metric in row['metrics']:
                self.assertNotIn('passed',metric);self.assertNotIn('relative_limit',metric)
            self.assertTrue(any(c['changed']for c in row['screen_status_comparisons']))
        self.assertEqual(before,(nominal,condition,baseline))

    def test_zero_nominal_denominators_report_none_instead_of_infinity_or_sensitivity_success(self):
        nominal=modes_fixture();condition=copy.deepcopy(nominal)
        for mode in MODES:
            nominal[mode]['actual_burdens']['SC_power_W']=0.
            condition[mode]['actual_burdens']['SC_power_W']=.02
            nominal[mode]['actual_burdens']['source_power_W']=0.
            condition[mode]['actual_burdens']['source_power_W']=0.
        result=self.tool.contact_comparisons(nominal,condition,baseline_fixture())
        for row in result['mode_comparisons']:
            metrics={m['name']:m for m in row['metrics']}
            for name in('SC_power_W','source_power_W'):
                self.assertIsNone(metrics[name]['relative_change']);self.assertIsNone(metrics[name]['absolute_relative_change'])
            self.assertAlmostEqual(metrics['SC_power_W']['signed_delta'],.02)
            self.assertEqual(metrics['source_power_W']['signed_delta'],0.)
        self.assertNotIn('all_passed',result)

    def test_original_eight_gate_status_changes_are_reported_both_directions_without_validation_promotion(self):
        for improvement in(False,True):
            nominal=modes_fixture();condition=copy.deepcopy(nominal)
            for mode in MODES:
                nominal[mode]['regions'][PRIMARY]['maxTIS']['mean']=4.0002 if not improvement else 3.9998
                condition[mode]['regions'][PRIMARY]['maxTIS']['mean']=3.9998 if not improvement else 4.0002
            result=self.tool.contact_comparisons(nominal,condition,baseline_fixture())
            self.assertEqual(result['status'],'contact_uncertainty_comparison_not_validation')
            for row in result['mode_comparisons']:
                checks=row['screen_status_comparisons'];self.assertEqual(len(checks),8)
                changed=[c for c in checks if c['changed']]
                self.assertEqual(len(changed),1)
                self.assertNotEqual(changed[0]['nominal_passed'],changed[0]['condition_passed'])
                self.assertEqual(changed[0]['condition_passed'],improvement)
            self.assertNotIn('all_passed',result);self.assertNotIn('candidate_adopted',result)

    def test_contact_comparison_cannot_silently_use_a_rematched_condition_amplitude(self):
        nominal=modes_fixture();condition=copy.deepcopy(nominal)
        condition['equal_total_power']['amplitude_scale']*=1.1
        with self.assertRaises(ValueError):self.tool.contact_comparisons(nominal,condition,baseline_fixture())


if __name__=='__main__':unittest.main()
