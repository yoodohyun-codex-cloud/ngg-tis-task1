#!/usr/bin/env python3
"""Add verified publication metadata to an immutable previous transfer manifest.

Metadata-only: no network, arrays, numerical imports, publication, or worker.
The old manifest is read and never rewritten. The new manifest is compatible
with Receive-TIS-Transfer.ps1 and closes publication receipt dependencies at M.
"""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from frozen_manifest_validation import EXTENSIONS, safe_path, validate_manifest

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REPOSITORY = "yoodohyun-codex-cloud/ngg-tis-task1"


def read_json_metadata(path):
    path = Path(path)
    if path.suffix.lower() != ".json" or path.is_symlink() or not path.is_file():
        raise ValueError("Expected an original regular JSON metadata file")
    if path.stat().st_size > 8_000_000:
        raise ValueError("JSON metadata exceeds bounded size")
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest(), len(raw)


def receipt_entries(receipt):
    if receipt.get("status") != "published_readback_verified":
        raise ValueError("A successful standard publication receipt is required")
    commit = receipt.get("commit", "")
    if not HEX40.fullmatch(commit):
        raise ValueError("Full immutable publication commit required")
    if not isinstance(receipt.get("files"), dict) or not receipt["files"]:
        raise ValueError("Publication file inventory is empty")
    entries = []
    for path, item in receipt["files"].items():
        safe_path(path)
        sha = item.get("SHA256", "")
        size = item.get("bytes")
        if item.get("readback_passed") is not True or not HEX64.fullmatch(sha):
            raise ValueError("Every file needs successful SHA256 readback proof")
        if type(size) is not int or size < 0:
            raise ValueError("Invalid byte count")
        suffix = "".join(PurePosixPath(path).suffixes)
        if suffix not in EXTENSIONS:
            suffix = ".artifact"
        entries.append({"fixed_commit": commit, "repo_relative_path": path,
                        "bytes": size, "SHA256": sha,
                        "safe_destination_relative_path": "objects/" + sha + suffix})
    return entries


def merge_manifest(previous, source_receipt, result_receipt, metadata_receipt,
                   *, package_id, previous_manifest_sha256=None,
                   original_receipt_hashes=None, metadata_receipt_sha256=None):
    """Pure dict API. M must preserve original S/R receipts, not its own receipt.

    original_receipt_hashes maps logical labels to the original JSON file SHA256.
    When supplied, each must be addressed by a verified S/R/M publication file.
    Call merge_files for actual metadata paths and automatic original hashes.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", package_id):
        raise ValueError("Safe, unique logical package ID required")
    validate_manifest(previous)
    if previous_manifest_sha256 is not None and not HEX64.fullmatch(previous_manifest_sha256):
        raise ValueError("Invalid previous manifest SHA256")
    incoming = [receipt_entries(r) for r in (source_receipt, result_receipt, metadata_receipt)]
    receipt_hashes = dict(original_receipt_hashes or {})
    covered_hashes = {x["SHA256"] for items in incoming for x in items}
    for label, sha in receipt_hashes.items():
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", label) or not HEX64.fullmatch(sha):
            raise ValueError("Invalid original receipt identity")
        if sha not in covered_hashes:
            raise ValueError("Original source/result/owner metadata is not durably packaged: " + label)
    if metadata_receipt_sha256 is not None and not HEX64.fullmatch(metadata_receipt_sha256):
        raise ValueError("Invalid M receipt hash")

    merged = copy.deepcopy(previous)
    files = merged["files"]
    aliases = merged.setdefault("logical_file_aliases", [])
    destination_identities = {}
    exact = set()
    for item in files + aliases:
        key = item["safe_destination_relative_path"].casefold()
        identity = item["SHA256"], item["bytes"]
        if key in destination_identities and destination_identities[key] != identity:
            raise ValueError("Previous case-insensitive destination collision")
        destination_identities[key] = identity
        exact.add(tuple(item[k] for k in sorted(item)))
    old_file_count, old_alias_count = len(files), len(aliases)
    for items in incoming:
        for item in items:
            signature = tuple(item[k] for k in sorted(item))
            if signature in exact:
                continue
            key = item["safe_destination_relative_path"].casefold()
            identity = item["SHA256"], item["bytes"]
            if key in destination_identities:
                if destination_identities[key] != identity:
                    raise ValueError("New case-insensitive destination collision")
                aliases.append(item)
            else:
                files.append(item)
                destination_identities[key] = identity
            exact.add(signature)
    packages = merged.setdefault("incremental_transfer_packages", [])
    if any(p.get("package_id") == package_id for p in packages):
        raise ValueError("Package ID already exists; preserve old package")
    packages.append({
        "package_id": package_id,
        "source_commit": source_receipt["commit"],
        "result_commit": result_receipt["commit"],
        "metadata_commit": metadata_receipt["commit"],
        "previous_manifest_SHA256": previous_manifest_sha256,
        "original_receipt_SHA256": receipt_hashes,
        "metadata_publication_receipt_SHA256": metadata_receipt_sha256,
        "metadata_publication_status": metadata_receipt["status"],
        "new_objects": len(files) - old_file_count,
        "new_aliases": len(aliases) - old_alias_count,
        "receipt_closure": "Original S/R and explicitly required owner metadata are preserved as files in a verified publication. The successful M receipt is represented by its fixed commit, file entries and bounded proof identity here. M need not publish its own later receipt. This new manifest's later T publication receipt is retained separately or in a future package; it is not a prerequisite for its own checksum.",
        "Windows_saved_verified": False,
        "experimental_validation_inferred": False,
    })
    merged["status"] = "incremental_manifest_prepared_actual_Windows_receive_unverified"
    merged["created_UTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    merged["public_reference_commit"] = metadata_receipt["commit"]
    merged["Windows_backup_complete"] = False
    merged["OneDrive_sync_verified"] = False
    merged["integrity_is_not_scientific_validation"] = True
    validate_manifest(merged)
    return merged


def merge_files(previous_path, source_receipt_path, result_receipt_path,
                metadata_receipt_path, output_path, *, package_id,
                expected_previous_sha256=None, extra_original_metadata=None):
    """Read only bounded JSON and create a new file; never replace any old file."""
    previous, previous_sha, _ = read_json_metadata(previous_path)
    if expected_previous_sha256 is not None and previous_sha != expected_previous_sha256:
        raise ValueError("Previous manifest SHA256 mismatch")
    source, source_sha, _ = read_json_metadata(source_receipt_path)
    result, result_sha, _ = read_json_metadata(result_receipt_path)
    metadata, metadata_sha, _ = read_json_metadata(metadata_receipt_path)
    required = {"source-publication-receipt": source_sha,
                "result-publication-receipt": result_sha}
    for label, path in (extra_original_metadata or {}).items():
        _, sha, _ = read_json_metadata(path)
        required[label] = sha
    merged = merge_manifest(previous, source, result, metadata, package_id=package_id,
                            previous_manifest_sha256=previous_sha,
                            original_receipt_hashes=required,
                            metadata_receipt_sha256=metadata_sha)
    out = Path(output_path)
    if out.resolve() == Path(previous_path).resolve():
        raise ValueError("Original full manifest must remain untouched")
    out.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(merged, ensure_ascii=False, indent=2) + "\n").encode()
    with out.open("xb") as stream:
        stream.write(encoded)
    return {"schema": "task1-incremental-transfer-build-receipt-v1",
            "package_id": package_id, "previous_manifest_SHA256": previous_sha,
            "manifest_SHA256": hashlib.sha256(encoded).hexdigest(),
            "manifest_bytes": len(encoded), "files": len(merged["files"]),
            "aliases": len(merged["logical_file_aliases"]),
            "public_reference_commit": merged["public_reference_commit"],
            "Windows_backup_complete": False, "OneDrive_sync_verified": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--previous", required=True)
    ap.add_argument("--source-receipt", required=True)
    ap.add_argument("--result-receipt", required=True)
    ap.add_argument("--metadata-receipt", required=True)
    ap.add_argument("--package-id", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-previous-sha256")
    ap.add_argument("--original-metadata", action="append", default=[], metavar="LABEL=JSON")
    args = ap.parse_args()
    extras = {}
    for value in args.original_metadata:
        label, sep, path = value.partition("=")
        if not sep or label in extras:
            raise ValueError("Unique LABEL=JSON original metadata is required")
        extras[label] = path
    receipt = merge_files(args.previous, args.source_receipt, args.result_receipt,
                          args.metadata_receipt, args.output, package_id=args.package_id,
                          expected_previous_sha256=args.expected_previous_sha256,
                          extra_original_metadata=extras)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
