import argparse
import hashlib
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from package_firmware import ar_members, deb_bytes, read_data, tar_gz, build
from build_inputs import fetch, load, prepare


class BoardDependencyTests(unittest.TestCase):
    def test_implicit_vendor_baseline_refused_for_both_boards(self):
        for board in ('uz801-v2.1', 'uz801-v3.0'):
            with self.subTest(board=board), self.assertRaisesRegex(ValueError, 'explicit pinned'):
                build('unused.deb', board, None, None, '1.0')

    def test_wrong_board_profile_refused_before_reading_vendor_base(self):
        with patch('package_firmware.validate_profile', return_value={'id': 'uz801-v2.1-b04'}):
            with self.assertRaisesRegex(ValueError, 'exactly match'):
                build('unused.deb', 'uz801-v3.0', 'profile.json', 'candidate', '1.0')

    def test_deterministic_tar_and_valid_deb_container(self):
        first = tar_gz({'usr/lib/firmware/b': b'b', 'usr/lib/firmware/a': b'a'})
        second = tar_gz({'usr/lib/firmware/a': b'a', 'usr/lib/firmware/b': b'b'})
        self.assertEqual(first, second)
        members = ar_members(deb_bytes(tar_gz({'control': b'Package: fixture\n'}), first))
        self.assertEqual(members['debian-binary'], b'2.0\n')
        with tarfile.open(fileobj=io.BytesIO(members['data.tar.gz'])) as archive:
            self.assertEqual(archive.getmember('./usr/lib/firmware').mode, 0o755)
            self.assertEqual(archive.extractfile('./usr/lib/firmware/a').read(), b'a')

    def test_nv_partition_payload_and_traversal_refused(self):
        for name in ('usr/lib/firmware/modemst1.img', '../../boot.img'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'bad.deb'
                path.write_bytes(deb_bytes(tar_gz({'control': b'Package: bad\n'}), tar_gz({name: b'private'})))
                with self.assertRaisesRegex(ValueError, 'Unsafe or per-device'):
                    read_data(path)

    def test_modified_cache_never_silently_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'asset'
            path.write_bytes(b'bad')
            item = {'filename': 'asset', 'bytes': 4, 'sha256': hashlib.sha256(b'good').hexdigest(), 'url': 'https://invalid.test/asset'}
            with patch('urllib.request.urlopen', side_effect=AssertionError('Must not fetch over a corrupt cache')):
                with self.assertRaisesRegex(ValueError, 'wrong size/hash'):
                    fetch(item, Path(directory))

    def test_other_board_deb_in_staging_refused_before_download(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'uz801-v3.0-firmware.deb').write_bytes(b'unexpected')
            args = argparse.Namespace(board='uz801-v2.1', package_dir=path, packages_only=True, output=None)
            with patch('urllib.request.urlopen', side_effect=AssertionError('Must not download a mixed set')):
                with self.assertRaisesRegex(ValueError, 'mixed/stale'):
                    prepare(args)

    def test_boards_resolve_distinct_locked_firmware(self):
        lock, v2 = load('uz801-v2.1')
        _, v3 = load('uz801-v3.0')
        self.assertNotEqual(v2['firmware']['sha256'], v3['firmware']['sha256'])
        self.assertEqual(v2['firmware']['filename'], 'uz801-v2.1-firmware.deb')
        self.assertEqual(v3['firmware']['filename'], 'uz801-v3.0-firmware.deb')
        self.assertEqual(lock['kernel_release'], 'v6.6.92-arm64')
        for asset in lock['kernel'].values():
            self.assertIn('v6.6.92-arm64', asset['url'])


if __name__ == '__main__':
    unittest.main()
