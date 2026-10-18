# UZ801 Debian 系统架构与定制清单

本项目基于 Debian 官方 ARM64 基础系统（Bookworm / Trixie），专为高通 MSM8916 架构的 **UZ801 WiFi 棒** 深度适配。

为了实现**开机免插拔即用、ADB 调试可用、SIM 基带正常通信、存储自适应扩容**，本项目在原生 Debian 基础上进行了如下 6 大维度的定制处理：

---

## 1. USB 控制器与 ADB 调试 (USB Gadget & ADB Daemon)

- **痛点解决**：原生 Linux 内核默认关闭物理 USB 口从机模式，导致插上电脑后 Windows 没有任何设备枚举反应（亮红灯、无 ADB、无网卡）。
- **定制组件**：
  - `/usr/bin/adbd`：ARM64 架构的原生 Android Debug Bridge 守护进程。
  - `/usr/bin/gc` + `/usr/lib/libusbgx.so*`：Linux USB Gadget ConfigFS 配置工具。
  - `/usr/sbin/linux-usb-gadget`：
    - 创建 ConfigFS USB Gadget (`/sys/kernel/config/usb_gadget/g1`)。
    - 绑定并初始化两个物理复合功能：`rndis`（虚拟网卡）与 `ffs.adb`（FunctionFS ADB）。
    - 挂载 `/dev/usb-ffs/adb` 并拉起后台 `adbd -D` 守护。
  - `/usr/lib/systemd/system/linux-adbd-utils.service`：系统启动时开机自启该 USB 复合设备。
  - `/usr/local/bin/restart-gc.sh` + `/etc/udev/rules.d/99-hotplug-restart-gc.rules`：监听高通 SPMI PMIC 的 USB 拔插事件，在 Windows 端断开或重新插入时自动重载 Gadget 控制器。
  - `/usr/lib/udev/rules.d/90-nm-gadget-managed.rules`：强制 NetworkManager 纳管虚拟网卡设备 `usb0`。

---

## 2. 移动基带与 SIM 卡激活 (Modem & SIM Provisioning)

- **痛点解决**：MSM8916 平台的基带处理器（Modem/ADSP）依赖高通专属的非易失存储服务（RMTFS）与 QMI 协议配置。缺少专属初始化会导致基带崩溃、SIM 卡读不出或无法连接 4G。
- **定制组件**：
  - **专属固件包**：
    - `/lib/firmware/qcom/msm8916/`：注入 Modem/ADSP 固件（`mba.mbn`、`modem.mdt`、`modem.b00~b25`、`wcnss.*`）。
    - `/lib/firmware/wlan/prima/WCNSS_qcom_wlan_nv.bin`：板载无线网卡射频校准文件。
  - `/usr/sbin/sim-active.sh` + `/usr/lib/systemd/system/sim-active.service`：
    - 开机自启后检测设备树型号是否匹配 `uz801`。
    - 通过 `qmicli` 自动配置电信/联通/移动的 3GPP EPS APN 初始承载（修复特定运营商网络无法附着的问题）。
  - `/usr/sbin/openstick-sim-changer.sh` + `/usr/lib/systemd/system/openstick-sim-changer.service`：
    - 控制 GPIO/LED 切卡脚，提供物理 SIM 卡槽与板载贴片 eSIM 的切换通路。
  - `/etc/NetworkManager/system-connections/modem.nmconnection`：
    - 预配置基于 `wwan0qmi0` 的移动数据拨号，实现插卡即联网。

---

## 3. 网络与 USB 虚拟网卡配置 (Networking)

- **痛点解决**：用户插上棒子后，PC 需要立即获取 IP 并能访问棒子的 SSH。
- **定制组件**：
  - `/etc/NetworkManager/system-connections/usb.nmconnection`：
    - 将 `usb0` 网卡固定为网关地址 `192.168.68.1/24`。
    - 配置 IPv4 模式为 `shared`（即棒子内置简易 DHCP 服务，自动为插入的 PC 分配 `192.168.68.x` 的 IP）。
  - `/etc/NetworkManager/conf.d/10-wifi.conf`：
    - 默认关闭随机 MAC 地址，避免每次连接路由器导致 IP 频繁变动。
    - 关闭 Wi-Fi 激进省电模式，保证 Wi-Fi 棒作为微型服务器/热点运行时的稳定性。

---

## 4. 存储与分区自扩容 (Automatic Partition Resize)

- **痛点解决**：为了保证刷机包轻量化和下载速度，打包的 ext4 镜像仅约为 1.2GB，但棒子的 eMMC 闪存通常为 4GB 或 8GB。
- **定制组件**：
  - `/usr/sbin/openstick-expanddisk-startup.sh` + `/usr/lib/systemd/system/openstick-expanddisk-startup.service`：
    - 首次开机时自动调用 `resize2fs` 将根分区在线扩容填满整个 eMMC 物理分区。
    - 执行成功后自动调用 `systemctl disable` 关闭该服务，杜绝二次开机冗余执行。

---

## 5. 语言环境与系统基础配置 (Locales & Security)

- **痛点解决**：针对终端乱码问题，系统抛弃第三方二次封装镜像残留的中文字符集缺陷，彻底规范化。
- **定制配置**：
  - `/etc/default/locale`：强制配置为标准英文环境：
    ```bash
    LANG=en_US.UTF-8
    LC_ALL=en_US.UTF-8
    ```
  - `/etc/locale.gen`：仅编译生成标准 `en_US.UTF-8` 字典，杜绝非 UTF-8 编码引起的 Windows PowerShell/cmd 乱码。
  - **默认凭据**：
    - 用户名：`root`
    - 默认密码：`1313144`
    - SSH 配置：`/etc/ssh/sshd_config` 默认开启 `PermitRootLogin yes`，插上 PC 即可通过 `ssh root@192.168.68.1` 登录。

---

## 6. 内核与硬件树 (Kernel & DeviceTree)

- **内核版本**：Linux Kernel 6.18-rc6 (ARM64)
- **设备树文件**：`msm8916-uz801.dtb`
- **内建模块支持**：
  - 高通 SPMI / PM8916 电源管理。
  - BAM-DMUX 与 QMI WWAN 驱动。
  - WCNSS 无线模块驱动。
  - USB ConfigFS Gadget + FunctionFS 驱动。
