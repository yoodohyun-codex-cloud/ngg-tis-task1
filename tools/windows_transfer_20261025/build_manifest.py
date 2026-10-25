#!/usr/bin/env python3
"""Build a fixed-commit transfer inventory from metadata; never open arrays.

All input paths are supplied by the caller and are excluded from the output.
Publication receipts must contain per-file readback_passed=true. Additional
preregistered dependencies are declarations until the owner verifies them.
This command does not publish, download, extract, delete, or run research code.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
EXTENSIONS = {"", ".json", ".py", ".java", ".class", ".md", ".txt", ".log", ".csv", ".csv.gz", ".bin", ".bin.gz", ".npz", ".npy", ".f64le", ".tar.gz", ".properties", ".ps1", ".xlsx", ".html", ".png", ".svg", ".zip", ".artifact"}


def read_metadata(path):
    path = Path(path)
    if path.stat().st_size > 8_000_000:
        raise ValueError("Metadata input exceeds the bounded JSON size")
    return json.loads(path.read_text(encoding="utf-8"))


def safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Unsafe relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("", ".", "..") for x in value.split("/")):
        raise ValueError("Unsafe relative path segment")
    for x in p.parts:
        if x[-1:] in (" ", ".") or RESERVED.match(x) or re.search(r'[<>"|?*\x00-\x1f]', x):
            raise ValueError("Unsafe Windows path component")
    return value


def named_inputs(values):
    answer = []
    for value in values:
        label, sep, path = value.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
            raise ValueError("Use a safe logical label followed by =input-path")
        answer.append((label, Path(path)))
    return answer


def path_hashes(value):
    """Yield declared path->hash pairs, retaining paths only in process memory."""
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(key, str) and "/" in key and isinstance(val, str) and HEX64.fullmatch(val):
                yield key, val
            elif isinstance(val, (dict, list)):
                yield from path_hashes(val)
    elif isinstance(value, list):
        for val in value:
            yield from path_hashes(val)


def metadata_digest(path):
    path = Path(path)
    if path.stat().st_size > 8_000_000 or path.suffix.lower() != ".json":
        raise ValueError("Only bounded JSON metadata may be hashed here")
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def compact_destination(repo_path, sha):
    suffix = "".join(PurePosixPath(repo_path).suffixes)
    if suffix not in EXTENSIONS:
        suffix = ".artifact"
    return safe_relative("objects/" + sha + suffix)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--receipt", action="append", default=[], metavar="LABEL=JSON")
    ap.add_argument("--dependency-document", action="append", default=[], metavar="LABEL=JSON")
    ap.add_argument("--cache", action="append", default=[], metavar="LABEL=JSON")
    ap.add_argument("--archive-inventory", action="append", default=[], metavar="LABEL=JSON")
    ap.add_argument("--extra-metadata", action="append", default=[], metavar="JSON",
                    help="Owner-provided extra fixed file entries and verified_SHA256 list")
    ap.add_argument("--required-hash", action="append", default=[], metavar="LOGICAL_ID=SHA256",
                    help="Explicit provenance dependency whose original path is not stored")
    ap.add_argument("--derived-checksum", action="append", default=[], metavar="LOGICAL_ID=SHA256",
                    help="Derived serialization checksum, explicitly not an independent HTTP file identity")
    ap.add_argument("--tree", required=True, help="Previously fetched public Git tree JSON")
    ap.add_argument("--head", required=True)
    ap.add_argument("--repository", default="yoodohyun-codex-cloud/ngg-tis-task1")
    ap.add_argument("--repo-root", required=True, help="For mapping declared source dependencies; not emitted")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if not HEX40.fullmatch(args.head):
        raise ValueError("A full fixed commit is required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        raise ValueError("Unsafe repository")
    tree_doc = read_metadata(args.tree)
    if tree_doc.get("truncated"):
        raise ValueError("A complete public Git tree is required")
    tree = {x["path"]: x for x in tree_doc["tree"] if x["type"] == "blob"}
    repo_root = Path(args.repo_root).resolve()
    entries, aliases, proof_chains, gaps, documents = {}, [], [], [], []
    proof_verified = set()

    def add(commit, repo_path, size, sha, declared_only=False):
        if not HEX40.fullmatch(commit) or not HEX64.fullmatch(sha):
            raise ValueError("Invalid fixed commit or SHA256")
        repo_path = safe_relative(repo_path)
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("Invalid byte count")
        destination = compact_destination(repo_path, sha)
        entry = {"fixed_commit": commit, "repo_relative_path": repo_path,
                 "bytes": size, "SHA256": sha,
                 "safe_destination_relative_path": destination}
        old = entries.get(destination)
        if old and (old["SHA256"] != sha or old["bytes"] != size):
            raise ValueError("Conflicting compact destination")
        if old and old != entry:
            aliases.append(entry)
        else:
            entries[destination] = entry
        if declared_only:
            gaps.append({"logical_id": "remote-readback:" + repo_path,
                         "status": "public_path_present_expected_SHA256_declared_but_owner_readback_required",
                         "SHA256": sha, "bytes": size})
        return destination

    for label, path in named_inputs(args.receipt):
        receipt = read_metadata(path)
        if receipt.get("status") != "published_readback_verified":
            raise ValueError("Publication receipt is not verified: " + label)
        commit = receipt["commit"]
        paths = []
        for repo_path, info in receipt["files"].items():
            if info.get("readback_passed") is not True:
                raise ValueError("Missing per-file readback proof: " + label)
            paths.append(add(commit, repo_path, info["bytes"], info["SHA256"]))
            proof_verified.add(info["SHA256"])
        digest, size = metadata_digest(path)
        proof_chains.append({"logical_id": label, "fixed_commit": commit,
                             "status": receipt["status"],
                             "expected_parent": receipt.get("expected_parent"),
                             "receipt_SHA256": digest, "receipt_bytes": size,
                             "transfer_destinations": sorted(set(paths))})
        documents.append(("publication-proof-" + label, path, receipt))

    owner_verified = set()
    for path in args.extra_metadata:
        extra = read_metadata(path)
        verified = set(extra.get("verified_SHA256", []))
        if any(not HEX64.fullmatch(sha) for sha in verified):
            raise ValueError("Invalid owner verified hash")
        owner_verified.update(verified)
        for item in extra.get("files", []):
            expected = compact_destination(item["repo_relative_path"], item["SHA256"])
            if item.get("safe_destination_relative_path", expected) != expected:
                raise ValueError("Extra entry must use the same safe content-addressed convention")
            add(item["fixed_commit"], item["repo_relative_path"], item["bytes"], item["SHA256"], item["SHA256"] not in verified)

    covered = {x["SHA256"] for x in entries.values()}
    covered.update(x["SHA256"] for x in aliases)
    hash_requirements = []
    for value in args.required_hash:
        label, sep, sha = value.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z0-9_.-]+", label) or not HEX64.fullmatch(sha):
            raise ValueError("Invalid logical provenance hash requirement")
        hash_requirements.append({"logical_id": label, "SHA256": sha,
                                  "status": "addressed_by_transfer_entry_subject_to_owner_readback_gate" if sha in covered else "required_origin_not_yet_addressed"})
        if sha not in covered:
            gaps.append({"logical_id": label, "SHA256": sha, "bytes": None,
                         "status": "required_origin_provenance_hash_not_yet_addressed_by_transfer_file"})
    declarations = []
    for label, path in named_inputs(args.dependency_document):
        doc = read_metadata(path)
        documents.append((label, path, doc))
        for original_path, sha in path_hashes(doc):
            logical = label + ":" + Path(original_path).name
            if sha in covered:
                declarations.append({"logical_id": logical, "SHA256": sha,
                                     "status": "covered_by_verified_public_file_or_alias"})
                continue
            local = Path(original_path)
            candidate = None
            try:
                candidate = local.resolve().relative_to(repo_root).as_posix()
            except ValueError:
                pass
            if candidate in tree:
                add(args.head, candidate, tree[candidate]["size"], sha, True)
                covered.add(sha)
                declarations.append({"logical_id": logical, "SHA256": sha,
                                     "status": "public_path_present_owner_readback_required"})
            else:
                size = local.stat().st_size if local.is_file() else None
                gaps.append({"logical_id": logical, "SHA256": sha, "bytes": size,
                             "status": "required_declared_dependency_not_yet_addressed_by_transfer_file",
                             "reason": "May be archive-contained, local metadata, or an unpublished cache; owner must reconcile explicitly."})

    # A successful publication receipt is a logical dependency too. Its own
    # result commit normally cannot contain that later-created proof document.
    for label, path, _ in documents:
        sha, size = metadata_digest(path)
        if sha not in covered:
            gaps.append({"logical_id": label, "SHA256": sha, "bytes": size,
                         "status": "metadata_exists_locally_but_its_own_durable_transfer_entry_is_missing"})

    caches, local_caches = [], []
    for label, path in named_inputs(args.cache):
        doc = read_metadata(path)
        chunks = []
        for item in doc["chunks"]:
            name = Path(item["path"]).name
            safe_relative(name)
            durable = item["SHA256"] in (proof_verified | owner_verified)
            chunks.append({"chunk_basename": name, "bytes": item["bytes"],
                           "SHA256": item["SHA256"], "row_start": item["row_start"],
                           "row_stop": item["row_stop"], "column_start": item["column_start"],
                           "column_stop": item["column_stop"],
                           "status": "verified_public_transfer_entry_available" if durable else "local_only_no_durable_transfer_entry"})
        caches.append({"logical_cache_id": label, "shape": doc["shape"],
                       "dtype": doc["dtype"], "order": doc["order"],
                       "chunks": chunks, "total_bytes": sum(x["bytes"] for x in chunks),
                       "local_readback_reported": doc.get("local_readback_passed") is True,
                       "remote_verified": all(x["status"] == "verified_public_transfer_entry_available" for x in chunks), "Windows_saved": False,
                       "required_action": "Preserve every original chunk and publish/transfer with fixed commit and verified hashes; do not substitute recomputation for user-requested raw preservation."})
        if not caches[-1]["remote_verified"]:
            local_caches.append(caches[-1])

    archives = []
    for label, path in named_inputs(args.archive_inventory):
        doc = read_metadata(path)
        digest, _ = metadata_digest(path)
        manifest_refs = [x for x in list(entries.values()) + aliases if x["SHA256"] == digest]
        archive_refs = []
        for ref in manifest_refs:
            archive_path = str(PurePosixPath(ref["repo_relative_path"]).parent / "evidence.tar.gz")
            archive_refs.extend(x for x in list(entries.values()) + aliases
                                if x["repo_relative_path"] == archive_path and x["fixed_commit"] == ref["fixed_commit"])
        if not archive_refs:
            raise ValueError("Archive inventory has no fixed downloadable archive entry")
        members = [{"member_relative_path": safe_relative(name), "bytes": info["bytes"],
                    "SHA256": info["SHA256"]} for name, info in doc["files"].items()]
        archives.append({"logical_id": label,
                         "fixed_archive_files": archive_refs,
                         "status": "archive-member metadata index; not separate HTTP files",
                         "members": members,
                         "auto_extraction": False,
                         "verification_note": "Transport hash validates archive bytes; this builder did not open archive payload or verify members anew."})

    # Resolve metadata gaps only with an actual transfer entry. A mere verified
    # hash assertion cannot conjure a downloadable object.
    gaps = [x for x in gaps if not (x.get("SHA256") in covered and
            (x["status"] != "public_path_present_expected_SHA256_declared_but_owner_readback_required" or x["SHA256"] in owner_verified))]
    derived = []
    for value in args.derived_checksum:
        label, sep, sha = value.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z0-9_.-]+", label) or not HEX64.fullmatch(sha):
            raise ValueError("Invalid derived provenance checksum")
        derived.append({"logical_id": label, "SHA256": sha,
                        "meaning": "Derived canonical serialization checksum; not the SHA256 of an independently downloadable file. Reconstruct from preserved original inputs using the frozen code."})
    result = {"schema": "task1-safe-windows-transfer-manifest-v1",
              "status": ("metadata_draft_owner_verification_and_missing_artifact_resolution_required"
                         if gaps or local_caches else
                         "public_objects_readback_verified_Windows_receipt_pending"),
              "created_UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "repository": args.repository, "public_reference_commit": args.head,
              "Windows_backup_complete": False, "OneDrive_sync_verified": False,
              "scope": "Completed U19, cached basis audit, layer-DtN CEM reference and coarse/fineXY benchmarks, including declared dependencies.",
              "files": sorted(entries.values(), key=lambda x: x["safe_destination_relative_path"]),
              "logical_file_aliases": aliases, "publication_proof_chains": proof_chains,
              "origin_provenance_hash_requirements": hash_requirements,
              "derived_provenance_checksums": derived,
              "declared_dependency_coverage": declarations,
              "archive_member_inventory": archives,
              "raw_eigen_cache_inventory": caches,
              "required_local_only_raw_arrays": local_caches,
              "durability_gaps": gaps,
              "integrity_is_not_scientific_validation": True,
              "receiving_requirements": ["Use a user-selected Windows destination; no private absolute destination is embedded.",
                  "Reject unsafe paths and reparse points, verify bytes andSHA256 before atomic placement, and never overwrite a different existing file.",
                  "Download archives without extraction or code execution.",
                  "Write an actual receive receipt only after local Windows verification; durable Git publication alone is not Windows backup."]}
    # Deliberately reject accidental leakage from input dictionaries/paths.
    from manifest_validation import validate_manifest
    validate_manifest(result, allow_draft=True)
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    for marker in [str(repo_root), "/dev/shm/", "/workspace/", "C:/Users/", "C:\\Users\\"]:
        if marker in encoded:
            raise ValueError("Internal/private path leaked into transfer metadata")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise FileExistsError("Refusing to replace an existing draft")
    out.write_text(encoded, encoding="utf-8")
    print(json.dumps({"files": len(result["files"]), "aliases": len(aliases),
                      "download_bytes": sum(x["bytes"] for x in result["files"]),
                      "local_only_cache_bytes": sum(x["total_bytes"] for x in local_caches),
                      "durability_gaps": len(gaps), "Windows_backup_complete": False}))


if __name__ == "__main__":
    main()
