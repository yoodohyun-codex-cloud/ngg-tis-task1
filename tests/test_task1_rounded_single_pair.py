"""Synthetic nominal-SC2 cached C1 comparison checks; no native inputs or PDE."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


def probes():
    return dict(status='complete',measurements=[dict(id=f'{d}-{p}-{a}',RMS_V=.01,Vpp_lower_V=.02,Vpp_upper_V=.020000001,
        fundamental_fixed_axis_envelope=dict(variation_range_V=0.),axis=a,depth_from_skin_surface_mm=d,position=p,tip_gap_mm=5.)
        for d in(5,10,15,20)for p in('centre','x_plus','x_minus','y_plus','y_minus')for a in('X','Y')])


def metrics():
    return dict(source_current_spectrum=[dict(frequency_Hz=3000,real_A=[.01],imaginary_A=[0.]),dict(frequency_Hz=3030,real_A=[.01],imaginary_A=[0.])],
        loaded_metal_voltage_spectrum=[dict(frequency_Hz=3000,real_V=[.5],imaginary_V=[0.]),dict(frequency_Hz=3030,real_V=[-1.],imaginary_V=[0.])],
        source_power_W=.0025,source_resistor_power_W=.005,source_current_RMS_by_output_mA=[10.])


class RoundedSinglePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rounded_single_pair_tested',ROOT/'tools/task1_rounded_single_pair.py')
        cls.tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.tool)

    def test_exact_nominal_sc2_three_reference_ids_and_modes_give_twelve_matches(self):
        self.assertEqual(self.tool.REFERENCE_IDS,('original-SC2-square3h','rounded-SC2-square3h','rounded-SC2-opt-e7b3bf639935'))
        self.assertEqual(self.tool.MODES,('raw','skin_contact_only'))
        rows=[]
        for ref in self.tool.REFERENCE_IDS:
            for mode in self.tool.MODES:
                rows.extend((ref,mode,k)for k in self.tool.target_matches(6.,8.,2.,4.,dict(source_power_W=.1,source_current_RMS_mA=1.),probes()))
        self.assertEqual(len(set(rows)),12)

    def test_population_weighted_moments_recover_energy_rms_without_using_mean_rms(self):
        stat=dict(mean=2.5,std=math.sqrt(.75),volume_m3=1e-7)
        result=self.tool.energy_rms_from_statistics(stat)
        self.assertAlmostEqual(result,self.tool.weighted_energy_rms([1.,3.],[.25,.75]),places=14)
        self.assertAlmostEqual(result,math.sqrt(7),places=14);self.assertNotEqual(result,stat['mean'])
        for bad in(dict(mean=-1.,std=1.,volume_m3=1.),dict(mean=1.,std=float('nan'),volume_m3=1.),dict(mean=1.,std=0.,volume_m3=0.)):
            with self.assertRaises(ValueError):self.tool.energy_rms_from_statistics(bad)

    def test_center_and_roi_matches_keep_different_source_voltage_and_power_scaling(self):
        raw=dict(source_power_W=.1,contact_power_W=.02,contact_voltage_RMS_max_V=.03,source_current_RMS_mA=2.)
        before=copy.deepcopy(raw);probe=probes();saved=copy.deepcopy(probe)
        result=self.tool.target_matches(6.,8.,2.,4.,raw,probe)
        for key,scale in(('centre20_E_RMS',3.),('ROI_energy_RMS',2.)):
            row=result[key];self.assertEqual(row['required_source_Vpp'],scale)
            self.assertAlmostEqual(row['burdens']['source_power_W'],.1*scale**2)
            self.assertAlmostEqual(row['burdens']['contact_voltage_RMS_max_V'],.03*scale)
            self.assertEqual(len(row['unloaded_probe40']),40)
            self.assertIn('zero temporal envelope variation',row['single_frequency_modulation_definition'])
        self.assertEqual(before,raw);self.assertEqual(saved,probe)

    def test_one_output_signed_power_preserves_negative_frequency_contributions(self):
        raw=metrics();saved=copy.deepcopy(raw);result=self.tool.single_signed_power(raw,2.)
        self.assertEqual(result['physical_outputs'],1);self.assertAlmostEqual(result['ideal_source_power_W'],.01)
        self.assertAlmostEqual(result['source_resistor_loss_W'],.02);self.assertAlmostEqual(result['output_current_RMS_mA'],20.)
        self.assertLess(result['spectrum'][1]['ideal_source_power_W'],0.)
        self.assertLess(result['metal_delivered_power_W'],0.);self.assertEqual(raw,saved)
        self.assertFalse(result['hardware_absorption_and_compliance_validated'])

    def test_single_output_power_rejects_two_outputs_or_mismatched_saved_totals(self):
        raw=metrics();raw['source_power_W']+=.00001
        with self.assertRaises(ValueError):self.tool.single_signed_power(raw)
        raw=metrics();raw['source_current_spectrum'][0]['real_A']=[.01,0.]
        with self.assertRaises(ValueError):self.tool.single_signed_power(raw)

    def test_sc4_contact_scaled_or_extra_outputs_cannot_alias_nominal_sc2_scope(self):
        case=dict(circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'},source_resistance_ohm=50),
            source_coating_nm=10,source_Rs_fit_window_Hz=500,expected_pad_areas_m2=[225e-6]*4)
        mesh=dict(sc_cells=2,h_xy_mm=.625,bulk_layer_counts=[14,14,40],cells=351680)
        self.tool.validate_sc2_scope(case,mesh)
        for kind in('sc4','outputs','coating','area'):
            c,m=copy.deepcopy(case),copy.deepcopy(mesh)
            if kind=='sc4':m['sc_cells']=4;m['cells']=361728
            elif kind=='outputs':c['circuit']['n_outputs']=4
            elif kind=='coating':c['source_coating_nm']=20
            else:c['expected_pad_areas_m2'][0]=224e-6
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.tool.validate_sc2_scope(c,m)

    def test_footprints_include_return_and_remain_450_versus_900_mm2(self):
        a=self.tool.reference_footprint([225e-6]*2,dict(n_pads=2,n_outputs=1,n_return_nodes=1))
        b=self.tool.reference_footprint([225e-6]*4,dict(n_pads=4,n_outputs=2,n_return_nodes=1))
        self.assertAlmostEqual(a['total_contact_area_mm2'],450.);self.assertAlmostEqual(b['total_contact_area_mm2'],900.)
        self.assertEqual(a['physical_pads'],2);self.assertEqual(a['independent_outputs'],1)
        self.assertEqual(self.tool.OUTPUT_BOUND_BYTES,64*1024**2)


if __name__=='__main__':unittest.main()
