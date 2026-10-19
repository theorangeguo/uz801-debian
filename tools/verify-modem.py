#!/usr/bin/env python3
"""Read-only post-deployment check; save results in the private workspace.

Does not send SMS, change radio state, register on a network or restore NV.
"""

import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--expected-cid", required=True)
    parser.add_argument("--expected-imei", required=True)
    parser.add_argument("--slot", choices=["1", "2"], default="1")
    parser.add_argument("--wait-seconds", type=int, default=90)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--firmware-profile", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite a prior verification report")
    if not 0 <= args.wait_seconds <= 300:
        parser.error("wait-seconds must be between 0 and 300")

    def shell(command):
        command += '; result=$?; printf "\\n__VERIFY_RC__=%s\\n" "$result"'
        result = subprocess.run([args.adb, "-s", args.serial, "shell", command],
                                capture_output=True, timeout=20)
        output = result.stdout.decode("utf-8", errors="replace").replace("\r", "")
        marker = re.search(r"\n__VERIFY_RC__=(\d+)\s*$", output)
        if result.returncode or not marker or marker.group(1) != "0":
            raise RuntimeError("Device command failed: " + command)
        return output[:marker.start()].strip()

    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "outbound_sms_tested": False, "internet_tested": False,
              "incoming_sms_tested_this_run": False, "checks": {}}
    deadline = time.monotonic() + args.wait_seconds
    while True:
        try:
            actual_cid = shell("cat /sys/block/mmcblk0/device/cid")
            if actual_cid != args.expected_cid:
                raise ValueError("Wrong physical device CID")
            boot_id = shell("cat /proc/sys/kernel/random/boot_id")
            properties = shell("mmcli -m any --output-keyvalue")
            fields = dict(re.findall(r"^([\w.-]+)\s*:\s*(.*?)\s*$", properties, re.M))
            checks = {
                "cid_matches": True,
                "imei_matches": fields.get("modem.generic.equipment-identifier") == args.expected_imei,
                "slot_matches": fields.get("modem.generic.primary-sim-slot") == args.slot,
                "registered": fields.get("modem.3gpp.registration-state") in ("home", "roaming"),
                "selector_succeeded": shell("systemctl show uz801-select-sim.service -p Result --value") == "success",
                "selector_active": shell("systemctl show uz801-select-sim.service -p ActiveState --value") == "active",
            }
            backend = shell("systemctl show rmtfs.service -p ActiveState -p ExecStart")
            checks["physical_nv_backend"] = ("ActiveState=active" in backend and " -P " in backend
                                               and "/run/nv-" not in backend)
            checks["no_temporary_nv_backend"] = not shell(
                "systemctl list-units --type=service --state=active --no-legend --plain 'rmtfs-nv-*'")
            report.update({"boot_id": boot_id, "checks": checks,
                           "modem_state": fields.get("modem.generic.state"),
                           "registration": fields.get("modem.3gpp.registration-state"),
                           "visited_operator": fields.get("modem.3gpp.operator-code"),
                           "data_bearers_present": fields.get("modem.generic.bearers") not in (None, '', '--')})
            if all(checks.values()) or time.monotonic() >= deadline:
                break
        except RuntimeError as error:
            report["last_read_error"] = str(error)
            if time.monotonic() >= deadline:
                break
        time.sleep(3)
    report["passed"] = bool(report["checks"]) and all(report["checks"].values())
    if report["passed"]:
        report.pop("last_read_error", None)
        report["sms_objects_present"] = len(re.findall(r"/SMS/\d+", shell("mmcli -m any --messaging-list-sms")))
        selector = shell("sha256sum /usr/local/sbin/uz801-select-sim").split()[0]
        source = Path(__file__).resolve().parents[1] / "rootfs/overlay/usr/local/sbin/uz801-select-sim"
        report["selector_matches_repository"] = selector == hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        report["passed"] = report["passed"] and report["selector_matches_repository"]
        report["cellular_rx_bytes"] = int(shell('cat /sys/class/net/wwan0/statistics/rx_bytes'))
        report["cellular_tx_bytes"] = int(shell('cat /sys/class/net/wwan0/statistics/tx_bytes'))
        if args.firmware_profile:
            profile = json.loads(args.firmware_profile.read_text(encoding='utf-8'))
            installed = json.loads(shell('cat /usr/share/uz801/modem-firmware-profile.json'))
            report['firmware_profile_matches'] = installed == profile
            file_checks = {}
            for name, info in profile['files'].items():
                if not re.fullmatch(r'modem\.(?:mdt|b\d\d)|mba\.mbn', name):
                    raise ValueError('Unexpected firmware filename')
                file_checks[name] = shell('sha256sum /usr/lib/firmware/' + name).split()[0] == info['sha256']
            report['firmware_files_match'] = all(file_checks.values())
            mounts = shell("findmnt -rn -o TARGET | grep -E '^/usr/lib/firmware/(modem\\.|mba\\.mbn)|^/run/fw-trial-' || true")
            report['no_firmware_trial_mounts'] = not mounts
            report['passed'] = (report['passed'] and report['firmware_profile_matches']
                                and report['firmware_files_match'] and report['no_firmware_trial_mounts'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
