"""Synthetic native-cell comparisons; no native inputs or reports are read."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_native_causal_audit as r


def grid(n):
    result=np.zeros(n,dtype=[('x_mm','<f8'),('y_mm','<f8'),('z_mm','<f8'),
                             ('layer','<i4'),('volume_m3','<f8')])
    result['x_mm']=np.arange(n,dtype=float)
    result['y_mm']=-np.arange(n,dtype=float)
    result['z_mm']=15.5+np.arange(n,dtype=float)
    result['layer']=3;result['volume_m3']=1.
    return result


class NativeCausalAuditTests(unittest.TestCase):
    def test_nearest_pad_labels_preserve_order_and_first_pad_exact_ties(self):
        centres=np.array([[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]])
        xy=np.array([[0.,0.],[0.,-10.],[10.,0.],[0.,10.],[-10.,0.],[9.,-9.],[-9.,9.]])
        labels=r.nearest_pad_labels(xy,centres)
        np.testing.assert_array_equal([0,0,1,1,0,2,3],labels)
        self.assertIn(np.asarray(labels).dtype.kind,('i','u'))

    def test_signed_delta_contributions_volumes_and_hotspot_ties_are_consistent(self):
        before=np.array([1.,3.,10.,4.]);after=np.array([3.,1.,20.,6.])
        weights=np.array([1.,2.,0.,1.]);native_grid=grid(4)
        result=r.delta_statistics(before,after,weights,native_grid,
                                  {'baseline_mean':2.5,'baseline_p10':1.})
        self.assertEqual(4.,result['total_volume_m3'])
        self.assertEqual(2.75,result['before_mean_V_m']);self.assertEqual(2.75,result['after_mean_V_m'])
        self.assertEqual(0.,result['signed_mean_change_V_m'])
        self.assertEqual(1.,result['positive_delta_mean_contribution_V_m'])
        self.assertEqual(-1.,result['negative_delta_mean_contribution_V_m'])
        self.assertEqual(result['signed_mean_change_V_m'],
            result['positive_delta_mean_contribution_V_m']+result['negative_delta_mean_contribution_V_m'])
        self.assertEqual(2.,result['positive_delta_volume_m3'])
        self.assertEqual(2.,result['negative_delta_volume_m3'])
        positive,negative=result['positive_hotspot'],result['negative_hotspot']
        self.assertEqual(0,positive['native_index']);self.assertEqual(2.,positive['delta_V_m'])
        self.assertEqual([0.,0.,15.5],list(positive['xyz_mm']))
        self.assertEqual(1,negative['native_index']);self.assertEqual(-2.,negative['delta_V_m'])
        self.assertEqual([1.,-1.,16.5],list(negative['xyz_mm']))

    def test_high_volume_uses_fixed_baseline_cutoffs_separately_before_and_after(self):
        before=np.array([1.,3.,10.,4.]);after=np.array([3.,1.,20.,6.]);weights=np.array([1.,2.,0.,1.])
        cutoffs={'baseline_mean':2.5,'baseline_p10':1.}
        result=r.delta_statistics(before,after,weights,grid(4),cutoffs)
        high=result['fixed_baseline_cutoffs']['baseline_mean']
        self.assertEqual(2.5,high['cutoff_V_m'])
        self.assertEqual(3.,high['before_high_volume_m3']);self.assertEqual(2.,high['after_high_volume_m3'])
        self.assertEqual(.75,high['before_fraction']);self.assertEqual(.5,high['after_fraction'])
        low=result['fixed_baseline_cutoffs']['baseline_p10']
        self.assertEqual(4.,low['before_high_volume_m3']);self.assertEqual(4.,low['after_high_volume_m3'])
        self.assertEqual({'baseline_mean':2.5,'baseline_p10':1.},cutoffs)
        shifted=r.delta_statistics(np.array([0.,1.,2.]),np.array([1.,2.,3.]),np.ones(3),grid(3),
                                   {'baseline_mean':2.5,'baseline_p10':0.})
        high=shifted['fixed_baseline_cutoffs']['baseline_mean']
        self.assertEqual(0.,high['before_high_volume_m3']);self.assertEqual(1.,high['after_high_volume_m3'])

    def test_empty_nonfinite_negative_or_zero_total_weights_are_rejected(self):
        fixtures=[(np.array([]),np.array([]),np.array([])),
                  (np.array([1.]),np.array([2.]),np.array([0.])),
                  (np.array([1.]),np.array([2.]),np.array([-1.])),
                  (np.array([-1.]),np.array([2.]),np.array([1.])),
                  (np.array([1.]),np.array([np.nan]),np.array([1.])),
                  (np.array([1.]),np.array([2.]),np.array([np.nan])),
                  (np.array([1.,2.]),np.array([2.]),np.array([1.]))]
        for before,after,weights in fixtures:
            with self.subTest(before=before,after=after,weights=weights):
                with self.assertRaises(ValueError):
                    r.delta_statistics(before,after,weights,grid(len(before)),{'baseline_mean':1.,'baseline_p10':.5})

    def test_weighted_percentiles_use_frozen_left_inverse_cdf_at_exact_tie(self):
        values=np.array([30.,10.,20.,40.]);weights=np.array([1.,10.,9.,0.])
        result=r.weighted_statistics(values,weights)
        self.assertEqual(15.5,result['mean']);self.assertEqual(10.,result['p10'])
        self.assertEqual(20.,result['p95'])
        self.assertEqual(10.,result['min']);self.assertEqual(30.,result['max'])
        self.assertEqual(20.,result['volume_m3'])
        for bad_weights in (np.zeros(4),np.array([1.,-1.,1.,1.]),np.array([1.,np.nan,1.,1.])):
            with self.assertRaises(ValueError):r.weighted_statistics(values,bad_weights)

    def test_metric_guard_keeps_registered_relative_and_absolute_tolerances(self):
        self.assertTrue(r.close_metric(1.,1.+.5e-10))
        self.assertFalse(r.close_metric(1.,1.+2e-10))
        self.assertTrue(r.close_metric(0.,5e-15))
        self.assertFalse(r.close_metric(0.,2e-14))

    def test_build_audit_shares_raw_primary_roi_cutoffs_across_every_region_and_mode(self):
        native_grid=grid(4)
        native_grid['z_mm']=[1.,2.,16.,17.];native_grid['layer']=[1,1,3,3]
        weights={'surface_0_5':np.array([1.,1.,0.,0.]),
                 'primary_r5_depth15_20':np.array([0.,0.,1.,1.]),
                 'primary_complement':np.array([1.,1.,0.,0.])}
        meta=dict(h_xy_mm=.625,z_faces_mm=[0.,.1,5.1,10.1,25.1],
            tissue_boundaries_mm=[0.,.1,5.1,10.1,25.1],source_peak_V=.5,
            source_resistance_ohm=50.,channels=2,field_reconstruction='same')
        datasets=[dict(grid=native_grid.copy(),meta=meta.copy(),scalar=np.array(values),
                       RMS=np.array(values)*2,weights={key:value.copy()for key,value in weights.items()})
                  for values in ([1.,2.,10.,20.],[2.,3.,11.,21.])]
        centres=[[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]]
        declared=[dict(case_id=ident,pad_centres_xy_mm=centres)for ident in (r.BASE_ID,r.ASYM_ID)]
        plan=dict(cases=declared,source_volume_report='/tmp/synthetic-volume.json',
            source_physical_pad_report='/tmp/synthetic-pads.json',source_feedback_id='synthetic-feedback')
        rows=[]
        for case,data in zip(declared,datasets):
            regions={region:{key:r.weighted_statistics(data[field],weight)
                              for key,field in (('maxTIS','scalar'),('RMS','RMS'))}
                     for region,weight in weights.items()}
            rows.append(dict(case_id=case['case_id'],comparison_signature='same',
                normalizations={mode:dict(amplitude_scale=1.,regions=regions)for mode in r.MODES}))
        volume=dict(cases=rows);pads=dict(cases=[dict(case_id=c['case_id'])for c in declared])
        captured=[]
        def capture_groups(*args):
            captured.append(dict(args[-1]));return []
        with (patch.object(r.core,'read',side_effect=[volume,pads]),
              patch.object(r,'load_scalar_case',side_effect=datasets),
              patch.object(r,'association_groups',side_effect=capture_groups),
              patch.object(r,'scaled_saved_pad_report',return_value={})):
            result=r.build_audit(plan)
        expected={'baseline_mean':15.,'baseline_p10':10.}
        self.assertEqual(6,len(captured))
        self.assertTrue(all(cutoffs==expected for cutoffs in captured))
        for mode in result['comparisons']:
            self.assertEqual(set(weights),set(mode['regions']))
            for region in mode['regions'].values():
                self.assertEqual(expected,{name:row['cutoff_V_m']
                    for name,row in region['fixed_baseline_cutoffs'].items()})


if __name__=='__main__':
    unittest.main()
