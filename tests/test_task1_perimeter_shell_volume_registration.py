"""Synthetic terminal receipts; never decode native arrays or run a solver."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module
reg=load('perimeter_shell_volume_tested',ROOT/'tools/task1_perimeter_shell_volume_registration.py')
fixtures=load('rotation_terminal_fixture',ROOT/'tests/test_task1_return_position_volume_registration.py')


class PerimeterShellVolumeRegistrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReturnPositionVolumeRegistrationTest();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.output=self.root/'docs/perimeter-volume-plan.json'
        self.feedback=self.root/'docs/live-feedback.json';comments=[]
        for ident in (6320375305,6321929825):
            body=f'Public synthetic peer context {ident}';comments.append(dict(id=ident,author='yoodohyun-codex-cloud',body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),html_url=f'https://github.com/example#issuecomment-{ident}'))
        self.fixture.write(self.feedback,dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,observed_utc='2026-10-21T17:11:46Z',
            receipts=[dict(pull=2,kind='comments',evidence=comments)]))
        self.decision=self.root/'docs/decision.json'
        self.fixture.write(self.decision,dict(schema='task1-perimeter-shell-root-decision-v1',status='selected_not_executed',
            root_selected=True,peer_endorsed=False,case_id=reg.CASE_ID,source_run_id=reg.PARENT_RUN,source_case_id=reg.PARENT_ID,
            new_PDE=1,new_native_RHS=8,independent_outputs=2,physical_pads=4,fixed_total_area_mm2=900,candidate_adopted=False,
            question='Combined fixed face-union geometry and placement contrast',
            feedback=dict(path=str(self.feedback),SHA256=reg.inherited.sha(self.feedback))))
        self.fixture.case_fixture(reg.NEW_RUN,reg.CASE_ID)
        for index,(run,ident)in enumerate(reg.CASE_TABLE):self.enrich(index,run,ident)

    def enrich(self,index,run_id,ident):
        run=self.root/'data-native'/run_id;pre_path=run/'preregistration.json';pre=json.loads(pre_path.read_text())
        case=next(c for c in pre['cases']if c['id']==ident)
        case.update(source_coating_nm=10,source_Rs_fit_window_Hz=500,
            expected_pad_areas_m2=[225.e-6]*4)
        case['circuit'].update(source_Vpp_each=1.,source_peak_V=.5,n_return_nodes=1,return_topology='all_return_pads_ideal_common_GND',
            carrier_assignment_Hz=[3000,3030],inactive_source_at_other_frequencies='0 V through 50 ohm')
        pads=[]
        for p,(sx,sy)in enumerate(reg.SIGNS):
            pads.append(dict(pad=p,shape='rectangle',center_mm=[sx*10.,sy*10.],width_mm=15.,height_mm=15.,rotation_deg=0.))
        case['design']=dict(pads=pads,physical_total_contact_area_mm2=900.)
        mask=Path(case['mask_file']);mask.write_text('pad,i,j,area_m2\n'+('0,5,5,0.000000390625\n'if index==1 else''))
        case['mask_sha256']=reg.inherited.sha(mask)
        if index==1:
            contract=dict(geometry_kind='fixed_native_face_union',combined_geometry_and_placement=True,
                isolated_shape_effect_claimed=False,native_full_face_contact=True,physical_total_contact_area_mm2=900.,
                minimum_physical_gap_mm=3.75,minimum_gap_XY_cells=6,
                maximum_physical_vertex_radius_squared_mm2=reg.RIM_RADIUS_SQUARED,rim_clearance_mm=reg.RIM_CLEARANCE)
            case.update(contract);case['design'].update(contract,minimum_gap_mm=3.75)
            for p,(sx,sy)in enumerate(reg.SIGNS):
                pads[p].update(shape='masked_face_union',geometry_primitive='fixed_union_of_native_full_face_rectangles',
                    center_mm=[sx*reg.CENTROID,sy*reg.CENTROID],bounding_box_center_mm=[sx*13.125,sy*13.125],
                    width_mm=22.5,height_mm=22.5,area_mm2=225.,analytic_area_mm2=225.,polygon_area_mm2=225.,
                    dimension_fields_role='bounding-box extents only; geometry is explicit full-face union',
                    native_face_indices=[[i,j]for j in range(24)for i in range(24)],
                    boundary_loops_mm=[[[0.,0.],[1.,0.],[1.,1.],[0.,1.]]])
            proof=dict(faces_per_pad=[576]*4,components_per_pad=[1]*4,holes_per_pad=[0]*4,partial_faces=0,
                clipping=False,renormalization=False,physical_total_contact_area_mm2=900.,minimum_physical_gap_mm=3.75,
                minimum_gap_XY_cells=6,maximum_physical_vertex_radius_squared_mm2=reg.RIM_RADIUS_SQUARED,
                rim_clearance_mm=reg.RIM_CLEARANCE)
            proof_path=run/'geometry-audit/perimeter-mask-proof.json';self.fixture.write(proof_path,proof)
            pre['source_and_input_sha256'][str(proof_path)]=reg.inherited.sha(proof_path)
            pre['root_selection_decision']=dict(path=str(self.decision),SHA256=reg.inherited.sha(self.decision))
            pre['source_feedback']=dict(path=str(self.feedback),SHA256=reg.inherited.sha(self.feedback))
        lines=['z.model=nominal500','muscle.sigma=0.3','h_mm=0.625','channels=2',
            'frequencies=3000,3030,9000,9090','validation.sc_cells=2','bulk.counts=14,14,40','mask.path='+str(mask),
            'mask.sha256='+case['mask_sha256']]
        for p,pad in enumerate(pads):
            lines += [f'pad.{p}.shape='+pad['shape'],f'pad.{p}.width_mm='+str(pad['width_mm']),
                f'pad.{p}.height_mm='+str(pad['height_mm']),f'pad.{p}.rotation_deg=0.0',
                f'pad.{p}.x_mm='+str(pad['center_mm'][0]),f'pad.{p}.y_mm='+str(pad['center_mm'][1])]
        config=Path(case['config_file']);config.write_text('\n'.join(lines)+'\n')
        case['config_sha256']=reg.inherited.sha(config);self.fixture.write(pre_path,pre)
        raw=run/'bases'/ident;meta=json.loads((raw/'mesh-metadata.json').read_text());meta['config_sha256']=case['config_sha256'];self.fixture.write(raw/'mesh-metadata.json',meta)
        summary_path=run/'postprocess'/ident/'summary.json';summary=json.loads(summary_path.read_text());summary['mesh_metadata']=meta
        probes=dict(status='complete',conditions=[dict(id=ident+'-square_3h',waveform='square_3h',probe40=dict(status='complete',unloaded_prediction=True,
            numerical_checks=dict(all_passed=True),measurement_grid=dict(tip_gap_mm=5),measurements=[dict(id=f'{d}-{p}-{a}',depth_from_skin_surface_mm=d,
                axis=a,tip_gap_mm=5)for d in(5,10,15,20)for p in range(5)for a in('X','Y')]))])
        probe_path=summary_path.parent/'probes.json';self.fixture.write(probe_path,probes)
        summary['artifacts']['files']['probes.json']['SHA256']=reg.inherited.sha(probe_path)
        summary['input_sha256']={str(p):reg.inherited.sha(p)for p in raw.iterdir()};self.fixture.write(summary_path,summary)
        record=run/'cases'/(ident+'.json');obj=json.loads(record.read_text());obj.update(config_sha256=case['config_sha256'],postprocess_sha256=reg.inherited.sha(summary_path));self.fixture.write(record,obj)
        audit=run/'audit'/('full-skin-'+ident+'.json');obj=json.loads(audit.read_text());obj.update(config_sha256=case['config_sha256'],
            summary_sha256=reg.inherited.sha(summary_path),registration_sha256=reg.inherited.sha(pre_path));self.fixture.write(audit,obj)

    def generate(self):
        with mock.patch.object(reg,'_committed_sources',return_value=('implementation-commit',{})), \
             mock.patch.object(reg.inherited.policy,'load_ledger',return_value=self.fixture.expanded), \
             mock.patch.object(reg.inherited.policy,'effective_limit',return_value=13800), \
             mock.patch.object(reg.inherited.policy,'remaining_seconds',return_value=5700), \
             mock.patch.object(reg.inherited.policy,'policy_refs',return_value={}):
            return reg.make_preregistration(self.output,root=self.root,decision_path=self.decision,feedback_path=self.feedback)

    def test_two_rows_original_baseline_no_array_reads(self):
        original=Path.read_bytes
        def guarded(path):
            if path.name=='volume.npz'or path.name.startswith(('grid.','field-','potential-','density-','source-','loss-')):
                raise AssertionError('Native array bytes read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):plan=self.generate()
        self.assertEqual([c['case_id']for c in plan['cases']],[i for _,i in reg.CASE_TABLE])
        self.assertEqual(plan['initial_case_count'],2);self.assertEqual(plan['baseline_summary_paths'],[plan['cases'][0]['summary']])
        self.assertFalse(plan['new_feedback_context']['peer_specific_perimeter_endorsement_inferred'])
        self.assertTrue(plan['geometry_comparison_contract']['combined_geometry_and_placement'])
        self.assertEqual(plan['geometry_comparison_contract']['minimum_gap_XY_cells'],6)

    def records(self):
        pre=json.loads((self.root/'data-native'/reg.NEW_RUN/'preregistration.json').read_text())
        case=next(c for c in pre['cases']if c['id']==reg.CASE_ID)
        proof=json.loads((self.root/'data-native'/reg.NEW_RUN/'geometry-audit/perimeter-mask-proof.json').read_text())
        return case,proof

    def test_native_union_requires_counts_connectivity_and_honest_geometry_kind(self):
        case,proof=self.records();reg.validate_shell_provenance(case,proof)
        for mutation in ('duplicate','smooth','hole','clipping','centroid','bbox','loop'):
            bad,receipt=copy.deepcopy(case),copy.deepcopy(proof)
            if mutation=='duplicate':bad['design']['pads'][0]['native_face_indices'][1]=bad['design']['pads'][0]['native_face_indices'][0]
            elif mutation=='smooth':bad['geometry_kind']='analytic_arc'
            elif mutation=='hole':receipt['holes_per_pad'][2]=1
            elif mutation=='clipping':receipt['clipping']=True
            elif mutation=='centroid':bad['design']['pads'][0]['center_mm'][0]=-.625
            elif mutation=='bbox':bad['design']['pads'][0]['dimension_fields_role']=''
            else:bad['design']['pads'][0]['boundary_loops_mm'][0][0]=[float('nan'),0.]
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):reg.validate_shell_provenance(bad,receipt)

    def test_descriptor_changes_do_not_allow_contact_circuit_or_frequency_changes(self):
        case,_=self.records()
        parent=reg.inherited._properties(self.root/'data-native'/reg.PARENT_RUN/'configs'/(reg.PARENT_ID+'.properties'))
        current=reg.inherited._properties(Path(case['config_file']))
        reg.validate_shell_configs(parent,current,case['design'])
        for key,value in [('muscle.sigma','0.4'),('channels','4'),('frequencies','2000,2010'),('pad.2.rotation_deg','90')]:
            bad=dict(current);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):reg.validate_shell_configs(parent,bad,case['design'])

    def test_missing_or_changed_geometry_proof_rejected(self):
        p=self.root/'data-native'/reg.NEW_RUN/'geometry-audit/perimeter-mask-proof.json';p.write_text('{}')
        with self.assertRaisesRegex(ValueError,'metadata SHA'):self.generate()
        self.assertFalse(self.output.exists())

    def test_missing_new_fullskin_or_controller_receipt_rejected(self):
        run=self.root/'data-native'/reg.NEW_RUN;record=run/'cases'/(reg.CASE_ID+'.json');saved=record.read_bytes();record.unlink()
        with self.assertRaises(ValueError):self.generate()
        record.write_bytes(saved);(run/'audit'/('full-skin-'+reg.CASE_ID+'.json')).unlink()
        with self.assertRaisesRegex(ValueError,'source-bound completed full-skin'):self.generate()
        self.assertFalse(self.output.exists())

    def test_latest_peer_body_hash_or_missing_feedback_rejected(self):
        obj=json.loads(self.feedback.read_text());obj['receipts'][0]['evidence'][-1]['body']='changed';self.fixture.write(self.feedback,obj)
        with self.assertRaisesRegex(ValueError,'body SHA'):self.generate()

    def test_stale_root_decision_cannot_bind_new_native(self):
        obj=json.loads(self.decision.read_text());obj['source_case_id']='other-baseline';self.fixture.write(self.decision,obj)
        with self.assertRaisesRegex(ValueError,'root perimeter-shell decision'):self.generate()

    def test_mixed_cohort_or_overwrite_rejected(self):
        with mock.patch.object(reg.inherited,'_signature',side_effect=['same','different']):
            with self.assertRaisesRegex(ValueError,'cohorts must match'):self.generate()
        self.output.write_text('preserved')
        with self.assertRaisesRegex(ValueError,'New canonical docs'):self.generate()
        self.assertEqual(self.output.read_text(),'preserved')

if __name__=='__main__':unittest.main()
