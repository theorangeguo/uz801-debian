# UZ801 v3.0 SOP

Read INSTALLATION-SOP.md first. This applies to a tested variant; it does not establish every board with the same marketing name.

## Select and verify

Confirm the physical PCB, CID and expected IMEI in the private device ledger. Back up current NV and GPT before changes. Never put actual device identifiers or NV files into this repository.

Target product name: uz801-v3.0-debian. Target firmware dependency name: uz801-v3.0-firmware.deb. These names are selected by CI; verify the actual bundle manifest and physical acceptance status.

## Tested maintenance case

The tested v3.0 case had incompatible NV contents and an unknown IMEI. A candidate was verified on the identified device in RAM before only modemst1/modemst2 were restored over Python EDL USB BULK, followed by complete partition readback and reboot/power-cycle/SMS checks. GPT, boot and rootfs were not part of that NV repair.

Use only that device's private, content-validated NV and a fresh audited recovery plan. A generic DeviceNotReady error is not sufficient to restore NV. If the current system already passes identity, slot, registration and SMS checks, preserve its NV.

For ordinary maintenance, deploy the common selector sources using tools/deploy-modem.py and validate using tools/verify-modem.py. For a fresh image, check the packaged firmware/boot/kernel/DT compatibility and require the full-image release gate. The build selects uz801-v3.0-firmware.deb from the immutable input lock and fixes its boot/kernel/headers version.

## Candidate image result (2026-10-21)

The published `uz801-v3.0-b10` candidate was flashed to the tested v3.0 board with complete rootfs readback; GPT, boot, aboot and all four NV partitions were preserved. Debian, ADB, IMEI and 145 firmware file hashes passed, but the preflash modem was B08 and the postflash B10 modem returned QMI `DeviceNotReady` and did not register. This candidate is rejected for this board. Do not restore NV to address this result. The complete preflash system rollback and comparison report remain in the private workspace. The identified rollback B08 source was subsequently audited and restored registration in a controlled modem-only trial on the new system; new builds select B08.

## B08 modem-only trial (2026-10-22)

The complete 22-file B08 set was extracted from the hash-verified, CID/IMEI-identified preflash EDL rootfs rollback. Replacing only these executable files on the new Debian system restored registration; all four physical NV hashes stayed unchanged. No GPT, boot, bootloader or NV writes were used in this trial. New packaging requires the explicit uz801-v3.0-b08 profile and cannot silently retain B10. This trial does not by itself certify a newly rebuilt full image or incoming SMS.

Persistence was verified after a user-performed physical power disconnect/reconnect on 2026-10-22: B08/profile hashes matched, the SIM selector and registration passed, physical NV stayed unchanged and no trial mounts remained. No cellular bearer or cellular traffic was present. Incoming SMS and a newly rebuilt full-image installation remain separate unperformed checks.

## Complete B08 image installation (2026-10-22)

The exact 10-r1 bundle from debian-bookworm-arm64-39780807753-r1 was installed over Python EDL USB BULK. The published boot prefix already matched, so rootfs was written and completely read back; GPT, four NV partitions, boot and aboot were preserved. First boot, software reboot and a user power cycle passed with B08/slot 1 registration, 145 matching firmware package files and zero cellular bytes. No post-flash repairs or trial mounts were required. See [the full-image record](validation/uz801-v3.0-b08-full-image-20261022.json). New incoming SMS and network connection checks remain untested.
