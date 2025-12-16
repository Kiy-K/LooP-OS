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
    --archive-areas "main contrib non-free-firmware" \
    --bootappend-live "boot=live components quiet splash" \
    --debian-installer live

# Prepare directory structure for chroot inclusions
echo "Preparing chroot includes..."
mkdir -p config/includes.chroot/opt/fyodoros

# Copy source code to the build environment
# We use -a to preserve attributes and include hidden files
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

# 2. Install Python and build dependencies
# We need these to compile extensions and run pip
# We also include standard system utilities that might be useful
apt-get install -y \
    python3-pip \
    python3-full \
    build-essential \
    python3-dev \
    git \
    patchelf \
    scons \
    curl \
    wget

# 3. Install FyodorOS
echo "Installing FyodorOS package..."
cd /opt/fyodoros

# Install build dependencies manually first to ensure they are available for setup
# Using --break-system-packages because we are in a dedicated ISO environment
pip install pybind11 nuitka scons --break-system-packages

# Install the package itself
pip install . --break-system-packages

# 4. Cleanup to reduce ISO size
apt-get clean

echo "FyodorOS Installation Hook: Complete."
EOF

chmod +x "$HOOK_FILE"

# Build the ISO
echo "Building ISO image... This may take a while."
lb build

# Verify and move the artifact
if [ -f "live-image-amd64.hybrid.iso" ]; then
    echo "Build successful. Moving artifact to $OUTPUT_FILE..."
    # Ensure output directory exists (it should, as it's a mount)
    mkdir -p "$(dirname "$OUTPUT_FILE")"
    cp live-image-amd64.hybrid.iso "$OUTPUT_FILE"
    echo "ISO created successfully at: $OUTPUT_FILE"

    # Verify file existence and size
    ls -lh "$OUTPUT_FILE"
else
    echo "Error: ISO file was not generated!"
    ls -la
    exit 1
fi
