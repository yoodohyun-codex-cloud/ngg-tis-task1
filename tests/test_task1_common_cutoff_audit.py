"""Synthetic-only common-threshold tests; no native data or PDE execution."""
from pathlib import Path
import sys
import unittest

import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_common_cutoff_audit as audit
import task1_volume_selectivity as volume


class CommonThresholdTests(unittest.TestCase):
    def test_inclusive_threshold_and_fractional_volume_not_cell_count(self):
        result=audit.summarize([1.,2.,4.],[.1,.2,.7],1.,{'cut':2.},volume)
        self.assertAlmostEqual(result['common_cutoff_volumes']['cut']['volume_m3'],.9)
        self.assertNotAlmostEqual(result['common_cutoff_volumes']['cut']['fraction'],2/3)
        self.assertEqual(result['common_cutoff_volumes']['cut']['comparison'],'>=')

    def test_amplitude_before_classification_threshold_stays_fixed(self):
        cutoffs={'cut':2.}
        raw=audit.summarize([1.,2.,4.],[.1,.2,.7],1.,cutoffs,volume)
        matched=audit.summarize([1.,2.,4.],[.1,.2,.7],.5,cutoffs,volume)
        self.assertAlmostEqual(raw['common_cutoff_volumes']['cut']['volume_m3'],.9)
        self.assertAlmostEqual(matched['common_cutoff_volumes']['cut']['volume_m3'],.7)
        self.assertEqual(matched['common_cutoff_volumes']['cut']['cutoff_V_m'],2.)
        self.assertEqual(cutoffs,{'cut':2.})
        self.assertAlmostEqual(matched['mean'],raw['mean']/2)

    def test_own_model_scale_retained_no_nominal_recalculation(self):
        case=dict(own_model_amplitude_scales=dict(raw_1Vpp=1.,skin_contact_only=.922),own_baseline_summary='Rs2000baseline')
        row=dict(normalizations={'raw_1Vpp':{'amplitude_scale':1.},'skin_contact_only':{'amplitude_scale':.922}},baseline_summary='Rs2000baseline')
        self.assertEqual(audit.own_scales(case,row)['skin_contact_only'],.922)
        row['normalizations']['skin_contact_only']['amplitude_scale']=.921
        with self.assertRaisesRegex(ValueError,'immutable normalization'):
            audit.own_scales(case,row)
        row['normalizations']['skin_contact_only']['amplitude_scale']=.922
        row['baseline_summary']='nominal500baseline'
        with self.assertRaisesRegex(ValueError,'Cross-model normalization'):
            audit.own_scales(case,row)

    def test_same_grid_and_six_roi_weights_exact_guard(self):
        data=dict(grid=np.array([(1.,2.)],dtype=[('x','<f8'),('y','<f8')]),
            regions={name:np.array([.5],dtype='<f8') for name in audit.REGIONS})
        reference=audit.require_same_geometry(None,data)
        self.assertIs(audit.require_same_geometry(reference,data),reference)
        data['regions'][audit.REGIONS[-1]][0]+=.0000000001
        with self.assertRaisesRegex(ValueError,'fractional ROI weights differ'):
            audit.require_same_geometry(reference,data)
        data['regions'][audit.REGIONS[-1]][0]=.5
        data['grid']['x'][0]=1.1
        with self.assertRaisesRegex(ValueError,'source grids'):
            audit.require_same_geometry(reference,data)

    def test_zero_weight_high_value_does_not_set_maximum(self):
        result=audit.summarize([999.,2.,4.],[0.,.25,.75],1.,{'cut':4.},volume)
        self.assertEqual(result['maximum'],4.)
        self.assertEqual(result['common_cutoff_volumes']['cut']['volume_m3'],.75)


if __name__=='__main__':unittest.main()
