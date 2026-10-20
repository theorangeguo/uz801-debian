#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

ARCH="${1:-arm64}"
BOARD="${2:-${UZ801_BOARD:-uz801-v3.0}}"
if [ "$ARCH" != arm64 ]; then
  echo "Only arm64 is implemented and validated by this build" >&2
  exit 1
fi
case "$BOARD" in
  uz801-v2.1|uz801-v3.0) ;;
  *) echo "Unsupported board: $BOARD" >&2; exit 1 ;;
esac
if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root" >&2
  exit 1
fi
if [ -n "${UZ801_MODEM_FIRMWARE_DIR:-}" ] || [ -n "${UZ801_FIRMWARE_PROFILE:-}" ]; then
  echo "Use the locked board package via UZ801_BOARD or the second argument; local firmware overrides are not accepted by release builds" >&2
  exit 1
fi
if [ -d debian ] && [ -n "$(ls -A debian)" ]; then
  echo "Existing rootfs staging tree found; use a clean build checkout" >&2
  exit 1
fi

DISTRO_ARCH=arm64
DIST=bookworm
FILESYSTEM_UUID=a7ab80e8-e9d1-e8cd-f157-93f69b1d141e
mounts=()
cleanup() {
  result=$?
  trap - EXIT
  for ((index=${#mounts[@]}-1; index>=0; index--)); do
    if mountpoint -q "${mounts[$index]}"; then
      umount "${mounts[$index]}" || result=1
    fi
  done
  exit "$result"
}
trap cleanup EXIT

mkdir -p ../kernel debian build deb-pkgs
python3 ../tools/build_inputs.py prepare --board "$BOARD" --package-dir deb-pkgs --kernel-dir ../kernel --output resolved-inputs.json
HOSTNAME=$(python3 -c 'import json; print(json.load(open("resolved-inputs.json"))["hostname"])')

echo "[*] Creating Debian $DIST / $BOARD / $DISTRO_ARCH"
debootstrap --arch="$DISTRO_ARCH" --foreign "$DIST" debian https://deb.debian.org/debian/
LANG=C LANGUAGE=C LC_ALL=C chroot debian /debootstrap/debootstrap --second-stage
cp deb-pkgs/*.deb chroot.sh debian/tmp/
cp -a overlay/. debian/
chmod 0755 debian/tmp/chroot.sh debian/usr/local/sbin/uz801-select-sim
chmod 0644 debian/etc/default/uz801-modem debian/usr/lib/systemd/system/uz801-select-sim.service
# Package scripts may enable units, but cannot start services against the runner.
printf '#!/bin/sh\nexit 101\n' > debian/usr/sbin/policy-rc.d
chmod 0755 debian/usr/sbin/policy-rc.d
for target in proc dev dev/pts sys; do
  mount --bind "/$target" "debian/$target"
  mounts+=("debian/$target")
done
LANG=C LANGUAGE=C LC_ALL=C UZ801_HOSTNAME="$HOSTNAME" UZ801_BOARD="$BOARD" chroot debian /tmp/chroot.sh
python3 ../tools/build_inputs.py verify-rootfs --board "$BOARD" --root debian
install -d debian/usr/share/uz801
install -m 0644 resolved-inputs.json debian/usr/share/uz801/build-inputs.json
printf '\n- Board: %s\n' "$BOARD" >> debian/tmp/info.md
cp debian/etc/debian_version ./
cp debian/tmp/info.md ./
rm -f debian/usr/sbin/policy-rc.d debian/root/.bash_history
find debian/tmp -mindepth 1 -maxdepth 1 -type f -delete
for ((index=${#mounts[@]}-1; index>=0; index--)); do
  umount "${mounts[$index]}"
done
mounts=()

echo "[*] Creating ext4 and Android sparse rootfs"
size_mb=$(( $(du -ms debian | cut -f1) + 256 ))
truncate -s "${size_mb}M" rootfs.raw.img
mkfs.ext4 -F -L rootfs -U "$FILESYSTEM_UUID" rootfs.raw.img
mount -o loop rootfs.raw.img build
mounts+=(build)
rsync -aHAX debian/ build/
sync
umount build
mounts=()
img2simg rootfs.raw.img rootfs.img
python3 -c 'import json,os; from pathlib import Path; d=json.loads(Path("resolved-inputs.json").read_text()); d["rootfs_expanded_bytes"]=os.path.getsize("rootfs.raw.img"); Path("resolved-inputs.json").write_text(json.dumps(d,indent=2)+"\n")'
echo "[+] Board-specific sparse rootfs completed: $BOARD"
