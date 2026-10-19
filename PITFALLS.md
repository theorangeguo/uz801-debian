# Maintenance pitfalls

- Verify device identity before every recovery. A shared ADB serial, directory name, build string or flashed device tree cannot establish physical ownership.
- Preserve original backup bytes and provenance. Identical files copied into several device directories are not independent known-good backups.
- Distinguish firmware programs from per-device NV. Restore only a proven candidate to its identified hardware.
- A RAM-backed rmtfs trial is temporary. Record its backend, flags and verification evidence; do not call it persistent recovery.
- A short write may leave the rest of a partition unchanged. Prepare and test the intended complete partition contents, then verify full readback.
- An ext4 image can be smaller than its containing partition. Size difference alone does not prove corruption, and sparse conversion does not fix boot compatibility or GPT layout.
- `root=PARTUUID=` matches a GPT partition GUID, not the ext4 filesystem UUID.
- ADB absence or a red LED does not by itself prove a kernel panic, power failure or bootloader mode. Preserve logs and identify the USB state.
- Read signal, registration, packet attachment, SMS delivery and Internet tests as separate evidence.
- Keep startup selectors and optional application recovery tasks from racing. Record enabled states and validate after reboot.
- Use LF shell sources. Do not let a later successful command hide an earlier failed check; check individual results.
- Never run historical fastboot, COM or ADB block-write recipes. Current policy is Python EDL USB BULK only.
