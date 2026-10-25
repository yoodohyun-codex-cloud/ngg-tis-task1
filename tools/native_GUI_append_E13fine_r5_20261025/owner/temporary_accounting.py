"""Owned task-root logical bytes, with per-file disappearance handling."""
def counted_bytes(root):
    try:
        if root.is_file():return root.stat().st_size
    except FileNotFoundError:return 0
    total=0
    try:
        for path in root.rglob('*'):
            try:
                if path.is_file():total+=path.stat().st_size
            except FileNotFoundError:continue
    except FileNotFoundError:pass
    return total
