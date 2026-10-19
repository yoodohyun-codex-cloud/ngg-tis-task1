"""Verify distribution bytes only; never import research code or run simulations."""
import hashlib
import json
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    index = json.loads((root / 'PACKAGE_INDEX.json').read_text(encoding='utf-8'))
    for item in index['files']:
        path = root / item['path']
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Missing or symlinked package file: ' + item['path'])
        content = path.read_bytes()
        if len(content) != item['bytes'] or hashlib.sha256(content).hexdigest() != item['sha256']:
            raise SystemExit('Package byte mismatch: ' + item['path'])
    actual = {
        str(p.relative_to(root)) for p in root.rglob('*')
        if p.is_file() and '.git' not in p.relative_to(root).parts
        and p.name != 'PACKAGE_INDEX.json'
    }
    expected = {item['path'] for item in index['files']}
    if actual != expected:
        raise SystemExit('Unexpected/missing package paths: ' + repr(sorted(actual ^ expected)))
    print(json.dumps({
        'status': 'passed', 'indexed_files': len(expected),
        'indexed_bytes': sum(item['bytes'] for item in index['files']),
        'scope': 'Distribution file sizes and SHA256 only; no numerical restoration or simulation.'
    }, indent=2))


if __name__ == '__main__':
    main()
