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
reg=load('tangential_return_volume_tested',ROOT/'tools/task1_tangential_return_volume_registration.py')
fixtures=load('rotation_terminal_fixture',ROOT/'tests/test_task1_return_position_volume_registration.py')


class TangentialReturnVolumeRegistrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ReturnPositionVolumeRegistrationTest();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;self.output=self.root/'docs/tangential-volume-plan.json'
        self.feedback=self.root/'docs/live-feedback.json';comments=[]
        for ident in (6320375305,6321929825):
            body=f'Public synthetic peer context {ident}';comments.append(dict(id=ident,author='yoodohyun-codex-cloud',body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),html_url=f'https://github.com/example#issuecomment-{ident}'))
        self.fixture.write(self.feedback,dict(schema='task1-queue-feedback-v1',status='read_only_feedback_checked',error=None,
            public_GitHub_only=True,messages_sent=0,new_PDE=0,observed_utc='2026-10-21T17:11:46Z',
            receipts=[dict(pull=2,kind='comments',evidence=comments)]))
        self.decision=self.root/'docs/decision.json'
        self.fixture.write(self.decision,dict(schema='task1-tangential-return-root-decision-v1',status='selected_not_executed',
            root_selected=True,peer_endorsed=False,case_id=reg.CASE_ID,source_run_id=reg.PARENT_RUN,source_case_id=reg.PARENT_ID,
            return_shift_grid_indices=reg.INDEX_SHIFTS,return_shift_mm=reg.SHIFTS,new_centres_mm=reg.NEW_CENTRES,
            physical_rotation_deg=0,unchanged_physical_pads=[0,1],moved_physical_pads=[2,3],
            new_PDE=1,new_native_RHS=8,independent_outputs=2,physical_pads=4,fixed_total_area_mm2=900,
            expected_minimum_gap_mm=1.25,expected_minimum_gap_XY_cells=2,candidate_adopted=False,
            question='Two commonGND return-pad tangential translation contrast',
            feedback=dict(path=str(self.feedback),SHA256=reg.inherited.sha(self.feedback))))
        self.fixture.case_fixture(reg.NEW_RUN,reg.CASE_ID)
        for index,(run,ident)in enumerate(reg.CASE_TABLE):self.enrich(index,run,ident)

    def enrich(self,index,run_id,ident):
        run=self.root/'data-native'/run_id;pre_path=run/'preregistration.json';pre=json.loads(pre_path.read_text())
        case=next(c for c in pre['cases']if c['id']==ident)
        case.update(source_coating_nm=10,source_Rs_fit_window_Hz=500,
            expected_pad_areas_m2=[a*1e-6 for a in ([225.]*4 if index==0 else[281.25,281.25,168.75,168.75])])
        case['circuit'].update(source_Vpp_each=1.,source_peak_V=.5,n_return_nodes=1,return_topology='all_return_pads_ideal_common_GND',
            carrier_assignment_Hz=[3000,3030],inactive_source_at_other_frequencies='0 V through 50 ohm')
        pads=[]
        for p in range(4):
            x,y=((-10.,-10.),(10.,10.),(10.,-10.),(-10.,10.))[p]
            width,height=(17.5,17.5)if p<2 else(15.,11.25)
            pads.append(dict(pad=p,shape='cross'if p<2 else'rectangle',center_mm=[x,y],width_mm=width,height_mm=height,
                rotation_deg=0.,role='signal'if p<2 else'common_gnd_return',source_output=p if p<2 else None,
                polygon_mm=[[x-width/2,y-height/2],[x+width/2,y-height/2],[x+width/2,y+height/2],[x-width/2,y+height/2]]))
        case['design']=dict(pads=pads,physical_total_contact_area_mm2=900.)
        mask=Path(case['mask_file']);mask.write_text('pad,i,j,area_m2\n'+('2,54,19,0.000000390625\n'if index==2 else''))
        case['mask_sha256']=reg.inherited.sha(mask)
        if index==2:
            case.update(applied_physical_rotation_deg=0,operative_config_rotation_deg=0,translation_only_contrast=True,
                moved_physical_pad_ids=[2,3],return_shift_grid_indices=reg.INDEX_SHIFTS,return_shift_mm=reg.SHIFTS)
            case['design'].update(physical_rotation_deg=0,moved_physical_pad_ids=[2,3],return_shift_grid_indices=reg.INDEX_SHIFTS,
                return_shift_mm=reg.SHIFTS,minimum_gap_mm=1.25,minimum_gap_XY_cells=2)
            for p in (2,3):
                shift=reg.SHIFTS[str(p)];pads[p]['center_mm']=reg.NEW_CENTRES[str(p)].copy()
                pads[p]['polygon_mm']=[[x+shift[0],y+shift[1]]for x,y in pads[p]['polygon_mm']]
                pads[p].update(applied_translation_mm=shift.copy(),applied_physical_rotation_deg=0)
            pre['root_selection_decision']=dict(path=str(self.decision),SHA256=reg.inherited.sha(self.decision))
            pre['source_feedback']=dict(path=str(self.feedback),SHA256=reg.inherited.sha(self.feedback))
        lines=['z.model=nominal500','muscle.sigma=0.3','h_mm=0.625','channels=2',
            'frequencies=3000,3030,9000,9090','validation.sc_cells=2','bulk.counts=14,14,40','mask.path='+str(mask),
            'mask.sha256='+case['mask_sha256']]
        for p in (2,3):
            centre=reg.NEW_CENTRES[str(p)]if index==2 else reg.PARENT_CENTRES[str(p)]
            lines += [f'pad.{p}.width_mm=15',f'pad.{p}.height_mm=11.25',f'pad.{p}.rotation_deg=0.0',
                f'pad.{p}.x_mm={centre[0]}',f'pad.{p}.y_mm={centre[1]}']
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

    def test_three_rows_original_baseline_no_array_reads(self):
        original=Path.read_bytes
        def guarded(path):
            if path.name=='volume.npz'or path.name.startswith(('grid.','field-','potential-','density-','source-','loss-')):
                raise AssertionError('Native array bytes read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):plan=self.generate()
        self.assertEqual([c['case_id']for c in plan['cases']],[i for _,i in reg.CASE_TABLE])
        self.assertEqual(plan['initial_case_count'],3);self.assertEqual(plan['baseline_summary_paths'],[plan['cases'][0]['summary']])
        self.assertFalse(plan['new_feedback_context']['peer_specific_tangential_endorsement_inferred'])
        self.assertEqual(plan['geometry_comparison_contract']['translated_physical_pad_ids'],[2,3])
        self.assertEqual(plan['geometry_comparison_contract']['minimum_gap_XY_cells'],2)

    def test_config_allows_only_exact_two_return_translations(self):
        parent={'mask.path':'old','mask.sha256':'a','pad.0.x_mm':'-10'}
        for p in ('2','3'):
            parent.update({f'pad.{p}.width_mm':'15',f'pad.{p}.height_mm':'11.25',f'pad.{p}.rotation_deg':'0',
                f'pad.{p}.x_mm':str(reg.PARENT_CENTRES[p][0]),f'pad.{p}.y_mm':str(reg.PARENT_CENTRES[p][1])})
        current=dict(parent,**{'mask.path':'new','mask.sha256':'b'})
        for p in ('2','3'):
            current.update({f'pad.{p}.x_mm':str(reg.NEW_CENTRES[p][0]),f'pad.{p}.y_mm':str(reg.NEW_CENTRES[p][1])})
        reg.validate_translation_configs(parent,current)
        for key,value in [('pad.2.rotation_deg','90'),('pad.0.x_mm','-9'),('pad.3.x_mm','-14'),('pad.2.width_mm','11.25')]:
            bad=dict(current);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):reg.validate_translation_configs(parent,bad)

    def test_hidden_rotation_source_change_or_pad_exchange_rejected(self):
        def case(run,ident):
            return next(c for c in json.loads((self.root/'data-native'/run/'preregistration.json').read_text())['cases']if c['id']==ident)
        parent=case(reg.PARENT_RUN,reg.PARENT_ID);current=case(reg.NEW_RUN,reg.CASE_ID)
        reg.validate_translation_provenance(parent,current)
        for mutation in ('source','rotation','exchange','polygon','gap'):
            bad=copy.deepcopy(current)
            if mutation=='source':bad['design']['pads'][0]['center_mm'][0]+=1
            elif mutation=='rotation':bad['applied_physical_rotation_deg']=90
            elif mutation=='exchange':bad['design']['pads'][2]['pad']=3
            elif mutation=='polygon':bad['design']['pads'][2]['polygon_mm'][0][0]+=.625
            else:bad['design']['minimum_gap_XY_cells']=1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):reg.validate_translation_provenance(parent,bad)

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
        obj=json.loads(self.decision.read_text());obj['return_shift_grid_indices']={'2':[6,7],'3':[-7,-7]};self.fixture.write(self.decision,obj)
        with self.assertRaisesRegex(ValueError,'root tangential-return decision'):self.generate()

    def test_mixed_cohort_or_overwrite_rejected(self):
        with mock.patch.object(reg.inherited,'_signature',side_effect=['same','same','different']):
            with self.assertRaisesRegex(ValueError,'cohorts must match'):self.generate()
        self.output.write_text('preserved')
        with self.assertRaisesRegex(ValueError,'New canonical docs'):self.generate()
        self.assertEqual(self.output.read_text(),'preserved')

if __name__=='__main__':unittest.main()
