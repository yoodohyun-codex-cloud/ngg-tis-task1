"""Pure inward-source geometry fixtures; no simulation or native audit."""
import copy
import csv
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_source_position_registration as r
import task1_asymmetric_registration as asym
import task1_cross_registration as cross


def mask_bytes(rows):
    stream=io.StringIO(newline='')
    writer=csv.writer(stream,lineterminator='\n');writer.writerow(['pad','i','j','area_m2'])
    writer.writerows((pad,i,j,format(area,'.17g'))for pad,i,j,area in rows)
    return stream.getvalue().encode()


class SourcePositionRegistrationTests(unittest.TestCase):
    def setUp(self):
        baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())
                      if d['id']=='baseline-square15')
        self.prototype=cross.cross_design(baseline,12.5)
        self.design=asym.mixed_design(self.prototype)
        self.rows,self.areas,_=asym.aligned_mixed_mask(self.design)

    def test_exact_integer_source_translation_preserves_every_return_tuple_and_area(self):
        for delta in (-.625,-1.25):
            step=round(delta/.625)
            moved,areas,receipt=r.translated_mask(self.rows,delta)
            expected=[(pad,i+(-step if pad==0 else step if pad==1 else 0),
                        j+(-step if pad==0 else step if pad==1 else 0),area)
                      for pad,i,j,area in self.rows]
            self.assertEqual(expected,moved);self.assertEqual(self.areas,areas)
            self.assertEqual([row for row in self.rows if row[0]>=2],[row for row in moved if row[0]>=2])
            self.assertEqual(2304,len(moved));self.assertEqual(2304,len({(i,j)for _,i,j,_ in moved}))
            self.assertEqual([720,720,432,432],[sum(p==pad for p,_,_,_ in moved)for pad in range(4)])
            self.assertAlmostEqual(900.,math.fsum(areas)*1e6,places=10)
            self.assertTrue(all(area==(.625/1000)**2 for _,_,_,area in moved))

    def test_design_moves_only_sources_rigidly_and_preserves_positive_physical_gaps(self):
        original=copy.deepcopy(self.design)
        for delta in (-.625,-1.25):
            moved=r.translated_design(self.design,delta)
            self.assertEqual(self.design['pads'][2:],moved['pads'][2:])
            for pad,dx in ((0,-delta),(1,delta)):
                before,after=self.design['pads'][pad],moved['pads'][pad]
                self.assertEqual([v+dx for v in before['center_mm']],after['center_mm'])
                self.assertEqual([[x+dx,y+dx]for x,y in before['polygon_mm']],after['polygon_mm'])
                for old_rect,new_rect in zip(before['union_rectangles_mm'],after['union_rectangles_mm']):
                    self.assertEqual([v+dx for v in old_rect['center_mm']],new_rect['center_mm'])
                    self.assertEqual(old_rect['width_mm'],new_rect['width_mm'])
                    self.assertEqual(old_rect['height_mm'],new_rect['height_mm'])
                for key in ('pad','shape','width_mm','height_mm','outer_length_mm','arm_width_mm',
                            'role','source_output','indexed_pair','analytic_area_mm2','area_mm2','rotation_deg'):
                    self.assertEqual(before[key],after[key])
            self.assertEqual(4,moved['total_pads']);self.assertEqual(2,moved['source_outputs'])
            self.assertEqual('all_return_pads_ideal_common_GND',moved['return_connection'])
            self.assertTrue(all(math.hypot(x,y)<25 for p in moved['pads']for x,y in p['polygon_mm']))
            source_right=max(x for x,y in moved['pads'][0]['polygon_mm'])
            return_left=min(x for x,y in moved['pads'][2]['polygon_mm'])
            self.assertEqual(3.75+delta,return_left-source_right)
            self.assertGreater(return_left-source_right,0.)
            a=10.+delta
            source_source_gap=(4*a-30)/math.sqrt(2)
            self.assertGreater(source_source_gap,0.)
            self.assertAlmostEqual(5.303300858899107 if delta==-.625 else 3.5355339059327373,
                                   source_source_gap,places=12)
        self.assertEqual(original,self.design)

    def test_mask_roundtrip_is_exact_and_return_serialization_remains_identical(self):
        for delta in (-.625,-1.25):
            moved,_,_=r.translated_mask(self.rows,delta)
            encoded=r._mask_bytes(moved)
            self.assertEqual(mask_bytes(moved),encoded)
            decoded=[(int(row['pad']),int(row['i']),int(row['j']),float(row['area_m2']))
                     for row in csv.DictReader(io.StringIO(encoded.decode()))]
            self.assertEqual(moved,decoded);self.assertEqual(encoded,mask_bytes(decoded))
            self.assertEqual(mask_bytes([row for row in self.rows if row[0]>=2]),
                             r._mask_bytes([row for row in moved if row[0]>=2]))
            for _,i,j,_ in moved:
                self.assertTrue(all((-25+x*.625)**2+(-25+y*.625)**2<625
                                    for x in (i,i+1)for y in (j,j+1)))

    def test_only_signal_xy_and_mask_config_fields_change(self):
        original=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        _,prototype_areas,_=cross.aligned_cross_mask(self.prototype)
        prototype,_=cross.changed_cross_config(original,self.prototype,Path('/tmp/prototype'),'a'*64,prototype_areas)
        source,_=asym.changed_mask_config(prototype,Path('/tmp/source'),'b'*64,self.areas)
        for delta in (-.625,-1.25):
            revised,changes=r.changed_position_config(source,Path('/tmp/moved'),'c'*64,delta)
            a,b=cross._properties(source),cross._properties(revised)
            allowed={'mask.path','mask.sha256','pad.0.x_mm','pad.0.y_mm','pad.1.x_mm','pad.1.y_mm'}
            self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
            self.assertEqual({k:v for k,v in a.items()if k not in allowed},
                             {k:v for k,v in b.items()if k not in allowed})
            self.assertEqual(-10.-delta,float(b['pad.0.x_mm']))
            self.assertEqual(-10.-delta,float(b['pad.0.y_mm']))
            self.assertEqual(10.+delta,float(b['pad.1.x_mm']))
            self.assertEqual(10.+delta,float(b['pad.1.y_mm']))
            self.assertTrue(all(a[k]==b[k]for k in a if k.startswith('z.')or'represented_area' in k))

    def test_outward_cross_is_outside_d50_and_unregistered_or_corrupt_inputs_are_rejected(self):
        self.assertEqual(660.15625,19.375**2+16.875**2)
        self.assertGreater(19.375**2+16.875**2,625.)
        for delta in (.625,0.,-1.875):
            with self.assertRaises(ValueError):r.translated_design(self.design,delta)
            with self.assertRaises(ValueError):r.translated_mask(self.rows,delta)
        bad=copy.deepcopy(self.design);bad['pads'][0]['arm_width_mm']=15.
        with self.assertRaises(ValueError):r.translated_design(bad,-.625)
        corrupt=[]
        bad=list(self.rows);pad,i,j,area=bad[0];bad[0]=(pad,i,j,area*2);corrupt.append(bad)
        bad=list(self.rows);pad,i,j,area=bad[0];bad[0]=(4,i,j,area);corrupt.append(bad)
        bad=list(self.rows);bad[1]=bad[0];corrupt.append(bad)
        for rows in corrupt:
            with self.assertRaises(ValueError):r.translated_mask(rows,-.625)

    def test_two_fixed_inward_conditions_keep_resource_bounds(self):
        self.assertEqual((-.625,-1.25),r.DELTAS)
        self.assertEqual(('asym-source-in0p625-xy80','asym-source-in1p25-xy80'),r.CASE_IDS)
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(422016000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(2*r.EXPECTED_CELLS*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1800,r.MIN_REMAINING_SECONDS)

    def test_root_decision_requires_both_actual_completed_return_cases_and_volume_report(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);run=root/'data-native/cloud-return-fixture';(run/'cases').mkdir(parents=True)
            cases=[];returns=[];sources={};volume_rows=[]
            for ident in r.RETURN_IDS:
                folder=run/'postprocess'/ident;folder.mkdir(parents=True)
                summary=folder/'summary.json';summary.write_text(json.dumps(dict(id=ident,status='complete')))
                config,mask=run/(ident+'.properties'),run/(ident+'.csv')
                config.write_text('synthetic config metadata\n');mask.write_text('synthetic mask metadata\n')
                record=run/'cases'/(ident+'.json')
                record.write_text(json.dumps(dict(id=ident,status='complete',postprocess_path=str(summary),
                    postprocess_sha256=r.core.sha(summary),validation={key:0. for key in r.core.GATES})))
                cases.append(dict(id=ident,h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40],channels=2,cells=351680,
                    config_file=str(config),config_sha256=r.core.sha(config),mask_file=str(mask),mask_sha256=r.core.sha(mask)))
                returns.append(dict(case_id=ident,summary_path=str(summary),summary_sha256=r.core.sha(summary),
                    case_record_path=str(record),case_record_sha256=r.core.sha(record)))
                sources[str(summary)]=r.core.sha(summary);volume_rows.append(dict(case_id=ident,summary_path=str(summary)))
            (run/'preregistration.json').write_text(json.dumps(dict(cases=cases)))
            report=root/'return-volume.json'
            report.write_text(json.dumps(dict(status='calculated_unadopted',inputs_unchanged=True,cases=volume_rows,inputs_sha256=sources)))
            decision=dict(schema='task1-source-position-decision-v1',status='preregistered_not_started',
                source_run_id=r.SOURCE_RUN,source_case_id=r.SOURCE_ID,case_ids=list(r.CASE_IDS),
                chosen_question='Explicit source-spacing contrast after reviewing both completed return results',
                return_results=returns,return_volume_report=dict(path=str(report),sha256=r.core.sha(report)))
            path=root/'decision.json';path.write_text(json.dumps(decision))
            with patch.object(r.core,'REPO',root):
                receipt,pins=r.verify_root_decision(path)
                self.assertEqual(list(r.RETURN_IDS),receipt['actual_return_case_ids'])
                self.assertIn(str(report),pins)
                for item in returns:self.assertIn(item['summary_path'],pins)
                # Even with updated hashes, an unfinished case cannot be admitted.
                record=Path(returns[0]['case_record_path']);data=json.loads(record.read_text());data['status']='running'
                record.write_text(json.dumps(data));decision['return_results'][0]['case_record_sha256']=r.core.sha(record)
                path.write_text(json.dumps(decision))
                with self.assertRaises(ValueError):r.verify_root_decision(path)
        self.assertEqual(351680,cross._mesh(dict(h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40]))['cells'])


if __name__=='__main__':
    unittest.main()
