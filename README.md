# uz801-debian

Debian 12 (Bookworm) arm64 image sources and maintenance tools for the tested UZ801 v3.0 and v2.1 variants. This repository maintains common startup behavior and explicit firmware profiles; per-device identity, NV, backups and recovery logs stay in the private companion workspace.

## Verified scope and release status

Existing-device repairs on one user-confirmed v3.0 and one v2.1 board passed reboot, user power disconnect/reconnect and new incoming SMS checks. That does not certify every board revision, carrier, Internet connectivity or outbound SMS.

New complete images containing these changes have not yet been built and published for both boards. Do not describe older Release images as newly validated dual-board images.

| Board | Current maintained firmware input | Target dependency name | Target image product name |
| --- | --- | --- | --- |
| v3.0 | Existing packaged baseline, legacy asset firmware-uz801v3.deb | uz801-v3.0-firmware.deb | uz801-v3.0-debian |
| v2.1 tested variant | Pinned uz801-v2.1-b04 profile, binary files supplied explicitly | uz801-v2.1-firmware.deb | uz801-v2.1-debian |

The renamed dependency assets in the table are target names, not a claim that those assets have been published. The current prebuilt-dependencies release supplies the legacy v3 firmware asset and openstick-utils-all.deb. The utility package contains shared USB/ADB/expansion code and SIM/LED defaults that require board configuration review. Never install two competing board firmware packages together.

## Build

rootfs/build.sh uses debootstrap for Debian Bookworm, installs kernel/firmware/utility packages, applies rootfs/overlay and produces rootfs.img. The manually dispatched .github/workflows/build.yml builds the current packaged baseline and publishes its artifacts; it is not yet a completed two-board release matrix. Only arm64 is implemented.

The kernel assets are resolved from the Haris131 releases API; firmware and utilities come from this repository's dependency release. Those references are not immutable content locks. Check exact origin, hashes, package contents and boot/module/device-tree compatibility when updating them. Keep the dependency release while builds reference it.

For the optional v2.1 B04 set, set UZ801_FIRMWARE_PROFILE=uz801-v2.1-b04 and UZ801_MODEM_FIRMWARE_DIR to the complete local set. All lengths and hashes are checked before building and the files are applied after dependency packages. See docs/FIRMWARE-PROFILES.md. Default builds retain their packaged firmware.

## Startup and maintenance

The maintained SIM selector, systemd unit and default policy live in rootfs/overlay. Preferred slot defaults to 1 and can be set to 2 or disabled. Private CID/IMEI guards belong in /etc/uz801/device.conf, never in the public image.

tools/deploy-modem.py deploys the same sources to an existing device with backups and identity checks. tools/deploy-firmware.py persists a complete, pinned, successful RAM-tested firmware set. tools/verify-modem.py checks identity, slot, registration, persistent backend and source hashes. See docs/CUSTOMIZATIONS.md and docs/FIRMWARE-PROFILES.md.

Default data roaming and cellular autoconnect remain disabled. Diagnostics do not authorize Internet traffic or outbound SMS. Network registration and receiving SMS are separate acceptance checks.

## Installation SOP

Start with docs/INSTALLATION-SOP.md, then docs/SOP-UZ801-v3.0.md or docs/SOP-UZ801-v2.1.md. Actual identity and device-specific commands are in the private workspace's matched device SOP.

Partition writes use Python EDL over USB BULK only. Fastboot may be used to enter EDL, never to write partitions. Do not flash an unknown backup or whole disk by filename. Preserve GPT and per-device NV during normal OS installation; an NV-only repair must not rewrite the OS. A GPT PARTUUID is separate from an ext4 UUID.

Initial image account: root / ChangeMe. Actual USB addressing and optional applications depend on the installed package/configuration; verify them rather than copying historical assumptions.

## Checks

Run python3 -m unittest discover -s tests -v, bash -n rootfs/build.sh rootfs/chroot.sh, and sh -n rootfs/overlay/usr/local/sbin/uz801-select-sim. The separate modem-check workflow runs source checks without publishing an image. Source checks, a successful build and a cold-booted image are separate evidence.
