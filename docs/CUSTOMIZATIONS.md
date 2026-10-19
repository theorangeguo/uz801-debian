# Maintained image customizations

This document records the customization added for preferred SIM selection. It is not an audit of every file shipped by the upstream dependency packages.

## Ownership boundary

| Image repository | Private companion workspace |
| --- | --- |
| Generic scripts, systemd units, default settings, build integration | Device identity and physical PCB revision |
| Behavior documentation and generic validation criteria | IMEI, CID, SIM subscription data and credentials |
| Generic recovery prerequisites | Original full-disk images, per-device NV, rollback images and provenance |
| Reproducible image source | Host-specific EDL tools, paths, driver state and recovery logs |

The image must never embed an individual device's IMEI, CID or NV backup. A similar board or common manufacturer does not make device-specific NV interchangeable. Hardware firmware packages and per-device NV are separate inputs.

## Preferred SIM selection

Source files under `rootfs/overlay/`:

- `usr/local/sbin/uz801-select-sim`: waits for ModemManager, requests the configured slot once, and verifies the result with bounded retries.
- `usr/lib/systemd/system/uz801-select-sim.service`: runs after ModemManager and is restarted with it; it does not reset the radio, restart ModemManager, or manipulate GPIO.
- `etc/default/uz801-modem`: defaults to `UZ801_PRIMARY_SIM_SLOT=1`. Set `2` to prefer the other slot, or `disabled` to leave selection unchanged.

On the tested UZ801 v3.0 device, ModemManager slot 1 was the physical SIM and slot 2 the built-in SIM. Do not assume the mapping applies to other PCB revisions; verify it before enabling this policy there. Selection does not guarantee registration, SMS delivery or Internet access.

The service optionally reads `/etc/uz801/device.conf` after the generic defaults. A private deployment may set `UZ801_EXPECTED_CID` and `UZ801_EXPECTED_IMEI` there. A CID mismatch refuses selection; an expected IMEI must be available before a switch. These values are provisioned outside the public image and are not required in the generic defaults.

`rootfs/build.sh` copies the overlay before customization; `rootfs/chroot.sh` verifies the required files and enables the service after installing the dependency packages. The selector does not replace the upstream GPIO setup script: the two have different responsibilities.

## Validation and current limits

The private device trial established that selecting physical slot 1 through ModemManager restored registration and incoming SMS after modem restart. Shell syntax, an already-selected slot, disabled mode, identity rejection and a mocked slot change were checked. The automated tests also cover a command returning an error after an asynchronous switch has actually completed. A built-image cold-boot test remains separate.

Before declaring an image usable, check USB/ADB availability, the intended SIM identity/slot, network registration and a newly received test SMS after cold boot. Validate Internet access separately. Confirm that any independent SIM-management application does not override the configured preference.

## NV recovery is not an image startup action

Never restore NV automatically during image build or boot. The private workspace must establish backup provenance, match the hardware, preserve rollback copies, verify target layout, and read back written partitions. A modem error alone does not prove NV corruption.

This project's flashing policy is Python EDL over WinUSB/libusb BULK only. Do not switch drivers or use COM/QDLoader, QFIL, emmcdl, fastboot or ADB block writes. Host paths and device-specific commands belong in the private workspace SOP.

## Update an existing device from these sources

Run `tools/deploy-modem.py` with `--adb`, `--serial`, `--expected-cid`, `--expected-imei`, and a private `--backup-dir`. The default preferred slot is 1; `--slot` can select 2 or `disabled`. Keep actual identity values and commands in the private deployment record, outside this repository.

The deployer reads this repository's overlay, normalizes LF, verifies CID and root access, backs up replaced files and previous unit states, checks staged and installed hashes, validates the systemd unit and enables it. It provisions the supplied identity guards into private `/etc/uz801/device.conf`, preserves other private settings, and disables the earlier `uz801-physical-sim.service` so it cannot race the maintained selector. It requests an asynchronous start and records that runtime validation is still pending. It neither restores NV nor reboots.

For an installed optional application that must wait for SIM selection, repeat `--after-selector-unit UNIT` for its service or timer. This installs a `Requires`/`After` drop-in and backs up the prior file if present. These are explicit deployment options, not assumptions that the application ships with the base image. A failed selector prevents a newly started dependent application from racing recovery.

Backups include `manifest.json` and the prior bytes under their absolute target-relative paths. On deployment failure, inspect this manifest before retrying or restoring files; do not discard the backups. A successful deployment does not prove registration, SMS reception or cold-boot behavior.

Run `tools/verify-modem.py` with the same private identity arguments and a new private `--output` path after startup. It waits for the modem, checks identity, the intended slot, registration, selector result and the physical-partition rmtfs backend, and compares the installed selector with the repository. It records SMS object count without reading message bodies. Newly received SMS, Internet access and a physical cold boot still require separate acceptance evidence.

## Build checks

`rootfs/chroot.sh` fails on command errors, checks the required USB executables supplied by the current utility package, and enables its actual `openstick-gc-startup.service`. NTP is enabled offline through systemd; the build does not call `timedatectl` against a nonexistent chroot system bus.

`.github/workflows/check-modem.yml` runs syntax, LF and behavioral checks without publishing an image. Run `python3 -m unittest discover -s tests -v` locally; Windows hosts can set `UZ801_TEST_SHELL` to Git for Windows' `sh.exe`.
