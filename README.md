# uz801v3-debian

Debian 12 (Bookworm) arm64 image sources for UZ801 v3 devices, using a community kernel and the necessary USB, storage and modem services. Validate the physical board before deployment; a flashed device-tree name alone is insufficient.

## Build and dependencies

`rootfs/build.sh` creates a Debian base with debootstrap, installs the kernel, firmware and OpenStick utility packages, applies `rootfs/overlay/`, and produces an Android sparse `rootfs.img`. `.github/workflows/build.yml` packages `aboot`, `boot.img` and `rootfs.img.xz` and publishes the release when dispatched.

The build currently resolves kernel assets from the Haris131 kernel releases API and downloads firmware/utilities from this repository's `prebuilt-dependencies` release. Those references are not immutable content locks; updating dependencies requires checking their origin, hashes, package contents and boot/module compatibility. Do not delete the dependency release while the build references it.

The configured account is `root` with initial password `ChangeMe`. USB addressing comes from the installed utility package and existing NetworkManager settings; verify it on the device.

## Maintained customization

The default preferred SIM slot is 1, configurable as 1, 2 or `disabled` in `/etc/default/uz801-modem`. Optional device identity guards belong in the private `/etc/uz801/device.conf`. The selector waits for ModemManager, requests one slot change and verifies the result. It does not rewrite NV or reset the modem.

See [customization and validation](docs/CUSTOMIZATIONS.md) for the source files, deployment instructions and known limits. Existing devices can receive these exact source files through `tools/deploy-modem.py`; rebuilding or flashing rootfs is not necessary for an ordinary configuration update.

## Flashing and recovery

Use Python edl over WinUSB/libusb USB BULK only. Verify the physical target, compatible loader, GPT, image format and complete rollback backups before writing. Host paths and per-device commands belong in the private companion workspace.

For an OS installation, validate the bootloader, boot image, kernel modules, rootfs and GPT root partition GUID together, then write only the partitions the installation actually requires. An ext4 UUID is not a GPT PARTUUID. A successful transfer does not prove successful boot.

NV partitions are per-device data. Never include them in the public image, restore another device's NV, or restore NV automatically during startup. A modem error alone is not sufficient reason to rewrite NV. An NV-only recovery must not rewrite the OS or GPT; verify complete partition readbacks after writing.

## Validation

Run `python3 -m unittest discover -s tests -v`, `bash -n rootfs/build.sh rootfs/chroot.sh`, and `sh -n rootfs/overlay/usr/local/sbin/uz801-select-sim`. The separate modem check workflow runs these checks without building or publishing an image.

After deployment or flashing, verify USB/ADB, hardware identity, the selected SIM and network registration after reboot and cold boot. Test a newly received SMS and Internet connectivity separately. Carrier and subscription behavior must be verified with the actual SIM; signal strength or a registered modem does not establish all services work.
