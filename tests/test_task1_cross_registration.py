import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_cross_registration as r


class CrossRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.baseline=next(d for d in json.loads((r.core.HIST/'inputs/designs.json').read_text())
                           if d['id']=='baseline-square15')
        self.template=r.core.read(r.core.HIST/'preregistration.json')['case_pool'][r.TEMPLATE_ID]
        self.config=(r.core.HIST/'configs'/(r.TEMPLATE_ID+'.properties')).read_bytes()

    def test_two_union_masks_have_exact_faces_and_area_without_corner_square(self):
        for arm,count,area in ((10.,640,250.),(12.5,720,281.25)):
            design=r.cross_design(self.baseline,arm)
            rows,areas,receipt=r.aligned_cross_mask(design)
            self.assertEqual(4*count,len(rows));self.assertEqual(len(rows),len({(i,j)for _,i,j,_ in rows}))
            self.assertTrue(all(a==(r.H_MM/1000)**2 for _,_,_,a in rows))
            for pad in range(4):
                self.assertEqual(count,sum(p==pad for p,_,_,_ in rows))
                self.assertAlmostEqual(area,areas[pad]*1e6,places=11)
            self.assertFalse(receipt['renormalization']);self.assertEqual(0,receipt['discarded_slivers'])
            self.assertEqual(2.5,receipt['bounding_box_gap_mm'])
            self.assertLess(receipt['maximum_physical_vertex_radius_mm'],25.)
            # A bounding-box square would extend outside D50; its corner is absent.
            self.assertGreater(math.hypot(18.75,18.75),25.)
            self.assertNotIn((1,69,69),{(p,i,j)for p,i,j,_ in rows})

    def test_honest_concave_outline_area_matches_union_and_wiring_stays_two_outputs(self):
        for arm in r.WIDTHS_MM:
            design=r.cross_design(self.baseline,arm)
            self.assertEqual(4,design['total_pads']);self.assertEqual(2,design['source_outputs'])
            self.assertEqual('all_return_pads_ideal_common_GND',design['return_connection'])
            for original,pad in zip(self.baseline['pads'],design['pads']):
                points=pad['polygon_mm']
                polygon_area=sum(x*v-u*y for (x,y),(u,v) in zip(points,points[1:]+points[:1]))/2
                self.assertEqual(12,len(points));self.assertEqual(pad['analytic_area_mm2'],polygon_area)
                for field in ('pad','center_mm','rotation_deg','role','source_output','indexed_pair'):
                    self.assertEqual(original[field],pad[field])
                turns=[(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
                       for a,b,c in zip(points,points[1:]+points[:1],points[2:]+points[:2])]
                self.assertLess(min(turns),0);self.assertGreater(max(turns),0)
            self.assertEqual(900.,sum(p['analytic_area_mm2'] for p in self.baseline['pads']))
            self.assertAlmostEqual(100*(design['physical_total_contact_area_mm2']/900-1),
                                   design['area_change_vs_four_square225_percent'])

    def test_config_changes_only_geometry_area_mask_preserving_interface_and_physics(self):
        a=r._properties(self.config)
        for arm in r.WIDTHS_MM:
            design=r.cross_design(self.baseline,arm);_,areas,_=r.aligned_cross_mask(design)
            revised,changes=r.changed_cross_config(self.config,design,Path('/tmp/cross-mask'),'a'*64,areas)
            b=r._properties(revised)
            allowed={'mask.path','mask.sha256'}|{f'pad.{p}.{key}' for p in range(4)
                for key in ('shape','width_mm','height_mm','analytic_area_mm2','represented_area_m2','arm_width_mm')}
            self.assertEqual(allowed,set(changes))
            self.assertEqual({k:v for k,v in a.items() if k not in allowed},
                             {k:v for k,v in b.items() if k not in allowed})
            self.assertEqual({f'pad.{p}.arm_width_mm'for p in range(4)},set(b)-set(a))
            self.assertEqual('3000,3030,9000,9090',b['frequencies'])
            self.assertTrue(all(b[k]==v for k,v in a.items() if k.startswith('z.')))

    def test_shift_rotation_wiring_and_area_mutations_are_rejected(self):
        r.validate_baseline_template(self.template,self.baseline,self.config)
        for field,value in (('center_mm',[-9.,-10.]),('rotation_deg',5),('source_output',1)):
            design=copy.deepcopy(self.baseline);design['pads'][0][field]=value
            with self.assertRaises(ValueError):r.validate_baseline_template(self.template,design,self.config)
        for field,value in (('center_mm',[-9.,-10.]),('rotation_deg',5),('area_mm2',225),('arm_width_mm',12.)):
            design=r.cross_design(self.baseline,10.);design['pads'][0][field]=value
            with self.assertRaises(ValueError):r.aligned_cross_mask(design)
        with self.assertRaises(ValueError):r.cross_design(self.baseline,15.)

    def test_future_half_mm_overlap_retains_partials_and_exact_area_no_renormalization(self):
        for arm,expected in ((10.,250.),(12.5,281.25)):
            for cx,cy in r.CENTRES_MM:
                areas=[r.cross_face_area_mm2(-25+i*.5,-25+j*.5,.5,cx,cy,arm)
                       for j in range(100) for i in range(100)]
                self.assertEqual(expected,math.fsum(areas))
                self.assertTrue(any(0<a<.25 for a in areas))
                self.assertEqual(.25,r.cross_face_area_mm2(cx,cy,.5,cx,cy,arm))

    def test_registration_is_two_bounded_conditions_and_never_runs_without_root_lock(self):
        mesh=r._mesh(dict(h_xy_mm=r.H_MM,sc_cells=2,bulk_counts=[14,14,40]))
        self.assertEqual(351680,mesh['cells']);self.assertEqual(422016000,2*mesh['cells']*600)
        self.assertEqual(2,len(r.CASE_IDS));self.assertEqual(800000,r.core.LIMITS['max_cells'])
        run=ROOT/'data-native/cloud-test-cross-no-execution'
        self.assertFalse(run.exists())
        with (patch.object(r,'_caller_owns_execution_lock',side_effect=ValueError('root lock absent')),
              patch.object(r.subprocess,'run') as command):
            with self.assertRaises(ValueError):r.prepare_cross(run)
            command.assert_not_called()
        self.assertFalse(run.exists())


if __name__=='__main__':
    unittest.main()
