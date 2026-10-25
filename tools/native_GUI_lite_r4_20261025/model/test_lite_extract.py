"""Synthetic source tests only; source author has not imported or run them."""
import base64
import unittest
import numpy as np
import lite_extract as x


def fixture():
    faces=np.asarray([0.,.05,.1,2.6,5.1,7.6,10.1,17.6,25.1])
    zs=(faces[:-1]+faces[1:])/2.;axis=[-18.75,-6.25,6.25,18.75]
    xy=[(a,b)for b in axis for a in axis if a*a+b*b<=625.]
    grid=np.asarray([[a,b,z,int(np.searchsorted(x.INTERFACES_MM,z,side='right')-1),1e-9]for z in zs for a,b in xy],float)
    return grid,faces


class DisplayPlaneFixtures(unittest.TestCase):
    def test_affine_scalar_has_correct_physical_xy_xz_yz_axes(self):
        grid,faces=fixture();layout=x.native_layout(np,grid,faces);field=100.+grid[:,0]+2*grid[:,1]+3*grid[:,2]
        xy,he,ve,meta=x.plane_values(np,layout,field,'XY',15.)
        for j,b in enumerate(layout['ys']):
            for i,a in enumerate(layout['xs']):
                if a*a+b*b<=625.:self.assertAlmostEqual(xy[j,i],145.+a+2*b,places=12)
                else:self.assertTrue(np.isnan(xy[j,i]))
        self.assertEqual(meta['physical_layer'],3);self.assertFalse(meta['cross_layer_interpolation'])
        self.assertEqual(he.tolist(),[-25.,-12.5,0.,12.5,25.])
        xz,_,ze,info=x.plane_values(np,layout,field,'XZ')
        np.testing.assert_allclose(xz,100.+layout['xs'][None,:]+3*layout['zs'][:,None],rtol=0,atol=1e-12)
        self.assertEqual(info['fixed_axis'],'y_mm');self.assertEqual(ze.tolist(),faces.tolist())
        yz,_,_,info=x.plane_values(np,layout,field,'YZ')
        np.testing.assert_allclose(yz,100.+2*layout['ys'][None,:]+3*layout['zs'][:,None],rtol=0,atol=1e-12)
        self.assertEqual(info['horizontal_axis'],'y_mm')

    def test_display_never_crosses_layer_or_extrapolates(self):
        grid,faces=fixture();layout=x.native_layout(np,grid,faces)
        with self.assertRaisesRegex(ValueError,'strictly inside'):x._z_bracket(np,layout,5.1)
        with self.assertRaisesRegex(ValueError,'cannot extrapolate'):x._z_bracket(np,layout,.08)
        broken=faces.copy();broken[4]+=.001
        with self.assertRaisesRegex(ValueError,'layer interfaces'):x.native_layout(np,grid,broken)

    def test_float16_only_changes_display_pixels_with_explicit_bound(self):
        values=np.asarray([[.00000003,1.234567],[np.nan,60000.]])
        item=x.encoded_plane(np,values,[0.,1.,2.],[0.,1.,2.],dict(orientation='XY',horizontal_axis='x_mm',vertical_axis='y_mm'),'AM_max2074','V/m')
        restored=np.frombuffer(base64.b64decode(item['values_b64_float16LE']),dtype='<f2').astype(float).reshape(2,2)
        valid=np.frombuffer(base64.b64decode(item['valid_mask_b64_u8']),dtype='u1').astype(bool).reshape(2,2)
        self.assertFalse(valid[1,0]);self.assertTrue(np.isnan(values[1,0]))
        self.assertTrue(np.all(abs(restored[valid]-values[valid])<=3.1e-8+5e-4*abs(values[valid])))
        self.assertFalse(item['quantization']['original_fields_clipped_or_overwritten'])
        with self.assertRaisesRegex(ValueError,'overflow'):x.encoded_plane(np,np.asarray([[70000.]]),[0.,1.],[0.,1.],item['sampling_metadata'],'RMS','V/m')

    def test_extract_uses_stored_scalars_and_signed_2000Hz_arrows_only(self):
        grid,faces=fixture();n=len(grid);a=10.+grid[:,2];r=20.+grid[:,2];E=np.tile(np.asarray([1+2j,-3+4j,5-6j]),(n,1))
        original=a.copy();display=x.extract_case(np,grid,faces,{'AM_max2074':a,'carrier_RMS':r},E_peak_2000=E)
        self.assertFalse(display['quantitative_statistics_recomputed']);np.testing.assert_array_equal(a,original)
        self.assertEqual(set(display['planes']['AM_max2074']),{'xy15','xy17p5','xy20','xz','yz'})
        self.assertEqual(display['planes']['contact_J']['status'],'unavailable')
        self.assertTrue(display['missing_pad_outlines']);self.assertEqual(display['new_angular_evaluations'],0)
        plane=display['planes']['carrier_RMS']['xz'];self.assertEqual(plane['arrow_frequency_Hz'],2000)
        self.assertEqual(plane['arrow_phase_rad'],0.)
        for arrow in plane['arrows']:
            self.assertAlmostEqual(arrow['u_V_m'],1.);self.assertAlmostEqual(arrow['v_V_m'],5.)

    def test_deadline_precedes_grid_or_field_access(self):
        with self.assertRaises(TimeoutError):x.extract_case(None,None,None,None,deadline_monotonic=0.)


class PhysicalPatchOutlineFixtures(unittest.TestCase):
    def test_exact_hole_boundary_is_not_filled_by_bbox(self):
        rectangles=[[i,i+1,j,j+1]for j in range(3)for i in range(3)if(i,j)!=(1,1)]
        row=x.rectangle_union_outline(rectangles,0,'out0',declared_area_mm2=8)
        self.assertEqual(row['exact_area_mm2'],{'numerator':8,'denominator':1})
        self.assertTrue(row['holes_preserved_by_boundary_segments']);self.assertFalse(row['bbox_or_area_inferred_patch'])
        segments=row['boundary_segments_xy_mm'];self.assertTrue(any(a[0]==b[0]==1. and min(a[1],b[1])==1. and max(a[1],b[1])==2. for a,b in segments))
        self.assertEqual(len(row['patch_rectangles_mm']),8)

    def test_overlap_area_correction_and_outside_phantom_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlap'):x.rectangle_union_outline([[0,2,0,2],[1,3,1,3]],0,'out0')
        with self.assertRaisesRegex(ValueError,'declared area'):x.rectangle_union_outline([[0,1,0,1]],0,'out0',declared_area_mm2=2)
        with self.assertRaisesRegex(ValueError,'fixedD50'):x.rectangle_union_outline([[24,25,24,25]],0,'out0')
