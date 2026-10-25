"""Prepare a LOCAL r3 publication plan for original bounded metadata only.

This module does not run the publisher, perform network I/O, change locks or
launch workers. A plan contains local paths and MUST NOT itself be published.
Original metadata file contents remain unchanged; the merged public manifest
contains only immutable public identities and safe relative object names.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from incremental_transfer import HEX40, REPOSITORY, read_json_metadata, receipt_entries
from frozen_manifest_validation import safe_path

BRANCH = "codex/task1-cloud-restart-20261020"


def metadata_publication_plan(*, source_receipt_path, result_receipt_path,
                              owner_receipt_path, repo_prefix, expected_parent,
                              required_result_receipt, package_id,
                              preregistration_path=None, extra_metadata=None):
    if not HEX40.fullmatch(expected_parent):
        raise ValueError("A fixed publication parent is required")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", package_id):
        raise ValueError("Safe logical package ID required")
    safe_path(repo_prefix)
    if not repo_prefix.startswith(("data-native/", "data-manufactured/", "docs/", "tools/")):
        raise ValueError("Approved research repository prefix required")
    source, _, _ = read_json_metadata(source_receipt_path)
    result, _, _ = read_json_metadata(result_receipt_path)
    receipt_entries(source); receipt_entries(result)
    owner, _, _ = read_json_metadata(owner_receipt_path)
    for key, expected in [("source_commit", source["commit"]), ("result_commit", result["commit"])]:
        if key in owner and owner[key] != expected:
            raise ValueError("Owner receipt points to a different publication")
    originals = {"source-publication-receipt.json": source_receipt_path,
                 "result-publication-receipt.json": result_receipt_path,
                 "owner-receipt.json": owner_receipt_path}
    if preregistration_path is not None:
        read_json_metadata(preregistration_path)
        originals["preregistration.json"] = preregistration_path
    for name, path in (extra_metadata or {}).items():
        safe_path(name)
        if name in originals or Path(name).suffix.lower() not in (".json", ".md", ".txt", ".log"):
            raise ValueError("Unique bounded original metadata name required")
        originals[name] = path
    files = {}
    for name, original in originals.items():
        path = Path(original)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000:
            raise ValueError("Bounded regular metadata input required; arrays are forbidden")
        raw = path.read_bytes()
        files[repo_prefix.rstrip("/") + "/" + name] = {
            "local_path": str(path.resolve()), "bytes": len(raw),
            "SHA256": hashlib.sha256(raw).hexdigest()}
    return {"schema": "task1-supported-Git-transport-plan-v1",
            "repository": REPOSITORY, "branch": BRANCH,
            "expected_parent": expected_parent, "new_PDE_required": False,
            "message": "Preserve original metadata for incremental transfer " + package_id,
            "required_result_receipt": str(Path(required_result_receipt).resolve()),
            "files": files}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ["source-receipt", "result-receipt", "owner-receipt", "repo-prefix", "expected-parent", "required-result-receipt", "package-id", "output"]:
        ap.add_argument("--" + key, required=True)
    ap.add_argument("--preregistration")
    args = ap.parse_args()
    plan = metadata_publication_plan(source_receipt_path=args.source_receipt,
        result_receipt_path=args.result_receipt, owner_receipt_path=args.owner_receipt,
        repo_prefix=args.repo_prefix, expected_parent=args.expected_parent,
        required_result_receipt=args.required_result_receipt, package_id=args.package_id,
        preregistration_path=args.preregistration)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, ensure_ascii=False, indent=2); stream.write("\n")
    print("Local metadata plan created; publisher was not executed.")
