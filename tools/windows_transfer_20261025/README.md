This package prepares a fixed-commit Windows transfer inventory. It does not attest that Windows storage or OneDrive synchronization has occurred.

The manifest uses five fields per downloadable file: `fixed_commit`, `repo_relative_path`, `bytes`, `SHA256`, and `safe_destination_relative_path`. Downloads are stored under short content-addressed `objects/` names. `logical_file_aliases` preserves the original repository names and revisions, including identical files shared by several runs. Original archives are retained without automatic extraction. Their member inventory is separate from the HTTP file inventory.

`build_manifest.py` reads publication receipts, preregistration metadata, a complete public Git tree and original eigen-cache manifests. It never opens numerical arrays. `--extra-metadata` accepts owner-verified additional fixed files, including later publication receipts and the 31 original Q chunks. Unaddressed dependencies and local-only original arrays remain explicit blockers to a complete transfer. A source or result publication receipt is itself a dependency; a later successful commit cannot retroactively erase a failed intermediate publication receipt.

The owner must independently verify any file listed only from a preregistered expected hash, publish missing proof files and raw chunks, and rebuild the manifest. `manifest_validation.py MANIFEST` rejects unresolved required dependencies; `--allow-draft` is only for reviewing an incomplete draft. The metadata contracts in `test_transfer_manifest.py` cover path traversal, alternate streams, reserved Windows names, non-fixed commits, identity collisions, internal-path leakage, false Windows completion and unpublished raw arrays. These tests do not validate scientific results.

On the actual Windows machine, use an operator-selected destination and the published manifest SHA256:

```powershell
.\Receive-TIS-Transfer.ps1 -Manifest .\transfer-manifest.json -ExpectedManifestSHA256 '<published 64-character SHA256>' -Destination '<operator-selected destination>'
```

The receiver uses only the fixed public repository and raw GitHub host. It validates all path metadata before downloading, refuses existing reparse points, does not follow HTTP redirects, preserves existing mismatching files and failed partial downloads, and verifies the byte count and SHA256 before moving a new file into place. It makes no installation, execution-policy, trust-store or security-setting change. It never extracts an archive or runs downloaded code. The destination is supplied locally and is omitted from the receipt and normal output.

A OneDrive folder may contain reparse points. If that check refuses the chosen destination, the receiver reports failure; this package has not tested that Windows path. A missing partial file is recorded as null rather than claimed as preserved evidence.

An actual receive receipt states whether every listed object passed local verification and whether required dependencies were addressed. It does not validate the science or verify OneDrive synchronization. Preserve both successful and failed receive receipts and partial-download evidence. The PowerShell receiver must be verified on Windows; a source review or Linux metadata test is not a Windows execution result.
