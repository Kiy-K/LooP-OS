#!/bin/bash
set -e

# ----------------------------------------------------------------------
# LOOP OS DISTRO BUILDER (Remastering Pipeline)
# Remasters Ubuntu 22.04 Live Server ISO into LooP OS.
# ----------------------------------------------------------------------

# Configuration
ISO_URL="https://releases.ubuntu.com/22.04/ubuntu-22.04.5-live-server-amd64.iso"
ISO_NAME="ubuntu-22.04.5-live-server-amd64.iso"
WORK_DIR="$(pwd)/tools/remaster/build"
OUT_DIR="$(pwd)/tools/remaster/out"
REPO_ROOT="$(pwd)"

# Ensure we are root (needed for mount/chroot)
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root (or with sudo)."
  exit 1
fi

# Create directories
mkdir -p "$WORK_DIR"
mkdir -p "$OUT_DIR"

# 1. DOWNLOAD ISO
echo "⬇️  Step 1: Downloading Ubuntu ISO..."
if [ ! -f "$WORK_DIR/$ISO_NAME" ]; then
    wget -c "$ISO_URL" -O "$WORK_DIR/$ISO_NAME"
else
    echo "   ISO already exists, skipping download."
fi

# 2. EXTRACT ISO
echo "📂 Step 2: Extracting ISO..."
mkdir -p "$WORK_DIR/iso_content"
# Use 7z or xorriso to extract. We use xorriso-dd-target logic or 7z.
# Assuming 7z is installed (added to Dockerfile).
if [ -z "$(ls -A "$WORK_DIR/iso_content")" ]; then
    7z x "$WORK_DIR/$ISO_NAME" -o"$WORK_DIR/iso_content" -y > /dev/null
else
    echo "   ISO content already extracted."
fi

# 3. UNSQUASH FILESYSTEM
echo "🔓 Step 3: Unsquashing Root Filesystem..."
if [ ! -d "$WORK_DIR/squashfs-root" ]; then
    unsquashfs -d "$WORK_DIR/squashfs-root" "$WORK_DIR/iso_content/casper/ubuntu-server-minimal.squashfs"
else
    echo "   Filesystem already unsquashed."
fi

# 4. INJECT LOOOP CORE
echo "💉 Step 4: Injecting LooP Core..."
CHROOT_DIR="$WORK_DIR/squashfs-root"

# Copy Repository
echo "   Copying repository to chroot..."
# We exclude .git and large build artifacts to keep ISO small
mkdir -p "$CHROOT_DIR/opt/loop_install_src"
rsync -a --exclude '.git' --exclude 'tools/remaster/build' "$REPO_ROOT/" "$CHROOT_DIR/opt/loop_install_src/"

# Copy DNS for network access
cp /etc/resolv.conf "$CHROOT_DIR/etc/resolv.conf"

# 5. CHROOT EXECUTION
echo "🔧 Step 5: executing setup inside Chroot..."

# Mount bind points
mount --bind /proc "$CHROOT_DIR/proc"
mount --bind /sys "$CHROOT_DIR/sys"
mount --bind /dev "$CHROOT_DIR/dev"

# Execute setup script
# We enter the chroot, go to the src dir, and run setup_loop.sh
chroot "$CHROOT_DIR" /bin/bash -c "cd /opt/loop_install_src && ./install/setup_loop.sh"

# Cleanup Chroot
echo "   Cleaning up Chroot..."
umount "$CHROOT_DIR/proc"
umount "$CHROOT_DIR/sys"
umount "$CHROOT_DIR/dev"

# Remove installer source (optional, but saves space. setup_loop.sh copies to /opt/loop)
rm -rf "$CHROOT_DIR/opt/loop_install_src"
# Restore resolv.conf (symlink usually)
rm "$CHROOT_DIR/etc/resolv.conf"
ln -sf /run/systemd/resolve/stub-resolv.conf "$CHROOT_DIR/etc/resolv.conf"


# 6. RESQUASH
echo "📦 Step 6: Repacking Filesystem..."
chmod +w "$WORK_DIR/iso_content/casper/ubuntu-server-minimal.squashfs"
rm "$WORK_DIR/iso_content/casper/ubuntu-server-minimal.squashfs"
mksquashfs "$CHROOT_DIR" "$WORK_DIR/iso_content/casper/filesystem.squashfs" -noappend -comp xz

# Note: We renamed it to filesystem.squashfs because Live boot usually expects that name
# for standard desktop live, though server uses different naming.
# We will verify GRUB config points to this file.

# 7. UPDATE BOOT CONFIG (GRUB)
echo "⚙️  Step 7: Updating GRUB..."
cp tools/remaster/grub.cfg "$WORK_DIR/iso_content/boot/grub/grub.cfg"

# 8. REPACK ISO
echo "💿 Step 8: Generating LooP ISO..."
# These flags are standard for xorriso repacking of UEFI/BIOS hybrid ISOs
xorriso -as mkisofs \
  -r -V "LooP OS v2.0" \
  -J -joliet-long \
  -b boot/grub/i386-pc/eltorito.img \
  -c boot.catalog \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  -eltorito-alt-boot \
  -e boot/grub/efi.img \
  -no-emul-boot -isohybrid-gpt-basdat \
  -o "$OUT_DIR/loop-os-v2.0.iso" \
  "$WORK_DIR/iso_content"

echo "✅ Build Complete: $OUT_DIR/loop-os-v2.0.iso"
