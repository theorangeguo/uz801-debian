#!/bin/bash
set -e

DISTRO_ARCH="arm64"
DIST=bookworm
UUID=a7ab80e8-e9d1-e8cd-f157-93f69b1d141e

# External pinned dependency URLs (Managed & Version-locked)
KERNEL_REPO_URL="https://api.github.com/repos/haris131/uz801v3-kernel/releases"
DEP_RELEASE_URL="https://github.com/theorangeguo/uz801v3-debian/releases/download/prebuilt-dependencies"
FIRMWARE_DEB_URL="${DEP_RELEASE_URL}/firmware-uz801v3.deb"
UTILS_DEB_URL="${DEP_RELEASE_URL}/openstick-utils-all.deb"

if [ `id -u` -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "[*] Resolving pinned kernel assets from upstream..."
BOOT_URL=$(curl -sL "${KERNEL_REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "browser_download_url:*.*-arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep boot.img | awk '{print $1}' | head -n1)
K_IMAGE_DEB_URL=$(curl -sL "${KERNEL_REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "browser_download_url:*.*-arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep linux-image | awk '{print $1}' | head -n1)
K_HEADER_DEB_URL=$(curl -sL "${KERNEL_REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "browser_download_url:*.*-arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep linux-headers | awk '{print $1}' | head -n1)

mkdir -p ../kernel debian build deb-pkgs

echo "[*] Downloading kernel assets..."
wget -q --show-progress -P ../kernel "$BOOT_URL"
wget -q --show-progress -P ../kernel "$K_IMAGE_DEB_URL"
wget -q --show-progress -P ../kernel "$K_HEADER_DEB_URL"

echo "[*] Downloading pinned deb packages..."
wget -q --show-progress -P deb-pkgs "$FIRMWARE_DEB_URL"
wget -q --show-progress -P deb-pkgs "$UTILS_DEB_URL"

echo "[*] Running debootstrap for Debian ($DIST)..."
debootstrap --arch=${DISTRO_ARCH} --foreign $DIST debian https://deb.debian.org/debian/
LANG=C LANGUAGE=C LC_ALL=C chroot debian /debootstrap/debootstrap --second-stage

cp deb-pkgs/*.deb ../kernel/linux-*.deb chroot.sh debian/tmp/
cp -a overlay/. debian/
chmod 0755 debian/usr/local/sbin/uz801-select-sim
chmod 0644 debian/etc/default/uz801-modem debian/usr/lib/systemd/system/uz801-select-sim.service
mount --bind /proc debian/proc
mount --bind /dev debian/dev
mount --bind /dev/pts debian/dev/pts
mount --bind /sys debian/sys

echo "[*] Executing chroot customization..."
LANG=C LANGUAGE=C LC_ALL=C chroot debian /tmp/chroot.sh

umount debian/proc
umount debian/dev/pts
umount debian/dev
umount debian/sys

cp debian/etc/debian_version ./
mv debian/tmp/info.md ./
rm -rf debian/tmp/* debian/root/.bash_history deb-pkgs > /dev/null 2>&1

echo "[*] Creating ext4 sparse rootfs..."
dd if=/dev/zero of=debian-uz801v3.img bs=1M count=$(( $(du -ms debian | cut -f1) + 100 ))
mkfs.ext4 -L rootfs -U $UUID debian-uz801v3.img
mount debian-uz801v3.img build
rsync -aH debian/ build/
umount build
img2simg debian-uz801v3.img rootfs.img
rm -rf debian-uz801v3.img debian build > /dev/null 2>&1
echo "[+] Build completed successfully!"
