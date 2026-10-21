"""Pure rigid-return-position fixtures; no simulation or native data reads."""
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
import task1_return_position_registration as r
import task1_asymmetric_registration as asym
import task1_cross_registration as cross


class ReturnPositionRegistrationTests(unittest.TestCase):
    def setUp(self):
        baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                      if d['id']=='baseline-square15')
        self.prototype=cross.cross_design(baseline,12.5)
        self.design=asym.mixed_design(self.prototype)
        self.rows,self.areas,_=asym.aligned_mixed_mask(self.design)

    def test_return_masks_are_exact_integer_translations_and_sources_unchanged(self):
        for delta in (.625,-.625):
            translated,areas,receipt=r.translated_mask(self.rows,delta)
            sign=1 if delta>0 else -1
            expected=[(pad,i+(sign if pad==2 else -sign if pad==3 else 0),
                        j+(-sign if pad==2 else sign if pad==3 else 0),area)
                      for pad,i,j,area in self.rows]
            self.assertEqual(expected,translated)
            self.assertEqual([row for row in self.rows if row[0]<2],
                             [row for row in translated if row[0]<2])
            self.assertEqual(self.areas,areas)
            self.assertEqual(2304,len(translated))
            self.assertEqual(2304,len({(i,j)for _,i,j,_ in translated}))
            self.assertEqual([720,720,432,432],[sum(p==pad for p,_,_,_ in translated)for pad in range(4)])
            self.assertAlmostEqual(900.,math.fsum(areas)*1e6,places=10)
            self.assertTrue(all(area==(.625/1000)**2 for _,_,_,area in translated))

    def test_native_mask_serialization_is_exact_ordered_and_lossless(self):
        area=(.625/1000)**2
        fixture=[(0,14,10,area),(2,45,14,area)]
        expected=('pad,i,j,area_m2\n0,14,10,'+format(area,'.17g')+'\n2,45,14,'+format(area,'.17g')+'\n').encode()
        self.assertEqual(expected,r._mask_bytes(fixture))
        for delta in (.625,-.625):
            rows,_,_=r.translated_mask(self.rows,delta)
            encoded=r._mask_bytes(rows)
            self.assertNotIn(b'\r',encoded);self.assertTrue(encoded.endswith(b'\n'))
            decoded=[(int(row['pad']),int(row['i']),int(row['j']),float(row['area_m2']))
                     for row in csv.DictReader(io.StringIO(encoded.decode()))]
            self.assertEqual(rows,decoded)
            self.assertEqual(encoded,r._mask_bytes(decoded))

    def test_design_metadata_rigidly_translates_only_the_two_return_rectangles(self):
        before=copy.deepcopy(self.design)
        for delta in (.625,-.625):
            moved=r.translated_design(self.design,delta)
            self.assertEqual(self.design['pads'][:2],moved['pads'][:2])
            self.assertEqual(4,moved['total_pads']);self.assertEqual(2,moved['source_outputs'])
            self.assertEqual('all_return_pads_ideal_common_GND',moved['return_connection'])
            for index,dx,dy in ((2,delta,-delta),(3,-delta,delta)):
                original,pad=self.design['pads'][index],moved['pads'][index]
                self.assertEqual([original['center_mm'][0]+dx,original['center_mm'][1]+dy],pad['center_mm'])
                self.assertEqual([[x+dx,y+dy]for x,y in original['polygon_mm']],pad['polygon_mm'])
                for key in ('pad','shape','width_mm','height_mm','rotation_deg','role','source_output',
                            'analytic_area_mm2','area_mm2','polygon_area_mm2','indexed_pair'):
                    self.assertEqual(original[key],pad[key])
                self.assertEqual(10.+delta,abs(pad['center_mm'][0]))
                self.assertEqual(10.+delta,abs(pad['center_mm'][1]))
        self.assertEqual(before,self.design)

    def test_config_changes_only_return_positions_and_mask_reference_not_area_or_physics(self):
        raw=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        _,prototype_areas,_=cross.aligned_cross_mask(self.prototype)
        prototype,_=cross.changed_cross_config(raw,self.prototype,Path('/tmp/prototype-mask'),'a'*64,prototype_areas)
        source,_=asym.changed_mask_config(prototype,Path('/tmp/asym-mask'),'b'*64,self.areas)
        for delta in (.625,-.625):
            revised,changes=r.changed_position_config(source,Path('/tmp/moved-mask'),'c'*64,delta)
            a,b=cross._properties(source),cross._properties(revised)
            allowed={'mask.path','mask.sha256','pad.2.x_mm','pad.2.y_mm','pad.3.x_mm','pad.3.y_mm'}
            self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
            self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                             {k:v for k,v in b.items()if k not in allowed})
            self.assertEqual(10.+delta,float(b['pad.2.x_mm']))
            self.assertEqual(-10.-delta,float(b['pad.2.y_mm']))
            self.assertEqual(-10.-delta,float(b['pad.3.x_mm']))
            self.assertEqual(10.+delta,float(b['pad.3.y_mm']))
            self.assertTrue(all(a[k]==b[k]for k in a if k.startswith('z.')or'represented_area' in k))

    def test_all_translated_physical_vertices_and_native_contact_faces_stay_inside_d50(self):
        for delta in (.625,-.625):
            design=r.translated_design(self.design,delta)
            for pad in design['pads']:
                self.assertTrue(all(math.hypot(x,y)<25 for x,y in pad['polygon_mm']))
            rows,_,_=r.translated_mask(self.rows,delta)
            for _,i,j,_ in rows:
                self.assertTrue(all((-25+x*.625)**2+(-25+y*.625)**2<625
                                    for x in (i,i+1)for y in (j,j+1)))
            returns=max(math.hypot(x,y)for p in design['pads'][2:]for x,y in p['polygon_mm'])
            self.assertAlmostEqual(math.hypot(17.5+delta,15.625+delta),returns,places=12)
            self.assertGreater(25.-returns,0.)
        outward=r.translated_design(self.design,.625)
        radius=max(math.hypot(x,y)for p in outward['pads'][2:]for x,y in p['polygon_mm'])
        self.assertAlmostEqual(24.3429276,radius,places=6)

    def test_unregistered_delta_and_corrupted_source_geometry_or_mask_are_rejected(self):
        for delta in (0.,1.25,-1.25):
            with self.assertRaises(ValueError):r.translated_design(self.design,delta)
            with self.assertRaises(ValueError):r.translated_mask(self.rows,delta)
        oversized=copy.deepcopy(self.design);oversized['pads'][2]['width_mm']=30.
        with self.assertRaises(ValueError):r.translated_design(oversized,.625)
        corruptions=[]
        bad=list(self.rows);pad,i,j,area=bad[0];bad[0]=(pad,i,j,area*2);corruptions.append(bad)
        bad=list(self.rows);pad,i,j,area=bad[0];bad[0]=(4,i,j,area);corruptions.append(bad)
        bad=list(self.rows);bad[1]=bad[0];corruptions.append(bad)
        for rows in corruptions:
            with self.assertRaises(ValueError):r.translated_mask(rows,.625)

    def test_exact_two_case_resource_bounds_preserve_fixed_domain_and_budget_floor(self):
        self.assertEqual(('asym-return-out0p625-xy80','asym-return-in0p625-xy80'),r.CASE_IDS)
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(422016000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(2*r.EXPECTED_CELLS*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1800,r.MIN_REMAINING_SECONDS)
        self.assertEqual(351680,cross._mesh(dict(h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40]))['cells'])


if __name__=='__main__':
    unittest.main()
