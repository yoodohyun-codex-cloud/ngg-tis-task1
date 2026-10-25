"""Pure one-return rotation fixtures; no native arrays or PDE are consumed."""
import copy
import csv
import io
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_one_return_rotation_registration as r
import task1_asymmetric_registration as asym
import task1_cross_registration as cross


class OneReturnRotationTests(unittest.TestCase):
    def setUp(self):
        baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                      if d['id']=='baseline-square15')
        self.prototype=cross.cross_design(baseline,12.5)
        self.design=asym.mixed_design(self.prototype)
        self.rows,self.areas,_=asym.aligned_mixed_mask(self.design)

    def test_exact_pad2_index_rotation_is_invertible_and_other_three_masks_are_unchanged(self):
        moved,areas,receipt=r.rotate_mask(self.rows)
        expected=sorted([(p,79-j,i-32,a)if p==2 else(p,i,j,a)for p,i,j,a in self.rows],
                        key=lambda row:(row[0],row[2],row[1]))
        self.assertEqual(expected,moved);self.assertEqual(self.areas,areas)
        self.assertEqual([row for row in self.rows if row[0]!=2],[row for row in moved if row[0]!=2])
        restored=sorted([(p,j+32,79-i,a)if p==2 else(p,i,j,a)for p,i,j,a in moved],
                        key=lambda row:(row[0],row[2],row[1]))
        self.assertEqual(self.rows,restored)
        self.assertEqual(set(range(47,65)),{i for p,i,j,a in moved if p==2})
        self.assertEqual(set(range(12,36)),{j for p,i,j,a in moved if p==2})

    def test_canonical_axis_aligned_metadata_proves_physical90degree_rotation_only_for_pad2(self):
        original=copy.deepcopy(self.design);moved=r.rotated_design(self.design)
        self.assertEqual(90,moved['applied_physical_rotation_deg'])
        self.assertEqual(2,moved['rotated_physical_pad_id'])
        for p in (0,1,3):self.assertEqual(self.design['pads'][p],moved['pads'][p])
        before,after=self.design['pads'][2],moved['pads'][2]
        self.assertEqual([10.,-10.],after['center_mm'])
        self.assertEqual(11.25,after['width_mm']);self.assertEqual(15.,after['height_mm'])
        self.assertEqual(0.,after['rotation_deg']);self.assertEqual(90,after['applied_physical_rotation_deg'])
        self.assertEqual([15.,11.25],after['original_intrinsic_dimensions_mm'])
        expected={(-y,x-20)for x,y in before['polygon_mm']}
        self.assertEqual(expected,{tuple(point)for point in after['polygon_mm']})
        for key in ('pad','role','source_output','indexed_pair','analytic_area_mm2','area_mm2','polygon_area_mm2'):
            self.assertEqual(before[key],after[key])
        self.assertEqual('all_return_pads_ideal_common_GND',moved['return_connection'])
        self.assertEqual(4,moved['total_pads']);self.assertEqual(2,moved['source_outputs'])
        self.assertEqual(original,self.design)

    def test_exact_counts_physical_gaps_and_all_contact_corners_stay_in_d50(self):
        moved=r.rotated_design(self.design);rows,areas,_=r.rotate_mask(self.rows)
        self.assertEqual(2304,len(rows));self.assertEqual(2304,len({(i,j)for _,i,j,_ in rows}))
        self.assertEqual([720,720,432,432],[sum(p==pad for p,_,_,_ in rows)for pad in range(4)])
        for actual,expected in zip(areas,(281.25,281.25,168.75,168.75)):
            self.assertAlmostEqual(expected,actual*1e6,places=10)
        self.assertAlmostEqual(900.,math.fsum(areas)*1e6,places=10)
        for _,i,j,area in rows:
            self.assertEqual((.625/1000)**2,area)
            self.assertTrue(all((-25+x*.625)**2+(-25+y*.625)**2<625
                                for x in (i,i+1)for y in (j,j+1)))
        pads=moved['pads'];rotated=pads[2]
        self.assertEqual(5.625,min(x for x,y in rotated['polygon_mm'])-max(x for x,y in pads[0]['polygon_mm']))
        self.assertEqual(3.75,min(y for x,y in pads[1]['polygon_mm'])-max(y for x,y in rotated['polygon_mm']))
        maximum=max(x*x+y*y for pad in pads for x,y in pad['polygon_mm'])
        self.assertEqual(615.625,maximum);self.assertLess(maximum,625.)

    def test_config_changes_only_pad2_intrinsic_width_height_and_mask_reference(self):
        original=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        _,prototype_areas,_=cross.aligned_cross_mask(self.prototype)
        prototype,_=cross.changed_cross_config(original,self.prototype,Path('/tmp/prototype'),'a'*64,prototype_areas)
        source,_=asym.changed_mask_config(prototype,Path('/tmp/asym'),'b'*64,self.areas)
        revised,changes=r.changed_rotation_config(source,Path('/tmp/rot90'),'c'*64)
        a,b=cross._properties(source),cross._properties(revised)
        allowed={'mask.path','mask.sha256','pad.2.width_mm','pad.2.height_mm'}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                         {k:v for k,v in b.items()if k not in allowed})
        self.assertEqual(11.25,float(b['pad.2.width_mm']));self.assertEqual(15.,float(b['pad.2.height_mm']))
        self.assertTrue(all(a[k]==b[k]for k in a if k.startswith('z.')or'represented_area'in k))

    def test_one_ulp_full_face_areas_are_preserved_and_invalid_source_or_fragments_are_rejected(self):
        below=math.nextafter((.625/1000)**2,0.)
        rows=[(p,i,j,below)for p,i,j,a in self.rows]
        moved,areas,_=r.rotate_mask(rows)
        self.assertTrue(all(a==below for p,i,j,a in moved))
        self.assertEqual([math.fsum(a for p,i,j,a in rows if p==pad)for pad in range(4)],areas)
        wrong=copy.deepcopy(self.design);wrong['id']='another-design'
        with self.assertRaises(ValueError):r.rotated_design(wrong)
        invalid=[]
        duplicate=list(self.rows);duplicate[1]=duplicate[0];invalid.append(duplicate)
        outside=list(self.rows);p,i,j,a=outside[0];outside[0]=(p,100,j,a);invalid.append(outside)
        for ratio in (.25,1-1e-8):
            changed=list(self.rows);p,i,j,a=changed[0];changed[0]=(p,i,j,a*ratio);invalid.append(changed)
        for rows in invalid:
            with self.assertRaises(ValueError):r.rotate_mask(rows)

    def test_csv_roundtrip_and_single_condition_resource_bound(self):
        rows,_,_=r.rotate_mask(self.rows);encoded=r._mask_bytes(rows)
        self.assertIsInstance(encoded,bytes)
        restored=[(int(row['pad']),int(row['i']),int(row['j']),float(row['area_m2']))
                  for row in csv.DictReader(io.StringIO(encoded.decode()))]
        self.assertEqual(rows,restored);self.assertEqual(encoded,r._mask_bytes(restored))
        self.assertEqual('asym-return2-rot90-xy80',r.CASE_ID)
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(351680*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1320,r.MIN_REMAINING_SECONDS)
        self.assertEqual(351680,cross._mesh(dict(h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40]))['cells'])


if __name__=='__main__':
    unittest.main()
