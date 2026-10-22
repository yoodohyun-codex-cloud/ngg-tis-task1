"""Pure three-case saved-scalar display tests; no files or plots are loaded."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_one_return_rotation_maps as r

IDS=('baseline-square15-xy80','asym-cross281p25-return168p75-xy80','asym-return2-rot90-xy80')


def rows():
    limits={key:float(index+1)for index,key in enumerate(sorted(r.base.CAPS))}
    output=[]
    for ident,scale in zip(IDS,(1.,.5,5.)):
        modes={name:dict(amplitude_scale=value,baseline_derived_numerical_limits=dict(limits),
                        includes_source_power_cap=False,includes_1Vpp_ceiling=False,source_Vpp_per_output=value)
               for name,value in (('raw_1Vpp',1.),('skin_contact_only',scale))}
        output.append(dict(case_id=ident,adopted=False,comparison_signature='same-grid-model',normalizations=modes,
            calculation_status='cached_native_scalar_audit_complete'))
    return output


def audit():
    return dict(schema='task1-volume-selectivity-v1',status='calculated_unadopted',inputs_unchanged=True,
                inputs_sha256={'/tmp/source-summary.json':'a'*64},selected_for_adoption=[],cases=rows())


def metadata():
    boundaries=[0.,.1,5.1,10.1,25.1];counts=[2,14,14,40];faces=[0.]
    for lo,hi,n in zip(boundaries,boundaries[1:],counts):
        faces.extend(lo+(hi-lo)*i/n for i in range(1,n+1))
    return dict(cells=351680,h_xy_mm=.625,radius_mm=25.,total_depth_mm=25.1,sc_cells=2,
                bulk_layer_counts=[14,14,40],tissue_boundaries_mm=boundaries,z_faces_mm=faces,
                source_peak_V=.5,source_resistance_ohm=50.,channels=2,frequencies_Hz=[3000,3030,9000,9090])


class OneReturnRotationMapsTests(unittest.TestCase):
    def test_only_three_terminal_unadopted_saved_case_rows_are_accepted_in_order(self):
        source=audit();before=copy.deepcopy(source)
        accepted=r.validate_audit(source)
        self.assertEqual(list(IDS),[row['case_id']for row in accepted])
        self.assertEqual(before,source)

    def test_changed_ids_order_terminal_state_or_adoption_claims_are_rejected(self):
        mutations=(lambda s:s.update(schema='task1-native-volume-selectivity-v1'),
                   lambda s:s.update(status='running'),lambda s:s.update(inputs_unchanged=False),
                   lambda s:s.update(selected_for_adoption=[IDS[2]]),
                   lambda s:s['cases'][2].update(adopted=True),lambda s:s['cases'].reverse(),
                   lambda s:s['cases'].pop(),lambda s:s['cases'][2].update(case_id='another-rotation'))
        for mutate in mutations:
            value=audit();mutate(value)
            with self.assertRaises(ValueError):r.validate_audit(value)

    def test_saved_mode_scales_are_positive_and_reference_identical_eight_skin_caps(self):
        source=rows();before=copy.deepcopy(source)
        scales=r.validate_modes(source)
        self.assertEqual([{'raw_1Vpp':1.,'skin_contact_only':value}for value in (1.,.5,5.)],scales)
        self.assertEqual(before,source)
        for mutate in (lambda s:s[2]['normalizations']['skin_contact_only'].update(amplitude_scale=0.),
                       lambda s:s[2]['normalizations']['raw_1Vpp'].update(amplitude_scale=-1.),
                       lambda s:s[2]['normalizations']['skin_contact_only'].update(amplitude_scale=float('nan')),
                       lambda s:s[2]['normalizations']['skin_contact_only'].update(includes_source_power_cap=True),
                       lambda s:s[2]['normalizations']['skin_contact_only'].update(includes_1Vpp_ceiling=True),
                       lambda s:s[2]['normalizations']['skin_contact_only']['baseline_derived_numerical_limits'].update(SC_power_W=999.),
                       lambda s:s[2]['normalizations'].pop('raw_1Vpp')):
            value=rows();mutate(value)
            with self.assertRaises((ValueError,KeyError)):r.validate_modes(value)

    def test_fixed_original_grid_and_layer_contract_rejects_other_meshes_or_phantoms(self):
        r.validate_grid_contract(metadata())
        for mutate in (lambda m:m.update(cells=351681),lambda m:m.update(h_xy_mm=1.25),
                       lambda m:m.update(radius_mm=26.),lambda m:m.update(total_depth_mm=30.1),
                       lambda m:m.update(sc_cells=4),lambda m:m.update(bulk_layer_counts=[18,18,56]),
                       lambda m:m.update(tissue_boundaries_mm=[0.,.2,5.2,10.2,25.2])):
            value=metadata();mutate(value)
            with self.assertRaises(ValueError):r.validate_grid_contract(value)

    def test_common_global_and_primary_roi_color_limits_include_all_three_saved_scales(self):
        cases=[]
        for value,scale in zip(([100.,2.,3.],[50.,4.,5.],[25.,6.,7.]),(1.,.5,5.)):
            values=np.array(value)
            arrays=dict(maxTIS=values.copy(),fixedTIS=values*.5,RMS=values*2,
                        region_target_m3=np.array([0.,.5,1.]))
            cases.append(dict(arrays=arrays,scales={'raw_1Vpp':1.,'skin_contact_only':scale}))
        before=copy.deepcopy(cases)
        self.assertEqual((0.,100.),r.shared_color_limits(cases,'maxTIS','raw_1Vpp'))
        self.assertEqual((0.,125.),r.shared_color_limits(cases,'maxTIS','skin_contact_only'))
        self.assertEqual((0.,7.),r.shared_color_limits(cases,'maxTIS','raw_1Vpp',deep_roi=True))
        self.assertEqual((0.,35.),r.shared_color_limits(cases,'maxTIS','skin_contact_only',deep_roi=True))
        self.assertEqual((0.,250.),r.shared_color_limits(cases,'RMS','skin_contact_only'))
        for current,original in zip(cases,before):
            for key in original['arrays']:np.testing.assert_array_equal(original['arrays'][key],current['arrays'][key])
            self.assertEqual(original['scales'],current['scales'])

    def test_native_slices_keep_values_faces_actual_planes_and_original_arrays(self):
        grid=np.array([(x,y,z)for z in (.5,2.)for y in (-.3125,.3125)for x in (-.3125,.3125)])
        values=np.arange(1.,9.);before_grid=grid.copy();before_values=values.copy()
        meta=dict(cells=8,h_xy_mm=.625,z_faces_mm=[0.,1.,3.])
        result=r.native_slices(grid,meta,values,xy_depth_mm=1.8)
        np.testing.assert_array_equal([[5.,6.],[7.,8.]],result['xy'])
        np.testing.assert_array_equal([[1.,2.],[5.,6.]],result['xz'])
        np.testing.assert_array_equal([-.625,0.,.625],result['x_edges_mm'])
        np.testing.assert_array_equal([0.,1.,3.],result['z_edges_mm'])
        self.assertEqual(2.,result['xy_actual_depth_mm']);self.assertEqual(-.3125,result['xz_actual_y_mm'])
        np.testing.assert_array_equal(before_grid,grid);np.testing.assert_array_equal(before_values,values)


if __name__=='__main__':
    unittest.main()
