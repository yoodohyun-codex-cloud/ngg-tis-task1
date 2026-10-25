"""Metadata security/identity contracts; no research input or numerical worker."""
import copy
import unittest
from manifest_validation import validate_manifest


def minimal():
    sha = "a" * 64
    return {"schema": "task1-safe-windows-transfer-manifest-v1",
            "repository": "yoodohyun-codex-cloud/ngg-tis-task1",
            "public_reference_commit": "b" * 40, "Windows_backup_complete": False,
            "files": [{"fixed_commit": "c" * 40, "repo_relative_path": "data/raw.bin",
                       "bytes": 12, "SHA256": sha,
                       "safe_destination_relative_path": "objects/" + sha + ".bin"}],
            "durability_gaps": [], "required_local_only_raw_arrays": []}


class ManifestContracts(unittest.TestCase):
    def test_valid_fixed_object(self):
        self.assertTrue(validate_manifest(minimal())["all_required_dependencies_addressed"])

    def test_rejects_branch_and_short_commit(self):
        for value in ["main", "a31cabc8", "https://example.test/x"]:
            d = minimal(); d["files"][0]["fixed_commit"] = value
            with self.assertRaises(ValueError): validate_manifest(d)

    def test_rejects_traversal_ads_reserved_and_case_unsafe_segments(self):
        for value in ["../x", "/x", "x/../y", "x\\y", "x:y", "x//y", "x/CON.txt", "x/LPT1", "x/trailing.", "x/trailing ", "x/a?b"]:
            d = minimal(); d["files"][0]["repo_relative_path"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): validate_manifest(d)

    def test_rejects_same_destination_different_size(self):
        d = minimal(); another = copy.deepcopy(d["files"][0]); another["bytes"] += 1
        d["files"].append(another)
        with self.assertRaises(ValueError): validate_manifest(d)

    def test_accepts_identical_alias_identity(self):
        d = minimal(); another = copy.deepcopy(d["files"][0]); another["repo_relative_path"] = "source/identical.bin"
        d["logical_file_aliases"] = [another]
        self.assertEqual(validate_manifest(d)["unique_destinations"], 1)

    def test_refuses_false_windows_completion(self):
        d = minimal(); d["Windows_backup_complete"] = True
        with self.assertRaises(ValueError): validate_manifest(d)

    def test_unpublished_raw_cache_blocks_complete_status(self):
        d = minimal(); d["required_local_only_raw_arrays"] = [{"logical_cache_id": "Q100"}]
        with self.assertRaises(ValueError): validate_manifest(d)
        self.assertFalse(validate_manifest(d, allow_draft=True)["all_required_dependencies_addressed"])

    def test_absolute_internal_path_cannot_hide_in_notes(self):
        for value in ["/dev/shm/private-artifact", r"D:\Users\name\private-artifact", "c:/Users/name/private-artifact"]:
            d = minimal(); d["note"] = value
            with self.subTest(value=value), self.assertRaises(ValueError): validate_manifest(d)

    def test_unknown_per_file_field_is_rejected(self):
        d = minimal(); d["files"][0]["download_url"] = "https://other.test/x"
        with self.assertRaises(ValueError): validate_manifest(d)

    def test_non_whitelisted_extension_is_rejected(self):
        d = minimal(); d["files"][0]["safe_destination_relative_path"] = "objects/" + "a" * 64 + ".exe"
        with self.assertRaises(ValueError): validate_manifest(d)


if __name__ == "__main__":
    unittest.main()
