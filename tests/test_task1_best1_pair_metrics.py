"""Pure synthetic best1/C1 metadata and algebra tests; no files or research runs."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
SPEC=importlib.util.spec_from_file_location('best1_pair_metrics_tested',ROOT/'tools/task1_best1_pair_metrics.py')
TOOL=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(TOOL)
DEGREES={'surface_J_RMS_max_A_m2':1,'surface_J_RMS_p95_A_m2':1,'contact_voltage_RMS_max_V':1,
    'SC_power_W':2,'contact_power_W':2,'source_power_W':2,'bulk_skin_J_vector_RMS_max_A_m2':1,
    'bulk_skin_J_vector_RMS_p95_A_m2':1,'skin_SC_plus_dermis_power_W':2}


def fixture():
    raw=dict(contact_J_RMS_max_A_m2=10.,contact_J_RMS_p95_A_m2=5.,contact_voltage_RMS_max_V=.01,
        SC_power_W=.00002,contact_power_W=.00001,source_power_W=.0005,bulk_skin_J_RMS_max_A_m2=8.,
        bulk_skin_J_RMS_p95_A_m2=4.,skin_SC_plus_dermis_power_W=.0003,source_resistor_power_W=.0001,
        source_current_RMS_mA=math.sqrt(2),source_current_peak_mA=2.,loaded_metal_Vpp=.8)
    unit=dict(case_id='baseline-square15-C1pair0-xy80',frequency_Hz=3000,raw_source_Vpp=1.,
        raw_centre20_E_RMS_V_m=2.,raw_ROI_energy_RMS_V_m=4.,raw_burdens=raw,
        circuit=dict(n_pads=2,n_outputs=1,n_return_nodes=1,source_peak_V=.5,source_resistance_ohm=50,
            pad_to_node={'0':'out0','1':'GND'}),
        unloaded_probe_reference=dict(path='/synthetic/original-C1-probes.json',condition_id='original-C1-sine'))
    electrical=dict(source_current_spectrum=[dict(frequency_Hz=3000,real_A=[0.],imaginary_A=[-.002])],
        loaded_metal_voltage_spectrum=[dict(frequency_Hz=3000,real_V=[0.],imaginary_V=[-.4])],
        source_power_W=.0005,source_resistor_power_W=.0001,source_current_RMS_by_output_mA=[math.sqrt(2)])
    burdens=dict(surface_J_RMS_max_A_m2=12.,surface_J_RMS_p95_A_m2=6.,contact_voltage_RMS_max_V=.015,
        SC_power_W=.00004,contact_power_W=.00003,source_power_W=.003,bulk_skin_J_vector_RMS_max_A_m2=10.,
        bulk_skin_J_vector_RMS_p95_A_m2=5.,skin_SC_plus_dermis_power_W=.0005)
    reference=dict(id='rounded-expand-f35b23a22166',source_case_id='rounded-fullface225-xy80',
        source_circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1,source_resistance_ohm=50,
            pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'}),
        source_waveform=dict(source_Vpp_intervals_V=[[.8,1.],[1.5,2.]]),
        electrical_metrics=dict(target20_total_E_RMS_V_m=6.),normalizations={},
        layer_contact_source_losses=dict(metrics=dict(SC_power_W=.00004,dermis_power_W=.00046,
            skin_SC_plus_dermis_power_W=.0005,skin_power_W=.00007,source_power_W=.003)))
    for name,scale in(('raw_1Vpp',1.),('skin_contact_only',2.)):
        reference['normalizations'][name]=dict(amplitude_scale=scale,
            regions={TOOL.PRIMARY:dict(RMS=dict(mean=6.*scale,std=8.*scale,volume_m3=1e-7))},
            normalized_burdens={key:value*scale**DEGREES[key]for key,value in burdens.items()},
            source_output_RMS_by_output_mA=[3.*scale,4.*scale],
            actual_source_Vpp_intervals_V=[[.8*scale,scale],[1.5*scale,2.*scale]])
    return reference,unit,electrical


class Best1PairMetricsTests(unittest.TestCase):
    def test_energy_rms_is_hypot_population_stats_and_point_roi_matches_are_independent(self):
        args=fixture();before=copy.deepcopy(args);report=TOOL.build_comparison(*args)
        self.assertEqual(args,before);self.assertEqual(report['reference']['candidate_id'],'rounded-expand-f35b23a22166')
        for mode,scale in(('raw_1Vpp',1.),('skin_contact_only',2.)):
            row=report['modes'][mode]
            self.assertEqual(row['target_ROI_energy_RMS_V_m'],10.*scale)
            self.assertNotEqual(row['target_ROI_energy_RMS_V_m'],6.*scale)
            self.assertEqual(row['target_centre20_E_RMS_V_m'],6.*scale)
            self.assertEqual(row['matches']['ROI_energy_RMS']['required_source_Vpp'],2.5*scale)
            self.assertEqual(row['matches']['centre20_E_RMS']['required_source_Vpp'],3.*scale)
            for match in row['matches'].values():
                self.assertIsNone(match['unloaded_probe40'])
                self.assertEqual(match['raw_probe_reference'],args[1]['unloaded_probe_reference'])
                self.assertEqual(match['fundamental_envelope_variation_V_m'],0.)
        self.assertEqual(report['geometry_comparison']['TIS_total_contact_area_mm2'],900.)
        self.assertEqual(report['geometry_comparison']['C1_total_contact_area_mm2'],450.)
        self.assertFalse(report['geometry_comparison']['same_pad_shape']);self.assertFalse(report['candidate_adopted'])

    def test_linear_j_current_voltage_quadratic_power_ratios_use_max_output_interval_not_sum(self):
        reference,unit,electrical=fixture();report=TOOL.build_comparison(reference,unit,electrical)
        for name,scale in(('raw_1Vpp',1.),('skin_contact_only',2.)):
            row=report['modes'][name]
            for criterion,k in(('ROI_energy_RMS',2.5*scale),('centre20_E_RMS',3.*scale)):
                match=row['matches'][criterion]
                self.assertEqual(match['source_peak_V'],.5*k)
                self.assertAlmostEqual(match['source_current_RMS_mA'],math.sqrt(2)*k)
                self.assertAlmostEqual(match['source_current_peak_mA'],2*k)
                self.assertAlmostEqual(match['loaded_metal_Vpp'],.8*k)
                for key,degree in DEGREES.items():
                    expected=unit['raw_burdens'][TOOL.BURDEN_SOURCE_KEYS[key]]*k**degree
                    self.assertAlmostEqual(match['burdens'][key],expected)
                    self.assertAlmostEqual(match['ratios_vs_reference']['burdens'][key],expected/row['reference_burdens'][key])
                voltage=match['ratios_vs_reference']['source_Vpp_to_max_TIS_output_interval']
                self.assertAlmostEqual(voltage['lower'],k/(2*scale));self.assertAlmostEqual(voltage['upper'],k/(1.5*scale))
                self.assertNotAlmostEqual(voltage['lower'],k/(3*scale))
                each=match['ratios_vs_reference']['source_Vpp_to_each_TIS_output_interval']
                self.assertAlmostEqual(each[0]['lower'],k/scale);self.assertAlmostEqual(each[0]['upper'],k/(.8*scale))
                self.assertFalse(match['ratios_vs_reference']['output_current_sum_is_physical_common_return_current'])
            self.assertAlmostEqual(row['reference_layer_contact_source_losses_W']['dermis_power_W'],.00046*scale**2)
            self.assertAlmostEqual(row['reference_layer_contact_source_losses_W']['skin_power_W'],.00007*scale**2)
            self.assertIsNone(row['reference_signed_output_power_evidence'])

    def test_one_actual_output_phasor_power_is_reconstructed_and_two_outputs_or_wrong_source_rejected(self):
        args=fixture();report=TOOL.build_comparison(*args)
        match=report['modes']['raw_1Vpp']['matches']['centre20_E_RMS'];power=match['signed_output_power_evidence']
        self.assertEqual(power['physical_outputs'],1)
        self.assertAlmostEqual(power['ideal_source_power_W'],.0005*3**2)
        self.assertAlmostEqual(power['source_resistor_loss_W'],.0001*3**2)
        self.assertAlmostEqual(power['metal_delivered_power_W'],.0004*3**2)
        self.assertAlmostEqual(power['output_current_RMS_mA'],math.sqrt(2)*3)
        self.assertFalse(power['hardware_absorption_and_compliance_validated'])
        for mutation in('two_outputs','wrong_pair','offfreq_voltage','peak','loaded','actual_source'):
            reference,unit,electrical=fixture()
            if mutation=='two_outputs':
                for row in electrical['source_current_spectrum']:
                    row['real_A'].append(0.);row['imaginary_A'].append(0.)
                for row in electrical['loaded_metal_voltage_spectrum']:
                    row['real_V'].append(0.);row['imaginary_V'].append(0.)
            elif mutation=='wrong_pair':unit['circuit']['n_pads']=4
            elif mutation=='offfreq_voltage':
                electrical['source_current_spectrum'].append(dict(frequency_Hz=9000,real_A=[0.],imaginary_A=[0.]))
                electrical['loaded_metal_voltage_spectrum'].append(dict(frequency_Hz=9000,real_V=[.1],imaginary_V=[0.]))
            elif mutation=='peak':unit['raw_burdens']['source_current_peak_mA']=3.
            elif mutation=='loaded':unit['raw_burdens']['loaded_metal_Vpp']=.9
            else:
                electrical['loaded_metal_voltage_spectrum'][0]['imaginary_V']=[-.3]
                electrical['source_power_W']=.0004;unit['raw_burdens']['source_power_W']=.0004;unit['raw_burdens']['loaded_metal_Vpp']=.6
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):TOOL.build_comparison(reference,unit,electrical)

    def test_wrong_best1_identity_roi_scaling_intervals_or_current_dimension_is_rejected(self):
        for mutation in('old_id','roi_volume','roi_scale','interval','two_currents','zero_bound'):
            reference,unit,electrical=fixture();mode=reference['normalizations']['skin_contact_only']
            if mutation=='old_id':reference['id']='historical-e7'
            elif mutation=='roi_volume':mode['regions'][TOOL.PRIMARY]['RMS']['volume_m3']=2e-7
            elif mutation=='roi_scale':mode['regions'][TOOL.PRIMARY]['RMS']['std']=8.
            elif mutation=='interval':mode['actual_source_Vpp_intervals_V'][0][0]=.7
            elif mutation=='two_currents':mode['source_output_RMS_by_output_mA']=[3.]
            else:reference['source_waveform']['source_Vpp_intervals_V'][0][0]=0.
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):TOOL.build_comparison(reference,unit,electrical)

    def test_optional_probe_rows_are_explicitly_reissued_only_when_supplied_and_scaled_once(self):
        reference,unit,electrical=fixture();probe=dict(status='complete',measurements=[dict(id=str(i),RMS_V=i/1000,
            Vpp_lower_V=i/500,Vpp_upper_V=i/300,fundamental_fixed_axis_envelope=dict(variation_range_V=0.))for i in range(1,41)])
        before=copy.deepcopy(probe);report=TOOL.build_comparison(reference,unit,electrical,raw_probe=probe)
        self.assertEqual(probe,before)
        for row in report['modes'].values():
            for match in row['matches'].values():
                output=match['unloaded_probe40'];self.assertEqual(len(output),40)
                self.assertEqual([item['id']for item in output],[item['id']for item in probe['measurements']])
                for new,old in zip(output,probe['measurements']):
                    self.assertAlmostEqual(new['RMS_V'],old['RMS_V']*match['amplitude_scale'])
                    self.assertAlmostEqual(new['Vpp_upper_V'],old['Vpp_upper_V']*match['amplitude_scale'])
                    self.assertEqual(new['fundamental_envelope_variation_V'],0.)


if __name__=='__main__':unittest.main()
