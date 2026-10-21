"""Fixed metadata fixtures; no PDE, NPZ decode, native grid or E/phi read."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1]/'tools/task1_return_position_volume_registration.py'
spec = importlib.util.spec_from_file_location('return_volume_under_test', MODULE)
reg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reg)


class ReturnPositionVolumeRegistrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root/'docs/return-position-plan.json'
        self.feedback = self.root/'docs/feedback.json'
        self.write(self.feedback, {'source_key': 'github-comment-test'})
        template = json.loads((MODULE.parents[1]/reg.TEMPLATE).read_text())
        template['frozen_definition_source_refs'] = {}
        self.write(self.root/reg.TEMPLATE, template)
        self.expanded = dict(limit_seconds=13800, spent_seconds=6000, runs=[])
        self.gates = dict(max_residual=2e-7, max_power_error=2e-7, max_current_error=2e-6,
                          max_area_relative_error=1e-10, max_interface_normal_current_relative_error=2e-7)
        for run, case in reg.CASE_TABLE:
            self.case_fixture(run, case)

    @staticmethod
    def write(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, allow_nan=False)+'\n')

    def case_fixture(self, run_id, ident):
        run = self.root/'data-native'/run_id
        summary_path = run/'postprocess'/ident/'summary.json'
        raw = run/'bases'/ident
        config = run/'configs'/(ident+'.properties')
        mask = run/'masks'/(ident+'.csv')
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text('z.model=nominal500\nmuscle.sigma=0.3\nmask.path='+str(mask)+'\n')
        mask.parent.mkdir(parents=True, exist_ok=True); mask.write_text('pad,i,j,area_m2\n')
        meta = dict(h_xy_mm=.625, sc_cells=2, bulk_layer_counts=[14,14,40], cells=351680,
                    config_sha256=reg.sha(config), radius_mm=25, source_resistance_ohm=50)
        raw.mkdir(parents=True, exist_ok=True)
        (raw/'BASIS_COMPLETE').touch()
        self.write(raw/'mesh-metadata.json', meta)
        self.write(raw/'validation.json', {k: v/100 for k,v in self.gates.items()})
        (raw/'grid.csv.gz').write_bytes(b'not actually a grid; must never decode in registration')
        (raw/'field-3000.bin.gz').write_bytes(b'not actually E; must never read')
        npz = summary_path.parent/'volume.npz'
        npz.parent.mkdir(parents=True, exist_ok=True); npz.write_bytes(b'not an NPZ; metadata-only')
        self.write(summary_path.parent/'probes.json', {'conditions': []})
        circuit = dict(n_pads=4, n_outputs=2, source_resistance_ohm=50.,
                       pad_to_node={'0':'out0','1':'out1','2':'GND','3':'GND'})
        case = dict(id=ident, config_file=str(config), config_sha256=reg.sha(config),
                    mask_file=str(mask), mask_sha256=reg.sha(mask), circuit=circuit)
        frozen = run/'frozen-source/tools/frozen.py'
        frozen.parent.mkdir(parents=True, exist_ok=True); frozen.write_text('# frozen numerical source\n')
        original = str(self.root/'tools/frozen.py')
        pre_path = run/'preregistration.json'
        pre = dict(source_commit='native-source-commit', cases=[case], gates=self.gates,
            source_and_input_sha256={original:reg.sha(frozen)},
            source_feedback=dict(path=str(self.feedback),SHA256=reg.sha(self.feedback),stable_source_keys=['github-comment-test']))
        # The two new cases share one run registration; retain previous case.
        if pre_path.exists():
            pre['cases'] = json.loads(pre_path.read_text())['cases']+[case]
        self.write(pre_path, pre)
        self.write(run/'frozen-source-manifest.json',dict(source_commit=pre['source_commit'],
            files={original:dict(path=str(frozen),sha256=reg.sha(frozen))}))
        condition = dict(id=ident+'-square_3h', waveform='square_3h', actual_fundamental_Hz=[3000,3030],
            phase_deg=[0.,0.], source_Vpp_per_output=1., native_volume_archive='volume.npz',
            volume_metrics={'regions':{'target':{'statistics':{m:dict(mean=4.,p10=3.)for m in ('maxTIS','fixedTIS','RMS')}}}})
        summary = dict(id=ident,status='complete',mesh_metadata=meta,conditions=[condition],
            input_sha256={str(p):reg.sha(p)for p in raw.iterdir()},artifacts=dict(probes_json='probes.json',
            files={p.name:dict(SHA256=reg.sha(p))for p in (npz,summary_path.parent/'probes.json')}))
        self.write(summary_path, summary)
        self.write(run/'cases'/(ident+'.json'),dict(id=ident,status='complete',config_sha256=case['config_sha256'],
            postprocess_path=str(summary_path),postprocess_sha256=reg.sha(summary_path)))
        self.write(run/'audit'/('full-skin-'+ident+'.json'),dict(case_id=ident,summary_sha256=reg.sha(summary_path),
            status='computed_spatial_and_skinJ_audit',native_inputs_unchanged=True,registration_sha256=reg.sha(pre_path),
            config_sha256=case['config_sha256'],source_commit=pre['source_commit'],
            conditions=[dict(condition_id=condition['id'],bulk_skin_J={},layer_contact_source_losses={})]))
        # Update prior audit registration binding when shared two-case pre grows.
        for audit in (run/'audit').glob('*.json'):
            obj=json.loads(audit.read_text());obj['registration_sha256']=reg.sha(pre_path);self.write(audit,obj)

    def generate(self):
        with mock.patch.object(reg, '_committed_sources', return_value=('implementation-commit', {})), \
             mock.patch.object(reg.policy, 'load_ledger', return_value=self.expanded), \
             mock.patch.object(reg.policy, 'effective_limit', return_value=13800), \
             mock.patch.object(reg.policy, 'remaining_seconds', return_value=7800), \
             mock.patch.object(reg.policy, 'policy_refs', return_value={}):
            return reg.make_preregistration(self.output,root=self.root)

    def test_fixed_order_baseline_and_no_npz_grid_or_field_reads(self):
        original = Path.read_bytes
        def guarded(path):
            if path.name == 'volume.npz' or path.name.startswith(('grid.', 'field-')):
                raise AssertionError('Metadata registration attempted native array byte read')
            return original(path)
        with mock.patch.object(Path,'read_bytes',guarded):
            plan = self.generate()
        self.assertEqual([c['case_id']for c in plan['cases']],[c for _,c in reg.CASE_TABLE])
        self.assertEqual(plan['baseline_summary_paths'],[plan['cases'][0]['summary']])
        self.assertEqual(plan['initial_case_count'],5)
        self.assertEqual(plan['resources']['cumulative_budget_limit_seconds'],13800)
        self.assertEqual(plan['feedback_id'],'T1-F010-S1-GH6297472037')
        self.assertEqual(plan['new_feedback_context']['phase'],'S4')
        self.assertFalse(plan['metadata_registration_scope']['volume_NPZ_decode_or_byte_read'])
        self.assertIn('--baseline-summary',plan['resume_command_argv'])

    def test_missing_controller_receipt_blocks_even_if_summary_complete(self):
        run,ident = reg.CASE_TABLE[-1]
        (self.root/'data-native'/run/'cases'/(ident+'.json')).unlink()
        with self.assertRaisesRegex(ValueError,'regular input'):
            self.generate()
        self.assertFalse(self.output.exists())

    def test_full_skin_false_or_wrong_summary_is_rejected(self):
        run,ident=reg.CASE_TABLE[-1]
        audit=self.root/'data-native'/run/'audit'/('full-skin-'+ident+'.json')
        obj=json.loads(audit.read_text());obj['native_inputs_unchanged']=False;self.write(audit,obj)
        with self.assertRaisesRegex(ValueError,'source-bound completed full-skin'):
            self.generate()

    def test_held_original_case_not_promoted_by_later_audit(self):
        run,ident=reg.CASE_TABLE[0]
        receipt=self.root/'data-native'/run/'cases'/(ident+'.json')
        obj=json.loads(receipt.read_text());obj['status']='failed';self.write(receipt,obj)
        with self.assertRaisesRegex(ValueError,'controller-completed'):
            self.generate()

    def test_frozen_source_and_config_drift_are_rejected(self):
        run,ident=reg.CASE_TABLE[1]
        path=self.root/'data-native'/run/'frozen-source/tools/frozen.py'
        path.write_text('# drift\n')
        with self.assertRaisesRegex(ValueError,'SHA mismatch'):
            self.generate()

    def test_config_drift_is_rejected(self):
        run,ident=reg.CASE_TABLE[-1]
        path=self.root/'data-native'/run/'configs'/(ident+'.properties')
        path.write_text('z.model=Rs2000\nmuscle.sigma=0.3\n')
        with self.assertRaisesRegex(ValueError,'SHA mismatch'):
            self.generate()

    def test_different_valid_model_cannot_join_original_cohort(self):
        self.assertNotEqual(reg._signature({}, {'z.model':'nominal500'}),
                            reg._signature({}, {'z.model':'Rs2000'}))
        with mock.patch.object(reg, '_signature', side_effect=['same']*4+['different_model']):
            with self.assertRaisesRegex(ValueError,'same grid/material/contact/ROI'):
                self.generate()

    def test_output_never_overwrites_existing_or_uses_outside_docs(self):
        self.output.write_text('preserved evidence')
        with self.assertRaisesRegex(ValueError,'New canonical docs'):
            self.generate()
        self.assertEqual(self.output.read_text(),'preserved evidence')

    def test_implementation_must_be_committed_at_head(self):
        for name in reg.SOURCES:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('# source\n')
        with mock.patch.object(reg.subprocess,'check_output',side_effect=['commit\n',b'not the source']):
            with self.assertRaisesRegex(ValueError,'Commit consumed implementation'):
                reg._committed_sources(self.root)


if __name__ == '__main__':
    unittest.main()
