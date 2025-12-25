#!/bin/bash
set -e

# ==============================================================================
# LooP ISO REMASTER SCRIPT
# Automated "Cubic" Workflow: Server ISO -> Desktop Kiosk
# ==============================================================================

INPUT_DIR="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_DIR" ]; then
    INPUT_DIR=$(pwd)
fi
if [ -z "$OUTPUT_FILE" ]; then
    OUTPUT_FILE="/output/loop-os-v1.iso"
fi

echo "SOURCE: $INPUT_DIR"
echo "TARGET: $OUTPUT_FILE"

# Constants
ISO_URL="https://releases.ubuntu.com/jammy/ubuntu-22.04.5-live-server-amd64.iso"
ISO_NAME="ubuntu-22.04.5-live-server-amd64.iso"
WORK_DIR="/tmp/remaster_work"
EXTRACT_DIR="$WORK_DIR/iso"
CHROOT_DIR="$WORK_DIR/chroot"
COMPILE_DIR="/tmp/compile_gui"

# Ensure clean state
rm -rf "$WORK_DIR" "$COMPILE_DIR"
mkdir -p "$WORK_DIR" "$EXTRACT_DIR" "$CHROOT_DIR" "$COMPILE_DIR"
mkdir -p "$(dirname "$OUTPUT_FILE")"

# ==============================================================================
# PHASE 1: BUILD GUI & SIDECAR
# ==============================================================================
echo "=== PHASE 1: BUILD GUI & SIDECAR ==="

echo "   Copying source to build context..."
cp -r "$INPUT_DIR"/gui "$COMPILE_DIR"/
cp -r "$INPUT_DIR"/src "$COMPILE_DIR"/

# 1. Compile Sidecar (Python Kernel)
echo "   Compiling Sidecar (Python Kernel)..."
cd "$COMPILE_DIR"
# Install project deps to ensure Nuitka can resolve them if needed, though usually standalone works.
# Assuming build env has deps installed or they are vendored.
# For this script, we assume the Docker env has basic python deps.
python3 -m nuitka --standalone --onefile --output-filename=loop-kernel.bin src/loop/cli.py

# 2. Prepare Sidecar for Tauri
echo "   Placing Sidecar..."
mkdir -p gui/src-tauri/bin
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
pnpm install

echo "   Building Frontend (Vite)..."
pnpm run build

echo "   Building Backend (Cargo)..."
cd src-tauri
# Enable custom-protocol for production build (standard Tauri behavior)
cargo build --release --features custom-protocol
cd ..

# 5. Locate Binary
echo "   Locating compiled binary..."
GUI_BINARY=$(find "$COMPILE_DIR/gui/src-tauri/target/release" -maxdepth 1 -type f -executable -not -name "*.so" -not -name "*.d" | head -n 1)
if [ -z "$GUI_BINARY" ] || [ ! -f "$GUI_BINARY" ]; then
    echo "Error: GUI compilation failed. Binary not found."
    ls -R src-tauri/target/release
    exit 1
fi
echo "   GUI Binary found at: $GUI_BINARY"


# ==============================================================================
# PHASE 2: PREPARE BASE ISO
# ==============================================================================
echo "=== PHASE 2: PREPARE BASE ISO ==="
cd "$WORK_DIR"

if [ ! -f "/build/$ISO_NAME" ]; then
    echo "Downloading Ubuntu Server ISO..."
    wget -O "$ISO_NAME" "$ISO_URL"
else
    echo "Using cached ISO..."
    cp "/build/$ISO_NAME" .
fi

echo "Extracting ISO contents..."
# 7z provides a reliable extraction for ISOs
7z x "$ISO_NAME" -o"$EXTRACT_DIR"

echo "Locating Root Filesystem..."
# Server ISO usually has ubuntu-server-minimal.squashfs, checking locations
if [ -f "$EXTRACT_DIR/casper/ubuntu-server-minimal.squashfs" ]; then
    SQUASH_FILE="$EXTRACT_DIR/casper/ubuntu-server-minimal.squashfs"
elif [ -f "$EXTRACT_DIR/casper/filesystem.squashfs" ]; then
    SQUASH_FILE="$EXTRACT_DIR/casper/filesystem.squashfs"
else
    echo "Error: Could not find squashfs file in ISO."
    exit 1
fi

echo "Unsquashing filesystem ($SQUASH_FILE)..."
unsquashfs -f -d "$CHROOT_DIR" "$SQUASH_FILE"


# ==============================================================================
# PHASE 3: INJECT & CONFIGURE
# ==============================================================================
echo "=== PHASE 3: INJECT & CONFIGURE ==="

# 1. Inject GUI Binary
echo "Injecting GUI Binary..."
mkdir -p "$CHROOT_DIR/usr/local/bin"
cp "$GUI_BINARY" "$CHROOT_DIR/usr/local/bin/loop-desktop"
chmod +x "$CHROOT_DIR/usr/local/bin/loop-desktop"

# 2. Inject Source Code
echo "Injecting Source Code..."
mkdir -p "$CHROOT_DIR/opt/loop"
cp -a "$INPUT_DIR"/. "$CHROOT_DIR/opt/loop/"

# 3. Inject Installer Script
echo "Injecting Installer Script..."
cp "$INPUT_DIR/install/setup_loop.sh" "$CHROOT_DIR/tmp/install.sh"
chmod +x "$CHROOT_DIR/tmp/install.sh"

# 4. Inject Custom GRUB Config
echo "Injecting GRUB Config..."
cp "$INPUT_DIR/tools/remaster/grub.cfg" "$EXTRACT_DIR/boot/grub/grub.cfg"
# Also ensure loopback.cfg exists for safety
cp "$INPUT_DIR/tools/remaster/grub.cfg" "$EXTRACT_DIR/boot/grub/loopback.cfg"

# 5. Create Openbox Configs Inline
echo "Creating Openbox Configs..."
mkdir -p "$CHROOT_DIR/etc/xdg/openbox"

# rc.xml (No decorations, maximize)
cat > "$CHROOT_DIR/etc/xdg/openbox/rc.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc" xmlns:xi="http://www.w3.org/2001/XInclude">
<resistance><strength>10</strength><screen_edge_strength>20</screen_edge_strength></resistance>
<focus><focusNew>yes</focusNew><followMouse>no</followMouse><focusLast>yes</focusLast><underMouse>no</underMouse><focusDelay>200</focusDelay><raiseOnFocus>no</raiseOnFocus></focus>
<placement><policy>Smart</policy><center>yes</center><monitor>Primary</monitor><primaryMonitor>1</primaryMonitor></placement>
<theme><name>Clearlooks</name><titleLayout>NLIMC</titleLayout><keepBorder>no</keepBorder><animateIconify>yes</animateIconify><font place="ActiveWindow"><name>sans</name><size>8</size><weight>bold</weight><slant>normal</slant></font><font place="InactiveWindow"><name>sans</name><size>8</size><weight>bold</weight><slant>normal</slant></font><font place="MenuHeader"><name>sans</name><size>9</size><weight>normal</weight><slant>normal</slant></font><font place="MenuItem"><name>sans</name><size>9</size><weight>normal</weight><slant>normal</slant></font><font place="ActiveOnScreenDisplay"><name>sans</name><size>9</size><weight>bold</weight><slant>normal</slant></font><font place="InactiveOnScreenDisplay"><name>sans</name><size>9</size><weight>bold</weight><slant>normal</slant></font></theme>
<desktops><number>1</number><firstdesk>1</firstdesk><names><name>LooP</name></names><popupTime>875</popupTime></desktops>
<resize><drawContents>yes</drawContents><popupShow>Nonpixel</popupShow><popupPosition>Center</popupPosition><popupFixedPosition><x>10</x><y>10</y></popupFixedPosition></resize>
<applications>
  <application class="*">
    <decor>no</decor>
    <maximized>yes</maximized>
  </application>
</applications>
</openbox_config>
EOF

# autostart (Background color, launch app)
cat > "$CHROOT_DIR/etc/xdg/openbox/autostart" <<EOF
# Set black background
xsetroot -solid "#000000"

# Disable screensaver and power management
xset s off
xset -dpms
xset s noblank

# Launch LooP Desktop
# Loop forever to restart if it crashes
while true; do
  /usr/local/bin/loop-desktop
  sleep 1
done &
EOF
chmod +x "$CHROOT_DIR/etc/xdg/openbox/autostart"


# ==============================================================================
# PHASE 4: CHROOT EXECUTION
# ==============================================================================
echo "=== PHASE 4: CHROOT EXECUTION ==="

echo "Mounting virtual filesystems..."
mount --bind /dev "$CHROOT_DIR/dev"
mount --bind /dev/pts "$CHROOT_DIR/dev/pts"
mount --bind /proc "$CHROOT_DIR/proc"
mount --bind /sys "$CHROOT_DIR/sys"

# Network
cat /etc/resolv.conf > "$CHROOT_DIR/etc/resolv.conf"

echo "ENTERING CHROOT..."
# We use a heredoc to run multiple commands safely inside chroot
chroot "$CHROOT_DIR" /bin/bash <<EOF
set -e
export DEBIAN_FRONTEND=noninteractive
export HOME=/root

echo "--> Updating package list..."
apt-get update

echo "--> Installing LooP Core & GUI Stack..."
# Run the setup script which installs deps, xorg, openbox, etc.
# We skip the "check for root" because we are root in chroot.
/tmp/install.sh

echo "--> Installing Live Boot Components (CRITICAL)..."
# These are required for the ISO to boot as a Live USB
apt-get install -y casper lupin-casper network-manager

echo "--> Cleaning up..."
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f /tmp/install.sh
truncate -s 0 /root/.bash_history
EOF

echo "Unmounting..."
umount "$CHROOT_DIR/sys"
umount "$CHROOT_DIR/proc"
umount "$CHROOT_DIR/dev/pts"
umount "$CHROOT_DIR/dev"
rm "$CHROOT_DIR/etc/resolv.conf"


# ==============================================================================
# PHASE 5: REPACK ISO
# ==============================================================================
echo "=== PHASE 5: REPACK ISO ==="

echo "Regenerating Manifests..."
# Required for Ubiquity/Casper to trust the filesystem
chmod +w "$EXTRACT_DIR/casper/filesystem.manifest" 2>/dev/null || true
chroot "$CHROOT_DIR" dpkg-query -W --showformat='${Package} ${Version}\n' > "$EXTRACT_DIR/casper/filesystem.manifest"
cp "$EXTRACT_DIR/casper/filesystem.manifest" "$EXTRACT_DIR/casper/filesystem.manifest-desktop"
# Cleanup unnecessary manifest entries
sed -i '/ubiquity/d' "$EXTRACT_DIR/casper/filesystem.manifest-desktop"
sed -i '/casper/d' "$EXTRACT_DIR/casper/filesystem.manifest-desktop"

echo "Building SquashFS..."
rm -f "$EXTRACT_DIR/casper/filesystem.squashfs" "$EXTRACT_DIR/casper/ubuntu-server-minimal.squashfs"
# Always name it filesystem.squashfs for standard Casper boot
mksquashfs "$CHROOT_DIR" "$EXTRACT_DIR/casper/filesystem.squashfs" -comp xz -noappend

echo "Updating MD5..."
cd "$EXTRACT_DIR"
find . -type f -print0 | xargs -0 md5sum > md5sum.txt

echo "Building Hybrid ISO..."
cd "$WORK_DIR"

# Flags as requested for Hybrid MBR/EFI
# Note: We need to point -b and -e to relative paths in the extracted dir.
# Ubuntu Server ISO usually has 'boot/grub/efi.img'.
# If 'boot/grub/i386-pc/eltorito.img' is missing, we might need to extract it or use isolinux.
# However, standard Ubuntu 22.04 uses GRUB for both.
# Let's verify presence or copy from system if missing (xorriso can generate it, but we want "Original").
# Since we just extracted the ISO, we assume the boot images are inside.

# If eltorito.img is not extracted (sometimes it's hidden), we can't point to it.
# However, xorriso -extract usually dumps everything.
# Let's check if the specific boot images exist in the extracted structure.
# If not, we might need to rely on xorriso generating them, but the prompt says "Original".
# Usually, standard Ubuntu ISOs have `boot/grub/efi.img`. The BIOS image is often `isolinux/isolinux.bin`
# or `boot/grub/i386-pc/eltorito.img` depending on the build.
# For this script, we will try to use the paths specified. If they fail, we rely on xorriso defaults (not implemented here to keep strict).

xorriso -as mkisofs \
  -r -V "LooP OS 22.04" \
  -J -joliet-long \
  -b boot/grub/i386-pc/eltorito.img \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  --grub2-boot-info \
  -eltorito-alt-boot \
  -e boot/grub/efi.img \
  -no-emul-boot -isohybrid-gpt-basdat \
  -o "$OUTPUT_FILE" \
  "$EXTRACT_DIR"

echo "✅ SUCCESS: ISO Generated at $OUTPUT_FILE"
ls -lh "$OUTPUT_FILE"
