"""Synthetic geometry/config/context fixtures; no native arrays or solves."""
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import task1_tangential_return_registration as r
import task1_cross_registration as cross
import task1_asymmetric_registration as asym


class TangentialGeometryTests(unittest.TestCase):
    def setUp(self):
        baseline=next(d for d in json.loads((cross.core.HIST/'inputs/designs.json').read_text())if d['id']=='baseline-square15')
        self.prototype=cross.cross_design(baseline,12.5)
        self.design=asym.mixed_design(self.prototype)
        self.rows,self.areas,_=asym.aligned_mixed_mask(self.design)

    def test_integer_translation_is_invertible_and_original_two_sources_are_byte_exact(self):
        moved,areas,receipt=r.translate_mask(self.rows)
        expected=sorted([(p,i+r.SHIFT.get(p,(0,0))[0],j+r.SHIFT.get(p,(0,0))[1],a)for p,i,j,a in self.rows],
                        key=lambda row:(row[0],row[2],row[1]))
        self.assertEqual(expected,moved);self.assertEqual(self.areas,areas)
        restored=sorted([(p,i-r.SHIFT.get(p,(0,0))[0],j-r.SHIFT.get(p,(0,0))[1],a)for p,i,j,a in moved],
                        key=lambda row:(row[0],row[2],row[1]))
        self.assertEqual(self.rows,restored)
        self.assertTrue(r.source_mask_bytes_unchanged(r._mask_bytes(self.rows),r._mask_bytes(moved)))
        damaged=list(moved);p,i,j,a=damaged[0];damaged[0]=(p,i,j,math.nextafter(a,0.))
        with self.assertRaisesRegex(ValueError,'byte-exact'):
            r.source_mask_bytes_unchanged(r._mask_bytes(self.rows),r._mask_bytes(damaged))
        self.assertEqual({'2':[7,7],'3':[-7,-7]},receipt['return_shift_grid_indices'])

    def test_metadata_centres_polygons_xy_and_wiring_change_only_the_return_translation(self):
        original=copy.deepcopy(self.design);moved=r.translated_design(self.design)
        self.assertEqual(original,self.design)
        for p in(0,1):self.assertEqual(self.design['pads'][p],moved['pads'][p])
        for p,shift in r.SHIFT.items():
            old,new=self.design['pads'][p],moved['pads'][p];dx,dy=[v*.625 for v in shift]
            self.assertEqual([old['center_mm'][0]+dx,old['center_mm'][1]+dy],new['center_mm'])
            self.assertEqual([[x+dx,y+dy]for x,y in old['polygon_mm']],new['polygon_mm'])
            for key in('pad','role','source_output','indexed_pair','shape','width_mm','height_mm','rotation_deg',
                       'analytic_area_mm2','area_mm2','polygon_area_mm2'):
                self.assertEqual(old[key],new[key])
        self.assertEqual([p['center_mm']for p in moved['pads']],moved['xy_mm'])
        self.assertEqual([14.375,-5.625],moved['pads'][2]['center_mm'])
        self.assertEqual([-14.375,5.625],moved['pads'][3]['center_mm'])
        self.assertEqual('all_return_pads_ideal_common_GND',moved['return_connection'])
        self.assertEqual(4,moved['total_pads']);self.assertEqual(2,moved['source_outputs'])
        self.assertEqual(0,moved['physical_rotation_deg'])

    def test_exact_full_faces_and_two_cell_physical_gap_stay_inside_original_d50(self):
        design=r.translated_design(self.design);rows,areas,receipt=r.translate_mask(self.rows)
        self.assertEqual([720,720,432,432],[sum(p==pad for p,_,_,_ in rows)for pad in range(4)])
        self.assertEqual(2304,len({(i,j)for p,i,j,a in rows}))
        for actual,expected in zip(areas,(281.25,281.25,168.75,168.75)):
            self.assertAlmostEqual(actual*1e6,expected,places=10)
        for _,i,j,a in rows:
            self.assertEqual((.625/1000)**2,a)
            self.assertTrue(all((-25+ii*.625)**2+(-25+jj*.625)**2<625 for ii in(i,i+1)for jj in(j,j+1)))
        self.assertEqual(set(range(51,75)),{i for p,i,j,a in rows if p==2})
        self.assertEqual(set(range(22,40)),{j for p,i,j,a in rows if p==2})
        self.assertEqual(set(range(5,29)),{i for p,i,j,a in rows if p==3})
        self.assertEqual(set(range(40,58)),{j for p,i,j,a in rows if p==3})
        self.assertEqual(1.25,min(g['gap_mm']for g in design['verified_physical_gaps_mm']))
        self.assertEqual(605.078125,max(x*x+y*y for p in design['pads'][2:]for x,y in p['polygon_mm']))
        self.assertEqual(2,receipt['minimum_gap_XY_cells']);self.assertFalse(receipt['mesh_convergence_claimed'])

    def test_config_exactly_six_permitted_fields_preserves_circuit_mesh_contact_and_sources(self):
        original=(cross.core.HIST/'configs/baseline-square15-xy80.properties').read_bytes()
        _,prototype_areas,_=cross.aligned_cross_mask(self.prototype)
        prototype,_=cross.changed_cross_config(original,self.prototype,Path('/tmp/prototype'),'a'*64,prototype_areas)
        source,_=asym.changed_mask_config(prototype,Path('/tmp/asym'),'b'*64,self.areas)
        revised,changes=r.changed_translation_config(source,Path('/tmp/tangent'),'c'*64)
        a,b=cross._properties(source),cross._properties(revised)
        allowed={'mask.path','mask.sha256','pad.2.x_mm','pad.2.y_mm','pad.3.x_mm','pad.3.y_mm'}
        self.assertEqual(allowed,set(changes));self.assertEqual(set(a),set(b))
        self.assertEqual({k:v for k,v in a.items()if k not in allowed},{k:v for k,v in b.items()if k not in allowed})
        self.assertEqual([14.375,-5.625,-14.375,5.625],[float(b[k])for k in('pad.2.x_mm','pad.2.y_mm','pad.3.x_mm','pad.3.y_mm')])
        rotated=source.replace(b'pad.2.rotation_deg=0.0',b'pad.2.rotation_deg=90.0')
        self.assertNotEqual(source,rotated)
        with self.assertRaises(ValueError):r.changed_translation_config(rotated,Path('/tmp/a'),'d'*64)

    def test_exact_area_values_survive_but_rotated_parent_fragments_duplicates_or_missing_faces_reject(self):
        below=math.nextafter((.625/1000)**2,0.)
        rows=[(p,i,j,below)for p,i,j,a in self.rows]
        moved,areas,_=r.translate_mask(rows)
        self.assertTrue(all(a==below for p,i,j,a in moved))
        self.assertEqual([math.fsum(a for p,i,j,a in rows if p==pad)for pad in range(4)],areas)
        invalid=[]
        duplicate=list(self.rows);duplicate[1]=duplicate[0];invalid.append(duplicate)
        invalid.append(self.rows[:-1])
        rotated=[(p,79-j,i-32,a)if p==2 else(p,i,j,a)for p,i,j,a in self.rows];invalid.append(rotated)
        for ratio in(.25,1-1e-8):
            changed=list(self.rows);p,i,j,a=changed[0];changed[0]=(p,i,j,a*ratio);invalid.append(changed)
        for rows in invalid:
            with self.assertRaises(ValueError):r.translate_mask(rows)
        wrong=copy.deepcopy(self.design);wrong['pads'][2]['rotation_deg']=90
        with self.assertRaises(ValueError):r.translated_design(wrong)

    def test_mask_csv_and_finite_resource_contract(self):
        rows,_,_=r.translate_mask(self.rows);encoded=r._mask_bytes(rows)
        restored=[(int(v['pad']),int(v['i']),int(v['j']),float(v['area_m2']))for v in csv.DictReader(io.StringIO(encoded.decode()))]
        self.assertEqual(rows,restored)
        self.assertEqual(351680,r.EXPECTED_CELLS);self.assertEqual(211008000,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(351680*600,r.EXPECTED_RAW_BOUND_BYTES)
        self.assertEqual(1320,r.MIN_REMAINING_SECONDS);self.assertEqual(120,r.PREPARATION_SECONDS)


class ContextAndFailureTests(unittest.TestCase):
    def context(self,root):
        paths={}
        for relative,(schema,status)in r.REQUIRED_CONTEXT.items():
            p=root/relative;p.parent.mkdir(parents=True,exist_ok=True)
            obj={'schema':schema,'status':status,'inputs_unchanged':True,'new_PDE':0}
            if 'coherent-'in relative:obj['conditions']=[{'status':'calculated_unadopted','canonical_screen_all_passed':False}for _ in range(5)]
            r.core.write(p,obj);paths[str(p)]=r.core.sha(p)
        comment={'id':6321929825,'author':'yoodohyun-codex-cloud','body':'fixture public feedback',
                 'html_url':'https://github.com/yoodohyun-codex-cloud/ngg-tis-task1/pull/2#issuecomment-6321929825'}
        comment['body_sha256']=hashlib.sha256(comment['body'].encode()).hexdigest()
        receipts=[]
        for pull in(1,2):
            for kind in('head','comments'):
                endpoint='repos/yoodohyun-codex-cloud/ngg-tis-task1/'+(f'pulls/{pull}'if kind=='head'else f'issues/{pull}/comments')
                receipts.append(dict(pull=pull,kind=kind,endpoint=endpoint,evidence={'head_sha':'a'*40}if kind=='head'else([comment]if pull==2 else[])))
        fp=root/'feedback.json';r.core.write(fp,dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,receipts=receipts,observed_utc='2026-10-21T17:57:02+00:00'))
        d=dict(schema='task1-tangential-return-root-decision-v1',status='selected_not_executed',case_id=r.CASE_ID,
            source_run_id=r.SOURCE_RUN,source_case_id=r.SOURCE_ID,question='Finite geometry question',
            return_shift_grid_indices={'2':[7,7],'3':[-7,-7]},return_shift_mm={'2':[4.375,4.375],'3':[-4.375,-4.375]},
            physical_rotation_deg=0,new_PDE=1,new_native_RHS=8,independent_outputs=2,physical_pads=4,
            fixed_total_area_mm2=900,candidate_adopted=False,root_selected=True,peer_endorsed=False,
            feedback=dict(path=str(fp),SHA256=r.core.sha(fp)),input_sha256=paths)
        dp=root/'decision.json';r.core.write(dp,d);return dp,fp,d

    def test_completed_hashed_context_passes_and_source_drift_or_extra_output_blocks(self):
        with tempfile.TemporaryDirectory()as td,mock.patch.object(r.core,'REPO',Path(td)):
            root=Path(td);dp,fp,d=self.context(root)
            decision,feedback,pins=r.verify_context(dp,fp)
            self.assertTrue(decision['root_selected']);self.assertFalse(decision['peer_endorsed'])
            self.assertEqual(r.core.sha(dp),pins[str(dp)])
            d['independent_outputs']=4;r.core.write(dp,d)
            with self.assertRaises(ValueError):r.verify_context(dp,fp)
            d['independent_outputs']=2;r.core.write(dp,d)
            path=Path(next(iter(d['input_sha256'])));path.write_text('{}')
            with self.assertRaisesRegex(ValueError,'SHA'):r.verify_context(dp,fp)

    def test_preparation_context_failure_preserves_evidence_and_debits_without_reset_or_run(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);(root/'data-native').mkdir();(root/'runtime').mkdir();run=root/'data-native/cloud-synthetic-tangent'
            ledger=dict(limit_seconds=13800,spent_seconds=7.,runs=[dict(stage='earlier',seconds=7.)])
            r.core.write(root/'runtime/task1-budget.json',ledger)
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r,'_caller_owns_execution_lock'),\
                 mock.patch.object(r.os,'sched_setaffinity'),mock.patch.object(r.policy,'load_ledger',return_value=copy.deepcopy(ledger)),\
                 mock.patch.object(r.policy,'effective_limit',return_value=13800),\
                 mock.patch.object(r,'verify_context',side_effect=ValueError('synthetic context drift')),\
                 mock.patch.object(r.subprocess,'Popen')as popen:
                with self.assertRaisesRegex(ValueError,'context drift'):r.prepare_tangential_return(run,root/'decision',root/'feedback')
            self.assertFalse(run.exists());popen.assert_not_called()
            self.assertEqual('preparation_failed_preserved',r.core.read(run.with_name(run.name+'.preparation-failure.json'))['status'])
            after=r.core.read(root/'runtime/task1-budget.json')
            self.assertEqual(ledger['runs'],after['runs'][:1]);self.assertGreater(after['spent_seconds'],7)
            self.assertEqual('preparation_failed_preserved',after['runs'][-1]['status'])
            before_bytes=(root/'runtime/task1-budget.json').read_bytes()
            with mock.patch.object(r.core,'REPO',root),mock.patch.object(r.policy,'load_ledger')as load:
                with self.assertRaisesRegex(ValueError,'failed run IDs'):
                    r.prepare_tangential_return(run,root/'decision',root/'feedback')
            load.assert_not_called();self.assertEqual(before_bytes,(root/'runtime/task1-budget.json').read_bytes())

    def test_bounded_java_timeout_kills_only_its_owned_group_and_never_retries(self):
        child=mock.Mock(pid=987654);child.wait.side_effect=[subprocess.TimeoutExpired(['java'],5),0];child.poll.return_value=None
        guard=mock.Mock(side_effect=[10.,ValueError('synthetic timeout')])
        with mock.patch.object(r.subprocess,'Popen',return_value=child)as popen,mock.patch.object(r.core,'rss',return_value=100),\
             mock.patch.object(r.os,'killpg')as killpg:
            with self.assertRaisesRegex(ValueError,'synthetic timeout'):r.bounded_command(['java'],io.StringIO(),guard)
        self.assertEqual(1,popen.call_count);self.assertTrue(popen.call_args.kwargs['start_new_session'])
        killpg.assert_called_once_with(987654,r.signal.SIGTERM)


if __name__=='__main__':unittest.main()
