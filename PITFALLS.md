# UZ801V3 刷机与固件构建避坑实录 (Pitfalls & Post-Mortem)

为了防止后续开发与多设备复用时再次出现致命踩坑、反复试错，本文档记录真实排查出的底层硬件、分区与通信硬性规则。

---

## 1. 分区对齐与镜像格式（核心血泪教训）

### 坑点现象
- 云端生成的 raw ext4 镜像只有约 1.25GB，通过 9008 烧录到 rootfs 分区后，开机长亮红灯、完全无 USB 枚举、变砖。

### 根因剖析
- 高通 GPT 分区表中，硬性划分给 rootfs 的物理扇区范围是 659456 至 7569374，物理容量整整为 3.29 GB (3,537,878,528 字节)。
- 若直接向该分区写入未对齐的 1.25GB raw 镜像，后半段分区数据缺失或存在脏块。Linux 内核在启动挂载根分区时，ext4 文件系统因 Superblock 与块组描述符越界抛出 Kernel Panic，CPU 停机，USB 控制器断电，导致物理 USB 端口彻底失联。

### 正规正解
- 必须使用 Android 稀疏镜像（Sparse Image, img2simg）：
  在 build.sh 中：
  `ash
  dd if=/dev/zero of=rootfs.raw bs=1M count=100
  mkfs.ext4 -L rootfs -U a7ab80e8-e9d1-e8cd-f157-93f69b1d141e rootfs.raw
  mount rootfs.raw build
  rsync -aH debian/ build/
  umount build
  img2simg rootfs.raw rootfs.img
  `
  img2simg 生成的稀疏镜像由 Fastboot 或 EDL 工具写入时，仅烧录有效数据块并自适应底层物理扇区，彻底规避 raw 镜像分区大小不匹配导致的崩溃。

---

## 2. 9008 原生 EDL Bulk 通信与 Windows 驱动避坑

### 坑点现象
- Python edl 工具在 Windows 下运行报 Permission denied accessing 05c6:9008 或 Couldn\'t get device configuration。

### 根因剖析
- 驱动冲突：系统自动给设备加载了 Qualcomm HS-USB QDLoader 9008 (COMx) 串口驱动，而 Python edl（基于 libusb）需要底层 WinUSB / Bulk 设备。
- 库兼容缺陷：开源 edl 的 usblib.py 在 Windows 下默认未加载 libusb-1.0.dll，导致 pyusb 无法初始化 backend。

### 正规正解
1. 必须使用 WinUSB 驱动将 9008 绑定为 QHSUSB__BULK，坚决不走 COM 口。
2. 在 Windows 下运行 Python edl 时，显式加载自带的 libusb-1.0.dll：
   `powershell
   python edl.py w aboot aboot.mbn
   python edl.py w boot boot.img
   python edl.py w rootfs rootfs.img
   python edl.py reset
   `

---

## 3. 引导链与内核（Bootloader & Kernel）强绑定

### 坑点现象
- 只刷 rootfs，不刷配套的 boot 和 aboot，开机黑屏。

### 根因剖析
- 高通 MSM8916 启动链为 PBL -> SBL1 -> RPM/TZ/HYP -> aboot (LK) -> boot (Kernel+DTB) -> rootfs。
- boot.img 内嵌的设备树（DTB）与内核启动命令行（cmdline）必须精准匹配 rootfs 的 PARTUUID（a7ab80e8-e9d1-e8cd-f157-93f69b1d141e），且 DTB 必须声明专属于 UZ801V3 的 USB PHY 与 PMIC 节点。

### 正规正解
- 采用 haris131/uz801v3-kernel 发布的标准 boot.img，每次刷机必须同步写入 aboot.mbn、boot.img 与 rootfs.img，保证全套引导链一致。

---

## 4. 固件与 USB Gadget 自动化服务

### 坑点现象
- 纯净 Debian 无法通过 USB 识别 ADB 或网络。

### 正规正解
- 系统构建必须通过 deb 包直接集成：
  - openstick-utils-all.deb：管理 FunctionFS、自动拉起 adbd 与 rndis 虚拟网卡。
  - firmware-uz801v3.deb：安装 /lib/firmware/ 下的高通调制解调器（Modem）与无线网卡（WCNSS）闭源镜像。
