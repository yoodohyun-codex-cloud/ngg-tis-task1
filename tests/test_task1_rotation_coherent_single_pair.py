"""Synthetic single-pair RMS comparison contracts; no research data or PDE."""
import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))


def probe_fixture():
    rows=[]
    for depth in(5,10,15,20):
        for position in('centre','x_plus','x_minus','y_plus','y_minus'):
            for axis in('X','Y'):
                index=len(rows)+1;rms=index/1000
                rows.append(dict(id=f'{depth}-{position}-{axis}',RMS_V=rms,
                    Vpp_lower_V=2*math.sqrt(2)*rms*(1-1e-7),Vpp_upper_V=2*math.sqrt(2)*rms*(1+1e-7),
                    fundamental_fixed_axis_envelope=dict(variation_range_V=0.),axis=axis,
                    depth_from_skin_surface_mm=depth,position=position,tip_gap_mm=5.))
    return dict(status='complete',measurements=rows,unloaded_prediction=True)


class RotationCoherentSinglePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('rotation_coherent_single_pair_tested',ROOT/'tools/task1_rotation_coherent_single_pair.py')
        cls.tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.tool)

    def setUp(self):
        self.probe=probe_fixture()
        self.burdens=dict(source_current_RMS_mA=2.,source_current_peak_mA=2*math.sqrt(2),
            contact_J_RMS_max_A_m2=3.,contact_J_RMS_p95_A_m2=2.5,contact_voltage_RMS_max_V=.02,
            loaded_metal_Vpp=.8,SC_power_W=.01,contact_power_W=.02,source_power_W=.1)

    def test_exact_three_references_two_modes_and_two_independent_matches(self):
        self.assertEqual(self.tool.REFERENCE_IDS,('rotation-square-control','rotation-sine-control','rotation-coherent-r1-p090'))
        self.assertEqual(self.tool.MODES,('raw','skin_contact_only'))
        rows=[]
        for reference in self.tool.REFERENCE_IDS:
            for mode in self.tool.MODES:
                matches=self.tool.target_matches(6.,8.,2.,4.,self.burdens,self.probe)
                self.assertEqual(set(matches),{'centre20_E_RMS','ROI_energy_RMS'})
                rows.extend((reference,mode,criterion)for criterion in matches)
        self.assertEqual(len(rows),12);self.assertEqual(len(set(rows)),12)

    def test_weighted_energy_rms_uses_squared_field_fractional_volume_not_mean(self):
        value=self.tool.weighted_energy_rms([1.,3.],[.25,.75])
        self.assertAlmostEqual(value,math.sqrt(7),places=15)
        self.assertNotAlmostEqual(value,2.5,places=3)
        self.assertAlmostEqual(self.tool.weighted_energy_rms([1.,3.],[2.5e-10,7.5e-10]),value,places=15)

    def test_weighted_energy_rms_rejects_invalid_weights_shape_and_nonfinite_values(self):
        for values,weights in(([1.,2.],[0.,0.]),([1.,2.],[-1.,1.]),([1.,2.],[1.]),
                ([float('nan')],[1.]),([1.],[float('inf')]),([-1.],[1.])):
            with self.subTest(values=values,weights=weights),self.assertRaises(ValueError):
                self.tool.weighted_energy_rms(values,weights)

    def test_point_and_roi_matching_require_distinct_voltage_ratios(self):
        matches=self.tool.target_matches(6.,8.,2.,4.,self.burdens,self.probe)
        self.assertEqual(matches['centre20_E_RMS']['required_source_Vpp'],3.)
        self.assertEqual(matches['ROI_energy_RMS']['required_source_Vpp'],2.)
        self.assertEqual(matches['centre20_E_RMS']['achieved_centre20_E_RMS_V_m'],6.)
        self.assertEqual(matches['ROI_energy_RMS']['achieved_ROI_energy_RMS_V_m'],8.)
        self.assertNotEqual(matches['centre20_E_RMS']['achieved_ROI_energy_RMS_V_m'],8.)
        self.assertNotEqual(matches['ROI_energy_RMS']['achieved_centre20_E_RMS_V_m'],6.)

    def test_matched_currents_voltages_and_field_burdens_scale_linearly_power_quadratically(self):
        matches=self.tool.target_matches(6.,8.,2.,4.,self.burdens,self.probe)
        for criterion,scale in(('centre20_E_RMS',3.),('ROI_energy_RMS',2.)):
            result=matches[criterion]
            self.assertEqual(result['amplitude_scale'],scale)
            self.assertEqual(result['actual_source_Vpp'],scale);self.assertEqual(result['source_peak_V'],.5*scale)
            self.assertIn('zero temporal envelope variation',result['single_frequency_modulation_definition'])
            for key,value in self.burdens.items():
                self.assertAlmostEqual(result['burdens'][key],value*scale**(2 if key.endswith('_W')else 1),places=14)

    def test_all_forty_unloaded_probe_rows_scale_once_with_matching_voltage(self):
        matches=self.tool.target_matches(6.,8.,2.,4.,self.burdens,self.probe)
        for criterion,scale in(('centre20_E_RMS',3.),('ROI_energy_RMS',2.)):
            rows=matches[criterion]['unloaded_probe40']
            self.assertEqual(len(rows),40);self.assertEqual(len({row['id']for row in rows}),40)
            self.assertEqual([row['id']for row in rows],[row['id']for row in self.probe['measurements']])
            for result,raw in zip(rows,self.probe['measurements']):
                for key in('RMS_V','Vpp_lower_V','Vpp_upper_V'):self.assertAlmostEqual(result[key],raw[key]*scale,places=15)
                self.assertEqual(result['fundamental_envelope_variation_V'],0.)

    def test_matching_leaves_original_probe_evidence_and_raw_burdens_unchanged(self):
        before=copy.deepcopy((self.probe,self.burdens))
        self.tool.target_matches(6.,8.,2.,4.,self.burdens,self.probe)
        self.assertEqual((self.probe,self.burdens),before)

    def test_matching_rejects_zero_rms_and_incomplete_or_duplicate_probe_grid(self):
        for centre,roi,single_centre,single_roi in((0.,1.,1.,1.),(1.,0.,1.,1.),(1.,1.,0.,1.),(1.,1.,1.,0.),(float('nan'),1.,1.,1.),(1.,float('inf'),1.,1.)):
            with self.assertRaises(ValueError):self.tool.target_matches(centre,roi,single_centre,single_roi,self.burdens,self.probe)
        for mutation in('missing','duplicate','failed'):
            probe=copy.deepcopy(self.probe)
            if mutation=='missing':probe['measurements'].pop()
            elif mutation=='duplicate':probe['measurements'][1]['id']=probe['measurements'][0]['id']
            else:probe['status']='error'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                self.tool.target_matches(6.,8.,2.,4.,self.burdens,probe)

    def test_true_single_pair_needs_two_physical_pads_one_source_and_one_return(self):
        case=dict(circuit=dict(n_pads=2,n_outputs=1,n_return_nodes=1,pad_to_node={'0':'out0','1':'GND'},
            source_peak_V=.5,source_resistance_ohm=50))
        mesh=dict(channels=1,h_xy_mm=.625,sc_cells=2,bulk_layer_counts=[14,14,40],cells=351680,phasor_convention='peak,+jomega_t')
        self.tool.validate_single(case,mesh)
        for key,value in(('n_pads',4),('n_outputs',2),('source_resistance_ohm',0)):
            bad=copy.deepcopy(case);bad['circuit'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.tool.validate_single(bad,mesh)

    def test_footprint_reports_physical_area_without_inventing_more_outputs(self):
        circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1)
        proof=self.tool.reference_footprint([225e-6,225e-6,281.25e-6,168.75e-6],circuit)
        self.assertEqual(proof['physical_pads'],4);self.assertEqual(proof['independent_outputs'],2)
        self.assertEqual(proof['common_return_nodes'],1)
        np.testing.assert_allclose(proof['per_pad_area_mm2'],[225.,225.,281.25,168.75],atol=1e-12,rtol=0)
        self.assertAlmostEqual(proof['total_contact_area_mm2'],900.)
        pair=self.tool.reference_footprint([225e-6,225e-6],dict(n_pads=2,n_outputs=1,n_return_nodes=1))
        self.assertEqual(pair['physical_pads'],2);self.assertEqual(pair['independent_outputs'],1)
        self.assertAlmostEqual(pair['total_contact_area_mm2'],450.)

    def test_footprint_rejects_nonpositive_nonfinite_or_wrong_pad_count(self):
        circuit=dict(n_pads=4,n_outputs=2,n_return_nodes=1)
        for areas in([225e-6]*3,[225e-6,225e-6,225e-6,0.],[225e-6,225e-6,225e-6,-1.],
                [225e-6,225e-6,225e-6,float('nan')],[225e-6,225e-6,225e-6,float('inf')]):
            with self.subTest(areas=areas),self.assertRaises(ValueError):self.tool.reference_footprint(areas,circuit)

    def test_complex_native_point_interpolation_is_separate_from_roi_energy_average(self):
        grid=np.array([(x,y,z)for z in(19.,21.)for y in(-1.,1.)for x in(-1.,1.)],
            dtype=[('x_mm','f8'),('y_mm','f8'),('z_mm','f8')])
        values=np.column_stack((grid['x_mm']+2*grid['z_mm'],grid['y_mm'],1j*grid['z_mm']))
        np.testing.assert_allclose(self.tool.sample_native(values,grid),[40.,0.,20j],rtol=0,atol=1e-15)


    def test_latest_rotation_source_and_inherited_single_pair_helpers_preserved(self):
        self.assertEqual(self.tool.SOURCE_SUMMARY,ROOT/'docs/cloud-rotation-coherent-20261021T182000Z/summary.json')
        self.assertEqual(self.tool.ROTATION_SUMMARY.parent.name,'asym-return2-rot90-xy80')
        self.assertEqual(self.tool.C1,'baseline-square15-C1pair0-xy80')
        self.assertIs(self.tool.weighted_energy_rms,self.tool.old.weighted_energy_rms)
        self.assertIs(self.tool.validate_single,self.tool.old.validate_single)
        self.assertIs(self.tool.matched_single,self.tool.old.matched_single)
        self.assertIs(self.tool.scaled_probe_rows,self.tool.drive.scaled_probe_rows)

    def test_root_decision_binds_exact_three_reference_modes_and_actual_source_sha(self):
        decision=dict(schema='task1-rotation-coherent-single-pair-decision-v1',status='selected_not_executed',
            reference_ids=list(self.tool.REFERENCE_IDS),modes=list(self.tool.MODES),single_case_id=self.tool.C1,
            single_frequency_Hz=3000,new_PDE=0,candidate_adopted=False,source_summary_path=str(self.tool.SOURCE_SUMMARY),
            source_summary_sha256='a'*64,question='Match field RMS at centre and ROI separately, without physiological equivalence')
        self.tool.validate_decision(decision,'a'*64)
        with self.assertRaises(ValueError):self.tool.validate_decision(decision,'b'*64)
        for key,value in(('reference_ids',list(self.tool.REFERENCE_IDS[:2])),('modes',['raw']),
                ('source_summary_path','/other/summary.json'),('single_frequency_Hz',9000),('candidate_adopted',True)):
            wrong=copy.deepcopy(decision);wrong[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.tool.validate_decision(wrong,'a'*64)


if __name__=='__main__':unittest.main()
