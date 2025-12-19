#!/bin/bash
set -e

INPUT_DIR="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 <input_dir> <output_file>"
    exit 1
fi

echo "Starting FyodorOS ISO build..."
echo "Input Directory: $INPUT_DIR"
echo "Output File: $OUTPUT_FILE"

# Ensure we are in the build directory
cd /build

# Clean up any previous builds
echo "Cleaning previous builds..."
lb clean

# Configure the live system
echo "Configuring live-build..."
lb config \
    --distribution bookworm \
    --architectures amd64 \
    --linux-flavours amd64 \
    --archive-areas "main contrib non-free-firmware" \
    --bootappend-live "boot=live components quiet splash" \
    --binary-images iso-hybrid \
    --bootloader syslinux

# Prepare package lists
echo "Creating package list..."
cat <<EOF > config/package-lists/fyodor.list.chroot
live-boot
live-config
live-config-systemd
syslinux
syslinux-utils
isolinux
python3-pip
python3-full
build-essential
python3-dev
cmake
python3-pybind11
git
patchelf
scons
curl
wget
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

# 2a. Force C++ Compilation (Critical Fix)
echo "Building and installing C++ extensions..."
python3 setup_extensions.py install --break-system-packages

# 2b. Install the package itself
pip install . --break-system-packages

# 2c. Verify C++ Artifacts
echo "Verifying C++ extensions..."
python3 -c "import sandbox_core; print(f'sandbox_core found: {sandbox_core}')" || exit 1
python3 -c "import registry_core; print(f'registry_core found: {registry_core}')" || exit 1

# 3. Seed Default Configurations (Critical Fix for Live User)
echo "Seeding default configurations..."
# Run init to generate the config structure in a temporary location
export HOME=/tmp/seed_home
mkdir -p \$HOME
/usr/local/bin/fyodor init

# Move the generated .fyodor folder to /etc/skel
# This ensures every new user (including the Live User) gets it on login
mkdir -p /etc/skel
cp -r /tmp/seed_home/.fyodor /etc/skel/

# Cleanup
rm -rf /tmp/seed_home

# 4. Cleanup to reduce ISO size
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
# -e runs the command. sh -c allows us to chain commands.
urxvt -geometry 120x40 -e sh -c "/usr/local/bin/fyodor start; bash" &
EOF

chmod +x config/includes.chroot/etc/xdg/openbox/autostart

# Build the ISO
echo "Building ISO image... This may take a while."
lb build

# Post-process verification
echo "Post-processing ISO..."
if [ -f "live-image-amd64.hybrid.iso" ]; then
    echo "Running isohybrid utility..."
    # --partok is safer for USB booting compatibility
    if command -v isohybrid >/dev/null 2>&1; then
        isohybrid --partok live-image-amd64.hybrid.iso
        echo "Hybrid MBR written successfully."
    else
        echo "ERROR: 'isohybrid' command not found! ISO will not be bootable."
        exit 1
    fi
    
    echo "Build successful. Moving artifact to $OUTPUT_FILE..."
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    cp live-image-amd64.hybrid.iso "$OUTPUT_FILE"
    echo "ISO created successfully at: $OUTPUT_FILE"

    ls -lh "$OUTPUT_FILE"
else
    echo "Error: ISO file was not generated!"
    ls -la
    exit 1
fi
