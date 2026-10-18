#!/bin/bash
set -euo pipefail

ROOTFS_DIR="${1:-rootfs}"
RELEASE="bookworm"
ARCH="arm64"
MIRROR="http://deb.debian.org/debian"

echo "=== Step 1: Debootstrap Debian $RELEASE ($ARCH) ==="
mkdir -p "$ROOTFS_DIR"
debootstrap --arch="$ARCH" --foreign --variant=minbase "$RELEASE" "$ROOTFS_DIR" "$MIRROR"

# Complete stage 2 with qemu-aarch64-static
cp /usr/bin/qemu-aarch64-static "$ROOTFS_DIR/usr/bin/"
chroot "$ROOTFS_DIR" /debootstrap/debootstrap --second-stage

echo "=== Step 2: Configure System & Essential Packages ==="
mount -t proc /proc "$ROOTFS_DIR/proc"
mount -t sysfs /sys "$ROOTFS_DIR/sys"
mount -o bind /dev "$ROOTFS_DIR/dev"
mount -o bind /dev/pts "$ROOTFS_DIR/dev/pts"

cleanup() {
    umount -l "$ROOTFS_DIR/proc" || true
    umount -l "$ROOTFS_DIR/sys" || true
    umount -l "$ROOTFS_DIR/dev/pts" || true
    umount -l "$ROOTFS_DIR/dev" || true
    rm -f "$ROOTFS_DIR/usr/bin/qemu-aarch64-static"
}
trap cleanup EXIT

# Apt sources
cat << 'EOF' > "$ROOTFS_DIR/etc/apt/sources.list"
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware
EOF

cat << 'EOF' | chroot "$ROOTFS_DIR" /bin/bash
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
    systemd-sysv locales sudo bash-completion kmod udev \
    net-tools iproute2 iputils-ping ifupdown dnsmasq-base \
    network-manager modemmanager libqmi-utils libmbim-utils \
    openssh-server ca-certificates curl nano htop usbutils \
    e2fsprogs rmtfs

# Locale setup: enforce pure en_US.UTF-8
sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Hostname
echo "uz801" > /etc/hostname
cat << 'HEOF' > /etc/hosts
127.0.0.1   localhost uz801
::1         localhost ip6-localhost ip6-loopback
HEOF

# Root password default to 1313144
echo "root:1313144" | chpasswd
# Allow SSH root login with password
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config || true

# Clean apt cache
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
EOF

echo "=== Step 3: Inject Kernel & Modules ==="
if [ -f "kernel/uz801-kernel-6.18.tar.gz" ]; then
    echo "Extracting UZ801 Linux kernel 6.18..."
    tar -xzf "kernel/uz801-kernel-6.18.tar.gz" -C "$ROOTFS_DIR/"
fi

echo "=== Step 4: Inject Overlay & Firmware ==="
cp -r overlay/* "$ROOTFS_DIR/"
chmod +x "$ROOTFS_DIR/usr/local/bin/uz801-firstboot.sh"

chroot "$ROOTFS_DIR" systemctl enable uz801-firstboot.service || true

# Firmware injection
mkdir -p "$ROOTFS_DIR/lib/firmware/qcom/msm8916"
mkdir -p "$ROOTFS_DIR/lib/firmware/wlan/prima"
cp -r firmware/qcom/* "$ROOTFS_DIR/lib/firmware/qcom/msm8916/" || true
cp -r firmware/wlan/prima/* "$ROOTFS_DIR/lib/firmware/wlan/prima/" || true

echo "=== Debian Rootfs build completed successfully! ==="