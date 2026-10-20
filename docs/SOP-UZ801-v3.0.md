# UZ801 v3.0 SOP

Read INSTALLATION-SOP.md first. This applies to a tested variant; it does not establish every board with the same marketing name.

## Select and verify

Confirm the physical PCB, CID and expected IMEI in the private device ledger. Back up current NV and GPT before changes. Never put actual device identifiers or NV files into this repository.

Target product name: uz801-v3.0-debian. Target firmware dependency name: uz801-v3.0-firmware.deb. These names do not mean a new validated full-image release currently exists.

## Tested maintenance case

The tested v3.0 case had incompatible NV contents and an unknown IMEI. A candidate was verified on the identified device in RAM before only modemst1/modemst2 were restored over Python EDL USB BULK, followed by complete partition readback and reboot/power-cycle/SMS checks. GPT, boot and rootfs were not part of that NV repair.

Use only that device's private, content-validated NV and a fresh audited recovery plan. A generic DeviceNotReady error is not sufficient to restore NV. If the current system already passes identity, slot, registration and SMS checks, preserve its NV.

For ordinary maintenance, deploy the common selector sources using tools/deploy-modem.py and validate using tools/verify-modem.py. For a fresh image, check the packaged firmware/boot/kernel/DT compatibility and require the full-image release gate. Current default builds use the existing packaged baseline; dependency asset renaming and a new full-image release remain separate work.
