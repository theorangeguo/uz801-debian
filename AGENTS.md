# UZ801 Debian maintenance rules

## Sources and ownership

- Build sources are `rootfs/build.sh`, `rootfs/chroot.sh` and `.github/workflows/build.yml`.
- Maintain generic target files in `rootfs/overlay/`. The live deployment tool reads the same files; do not maintain a second device-only copy of generic behavior.
- Keep CID, IMEI, subscriptions, credentials, NV, full-disk images and host recovery logs in the private companion workspace. Never commit them or embed them in an image.
- `docs/CUSTOMIZATIONS.md` describes maintained behavior and its validation limits. Historical chat conclusions are not evidence of an installed component or successful test.

## Device and flashing rules

- Match the physical target with eMMC CID and verified IMEI. An ADB serial or flashed device-tree name does not prove identity or PCB revision.
- Flash only through Python edl over WinUSB/libusb USB BULK. No COM/QDLoader, QFIL, emmcdl, fastboot or ADB block writes. Fastboot may be used solely to enter EDL when explicitly requested; never use it to write partitions. Never change a driver without explicit authorization.
- Before any write, verify source provenance, partition geometry, rollback backups and EDL readback from the identified device. Read back complete written partitions and compare SHA256 afterward.
- NV recovery is separate from installing an OS. Restore only verified changed NV partitions; do not touch GPT, bootloaders, boot or rootfs as part of NV repair.
- Never restore NV automatically during build or boot. Similar hardware or matching directory names do not establish interchangeable NV.
- Preserve a working diagnostic session unless interruption is authorized. RAM-backed recovery disappears at reboot.

## Build and deployment rules

- Keep boot image, kernel modules and device tree compatible. `root=PARTUUID=` refers to the GPT partition GUID; the ext4 filesystem UUID is separate.
- Do not package an image without working USB Gadget and ADB startup. The current openstick-utils implementation provides `/usr/bin/adbd`, `/usr/bin/gc`, `/usr/sbin/openstick-gc-manager.sh`, and `openstick-gc-startup.service`. Recheck package contents when updating dependencies.
- Keep shell sources LF. Run shell syntax checks and selector tests before deployment.
- Use `tools/deploy-modem.py` for existing devices. It verifies CID, preserves backups, installs the same overlay sources and enables the selector. Record deployed hashes and settings privately.
- Never run two SIM selectors concurrently. The deployer disables the former `uz801-physical-sim.service` while retaining its files and backing up unit state.
- Optional application dependencies belong in explicitly requested deployment settings; do not assume SimAdmin is part of the base image.
- Distinguish source tests, live deployment, a successful image build, reboot verification, cold-boot verification, SMS reception and Internet connectivity. None implies all the others.
- The build workflow currently runs by manual or repository dispatch and publishes a release. Do not trigger a release accidentally while running checks.
