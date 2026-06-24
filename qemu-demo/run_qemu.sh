#!/bin/bash
set -e

QEMU_DIR="$(cd "$(dirname "$0")" && pwd)"

KERNEL="${QEMU_DIR}/Image"
INITRD="${QEMU_DIR}/initramfs.cpio"

if [ ! -f "$KERNEL" ]; then
    echo "[ERROR] Missing kernel image: $KERNEL"
    echo "Please put ARM64 Linux kernel Image into qemu-demo/Image"
    exit 1
fi

if [ ! -f "$INITRD" ]; then
    echo "[ERROR] Missing initramfs: $INITRD"
    echo "Please put initramfs.cpio into qemu-demo/initramfs.cpio"
    exit 1
fi

qemu-system-aarch64 \
  -M virt \
  -cpu cortex-a53 \
  -m 1024M \
  -nographic \
  -kernel "$KERNEL" \
  -initrd "$INITRD" \
  -append "console=ttyAMA0 root=/dev/ram rdinit=/sbin/init"
