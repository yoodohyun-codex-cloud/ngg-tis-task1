"""Execution-boundary regressions; no research imports or phantom solves.

Optional Java cases call only CloudShapeBasis.cloudPathsGuard via a tiny harness.
Set TASK1_CLOUD_CLASSES to the isolated compiled adapter class directory to run
them; compilation of the numerical sources belongs to the bounded controller.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('task1_cloud_batch_test_target', ROOT/'tools/task1_cloud_batch.py')
batch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(batch)


def digest(value):
    return hashlib.sha256(value).hexdigest()


class OriginalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.original = self.repo/'original.dat'
        self.original.write_bytes(b'original')
        (self.repo/'PACKAGE_INDEX.json').write_text(json.dumps({'files': [
            {'path': 'original.dat', 'bytes': 8, 'sha256': digest(b'original')}
        ]}))
        self.patcher = patch.object(batch, 'REPO', self.repo)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_new_artifacts_allowed_but_changed_original_rejected(self):
        (self.repo/'new-report.json').write_text('{}')
        self.assertEqual(batch.original_integrity()['files'], 1)
        self.original.write_bytes(b'mutated!')  # Same byte count isolates SHA checking.
        with self.assertRaisesRegex(ValueError, 'Original payload changed original.dat'):
            batch.original_integrity()

    def test_missing_and_symlink_originals_rejected(self):
        self.original.unlink()
        with self.assertRaisesRegex(ValueError, 'Missing original'):
            batch.original_integrity()
        target = self.repo/'copy.dat'
        target.write_bytes(b'original')
        self.original.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'Missing original'):
            batch.original_integrity()

    def test_changed_source_pin_rejected_before_research_import_or_child(self):
        (self.repo/'runtime').mkdir()
        pinned = self.repo/'solver.java'
        pinned.write_bytes(b'changed')
        pre = {'preparation_seconds': 0., 'source_and_input_sha256': {str(pinned): digest(b'frozen')}}
        imports = []
        original_import = __import__

        def checked_import(name, *args, **kwargs):
            imports.append(name)
            if name == 'selectivity_postprocess':
                self.fail('Research module imported before source pins passed')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=checked_import), patch.object(batch.subprocess, 'Popen') as child:
            with self.assertRaisesRegex(ValueError, 'Pinned source/input changed'):
                batch.execute_locked(self.repo/'data-native/cloud-test', pre)
            child.assert_not_called()
        self.assertNotIn('selectivity_postprocess', imports)
        self.assertFalse((self.repo/'data-native').exists())


class RunBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.native = self.repo/'data-native'
        self.native.mkdir()
        self.run = self.native/'cloud-test'
        self.patcher = patch.object(batch, 'REPO', self.repo)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.affinity = patch.object(batch.os, 'sched_setaffinity')
        self.affinity.start()
        self.addCleanup(self.affinity.stop)

    def test_wrong_parent_and_old_run_namespace_rejected(self):
        for run in (self.repo/'cloud-test', self.native/'selectivity-design-old'):
            with self.subTest(run=run), self.assertRaisesRegex(ValueError, 'New run must'):
                batch.paths_check(run)

    def test_run_symlink_rejected(self):
        target = self.native/'cloud-target'
        target.mkdir()
        self.run.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            batch.paths_check(self.run)

    def test_duplicate_preparation_preserves_existing_evidence(self):
        hist = self.repo/'history'
        hist.mkdir()
        (hist/'preregistration.json').write_text(json.dumps({'case_pool': {'baseline': {}}}))
        self.run.mkdir()
        evidence = self.run/'failure-evidence.json'
        evidence.write_bytes(b'preserve-me')
        with patch.object(batch, 'HIST', hist), patch.object(batch, 'original_integrity', return_value={}), \
                patch.object(batch.subprocess, 'run') as launched:
            with self.assertRaisesRegex(ValueError, 'Never overwrite or retry'):
                batch.prepare(self.run, ['baseline'])
            launched.assert_not_called()
        self.assertEqual(evidence.read_bytes(), b'preserve-me')
        self.assertEqual(sorted(p.name for p in self.run.iterdir()), ['failure-evidence.json'])

    def test_duplicate_case_ids_rejected_before_create_or_compile(self):
        with patch.object(batch, 'original_integrity', return_value={}), patch.object(batch.subprocess, 'run') as launched:
            with self.assertRaisesRegex(ValueError, 'Finite unique'):
                batch.prepare(self.run, ['baseline', 'baseline'])
            launched.assert_not_called()
        self.assertFalse(self.run.exists())


class FrozenNumericalBodyTests(unittest.TestCase):
    def test_adapter_retains_frozen_numerical_main_body(self):
        frozen = (ROOT/'tis-java/SelectivityShapeBasis.java').read_text()
        adapter = (ROOT/'tools/java/CloudShapeBasis.java').read_text()
        marker = '    Properties p=new Properties();try(InputStream in=new ByteArrayInputStream(configBytes)){p.load(in);}'
        original_body = frozen.split(marker, 1)[1]
        adapted_body = adapter.split(marker, 1)[1].replace('    wrapperReceipt(dir);\n', '')
        self.assertEqual(digest(original_body.encode()), digest(adapted_body.encode()),
                         'New execution boundary must preserve the frozen numerical loop and exports')


class JavaPathGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        classes = os.environ.get('TASK1_CLOUD_CLASSES')
        if not classes:
            raise unittest.SkipTest('Set TASK1_CLOUD_CLASSES to bounded-controller compiled classes for Java guard fixtures')
        cls.classes = Path(classes).resolve()
        if not (cls.classes/'CloudShapeBasis.class').is_file():
            raise unittest.SkipTest('CloudShapeBasis compiled class unavailable')
        javac = shutil.which('javac')
        if not javac:
            candidate = Path('/workspace/.cloud-setup/jdk/usr/lib/jvm/java-21-openjdk-amd64/bin/javac')
            javac = str(candidate) if candidate.is_file() else None
        if not javac:
            raise unittest.SkipTest('Java guard fixture compiler unavailable')
        cls.java = str(Path(javac).parent/'java')
        cls.temp_classes = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp_classes.cleanup)
        output = Path(cls.temp_classes.name)
        harness = output/'CloudPathGuardHarness.java'
        harness.write_text('''import java.nio.file.*;
public class CloudPathGuardHarness {
  public static void main(String[] args)throws Exception {
    System.out.println(CloudShapeBasis.cloudPathsGuard(Paths.get(args[0]),Paths.get(args[1]),Paths.get(args[2]),Paths.get(args[3])));
  }
}
''')
        subprocess.run([javac, '-J-Xmx128m', '-J-XX:ActiveProcessorCount=1', '-cp', str(cls.classes),
                        '-d', str(output), str(harness)], check=True, capture_output=True, timeout=30)
        cls.classpath = os.pathsep.join((str(output), str(cls.classes)))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name).resolve()
        self.run = self.repo/'data-native/cloud-test'
        (self.run/'configs').mkdir(parents=True)
        (self.run/'bases').mkdir()
        self.config = self.run/'configs/baseline.properties'
        self.config.write_text('fixture only; no research solver\n')
        self.basis = self.run/'bases/baseline'

    def invoke(self, *, run=None, config=None, basis=None):
        return subprocess.run([self.java, '-Xmx32m', '-XX:ActiveProcessorCount=1', '-cp', self.classpath,
                               'CloudPathGuardHarness', str(self.repo), str(run or self.run),
                               str(config or self.config), str(basis or self.basis)],
                              capture_output=True, text=True, timeout=10)

    def test_valid_layout_allows_only_path_validation_without_output(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'baseline')
        self.assertFalse(self.basis.exists())

    def test_config_cannot_be_outside_registered_run(self):
        other = self.repo/'baseline.properties'
        other.write_bytes(self.config.read_bytes())
        result = self.invoke(config=other)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Config must be regular run/configs', result.stderr)

    def test_basis_cannot_escape_or_overwrite(self):
        outside = self.repo/'baseline'
        result = self.invoke(basis=outside)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Basis output must be the absent', result.stderr)
        self.basis.mkdir()
        (self.basis/'failure.bin').write_bytes(b'evidence')
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.basis/'failure.bin').read_bytes(), b'evidence')

    def test_symlink_config_and_directory_aliases_rejected(self):
        outside = self.repo/'outside'
        outside.mkdir()
        target = outside/'baseline.properties'
        target.write_bytes(self.config.read_bytes())
        self.config.unlink()
        self.config.symlink_to(target)
        self.assertNotEqual(self.invoke().returncode, 0)
        self.config.unlink()
        (self.run/'configs').rmdir()
        (self.run/'configs').symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.invoke().returncode, 0)

    def test_symlink_basis_directory_and_run_alias_rejected(self):
        outside = self.repo/'outside'
        outside.mkdir()
        (self.run/'bases').rmdir()
        (self.run/'bases').symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.invoke().returncode, 0)
        (self.run/'bases').unlink()
        (self.run/'bases').mkdir()
        alias = self.repo/'data-native/cloud-alias'
        alias.symlink_to(self.run, target_is_directory=True)
        self.assertNotEqual(self.invoke(run=alias).returncode, 0)


if __name__ == '__main__':
    unittest.main()
