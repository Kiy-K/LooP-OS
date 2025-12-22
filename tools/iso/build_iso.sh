#!/bin/bash
set -e

echo "=== FORCING RUNTIME DEPENDENCIES ==="
# GitHub Actions cache might be stale. We force install critical tools here.
apt-get update
apt-get install -y syslinux-utils xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools
echo "===================================="

# FORCE PATH EXPORT
export PATH=$PATH:/usr/bin:/usr/sbin

echo "=== PRE-FLIGHT CHECK ==="
echo "Checking for xorriso..."
which xorriso || echo "WARNING: xorriso not found (Required for GRUB ISO)!"
echo "========================"

INPUT_DIR="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <input_dir> <output_file>"
    exit 1
fi

echo "Starting FyodorOS ISO build (Ubuntu 22.04 / GRUB)..."
echo "Input Directory: $INPUT_DIR"
echo "Output File: $OUTPUT_FILE"

# Ensure we are in the build directory
cd /build

# Clean up any previous builds
echo "Cleaning previous builds..."
lb clean

# Configure the live system
# CRITICAL: Using GRUB-EFI. Ubuntu 22.04 handles hybrid ISOs via xorriso natively.
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
    --binary-images iso-hybrid \
    --bootloader grub-efi

# Prepare package lists
echo "Creating package list..."
mkdir -p config/package-lists
cat <<EOF > config/package-lists/fyodor.list.chroot
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
EOF

# Prepare directory structure for chroot inclusions
echo "Preparing chroot includes..."
mkdir -p config/includes.chroot/opt/fyodoros

# Copy source code to the build environment
echo "Copying source code to /opt/fyodoros..."
cp -a "$INPUT_DIR"/. config/includes.chroot/opt/fyodoros/

# Create the installation hook
echo "Creating installation hook..."
mkdir -p config/hooks/normal
HOOK_FILE="config/hooks/normal/050-install-fyodor.chroot"

cat <<EOF > "$HOOK_FILE"
#!/bin/sh
set -e

echo "FyodorOS Installation Hook: Starting..."

# 1. Update package lists
apt-get update

# 2. Install FyodorOS
echo "Installing FyodorOS package..."
cd /opt/fyodoros

# Install build dependencies
pip install pybind11 nuitka scons --break-system-packages

# CRITICAL FIX: Force compatible urllib3
pip install "urllib3<2.4.0" --break-system-packages

# Hack: Remove EXTERNALLY-MANAGED
rm -f /usr/lib/python*/EXTERNALLY-MANAGED

# 2a. Force C++ Compilation
echo "Building and installing C++ extensions..."
if [ -f "setup_extensions.py" ]; then
    echo "Found setup_extensions.py, executing..."
    python3 setup_extensions.py install
else
    echo "WARNING: setup_extensions.py not found, skipping C++ compilation..."
fi

# 2b. Install the package itself
echo "Installing main package..."
pip install . --break-system-packages

# 2c. Verify C++ Artifacts
echo "Verifying C++ extensions..."
python3 -c "import sandbox_core; print(f'sandbox_core found: {sandbox_core}')" || echo "WARNING: sandbox_core import failed!"
python3 -c "import registry_core; print(f'registry_core found: {registry_core}')" || echo "WARNING: registry_core import failed!"

# 3. Seed Default Configurations
echo "Seeding default configurations..."
export HOME=/tmp/seed_home
mkdir -p \$HOME
/usr/local/bin/fyodor init

# Move the generated .fyodor folder to /etc/skel
mkdir -p /etc/skel
cp -r /tmp/seed_home/.fyodor /etc/skel/

# Cleanup
rm -rf /tmp/seed_home

# 4. Cleanup
apt-get clean

echo "FyodorOS Installation Hook: Complete."
EOF

chmod +x "$HOOK_FILE"

# Configure Openbox Kiosk Mode
echo "Configuring Kiosk Autostart..."
mkdir -p config/includes.chroot/etc/xdg/openbox

cat <<EOF > config/includes.chroot/etc/xdg/openbox/autostart
# Disable power management
xset -dpms
xset s off
xset s noblank

# Launch FyodorOS in urxvt debug terminal
urxvt -geometry 120x40 -e sh -c "/usr/local/bin/fyodor start; bash" &
EOF

chmod +x config/includes.chroot/etc/xdg/openbox/autostart

# Build the ISO
echo "Building ISO image... This may take a while."
lb build

# Post-process verification
echo "Post-processing ISO..."
# Note: We rely on lb build (using xorriso) to handle the hybrid boot record.
# We do NOT run 'isohybrid' manually for GRUB images.
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
