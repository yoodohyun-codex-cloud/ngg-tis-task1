"""Small metadata-only snapshot/versioning tests; no rendering jobs or arrays."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
SPEC = importlib.util.spec_from_file_location('snapshot_merge_tested',ROOT/'tools/task1_volume_snapshot_merge_view.py')
M = importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)


class SnapshotMergeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        source=self.root/'summary.json';source.write_text('{}')
        self.case=dict(summary_path=str(source),baseline_summary=str(source),case_id='baseline',run_id='historical',
            comparison_signature='same',circuit=dict(n_pads=4,n_outputs=2),mesh=dict(h_xy_mm=.625),value=3.141592653589793)
        self.report=self.root/'report.json';self.report.write_text(json.dumps(dict(cases=[self.case],
            inputs_sha256={str(self.root/'changed-live-helper.py'):'a'*64})))
        self.html=self.root/'v6.html';self.receipt=self.root/'v6.receipt.json'
        self.model=dict(schema='task1-volume-audit-view-model-v1',cases=[dict(self.case,viewer_id='historical/baseline',
            baseline_present=True,viewer_holds=[],links=dict(summary='summary.json'))],audits=[],cohorts=[],holds=[])
        self.html.write_text('<script id="report-data" type="application/json">'+json.dumps(self.model)+'</script>')
        self.receipt.write_text(json.dumps(dict(schema='task1-volume-audit-view-receipt-v1',status='rendered_precomputed_JSON_only',
            output=dict(SHA256=M.view.sha(self.html),bytes=self.html.stat().st_size),case_count=1,
            source_commit='b'*40,implementation_SHA256='c'*64,
            audit_inputs=[dict(path=str(self.report),SHA256=M.view.sha(self.report))])))

    def test_immutable_historical_snapshot_is_not_current_helper_validation(self):
        (self.root/'changed-live-helper.py').write_text('current implementation differs intentionally')
        model,proof=M.load_snapshot(self.html,self.receipt)
        self.assertEqual(model,self.model)
        self.assertIn('original successful snapshot',proof['scope'])
        self.assertEqual(proof['historical_viewer_source_commit'],'b'*40)

    def test_changed_snapshot_or_original_report_is_rejected(self):
        original_html=self.html.read_bytes()
        self.html.write_bytes(original_html+b'changed')
        with self.assertRaises(ValueError):M.load_snapshot(self.html,self.receipt)
        self.html.write_bytes(original_html)
        self.report.write_text(json.dumps(dict(cases=[dict(self.case,value=0.)])))
        with self.assertRaises(ValueError):M.load_snapshot(self.html,self.receipt)

    def test_merge_preserves_old_values_baseline_and_rejects_conflicting_duplicate(self):
        candidate=dict(self.case,summary_path=str(self.root/'new.json'),case_id='new',run_id='newrun',value=4.)
        new=dict(report=dict(cases=[copy.deepcopy(self.case),candidate]))
        before=copy.deepcopy(self.model)
        with patch.object(M.view,'build_model',return_value=dict(audits=[])):
            merged=M.merge_model(self.model,new)
            self.assertEqual(len(merged['cases']),2)
            self.assertEqual(merged['cohorts'][0]['baseline_id'],'historical/baseline')
            self.assertEqual(merged['cases'][0]['value'],self.case['value'])
            self.assertEqual(self.model,before)
            new['report']['cases'][0]['value']=9.
            with self.assertRaises(ValueError):M.merge_model(self.model,new)

    def test_new_report_completion_markers_are_explicit_empty_hashed_metadata(self):
        spec=importlib.util.spec_from_file_location('merge_audit_fixture',ROOT/'tests/test_task1_volume_audit_view.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fixture=module.VolumeAuditViewTests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        marker=fixture.directory/'run/bases/case/BASIS_COMPLETE';marker.parent.mkdir(parents=True);marker.write_bytes(b'')
        fixture.report['inputs_sha256'][str(marker)]=M.view.sha(marker);fixture.write()
        result=M.validate_new_audit(fixture.path)
        self.assertIn(str(marker),result['verified_small_inputs'])
        marker.write_bytes(b'nonempty');fixture.report['inputs_sha256'][str(marker)]=M.view.sha(marker);fixture.write()
        with self.assertRaisesRegex(ValueError,'marker must remain empty'):M.validate_new_audit(fixture.path)

    def test_new_report_rejects_unregistered_marker_names(self):
        spec=importlib.util.spec_from_file_location('merge_other_fixture',ROOT/'tests/test_task1_volume_audit_view.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fixture=module.VolumeAuditViewTests('runTest');fixture.setUp();self.addCleanup(fixture.doCleanups)
        marker=fixture.directory/'run/bases/case/OTHER_COMPLETE';marker.parent.mkdir(parents=True);marker.write_bytes(b'')
        fixture.report['inputs_sha256'][str(marker)]=M.view.sha(marker);fixture.write()
        with self.assertRaisesRegex(ValueError,'Unsupported small input type'):M.validate_new_audit(fixture.path)


if __name__=='__main__':unittest.main()
