#!/bin/bash
set -euo pipefail

ROOTFS_DIR="${1:-rootfs}"
OUTPUT_IMG="${2:-rootfs-debian.img}"
IMG_SIZE_MB="${3:-1200}"

echo "=== Packing Rootfs to $OUTPUT_IMG ($IMG_SIZE_MB MB Android Sparse ext4 image) ==="
RAW_IMG="/tmp/rootfs_raw.img"
dd if=/dev/zero of="$RAW_IMG" bs=1M count=0 seek="$IMG_SIZE_MB"
mkfs.ext4 -F -L "rootfs" -b 4096 "$RAW_IMG"

MNT_DIR="/tmp/mnt_rootfs"
mkdir -p "$MNT_DIR"
mount -o loop "$RAW_IMG" "$MNT_DIR"

cleanup() {
    umount -l "$MNT_DIR" || true
    rm -rf "$MNT_DIR" "$RAW_IMG"
}
trap cleanup EXIT

echo "Copying rootfs files..."
cp -a "$ROOTFS_DIR"/. "$MNT_DIR"/

umount -l "$MNT_DIR"

echo "Converting raw ext4 image to Android sparse image..."
img2simg "$RAW_IMG" "$OUTPUT_IMG"

echo "Android sparse image created successfully: $OUTPUT_IMG"
ls -lh "$OUTPUT_IMG"