"""Pure geometry/config fixtures for one asymmetric four-pad proposal."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_asymmetric_registration as r
import task1_cross_registration as cross


class AsymmetricRegistrationTests(unittest.TestCase):
    def setUp(self):
        baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                      if d['id']=='baseline-square15')
        self.source=cross.cross_design(baseline,12.5)

    def test_exact_full_face_counts_areas_and_total900mm2(self):
        design=r.mixed_design(self.source)
        rows,areas,receipt=r.aligned_mixed_mask(design)
        face=(.625/1000)**2
        self.assertEqual(2304,len(rows));self.assertEqual(2304,len({(i,j)for _,i,j,_ in rows}))
        self.assertTrue(all(a==face for _,_,_,a in rows))
        for pad,count,area in ((0,720,281.25),(1,720,281.25),(2,432,168.75),(3,432,168.75)):
            self.assertEqual(count,sum(p==pad for p,_,_,_ in rows))
            self.assertAlmostEqual(area,areas[pad]*1e6,places=11)
        self.assertAlmostEqual(900.,math.fsum(areas)*1e6,places=10)
        self.assertEqual(1125.,sum(p['analytic_area_mm2']for p in self.source['pads']))
        for _,i,j,_ in rows:
            self.assertTrue(all((-25+x*.625)**2+(-25+y*.625)**2<625
                                for x in (i,i+1)for y in (j,j+1)))

    def test_source_contacts_and_all_pad_wiring_and_centres_are_preserved(self):
        design=r.mixed_design(self.source)
        self.assertEqual(4,design['total_pads']);self.assertEqual(2,design['source_outputs'])
        self.assertEqual('all_return_pads_ideal_common_GND',design['return_connection'])
        for original,pad in zip(self.source['pads'],design['pads']):
            for key in ('pad','center_mm','rotation_deg','corner_radius_mm','role','source_output','indexed_pair'):
                self.assertEqual(original[key],pad[key])
        for original,pad in zip(self.source['pads'][:2],design['pads'][:2]):
            for key in ('shape','width_mm','height_mm','outer_length_mm','arm_width_mm',
                        'polygon_mm','analytic_area_mm2','area_mm2','polygon_area_mm2'):
                self.assertEqual(original[key],pad[key])
        self.assertEqual(self.source,cross.cross_design(
            next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                 if d['id']=='baseline-square15'),12.5))

    def test_returns_are_honest15_by11p25_rectangles_with_four_vertices(self):
        design=r.mixed_design(self.source)
        for pad in design['pads'][2:]:
            self.assertEqual('rectangle',pad['shape'])
            self.assertEqual(15.,pad['width_mm']);self.assertEqual(11.25,pad['height_mm'])
            self.assertEqual(168.75,pad['analytic_area_mm2'])
            x,y=pad['center_mm'];expected={(x-7.5,y-5.625),(x+7.5,y-5.625),
                                         (x+7.5,y+5.625),(x-7.5,y+5.625)}
            self.assertEqual(4,len(pad['polygon_mm']))
            self.assertEqual(expected,{tuple(p)for p in pad['polygon_mm']})
            points=pad['polygon_mm']
            area=abs(sum(x*v-u*y for (x,y),(u,v)in zip(points,points[1:]+points[:1]))/2)
            self.assertEqual(168.75,area)

    def test_config_changes_only_mask_area_and_honest_return_geometry_descriptors(self):
        original=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        _,old_areas,_=cross.aligned_cross_mask(self.source)
        source_data,_=cross.changed_cross_config(original,self.source,Path('/tmp/source-mask.csv'),'a'*64,old_areas)
        _,new_areas,_=r.aligned_mixed_mask(r.mixed_design(self.source))
        revised,changes=r.changed_mask_config(source_data,Path('/tmp/new-mask.csv'),'b'*64,new_areas)
        a,b=cross._properties(source_data),cross._properties(revised)
        removed={f'pad.{p}.arm_width_mm'for p in (2,3)}
        allowed={'mask.path','mask.sha256'}|{f'pad.{p}.represented_area_m2'for p in range(4)}|{
            f'pad.{p}.{key}'for p in (2,3)for key in ('shape','width_mm','height_mm','analytic_area_mm2','arm_width_mm')}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(a)-removed,set(b))
        self.assertTrue(all(changes[key] is None for key in removed))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                         {k:v for k,v in b.items()if k not in allowed})
        for pad,area in enumerate((281.25,281.25,168.75,168.75)):
            self.assertAlmostEqual(area,float(b[f'pad.{pad}.represented_area_m2'])*1e6,places=11)
        self.assertTrue(all(a[key]==b[key]for key in a if key.startswith('z.')))
        for p in (2,3):
            self.assertEqual('rectangle',b[f'pad.{p}.shape'])
            self.assertEqual(15.,float(b[f'pad.{p}.width_mm']))
            self.assertEqual(11.25,float(b[f'pad.{p}.height_mm']))
            self.assertEqual(168.75,float(b[f'pad.{p}.analytic_area_mm2']))
        for p in (0,1):
            for key in ('shape','width_mm','height_mm','analytic_area_mm2','arm_width_mm'):
                self.assertEqual(a[f'pad.{p}.{key}'],b[f'pad.{p}.{key}'])
        self.assertEqual('0.625',b['h_mm']);self.assertEqual('2',b['validation.sc_cells'])
        self.assertEqual('14,14,40',b['bulk.counts'])

    def test_mask_rejects_shift_rotation_wiring_or_physical_area_change(self):
        for pad,key,value in ((0,'center_mm',[-9.375,-10.]),(2,'center_mm',[10.,-9.375]),
                              (0,'rotation_deg',5.),(2,'rotation_deg',90.),
                              (0,'source_output',1),(2,'role','signal'),
                              (0,'analytic_area_mm2',225.),(2,'analytic_area_mm2',225.)):
            design=r.mixed_design(self.source);design['pads'][pad][key]=value
            with self.assertRaises(ValueError):r.aligned_mixed_mask(design)

    def test_fixed_single_case_cell_and_raw_bounds(self):
        self.assertEqual('asym-cross281p25-return168p75-xy80',r.CASE_ID)
        self.assertEqual(351680,r.EXPECTED_CELLS)
        self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(r.EXPECTED_RAW_BOUND_BYTES,r.EXPECTED_CELLS*600)
        self.assertEqual(351680,cross._mesh(dict(h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40]))['cells'])


if __name__=='__main__':
    unittest.main()
