# UZ801 Debian System Image Builder

Automated CI/CD builder for creating minimal, pure, and authentic **Debian LTS (Bookworm arm64)** system images tailored for **Qualcomm Snapdragon 410 (MSM8916) based UZ801 USB WiFi sticks**.

---

## 🌟 Key Features & Core Fixes

1. **Pure English Environment**:
   - Fixed to `en_US.UTF-8` globally out of the box, eliminating square-box terminal character garble.
2. **Wi-Fi Single-RF Friendly**:
   - Default to client (Managed) mode (`connection.autoconnect no` for default AP).
   - Prevents the single-antenna WCN3660 radio from being blocked by an unwanted AP, allowing instant background Wi-Fi scanning.
3. **Authentic Baseband & SIM Ready**:
   - Pre-installed `rmtfs` with systemd unit auto-recovery.
   - Authentic UZ801 modem firmware pre-injected into `/lib/firmware/qcom/msm8916/`.
   - Supports physical SIM slot and LTE network management via `ModemManager` and `qmicli`.
4. **USB RNDIS Static IP**:
   - Plug into any PC via USB to immediately access `192.168.68.1`. Default login `root:1313144`.
5. **Lightweight & Clean**:
   - Tailored for 512MB RAM MSM8916 devices without heavy desktop or redundant bloatware.

---

## 🏗️ Repository Architecture

```text
├── .github/workflows/
│   └── build-image.yml         # GitHub Actions automated build pipeline
├── overlay/                    # System rootfs overlay
│   ├── etc/
│   │   ├── default/locale      # Pure en_US.UTF-8 locale
│   │   ├── systemd/system/     # rmtfs & firstboot services
│   │   └── NetworkManager/     # Managed Wi-Fi rules
│   └── usr/local/bin/
│       └── uz801-firstboot.sh  # Auto-resizes rootfs on initial boot
├── firmware/                   # UZ801 closed-source authentic drivers
│   ├── qcom/                   # MSM8916 modem & MBA firmware
│   └── wlan/prima/             # WCN3660 NV calibration file
└── scripts/
    ├── 01-build-rootfs.sh      # Debootstrap & package setup script
    └── 02-pack-image.sh        # Sparse ext4 rootfs image packer
```

---

## 🚀 How to Build & Use

### 1. Build via GitHub Actions
Every push to `main` or new tag (e.g. `v1.0.0`) automatically builds `rootfs-debian.img.gz` in GitHub Actions and publishes it to Releases.

### 2. Flashing to UZ801
Download the output image, place it in your local workspace, and flash via Fastboot:
```bash
fastboot flash rootfs rootfs-debian.img
fastboot reboot
```

Default credentials:
- **User**: `root`
- **Password**: `1313144`
- **SSH / RNDIS IP**: `192.168.68.1`
