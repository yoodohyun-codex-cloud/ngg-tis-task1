"""Archive and clean-restore completed NEW cloud runs without executing research.

The archive contains only regular files from one completed data-native/cloud-*
run. Byte identity and native array decoding are distinct checks. An externally
stored/downloaded archive is required before claiming an independent backup;
this local tool never changes run status, deletes evidence, or publishes assets.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from datetime import datetime, timezone
import fcntl
import gzip
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import stat
import struct
import tarfile


ROOT = Path(__file__).resolve().parents[1]
EMBEDDED_MANIFEST = 'ARCHIVE_MANIFEST.json'
CHUNK = 1024 * 1024
DISK_RESERVE = 2 * 1024**3


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(name):
    path = PurePosixPath(name)
    require(name and '\\' not in name and not path.is_absolute()
            and all(part not in ('', '.', '..') for part in name.split('/'))
            and str(path) == name, 'Unsafe archive member: ' + name)
    return name


@contextmanager
def execution_lock():
    # Uses the same two Linux lock namespaces as the finite compute controller.
    with (ROOT / '.task1-execution.lock').open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def inventory(run):
    run = Path(run).absolute()
    require(run == run.resolve() and run.parent == ROOT / 'data-native'
            and run.name.startswith('cloud-') and run.is_dir(),
            'Only a canonical new repository data-native/cloud-* directory is supported')
    require(read(run / 'controller.json')['status'] == 'complete'
            and read(run / 'summary.json')['status'] == 'complete',
            'Only completed runs can be frozen for archive; partial runs stay untouched')
    require(not (run / EMBEDDED_MANIFEST).exists(), 'Reserved archive manifest filename exists')
    files = []
    for path in sorted(run.rglob('*')):
        mode = path.lstat().st_mode
        require(stat.S_ISREG(mode) or stat.S_ISDIR(mode),
                'Symlink or special file is not allowed: ' + str(path))
        if stat.S_ISREG(mode):
            name = safe_name(path.relative_to(run).as_posix())
            files.append(dict(path=name, bytes=path.stat().st_size, sha256=digest(path)))
    pre = read(run / 'preregistration.json')
    return dict(schema='task1-new-native-archive-v1', run_id=run.name,
                created_utc=datetime.now(timezone.utc).isoformat(),
                source_commit=pre['source_commit'],
                preregistration_sha256=digest(run / 'preregistration.json'),
                terminal_summary_sha256=digest(run / 'summary.json'),
                scope='New cloud recomputation only; missing historical arrays are not recovered',
                frozen_references_note='Absolute paths inside original run metadata remain unchanged; restore is inspection only',
                raw_bytes=sum(row['bytes'] for row in files), files=files)


def pack(run, archive):
    run, archive = Path(run).absolute(), Path(archive).absolute()
    require(archive == archive.resolve() and run not in archive.parents,
            'Archive must be a canonical path outside its source run')
    manifest = inventory(run)
    require(shutil.disk_usage(archive.parent).free >= DISK_RESERVE + manifest['raw_bytes']
            + 4096*len(manifest['files']) + 16*CHUNK,
            'Archive copy plus unchanged 2GiB disk reserve unavailable')
    # Leave a partial file after an error instead of overwriting or deleting evidence.
    with archive.open('xb') as raw:
        with tarfile.open(fileobj=raw, mode='w', format=tarfile.PAX_FORMAT) as bundle:
            payload = encoded(manifest)
            info = tarfile.TarInfo(EMBEDDED_MANIFEST)
            info.size, info.mode = len(payload), 0o644
            bundle.addfile(info, io.BytesIO(payload))
            for row in manifest['files']:
                source = run / row['path']
                require(source.is_file() and not source.is_symlink()
                        and source.stat().st_size == row['bytes'] and digest(source) == row['sha256'],
                        'Source changed during archive: ' + row['path'])
                info = tarfile.TarInfo(safe_name(run.name + '/' + row['path']))
                info.size, info.mode = row['bytes'], 0o644
                with source.open('rb') as stream:
                    bundle.addfile(info, stream)
    # Independent archive read verifies bytes, rather than trusting successful writing.
    receipt = verify(archive, digest(archive))
    receipt.update(source_manifest_sha256=hashlib.sha256(encoded(manifest)).hexdigest(),
                   persistent_independent_backup_verified=False,
                   scientific_numerical_reproduction=False,
                   experimental_validation=False)
    for suffix, value in (('.manifest.json', manifest), ('.receipt.json', receipt)):
        with Path(str(archive) + suffix).open('xb') as stream:
            stream.write(encoded(value))
    return receipt


def inspect_members(bundle):
    members = bundle.getmembers()
    names = [safe_name(member.name) for member in members]
    require(len(names) == len(set(names)), 'Duplicate archive members')
    require(all(member.isfile() for member in members), 'Only regular archive files are allowed')
    require(names.count(EMBEDDED_MANIFEST) == 1, 'Missing unique archive manifest')
    manifest_member = bundle.getmember(EMBEDDED_MANIFEST)
    require(manifest_member.size <= 16 * CHUNK, 'Manifest exceeds bounded inventory size')
    manifest = json.load(bundle.extractfile(manifest_member))
    require(manifest['schema'] == 'task1-new-native-archive-v1', 'Unsupported manifest schema')
    run_id = safe_name(manifest['run_id'])
    require('/' not in run_id and run_id.startswith('cloud-'), 'Invalid new run identifier')
    expected = {}
    for row in manifest['files']:
        name = safe_name(run_id + '/' + safe_name(row['path']))
        require(name not in expected and isinstance(row['bytes'], int) and row['bytes'] >= 0,
                'Duplicate or invalid manifest file')
        require(len(row['sha256']) == 64 and all(c in '0123456789abcdef' for c in row['sha256']),
                'Invalid SHA256 in manifest')
        expected[name] = row
    require(set(names) == set(expected) | {EMBEDDED_MANIFEST}, 'Archive and manifest file set differs')
    require(sum(row['bytes'] for row in expected.values()) == manifest['raw_bytes'],
            'Manifest raw byte sum differs')
    for member in members:
        if member.name == EMBEDDED_MANIFEST:
            continue
        row = expected[member.name]
        require(member.size == row['bytes'], 'Archived size differs: ' + member.name)
        with bundle.extractfile(member) as stream:
            result = hashlib.sha256()
            for block in iter(lambda: stream.read(CHUNK), b''):
                result.update(block)
        require(result.hexdigest() == row['sha256'], 'Archived hash differs: ' + member.name)
    return manifest, members


def verify(archive, expected_sha256):
    archive = Path(archive)
    require(not archive.is_symlink() and digest(archive) == expected_sha256,
            'Archive SHA256 differs from independently pinned value')
    with tarfile.open(archive, 'r:') as bundle:
        manifest, _ = inspect_members(bundle)
    return dict(schema='task1-native-byte-archive-receipt-v1', archive=str(archive),
                archive_bytes=archive.stat().st_size, archive_sha256=expected_sha256,
                run_id=manifest['run_id'], files=len(manifest['files']),
                raw_bytes=manifest['raw_bytes'], byte_hash_verification='passed',
                native_array_decode_verification='not_run',
                independent_persistent_backup_verified=False,
                original_environment_retirement_allowed=False)


def binary_decode(path, expected_bytes):
    opener = gzip.open if path.suffix == '.gz' else open
    size = 0
    with opener(path, 'rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            require(len(block) % 8 == 0, 'Float64 alignment differs: ' + str(path))
            require(all(math.isfinite(value) for (value,) in struct.iter_unpack('<d', block)),
                    'Nonfinite native Float64: ' + str(path))
            size += len(block)
            require(size <= expected_bytes, 'Decoded array exceeds declared shape: ' + str(path))
    require(size == expected_bytes, 'Decoded array length differs: ' + str(path))
    return dict(path=str(path), decoded_bytes=size, dtype='little-endian complex128', finite=True)


def properties(path):
    values = {}
    for line in path.read_text().splitlines():
        if '=' not in line or line.lstrip().startswith(('#', '!')):
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        require(key not in values, 'Duplicate restored config property: ' + key)
        values[key] = value
    return values


def grouped_contract(run, folder, meta):
    """Physical-pad bookkeeping from honest grouped metadata and frozen inputs."""
    require(meta.get('exporter_kind') == 'grouped_native'
            and meta.get('exporter_class') == 'GroupedPadBasis'
            and meta.get('numerical_base_class') == 'SelectivityShapeBasis'
            and meta.get('frozen_four_pad_postprocessor_compatible') is False,
            'Grouped exporter identity must be explicit and honest')
    count, outputs = meta.get('n_pads'), meta.get('n_outputs')
    require(type(count) is int and count in (4, 8, 12, 16)
            and type(outputs) is int and outputs == meta.get('channels') == 2,
            'Grouped physical pad count requires exactly two independent outputs')
    nodes = meta.get('pad_node_ids')
    require(isinstance(nodes, list) and len(nodes) == count
            and all(type(node) is int and node in (-1, 0, 1) for node in nodes),
            'Explicit grouped physical-pad to electrical-node mapping required')
    require(nodes.count(0) == nodes.count(1) == count//4 and nodes.count(-1) == count//2,
            'Grouped node counts must preserve two signal groups and common return pads')
    require(meta.get('n_return_nodes') == 1 and meta.get('return_topology') == 'common_GND',
            'Grouped common return topology differs')
    matches = [case for case in read(run/'preregistration.json')['cases'] if case['id'] == folder.name]
    require(len(matches) == 1, 'Unique restored grouped registration case required')
    case = matches[0]
    require(case.get('exporter_class') == 'GroupedPadBasis' and case.get('n_pads') == count
            and case.get('n_outputs') == outputs and case.get('pad_node_ids') == nodes,
            'Restored grouped case and native topology differ')
    config_path = run/'configs'/(folder.name+'.properties')
    require(digest(config_path) == meta.get('config_sha256') == case.get('config_sha256'),
            'Restored grouped config hash differs from native metadata or registration')
    config = properties(config_path)
    require(config.get('channels') == config.get('n_outputs') == '2'
            and config.get('n_pads') == str(count) and config.get('n_return_nodes') == '1'
            and config.get('return_topology') == 'common_GND'
            and all(config.get(f'pad.node.{pad}') == str(nodes[pad]) for pad in range(count)),
            'Restored grouped config node mapping differs')
    expected = case.get('expected_pad_areas_m2')
    require(isinstance(expected, list) and len(expected) == count
            and all(math.isfinite(area) and area > 0 for area in expected),
            'Registered physical pad areas must be finite positive values')
    for pad, area in enumerate(expected):
        value = float(config[f'pad.{pad}.represented_area_m2'])
        require(math.isfinite(value) and value > 0 and abs(value/area-1) <= 1e-10,
                'Restored grouped registered/config pad areas differ')
    return count, nodes, expected


def decode_native(run):
    """Check native shapes/finite values only; no fields or metrics are recomputed."""
    records, bases = [], []
    for folder in sorted((run / 'bases').iterdir()):
        require(folder.is_dir() and (folder / 'BASIS_COMPLETE').is_file(), 'Incomplete restored basis')
        meta = read(folder / 'mesh-metadata.json')
        cells, channels = meta['cells'], meta['channels']
        require(type(cells) is int and type(channels) is int
                and 0 < cells <= 800000 and 0 < channels <= 2, 'Unsupported new native shape')
        grouped = (meta.get('exporter_kind') == 'grouped_native'
                   or meta.get('exporter_class') == 'GroupedPadBasis'
                   or any(key in meta for key in ('n_pads', 'n_outputs', 'pad_node_ids')))
        if grouped:
            physical_pads, pad_nodes, expected_areas = grouped_contract(run, folder, meta)
        else:
            physical_pads, pad_nodes, expected_areas = 2*channels, None, None
        require(meta['source_peak_V'] == .5 and meta['source_resistance_ohm'] == 50,
                'Unexpected source normalization')
        require(meta['phasor_convention'] == 'peak,+jomega_t', 'Unexpected phasor convention')
        require(meta['radius_mm'] == 25 and meta['total_depth_mm'] == 25.1
                and meta['tissue_boundaries_mm'] == [0, .1, 5.1, 10.1, 25.1],
                'Unexpected fixed phantom geometry or layer units')
        require(meta['frequencies_Hz'] == [3000, 3030, 9000, 9090],
                'Unexpected retained frequency order')
        with gzip.open(folder / 'grid.csv.gz', 'rt') as stream:
            rows = csv.DictReader(stream)
            count = 0
            for row in rows:
                values = [float(row[key]) for key in ('x_mm', 'y_mm', 'z_mm', 'volume_m3')]
                require(all(math.isfinite(v) for v in values) and values[-1] > 0,
                        'Invalid restored grid row')
                require(0 < values[2] < 25.1, 'Depth coordinate must be +z below z=0 surface')
                require(values[0]**2 + values[1]**2 < 25**2,
                        'Restored grid center lies outside D50 phantom')
                count += 1
            require(count == cells, 'Restored grid row count differs')
        reference_contacts, area_totals = None, None
        for frequency in meta['frequencies_Hz']:
            with (folder / f'contacts-{frequency}.csv').open() as stream:
                contacts = list(csv.DictReader(stream))
            require(contacts and all(math.isfinite(float(row['area_m2'])) and float(row['area_m2']) > 0
                                     for row in contacts), 'Invalid restored contact areas')
            require({int(row['pad']) for row in contacts} == set(range(physical_pads)),
                    'Contact pad ordering or physical pad count differs')
            if grouped:
                require(all(math.isfinite(float(row[key])) for row in contacts for key in ('x_mm', 'y_mm')),
                        'Grouped contact coordinates must be finite')
                signature = [(int(row['pad']), float(row['x_mm']), float(row['y_mm']), float(row['area_m2']))
                             for row in contacts]
                if reference_contacts is None:
                    reference_contacts = signature
                require(signature == reference_contacts, 'Grouped physical contact ordering differs across frequencies')
                area_totals = [math.fsum(float(row['area_m2']) for row in contacts if int(row['pad']) == pad)
                               for pad in range(physical_pads)]
                require(all(abs(area/expected-1) <= 1e-10 for area, expected in zip(area_totals, expected_areas)),
                        'Grouped restored physical contact area differs from registration')
            specs = {f'field-{frequency}.bin.gz': channels*cells*3*16,
                     f'potential-{frequency}.bin.gz': channels*cells*16,
                     f'density-{frequency}.bin': channels*len(contacts)*16,
                     f'source-{frequency}.bin': channels*channels*16,
                     f'loss-{frequency}.bin': 6*channels*channels*16}
            records.extend(binary_decode(folder / name, size) for name, size in specs.items())
        bases.append(dict(case_id=folder.name, exporter_class=meta.get('exporter_class'),
                          cells=cells, n_outputs=channels, n_pads=physical_pads,
                          pad_node_ids=pad_nodes, restored_pad_areas_m2=area_totals,
                          source_matrix_shape=[channels, channels], loss_matrix_shape=[6, channels, channels]))
    require(records, 'No native arrays decoded')
    return dict(status='passed', arrays=records, bases=bases,
                scope='Storage decode, dimensions and finite values only; no scientific metric or PDE reproduction')


def restore(archive, expected_sha256, destination):
    receipt = verify(archive, expected_sha256)
    destination = Path(destination).absolute()
    require(destination == destination.resolve() and not destination.exists(),
            'Clean restore destination must be canonical and absent')
    require(destination != ROOT / 'data-native' and ROOT / 'data-native' not in destination.parents,
            'Restore into inspection space, never the executable data-native namespace')
    with tarfile.open(archive, 'r:') as bundle:
        manifest, members = inspect_members(bundle)
        existing_parent = destination.parent
        while not existing_parent.exists():
            existing_parent = existing_parent.parent
        require(shutil.disk_usage(existing_parent).free >= DISK_RESERVE + manifest['raw_bytes'] + 16*CHUNK,
                'Restore copy plus unchanged 2GiB disk reserve unavailable')
        destination.mkdir(parents=True)
        for member in members:
            output = destination / member.name
            output.parent.mkdir(parents=True, exist_ok=True)
            # extractall is deliberately avoided: links and special files have no code path.
            with output.open('xb') as stream, bundle.extractfile(member) as source:
                for block in iter(lambda: source.read(CHUNK), b''):
                    stream.write(block)
            if member.name != EMBEDDED_MANIFEST:
                row = next(row for row in manifest['files']
                           if member.name == manifest['run_id'] + '/' + row['path'])
                require(output.stat().st_size == row['bytes'] and digest(output) == row['sha256'],
                        'Clean restore hash differs: ' + member.name)
    native = decode_native(destination / manifest['run_id'])
    receipt.update(clean_restore_destination=str(destination),
                   clean_restored_file_hash_verification='passed',
                   native_array_decode_verification=native,
                   scientific_numerical_reproduction=False, experimental_validation=False)
    with (destination / 'CLEAN_RESTORE_RECEIPT.json').open('xb') as stream:
        stream.write(encoded(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    packing = sub.add_parser('pack')
    packing.add_argument('--run', type=Path, required=True)
    packing.add_argument('--archive', type=Path, required=True)
    for name in ('verify', 'restore'):
        command = sub.add_parser(name)
        command.add_argument('--archive', type=Path, required=True)
        command.add_argument('--expected-sha256', required=True)
        if name == 'restore':
            command.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    with execution_lock():
        if args.command == 'pack':
            result = pack(args.run, args.archive)
        elif args.command == 'restore':
            result = restore(args.archive, args.expected_sha256, args.destination)
        else:
            result = verify(args.archive, args.expected_sha256)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
