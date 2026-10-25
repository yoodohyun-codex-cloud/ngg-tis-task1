"""Pure analytic unit-test SOURCE; finite owner alone may execute these checks."""
import math
import unittest
import screen_metrics as f


def np_for_test():
    import numpy as np
    return np


def electrical_fixture(amplitude=1.):
    return dict(source_Vpp_each=1.*amplitude,source_current_RMS_by_output_A=[.001*amplitude,.0012*amplitude],
                sum_output_current_RMS_A_bookkeeping=.0022*amplitude,source_power_W=.3*amplitude**2,
                layers_power_W=dict(sc=.01*amplitude**2,dermis=.09*amplitude**2,fat=.02*amplitude**2,muscle=.03*amplitude**2),
                SC_power_W=.01*amplitude**2,skin_power_W=.1*amplitude**2,contact_power_W=.05*amplitude**2,
                source_resistor_power_W=.15*amplitude**2,contact_normal_J_RMS_max_A_m2=2.*amplitude,
                contact_normal_J_RMS_P95_A_m2=1.*amplitude,contact_voltage_RMS_max_V=.01*amplitude,
                skin_vector_J_RMS_max_A_m2=3.*amplitude,skin_vector_J_RMS_P95_A_m2=2.*amplitude)


def evaluate_fixture(np):
    layer=np.asarray([0,1,1,2,2,3,3,3]);z=np.asarray([.05,1.,4.,6.,9.,12.,16.,18.])
    volume=np.full(8,1e-9);grid=np.column_stack((np.zeros(8),np.zeros(8),z,layer,volume))
    target=volume*((z>=15)&(z<=20));surface=volume*(z<5);sub=volume*((z>=5)&(z<10))
    weights=dict(total=volume,target=target,surface_0_5=surface,subsurface_5_10=sub,
                 remaining=volume-target-surface-sub,off_target=volume-target)
    a=np.tile(np.asarray([1.+.5j,0.,0.]),(8,1));b=a/2.
    return grid,weights,a,b,np.full(4,.2+.03j)


def normalization_fixture(amplitude):
    electrical=electrical_fixture(amplitude)
    # The registered source remains 1 Vpp for the raw candidate; electrical
    # quantities below represent a different transfer response at that drive.
    electrical['source_Vpp_each']=1.
    regions={}
    for region in('target','surface_0_5','surface_without_SC','off_target','total'):
        regions[region]=dict(statistics={})
        for metric in('maxTIS','RMS','X_TIS','Y_TIS','Z_TIS'):
            regions[region]['statistics'][metric]={key:2.*amplitude for key in('mean','p10','median','p95','p99','max','std')}
    return dict(electrical=electrical,regions=regions)


class ScreenMetricsTests(unittest.TestCase):
    def test_shared_direction_count_order_and_unit_norms(self):
        np=np_for_test();directions=f.directions(np)
        self.assertEqual(directions.shape,(2074,3))
        np.testing.assert_allclose(np.linalg.norm(directions,axis=1),1.,rtol=0,atol=1e-12)
        np.testing.assert_allclose(directions[0],np.asarray([-1.,-1.,-1.])/math.sqrt(3.),rtol=0,atol=1e-15)

    def test_volume_weighted_inverse_ecdf_std_and_representative_extrema(self):
        np=np_for_test();grid=np.zeros((3,5));grid[:,0]=[10.,20.,30.]
        stats=f.weighted_stats(np,np.asarray([3.,1.,2.]),np.asarray([.1,.8,.1]),grid)
        self.assertAlmostEqual(stats['mean'],1.3)
        self.assertEqual(stats['p10'],1.)
        self.assertEqual(stats['median'],1.)
        self.assertEqual(stats['p95'],3.)
        self.assertEqual(stats['p99'],3.)
        self.assertEqual(stats['maximum_xyz_mm'],[10.,0.,0.])
        self.assertAlmostEqual(stats['std'],math.sqrt(.1*(3.-1.3)**2+.8*(1.-1.3)**2+.1*(2.-1.3)**2))

    def test_two_carrier_fields_complete_sampled_max_waveform_and_derived_current(self):
        np=np_for_test();grid,w,a,b,g=evaluate_fixture(np)
        result=f.evaluate(np,grid,w,a,b,g,g,electrical_fixture())
        arrays=result['arrays'];summary=result['summary']
        expected_am=2.*abs(.5+.25j);expected_rms=math.sqrt((abs(1.+.5j)**2+abs(.5+.25j)**2)/2.)
        np.testing.assert_allclose(arrays['AM_max2074'],expected_am,rtol=1e-10,atol=1e-10)
        np.testing.assert_allclose(arrays['AM_x'],expected_am,rtol=1e-10,atol=1e-10)
        np.testing.assert_array_equal(arrays['AM_y'],np.zeros(8))
        np.testing.assert_allclose(arrays['carrier_RMS'],expected_rms,rtol=1e-10,atol=1e-10)
        np.testing.assert_allclose(arrays['Jtotal_vector_RMS'],abs(.2+.03j)*expected_rms,rtol=1e-10,atol=1e-10)
        self.assertTrue(summary['directional_search']['completed'])
        self.assertEqual(summary['waveform_checks']['status'],'passed')
        self.assertAlmostEqual(summary['regions']['target']['volume_m3'],2e-9)
        self.assertAlmostEqual(summary['regions']['surface_without_SC']['volume_m3'],2e-9)
        self.assertFalse(summary['holds']['candidate_adopted'])

    def test_expired_deadline_never_returns_partial_angular_maximum(self):
        np=np_for_test()
        with self.assertRaises(TimeoutError):f.evaluate(np,None,None,None,None,None,None,{},deadline=0.)

    def test_separate_normalizations_preserve_raw_voltage_absolute_target(self):
        candidate=normalization_fixture(2.);baseline=normalization_fixture(1.)
        result=f.normalize(candidate,baseline);rows=result['comparisons']
        self.assertEqual(rows['same_source_voltage']['amplitude_scale'],1.)
        self.assertEqual(rows['same_source_voltage']['absolute_ROI_fields_V_m']['target']['maxTIS']['mean'],4.)
        for key in('same_sum_output_RMS_current_bookkeeping','same_source_real_power','joint_eight_surface_contact_burden_caps'):
            self.assertEqual(rows[key]['amplitude_scale'],.5)
            self.assertEqual(rows[key]['absolute_ROI_fields_V_m']['target']['maxTIS']['mean'],2.)
        self.assertFalse(result['simultaneous_equal_current_power_burden_assumed'])
        self.assertEqual(candidate['regions']['target']['statistics']['maxTIS']['mean'],4.)

    def test_joint_eight_names_limiting_contact_voltage_and_retained_absolute_am(self):
        candidate=normalization_fixture(2.);baseline=normalization_fixture(1.)
        candidate['electrical']['contact_voltage_RMS_max_V']=.04
        row=f.normalize(candidate,baseline)['comparisons']['joint_eight_surface_contact_burden_caps']
        self.assertEqual(row['amplitude_scale'],.25)
        self.assertEqual(row['limiting_constraints'],['contact_voltage_RMS_max_V'])
        self.assertEqual(row['absolute_ROI_fields_V_m']['target']['maxTIS']['mean'],1.)
        self.assertEqual(len(row['individual_amplitude_caps']),8)

    def test_missing_electrical_inputs_are_not_invented(self):
        candidate=normalization_fixture(2.);baseline=normalization_fixture(1.)
        del candidate['electrical']['SC_power_W']
        result=f.normalize(candidate,baseline)
        self.assertEqual(result['status'],'not_run_missing_normalization_inputs')
        self.assertEqual(result['missing_keys'],['SC_power_W'])


if __name__=='__main__':unittest.main()
