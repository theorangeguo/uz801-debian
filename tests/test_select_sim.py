"""Exercise selector safety and modem re-enumeration using shell command doubles."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "rootfs/overlay/usr/local/sbin/uz801-select-sim").read_text(encoding="utf-8")
SHELL = os.environ.get("UZ801_TEST_SHELL") or shutil.which("sh")


@unittest.skipUnless(SHELL, "A POSIX shell is required")
class SelectSimTests(unittest.TestCase):
    def run_selector(self, slot="2", preferred="1", imei="123456789012345", expected="", switch_rc=0):
        prelude = '''
timeout() { shift; "$@"; }
sleep() { :; }
mmcli() {
    case "$*" in
        *--set-primary-sim-slot=*)
            printf 'switch\\n' >&2
            slot=$preferred
            return "$switch_rc" ;;
        *--output-keyvalue*)
            printf 'modem.generic.equipment-identifier : %s\\n' "$imei"
            printf 'modem.generic.primary-sim-slot : %s\\n' "$slot" ;;
    esac
}
'''
        # Command substitution runs mmcli in a subshell, so switching is reflected
        # by the shell function in the parent before the next snapshot.
        setup = ("slot=" + slot + "\npreferred=" + preferred + "\nimei=" + imei
                 + "\nswitch_rc=" + str(switch_rc) + "\n")
        env = dict(os.environ, UZ801_PRIMARY_SIM_SLOT=preferred, UZ801_EXPECTED_IMEI=expected)
        env.pop("UZ801_EXPECTED_CID", None)
        return subprocess.run([SHELL], input=setup + prelude + SCRIPT,
                              text=True, capture_output=True, env=env, timeout=60)

    def test_already_selected_does_not_switch(self):
        result = self.run_selector(slot="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("switch\n", result.stderr)

    def test_switches_once_and_verifies_new_slot(self):
        result = self.run_selector()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("switch\n"), 1)

    def test_failed_command_can_still_have_completed_async_switch(self):
        result = self.run_selector(switch_rc=1)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("switch\n"), 1)

    def test_wrong_identity_never_switches(self):
        result = self.run_selector(expected="999999999999999")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("switch\n", result.stderr)

    def test_missing_identity_never_switches(self):
        result = self.run_selector(imei="unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("switch\n", result.stderr)

    def test_disabled_does_not_contact_modem(self):
        result = self.run_selector(preferred="disabled")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout + result.stderr, "")

    def test_invalid_slot_refused(self):
        result = self.run_selector(preferred="invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("switch\n", result.stderr)


if __name__ == "__main__":
    unittest.main()
