# Optional modem firmware profiles

The default build keeps firmware from the configured dependency package. A different physical board may require another modem executable firmware set. Do not infer suitability from a filename or device-tree model, and do not replace firmware automatically when a modem reports an error.

## Pinned profile

`rootfs/firmware-profiles/uz801-v2.1-b04.json` describes the complete B04 modem executable set tested on one user-confirmed UZ801 v2.1 board. It contains filenames, lengths and SHA256 hashes; the binaries and per-device backup evidence stay in the private companion workspace. It includes neither NV nor Wi-Fi calibration. This does not certify every v2.1 variant.

The test held the current kernel and physical NV constant. The packaged firmware reported `UZ801_V3.0_21_V01R01B10` and failed to enter normal radio operation. A complete RAM-mounted B04 set retained the expected IMEI and registered with the physical SIM, while physical NV hashes stayed unchanged. The legacy image extraction lineage was audited separately; it was not assumed to be an untouched factory backup.

## Build with an explicitly supplied profile

From `rootfs/`, set `UZ801_FIRMWARE_PROFILE=uz801-v2.1-b04` and `UZ801_MODEM_FIRMWARE_DIR` to a local directory containing the complete pinned set, then run the existing build normally. The directory must be available to the build process. The tool validates all lengths and hashes before starting the build and applies the selected set after the dependency packages have installed their default firmware.

`packaged` remains the default. The existing release workflow does not fetch or publish the private firmware directory automatically. No new full-image build is implied by a successful live deployment.

For offline validation or a staged rootfs, use `tools/firmware_profile.py --profile PROFILE --source DIRECTORY`, optionally with `--root STAGED_ROOTFS`. The installer refuses the host root and permits only modem executable filenames; it records the selected public profile under `/usr/share/uz801/modem-firmware-profile.json`.

## Existing device deployment

`tools/deploy-firmware.py` requires explicit hardware identity, a pinned profile/source, a successful RAM trial report with unchanged physical NV, and a new private backup directory. It verifies the original firmware files below the temporary trial mounts and saves their bytes before interrupting the modem. It then stops the identified modem remoteproc, removes the trial file mounts, installs and checks the normal rootfs files, releases the tmpfs, and restarts normal services.

If installation fails after interruption, the deployment record identifies the verified rollback files and the modem should remain stopped for inspection. Do not reboot or flash unrelated partitions to hide a partial installation. The tool never restores NV, enables data roaming, dials data or sends SMS. Registration, a new incoming SMS, reboot and physical power-cycle checks remain separate acceptance steps.

If the deployment was interrupted during its recorded `installing` phase, `--resume-install` reuses the same private backup directory. It requires the same boot/CID/profile, verifies every rollback file and the pre-trial physical NV audit, and finishes from the verified tmpfs candidate while the modem is stopped. It refuses a changed boot or completed deployment. Profile metadata is transferred as a file to support older ADB daemons with short command limits.
