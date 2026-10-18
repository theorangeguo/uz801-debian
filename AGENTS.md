# AGENTS.md - UZ801 Debian System Development & Maintenance Guide

本项目专为高通 MSM8916 架构的 UZ801 WiFi 棒定制打造。为防止后续开发与维护中再次出现导致设备变砖、失联的致命问题，任何代理或维护者必须严格遵循以下硬性规范。

---

## 1. 致命红线（NEVER VIOLATE）

1. **绝对严禁在缺少 USB Gadget / ADB 守护的情况下生成或烧录镜像**：
   - UZ801 棒子**没有物理屏幕、没有独立串口**，与外界通信的唯一通道就是板载的物理 USB 接口。
   - 如果系统启动时没有开机拉起 USB Gadget 控制器（FunctionFS + adbd），系统即使成功跑完内核也会关闭物理 USB 控制器，导致 PC 无法识别任何 USB 设备（表现为长亮红灯、完全失联）。
   - **底线原则**：任何镜像在打包前，必须确保包含并启用了 `linux-adbd-utils.service`、`adbd` 二进制、`linux-usb-gadget` 脚本以及 `libusbgx` 支持。

2. **严禁在未彻底验证构建结果前向硬件烧录未经验证的包**：
   - 必须确认云端打包完成、文件大小完整（ext4 稀疏镜像正常在 1GB 以上，压缩包在 140MB 以上），严禁烧录残缺文件。

3. **保留 9008 底层救砖通道**：
   - 只要 MSM8916 的 GPT 分区表与 SBL1/RPM/TZ 正常，短接或进入 9008（`Qualcomm HS-USB QDLoader 9008`）就可以使用 `emmcdl` 恢复 `rootfs` 分区。

---

## 2. 系统核心定制组件与职责清单

所有修改与迭代必须保证以下组件在 `overlay/` 中完备存在，且在 `01-build-rootfs.sh` 中正确赋予可执行权限和 systemd 自启：

| 组件路径 | 职责说明 | 缺失后果 |
| :--- | :--- | :--- |
| `/usr/bin/adbd` | ARM64 原生 ADB 守护二进制 | 无法通过 `adb shell` 登录棒子 |
| `/usr/bin/gc` + `libusbgx.so*` | Linux USB Gadget 状态配置工具 | 无法配置 ConfigFS 复合设备 |
| `/usr/sbin/linux-usb-gadget` | 初始化 RNDIS 虚拟网卡与 FunctionFS ADB | 物理 USB 口关闭，PC 无法枚举出任何设备 |
| `/usr/lib/systemd/system/linux-adbd-utils.service` | 开机自启 USB Gadget 复合设备 | 无法免插拔直接识别 ADB |
| `/usr/local/bin/restart-gc.sh` + PMIC udev 规则 | 监听 SPMI 拔插事件，热重载 Gadget | 拔插 USB 后无法重新枚举网卡和 ADB |
| `/usr/sbin/sim-active.sh` + `sim-active.service` | 配置 3GPP EPS APN，拉起 ModemManager | SIM 卡识别异常或无法附着 4G 网络 |
| `/usr/sbin/openstick-sim-changer.sh` | GPIO 控制物理卡槽 / eSIM 通路切换 | 物理卡槽无信号 |
| `/usr/sbin/openstick-expanddisk-startup.sh` | 首次开机无损扩容 rootfs 至 eMMC 全量空间 | 根目录只剩几百兆空间可用 |
| `/etc/NetworkManager/system-connections/usb.nmconnection` | `usb0` 静态网关 `192.168.68.1` + DHCP Server | PC 插上后无法获取 IP，无法 SSH |
| `/etc/default/locale` | 强制锁定 `en_US.UTF-8` | 终端字符集混乱导致乱码 |

---

## 3. 固件依赖（Firmware Dependencies）

高通平台的无线与基带完全依赖闭源固件，镜像构建必须包含：
- `/lib/firmware/qcom/msm8916/`：注入 `mba.mbn`、`modem.mdt`、`modem.b00~b25`、`wcnss.*`。
- `/lib/firmware/wlan/prima/WCNSS_qcom_wlan_nv.bin`：板载射频校准参数。

---

## 4. 自动化构建与发布规范

- **流水线文件**：`.github/workflows/build-image.yml`
- **触发机制**：
  - 推送到 `main` 分支会自动构建并生成 GitHub Actions Artifact。
  - 推送 `v*` 格式的 Git Tag（如 `git tag v1.2.0 && git push origin --tags`）会自动触发 GitHub Release，直接发布正式打包的 `rootfs-debian.img.gz`。
- **发布产物规范**：
  - `rootfs-debian.img.gz`：经由 `img2simg` 转换的 Android 稀疏镜像并经 gzip -9 压缩，可直接通过 fastboot 或解压后通过 9008 烧录。


---

## 5. 刷机工具与驱动强规范（EDL Bulk Only）

1. **必须且仅使用 edl bulk 进行底层烧录**：
   - 严禁使用 Qualcomm HS-USB QDLoader 9008 虚拟串口或任何带 COM 口驱动的方案。
   - 必须通过 WinUSB / libusb 将 9008 设备绑定为 `QHSUSB__BULK`。
   - 烧录工具统一使用开源 Python `edl`（基于 pyusb / libusb 原生 bulk 通信）：
     `powershell
     python "C:\Program Files\edl\edl.py" --loader=<loader.mbn> w <partition> <image_file>
     `
2. **严禁单刷 rootfs，必须全量刷入配套底层**：
   - 内核命令行固定依赖 PARTUUID，每次刷入新系统时，必须同步写入对应的 `aboot.bin`、`boot.img` 与 `rootfs.img`，保证引导链与设备树完全匹配。
