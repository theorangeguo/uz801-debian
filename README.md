# uz801-debian

Debian 12 (Bookworm) arm64 image sources for the tested UZ801 v2.1 and v3.0 profiles. Common startup code is shared; each build installs exactly one board firmware package. Per-device identity, modemst/fsg/fsc NV, credentials and recovery logs never belong in these packages or images.

## Board dependencies

| Board | Locked firmware package | Modem profile | Image product |
| --- | --- | --- | --- |
| v2.1 tested variant | uz801-v2.1-firmware.deb | uz801-v2.1-b04 | uz801-v2.1-debian |
| v3.0 tested variant | uz801-v3.0-firmware.deb | uz801-v3.0-b08 | uz801-v3.0-debian |

Both packages are published in [board-dependencies-2026.10.22.1](https://github.com/theorangeguo/uz801-debian/releases/tag/board-dependencies-2026.10.22.1) together with the unchanged shared openstick-utils-all.deb, per-file manifests, profiles and SHA256SUMS. config/dependencies.lock.json pins exact URLs, sizes and SHA256 hashes. The legacy prebuilt-dependencies assets remain for old source revisions; release builds consume the versioned tag.

Both packages retain the same public vendor support/WLAN baseline and install a complete explicitly pinned modem set: B04 for v2.1, B08 for v3.0. The previous v3.0 B10 candidate failed modem enable with DeviceNotReady on the tested board. On 2026-10-22, replacing only its modem executable files with the identified preflash B08 set restored registration on the new Debian system with unchanged kernel and physical NV. File persistence and a user-performed power cycle passed on 2026-10-22: the modem registered from normal rootfs files, NV stayed unchanged, and cellular byte counters remained zero. New incoming SMS and a newly rebuilt B08 full image are not yet accepted. Never install both board packages. The public vendor WLAN defaults are separate from captured device NV.

## CI/CD

Build UZ801 Debian images is manually dispatched with board=uz801-v2.1, uz801-v3.0 or both. Default is both. It first verifies dependency hashes, Debian package identity and native dpkg installation in disposable roots, then builds on native ubuntu-24.04-arm runners.

The boot image, linux-image and headers are locked together to v6.6.92-arm64, the version used in the live maintenance tests. The build rejects mixed/stale deb directories, verifies every installed firmware file, checks ARM64 ADB/USB executables and required startup units, and refuses private device.conf in a public rootfs.

Each artifact has a distinct product name and contains a zip with boot.img, rootfs.img.xz, reviewed-optional aboot.mbn, image-manifest.json and SHA256SUMS. The manifest records the board, firmware profile, kernel/dependency versions, source commit, image format and expanded rootfs size. Extract each board bundle into its own directory.

publish=false uploads Actions artifacts only. Explicit publish=true creates a prerelease containing successful bundles. Build/source/package checks do not certify physical boot of a newly built full image; its manifest says hardware acceptance is pending. Do not overwrite GPT or per-device NV when validating an OS image.

Both board builds and publication passed in [run 39439771848](https://github.com/theorangeguo/uz801-debian/actions/runs/39439771848) from source commit `3ae9e9a734145bb3e03972cf4f283a2f09a86458`. The [two complete-image candidate bundles](https://github.com/theorangeguo/uz801-debian/releases/tag/debian-bookworm-arm64-39439771848-r1) are published as a prerelease. The v2.1 candidate passed system/first-boot/software-reboot checks. The v3.0 candidate passed system flash/readback/boot checks but its B10 modem was rejected with DeviceNotReady. Neither candidate has complete cold-boot/SMS acceptance.

The corrected [v3.0 B08 complete-image candidate](https://github.com/theorangeguo/uz801-debian/releases/tag/debian-bookworm-arm64-39780807753-r1) passed [native ARM64 build 39780807753](https://github.com/theorangeguo/uz801-debian/actions/runs/39780807753). Its manifest selects B08 and the 2026.10.22.1 dependency lock. The modem-only upgrade on the new Debian base passed user power-cycle and software reboot; flashing this newly built complete-image candidate remains untested.

## Local build

On an ARM64 Linux host with the build dependencies installed:

```bash
sudo bash rootfs/build.sh arm64 uz801-v2.1
# or: sudo bash rootfs/build.sh arm64 uz801-v3.0
```

The build downloads only the selected board deb and the shared utilities, checks the immutable input lock and uses debootstrap for Bookworm. Do not supply local firmware override environment variables to a release build; they are deliberately rejected. Offline profile validation and existing-device deployment remain available through the maintenance tools.

## Startup, safety and SOP

rootfs/overlay contains the shared SIM selector, unit and defaults. Preferred slot defaults to 1; board mapping must be validated on the physical variant. Private CID/IMEI guards stay in /etc/uz801/device.conf outside the public image. Defaults create no cellular data profile, enable no data roaming and send no SMS.

Use docs/INSTALLATION-SOP.md, then docs/SOP-UZ801-v2.1.md or docs/SOP-UZ801-v3.0.md. EDL USB BULK is the only partition-write transport. Fastboot may be used to enter EDL, not to write partitions. Match physical hardware, preserve rollback data, validate the complete board bundle and read back written data.

tools/deploy-modem.py and tools/deploy-firmware.py update existing systems from the same pinned sources with identity checks, verified backups and staged validation. tools/verify-modem.py verifies persistent files, identity, slot and registration. Existing-device reboot/power-cycle/incoming-SMS acceptance on the two tested boards is separate from new full-image acceptance. Other board variants, Internet access and outbound SMS are not certified by those tests.

Initial image account remains root / ChangeMe. Verify actual USB addressing and optional application configuration; do not copy historical assumptions.

## Checks and firmware packaging

Run python3 -m unittest discover -s tests -v and bash -n rootfs/build.sh rootfs/chroot.sh tools/ci_check_dependencies.sh. The source-check workflow does not publish images. Verify published board dependencies also checks the public packages through native dpkg.

tools/package_firmware.py builds deterministic debs from the SHA256-pinned public vendor base. Both boards require an explicit complete repository-pinned profile/source (v2.1 B04, v3.0 B08); silently retaining the vendor B10 modem baseline is rejected. It accepts firmware executables/support files only, creates distinct mutually exclusive package identities and emits per-file manifests. Firmware binaries remain Release assets, not Git objects. See docs/FIRMWARE-PROFILES.md.
