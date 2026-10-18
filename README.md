# uz801v3-debian

Debian 13 (Trixie) Linux Distribution for Qualcomm MSM8916 UZ801_V3 / V3.2 USB Dongles.

## Features

- **Base OS**: Pure Minimal Debian 13 (Trixie) arm64.
- **Kernel**: Modern Linux 6.6 LTS with UZ801V3 hardware device tree.
- **Out of Box**: Automatic USB Gadget RNDIS network and ADB daemon (`0123456789 device`).
- **Cellular Support**: Integrated Qualcomm modem firmware and ModemManager.

## Credentials

- **User**: `root`
- **Password**: `ChangeMe`
- **USB RNDIS IP**: `192.168.100.1`

---

## Flashing SOP (Standard Operating Procedure)

Always flash matching `aboot`, `boot`, and `rootfs` partitions together.

### Method 1: Fastboot Flashing (Standard)
1. Reboot to fastboot:
   ```bash
   adb reboot bootloader
   fastboot devices
   ```
2. Flash all images:
   ```bash
   fastboot flash aboot aboot.mbn
   fastboot flash boot boot.img
   fastboot flash rootfs rootfs.img
   fastboot reboot
   ```

### Method 2: Qualcomm EDL (9008) Flashing
1. Hold the hardware key while connecting to USB to enter 9008 EDL mode.
2. Flash partitions sequentially using an EDL programmer client:
   - Partition `aboot`: `aboot.mbn`
   - Partition `boot`: `boot.img`
   - Partition `rootfs`: `rootfs` raw/sparse image
3. Send reset command to boot.

---

## Cellular & SIM Notice

- **Supported Carriers**: China Mobile, China Unicom, and international roaming SIMs.
- **China Telecom Notice**: Not recommended due to carrier-mandated VoLTE-only authentication on current open-source Qualcomm baseband stacks.
