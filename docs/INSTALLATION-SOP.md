# Common installation and maintenance SOP

## Release gate

Existing-device v3.0 and v2.1 repairs were verified. New full images containing the maintained startup/profile changes have not been published for both variants. Do not perform a fresh full-image installation from an old artifact solely because its name says Debian or UZ801. Stop unless the selected board has a completed build, approved image set, hashes and validation record.

## Identify and preserve

Match the physical board through independent hardware/user evidence and eMMC CID plus expected IMEI. A shared ADB serial or flashed device-tree name is insufficient. Save a new current NV/GPT capture with lengths, hashes and rollback evidence; preserve original files. An unknown IMEI requires explicit technical identity review, not changing an expected value to bypass a check.

Never infer full-image ownership from directory names, software build versions or a copied manifest. Firmware executables and per-device NV are different assets. Common images must not contain IMEI, CID, subscriptions, credentials or per-device NV.

## Select the path

- Existing system passes verify: no repair is required.
- Startup selection change: use deploy-modem.py with explicit identity and a new private backup directory.
- Tested v2.1 firmware mismatch: follow SOP-UZ801-v2.1.md, validate the full set, RAM trial and then deploy-firmware.py.
- Proven device-specific NV fault: follow the private device recovery plan. This is separate from image installation.
- Fresh install/rescue: require a board-matched boot/rootfs/kernel/modules/DT set, loader, GPT capacity and exact readback plan first.

## EDL

Only Python EDL USB BULK is allowed for partition writes. ADB -> bootloader -> fastboot oem reboot-edl may be used only as a transition. Verify a unique 9008 target and WinUSB/QHSUSB__BULK, not COM/QDLoader. Driver changes need explicit authorization. Match the device again through the controlled transition and GPT/NV readback; Sahara serial is not eMMC CID.

Use a verified programmer and the geometry it actually supports. Read current partitions before writing. Write only the reviewed partition list, not GPT/NV by default. Keep bootloaders unless their replacement is independently required. A successful USB transfer is not boot acceptance. A compressed/sparse file hash is not the same as a raw physical partition hash; the image manifest must specify unpacked content and readback scope.

## Acceptance

Verify USB/ADB, identity, firmware/profile hashes, the selected SIM, registration, normal persistent storage and no trial mounts. Verify software reboot and an independently user-performed power disconnect/reconnect with distinct boot IDs. Receive a new test SMS without retaining private text or codes. Keep data roaming/autoconnect off; Internet traffic and outbound SMS require separate authorization.
