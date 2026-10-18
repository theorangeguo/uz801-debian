# UZ801 Pure Debian System Builder

基于 Debian 官方 ARM64 打造的纯净、可复现、具备完整基带通信与 USB 调试支持的系统镜像构建仓库。

## 特色

- **最新官方系统**：纯净 Debian 12 (Bookworm) / 13 (Trixie) ARM64。
- **即插即用 ADB & RNDIS**：内置 `adbd` 守护与 `linux-usb-gadget`，插上 PC 免驱动即出 ADB 调试与 `192.168.68.1` 虚拟网卡。
- **完整基带与 SIM 支持**：预置高通 MSM8916 Modem/ADSP 固件，支持自动附着 4G 网络与收发短信。
- **开机自适应扩容**：首次启动自动将文件系统无损扩容至 eMMC 分区全部容量。
- **英文纯净环境**：标准 `en_US.UTF-8`，彻底消除 Windows 终端乱码。
- **详细定制文档**：完整定制逻辑与组件说明请参阅 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 系统默认凭据

- **Root 密码**：`1313144`
- **SSH 访问**：`ssh root@192.168.68.1`
- **ADB 访问**：`adb shell`（插上物理 USB 口即认）

## 目录结构

```text
├── .github/workflows/       # GitHub Actions 云端全自动流水线
├── firmware/                # MSM8916 高通基带与 WiFi 固件
├── kernel/                  # Linux 6.18 内核与驱动模块包
├── overlay/                 # 系统定制组件（ADB、基带激活、网络、自扩容）
├── scripts/                 # 本地构建与稀疏打包脚本
│   ├── 01-build-rootfs.sh   # debootstrap 构建 rootfs
│   └── 02-pack-image.sh     # 打包 ext4 并转换为 Android sparse 格式
├── ARCHITECTURE.md          # 详细系统架构与 6 大定制维度说明
└── README.md                # 项目简介
```

## 构建方法

### 方式 1：GitHub Actions 自动构建 (推荐)
推送代码或创建 Release Tag（如 `v1.2.0`），GitHub 将自动执行 debootstrap 构建并产出可直接刷入的 `rootfs-debian.img.gz`。

### 方式 2：本地 Linux 构建
```bash
sudo apt-get install -y debootstrap qemu-user-static binfmt-support e2fsprogs android-sdk-libsparse-utils
sudo bash scripts/01-build-rootfs.sh rootfs
sudo bash scripts/02-pack-image.sh rootfs rootfs-debian.img 1200
gzip -k -9 rootfs-debian.img
```
