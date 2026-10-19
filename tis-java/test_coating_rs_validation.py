"""Isolated coating-executor guards; no prepare, compiler, Java or PDE calls.

Temporary fixtures stand in for immutable manifests. Production inputs, source
hashes, workers and numerical module globals are never changed by these tests.
"""
from contextlib import nullcontext
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import coating_rs_validation as coat


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metric(wave, factor=1.0):
    return dict(waveform=wave, target20_modulation_V_m=3 * factor,
                target20_total_E_RMS_V_m=2 * factor,
                surface_J_RMS_max_A_m2=10 * factor,
                surface_J_RMS_p95_A_m2=7 * factor,
                SC_power_W=4 * factor * factor,
                contact_power_W=9 * factor * factor,
                contact_voltage_RMS_max_V=5 * factor,
                source_power_W=16 * factor * factor)


class NoExecution(unittest.TestCase):
    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        self.process = mock.patch.object(subprocess, 'Popen',
            side_effect=AssertionError('A unit test attempted a real process')).start()
        self.runner = mock.patch.object(coat.common, 'run_guarded',
            side_effect=AssertionError('Compiler/Java/PDE is forbidden here')).start()


class ManifestGuards(NoExecution):
    def setUp(self):
        super().setUp()
        original_preparation = coat.PREPARATION
        self.spec = json.loads((original_preparation / 'preregistration.json').read_text())
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'tis-java'
        self.prep = self.root / 'runs' / 'fixture-inputs'
        self.output = self.root / 'runs' / 'coating-rs-validation-fixture'
        self.prep.mkdir(parents=True)
        self.output.mkdir(parents=True)
        for name in ('inputs', 'configs', 'classes', 'private-src', 'logs'):
            (self.output / name).mkdir()
        for case in self.spec['case_plan']:
            target = self.output / case['config_file']
            target.write_bytes((original_preparation / case['config_file']).read_bytes())
        for name in set(coat.SOURCES + coat.DEPENDENCIES):
            (self.root / name).write_text('unit fixture: ' + name)
        (self.output / 'private-src' / 'CoatingRsBasis.java').write_text('fixture only')
        (self.output / 'classes' / 'CoatingRsBasis.class').write_bytes(b'not executable')
        (self.output / 'inputs' / 'fixture.json').write_text('{}\n')
        self.preparation_file = self.prep / 'preregistration.json'
        self.preparation_file.write_text(json.dumps(self.spec))
        self.registration = dict(
            authorization=dict(user_instruction=coat.AUTHORIZATION),
            maximum_new_PDE_cases=9, complete_basis_reuse_count=1,
            case_plan=copy.deepcopy(self.spec['case_plan']),
            resource_limits=copy.deepcopy(coat.LIMITS),
            numerical_gates=copy.deepcopy(coat.NUMERICAL),
            execution_source_hashes={str(self.root / n): digest(self.root / n)
                for n in set(coat.SOURCES + coat.DEPENDENCIES)})
        self.registration_file = self.output / 'preregistration.json'
        self.registration_file.write_text(json.dumps(self.registration))
        mock.patch.object(coat, 'ROOT', self.root).start()
        mock.patch.object(coat, 'PREPARATION', self.prep).start()
        mock.patch.object(coat, 'PREP_SHA', digest(self.preparation_file)).start()
        self.manifest = dict(status='prepared', output_run=str(self.output),
            preparation_sha256=coat.PREP_SHA,
            preregistration_sha256=digest(self.registration_file),
            resource_limits=copy.deepcopy(coat.LIMITS),
            numerical_gates=copy.deepcopy(coat.NUMERICAL),
            plan=coat.plan_for(self.spec, self.output),
            classes=str(self.output / 'classes'), java='/forbidden/java',
            preparation_wall_seconds=0)
        files = [self.registration_file,
                 *[self.root / n for n in set(coat.SOURCES + coat.DEPENDENCIES)],
                 *[Path(c['config_file']) for c in self.manifest['plan']]]
        files += [p for d in ('inputs', 'private-src', 'classes')
                  for p in (self.output / d).iterdir()]
        self.manifest['guard_hashes'] = {str(p): digest(p) for p in files}

    def rebind_registration(self):
        self.registration_file.write_text(json.dumps(self.registration))
        sha = digest(self.registration_file)
        self.manifest['preregistration_sha256'] = sha
        self.manifest['guard_hashes'][str(self.registration_file)] = sha

    def test_valid_frozen_fixture_is_accepted_without_execution(self):
        self.assertTrue(coat.validate_manifest(self.manifest))
        self.runner.assert_not_called()
        self.process.assert_not_called()

    def test_plan_is_ten_ordered_conditions_and_only_bare_reuses(self):
        before = copy.deepcopy(self.spec)
        plan = coat.plan_for(self.spec, self.output)
        self.assertEqual(self.spec, before)
        self.assertEqual([c['id'] for c in plan],
                         [c['condition_id'] for c in self.spec['case_plan']])
        self.assertEqual(len(plan), 10)
        self.assertEqual([c['id'] for c in plan
                          if c['execution_action'] == 'reuse_verified_complete_basis'],
                         ['coat000-minusRs'])
        self.assertEqual(sum(c['execution_action'] == 'new_private_solve' for c in plan), 9)

    def test_reordered_or_relabelled_or_extra_case_is_rejected(self):
        for mutate in (lambda p: p.reverse(),
                       lambda p: p.append(copy.deepcopy(p[0])),
                       lambda p: p[1].update(id='coat000-minusRs'),
                       lambda p: p[1].update(execution_action='reuse_verified_complete_basis')):
            with self.subTest(mutation=mutate):
                value = copy.deepcopy(self.manifest)
                mutate(value['plan'])
                with self.assertRaises(ValueError): coat.validate_manifest(value)

    def test_frequency_phase_coating_boundary_and_mesh_tampering_rejected(self):
        mutations = [lambda c: c.update(frequencies_Hz=[2000, 2010, 6000, 6030]),
                     lambda c: c['design'].update(phase_deg=[0, 90]),
                     lambda c: c.update(thickness_nm=999),
                     lambda c: c.update(boundary_mode='full_measured'),
                     lambda c: c.update(h_xy_mm=.625),
                     lambda c: c.update(sc_cells=8)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                value = copy.deepcopy(self.manifest)
                mutate(value['plan'][0])
                with self.assertRaises(ValueError): coat.validate_manifest(value)

    def test_resource_and_numerical_caps_cannot_be_widened_or_nonfinite(self):
        for namespace in ('resource_limits', 'numerical_gates'):
            for key, original in self.manifest[namespace].items():
                values = [float('nan'), float('inf'), -1]
                values.append(original * 2 if isinstance(original, (int, float))
                              else 'changed')
                for changed in values:
                    with self.subTest(namespace=namespace, key=key, changed=changed):
                        value = copy.deepcopy(self.manifest)
                        value[namespace][key] = changed
                        with self.assertRaises(ValueError): coat.validate_manifest(value)

    def test_registration_plan_caps_and_authorization_cannot_be_rebound(self):
        original = copy.deepcopy(self.registration)
        changes = [lambda r: r.update(maximum_new_PDE_cases=10),
                   lambda r: r['authorization'].update(user_instruction='continue'),
                   lambda r: r['case_plan'].reverse(),
                   lambda r: r['resource_limits'].update(per_case_wall_seconds=601),
                   lambda r: r['numerical_gates'].update(max_residual=1)]
        for mutate in changes:
            with self.subTest(mutation=mutate):
                self.registration = copy.deepcopy(original)
                mutate(self.registration)
                self.rebind_registration()
                with self.assertRaises(ValueError): coat.validate_manifest(self.manifest)

    def test_new_config_bytes_cannot_be_accepted_by_rehashing_only_the_guard(self):
        cfg = Path(self.manifest['plan'][1]['config_file'])
        cfg.write_bytes(cfg.read_bytes() + b'\n# changed bytes\n')
        self.manifest['guard_hashes'][str(cfg)] = digest(cfg)
        with self.assertRaises(ValueError): coat.validate_manifest(self.manifest)

    def test_missing_dependency_or_class_guard_is_rejected(self):
        for path in (self.root / 'validation_3k_postprocess.py',
                     self.output / 'classes' / 'CoatingRsBasis.class'):
            with self.subTest(path=path):
                value = copy.deepcopy(self.manifest)
                del value['guard_hashes'][str(path)]
                with self.assertRaises(ValueError): coat.validate_manifest(value)

    def test_producer_source_namespace_cannot_be_changed(self):
        path = str(self.root / 'CoatingRsBasis.java')
        self.registration['execution_source_hashes'][path] = '0' * 64
        self.rebind_registration()
        with self.assertRaises(ValueError): coat.validate_manifest(self.manifest)

    def test_wrong_output_or_classpath_is_rejected(self):
        for key, value in [('output_run', str(self.root / 'runs' / 'original-source')),
                           ('classes', str(self.root))]:
            bad = copy.deepcopy(self.manifest); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                coat.validate_manifest(bad)

    def test_missing_or_wrong_publication_receipt_never_launches(self):
        (self.output / 'manifest.json').write_text(json.dumps(self.manifest))
        for receipt in ({}, dict(status='published_before_PDE', manifest_sha256='wrong',
                                 preregistration_sha256=self.manifest['preregistration_sha256'])):
            (self.output / 'execution-publication.json').write_text(json.dumps(receipt))
            with self.assertRaises(ValueError): coat.execute(self.manifest)
        self.runner.assert_not_called()

    def test_completed_partial_and_failed_summaries_are_never_retried(self):
        mf = self.output / 'manifest.json'
        mf.write_text(json.dumps(self.manifest))
        receipt = dict(status='published_before_PDE', manifest_sha256=digest(mf),
                       preregistration_sha256=self.manifest['preregistration_sha256'])
        (self.output / 'execution-publication.json').write_text(json.dumps(receipt))
        mock.patch.object(coat.common, 'diagnostic_lock', return_value=nullcontext()).start()
        summary = self.output / 'summary.json'
        for status in ('complete', 'running', 'stopped', 'postprocessing_failed', 'interrupted'):
            summary.write_text(json.dumps(dict(status=status)))
            before = summary.read_bytes()
            with self.subTest(status=status), self.assertRaises(ValueError):
                coat.execute(self.manifest)
            self.assertEqual(summary.read_bytes(), before)
        self.runner.assert_not_called()
        self.process.assert_not_called()


class SameWaveBaselines(NoExecution):
    def test_waveform_join_uses_same_wave_despite_different_order_and_amplitude(self):
        bare = [metric('sine', 1), metric('square_3h', 3), metric('triangle_3h', 2)]
        rows = [metric('triangle_3h', 4), metric('sine', 2), metric('square_3h', 6)]
        original_bare = copy.deepcopy(bare)
        result = coat.matched_rows(rows, bare)
        for row in result:
            cap = row['same_wave_bare_baseline']
            self.assertEqual(cap['waveform'], row['waveform'])
            self.assertAlmostEqual(cap['burden_source_Vpp'], .5)
            self.assertAlmostEqual(cap['power_source_Vpp'], .5)
            self.assertEqual(cap['condition_id'], 'xy120-leader')
        self.assertEqual(bare, original_bare)

    def test_bare_copy_self_reference_is_one_without_modifying_original(self):
        bare = [metric(w, i) for i, w in enumerate(('sine', 'square_3h', 'triangle_3h'), 1)]
        original = copy.deepcopy(bare)
        result = coat.matched_rows(copy.deepcopy(bare), bare)
        for row in result:
            cap = row['same_wave_bare_baseline']
            self.assertEqual(cap['burden_source_Vpp'], 1)
            self.assertEqual(cap['power_source_Vpp'], 1)
        self.assertEqual(bare, original)

    def test_cap_does_not_increase_source_to_exhaust_unused_budget(self):
        row = metric('sine', .5)
        cap = coat.matched_rows([row], [metric('sine', 1)])[0]['same_wave_bare_baseline']
        self.assertEqual(cap['burden_source_Vpp'], 1)
        self.assertEqual(cap['power_source_Vpp'], 1)

    def test_J95_is_report_only_and_does_not_define_the_existing_cap(self):
        row = metric('sine', 1); row['surface_J_RMS_p95_A_m2'] = 1e30
        cap = coat.matched_rows([row], [metric('sine', 1)])[0]['same_wave_bare_baseline']
        self.assertEqual(cap['burden_source_Vpp'], 1)


if __name__ == '__main__':
    unittest.main()
