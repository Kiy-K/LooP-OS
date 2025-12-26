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
# Use xorriso to extract everything including hidden boot images
xorriso -osirrox on -indev "$ISO_NAME" -extract / "$EXTRACT_DIR"

# Fix permissions to ensure xorriso can read everything later
chmod -R +rw "$EXTRACT_DIR"

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

# 2. Inject Source Code (Temporary Location)
echo "Injecting Source Code..."
mkdir -p "$CHROOT_DIR/tmp/loop_source"
# cp -r is safer than cp -a for cross-filesystem copies in docker mounts
cp -r "$INPUT_DIR"/. "$CHROOT_DIR/tmp/loop_source/"
if [ ! -f "$CHROOT_DIR/tmp/loop_source/pyproject.toml" ]; then
    echo "Error: pyproject.toml not found in injected source!"
    ls -la "$CHROOT_DIR/tmp/loop_source/"
    exit 1
fi

# 3. Inject Installer Script (Copy for explicit reference if needed, but we use in-source)
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
# CRITICAL: We MUST be inside the source directory for the script to detect pyproject.toml
cd /tmp/loop_source
echo "DEBUG: Current Directory in Chroot: \$(pwd)"
ls -la
./install/setup_loop.sh

echo "--> Installing Live Boot Components (CRITICAL)..."
# These are required for the ISO to boot as a Live USB
apt-get install -y casper lupin-casper network-manager

echo "--> Cleaning up..."
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f /tmp/install.sh
rm -rf /tmp/loop_source
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

# Dynamic Boot Image Discovery
echo "Locating Boot Images..."
# Debug listing
find "$EXTRACT_DIR/boot" -maxdepth 4 -name "*.img" || echo "No .img files in boot/"

EFI_IMG_PATH=$(find "$EXTRACT_DIR" -name "efi.img" | head -n 1)
ELTORITO_IMG_PATH=$(find "$EXTRACT_DIR" -name "eltorito.img" | head -n 1)

# Fallbacks for standard Ubuntu paths if find fails (relative to extract dir)
if [ -z "$EFI_IMG_PATH" ]; then
    echo "Warning: efi.img not found via find. Checking standard path..."
    if [ -f "$EXTRACT_DIR/boot/grub/efi.img" ]; then
        EFI_IMG_REL="boot/grub/efi.img"
    else
        echo "Error: Critical Boot Image 'efi.img' missing."
        ls -R "$EXTRACT_DIR/boot"
        exit 1
    fi
else
    # Make relative to EXTRACT_DIR
    EFI_IMG_REL=${EFI_IMG_PATH#$EXTRACT_DIR/}
    # Remove leading slash if present
    EFI_IMG_REL=${EFI_IMG_REL#/}
fi

# Ensure EFI image is a file, not a symlink (xorriso requirement for -e sometimes)
if [ -L "$EXTRACT_DIR/$EFI_IMG_REL" ]; then
    echo "Resolving symlink for EFI Image..."
    cp --remove-destination "$(realpath "$EXTRACT_DIR/$EFI_IMG_REL")" "$EXTRACT_DIR/$EFI_IMG_REL"
fi

if [ -z "$ELTORITO_IMG_PATH" ]; then
    echo "Warning: eltorito.img not found via find. Checking standard path..."
    if [ -f "$EXTRACT_DIR/boot/grub/i386-pc/eltorito.img" ]; then
        ELTORITO_IMG_REL="boot/grub/i386-pc/eltorito.img"
    else
        echo "Error: Critical Boot Image 'eltorito.img' missing."
        exit 1
    fi
else
    # Make relative
    ELTORITO_IMG_REL=${ELTORITO_IMG_PATH#$EXTRACT_DIR/}
    ELTORITO_IMG_REL=${ELTORITO_IMG_REL#/}
fi

# Ensure El Torito image is a file
if [ -L "$EXTRACT_DIR/$ELTORITO_IMG_REL" ]; then
    echo "Resolving symlink for El Torito Image..."
    cp --remove-destination "$(realpath "$EXTRACT_DIR/$ELTORITO_IMG_REL")" "$EXTRACT_DIR/$ELTORITO_IMG_REL"
fi

echo "Using EFI Image: $EFI_IMG_REL"
ls -l "$EXTRACT_DIR/$EFI_IMG_REL"
file "$EXTRACT_DIR/$EFI_IMG_REL"

echo "Using El Torito Image: $ELTORITO_IMG_REL"
ls -l "$EXTRACT_DIR/$ELTORITO_IMG_REL"
file "$EXTRACT_DIR/$ELTORITO_IMG_REL"

xorriso -as mkisofs \
  -r -V "LooP_OS_22.04" \
  -J -joliet-long \
  -b "$ELTORITO_IMG_REL" \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  --grub2-boot-info \
  -eltorito-alt-boot \
  -e "$EFI_IMG_REL" \
  -no-emul-boot -isohybrid-gpt-basdat \
  -o "$OUTPUT_FILE" \
  "$EXTRACT_DIR"

echo "✅ SUCCESS: ISO Generated at $OUTPUT_FILE"
ls -lh "$OUTPUT_FILE"
