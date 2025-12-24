#!/bin/bash
set -e

echo "=== FORCING RUNTIME DEPENDENCIES ==="
# GitHub Actions cache might be stale. We force install critical tools here.
apt-get update
apt-get install -y syslinux-utils xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools python3-pip python3-venv patchelf
pip install nuitka
echo "===================================="

# FORCE PATH EXPORT
export PATH=$PATH:/usr/bin:/usr/sbin:/root/.cargo/bin

INPUT_DIR="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <input_dir> <output_file>"
    exit 1
fi

echo "Starting LooP ISO build (Ubuntu 22.04 / GRUB)..."
echo "Input Directory: $INPUT_DIR"
echo "Output File: $OUTPUT_FILE"

# === PHASE 1: COMPILE GUI ===
echo "Phase 1: Compiling Frontend (React + Tauri)..."

# Create a temporary workspace for compilation
# We copy input files to avoid modifying the mounted source volume
COMPILE_DIR="/tmp/compile_gui"
mkdir -p "$COMPILE_DIR"
cp -r "$INPUT_DIR"/gui "$COMPILE_DIR"/
cp -r "$INPUT_DIR"/src "$COMPILE_DIR"/  # Tauri needs python source for sidecar? Or maybe not.
# Actually Tauri build uses 'gui' directory.

# Install Dependencies
cd "$COMPILE_DIR/gui"
echo "Installing Node dependencies..."
pnpm install || npm install

# Compile LooP Kernel (Sidecar)
echo "Compiling LooP Kernel for Sidecar..."
cd "$COMPILE_DIR"
# The source files are in $COMPILE_DIR/src
# Compile cli.py to a standalone binary
python3 -m nuitka --standalone --onefile --output-filename=loop-kernel.bin src/loop/cli.py

# Place Sidecar
echo "Placing Sidecar binary..."
# Create target directory in the gui build tree
mkdir -p gui/src-tauri/bin
# Move and Rename with the Target Triple (Critical for Tauri)
# Assuming building on x86_64 linux
cp loop-kernel.bin gui/src-tauri/bin/loop-kernel-x86_64-unknown-linux-gnu

# Generate Dummy Icons
echo "Generating dummy icons..."
mkdir -p gui/src-tauri/icons

# 1x1 Transparent PNG Base64
ICON_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="

echo "$ICON_B64" | base64 -d > gui/src-tauri/icons/32x32.png
echo "$ICON_B64" | base64 -d > gui/src-tauri/icons/128x128.png
echo "$ICON_B64" | base64 -d > gui/src-tauri/icons/icon.png
# Copy png to ico/icns just to satisfy file existence checks (Tauri might warn but proceed)
cp gui/src-tauri/icons/icon.png gui/src-tauri/icons/icon.ico
cp gui/src-tauri/icons/icon.png gui/src-tauri/icons/icon.icns

# Return to GUI directory
cd "$COMPILE_DIR/gui"

# Build Frontend
echo "Building React Frontend..."
npm run build

# Build Tauri App
echo "Building Tauri Application..."
# We need to ensure the binary name matches. Assuming "loop-desktop" from instructions.
# If tauri.conf.json identifier is different, this might output elsewhere.
npm run tauri build

# Verify artifact
TAURI_BIN="$COMPILE_DIR/gui/src-tauri/target/release/loop-desktop"
if [ ! -f "$TAURI_BIN" ]; then
    # Fallback check for default 'app' or other name if instruction was slightly off config
    TAURI_BIN=$(find "$COMPILE_DIR/gui/src-tauri/target/release" -maxdepth 1 -type f -executable | head -n 1)
fi

if [ -f "$TAURI_BIN" ]; then
    echo "Tauri binary built successfully: $TAURI_BIN"
else
    echo "Error: Tauri compilation failed. Binary not found."
    ls -R src-tauri/target/release
    exit 1
fi

# === PHASE 2: BUILD ISO ===
cd /build

# Clean up any previous builds
echo "Cleaning previous builds..."
lb clean

# Configure the live system
echo "Configuring live-build..."
lb config \
    --mode ubuntu \
    --distribution jammy \
    --architectures amd64 \
    --linux-flavours generic \
    --archive-areas "main universe restricted multiverse" \
    --mirror-bootstrap "http://archive.ubuntu.com/ubuntu" \
    --mirror-binary "http://archive.ubuntu.com/ubuntu" \
    --bootappend-live "boot=live components quiet splash" \
    --binary-images iso \
    --bootloader grub-efi

# Prepare package lists
echo "Creating package list..."
mkdir -p config/package-lists
cat <<EOF > config/package-lists/loop.list.chroot
live-boot
live-config
live-config-systemd
# GRUB / EFI Support
grub-efi-amd64-bin
grub-pc-bin
grub-efi
mtools
dosfstools
# Python / Build
python3-pip
python3-full
build-essential
python3-dev
python3-setuptools
cmake
python3-pybind11
git
patchelf
scons
curl
wget
# GUI / X11
python3-tk
libwebkit2gtk-4.0-37
libwebkit2gtk-4.1-0
rxvt-unicode
x11-utils
htop
xorg
openbox
lightdm
policykit-1
dbus-user-session
EOF

# Prepare directory structure for chroot inclusions
echo "Preparing chroot includes..."
mkdir -p config/includes.chroot/opt/loop
mkdir -p config/includes.chroot/usr/local/bin

# Copy compiled GUI binary
echo "Injecting Loop Desktop Binary..."
cp "$TAURI_BIN" config/includes.chroot/usr/local/bin/loop-desktop
chmod +x config/includes.chroot/usr/local/bin/loop-desktop

# Copy source code to the build environment (for kernel/scripts)
echo "Copying source code to /opt/loop..."
cp -a "$INPUT_DIR"/. config/includes.chroot/opt/loop/

# Create the installation hook
echo "Creating installation hook..."
mkdir -p config/hooks/normal
HOOK_FILE="config/hooks/normal/050-install-loop.chroot"

cat <<EOF > "$HOOK_FILE"
#!/bin/sh
set -e

echo "LooP Installation Hook: Starting..."

# 1. Update package lists
apt-get update

# 2. Install LooP
echo "Installing LooP package..."
cd /opt/loop

# Install build dependencies
pip install pybind11 nuitka scons --break-system-packages

# CRITICAL FIX: Force compatible urllib3
pip install "urllib3<2.4.0" --break-system-packages

# Hack: Remove EXTERNALLY-MANAGED
rm -f /usr/lib/python*/EXTERNALLY-MANAGED

# 2a. Force C++ Compilation
echo "Building and installing C++ extensions..."
if [ -f "setup_extensions.py" ]; then
    python3 setup_extensions.py install
fi

# 2b. Install the package itself
echo "Installing main package..."
pip install . --break-system-packages

# 2c. Run the Installer Script
# This sets up the Session, Systemd, Polkit, etc.
if [ -f "install/setup_loop.sh" ]; then
    echo "Running setup_loop.sh..."
    bash install/setup_loop.sh
else
    echo "Error: setup_loop.sh not found!"
    exit 1
fi

# 4. Plymouth Theme
echo "Setting Boot Splash..."
if [ -f /usr/share/plymouth/themes/ubuntu-text/ubuntu-text.plymouth ]; then
    sed -i 's/Ubuntu/LooP OS/g' /usr/share/plymouth/themes/ubuntu-text/ubuntu-text.plymouth
fi

# 5. Cleanup
apt-get clean

echo "LooP Installation Hook: Complete."
EOF

chmod +x "$HOOK_FILE"

# Configure Openbox Kiosk Mode
echo "Configuring Kiosk Autostart..."
mkdir -p config/includes.chroot/etc/xdg/openbox

# Inject Custom rc.xml
if [ -f "$INPUT_DIR/install/resources/etc/xdg/openbox/rc.xml" ]; then
    echo "Injecting custom rc.xml..."
    cp "$INPUT_DIR/install/resources/etc/xdg/openbox/rc.xml" config/includes.chroot/etc/xdg/openbox/rc.xml
else
    echo "Warning: Custom rc.xml not found!"
fi

cat <<EOF > config/includes.chroot/etc/xdg/openbox/autostart
# Disable power management
xset -dpms
xset s off
xset s noblank

# Set background to black
xsetroot -solid "#000000"

# Launch LooP UI Wrapper
# This script handles the delay and launches loop-desktop
/usr/local/bin/loop-ui &
EOF

chmod +x config/includes.chroot/etc/xdg/openbox/autostart

# Build the ISO
echo "Building ISO image... This may take a while."
lb build

# Post-process verification
echo "Post-processing ISO..."
ISO_NAME=$(ls live-image-*.iso 2>/dev/null | head -n 1)

if [ -n "$ISO_NAME" ] && [ -f "$ISO_NAME" ]; then
    echo "Build successful. Moving artifact $ISO_NAME to $OUTPUT_FILE..."
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    cp "$ISO_NAME" "$OUTPUT_FILE"
    echo "ISO created successfully at: $OUTPUT_FILE"
    ls -lh "$OUTPUT_FILE"
else
    echo "Error: ISO file was not generated!"
    ls -la
    exit 1
fi
