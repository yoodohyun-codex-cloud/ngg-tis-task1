"""Native-cell display fixtures; no actual files, decoder, PDE or worker."""
import base64
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import task1_top5_build as display


class Top5DisplayDataTest(unittest.TestCase):
    def test_fractional_ROI_weights_are_not_equal_cell_weights(self):
        proof=display.weighted_primary_proof(np.array([0.,10.,20.]),np.array([.01,.98,.01]),dict(mean=10.,p10=10.,max=20.,volume_m3=1.))
        self.assertTrue(proof['passed'])
        with self.assertRaisesRegex(ValueError,'statistic mismatch'):
            display.weighted_primary_proof(np.array([0.,10.,20.]),np.array([.01,.98,.01]),dict(mean=10.,p10=0.,max=20.,volume_m3=1.))

    def test_native_slices_preserve_cell_order_nearest_actual_depth_and_missing_cells(self):
        x=np.array([-.5,.5]);y=np.array([-.5,.5]);z=np.array([4.9,9.8,14.8,17.4,19.9]);points=[]
        for k in range(5):
            for j in range(2):
                for i in range(2):
                    if(j,i)!=(1,1):points.append((i,j,k))
        points=list(reversed(points));ix,iy,iz=(np.array([p[k]for p in points])for k in range(3));values=100*iz+10*iy+ix
        result=display.scalar_planes(values,dict(x=x,y=y,z=z,ix=ix,iy=iy,iz=iz))
        xy=np.frombuffer(base64.b64decode(result['xy'][4]),dtype='<f4').reshape(2,2)
        np.testing.assert_equal(xy,np.array([[400,401],[410,np.nan]],float))
        xz=np.frombuffer(base64.b64decode(result['xz']),dtype='<f4').reshape(5,2)
        np.testing.assert_array_equal(xz,np.array([[0,1],[100,101],[200,201],[300,301],[400,401]]))
        yz=np.frombuffer(base64.b64decode(result['yz']),dtype='<f4').reshape(5,2)
        np.testing.assert_array_equal(yz,np.array([[0,10],[100,110],[200,210],[300,310],[400,410]]))

    def test_little_endian_float_display_preserves_nan_and_does_not_mutate_source(self):
        source=np.array([1.25,np.nan,3.5],dtype='>f8');before=source.copy();value=display.encode_f32(source)
        np.testing.assert_equal(np.frombuffer(base64.b64decode(value),dtype='<f4'),[1.25,np.nan,3.5]);np.testing.assert_equal(source,before)

    def test_invalid_native_grid_does_not_claim_comparable_dimensions(self):
        with self.assertRaises(ValueError):display.axes_and_indices(np.zeros((3,5)),dict(cells=3,h_xy_mm=.625,z_faces_mm=[0,1],sc_cells=2,bulk_layer_counts=[14,14,40]))


if __name__=='__main__':unittest.main()
