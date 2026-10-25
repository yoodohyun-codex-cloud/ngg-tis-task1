"""Pure metadata checks for the fixed-commit transfer contract."""
import json
from pathlib import PurePosixPath
import re

REPOSITORY = "yoodohyun-codex-cloud/ngg-tis-task1"
FIELDS = {"fixed_commit", "repo_relative_path", "bytes", "SHA256", "safe_destination_relative_path"}
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)
EXTENSIONS = {"", ".json", ".py", ".java", ".class", ".md", ".txt", ".log", ".csv", ".csv.gz", ".bin", ".bin.gz", ".npz", ".npy", ".f64le", ".tar.gz", ".properties", ".ps1", ".xlsx", ".html", ".png", ".svg", ".zip", ".artifact"}


def safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("Unsafe relative path")
    if PurePosixPath(value).is_absolute():
        raise ValueError("Absolute path is forbidden")
    for part in value.split("/"):
        if part in ("", ".", "..") or part[-1:] in (" ", ".") or RESERVED.match(part):
            raise ValueError("Unsafe path segment")
        if re.search(r'[<>"|?*\x00-\x1f]', part):
            raise ValueError("Forbidden Windows path character")
    return value


def validate_manifest(doc, allow_draft=False):
    if doc.get("schema") != "task1-safe-windows-transfer-manifest-v1":
        raise ValueError("Unknown manifest schema")
    if doc.get("repository") != REPOSITORY:
        raise ValueError("Unexpected repository")
    if not re.fullmatch(r"[0-9a-f]{40}", doc.get("public_reference_commit", "")):
        raise ValueError("A fixed reference commit is required")
    if doc.get("Windows_backup_complete") is not False:
        raise ValueError("A cloud manifest cannot attest actual Windows receipt")
    if not allow_draft and (doc.get("durability_gaps") or doc.get("required_local_only_raw_arrays")):
        raise ValueError("Required logical dependencies remain unresolved")
    destinations = {}
    files = doc.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("No downloadable file inventory")
    for item in files + doc.get("logical_file_aliases", []):
        if set(item) != FIELDS:
            raise ValueError("File entry fields do not match contract")
        if not re.fullmatch(r"[0-9a-f]{40}", item["fixed_commit"]):
            raise ValueError("Branch names or abbreviated commits are forbidden")
        if not re.fullmatch(r"[0-9a-f]{64}", item["SHA256"]):
            raise ValueError("Invalid SHA256")
        if not isinstance(item["bytes"], int) or isinstance(item["bytes"], bool) or item["bytes"] < 0:
            raise ValueError("Invalid byte count")
        safe_path(item["repo_relative_path"])
        safe_path(item["safe_destination_relative_path"])
        destination = item["safe_destination_relative_path"]
        dest = destination.casefold()
        prefix = "objects/" + item["SHA256"]
        if not destination.startswith(prefix) or destination[len(prefix):] not in EXTENSIONS:
            raise ValueError("Destination must be full-SHA256 addressed")
        identity = (item["SHA256"], item["bytes"])
        if dest in destinations and destinations[dest] != identity:
            raise ValueError("Conflicting case-insensitive destination")
        destinations[dest] = identity
    def check_strings(value):
        if isinstance(value, str):
            if "/dev/shm/" in value or "/workspace/" in value or re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", value):
                raise ValueError("Internal/private path in public transfer metadata")
        elif isinstance(value, dict):
            for key, val in value.items():
                check_strings(key); check_strings(val)
        elif isinstance(value, list):
            for val in value:
                check_strings(val)
    check_strings(doc)
    return {"files": len(files), "unique_destinations": len(destinations),
            "all_required_dependencies_addressed": not doc.get("durability_gaps") and not doc.get("required_local_only_raw_arrays")}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--allow-draft", action="store_true")
    args = ap.parse_args()
    with open(args.manifest, encoding="utf-8") as f:
        print(json.dumps(validate_manifest(json.load(f), args.allow_draft)))
