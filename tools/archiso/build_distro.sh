#!/bin/bash
set -e

# ==============================================================================
# LooP ARCH LINUX ISO BUILDER (ROOT-SAFE)
# ==============================================================================

INPUT_DIR="$1"
OUTPUT_DIR="$2"

if [ -z "$INPUT_DIR" ]; then INPUT_DIR=$(pwd); fi
if [ -z "$OUTPUT_DIR" ]; then OUTPUT_DIR="/output"; fi

WORK_DIR="/tmp/archiso-work"
COMPILE_DIR="/tmp/compile_loop"
PROFILE_DIR="$WORK_DIR/loop-profile"

echo "SOURCE: $INPUT_DIR"
echo "OUTPUT: $OUTPUT_DIR"

# Cleanup
rm -rf "$WORK_DIR" "$COMPILE_DIR"
mkdir -p "$WORK_DIR" "$COMPILE_DIR" "$OUTPUT_DIR"

# ==============================================================================
# PHASE 1: COMPILE LOOP (SIDELOAD)
# ==============================================================================
echo "=== PHASE 1: COMPILATION ==="

# Copy source efficiently
echo "--> Copying source..."
mkdir -p "$COMPILE_DIR"
# Use tar to copy excluding .git and output to avoid recursion loops
tar -cf - --exclude='.git' --exclude='output' --exclude='tools/archiso/work' -C "$INPUT_DIR" . | tar -xf - -C "$COMPILE_DIR"

cd "$COMPILE_DIR"

# 1. Compile Kernel (Nuitka)
echo "--> Compiling Kernel..."

# Fix: Unpin Playwright to allow compatibility with Arch's Python 3.13
# The pinned version (1.41.2) pulls in older greenlet/compilation issues on Py3.13
sed -i 's/playwright==1.41.2/playwright/g' pyproject.toml

# Fix: Force Greenlet >= 3.1.1 to support Python 3.13 (fixes _PyCFrame error)
pip install "greenlet>=3.1.1" --break-system-packages

# Install deps if needed (assuming image has them or we install minimal)
# We install '.' to get dependencies and ensure 'loop' is in path
# Use --no-build-isolation to prefer system packages (like python-greenlet)
pip install . --break-system-packages --no-build-isolation

python -m nuitka --standalone --onefile \
    --output-filename=loop-kernel \
    --include-package=loop \
    src/loop/cli.py

if [ ! -f "loop-kernel" ]; then
    echo "Error: loop-kernel compilation failed."
    exit 1
fi

# 2. Prepare GUI
echo "--> Compiling GUI..."
cd gui

# Generate Icons (Critical for Tauri)
mkdir -p src-tauri/icons
ICON_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
echo "$ICON_B64" | base64 -d > src-tauri/icons/32x32.png
echo "$ICON_B64" | base64 -d > src-tauri/icons/128x128.png
echo "$ICON_B64" | base64 -d > src-tauri/icons/icon.png
cp src-tauri/icons/icon.png src-tauri/icons/icon.ico
cp src-tauri/icons/icon.png src-tauri/icons/icon.icns

# Use pnpm (Respect Lockfile)
# We assume pnpm is installed in the builder image
pnpm install
pnpm run build

# Compile Tauri Backend
cd src-tauri
# Inject Sidecar
mkdir -p bin
ARCH=$(uname -m)
if [ "$ARCH" == "x86_64" ]; then TRIPLE="x86_64-unknown-linux-gnu"; else TRIPLE="$ARCH"; fi
cp ../../loop-kernel "bin/loop-kernel-$TRIPLE"

cargo build --release
cd ..

# Locate Binary
GUI_BINARY=$(find "src-tauri/target/release" -maxdepth 1 -type f -executable -not -name "*.so" -not -name "*.d" | head -n 1)
if [ -z "$GUI_BINARY" ]; then
    echo "Error: GUI binary not found."
    exit 1
fi
echo "GUI Binary: $GUI_BINARY"
cp "$GUI_BINARY" ../loop-desktop


# ==============================================================================
# PHASE 2: CONFIGURE ARCHISO (ROOT-SAFE)
# ==============================================================================
echo "=== PHASE 2: ARCHISO CONFIGURATION ==="
cd "$WORK_DIR"

# Copy base profile
cp -r /usr/share/archiso/configs/releng "$PROFILE_DIR"

# 1. Add Packages
echo "--> Configuring Packages..."
cat <<EOF >> "$PROFILE_DIR/packages.x86_64"
xorg-server
xorg-xinit
openbox
lightdm
lightdm-gtk-greeter
rxvt-unicode
python
webkit2gtk
ttf-jetbrains-mono
ttf-font-awesome
sudo
EOF

# 2. Inject Binaries
echo "--> Injecting Binaries..."
mkdir -p "$PROFILE_DIR/airootfs/usr/local/bin"
cp "$COMPILE_DIR/loop-kernel" "$PROFILE_DIR/airootfs/usr/local/bin/"
cp "$COMPILE_DIR/loop-desktop" "$PROFILE_DIR/airootfs/usr/local/bin/"
chmod +x "$PROFILE_DIR/airootfs/usr/local/bin/"*

# 3. Inject Source Code
echo "--> Injecting Source Code..."
mkdir -p "$PROFILE_DIR/airootfs/opt/loop-src"
cp -r "$COMPILE_DIR/src/loop" "$PROFILE_DIR/airootfs/opt/loop-src/"

# 4. Configure User & Boot (Systemd Method)
echo "--> Configuring Boot Services..."

AIROOTFS="$PROFILE_DIR/airootfs"
mkdir -p "$AIROOTFS/etc/systemd/system"

# A. Create Setup Service (First Boot User Creation)
cat <<EOF > "$AIROOTFS/etc/systemd/system/setup-loop-user.service"
[Unit]
Description=Setup LooP User
Before=lightdm.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c "id -u loop || (useradd -m -G wheel loop && echo 'loop:loop' | chpasswd && echo '%wheel ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers)"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# B. Enable Setup Service
mkdir -p "$AIROOTFS/etc/systemd/system/multi-user.target.wants"
ln -sf "/etc/systemd/system/setup-loop-user.service" "$AIROOTFS/etc/systemd/system/multi-user.target.wants/setup-loop-user.service"

# C. Enable LightDM (Display Manager)
# In Arch, enabling a DM is linking it to /etc/systemd/system/display-manager.service
ln -sf "/usr/lib/systemd/system/lightdm.service" "$AIROOTFS/etc/systemd/system/display-manager.service"

# 5. Application Configuration
echo "--> Configuring Session..."

# LightDM Autologin
mkdir -p "$AIROOTFS/etc/lightdm"
cat <<EOF > "$AIROOTFS/etc/lightdm/lightdm.conf"
[Seat:*]
autologin-user=loop
autologin-session=openbox
user-session=openbox
EOF

# Openbox Autostart
mkdir -p "$AIROOTFS/etc/xdg/openbox"
cat <<EOF > "$AIROOTFS/etc/xdg/openbox/autostart"
# Black background
xsetroot -solid "#000000"

# Loop Desktop
# Using a loop to restart if it crashes
while true; do
  /usr/local/bin/loop-desktop
  sleep 1
done &
EOF


# ==============================================================================
# PHASE 3: BUILD ISO
# ==============================================================================
echo "=== PHASE 3: BUILD ISO ==="

mkarchiso -v -w "$WORK_DIR/iso_work" -o "$OUTPUT_DIR" "$PROFILE_DIR"

echo "✅ SUCCESS: ISO Generated in $OUTPUT_DIR"
