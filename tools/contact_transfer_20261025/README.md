This metadata-only helper appends completed finite batches to the existing safe Windows transfer manifest. It never runs research code, reads numerical arrays, calls a network service, publishes a commit, or changes execution policy. The previous full manifest remains untouched.

Use the existing owner-controlled publisher for three finite publications: S for source/preregistration, R for results/raw arrays, and M for original source/result/owner receipts and any additional original metadata. An already durable preregistration in S need not be duplicated in M. `metadata_plan.py` can prepare a local r3 plan for a future M publication; the plan contains local paths and must not be published. The original metadata contents are preserved byte for byte. A prepared plan does not start the publisher.

After M succeeds, use:

```text
python incremental_transfer.py --previous OLD.json --source-receipt SOURCE-RECEIPT.json --result-receipt RESULT-RECEIPT.json --metadata-receipt METADATA-RECEIPT.json --package-id unique-finite-batch --output NEW.json --expected-previous-sha256 EXPECTED_OLD_SHA256 --original-metadata owner=OWNER-RECEIPT.json
```

The new manifest includes every file in the verified S, R and M receipts. Existing identical objects become relative-path aliases. Conflicting content identities, unsafe paths, branch names, unverified receipts, unresolved old required dependencies, missing original receipt packaging and replacement of an existing output are rejected. All sizes remain integers without a 32-bit truncation. Download destinations remain full-SHA256 object names with whitelisted extensions and are compatible with the existing Windows receiver.

The original S/R receipts must be addressed by a verified S/R/M file entry. Caller-declared original owner metadata must be addressed too. The successful M receipt is represented by a bounded inline proof identity and its verified fixed-commit files; M does not need to publish its own later receipt. The resulting manifest's T publication receipt is observed afterward and retained separately or in a future package. It is never a prerequisite for its own checksum. This terminates receipt closure without discarding the original receipts.

`merge_files(...)` is the path API; `merge_manifest(...)` is the pure dictionary API. `test_incremental_transfer.py` defines metadata-only contracts for additive preservation, aliases, large byte counts, path and identity rejection, finite receipt closure and original-file preservation. Test source preparation is not a test execution result.

Every generated manifest keeps `Windows_backup_complete:false` and `OneDrive_sync_verified:false`. Scientific validation, candidate adoption and safety are not inferred from file integrity. Actual Windows receipt requires executing the existing verified receiver on the user's machine and checking its local receive receipt; a GitHub publication or successful manifest merge does not prove Windows storage.
