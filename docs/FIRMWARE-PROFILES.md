# Pinned board firmware packages

## Published inputs

config/dependencies.lock.json is the release build contract. It selects uz801-v2.1-firmware.deb / uz801-v2.1-b04 or uz801-v3.0-firmware.deb / uz801-v3.0-b08 from the immutable board-dependencies-2026.10.22.1 tag. Shared openstick-utils-all.deb is separately hashed. Kernel/boot/headers are fixed to the matched v6.6.92-arm64 release.

packaging/manifests contains the exact complete payload contracts. Each new firmware deb has its own Package identity and conflicts with the other board package. The vendor support/WLAN baseline is retained; both board modem executable sets replace that baseline. Neither package includes modemst/fsg/fsc partitions or private captures.

## Build

Use sudo bash rootfs/build.sh arm64 uz801-v2.1 or uz801-v3.0. The selected package is verified before installing it, and every installed firmware file/profile is checked before producing the image. A package with the other board name in staging is an error. Local override directories are rejected by release builds.

Build UZ801 Debian images offers v2.1, v3.0 and both, uses native ARM64 runners, and emits separate board bundle names. Explicit publishing creates a prerelease. Fresh full-image hardware acceptance remains a separate step; no firmware filename alone establishes compatibility.

## Packaging and provenance

tools/package_firmware.py accepts the hash-pinned legacy vendor deb. For either board, provide the full source directory and its exact repository-pinned profile: B04 for v2.1, B08 for v3.0. The implicit B10 fallback was removed after physical rejection. The B04 extraction lineage and identified preflash B08 system rollback were audited separately. Complete-set runtime trials keep kernel and physical NV unchanged. The B08 trial restored registration on the new Debian system; per-device persistence/reboot results remain separate. This does not claim an untouched factory backup or every PCB variant.

The builder makes deterministic gzip/tar/ar containers, emits package/profile/file manifests, and does not include maintainer scripts. New firmware package data contains the selected complete modem set and the unchanged public vendor support/WLAN files. The Linux WLAN default named WCNSS_qcom_wlan_nv.bin is from the previously public vendor package, not a copied private eMMC NV partition.

## Existing systems

tools/firmware_profile.py still validates or applies a modem-only set to an explicitly staged rootfs. tools/deploy-firmware.py requires a successful current RAM trial, explicit identity and new private rollback directory before persisting ordinary files. Interrupted installation may use --resume-install only on the same boot with verified rollback, staged files and physical NV evidence. Metadata is transferred as a file for legacy ADB command-length limits.

The deployment tool does not write partitions or enable data. Verify firmware, identity, slot, registration, new SMS, reboot and physical power-cycle separately. Preserve the user's disabled roaming setting.
