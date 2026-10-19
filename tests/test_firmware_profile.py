import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from firmware_profile import apply_profile, validate_profile


class FirmwareProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.profile = {'schema_version': 1, 'id': 'test-profile', 'files': {}}
        for name in ('modem.mdt', 'modem.b00', 'mba.mbn'):
            payload = ('fixture-' + name).encode()
            (self.source / name).write_bytes(payload)
            self.profile['files'][name] = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
        self.profile_path = self.root / 'profile.json'
        self.write_profile()

    def write_profile(self):
        self.profile_path.write_text(json.dumps(self.profile), encoding='utf-8')

    def test_complete_pinned_set_applies_to_staged_rootfs(self):
        profile = validate_profile(self.profile_path, self.source)
        staged = self.root / 'staged'
        apply_profile(profile, self.source, staged)
        self.assertEqual((staged / 'usr/lib/firmware/modem.mdt').read_bytes(), (self.source / 'modem.mdt').read_bytes())
        self.assertEqual(json.loads((staged / 'usr/share/uz801/modem-firmware-profile.json').read_text())['id'], 'test-profile')

    def test_corrupt_source_refused_before_deployment(self):
        (self.source / 'modem.b00').write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            validate_profile(self.profile_path, self.source)

    def test_nv_partition_and_path_escape_refused(self):
        for name in ('modemst1.img', '../../boot.img'):
            with self.subTest(name=name):
                self.profile['files'][name] = {'bytes': 1, 'sha256': '0' * 64}
                self.write_profile()
                with self.assertRaisesRegex(ValueError, 'only modem executable'):
                    validate_profile(self.profile_path, self.source)
                del self.profile['files'][name]

    def test_host_root_refused_before_any_filesystem_change(self):
        with patch('pathlib.Path.mkdir', side_effect=AssertionError('Host root must be rejected before filesystem access')):
            with self.assertRaisesRegex(ValueError, 'not the host root'):
                apply_profile(self.profile, self.source, Path(self.root.anchor))


if __name__ == '__main__':
    unittest.main()
