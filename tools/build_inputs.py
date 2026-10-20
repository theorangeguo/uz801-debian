#!/usr/bin/env python3
"""Resolve one board's exact dependency set; validate downloads and installed files."""
import argparse
import hashlib
import io
import json
import os
import tarfile
import time
import urllib.request
from pathlib import Path
from package_firmware import ar_members, read_data

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load(board):
    lock = json.loads((REPO / 'config/dependencies.lock.json').read_text())
    if lock.get('schema_version') != 1 or board not in lock['boards']:
        raise ValueError('Unknown board or lock schema')
    return lock, lock['boards'][board]


def fetch(item, directory):
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / item['filename']
    def valid():
        return target.is_file() and target.stat().st_size == item['bytes'] and sha(target) == item['sha256']
    if target.exists():
        if not valid():
            raise ValueError('Existing cached input has wrong size/hash: ' + str(target))
        return target
    temporary = directory / ('.' + item['filename'] + '.download')
    for attempt in range(3):
        try:
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'uz801-debian-locked-build'})
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as destination:
                while block := response.read(1024 * 1024):
                    destination.write(block)
            if temporary.stat().st_size != item['bytes'] or sha(temporary) != item['sha256']:
                raise ValueError('Downloaded input size/hash mismatch: ' + item['filename'])
            temporary.replace(target)
            return target
        except OSError:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def verify_package(board, path):
    lock, selected = load(board)
    expected = selected['firmware']
    if sha(path) != expected['sha256'] or Path(path).stat().st_size != expected['bytes']:
        raise ValueError('Wrong board package digest')
    members = ar_members(Path(path).read_bytes())
    control_name = next(name for name in members if name.startswith('control.tar'))
    with tarfile.open(fileobj=io.BytesIO(members[control_name]), mode='r:*') as archive:
        control = archive.extractfile(next(m for m in archive.getmembers() if m.name.endswith('/control') or m.name == 'control')).read().decode()
    fields = dict(line.split(': ', 1) for line in control.splitlines() if ': ' in line and not line.startswith(' '))
    if fields.get('Package') != expected['package'] or fields.get('Architecture') != 'all':
        raise ValueError('Unexpected Debian package identity/architecture')
    manifest = json.loads((REPO / expected['manifest']).read_text())
    files = read_data(path)
    if set(files) != set(manifest['files']):
        raise ValueError('Firmware package content set changed')
    for name, info in manifest['files'].items():
        if len(files[name]) != info['bytes'] or hashlib.sha256(files[name]).hexdigest() != info['sha256']:
            raise ValueError('Firmware payload mismatch: ' + name)
    profile = json.loads(files['usr/share/uz801/modem-firmware-profile.json'])
    if profile['id'] != selected['firmware_profile']:
        raise ValueError('Wrong embedded modem profile')
    return manifest


def prepare(args):
    lock, selected = load(args.board)
    expected = {selected['firmware']['filename'], lock['utils']['filename']}
    if not args.packages_only:
        expected |= {lock['kernel']['image']['filename'], lock['kernel']['headers']['filename']}
    if args.package_dir.exists():
        extra = {p.name for p in args.package_dir.glob('*.deb')} - expected
        if extra:
            raise ValueError('Refusing mixed/stale dependency directory: ' + ', '.join(sorted(extra)))
    firmware = fetch(selected['firmware'], args.package_dir)
    verify_package(args.board, firmware)
    fetch(lock['utils'], args.package_dir)
    if not args.packages_only:
        fetch(lock['kernel']['boot'], args.kernel_dir)
        fetch(lock['kernel']['image'], args.package_dir)
        fetch(lock['kernel']['headers'], args.package_dir)
    record = {'schema_version': 1, 'board': args.board, 'product': selected['product'], 'hostname': selected['hostname'],
              'architecture': lock['architecture'], 'distribution': lock['distribution'],
              'firmware_profile': selected['firmware_profile'], 'dependency_release': lock['dependency_release'],
              'firmware': selected['firmware'], 'utils': lock['utils'],
              'kernel_release': lock['kernel_release'], 'kernel': lock['kernel']}
    if args.output:
        args.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print('Verified locked inputs for ' + args.board + ' / ' + selected['firmware_profile'])


def verify_root(board, root):
    _, selected = load(board)
    manifest = json.loads((REPO / selected['firmware']['manifest']).read_text())
    for name, info in manifest['files'].items():
        path = root / name
        if not path.is_file() or path.stat().st_size != info['bytes'] or sha(path) != info['sha256']:
            raise ValueError('Installed firmware differs from selected package: ' + name)
    if (root / 'etc/uz801/device.conf').exists():
        raise ValueError('Private identity guards must not be embedded in a public image')
    for name in ('adbd', 'gc'):
        path = root / 'usr/bin' / name
        header = path.read_bytes()[:20]
        if header[:5] != b'\x7fELF\x02' or int.from_bytes(header[18:20], 'little') != 183 or not os.access(path, os.X_OK):
            raise ValueError('Required USB utility is not executable ARM64 ELF: ' + name)
    for path in ('usr/sbin/openstick-gc-manager.sh', 'usr/local/sbin/uz801-select-sim',
                 'usr/lib/systemd/system/openstick-gc-startup.service', 'usr/lib/systemd/system/uz801-select-sim.service'):
        if not (root / path).is_file():
            raise ValueError('Required startup component missing: ' + path)
    print('Installed firmware, ARM64 USB utilities and startup files verified: ' + board)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prepare_parser = sub.add_parser('prepare')
    prepare_parser.add_argument('--board', required=True)
    prepare_parser.add_argument('--package-dir', type=Path, required=True)
    prepare_parser.add_argument('--kernel-dir', type=Path, default=Path('kernel'))
    prepare_parser.add_argument('--output', type=Path)
    prepare_parser.add_argument('--packages-only', action='store_true')
    verify = sub.add_parser('verify-package')
    verify.add_argument('--board', required=True)
    verify.add_argument('--package', type=Path, required=True)
    root = sub.add_parser('verify-rootfs')
    root.add_argument('--board', required=True)
    root.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args)
    elif args.command == 'verify-package':
        verify_package(args.board, args.package)
        print('Package format/content/profile verified: ' + args.board)
    else:
        verify_root(args.board, args.root)


if __name__ == '__main__':
    main()
