"""Unrun pure metadata contracts for cached absolute values and four modes."""
import copy,unittest
import native_light_post as subject

class CachedValueContracts(unittest.TestCase):
    def rows(self):
        stats=dict(mean=4.,p10=2.,max=8.,std=1.)
        record=dict(metrics=dict(regions={name:dict(statistics=dict(maxTIS=dict(stats)))for name in subject.REGIONS}))
        rows={mode:dict(amplitude_scale=.5,absolute_ROI_fields_V_m={
            name:dict(maxTIS=dict(mean=2.,p10=1.,max=4.,std=.5))for name in
            ('total','target','surface_0_5','surface_without_SC','off_target')},electrical={'source_power_W':1.})for mode in subject.MODES}
        return record,rows
    def test_remaining_ROI_is_labelled_scaled_cached_statistic_not_invented_producer_row(self):
        record,rows=self.rows();original=copy.deepcopy((record,rows));result=subject.cached_absolute_ROIs(rows,record)
        for row in result.values():
            self.assertNotIn('remaining',row['producer_normalized_AM_by_available_ROI'])
            self.assertEqual(row['all_six_ROI_AM_statistics_by_algebraic_amplitude_scaling']['remaining']['p10'],1.)
            self.assertEqual(row['all_six_ROI_AM_statistics_by_algebraic_amplitude_scaling']['target']['mean'],2.)
        self.assertEqual((record,rows),original)
    def test_all_four_cached_modes_and_positive_finite_scales_are_required(self):
        _,rows=self.rows();container=dict(normalizations=dict(status='complete',comparisons=rows))
        self.assertIs(subject.normalization_rows(container),rows)
        for bad in(float('nan'),-1.,True):
            changed=copy.deepcopy(container);changed['normalizations']['comparisons'][subject.MODES[0]]['amplitude_scale']=bad
            with self.assertRaises(ValueError):subject.normalization_rows(changed)
        changed=copy.deepcopy(container);changed['normalizations']['comparisons'].pop(subject.MODES[-1])
        with self.assertRaises(ValueError):subject.normalization_rows(changed)
    def test_explicit_extrapolation_does_not_become_strict_native_availability(self):
        rows=[dict(probe_id='p'+str(i),status='calculated_unloaded_only',same_layer_extrapolation_used=i<10,
            strict_same_layer_bracket_available=i>=10)for i in range(40)]
        summary=dict(probes=rows,probe_count=40,requested_probe_count=40,calculated_probe_count=40,
            unavailable_probe_count=0,same_layer_extrapolated_probe_count=10,strict_same_layer_bracket_available_probe_count=30)
        self.assertEqual(subject.validate_probe_accounting(summary)['strict_same_layer_bracket_available_probe_count'],30)
        for change in('drop','duplicate','count','strict'):
            bad=copy.deepcopy(summary)
            if change=='drop':bad['probes'].pop()
            elif change=='duplicate':bad['probes'][0]['probe_id']=bad['probes'][1]['probe_id']
            elif change=='count':bad['unavailable_probe_count']=1
            else:bad['probes'][0]['strict_same_layer_bracket_available']=True
            with self.assertRaises(ValueError):subject.validate_probe_accounting(bad)

if __name__=='__main__':unittest.main()
