#!/bin/bash
set -euo pipefail

ROOTFS_DIR="${1:-rootfs}"
OUTPUT_IMG="${2:-rootfs-debian.img}"
IMG_SIZE_MB="${3:-1200}"

echo "=== Packing Rootfs to $OUTPUT_IMG ($IMG_SIZE_MB MB ext4 sparse image) ==="
dd if=/dev/zero of="$OUTPUT_IMG" bs=1M count=0 seek="$IMG_SIZE_MB"
mkfs.ext4 -F -L "rootfs" -b 4096 "$OUTPUT_IMG"

MNT_DIR="/tmp/mnt_rootfs"
mkdir -p "$MNT_DIR"
mount -o loop "$OUTPUT_IMG" "$MNT_DIR"

cleanup() {
    umount -l "$MNT_DIR" || true
    rm -rf "$MNT_DIR"
}
trap cleanup EXIT

echo "Copying rootfs files..."
cp -a "$ROOTFS_DIR"/. "$MNT_DIR"/

echo "Rootfs packed successfully: $OUTPUT_IMG"
