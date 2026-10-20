#!/usr/bin/env python3
"""Package one board's built images with a manifest and unambiguous product name."""
import argparse
import hashlib
import json
import lzma
import os
import re
import struct
import subprocess
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board', required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--build-id', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9._-]+', args.build_id):
        parser.error('Invalid build id')
    record = json.loads((args.build_dir / 'resolved-inputs.json').read_text())
    if record['board'] != args.board:
        raise ValueError('Build/selected board mismatch')
    boot = REPO / 'kernel' / record['kernel']['boot']['filename']
    rootfs = args.build_dir / 'rootfs.img.xz'
    aboot = REPO / 'aboot/aboot.mbn'
    if digest(boot) != record['kernel']['boot']['sha256'] or boot.read_bytes()[:8] != b'ANDROID!':
        raise ValueError('Boot image hash/format mismatch')
    with lzma.open(rootfs, 'rb') as source:
        header = source.read(28)
    magic, major, minor, header_size, chunk_size, block_size, blocks, chunks, crc = struct.unpack('<I4H4I', header)
    if magic != 0xed26ff3a or major != 1 or blocks * block_size != record['rootfs_expanded_bytes']:
        raise ValueError('Compressed rootfs is not the expected expanded Android sparse image')
    commit = os.environ.get('GITHUB_SHA') or subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, check=True, text=True).stdout.strip()
    payloads = {'boot.img': boot, 'rootfs.img.xz': rootfs, 'aboot.mbn': aboot}
    manifest = {'schema_version': 1, 'product': record['product'], 'board': args.board,
                'distribution': record['distribution'], 'architecture': 'arm64', 'source_commit': commit,
                'firmware_profile': record['firmware_profile'], 'kernel_release': record['kernel_release'],
                'dependency_release': record['dependency_release'], 'build_id': args.build_id,
                'hardware_acceptance': 'pending for this newly built complete image',
                'preserve_gpt_and_per_device_nv': True, 'default_data_roaming': False,
                'flashing_transport': 'Python EDL USB BULK only',
                'aboot_policy': 'Included for review; replace only when compatibility review requires it',
                'files': {name: {'sha256': digest(path), 'bytes': path.stat().st_size} for name, path in payloads.items()},
                'rootfs': {'container': 'xz-compressed Android sparse image', 'expanded_ext4_bytes': record['rootfs_expanded_bytes'],
                           'root_partition_guid_expected': 'a7ab80e8-e9d1-e8cd-f157-93f69b1d141e'}}
    checksums = ''.join(item['sha256'] + '  ' + name + '\n' for name, item in manifest['files'].items())
    prefix = record['product'] + '-bookworm-arm64-' + args.build_id
    args.output_dir.mkdir(parents=True, exist_ok=True)
    archive = args.output_dir / (prefix + '.zip')
    if archive.exists():
        raise ValueError('Refusing to overwrite an existing image bundle')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as output:
        for name, path in payloads.items():
            output.write(path, name)
        output.writestr('image-manifest.json', json.dumps(manifest, indent=2) + '\n')
        output.writestr('SHA256SUMS', checksums)
    (args.output_dir / (prefix + '.manifest.json')).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (args.output_dir / (prefix + '.sha256')).write_text(digest(archive) + '  ' + archive.name + '\n', encoding='ascii')
    print('Board image bundle: ' + archive.name)


if __name__ == '__main__':
    main()
