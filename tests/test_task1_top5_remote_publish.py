"""Synthetic publication guards only; no API, Git mutation or research inputs."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import task1_top5_remote_publish as publisher


HEAD = 'a' * 40
ADVANCED = 'd' * 40
BASE_TREE = 'b' * 40
NEW_TREE = 'c' * 40
NEW_COMMIT = 'e' * 40
DOCS_TREE = 'f' * 40
BUNDLE_TREE = '1' * 40


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


class FakeGitDatabase:
    """A Git database API recorder; deliberately has no network implementation."""

    def __init__(self, root, *, concurrent_advance=False):
        self.root = root
        self.concurrent_advance = concurrent_advance
        self.calls = []
        self.ref_reads = 0
        self.blobs = {}
        self.tree_body = None
        self.commit_body = None
        self.patch_body = None

    def __call__(self, argv, input_bytes=None):
        if argv[:2] != ['gh', 'api']:
            raise AssertionError('Only mocked gh api calls are permitted: ' + repr(argv))
        endpoint = argv[2]
        method = argv[argv.index('-X') + 1] if '-X' in argv else 'GET'
        body = json.loads(input_bytes) if input_bytes is not None else None
        self.calls.append((method, endpoint, body))
        if '/git/ref/heads/' in endpoint and method == 'GET':
            self.ref_reads += 1
            current = HEAD
            if self.patch_body is not None:
                current = NEW_COMMIT
            elif self.concurrent_advance and self.ref_reads >= 2:
                current = ADVANCED
            return json.dumps({'object': {'sha': current}})
        if endpoint.endswith('/git/commits/' + HEAD) and method == 'GET':
            return json.dumps({'tree': {'sha': BASE_TREE}})
        if endpoint.endswith('/git/commits/' + NEW_COMMIT) and method == 'GET':
            return json.dumps({'tree': {'sha': NEW_TREE}, 'parents': [{'sha': HEAD}]})
        if endpoint.endswith('/git/blobs') and method == 'POST':
            if body.get('encoding') != 'base64':
                raise AssertionError('Binary-safe blob encoding required')
            raw = base64.b64decode(body['content'], validate=True)
            sha = git_blob(raw)
            self.blobs[sha] = raw
            return json.dumps({'sha': sha})
        if endpoint.endswith('/git/trees') and method == 'POST':
            self.tree_body = body
            return json.dumps({'sha': NEW_TREE})
        if endpoint.endswith('/git/commits') and method == 'POST':
            self.commit_body = body
            return json.dumps({'sha': NEW_COMMIT})
        if '/git/refs/heads/' in endpoint and method == 'PATCH':
            self.patch_body = body
            return json.dumps({'object': {'sha': NEW_COMMIT}})
        if '/git/trees/' in endpoint and method == 'GET':
            sha = endpoint.rsplit('/', 1)[-1]
            entries = {
                NEW_TREE: [dict(path='docs', mode='040000', type='tree', sha=DOCS_TREE)],
                DOCS_TREE: [dict(path='TASK1_TOP5_20261022_compact', mode='040000', type='tree', sha=BUNDLE_TREE)],
                BUNDLE_TREE: [dict(path=Path(row['path']).name, mode='100644', type='blob', sha=row['sha'])
                              for row in self.tree_body['tree']],
            }
            return json.dumps({'sha': sha, 'truncated': False, 'tree': entries[sha]})
        raise AssertionError('Unexpected mocked API request: ' + repr((method, endpoint)))


class Top5RemotePublishTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / 'docs/TASK1_TOP5_20261022_compact'
        directory.mkdir(parents=True)
        content = {'index.html': b'<html>synthetic saved evidence</html>\n',
                   'preview.png': b'\x89PNG\r\n\x1a\nsynthetic-preview',
                   'README.md': b'Synthetic publication fixture only.\n'}
        for name, raw in content.items():
            (directory / name).write_bytes(raw)
        manifest = dict(status='compact_dashboard_complete_unadopted', native_inputs_unchanged=True,
                        artifacts={name: dict(SHA256=digest(content[name]), bytes=len(content[name]))
                                   for name in ('index.html', 'preview.png')})
        manifest_bytes = (json.dumps(manifest, sort_keys=True) + '\n').encode()
        (directory / 'manifest.json').write_bytes(manifest_bytes)
        validation = root / 'docs/external-final-validation.json'
        validation.write_text(json.dumps(dict(status='existing_compact_GUI_verified_unadopted',
            input_sha256={str(directory / 'manifest.json'): digest(manifest_bytes),
                          str(directory / 'index.html'): digest(content['index.html'])})))
        return directory, validation

    def test_bundle_requires_successful_bound_validation_and_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            directory, validation = self.fixture(root)
            files = publisher.validate_bundle(directory, validation, root=root)
            self.assertEqual({p.name for p in files}, {'index.html', 'manifest.json', 'preview.png', 'README.md'})
            proof = json.loads(validation.read_text())
            validation.write_text(json.dumps(dict(proof, status='failed')))
            with self.assertRaises((ValueError, RuntimeError)):
                publisher.validate_bundle(directory, validation, root=root)
            validation.write_text(json.dumps(proof))
            (directory / 'index.html').write_bytes(b'<html>changed after validation</html>')
            with self.assertRaises((ValueError, RuntimeError)):
                publisher.validate_bundle(directory, validation, root=root)

    def test_concurrent_remote_advance_aborts_without_ref_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            directory, validation = self.fixture(root)
            files = publisher.validate_bundle(directory, validation, root=root)
            run = FakeGitDatabase(root, concurrent_advance=True)
            with self.assertRaises((ValueError, RuntimeError)):
                publisher.remote_update(HEAD, files, run, root=root)
            self.assertGreaterEqual(run.ref_reads, 2)
            self.assertIsNone(run.patch_body)
            self.assertFalse(any(method == 'PATCH' for method, _, _ in run.calls))

    def test_success_uploads_exact_blobs_based_tree_parent_head_and_nonforce_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            directory, validation = self.fixture(root)
            files = publisher.validate_bundle(directory, validation, root=root)
            before = {p: p.read_bytes() for p in files}
            run = FakeGitDatabase(root)
            commit = publisher.remote_update(HEAD, files, run, root=root)
            self.assertEqual(commit, NEW_COMMIT)
            self.assertEqual(run.tree_body['base_tree'], BASE_TREE)
            self.assertEqual(run.commit_body['tree'], NEW_TREE)
            self.assertEqual(run.commit_body['parents'], [HEAD])
            self.assertEqual(run.patch_body, {'sha': NEW_COMMIT, 'force': False})
            self.assertEqual(run.blobs, {git_blob(raw): raw for raw in before.values()})
            self.assertEqual({row['path'] for row in run.tree_body['tree']},
                             {p.relative_to(root).as_posix() for p in files})
            self.assertTrue(all(row['mode'] == '100644' and row['type'] == 'blob'
                                for row in run.tree_body['tree']))
            self.assertEqual(before, {p: p.read_bytes() for p in files})


if __name__ == '__main__':
    unittest.main()
