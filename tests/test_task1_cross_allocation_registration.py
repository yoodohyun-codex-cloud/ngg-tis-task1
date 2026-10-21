"""Pure fixed-total-area cross allocation fixtures; no simulation executes."""
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
import task1_cross_allocation_registration as r
import task1_cross_registration as cross


class CrossAllocationTests(unittest.TestCase):
    def setUp(self):
        self.baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                           if d['id']=='baseline-square15')

    def test_all_three_allocations_have_exact_full_faces_and900mm2_without_overlap(self):
        for source_area,source_count,return_count in ((200.,512,640),(225.,576,576),(250.,640,512)):
            design=r.allocation_design(self.baseline,source_area)
            rows,areas,receipt=r.allocation_mask(design)
            self.assertEqual(2304,len(rows));self.assertEqual(2304,len({(i,j)for _,i,j,_ in rows}))
            self.assertTrue(all(a==(.625/1000)**2 for _,_,_,a in rows))
            for pad,count,area in ((0,source_count,source_area),(1,source_count,source_area),
                                   (2,return_count,450-source_area),(3,return_count,450-source_area)):
                self.assertEqual(count,sum(p==pad for p,_,_,_ in rows))
                self.assertAlmostEqual(area,areas[pad]*1e6,places=10)
            self.assertAlmostEqual(900.,math.fsum(areas)*1e6,places=10)
            for _,i,j,_ in rows:
                self.assertTrue(all((-25+x*.625)**2+(-25+y*.625)**2<625
                                    for x in (i,i+1)for y in (j,j+1)))

    def test_honest_concave_polygons_rectangular_primitives_and_wiring(self):
        before=copy.deepcopy(self.baseline)
        for source_area,source_length in ((200.,15.),(225.,16.25),(250.,17.5)):
            design=r.allocation_design(self.baseline,source_area)
            self.assertEqual(4,design['total_pads']);self.assertEqual(2,design['source_outputs'])
            self.assertEqual('all_return_pads_ideal_common_GND',design['return_connection'])
            for original,pad in zip(self.baseline['pads'],design['pads']):
                length=source_length if pad['pad']<2 else 32.5-source_length
                expected_area=source_area if pad['pad']<2 else 450-source_area
                self.assertEqual('cross',pad['shape']);self.assertEqual(10.,pad['arm_width_mm'])
                self.assertEqual(length,pad['outer_length_mm'])
                self.assertEqual(length,pad['width_mm']);self.assertEqual(length,pad['height_mm'])
                self.assertEqual(expected_area,pad['analytic_area_mm2'])
                for key in ('pad','center_mm','rotation_deg','corner_radius_mm','role','source_output','indexed_pair'):
                    self.assertEqual(original[key],pad[key])
                points=pad['polygon_mm'];self.assertEqual(12,len(points))
                signed_area=sum(x*v-u*y for (x,y),(u,v)in zip(points,points[1:]+points[:1]))/2
                self.assertEqual(expected_area,signed_area)
                turns=[(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
                       for a,b,c in zip(points,points[1:]+points[:1],points[2:]+points[:2])]
                self.assertLess(min(turns),0.);self.assertGreater(max(turns),0.)
                rectangles=pad['union_rectangles_mm'];self.assertEqual(2,len(rectangles))
                self.assertEqual({(length,10.),(10.,length)},
                                 {(p['width_mm'],p['height_mm'])for p in rectangles})
                self.assertTrue(all(p['center_mm']==pad['center_mm']for p in rectangles))
                self.assertTrue(all(math.hypot(x,y)<25. for x,y in points))
            self.assertEqual((source_area-225)/20,source_length-16.25)
        self.assertEqual(before,self.baseline)

    def test_source_return_gap_is_constant3p75_and_outermost_contact_stays_inside_d50(self):
        for area in (200.,225.,250.):
            design=r.allocation_design(self.baseline,area)
            pads=design['pads']
            def extent(pad,axis,minimum):
                return (min if minimum else max)(p[axis]for p in pad['polygon_mm'])
            self.assertEqual(3.75,extent(pads[2],0,True)-extent(pads[0],0,False))
            self.assertEqual(3.75,extent(pads[3],1,True)-extent(pads[0],1,False))
            self.assertEqual(3.75,extent(pads[1],1,True)-extent(pads[2],1,False))
            self.assertEqual(3.75,extent(pads[1],0,True)-extent(pads[3],0,False))
            radius=max(math.hypot(x,y)for p in pads for x,y in p['polygon_mm'])
            self.assertLessEqual(radius,math.hypot(18.75,15.))
            self.assertLess(radius,25.)

    def test_config_allowlist_changes_contact_geometry_and_mask_but_preserves_models_and_circuit(self):
        raw=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        a=cross._properties(raw)
        for area in (200.,225.,250.):
            design=r.allocation_design(self.baseline,area);_,areas,_=r.allocation_mask(design)
            revised,changes=r.config_for_allocation(raw,design,Path('/tmp/allocation-mask'),'a'*64,areas)
            b=cross._properties(revised)
            allowed={'mask.path','mask.sha256'}|{f'pad.{p}.{key}'for p in range(4)
                for key in ('shape','width_mm','height_mm','analytic_area_mm2','represented_area_m2','arm_width_mm')}
            self.assertEqual(allowed,set(changes))
            self.assertEqual(set(a)|{f'pad.{p}.arm_width_mm'for p in range(4)},set(b))
            self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                             {k:v for k,v in b.items()if k not in allowed})
            for p,pad in enumerate(design['pads']):
                self.assertEqual('cross',b[f'pad.{p}.shape'])
                self.assertEqual(10.,float(b[f'pad.{p}.arm_width_mm']))
                self.assertEqual(pad['outer_length_mm'],float(b[f'pad.{p}.width_mm']))
                self.assertEqual(pad['analytic_area_mm2'],float(b[f'pad.{p}.analytic_area_mm2']))
                self.assertAlmostEqual(pad['analytic_area_mm2'],float(b[f'pad.{p}.represented_area_m2'])*1e6,places=10)
            self.assertTrue(all(a[k]==b[k]for k in a if k.startswith('z.')))
            self.assertEqual('2',b['channels']);self.assertEqual('3000,3030,9000,9090',b['frequencies'])

    def test_unknown_allocation_and_mutated_geometry_are_rejected(self):
        for area in (0.,199.,225.1,251.):
            with self.assertRaises(ValueError):r.allocation_design(self.baseline,area)
        for index,key,value in ((0,'center_mm',[-9.375,-10.]),(2,'rotation_deg',5.),
                                (0,'arm_width_mm',12.5),(1,'analytic_area_mm2',250.),
                                (2,'role','signal')):
            design=r.allocation_design(self.baseline,225.)
            design['pads'][index][key]=value
            with self.assertRaises(ValueError):r.allocation_mask(design)

    def test_native_csv_roundtrip_and_exact_three_case_resource_bounds(self):
        for area in (200.,225.,250.):
            rows,_,_=r.allocation_mask(r.allocation_design(self.baseline,area))
            encoded=r._mask_bytes(rows);self.assertIsInstance(encoded,bytes)
            restored=[(int(row['pad']),int(row['i']),int(row['j']),float(row['area_m2']))
                      for row in csv.DictReader(io.StringIO(encoded.decode()))]
            self.assertEqual(rows,restored);self.assertEqual(encoded,r._mask_bytes(restored))
        self.assertEqual((200.,225.,250.),r.SOURCE_AREAS)
        self.assertEqual(('crossalloc-source200-return250-xy80','crossalloc-source225-return225-xy80',
                          'crossalloc-source250-return200-xy80'),r.CASE_IDS)
        self.assertEqual(351680,r.EXPECTED_CELLS)
        bound=getattr(r,'EXPECTED_RAW_BOUND_BYTES',getattr(r,'TOTAL_RAW_BOUND_BYTES',None))
        self.assertEqual(633024000,bound);self.assertEqual(3*351680*600,bound)
        self.assertEqual(2700,r.MIN_REMAINING_SECONDS)
        self.assertEqual(351680,cross._mesh(dict(h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40]))['cells'])


if __name__=='__main__':
    unittest.main()
