import importlib.util
from pathlib import Path
import unittest
import numpy as np

path=Path(__file__).resolve().parents[1]/'tools/task1_coherent_single_pair.py'
spec=importlib.util.spec_from_file_location('coherent_single_pair_tested',path);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

class CoherentSinglePairTest(unittest.TestCase):
    def test_true_roi_energy_not_mean_rms_and_fractional_weights(self):
        self.assertAlmostEqual(tool.weighted_energy_rms([1,3],[.25,.75]),np.sqrt(7))
        self.assertNotEqual(tool.weighted_energy_rms([1,3],[1,1]),2.)

    def test_point_and_roi_match_have_independent_ratios_and_power_scaling(self):
        result=tool.matched_single(6,8,2,4,dict(source_current_RMS_mA=2,contact_power_W=5))
        self.assertEqual(result['centre20_E_RMS']['required_source_Vpp'],3)
        self.assertEqual(result['ROI_energy_RMS']['required_source_Vpp'],2)
        self.assertEqual(result['centre20_E_RMS']['burdens']['source_current_RMS_mA'],6)
        self.assertEqual(result['centre20_E_RMS']['burdens']['contact_power_W'],45)

    def test_native_trilinear_point_matches_linear_vector_field(self):
        grid=np.array([(x,y,z)for z in(19.,21.)for y in(-1.,1.)for x in(-1.,1.)],dtype=[('x_mm',float),('y_mm',float),('z_mm',float)])
        values=np.column_stack((grid['x_mm']+2*grid['z_mm'],grid['y_mm'],1j*grid['z_mm']))
        np.testing.assert_allclose(tool.sample_native(values,grid),[40,0,20j])

    def test_invalid_weights_or_denominators_cannot_invent_matching_voltage(self):
        for values,weights in [([1,2],[0,0]),([1,2],[-1,1]),([float('nan')],[1])]:
            with self.assertRaises(ValueError):tool.weighted_energy_rms(values,weights)
        with self.assertRaises(ValueError):tool.matched_single(1,1,0,1,{})

    def test_four_pad_disabled_output_is_not_a_single_pair(self):
        case=dict(circuit=dict(n_pads=4,n_outputs=1,n_return_nodes=1,pad_to_node={'0':'out0','1':'GND'},source_peak_V=.5,source_resistance_ohm=50))
        with self.assertRaisesRegex(ValueError,'actual source/return pair'):tool.validate_single(case,{'channels':1})

    def test_root_selection_is_bound_to_exact_candidate_and_source_sha(self):
        source=Path('/example/condition.json');digest='a'*64
        obj=dict(schema='task1-coherent-single-pair-decision-v1',status='selected_not_executed',candidate_id=tool.CANDIDATE,
            single_case_id=tool.C1,single_frequency_Hz=3000,new_PDE=0,candidate_adopted=False,
            source_condition_path=str(source),source_condition_sha256=digest,question='Match point and ROI RMS separately')
        tool.validate_decision(obj,source,digest)
        with self.assertRaises(ValueError):tool.validate_decision(obj,source,'b'*64)
        obj['candidate_adopted']=True
        with self.assertRaises(ValueError):tool.validate_decision(obj,source,digest)

    def test_failed_feedback_snapshot_cannot_be_treated_as_review(self):
        obj=dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',public_GitHub_only=True,
            messages_sent=0,new_PDE=0,error=None,observed_utc='2026-10-21T17:04:55Z')
        tool.validate_feedback(obj);obj['error']='GET failed'
        with self.assertRaises(ValueError):tool.validate_feedback(obj)

if __name__=='__main__':unittest.main()
