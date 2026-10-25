#!/usr/bin/env python3
"""Refresh presentation from an existing compact HTML; preserve packed bytes.

No research modules, locks, budgets, workers or original native files are read.
The output must be a new file. This does not rerun the compact quantizer.
"""
import argparse
import base64
import hashlib
from pathlib import Path
import re
from task1_top5_dashboard import SCRIPT, CSS


def refresh(original):
    active = re.search(r'<script>(.*?)</script>\s*</body>', original, re.S).group(1)
    codec = active[active.index('function f16('):active.index('function color(')]
    start, end = SCRIPT.index('function decode('), SCRIPT.index('function color(')
    script = SCRIPT[:start] + codec + SCRIPT[end:]
    bootstrap = active[:active.index("\n'use strict';")] + script + active[active.rindex('\n})().catch'):]
    result = original.replace(active, bootstrap)
    result = re.sub(r'<style>.*?</style>', lambda _: '<style>'+CSS+'</style>', result, flags=re.S)
    # Keep the warning shared with the ordinary renderer, without loading data.
    source = Path(__file__).with_name('task1_top5_dashboard.py').read_text()
    warning = re.search(r'<p class="display-warning">.*?</p>', source).group(0)
    marker = '<p id="mode-note" class="mode-note" aria-live="polite"></p>'
    result = result.replace(marker, marker+warning)
    digest = base64.b64encode(hashlib.sha256(bootstrap.encode()).digest()).decode()
    result = re.sub(r"script-src 'sha256-[^']+'", lambda _: "script-src 'sha256-"+digest+"'", result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with args.output.open('x') as stream:
        stream.write(refresh(args.source.read_text()))
