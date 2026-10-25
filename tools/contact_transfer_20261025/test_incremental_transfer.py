"""Pure metadata contracts; source-only preparation does not execute these."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from incremental_transfer import merge_files, merge_manifest, receipt_entries


def previous():
    sha = "a" * 64
    return {"schema": "task1-safe-windows-transfer-manifest-v1",
            "repository": "yoodohyun-codex-cloud/ngg-tis-task1",
            "public_reference_commit": "1" * 40, "Windows_backup_complete": False,
            "OneDrive_sync_verified": False,
            "files": [{"fixed_commit": "1" * 40, "repo_relative_path": "data-native/old/arrays.npz",
                       "bytes": 99, "SHA256": sha,
                       "safe_destination_relative_path": "objects/" + sha + ".npz"}],
            "logical_file_aliases": [], "durability_gaps": [],
            "required_local_only_raw_arrays": [],
            "old_scientific_failure_evidence": {"adopted": False, "status": "failed_gate_retained"}}


def published(commit, path, sha, size):
    return {"status": "published_readback_verified", "commit": commit,
            "files": {path: {"SHA256": sha, "bytes": size, "readback_passed": True}}}


def publications():
    return (published("2" * 40, "tools/new/source.py", "b" * 64, 10),
            published("3" * 40, "data-native/new/arrays.npz", "c" * 64, 4_500_000_000),
            published("4" * 40, "docs/new/original-receipt.json", "d" * 64, 200))


class IncrementalContracts(unittest.TestCase):
    def test_additive_merge_preserves_old_objects_and_failed_gate(self):
        old = previous(); snapshot = copy.deepcopy(old)
        merged = merge_manifest(old, *publications(), package_id="new-condition")
        self.assertEqual(old, snapshot)
        self.assertEqual(merged["files"][0], old["files"][0])
        self.assertEqual(merged["old_scientific_failure_evidence"], old["old_scientific_failure_evidence"])
        self.assertEqual(len(merged["files"]), 4)
        self.assertFalse(merged["Windows_backup_complete"])

    def test_full_large_size_is_metadata_only_and_not_truncated(self):
        merged = merge_manifest(previous(), *publications(), package_id="large-identity")
        self.assertIn(4_500_000_000, [x["bytes"] for x in merged["files"]])

    def test_identical_bytes_become_alias_without_duplicate_object(self):
        source, result, metadata = publications()
        source = published("2" * 40, "data-native/new/same.npz", "a" * 64, 99)
        merged = merge_manifest(previous(), source, result, metadata, package_id="aliases")
        self.assertEqual(len(merged["files"]), 3)
        self.assertEqual(merged["logical_file_aliases"][0]["repo_relative_path"], "data-native/new/same.npz")

    def test_same_hash_different_size_is_rejected(self):
        source, result, metadata = publications()
        source = published("2" * 40, "data-native/new/same.npz", "a" * 64, 100)
        with self.assertRaises(ValueError): merge_manifest(previous(), source, result, metadata, package_id="collision")

    def test_unverified_or_non_fixed_publication_cannot_enter(self):
        for change in ["status", "commit", "readback"]:
            source, result, metadata = publications()
            if change == "status": source["status"] = "running"
            elif change == "commit": source["commit"] = "main"
            else: next(iter(source["files"].values()))["readback_passed"] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                merge_manifest(previous(), source, result, metadata, package_id="reject")

    def test_missing_original_receipt_requires_metadata_publication(self):
        with self.assertRaises(ValueError):
            merge_manifest(previous(), *publications(), package_id="missing-original",
                           original_receipt_hashes={"result-receipt": "e" * 64})

    def test_metadata_receipt_does_not_require_its_own_later_publication(self):
        merged = merge_manifest(previous(), *publications(), package_id="finite-closure",
            original_receipt_hashes={"result-receipt": "d" * 64}, metadata_receipt_sha256="f" * 64)
        self.assertEqual(merged["incremental_transfer_packages"][0]["metadata_publication_receipt_SHA256"], "f" * 64)
        self.assertFalse(any(x["SHA256"] == "f" * 64 for x in merged["files"]))

    def test_unsafe_new_path_and_private_notes_are_rejected(self):
        source, result, metadata = publications()
        source["files"]["../escape.json"] = source["files"].pop("tools/new/source.py")
        with self.assertRaises(ValueError): merge_manifest(previous(), source, result, metadata, package_id="unsafe")
        old = previous(); old["private_note"] = "/dev/shm/private"
        with self.assertRaises(ValueError): merge_manifest(old, *publications(), package_id="private")

    def test_file_api_preserves_original_bytes_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / "previous.json"; old.write_text(json.dumps(previous()))
            old_bytes = old.read_bytes()
            source, result, metadata = publications()
            sp = root / "source.json"; sp.write_text(json.dumps(source))
            rp = root / "result.json"; rp.write_text(json.dumps(result))
            metadata["files"] = {
                "docs/new/source-receipt.json": {"SHA256": hashlib.sha256(sp.read_bytes()).hexdigest(), "bytes": sp.stat().st_size, "readback_passed": True},
                "docs/new/result-receipt.json": {"SHA256": hashlib.sha256(rp.read_bytes()).hexdigest(), "bytes": rp.stat().st_size, "readback_passed": True}}
            mp = root / "metadata.json"; mp.write_text(json.dumps(metadata))
            out = root / "new.json"
            proof = merge_files(old, sp, rp, mp, out, package_id="file-api")
            self.assertEqual(old.read_bytes(), old_bytes)
            self.assertEqual(proof["manifest_SHA256"], hashlib.sha256(out.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError): merge_files(old, sp, rp, mp, out, package_id="file-api")
            with self.assertRaises(ValueError): merge_files(old, sp, rp, mp, old, package_id="overwrite-old")


if __name__ == "__main__":
    unittest.main()
