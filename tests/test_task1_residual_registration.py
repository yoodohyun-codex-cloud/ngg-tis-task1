"""Held-reference provenance counterexamples; no Java or phantom calculation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import task1_residual_registration as residual


def digest(data):
    return hashlib.sha256(data).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True))


class CachedReferenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        self.patch = patch.object(residual.core, 'REPO', self.repo)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def fixture(self, *, held=True, case_id=None, run_name=None):
        case_id = case_id or (residual.HELD_CASE if held else 'baseline-square15-coarse')
        run = self.repo/'data-native'/(run_name or (residual.HELD_RUN if held else 'cloud-baseline-fixture'))
        folder = run/'bases'/case_id
        folder.mkdir(parents=True)
        config, mask = run/'configs/source.properties', run/'masks/source.csv'
        config.parent.mkdir(); mask.parent.mkdir()
        config.write_bytes(b'channels=2\nfrequencies=3000,3030,9000,9090\n')
        mask.write_bytes(b'pad,i,j,area_m2\n0,1,1,.000225\n')
        case = dict(id=case_id, config_file=str(config), config_sha256=digest(config.read_bytes()),
                    mask_file=str(mask), mask_sha256=digest(mask.read_bytes()))
        files = ['BASIS_COMPLETE', 'grid.csv', 'contacts-3000.csv']
        files += [kind+'-3000.bin' for kind in residual.ARRAYS]
        for name in files:
            (folder/name).write_bytes(b'' if name == 'BASIS_COMPLETE' else name.encode())
        put(folder/'mesh-metadata.json', dict(exporter_class='SelectivityShapeBasis', channels=2,
            config_sha256=case['config_sha256'], frequencies_Hz=[3000, 3030, 9000, 9090]))
        put(folder/'validation.json', {key: limit/10 for key, limit in residual.core.GATES.items()})
        pins = {str(path): digest(path.read_bytes()) for path in (*folder.iterdir(), config, mask)}
        manifest = digest(json.dumps(pins, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
        post = run/'postprocess'/case_id/'summary.json'
        put(post, dict(id=case_id, status='complete', input_sha256=pins, input_manifest_sha256=manifest))
        registration = run/'preregistration.json'
        put(registration, dict(cases=[case]))
        if held:
            put(run/'reference-comparison.json', dict(status='failed', run_id=run.name, case_id=case_id,
                matrix_relative_tolerance=1e-8, absolute_tolerance=1e-14,
                circuit_comparisons=[dict(name='source-3000.bin', passed=False)]))
            put(run/'controller.json', dict(status='error', phase='stopped', current_case=case_id,
                current_config_sha256=case['config_sha256']))
            receipt = dict(status='error', run_id=run.name, failed_case=case_id,
                registration_sha256=digest(registration.read_bytes()), partial_evidence_preserved=True,
                error='Historical Best1 mismatch; C1 not run before investigation')
            put(run/'summary.json', receipt)
            put(run/'failure.json', receipt)
        else:
            put(run/'cases'/(case_id+'.json'), dict(status='complete', postprocess_path=str(post),
                postprocess_sha256=digest(post.read_bytes())))
        return run, case, folder, post

    def test_complete_baseline_receipt_remains_required_and_accepted(self):
        run, case, _, _ = self.fixture(held=False)
        _, reference = residual._reference(case['id'])
        self.assertTrue(reference['case_completion_receipt_present'])
        self.assertEqual(reference['reference_status'], 'case_calculated_complete')
        (run/'cases'/(case['id']+'.json')).unlink()
        with self.assertRaisesRegex(ValueError, 'Only the explicitly held D'):
            residual._reference(case['id'])

    def test_held_D_missing_case_receipt_accepted_read_only_with_failed_proof(self):
        run, case, _, _ = self.fixture()
        before = {str(path): digest(path.read_bytes()) for path in run.rglob('*') if path.is_file()}
        _, reference = residual._reference(case['id'])
        self.assertEqual(reference['reference_status'], 'held_computed_only')
        self.assertFalse(reference['case_completion_receipt_present'])
        self.assertFalse(reference['historical_strict_reproduction_passed'])
        self.assertIn(str(run/'failure.json'), reference['input_sha256'])
        self.assertEqual(before, {str(path): digest(path.read_bytes()) for path in run.rglob('*') if path.is_file()})
        self.assertFalse((run/'cases'/(case['id']+'.json')).exists())

    def test_missing_failed_proof_is_not_generic_completion_bypass(self):
        run, case, _, _ = self.fixture()
        (run/'failure.json').unlink()
        with self.assertRaisesRegex(ValueError, 'failure proof missing'):
            residual._reference(case['id'])

    def test_reclassified_historical_comparison_is_rejected(self):
        run, case, _, _ = self.fixture()
        proof = json.loads((run/'reference-comparison.json').read_text())
        proof['status'] = 'passed'
        put(run/'reference-comparison.json', proof)
        with self.assertRaisesRegex(ValueError, 'must remain failed'):
            residual._reference(case['id'])

    def test_wrong_controller_case_and_registration_proof_rejected(self):
        run, case, _, _ = self.fixture()
        controller = json.loads((run/'controller.json').read_text())
        controller['current_case'] = 'some-other-case'
        put(run/'controller.json', controller)
        with self.assertRaisesRegex(ValueError, 'controller does not prove stop'):
            residual._reference(case['id'])
        controller['current_case'] = case['id']
        put(run/'controller.json', controller)
        failure = json.loads((run/'failure.json').read_text())
        failure['registration_sha256'] = '0'*64
        put(run/'failure.json', failure)
        with self.assertRaisesRegex(ValueError, 'error/registration proof differs'):
            residual._reference(case['id'])

    def test_other_run_with_same_case_cannot_use_held_exception(self):
        _, case, _, _ = self.fixture(run_name='cloud-not-the-held-D')
        with self.assertRaisesRegex(ValueError, 'Only the explicitly held D'):
            residual._reference(case['id'])

    def test_held_raw_corruption_is_rejected(self):
        _, case, folder, _ = self.fixture()
        (folder/'source-3000.bin').write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'Cached native SHA differs'):
            residual._reference(case['id'])

    def test_held_postprocess_manifest_corruption_is_rejected(self):
        _, case, _, post = self.fixture()
        value = json.loads(post.read_text())
        value['input_manifest_sha256'] = '0'*64
        put(post, value)
        with self.assertRaisesRegex(ValueError, 'input manifest differs'):
            residual._reference(case['id'])

    def test_complete_receipt_cannot_bypass_postprocess_sha(self):
        _, case, _, post = self.fixture(held=False)
        post.write_text(post.read_text()+' ')
        with self.assertRaisesRegex(ValueError, 'postprocess SHA/path differs'):
            residual._reference(case['id'])


if __name__ == '__main__':
    unittest.main()
