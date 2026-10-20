# UZ801 v2.1 SOP

Read INSTALLATION-SOP.md first. This applies to a tested variant; it does not establish every board with the same marketing name.

## Select and verify

Confirm the physical PCB, CID and expected IMEI in the private device ledger. Back up current NV and GPT before changes. Never put actual device identifiers or NV files into this repository.

Target product name: uz801-v2.1-debian. Target firmware dependency name: uz801-v2.1-firmware.deb. These names do not mean a new validated full-image release currently exists.

## Tested maintenance case

The tested v2.1 case retained correct IMEI but failed normal radio operation. Holding the kernel and physical NV unchanged, the complete B04 modem executable set restored registration. It was persisted as ordinary rootfs files through ADB. EDL, NV restoration and a new kernel were not needed for that repair.

1. Validate the complete rootfs/firmware-profiles/uz801-v2.1-b04.json against the explicit source directory using tools/firmware_profile.py.
2. Preserve current firmware, NV and identity. Verify the extraction lineage; do not trust a backup name.
3. Use the private host RAM trial tooling with read-only physical NV and the actual modem remoteproc identified by driver. Require correct IMEI, registration and unchanged NV before deployment.
4. Run tools/deploy-firmware.py with explicit identity, profile/source, the successful current trial and a new private backup directory. It backs up original files, stops the modem, persists and checks all files, removes trial mounts and restarts normal services.
5. Run tools/verify-modem.py with --firmware-profile. Check reboot, physical power cycle and a newly received SMS, keeping data off.

For a new build, explicitly supply UZ801_FIRMWARE_PROFILE=uz801-v2.1-b04 and the local UZ801_MODEM_FIRMWARE_DIR. No private source directory is fetched automatically by CI. Do not advertise a complete new v2.1 image until the build and full-image cold-boot gate pass.
