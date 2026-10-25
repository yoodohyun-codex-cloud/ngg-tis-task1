"""Pure four-pad wiring contrast; no native data or simulations are read."""
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
import task1_adjacent_source_registration as r
import task1_cross_allocation_registration as allocation
import task1_cross_registration as cross


class AdjacentSourceRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                           if d['id']=='baseline-square15')
        self.source=allocation.allocation_design(self.baseline,225.)
        self.rows,self.areas,_=allocation.allocation_mask(self.source)

    def test_relabelled_design_preserves_each_physical_shape_and_canonical_roles(self):
        original=copy.deepcopy(self.source)
        moved=r.adjacent_design(self.source)
        self.assertEqual((0,2,1,3),r.OLD_PHYSICAL_PAD_BY_NEW)
        geometry=('shape','center_mm','width_mm','height_mm','outer_length_mm','arm_width_mm',
                  'rotation_deg','corner_radius_mm','polygon_mm','union_rectangles_mm',
                  'analytic_area_mm2','area_mm2','polygon_area_mm2')
        for new,old in enumerate(r.OLD_PHYSICAL_PAD_BY_NEW):
            a,b=self.source['pads'][old],moved['pads'][new]
            self.assertEqual(new,b['pad']);self.assertEqual(new%2,b['indexed_pair'])
            self.assertEqual('signal'if new<2 else'common_gnd_return',b['role'])
            self.assertEqual(new if new<2 else None,b['source_output'])
            for key in geometry:self.assertEqual(a[key],b[key])
        self.assertNotEqual(self.source['id'],moved['id'])
        self.assertNotEqual('baseline-square15',moved['id'])
        self.assertEqual(original,self.source)

    def test_sources_are_adjacent20mm_while_topology_remains_two_outputs_and_common_gnd(self):
        moved=r.adjacent_design(self.source)
        old=[p['center_mm']for p in self.source['pads'][:2]]
        new=[p['center_mm']for p in moved['pads'][:2]]
        self.assertAlmostEqual(math.sqrt(800),math.dist(*old))
        self.assertEqual(20.,math.dist(*new))
        self.assertEqual([[-10.,-10.],[10.,-10.]],new)
        self.assertEqual([[10.,10.],[-10.,10.]],[p['center_mm']for p in moved['pads'][2:]])
        self.assertEqual(4,moved['total_pads']);self.assertEqual(2,moved['source_outputs'])
        self.assertEqual('all_return_pads_ideal_common_GND',moved['return_connection'])
        self.assertTrue(all(p['source_output'] is None for p in moved['pads'][2:]))

    def test_mask_relabel_is_a_sorted_bijection_with225mm2_per_pad_and_no_geometry_change(self):
        rows,areas,receipt=r.relabel_mask(self.rows)
        old_to_new={old:new for new,old in enumerate(r.OLD_PHYSICAL_PAD_BY_NEW)}
        expected=sorted([(old_to_new[p],i,j,a)for p,i,j,a in self.rows],key=lambda row:(row[0],row[2],row[1]))
        self.assertEqual(expected,rows)
        self.assertEqual({(i,j,a)for _,i,j,a in self.rows},{(i,j,a)for _,i,j,a in rows})
        self.assertEqual(2304,len(rows));self.assertEqual(2304,len({(i,j)for _,i,j,_ in rows}))
        for pad in range(4):
            self.assertEqual(576,sum(p==pad for p,_,_,_ in rows))
            self.assertAlmostEqual(225.,areas[pad]*1e6,places=10)
        self.assertAlmostEqual(900.,math.fsum(areas)*1e6,places=10)
        for _,i,j,area in rows:
            self.assertEqual((.625/1000)**2,area)
            self.assertTrue(all((-25+x*.625)**2+(-25+y*.625)**2<625
                                for x in (i,i+1)for y in (j,j+1)))

    def test_config_swaps_only_pad1_and2_positions_and_mask_references(self):
        original=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        source,_=allocation.config_for_allocation(original,self.source,Path('/tmp/opposite-mask'),'a'*64,self.areas)
        revised,changes=r.changed_wiring_config(source,Path('/tmp/adjacent-mask'),'b'*64)
        a,b=cross._properties(source),cross._properties(revised)
        allowed={'mask.path','mask.sha256','pad.1.x_mm','pad.1.y_mm','pad.2.x_mm','pad.2.y_mm'}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                         {k:v for k,v in b.items()if k not in allowed})
        for axis in ('x_mm','y_mm'):
            self.assertEqual(float(a[f'pad.2.{axis}']),float(b[f'pad.1.{axis}']))
            self.assertEqual(float(a[f'pad.1.{axis}']),float(b[f'pad.2.{axis}']))
        self.assertTrue(all(a[k]==b[k]for k in a if k.startswith('z.')or k.startswith('pad.0.')))
        self.assertEqual('2',b['channels']);self.assertEqual('3000,3030,9000,9090',b['frequencies'])

    def test_duplicate_physical_faces_or_invalid_pad_ids_are_rejected(self):
        duplicate=list(self.rows);duplicate[1]=duplicate[0]
        with self.assertRaises(ValueError):r.relabel_mask(duplicate)
        bad=list(self.rows);pad,i,j,area=bad[0];bad[0]=(4,i,j,area)
        with self.assertRaises(ValueError):r.relabel_mask(bad)

    def test_native_csv_roundtrip_and_single_case_resource_bounds(self):
        rows,_,_=r.relabel_mask(self.rows)
        encoded=r._mask_bytes(rows);self.assertIsInstance(encoded,bytes)
        restored=[(int(row['pad']),int(row['i']),int(row['j']),float(row['area_m2']))
                  for row in csv.DictReader(io.StringIO(encoded.decode()))]
        self.assertEqual(rows,restored);self.assertEqual(encoded,r._mask_bytes(restored))
        self.assertEqual('balancedcross225-adjacent-sources-xy80',r.CASE_ID)
        self.assertNotEqual('baseline-square15-xy80',r.CASE_ID)
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(r.EXPECTED_CELLS*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1020,r.MIN_REMAINING_SECONDS)
        self.assertEqual(351680,cross._mesh(dict(h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40]))['cells'])


if __name__=='__main__':
    unittest.main()
