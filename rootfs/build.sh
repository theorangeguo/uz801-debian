#!/bin/bash

DISTRO_ARCH="arm64"
DIST=trixie
REPO_URL="https://api.github.com/repos/haris131/uz801v3-kernel/releases"
BOOT_URL=$(curl -sL "${REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "browser_download_url:*.*-arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep boot.img | awk '{print $1}' | head -n1)
K_IMAGE_DEB_URL=$(curl -sL "${REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "browser_download_url:*.*-arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep linux-image | awk '{print $1}' | head -n1)
K_HEADER_DEB_URL=$(curl -sL "${REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "browser_download_url:*.*-arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep linux-headers | awk '{print $1}' | head -n1)
K_DEV_URL=$(curl -sL "${REPO_URL}" | sed -e 's|"||g' -e 's| ||g' | grep "arm64" | sed -e's|browser_download_url:||g' -e 's|,||g' | grep html_url | awk -F 'html_url:' '{print $2}' | head -n1)
UUID=a7ab80e8-e9d1-e8cd-f157-93f69b1d141e

if [ `id -u` -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

mkdir -p ../kernel
wget -P ../kernel "$BOOT_URL"
wget -P ../kernel "$K_IMAGE_DEB_URL"
wget -P ../kernel "$K_HEADER_DEB_URL"

mkdir -p debian build
debootstrap --arch=${DISTRO_ARCH} --foreign $DIST debian https://deb.debian.org/debian/
LANG=C LANGUAGE=C LC_ALL=C chroot debian /debootstrap/debootstrap --second-stage
cp ../deb-pkgs/*.deb ../deb-pkgs/arm64/*.deb ../kernel/linux-*.deb chroot.sh debian/tmp/
mount --bind /proc debian/proc
mount --bind /dev debian/dev
mount --bind /dev/pts debian/dev/pts
mount --bind /sys debian/sys
LANG=C LANGUAGE=C LC_ALL=C chroot debian /tmp/chroot.sh
umount debian/proc
umount debian/dev/pts
umount debian/dev
umount debian/sys

cp debian/etc/debian_version ./
mv debian/tmp/info.md ./
rm -rf debian/tmp/* debian/root/.bash_history > /dev/null 2>&1

dd if=/dev/zero of=debian-uz801v3.img bs=1M count=$(( $(du -ms debian | cut -f1) + 100 ))
mkfs.ext4 -L rootfs -U $UUID debian-uz801v3.img
mount debian-uz801v3.img build
rsync -aH debian/ build/
umount build
img2simg debian-uz801v3.img rootfs.img
rm -rf debian-uz801v3.img debian build > /dev/null 2>&1
