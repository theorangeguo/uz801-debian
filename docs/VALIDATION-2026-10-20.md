# Modem customization validation — 2026-10-20

## Source checks

- Shell syntax checked for the build, chroot and selector scripts.
- Seven behavioral tests passed: an already-selected slot, one verified switch, an asynchronous switch despite a command error, wrong identity, missing identity, disabled mode and invalid slot.
- Sources use LF; Python deployment and verification tools compile successfully.

## Existing-device deployment

The maintained selector and unit were deployed from this repository to a user-confirmed UZ801 v3.0 running Debian 12 and Linux 6.6.92. Device-specific identity constraints and the deployment backups remain in the private workspace. The previous per-device selector was disabled. Optional SimAdmin service and recovery timer dependencies were installed through the deployer's explicit options.

Following a separately verified device-specific NV recovery, a reboot and a user-performed power disconnect/reconnect both established:

- ADB reachable; private eMMC CID and expected IMEI match.
- Standard rmtfs uses physical partitions, with no transient RAM candidate backend.
- The preferred SIM is selected automatically and the selector succeeds.
- The installed selector matches this repository's source hash.
- The physical SIM registers through China Unicom roaming.
- After the power cycle, a new incoming SMS was observed and confirmed as received in SimAdmin. No sender number, body or PDU is included in public validation data.
- SimAdmin and its periodic recovery timer are active after startup.

This validates the existing-device deployment on that board. It does not establish other PCB revisions, Internet connectivity, outbound SMS or a complete newly built image. No new full image was built, released or flashed during this deployment. Private recovery logs, hashes and NV must not be copied into this repository.
