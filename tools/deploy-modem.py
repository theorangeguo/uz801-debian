#!/usr/bin/env python3
"""Deploy the maintained modem overlay over ADB, with backups and identity checks.

This updates ordinary system files only. NV recovery is a separate EDL operation.
Requires Python 3.9+ on the host and root ADB access on the target.
"""

import argparse
import base64
import hashlib
import json
import posixpath
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "usr/local/sbin/uz801-select-sim": "0755",
    "usr/lib/systemd/system/uz801-select-sim.service": "0644",
    "etc/default/uz801-modem": "0644",
}
UNIT = "uz801-select-sim.service"
LEGACY = "uz801-physical-sim.service"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--expected-cid", required=True)
    parser.add_argument("--expected-imei", required=True)
    parser.add_argument("--slot", choices=["1", "2", "disabled"], default="1")
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--after-selector-unit", action="append", default=[],
                        help="Optional existing service/timer to start only after successful SIM selection")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{32}", args.expected_cid):
        parser.error("expected CID must be 32 hex characters")
    if not re.fullmatch(r"[0-9]{15}", args.expected_imei):
        parser.error("expected IMEI must be 15 digits")

    def shell(command, timeout=30):
        command += '; result=$?; printf "\\n__DEPLOY_RC__=%s\\n" "$result"'
        result = subprocess.run([args.adb, "-s", args.serial, "shell", command],
                                capture_output=True, timeout=timeout)
        output = result.stdout.decode("utf-8", errors="replace").replace("\r", "")
        marker = re.search(r"\n__DEPLOY_RC__=(\d+)\s*$", output)
        if result.returncode or not marker or marker.group(1) != "0":
            raise RuntimeError(output + result.stderr.decode("utf-8", errors="replace"))
        return output[:marker.start()].strip()

    def identity():
        if shell("cat /sys/block/mmcblk0/device/cid").lower() != args.expected_cid.lower():
            raise RuntimeError("CID mismatch; refusing deployment")
        if shell("id -u") != "0":
            raise RuntimeError("Root ADB is required")

    identity()
    boot_id = shell("cat /proc/sys/kernel/random/boot_id")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = args.backup_dir / ("modem-overlay-" + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    report = {"status": "staging", "boot_id": boot_id, "files": {}, "units": {}}
    for unit in (UNIT, LEGACY):
        report["units"][unit] = shell(
            "systemctl show " + unit + " -p LoadState -p ActiveState -p UnitFileState")
    payloads = {}
    for name, mode in FILES.items():
        payloads["/" + name] = ((ROOT / "rootfs/overlay" / name).read_bytes()
                                  .replace(b"\r\n", b"\n"), mode)
    payloads["/etc/default/uz801-modem"] = (
        ("UZ801_PRIMARY_SIM_SLOT=" + args.slot + "\n").encode(), "0644")
    private = ("UZ801_EXPECTED_CID=" + args.expected_cid.lower() + "\n"
               "UZ801_EXPECTED_IMEI=" + args.expected_imei + "\n").encode()
    # Preserve any unrelated private settings in an existing device.conf.
    old_private = shell("if test -f /etc/uz801/device.conf; then base64 /etc/uz801/device.conf; fi")
    if old_private:
        old = base64.b64decode(old_private).decode("utf-8")
        old = re.sub(r"(?m)^(?:export\s+)?UZ801_EXPECTED_(?:CID|IMEI)=.*\n?", "", old)
        private = old.rstrip().encode() + b"\n" + private
    payloads["/etc/uz801/device.conf"] = (private, "0600")
    for unit in args.after_selector_unit:
        if not re.fullmatch(r"[A-Za-z0-9_.@-]+\.(?:service|timer)", unit):
            parser.error("Invalid unit name")
        if "LoadState=loaded" not in shell("systemctl show " + unit + " -p LoadState"):
            raise RuntimeError("Requested dependent unit is not installed: " + unit)
        destination = "/etc/systemd/system/" + unit + ".d/50-uz801-select-sim.conf"
        payloads[destination] = (("[Unit]\nRequires=" + UNIT + "\nAfter=" + UNIT + "\n").encode(), "0644")
    staging = "/run/uz801-overlay-" + stamp
    shell("mkdir -m 700 " + staging)
    for index, (destination, (payload, mode)) in enumerate(payloads.items()):
        quoted = shlex.quote(destination)
        old = shell("if test -f " + quoted + "; then base64 " + quoted + "; fi")
        existed = shell("test -e " + quoted + " && echo yes || echo no") == "yes"
        if existed:
            local = backup / destination.lstrip("/")
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(base64.b64decode(old))
        target = staging + "/" + str(index)
        encoded = base64.b64encode(payload).decode()
        shell("printf %s " + shlex.quote(encoded) + " | base64 -d > " + target)
        digest = hashlib.sha256(payload).hexdigest()
        if shell("sha256sum " + target).split()[0] != digest:
            raise RuntimeError("Staged file hash mismatch")
        report["files"][destination] = {"existed": existed, "sha256": digest,
                                          "staged": target, "mode": mode}
    (backup / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shell("sh -n " + report["files"]["/usr/local/sbin/uz801-select-sim"]["staged"])
    identity()
    if shell("cat /proc/sys/kernel/random/boot_id") != boot_id:
        raise RuntimeError("Target rebooted during staging")
    # Retire the prior selector so two implementations cannot race each other.
    shell("if systemctl cat " + LEGACY + " >/dev/null 2>&1; then systemctl disable --now " + LEGACY + "; fi")
    shell("systemctl stop " + UNIT + " 2>/dev/null || true")
    for destination, info in report["files"].items():
        shell("install -d " + shlex.quote(posixpath.dirname(destination)))
        shell("install -m " + info["mode"] + " " + info["staged"] + " " + shlex.quote(destination))
        if shell("sha256sum " + shlex.quote(destination)).split()[0] != info["sha256"]:
            raise RuntimeError("Installed file hash mismatch")
    shell("systemd-analyze verify /usr/lib/systemd/system/" + UNIT)
    shell("systemctl daemon-reload && systemctl enable " + UNIT)
    shell("systemctl restart --no-block " + UNIT)
    report["status"] = "installed; service-start-requested; runtime-validation-pending"
    report["final_unit"] = shell("systemctl show " + UNIT + " -p ActiveState -p SubState -p UnitFileState")
    (backup / "manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Overlay installed and enabled. Runtime and reboot validation remain required.")
    print("Backup and deployment manifest: " + str(backup))


if __name__ == "__main__":
    main()
