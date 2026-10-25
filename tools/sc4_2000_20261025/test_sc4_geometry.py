"""Synthetic geometry contracts; sole owner decides whether/when to execute."""
import unittest
import numpy as np
import sc4_math as geom


def fixture(counts=(2,3,3,4)):
    boundaries=np.asarray([0.,.1,5.1,10.1,25.1]);h=12.5
    faces=np.concatenate([np.linspace(boundaries[k],boundaries[k+1],counts[k]+1)[:-1]
                          for k in range(4)]+[boundaries[-1:]])
    z=(faces[:-1]+faces[1:])/2
    axis=-25+(np.arange(4)+.5)*h
    xx,yy=np.meshgrid(axis,axis,indexing='xy');inside=xx*xx+yy*yy<25**2
    xy=np.column_stack((xx[inside],yy[inside]));layer=np.repeat(np.arange(4),counts)
    grid=np.column_stack((np.tile(xy,(len(z),1)),np.repeat(z,len(xy)),
                          np.repeat(layer,len(xy)),np.repeat(h*h*np.diff(faces)*1e-9,len(xy))))
    meta=dict(h_xy_mm=h,radius_mm=25,sc_cells=counts[0],bulk_layer_counts=list(counts[1:]),z_faces_mm=faces.tolist())
    return grid,meta


class DynamicBulkGeometry(unittest.TestCase):
    def test_bulk_count_is_metadata_driven_not_fixed_seventy_planes(self):
        for counts in((2,3,3,4),(2,4,4,6),(2,18,18,56),(4,18,18,56)):
            with self.subTest(counts=counts):
                grid,meta=fixture(counts)
                result=geom.native_geometry(grid,meta)
                self.assertEqual(result['layer_counts'],list(counts))
                self.assertEqual(result['lookup'].shape,(sum(counts),4,4))
                self.assertEqual(len(result['z']),sum(counts))

    def test_duplicate_cell_is_rejected(self):
        grid,meta=fixture();grid[1]=grid[0]
        with self.assertRaises(ValueError):geom.native_geometry(grid,meta)

    def test_physical_layer_interface_change_is_rejected(self):
        grid,meta=fixture();meta['z_faces_mm'][2]=.2
        with self.assertRaises(ValueError):geom.native_geometry(grid,meta)

    def test_partial_bulk_column_is_rejected(self):
        grid,meta=fixture()
        with self.assertRaises(ValueError):geom.native_geometry(grid[:-1],meta)

    def test_volume_must_follow_actual_bulk_thickness(self):
        grid,meta=fixture();grid[0,4]*=1.1
        with self.assertRaises(ValueError):geom.native_geometry(grid,meta)


if __name__=='__main__':unittest.main()
