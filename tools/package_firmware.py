#!/usr/bin/env python3
"""Build deterministic board firmware debs from audited executable-only sources.

The vendor base is hash-pinned. Both boards replace the complete modem set, keeping
the same public vendor Wi-Fi/support baseline used during the live acceptance.
Never accepts a device NV dump or a whole-disk image as package input.
"""

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from firmware_profile import validate_profile

BASE_SHA256 = 'fdd545e9a5b1d84d471e89be81e85cafebc05a72f293122cb93a72c15a705820'
FORBIDDEN = {'modemst1', 'modemst2', 'modemst1.img', 'modemst2.img', 'fsg', 'fsc', 'fsg.mbn', 'fsc.mbn', 'persist', 'userdata'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ar_members(payload):
    if payload[:8] != b'!<arch>\n':
        raise ValueError('Not a deb/ar archive')
    offset, result = 8, {}
    while offset < len(payload):
        header = payload[offset:offset + 60]
        if len(header) != 60 or header[58:60] != b'`\n':
            raise ValueError('Invalid ar member')
        size = int(header[48:58])
        name = header[:16].decode().strip().rstrip('/')
        data = payload[offset + 60:offset + 60 + size]
        if len(data) != size or name in result:
            raise ValueError('Truncated or duplicate ar member')
        result[name] = data
        offset += 60 + size + size % 2
    return result


def safe_name(name):
    while name.startswith('./'):
        name = name[2:]
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or any(part in FORBIDDEN for part in path.parts):
        raise ValueError('Unsafe or per-device partition path: ' + name)
    return str(path)


def read_data(deb):
    members = ar_members(Path(deb).read_bytes())
    name = next(key for key in members if key.startswith('data.tar'))
    try:
        archive = tarfile.open(fileobj=io.BytesIO(members[name]), mode='r:*')
    except (tarfile.ReadError, tarfile.CompressionError):
        # Python <3.14 may lack zstd; dpkg is native to the Linux build runner.
        raw = subprocess.run(['dpkg-deb', '--fsys-tarfile', str(deb)], capture_output=True, check=True).stdout
        archive = tarfile.open(fileobj=io.BytesIO(raw), mode='r:')
    files = {}
    with archive:
        for member in archive.getmembers():
            name = safe_name(member.name)
            if member.isdir():
                continue
            if not member.isfile() or not name.startswith(('usr/lib/firmware/', 'usr/share/uz801/')):
                raise ValueError('Unexpected firmware package content: ' + name)
            if name in files:
                raise ValueError('Duplicate package file')
            files[name] = archive.extractfile(member).read()
    return files


def tar_gz(files):
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode='wb', filename='', mtime=0, compresslevel=9) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.GNU_FORMAT) as archive:
            directories = {str(parent) for name in files for parent in PurePosixPath(name).parents if str(parent) != '.'}
            for name in sorted(directories, key=lambda value: (value.count('/'), value)):
                info = tarfile.TarInfo('./' + name)
                info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, 0
                info.uid = info.gid = 0
                info.uname = info.gname = 'root'
                archive.addfile(info)
            for name, payload in sorted(files.items()):
                info = tarfile.TarInfo('./' + name)
                info.size, info.mode, info.mtime = len(payload), 0o644, 0
                info.uid = info.gid = 0
                info.uname = info.gname = 'root'
                archive.addfile(info, io.BytesIO(payload))
    return output.getvalue()


def deb_bytes(control, data):
    result = bytearray(b'!<arch>\n')
    for name, payload in [('debian-binary', b'2.0\n'), ('control.tar.gz', control), ('data.tar.gz', data)]:
        header = f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(payload):<10}`\n'.encode('ascii')
        if len(header) != 60:
            raise ValueError('Invalid ar header length')
        result.extend(header + payload + (b'\n' if len(payload) % 2 else b''))
    return bytes(result)


def build(base, board, profile_path, modem_dir, version):
    expected = {'uz801-v2.1': 'uz801-v2.1-b04', 'uz801-v3.0': 'uz801-v3.0-b08'}
    if board not in expected or not profile_path or not modem_dir:
        raise ValueError('Both boards require an explicit pinned complete modem profile/source')
    profile = validate_profile(profile_path, modem_dir)
    pinned = json.loads((Path(__file__).resolve().parents[1] / 'rootfs/firmware-profiles' / (expected[board] + '.json')).read_text())
    if profile != pinned:
        raise ValueError('Board profile must exactly match the repository pinned profile')
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+:~\-]*', version):
        raise ValueError('Invalid Debian package version')
    if digest(Path(base).read_bytes()) != BASE_SHA256:
        raise ValueError('Vendor base SHA256 mismatch')
    files = read_data(base)
    # A published vendor filename is not evidence of board compatibility. Replace
    # the entire modem set with the explicitly audited, board-pinned source.
    for name in list(files):
        if re.fullmatch(r'usr/lib/firmware/(modem\.(?:mdt|b\d\d)|mba\.mbn)', name):
            del files[name]
    for name in profile['files']:
        files['usr/lib/firmware/' + name] = (Path(modem_dir) / name).read_bytes()
    files['usr/share/uz801/modem-firmware-profile.json'] = (json.dumps(profile, indent=2) + '\n').encode()
    name = board + '-firmware'
    opposite = 'uz801-v2.1-firmware' if board == 'uz801-v3.0' else 'uz801-v3.0-firmware'
    control = (f'Package: {name}\nVersion: {version}\nArchitecture: all\n'
               'Maintainer: theorangeguo <theorangeguo@gmail.com>\nSection: non-free/kernel\nPriority: optional\n'
               f'Provides: openstick-firmware\nConflicts: openstick-firmware, {opposite}\nReplaces: openstick-firmware, {opposite}\n'
               f'Installed-Size: {(sum(map(len, files.values())) + 1023) // 1024}\n'
               f'Description: Pinned executable firmware for {board}\n'
               ' Includes public vendor support/WLAN defaults and the selected modem set.\n'
               ' Does not include per-device modemst, fsg, fsc or captured credentials.\n').encode()
    md5sums = ''.join(hashlib.md5(payload).hexdigest() + '  ' + path + '\n' for path, payload in sorted(files.items())).encode()
    payload = deb_bytes(tar_gz({'control': control, 'md5sums': md5sums}), tar_gz(files))
    manifest = {'schema_version': 1, 'board': board, 'package': name, 'version': version,
                'filename': name + '.deb', 'sha256': digest(payload), 'bytes': len(payload),
                'base_package_sha256': BASE_SHA256, 'modem_profile': profile['id'],
                'vendor_wlan_defaults': 'Unchanged from the pinned public vendor base; not taken from a private device capture',
                'per_device_nv_included': False,
                'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in sorted(files.items())}}
    return payload, manifest, profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-deb', type=Path, required=True)
    parser.add_argument('--board', choices=['uz801-v2.1', 'uz801-v3.0'], required=True)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--modem-dir', type=Path)
    parser.add_argument('--version', default='1.0.0+20261020')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not (args.profile and args.modem_dir):
        parser.error('Both boards require a validated complete modem source and profile')
    payload, manifest, profile = build(args.base_deb, args.board, args.profile, args.modem_dir, args.version)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / manifest['filename']
    if output.exists() and output.read_bytes() != payload:
        raise ValueError('Refusing to overwrite a different published package')
    output.write_bytes(payload)
    (args.output_dir / (manifest['package'] + '.manifest.json')).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (args.output_dir / (manifest['package'] + '.profile.json')).write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')
    print(manifest['filename'] + ' sha256:' + manifest['sha256'])


if __name__ == '__main__':
    main()
