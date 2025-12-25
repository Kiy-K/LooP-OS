#!/bin/bash
set -e

# ==============================================================================
# LooP ISO REMASTER SCRIPT (Cubic-style CLI)
# ==============================================================================
# This script downloads a base Ubuntu ISO, extracts it, injects the LooP OS
# core and GUI, runs the installer in a chroot, and repacks it into a new ISO.
# ==============================================================================

INPUT_DIR="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <input_dir> <output_file>"
    echo "Example: $0 . /output/loop-remastered.iso"
    exit 1
fi

# Constants
ISO_URL="https://releases.ubuntu.com/jammy/ubuntu-22.04.5-desktop-amd64.iso"
ISO_NAME="ubuntu-22.04.5-desktop-amd64.iso"
WORK_DIR="/tmp/remaster_work"
ISO_MOUNT="/mnt/iso"
EXTRACT_DIR="$WORK_DIR/extracted_iso"
SQUASH_DIR="$WORK_DIR/chroot"

# Ensure clean state
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

echo "=== PHASE 1: BUILD GUI & SIDECAR ==="
echo "Compiling LooP GUI components..."

COMPILE_DIR="/tmp/compile_gui"
rm -rf "$COMPILE_DIR"
mkdir -p "$COMPILE_DIR"
cp -r "$INPUT_DIR"/gui "$COMPILE_DIR"/
cp -r "$INPUT_DIR"/src "$COMPILE_DIR"/

# 1. Compile Sidecar (Python Kernel)
echo "   Compiling Sidecar (Python Kernel)..."
cd "$COMPILE_DIR"
python3 -m nuitka --standalone --onefile --output-filename=loop-kernel.bin src/loop/cli.py

# 2. Prepare Sidecar for Tauri
echo "   Placing Sidecar..."
mkdir -p gui/src-tauri/bin
# Determine architecture for triple (assuming building on same arch as target for now)
ARCH=$(uname -m)
if [ "$ARCH" == "x86_64" ]; then
    TRIPLE="x86_64-unknown-linux-gnu"
else
    echo "Error: Unsupported architecture $ARCH"
    exit 1
fi
cp loop-kernel.bin "gui/src-tauri/bin/loop-kernel-$TRIPLE"

# 3. Generate Dummy Icons
echo "   Generating Icons..."
mkdir -p gui/src-tauri/icons
ICON_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
echo "$ICON_B64" | base64 -d > gui/src-tauri/icons/32x32.png
echo "$ICON_B64" | base64 -d > gui/src-tauri/icons/128x128.png
echo "$ICON_B64" | base64 -d > gui/src-tauri/icons/icon.png
cp gui/src-tauri/icons/icon.png gui/src-tauri/icons/icon.ico
cp gui/src-tauri/icons/icon.png gui/src-tauri/icons/icon.icns

# 4. Build Tauri App
cd "$COMPILE_DIR/gui"
echo "   Installing Node dependencies..."
npm install

echo "   Building Frontend (Vite)..."
npm run build

echo "   Building Backend (Cargo)..."
cd src-tauri
# Enable custom-protocol for production build (standard Tauri behavior)
# Also ensure features match Cargo.toml (shell-execute, shell-sidecar)
cargo build --release --features custom-protocol
cd ..

# 5. Locate Binary
echo "   Locating compiled binary..."
BINARY_PATH=$(find "$COMPILE_DIR/gui/src-tauri/target/release" -maxdepth 1 -type f -executable -not -name "*.so" -not -name "*.d" | head -n 1)
if [ -z "$BINARY_PATH" ] || [ ! -f "$BINARY_PATH" ]; then
    echo "Error: GUI compilation failed. Binary not found."
    ls -R src-tauri/target/release
    exit 1
fi
echo "   GUI Binary found at: $BINARY_PATH"


echo "=== PHASE 2: PREPARE BASE ISO ==="
cd "$WORK_DIR"

if [ ! -f "/build/$ISO_NAME" ]; then
    echo "Downloading Ubuntu Base ISO..."
    wget -O "$ISO_NAME" "$ISO_URL"
else
    echo "Using cached ISO from /build/$ISO_NAME"
    cp "/build/$ISO_NAME" .
fi

echo "Extracting ISO..."
xorriso -osirrox on -indev "$ISO_NAME" -extract / "$EXTRACT_DIR"

echo "Extracting Filesystem (SquashFS)..."
unsquashfs -d "$SQUASH_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs"


echo "=== PHASE 3: INJECT & INSTALL ==="

# 1. Inject GUI Binary
echo "Injecting GUI Binary..."
mkdir -p "$SQUASH_DIR/usr/local/bin"
cp "$BINARY_PATH" "$SQUASH_DIR/usr/local/bin/loop-desktop"
chmod +x "$SQUASH_DIR/usr/local/bin/loop-desktop"

# 2. Inject Source Code
echo "Injecting Source Code..."
mkdir -p "$SQUASH_DIR/opt/loop"
cp -a "$INPUT_DIR"/. "$SQUASH_DIR/opt/loop/"

# 3. Inject Installer Script
echo "Injecting Installer Script..."
cp "$INPUT_DIR/install/setup_loop.sh" "$SQUASH_DIR/tmp/install.sh"
chmod +x "$SQUASH_DIR/tmp/install.sh"

# 4. Prepare Chroot
echo "Mounting virtual filesystems..."
mount --bind /dev "$SQUASH_DIR/dev"
mount --bind /dev/pts "$SQUASH_DIR/dev/pts"
mount --bind /proc "$SQUASH_DIR/proc"
mount --bind /sys "$SQUASH_DIR/sys"

# 5. DNS Resolution in Chroot
echo "Configuring DNS for Chroot..."
cat /etc/resolv.conf > "$SQUASH_DIR/etc/resolv.conf"

# 6. Run Installation in Chroot
echo "ENTERING CHROOT: Running LooP Installer..."
chroot "$SQUASH_DIR" /bin/bash -c "/tmp/install.sh"

# 7. Cleanup Chroot
echo "Cleaning up Chroot..."
# Remove temporary installer
rm "$SQUASH_DIR/tmp/install.sh"
# Clean apt cache in chroot
chroot "$SQUASH_DIR" apt-get clean
chroot "$SQUASH_DIR" rm -rf /var/lib/apt/lists/*
# Clear bash history
chroot "$SQUASH_DIR" truncate -s 0 /root/.bash_history

# Unmount
echo "Unmounting virtual filesystems..."
umount "$SQUASH_DIR/sys"
umount "$SQUASH_DIR/proc"
umount "$SQUASH_DIR/dev/pts"
umount "$SQUASH_DIR/dev"


echo "=== PHASE 4: REPACK ISO ==="

echo "Regenerating Manifest..."
chmod +w "$EXTRACT_DIR/casper/filesystem.manifest"
chroot "$SQUASH_DIR" dpkg-query -W --showformat='${Package} ${Version}\n' > "$EXTRACT_DIR/casper/filesystem.manifest"
cp "$EXTRACT_DIR/casper/filesystem.manifest" "$EXTRACT_DIR/casper/filesystem.manifest-desktop"
sed -i '/ubiquity/d' "$EXTRACT_DIR/casper/filesystem.manifest-desktop"
sed -i '/casper/d' "$EXTRACT_DIR/casper/filesystem.manifest-desktop"

echo "Repacking SquashFS..."
# Delete old squashfs
rm "$EXTRACT_DIR/casper/filesystem.squashfs"
# Create new one
mksquashfs "$SQUASH_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs" -comp xz -noappend

echo "Updating MD5 sums..."
cd "$EXTRACT_DIR"
find . -type f -print0 | xargs -0 md5sum > md5sum.txt

echo "Building Bootable ISO..."
cd "$WORK_DIR"
# xorriso command to recreate a hybrid ISO (EFI + BIOS)
# Based on common Ubuntu remastering commands
xorriso -as mkisofs \
  -r -V "LooP OS 22.04" \
  -J -joliet-long \
  -b boot/grub/i386-pc/eltorito.img \
  -c boot.catalog \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  -eltorito-alt-boot \
  -e boot/grub/efi.img \
  -no-emul-boot -isohybrid-gpt-basdat \
  -o "$OUTPUT_FILE" \
  "$EXTRACT_DIR"

echo "=== REMASTER COMPLETE ==="
ls -lh "$OUTPUT_FILE"
