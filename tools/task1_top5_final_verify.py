#!/usr/bin/env python3
"""Validate the existing compact GUI; write one new receipt, never a new GUI.

Only four existing HTML/JSON artifacts are read. Native fields and archives are
not decoded. New runtime observations do not retroactively validate old RSS.
"""
from __future__ import annotations

import argparse
import base64
import copy
from contextlib import ExitStack
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tempfile
import threading
import time

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '1'

import task1_bounded_continuation as bounded
import task1_resource_policy as policy

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024**3
MAX_RECEIPT = 64*1024
MAX_SECONDS = 120
MODES = ('raw_1Vpp', 'equal_total_source_output_RMS_sum', 'equal_total_power',
         'skin_contact_only', 'legacy_composite_full_skin')
METRICS = ('maxTIS', 'fixedTIS', 'RMS')
J_KEYS = ('surface_J_RMS_max_A_m2', 'surface_J_RMS_p95_A_m2')
PRIMARY = 'primary_r5_depth15_20'
INPUTS = ('docs/TASK1_TOP5_20261022_compact/index.html',
          'docs/TASK1_TOP5_20261022_compact/manifest.json',
          'docs/task1-top5-context-20261022/preregistration-v2.json',
          'docs/task1-top5-context-20261022/mobile-overflow-diagnostic.json')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def verify_payload(html, manifest, plan, diagnostic):
    """Inspect JSON proofs and renderer metadata, without decoding pixel arrays."""
    match = re.search(r'<script id="packed" type="application/octet-stream">(.*?)</script>', html, re.S)
    require(match is not None, 'One compact packed payload required')
    packed = base64.b64decode(match.group(1), validate=True)
    require(len(packed) <= 4*1024**2, 'Bounded compact payload required')
    # Decompress JSON text only, never the native or encoded pixel arrays.
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
        raw = stream.read(12*1024**2+1)
    require(len(raw) <= 12*1024**2, 'Bounded uncompressed display JSON required')
    payload = json.loads(raw)
    rendered = copy.deepcopy(payload['catalog'])
    require('_ui_pad_count_source' in rendered, 'Expected renderer pad-reference link required')
    rendered.pop('_ui_pad_count_source')
    rows = [rendered['canonical_baseline'], *rendered['selected_layouts']]
    require(len(rows) == 6, 'One baseline and five selected layouts required')
    ui_paths = ['/_ui_pad_count_source', '/canonical_baseline/_ui_links']
    ui_paths += ['/selected_layouts/'+str(i)+'/_ui_links' for i in range(5)]
    for row in rows:
        require('_ui_links' in row, 'Expected renderer row links required')
        row.pop('_ui_links')
    require(rendered == plan['catalog'], 'Scientific catalog differs beyond the seven renderer link keys')
    require(manifest['status'] == 'compact_dashboard_complete_unadopted' and
            diagnostic['source_HTML_SHA256'] == manifest['source_HTML']['SHA256'], 'Bound completed compact source required')
    require(manifest['candidate_adopted'] is False and manifest['full_convergence_validated'] is False and
            manifest['experimentally_validated'] is False, 'Display verification must not promote scientific validation')
    display = payload['display']
    cases = display['cases']
    require(len(cases) == 6 and len({c['id'] for c in cases}) == 6 and
            {c['id'] for c in cases} == {r['id'] for r in rows}, 'Exactly six source-bound display cases required')
    by_id = {r['id']: r for r in rows}
    contacts = scalars = 0
    for case in cases:
        row = by_id[case['id']]
        proofs = case['native_stats_proofs']
        require(set(proofs) == set(METRICS) and manifest['native_scalar_primary_proofs'][case['id']] == proofs,
                'All three original scalar proofs required')
        for metric, proof in proofs.items():
            require(proof['passed'] is True, 'Original scalar proof failed')
            saved = row['normalizations']['raw_1Vpp']['regions'][PRIMARY][metric]
            for key in ('mean', 'p10', 'max', 'volume_m3'):
                require(proof['saved'][key] == saved[key] and finite(proof['actual'][key]) and
                        math.isclose(proof['actual'][key], saved[key], rel_tol=1e-10,
                                     abs_tol=1e-25 if key == 'volume_m3' else 1e-12), 'Scalar proof differs from saved Float64 statistics')
            scalars += 1
        regression = case['contact_J_RMS']['regression']
        require(regression == manifest['contact_regression'][case['id']] and regression['passed'] is True and
                regression['relative_tolerance'] == 2e-7 and regression['absolute_tolerance_A_m2'] == 1e-14,
                'Original contact regression identity/tolerance required')
        expected_pairs = {(m, k) for m in ('raw', *MODES) for k in J_KEYS}
        require(len(regression['checks']) == 12 and
                {(c['mode'], c['metric']) for c in regression['checks']} == expected_pairs, 'Twelve unique raw/five-mode contact checks required')
        for check in regression['checks']:
            saved = row['electrical_metrics'] if check['mode'] == 'raw' else row['normalizations'][check['mode']]['normalized_burdens']
            expected = saved[check['metric']]
            require(check['passed'] is True and check['saved_A_m2'] == expected and finite(check['actual_A_m2']) and
                    abs(check['actual_A_m2']-expected) <= 1e-14+2e-7*abs(expected), 'Original contact proof differs from saved burdens')
            contacts += 1
    require(contacts == 72 and scalars == 18, 'All 72 contact and 18 scalar checks required')
    for mode in MODES:
        for metric in METRICS:
            for scope, region in (('global', 'total'), ('primary_ROI', PRIMARY)):
                expected = max(r['normalizations'][mode]['regions'][region][metric]['max'] for r in rows)
                bounds = display['color_limits'][mode][metric][scope]
                require(bounds[0] == 0 and math.isclose(bounds[1], expected, rel_tol=1e-12), 'Shared field ranges differ from saved statistics')
        expected = max(r['normalizations'][mode]['normalized_burdens'][J_KEYS[0]] for r in rows)
        bounds = display['contact_color_limits'][mode]
        require(bounds[0] == 0 and math.isclose(bounds[1], expected, rel_tol=1e-12), 'Shared contact ranges differ from saved statistics')
    return payload, dict(scientific_catalog_matches_plan=True, ignored_renderer_only_paths=ui_paths,
        contact_checks_passed=contacts, scalar_proofs_passed=scalars, saved_Float64_ranges_match=True,
        display_arrays_decoded=False, new_native_validation=False)


def aggregate_rss(owner_pid, owner_ticks, known):
    owned = bounded.owned_descendants(owner_pid, owner_ticks, known)
    live = {pid: ticks for pid, ticks in owned.items() if bounded.live(pid, ticks)}
    return sum(bounded.rss(pid) for pid in live), live


def browser_verify(html, payload, guard):
    from playwright.sync_api import sync_playwright
    errors, console_errors, requests = [], [], []
    require(Path('/dev/shm').is_dir() and shutil.disk_usage('/dev/shm').free >= 8*1024**2, 'At least8MiB existing tmpfs scratch required')
    with tempfile.TemporaryDirectory(prefix='task1-top5-final-', dir='/dev/shm') as scratch:
        scratch = Path(scratch)
        (scratch/'tmp').mkdir()
        env = dict(os.environ, TMPDIR=str(scratch/'tmp'), TMP=str(scratch/'tmp'), TEMP=str(scratch/'tmp'))
        with sync_playwright() as engine:
            context = engine.chromium.launch_persistent_context(str(scratch/'profile'), executable_path='/usr/bin/chromium',
                headless=True, viewport=dict(width=1540, height=1100), env=env,
                ignore_default_args=['--disable-dev-shm-usage'],
                args=['--disk-cache-size=0', '--media-cache-size=0', '--disable-gpu-shader-disk-cache'])
            try:
                page = context.pages[0]
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)
                page.on('request', lambda r: requests.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
                page.set_content(html, wait_until='load', timeout=30000)
                page.wait_for_function("document.querySelectorAll('.case-card').length===6", timeout=30000)
                guard()
                require(page.locator('.field-map').count() == page.locator('.contact-map').count() == 6, 'Six actual map panels required')
                count = 0
                page.select_option('#range', 'global')
                for mode in MODES:
                    for metric in METRICS:
                        for plane in ('xy', 'xz', 'yz'):
                            guard()
                            for selector, value in (('#mode', mode), ('#metric', metric), ('#plane', plane)):
                                page.select_option(selector, value)
                            for selector, expected in (('.field-map', payload['display']['color_limits'][mode][metric]['global'][1]),
                                                       ('.contact-map', payload['display']['contact_color_limits'][mode][1])):
                                ranges = page.locator(selector).evaluate_all('(a)=>a.map(c=>Number(c.dataset.vmax))')
                                require(len(ranges) == 6 and all(finite(v) and math.isclose(v, expected, rel_tol=1e-12) for v in ranges),
                                        'Six maps must use saved shared ranges')
                            count += 1
                page.set_viewport_size(dict(width=390, height=844))
                page.wait_for_timeout(100)
                width = page.evaluate('document.documentElement.scrollWidth')
                require(width <= 392 and not errors and not console_errors and not requests, 'Mobile overflow/JS/external request gate failed')
                owner, ticks = os.getpid(), bounded.ticks(os.getpid())
                _, live = aggregate_rss(owner, ticks, {})
                observed = 0
                for pid in live:
                    try:
                        argv = Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\0')
                        if argv and b'chromium' in Path(os.fsdecode(argv[0])).name.encode():
                            observed += 1
                            require(b'--disable-dev-shm-usage' not in argv, 'Chromium must retain tmpfs shared memory')
                    except FileNotFoundError:
                        pass
                require(observed > 0, 'Actual live Chromium argv proof required')
                guard()
                return dict(status='passed', actual_Chromium=True, combinations=count, cards=6, field_maps=6, contact_maps=6,
                    mobile_width=390, mobile_scroll_width=width, JS_errors=errors, console_errors=console_errors,
                    external_requests=requests, live_Chromium_argv_checked=observed, disable_dev_shm_usage_present=False,
                    browser_TMPDIR_and_profile='owned /dev/shm temporary directory; cleaned after close', screenshots_written=False)
            finally:
                context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.absolute()
    require(output == output.resolve() and output.is_relative_to(ROOT/'docs') and output.parent.is_dir() and
            not output.exists() and not output.is_symlink(), 'Unique canonical new docs receipt required')
    with ExitStack() as stack:
        stack.enter_context(bounded.dual_lock(ROOT/'.task1-loop.lock'))
        stack.enter_context(bounded.dual_lock(ROOT/'.task1-execution.lock'))
        ledger = policy.load_ledger(ROOT/'runtime/task1-budget.json')
        require(policy.remaining_seconds(ledger) >= MAX_SECONDS and shutil.disk_usage(ROOT).free >= 2*GIB+MAX_RECEIPT,
                'Existing120s budget and2GiB plus64KiB admission required')
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        start = time.monotonic()
        pid, ticks = os.getpid(), bounded.ticks(os.getpid())
        state = dict(pid=pid, proc_start_ticks=ticks, phase='pin_artifacts', peak_aggregate_RSS_bytes=0,
                     peak_live_processes=0, owned={pid: ticks})
        stop = threading.Event()
        prior = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGINT)}
        receipt = dict(schema='task1-top5-final-verification-v1', status='failed_preserved', started_utc=stamp(),
            new_PDE=0, native_arrays_decoded=False, GUI_or_originals_overwritten=False, old_runtime_aggregate_RSS_retroverified=False)
        error = None
        def guard():
            rss, owned = aggregate_rss(pid, ticks, state['owned'])
            state.update(owned=owned, peak_aggregate_RSS_bytes=max(state['peak_aggregate_RSS_bytes'], rss),
                         peak_live_processes=max(state['peak_live_processes'], len(owned)))
            require(time.monotonic()-start < MAX_SECONDS, 'Finite120s verification deadline')
            require(rss < 3*GIB and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 < 3*GIB, 'Aggregate3GiB RSS guard')
            require(shutil.disk_usage(ROOT).free >= 2*GIB+MAX_RECEIPT, 'Preserve2GiB plus reserved receipt bytes')
        def interrupt(signum, frame):
            raise TimeoutError(state.get('guard_failure', 'Controlled verification signal '+str(signum)))
        def monitor():
            while not stop.wait(1):
                try:
                    guard()
                except BaseException as exc:
                    state['guard_failure'] = type(exc).__name__+': '+str(exc)
                    os.kill(pid, signal.SIGTERM)
                    return
        for sig in prior:
            signal.signal(sig, interrupt)
        signal.setitimer(signal.ITIMER_REAL, MAX_SECONDS)
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            code = {}
            for name in ('tools/task1_top5_final_verify.py', 'tests/test_task1_top5_final_verify.py',
                         'tools/task1_bounded_continuation.py', 'tools/task1_resource_policy.py'):
                path = ROOT/name
                raw = path.read_bytes()
                require(raw == subprocess.check_output(['git', 'show', commit+':'+name], cwd=ROOT), 'Commit exact verifier dependencies first')
                code[str(path)] = digest(raw)
            raw_inputs = {}
            for name in INPUTS:
                guard()
                path = ROOT/name
                require(path == path.resolve() and path.is_file() and not path.is_symlink() and path.stat().st_size <= 4*1024**2,
                        'Canonical bounded existing display artifact required')
                raw_inputs[str(path)] = path.read_bytes()
            pins = {path: digest(raw) for path, raw in raw_inputs.items()}
            html = raw_inputs[str(ROOT/INPUTS[0])].decode()
            manifest, plan, diagnostic = (json.loads(raw_inputs[str(ROOT/name)]) for name in INPUTS[1:])
            require(pins[str(ROOT/INPUTS[0])] == manifest['artifacts']['index.html']['SHA256'] and
                    pins[str(ROOT/INPUTS[2])] == manifest['source_plan']['SHA256'], 'Existing release/plan SHA mismatch')
            payload, proof = verify_payload(html, manifest, plan, diagnostic)
            state['phase'] = 'actual_offline_browser_matrix'
            browser = browser_verify(html, payload, guard)
            state['phase'] = 'verify_sources_unchanged'
            for path, expected in {**pins, **code, **policy.policy_refs(ledger)}.items():
                guard()
                require(digest(Path(path).read_bytes()) == expected, 'Verification input changed: '+path)
            guard()
            receipt.update(status='existing_compact_GUI_verified_unadopted', source_commit=commit, implementation_sha256=code,
                input_sha256=pins, inputs_unchanged=True, quantitative_metadata=proof, browser_validation=browser,
                old_release_process_RSS_bytes=manifest['resources']['peak_process_RSS_bytes'],
                old_runtime_scope='Old receipt recorded self RSS only; this new run observes its own live descendants, not past RSS or scratch usage',
                display_error_scope='Saved bound is for RAW Float32-to-Float16 pixels: |error|<=3.1e-8+0.0005*|raw|. After amplitude A, |error|<=|A|*(3.1e-8+0.0005*|raw|); tables/proofs/ranges remain Float64. No new pixel/native decoding.',
                candidate_adopted=False, full_convergence_validated=False, experimentally_validated=False)
        except BaseException as exc:
            error = type(exc).__name__+': '+str(exc)
            receipt.update(status='failed_preserved', error=error, phase=state['phase'], resource_guard_failure=state.get('guard_failure'))
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            stop.set()
            thread.join(timeout=2)
            elapsed = time.monotonic()-start
            ledger['spent_seconds'] += elapsed
            ledger['runs'].append(dict(run_id=output.stem, stage='existing_top5_GUI_validation_only', status=receipt['status'],
                                      seconds=elapsed, error=error, finished_utc=stamp()))
            bounded.write(ROOT/'runtime/task1-budget.json', ledger)
            receipt.update(finished_utc=stamp(), resources=dict(wall_seconds=elapsed, max_seconds=MAX_SECONDS, CPU_count=1,
                peak_aggregate_RSS_bytes=state['peak_aggregate_RSS_bytes'], peak_live_processes=state['peak_live_processes'],
                RSS_limit_bytes=3*GIB, minimum_free_bytes=2*GIB, max_receipt_bytes=MAX_RECEIPT, live_monitor_seconds=1),
                remaining_approved_seconds=policy.remaining_seconds(ledger))
            data = json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False).encode()+b'\n'
            require(len(data) <= MAX_RECEIPT and shutil.disk_usage(ROOT).free >= 2*GIB+len(data), 'Preserve64KiB receipt cap and2GiB reserve')
            with output.open('xb') as stream:
                stream.write(data)
            for sig, handler in prior.items():
                signal.signal(sig, handler)
        print(json.dumps(dict(status=receipt['status'], output=str(output), seconds=elapsed)))


if __name__ == '__main__':
    main()
