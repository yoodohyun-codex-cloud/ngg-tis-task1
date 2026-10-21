"""Synthetic physical-gap versus native-face support geometry only."""
import copy
import csv
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_grouped_gap_geometry as r


def case(h):
    nodes=[0,1,-1,-1]
    centres=[(-.375,.625),(1.625,.625),(-.375,5.625),(1.625,5.625)]
    pads=[dict(pad_id=i,parent_group=i,node=nodes[i],shape='rectangle',width_mm=1.,height_mm=1.,
               x_mm=x,y_mm=y,rotation_deg=0.,attachment='top_z0',area_mm2=1.)
          for i,(x,y)in enumerate(centres)]
    return dict(n_pads=4,n_outputs=2,n_return_nodes=1,pad_node_ids=nodes,pads=pads,
                h_xy_mm=h,expected_pad_areas_m2=[1e-6]*4)


def exact_rows(geometry):
    h=geometry['h_xy_mm'];rows=[]
    for pad in geometry['pads']:
        xmin,xmax=pad['x_mm']-.5,pad['x_mm']+.5
        ymin,ymax=pad['y_mm']-.5,pad['y_mm']+.5
        for j in range(math.floor((ymin+25)/h),math.ceil((ymax+25)/h)):
            dy=max(0.,min(ymax,-25+(j+1)*h)-max(ymin,-25+j*h))
            for i in range(math.floor((xmin+25)/h),math.ceil((xmax+25)/h)):
                dx=max(0.,min(xmax,-25+(i+1)*h)-max(xmin,-25+i*h))
                if dx*dy>0:rows.append((pad['pad_id'],i,j,dx*dy*1e-6))
    return rows


def pair(receipt,a,b):
    return next(row for row in receipt['pairwise']if {row['pad_a'],row['pad_b']}=={a,b})


class GroupedGapGeometryTests(unittest.TestCase):
    def test_one_mm_physical_gap_is_preserved_while_shared_native_faces_change(self):
        coarse=r.audit_mask_geometry(exact_rows(case(1.25)),case(1.25))
        fine=r.audit_mask_geometry(exact_rows(case(.625)),case(.625))
        self.assertEqual(1.,coarse['analytical_minimum_gap_mm'])
        self.assertEqual(1.,fine['analytical_minimum_gap_mm'])
        for a,b in ((0,1),(2,3)):
            old,new=pair(coarse,a,b),pair(fine,a,b)
            self.assertEqual(1.,old['analytic_gap_mm']);self.assertEqual(1.,new['analytic_gap_mm'])
            self.assertEqual([1.,-1.],old['analytic_signed_axis_gap_mm'])
            self.assertEqual(1,old['shared_top_face_count']);self.assertEqual(0,new['shared_top_face_count'])
            self.assertLess(old['represented_support_signed_bbox_gap_mm'],0.)
            self.assertGreaterEqual(new['represented_support_signed_bbox_gap_mm'],0.)
            self.assertAlmostEqual(1.6,new['analytic_gap_mm']/.625)
        self.assertEqual(2,coarse['shared_tissue_top_faces']['count'])
        self.assertEqual(0,fine['shared_tissue_top_faces']['count'])

    def test_same_and_different_electrical_node_shared_faces_are_explicit_without_metal_merging(self):
        receipt=r.audit_mask_geometry(exact_rows(case(1.25)),case(1.25))
        self.assertFalse(pair(receipt,0,1)['same_electrical_node'])
        self.assertTrue(pair(receipt,2,3)['same_electrical_node'])
        shared=receipt['shared_tissue_top_faces']
        self.assertEqual(1,shared['physical_pad_pairs_same_node'])
        self.assertEqual(1,shared['physical_pad_pairs_different_nodes'])
        self.assertEqual([[2,3]],shared['same_node_pairs'])
        self.assertEqual([[0,1]],shared['different_node_pairs'])
        self.assertFalse(receipt['physical_electrode_merging_assumed'])
        self.assertEqual(4,receipt['physical_pad_count']);self.assertEqual(2,receipt['n_outputs'])
        self.assertEqual(1,receipt['n_return_nodes'])

    def test_exact_fragment_areas_and_fractions_preserve_all_pad_and_parent_totals(self):
        for h,cells,fraction in ((1.25,2,.08),(.625,6,.16)):
            geometry=case(h);rows=exact_rows(geometry);original=copy.deepcopy(rows)
            receipt=r.audit_mask_geometry(rows,geometry)
            self.assertEqual(original,rows)
            for pad in receipt['pads']:
                self.assertEqual(1.,pad['analytic_area_mm2'])
                self.assertAlmostEqual(1e-6,pad['represented_area_m2'],places=18)
                self.assertEqual(1e-6,pad['expected_area_m2'])
                self.assertLessEqual(abs(pad['represented_vs_analytic_relative_error']),1e-10)
                self.assertTrue(pad['area_gate_passed']);self.assertEqual(cells,pad['contact_cells'])
                self.assertEqual(cells,pad['partial_face_count'])
                self.assertAlmostEqual(fraction,pad['minimum_fragment_fraction'],places=12)
                self.assertGreater(pad['minimum_fragment_area_m2'],0.)
            for parent in receipt['parents']:
                self.assertEqual(1.,parent['analytic_area_mm2'])
                self.assertAlmostEqual(1e-6,parent['represented_area_m2'],places=18)
                self.assertEqual(1e-6,parent['expected_area_m2'])

    def test_mask_csv_roundtrip_preserves_exact_native_indices_and_area_values(self):
        rows=exact_rows(case(1.25))
        with tempfile.TemporaryDirectory()as temporary:
            path=Path(temporary)/'toy-mask.csv'
            with path.open('w',newline='')as stream:
                writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','i','j','area_m2'])
                writer.writerows((pad,i,j,format(area,'.17g'))for pad,i,j,area in rows)
            self.assertEqual(rows,r.masks_from_csv(path))

    def test_duplicate_fragment_oversized_or_aggregate_overfull_faces_are_rejected(self):
        geometry=case(1.25);rows=exact_rows(geometry);face=(1.25/1000)**2
        duplicate=list(rows);duplicate.append(duplicate[0])
        overfull=list(rows);p,i,j,_=overfull[0];overfull[0]=(p,i,j,2*face)
        aggregate=[(p,i,j,.75*face if (i,j)==(20,20)else area)for p,i,j,area in rows]
        for invalid in (duplicate,overfull,aggregate):
            with self.assertRaises(ValueError):r.audit_mask_geometry(invalid,geometry)

    def test_bad_node_rotation_and_wrong_exact_rectangle_fragment_are_rejected(self):
        geometry=case(1.25);rows=exact_rows(geometry)
        invalid=copy.deepcopy(geometry);invalid['pad_node_ids'][0]=2;invalid['pads'][0]['node']=2
        with self.assertRaises(ValueError):r.audit_mask_geometry(rows,invalid)
        invalid=copy.deepcopy(geometry);invalid['pads'][0]['rotation_deg']=5.
        with self.assertRaises(ValueError):r.audit_mask_geometry(rows,invalid)
        invalid=list(rows);p,i,j,area=invalid[0];invalid[0]=(p,i,j,area*.99)
        with self.assertRaises(ValueError):r.audit_mask_geometry(invalid,geometry)


if __name__=='__main__':
    unittest.main()
