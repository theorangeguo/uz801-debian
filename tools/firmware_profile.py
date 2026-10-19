#!/usr/bin/env python3
"""Validate pinned modem executable firmware and apply it to a staged rootfs."""

import argparse
import hashlib
import json
import re
from pathlib import Path


def validate_profile(profile_path, source):
    profile = json.loads(Path(profile_path).read_text(encoding='utf-8'))
    if profile.get('schema_version') != 1 or not re.fullmatch(r'[a-z0-9._-]+', profile.get('id', '')):
        raise ValueError('Invalid firmware profile')
    files = profile.get('files', {})
    if not {'modem.mdt', 'mba.mbn'}.issubset(files) or not 3 <= len(files) <= 32:
        raise ValueError('Incomplete modem firmware set')
    total = 0
    for name, expected in files.items():
        if not re.fullmatch(r'modem\.(?:mdt|b\d\d)|mba\.mbn', name):
            raise ValueError('Profile may contain only modem executable firmware')
        payload = (Path(source) / name).read_bytes()
        if len(payload) != expected['bytes'] or hashlib.sha256(payload).hexdigest() != expected['sha256']:
            raise ValueError('Firmware size/hash mismatch: ' + name)
        total += len(payload)
    if total > 64 * 1024 * 1024:
        raise ValueError('Firmware set exceeds size limit')
    return profile


def apply_profile(profile, source, root):
    root = Path(root).resolve()
    if root == Path(root.anchor):
        raise ValueError('Use a staged rootfs directory, not the host root')
    destination = root / 'usr/lib/firmware'
    destination.mkdir(parents=True, exist_ok=True)
    if root not in destination.resolve().parents:
        raise ValueError('Firmware destination escapes the staged rootfs')
    for name in profile['files']:
        temporary = destination / ('.' + name + '.uz801-new')
        temporary.write_bytes((Path(source) / name).read_bytes())
        temporary.chmod(0o644)
        temporary.replace(destination / name)
    metadata = root / 'usr/share/uz801/modem-firmware-profile.json'
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    profile = validate_profile(args.profile, args.source)
    if args.root is not None:
        apply_profile(profile, args.source, args.root)
    print('Firmware profile verified' + (' and installed: ' if args.root else ': ') + profile['id'])


if __name__ == '__main__':
    main()
