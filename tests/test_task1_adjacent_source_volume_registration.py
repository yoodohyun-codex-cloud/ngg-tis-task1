"""Synthetic 2x2 cached-source registration; no native decode or real jobs."""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
EXPECTED=(
    ('cloud-mesh-c1-20261019T190000Z','baseline-square15-xy80'),
    ('cloud-finite-loop-20261020T002600Z-fine','adjacent-square15-xy80'),
    ('cloud-cross-allocation-20261021T150000Z','crossalloc-source225-return225-xy80'),
    ('cloud-adjacent-cross-20261021T164000Z','balancedcross225-adjacent-sources-xy80'))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

reg=load('adjacent_volume_under_test',ROOT/'tools/task1_adjacent_source_volume_registration.py')
fixtures=load('adjacent_volume_fixture',ROOT/'tests/test_task1_return_position_volume_registration.py')


class AdjacentSourceVolumeRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReturnPositionVolumeRegistrationTest();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.output=self.root/'docs/adjacent-source-volume-plan.json'
        self.live_feedback=self.root/'docs/cloud-grouped-fine-recovery-20261021T161000Z/feedback-before.json'
        self.feedback_body='Synthetic live feedback: compare fixed-contact source adjacency'
        self.feedback_body_sha=hashlib.sha256(self.feedback_body.encode()).hexdigest()
        self.fixture.write(self.live_feedback,dict(receipts=[dict(evidence=[dict(id=6320375305,comment_id=6320375305,
            body=self.feedback_body,body_sha256=self.feedback_body_sha,source_key='issue_comment:6320375305',
            user=dict(login='yoodohyun2'),author='yoodohyun2')])]))
        for index,(run,ident) in enumerate(EXPECTED):
            path=self.root/'data-native'/run/'preregistration.json'
            if not path.exists():self.fixture.case_fixture(run,ident)
            self.enrich_case(index)
        self.make_allocation_evidence()

    def make_allocation_evidence(self):
        baseline=self.root/'data-native'/EXPECTED[0][0]/'postprocess'/EXPECTED[0][1]/'summary.json'
        balanced=self.root/'data-native'/EXPECTED[2][0]/'postprocess'/EXPECTED[2][1]/'summary.json'
        rows=[dict(case_id=EXPECTED[0][1],summary_path=str(baseline))]
        refs={str(baseline):reg.inherited.sha(baseline),str(balanced):reg.inherited.sha(balanced)}
        for area,return_area in ((200,250),(225,225),(250,200)):
            ident=f'crossalloc-source{area}-return{return_area}-xy80'
            summary=balanced if area==225 else self.root/'docs'/(ident+'-summary.json')
            if area!=225:self.fixture.write(summary,dict(id=ident,status='complete'))
            refs[str(summary)]=reg.inherited.sha(summary);rows.append(dict(case_id=ident,summary_path=str(summary)))
        self.allocation_report=self.root/'docs/allocation-screen.json'
        self.fixture.write(self.allocation_report,dict(status='calculated_unadopted',inputs_unchanged=True,cases=rows,inputs_sha256=refs))
        self.decision_path=self.root/'docs/root-selection.json';decision=json.loads(self.decision_path.read_text())
        decision['cross_allocation_report']=dict(path=str(self.allocation_report),sha256=reg.inherited.sha(self.allocation_report))
        self.fixture.write(self.decision_path,decision)
        pre_path=self.root/'data-native'/EXPECTED[-1][0]/'preregistration.json';pre=json.loads(pre_path.read_text())
        pre['root_selection_decision']['SHA256']=reg.inherited.sha(self.decision_path);self.fixture.write(pre_path,pre);self.refresh_case(3)

    def enrich_case(self,index):
        run_id,ident=EXPECTED[index];run=self.root/'data-native'/run_id;pre_path=run/'preregistration.json'
        pre=json.loads(pre_path.read_text());case=next(row for row in pre['cases']if row['id']==ident)
        adjacent=index in (1,3);shape='cross'if index>=2 else'rectangle';width=16.25 if shape=='cross'else 15.
        centres=[[-10.,-10.],[10.,-10.],[10.,10.],[-10.,10.]]if adjacent else[[-10.,-10.],[10.,10.],[10.,-10.],[-10.,10.]]
        pads=[]
        for number,centre in enumerate(centres):
            pad=dict(pad=number,shape=shape,center_mm=centre,rotation_deg=0.,width_mm=width,height_mm=width,
                analytic_area_mm2=225.,area_mm2=225.,role='signal'if number<2 else'common_gnd_return',
                source_output=number if number<2 else None)
            if shape=='cross':pad.update(outer_length_mm=16.25,arm_width_mm=10.)
            pads.append(pad)
        case['design']=dict(id=ident.removesuffix('-xy80'),pads=pads,total_pads=4,source_outputs=2,
            return_connection='all_return_pads_ideal_common_GND',xy_mm=centres,
            physical_total_contact_area_mm2=900.,source_pad_area_mm2=225.,return_pad_area_mm2=225.)
        case['expected_pad_areas_m2']=[.000225]*4
        if index==3:case.update(original_physical_pad_by_solver_pad=[0,2,1,3],wiring_only_contrast=True,source_adjacency='adjacent_bottom_row')
        mask=Path(case['mask_file']);self.write_mask(mask,centres,shape);case['mask_sha256']=reg.inherited.sha(mask)
        case['circuit'].update(n_return_nodes=1,return_topology='all_return_pads_ideal_common_GND',
            source_Vpp_each=1.,source_peak_V=.5,carrier_assignment_Hz=[3000,3030],
            inactive_source_at_other_frequencies='0 V through 50 ohm')
        case.update(n_pads=4,n_outputs=2,channels=2,source_coating_nm=10.,source_Rs_fit_window_Hz=500,h_xy_mm=.625,sc_cells=2,bulk_counts=[14,14,40],cells=351680)
        config=Path(case['config_file']);lines=['z.model=nominal500','muscle.sigma=0.3','h_mm=0.625','channels=2',
            'frequencies=3000,3030,9000,9090','validation.sc_cells=2','bulk.counts=14,14,40',
            'mask.path='+case['mask_file'],'mask.sha256='+case['mask_sha256']]
        for number,pad in enumerate(pads):
            values=dict(shape=shape,x_mm=pad['center_mm'][0],y_mm=pad['center_mm'][1],width_mm=width,height_mm=width,
                analytic_area_mm2=225.,represented_area_m2=.000225,rotation_deg=0.)
            if shape=='cross':values['arm_width_mm']=10.
            lines.extend(f'pad.{number}.{key}={value}'for key,value in values.items())
        config.write_text('\n'.join(lines)+'\n');case['config_sha256']=reg.inherited.sha(config)
        pre['root_selection_decision']=dict(path=str(self.root/'docs/root-selection.json'),SHA256='')
        self.fixture.write(Path(pre['root_selection_decision']['path']),dict(schema='task1-adjacent-source-decision-v1',status='preregistered_not_started',
            case_ids=['balancedcross225-adjacent-sources-xy80'],chosen_question='Shape x source adjacency at unchanged two-output common-GND circuit'))
        pre['root_selection_decision']['SHA256']=reg.inherited.sha(pre['root_selection_decision']['path'])
        self.fixture.write(pre_path,pre)
        self.refresh_case(index)

    @staticmethod
    def write_mask(path,centres,shape):
        face=(.625/1000)**2
        with path.open('w',newline='')as stream:
            writer=csv.writer(stream);writer.writerow(('pad','i','j','area_m2'))
            for pad,(x,y)in enumerate(centres):
                cx,cy=round((x+25)/.625),round((y+25)/.625)
                boxes=((26,16),(16,26))if shape=='cross'else((24,24),)
                cells={(i,j)for width,height in boxes for i in range(cx-width//2,cx+width//2)
                       for j in range(cy-height//2,cy+height//2)}
                for i,j in sorted(cells,key=lambda ij:(ij[1],ij[0])):writer.writerow((pad,i,j,format(face,'.17g')))

    def refresh_case(self,index,probe_override=None):
        run_id,ident=EXPECTED[index];run=self.root/'data-native'/run_id;pre_path=run/'preregistration.json'
        pre=json.loads(pre_path.read_text());case=next(row for row in pre['cases']if row['id']==ident)
        config=Path(case['config_file']);case['config_sha256']=reg.inherited.sha(config);self.fixture.write(pre_path,pre)
        raw=run/'bases'/ident;meta=json.loads((raw/'mesh-metadata.json').read_text());meta['config_sha256']=case['config_sha256']
        self.fixture.write(raw/'mesh-metadata.json',meta)
        summary_path=run/'postprocess'/ident/'summary.json';summary=json.loads(summary_path.read_text());summary['mesh_metadata']=meta
        probes=dict(status='complete',conditions=[dict(id=ident+'-square_3h',waveform='square_3h',probe40=dict(status='complete',
            unloaded_prediction=True,numerical_checks=dict(all_passed=True),measurement_grid=dict(tip_gap_mm=5.,depths_mm=[5.,10.,15.,20.]),
            measurements=[dict(id=f'd{depth}-{position}-{axis}',depth_from_skin_surface_mm=depth,position=position,axis=axis,
                tip_gap_mm=5.,centre_mm=[x,y,depth],plus_mm=[x+(2.5 if axis=='X'else 0.),y+(2.5 if axis=='Y'else 0.),depth],
                minus_mm=[x-(2.5 if axis=='X'else 0.),y-(2.5 if axis=='Y'else 0.),depth])
                for depth in (5.,10.,15.,20.)for position,x,y in (('centre',0.,0.),('x+',5.,0.),('x-',-5.,0.),('y+',0.,5.),('y-',0.,-5.))for axis in ('X','Y')]))])
        if probe_override is not None:probes=probe_override
        probe_path=summary_path.parent/'probes.json';self.fixture.write(probe_path,probes)
        summary['input_sha256']={str(path):reg.inherited.sha(path)for path in raw.iterdir()}
        summary['artifacts']['files']['probes.json']['SHA256']=reg.inherited.sha(probe_path)
        self.fixture.write(summary_path,summary)
        record=run/'cases'/(ident+'.json');obj=json.loads(record.read_text());obj.update(config_sha256=case['config_sha256'],postprocess_sha256=reg.inherited.sha(summary_path));self.fixture.write(record,obj)
        audit=run/'audit'/('full-skin-'+ident+'.json');obj=json.loads(audit.read_text());obj.update(config_sha256=case['config_sha256'],
            summary_sha256=reg.inherited.sha(summary_path),registration_sha256=reg.inherited.sha(pre_path));self.fixture.write(audit,obj)

    def generate(self):
        with mock.patch.object(reg,'_committed_sources',return_value=('implementation-commit',{})), \
             mock.patch.object(reg,'COMMENT_BODY_SHA256',self.feedback_body_sha), \
             mock.patch.object(reg.inherited.policy,'load_ledger',return_value=self.fixture.expanded), \
             mock.patch.object(reg.inherited.policy,'effective_limit',return_value=13800), \
             mock.patch.object(reg.inherited.policy,'remaining_seconds',return_value=7800), \
             mock.patch.object(reg.inherited.policy,'policy_refs',return_value={}):
            return reg.make_preregistration(self.output,root=self.root)

    def test_exact_four_ordered_factorial_controls_and_original_baseline(self):
        self.assertEqual(tuple(reg.CASE_TABLE),EXPECTED)
        plan=self.generate()
        self.assertEqual([row['case_id']for row in plan['cases']],[ident for _,ident in EXPECTED])
        self.assertEqual(plan['initial_case_count'],4)
        self.assertEqual(plan['baseline_summary_paths'],[plan['cases'][0]['summary']])
        self.assertEqual(plan['baseline_case_ids'],['baseline-square15-xy80'])
        self.assertEqual(plan['feedback_id'],'T1-F010-S1-GH6297472037')
        self.assertIn('tools/task1_adjacent_source_volume_registration.py',reg.SOURCES)
        self.assertIn('tests/test_task1_adjacent_source_volume_registration.py',reg.SOURCES)
        self.assertFalse(plan['metadata_registration_scope']['volume_NPZ_decode_or_byte_read'])

    def test_registration_never_reads_grid_fields_or_npz_bytes(self):
        original=Path.read_bytes
        def guard(path):
            if path.name=='volume.npz'or path.name.startswith(('grid.','field-')):raise AssertionError('Native array opened')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guard):plan=self.generate()
        self.assertEqual(plan.get('new_PDE_conditions',0),0)

    def test_missing_candidate_controller_or_full_skin_receipt_blocks(self):
        run,ident=EXPECTED[-1];record=self.root/'data-native'/run/'cases'/(ident+'.json')
        original=record.read_bytes();record.unlink()
        with self.assertRaises(ValueError):self.generate()
        record.write_bytes(original)
        audit=self.root/'data-native'/run/'audit'/('full-skin-'+ident+'.json');audit.unlink()
        with self.assertRaises(ValueError):self.generate()
        self.assertFalse(self.output.exists())

    def test_failed_or_stale_full_skin_provenance_is_rejected(self):
        run,ident=EXPECTED[-1];audit=self.root/'data-native'/run/'audit'/('full-skin-'+ident+'.json')
        original=json.loads(audit.read_text())
        for key,value in (('native_inputs_unchanged',False),('summary_sha256','0'*64),('registration_sha256','0'*64),('source_commit','other')):
            obj=copy.deepcopy(original);obj[key]=value;self.fixture.write(audit,obj)
            with self.subTest(key=key),self.assertRaises(ValueError):self.generate()

    def test_missing_npz_manifest_hash_and_probe_source_are_rejected(self):
        run,ident=EXPECTED[-1];summary=self.root/'data-native'/run/'postprocess'/ident/'summary.json'
        obj=json.loads(summary.read_text());obj['artifacts']['files']['volume.npz']['SHA256']='bad';self.fixture.write(summary,obj)
        self.refresh_case(3)
        with self.assertRaises(ValueError):self.generate()

    def test_mixed_material_contact_or_grid_signature_is_rejected(self):
        with mock.patch.object(reg.inherited,'_signature',side_effect=['same','same','same','different']):
            with self.assertRaises(ValueError):self.generate()

    def test_different_pad_area_cannot_use_registered_balanced_identity(self):
        run,ident=EXPECTED[-1];pre_path=self.root/'data-native'/run/'preregistration.json';pre=json.loads(pre_path.read_text())
        pre['cases'][0]['expected_pad_areas_m2']=[.0002,.0002,.00025,.00025];self.fixture.write(pre_path,pre);self.refresh_case(3)
        with self.assertRaises(ValueError):self.generate()

    def test_wrong_source_order_or_outline_config_is_rejected(self):
        run,ident=EXPECTED[-1];config=self.root/'data-native'/run/'configs'/(ident+'.properties')
        original=config.read_text()
        for before,after in (('pad.1.y_mm=-10.0','pad.1.y_mm=10.0'),('pad.0.shape=cross','pad.0.shape=square'),
                             ('pad.0.arm_width_mm=10.0','pad.0.arm_width_mm=9.0')):
            config.write_text(original.replace(before,after));self.refresh_case(3)
            with self.subTest(before=before),self.assertRaises(ValueError):self.generate()

    def test_frozen_source_change_and_path_escape_are_rejected(self):
        run,_=EXPECTED[-1];manifest=self.root/'data-native'/run/'frozen-source-manifest.json';obj=json.loads(manifest.read_text())
        next(iter(obj['files'].values()))['path']='../escape.py';self.fixture.write(manifest,obj)
        with self.assertRaises(ValueError):self.generate()

    def test_root_decision_sha_must_bind_existing_metadata(self):
        run,_=EXPECTED[-1];pre_path=self.root/'data-native'/run/'preregistration.json';pre=json.loads(pre_path.read_text())
        pre['root_selection_decision']['SHA256']='0'*64;self.fixture.write(pre_path,pre);self.refresh_case(3)
        with self.assertRaises(ValueError):self.generate()

    def test_live_feedback_is_context_not_a_specific_wiring_endorsement(self):
        plan=self.generate();context=plan['new_feedback_context']
        self.assertEqual(context['source']['comment_id'],6320375305)
        self.assertEqual(context['source']['body_SHA256'],self.feedback_body_sha)
        self.assertEqual(context['source']['SHA256'],reg.inherited.sha(self.live_feedback))
        self.assertFalse(context['peer_specific_wiring_endorsement_inferred'])
        self.assertFalse(context['source']['peer_specific_wiring_endorsement_inferred'])
        self.assertNotEqual(context['source']['path'],context['inherited_source_feedback_context']['path'])

    def test_live_comment_id_body_and_sha_are_all_bound(self):
        original=json.loads(self.live_feedback.read_text())
        for key,value in (('id',1),('body','different'),('body_sha256','0'*64)):
            snapshot=copy.deepcopy(original);snapshot['receipts'][0]['evidence'][0][key]=value;self.fixture.write(self.live_feedback,snapshot)
            with self.subTest(key=key),self.assertRaises(ValueError):self.generate()

    def test_exact_forty_unloaded_5mm_probes_are_required(self):
        run,ident=EXPECTED[-1];path=self.root/'data-native'/run/'postprocess'/ident/'probes.json'
        original=json.loads(path.read_text())
        for variant in ('count','duplicate','loaded','gap','depth','axis','gate'):
            probes=copy.deepcopy(original);probe=probes['conditions'][0]['probe40']
            if variant=='count':probe['measurements'].pop()
            elif variant=='duplicate':probe['measurements'][1]['id']=probe['measurements'][0]['id']
            elif variant=='loaded':probe['unloaded_prediction']=False
            elif variant=='gap':probe['measurements'][0]['tip_gap_mm']=10.
            elif variant=='depth':probe['measurements'][0]['depth_from_skin_surface_mm']=25.
            elif variant=='axis':
                for row in probe['measurements']:row['axis']='X'
            else:probe['numerical_checks']['all_passed']=False
            self.refresh_case(3,probe_override=probes)
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.generate()

    def test_new_cross_must_remain_a_pure_physical_pad_role_permutation(self):
        path=self.root/'data-native'/EXPECTED[-1][0]/'preregistration.json';original=json.loads(path.read_text())
        for key,value in (('original_physical_pad_by_solver_pad',[0,1,2,3]),('wiring_only_contrast',False),('source_adjacency','opposite')):
            pre=copy.deepcopy(original);pre['cases'][0][key]=value;self.fixture.write(path,pre);self.refresh_case(3)
            with self.subTest(key=key),self.assertRaises(ValueError):self.generate()

    def test_completed_allocation_report_must_bind_original_square_and_balanced_cross(self):
        original=json.loads(self.allocation_report.read_text())
        for variant in ('running','changed','missing_control','wrong_summary_sha'):
            report=copy.deepcopy(original)
            if variant=='running':report['status']='running'
            elif variant=='changed':report['inputs_unchanged']=False
            elif variant=='missing_control':report['cases']=[row for row in report['cases']if row['case_id']!=EXPECTED[2][1]]
            else:
                baseline=str(self.root/'data-native'/EXPECTED[0][0]/'postprocess'/EXPECTED[0][1]/'summary.json')
                report['inputs_sha256'][baseline]='0'*64
            self.fixture.write(self.allocation_report,report)
            decision=json.loads(self.decision_path.read_text());decision['cross_allocation_report']['sha256']=reg.inherited.sha(self.allocation_report)
            self.fixture.write(self.decision_path,decision)
            path=self.root/'data-native'/EXPECTED[-1][0]/'preregistration.json';pre=json.loads(path.read_text())
            pre['root_selection_decision']['SHA256']=reg.inherited.sha(self.decision_path);self.fixture.write(path,pre);self.refresh_case(3)
            with self.subTest(variant=variant),self.assertRaises(ValueError):self.generate()

    def test_common_return_termination_and_contact_provenance_cannot_change(self):
        path=self.root/'data-native'/EXPECTED[-1][0]/'preregistration.json';original=json.loads(path.read_text())
        variants=(('n_return_nodes',2),('source_peak_V',1.),('source_Vpp_each',2.),
                  ('inactive_source_at_other_frequencies','open circuit'),('carrier_assignment_Hz',[2000,2010]))
        for key,value in variants:
            pre=copy.deepcopy(original);pre['cases'][0]['circuit'][key]=value;self.fixture.write(path,pre);self.refresh_case(3)
            with self.subTest(key=key),self.assertRaises(ValueError):self.generate()
        for key,value in (('source_coating_nm',20),('source_Rs_fit_window_Hz',2000)):
            pre=copy.deepcopy(original);pre['cases'][0][key]=value;self.fixture.write(path,pre);self.refresh_case(3)
            with self.subTest(key=key),self.assertRaises(ValueError):self.generate()

    def test_output_never_overwrites_or_escapes_docs(self):
        self.output.write_text('preserved evidence')
        with self.assertRaises(ValueError):self.generate()
        self.assertEqual(self.output.read_text(),'preserved evidence')
        self.output=self.root/'outside-plan.json'
        with self.assertRaises(ValueError):self.generate()
        self.output=self.root/'docs/volume.json'
        with self.assertRaises(ValueError):self.generate()
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
