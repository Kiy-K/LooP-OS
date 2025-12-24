#!/bin/bash
set -e

# ----------------------------------------------------------------------
# LOOP OS INSTALLER (Formerly LooP)
# Transforms a standard Linux install into LooP OS.
# Supports Interactive (sudo), Unattended (Cloud-Init), and Chroot (Remaster).
# ----------------------------------------------------------------------

# 1. CHECKS
if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root."
  exit 1
fi

if [ ! -f "pyproject.toml" ]; then
  echo "❌ Error: Please run from the repository root."
  exit 1
fi

# Detect Chroot Environment
IS_CHROOT=false
if [ -r /proc/1/root ]; then
    if [ "$(stat -c %d:%i /)" != "$(stat -c %d:%i /proc/1/root)" ]; then
        IS_CHROOT=true
        echo "🔧 Chroot environment detected."
    fi
fi
# Fallback check
if [ "$IS_CHROOT" = false ] && [ -f /.dockerenv ]; then
   # Treat docker build as a chroot-like environment for service handling
   IS_CHROOT=true
   echo "🔧 Container environment detected."
fi


# 2. USER DETERMINATION & CREATION
if [ "$IS_CHROOT" = true ]; then
    # In chroot/remaster, we target the future 'ubuntu' or 'loop' user.
    # Standard Live ISOs use 'ubuntu'.
    # We will assume 'ubuntu' for Live session compatibility.
    TARGET_USER="ubuntu"
    echo "💿 Remaster mode. Target User: $TARGET_USER"
    # Note: 'ubuntu' user might not exist yet in chroot base, handled by casper.
    # We will skip user creation and rely on casper or create a default if needed.
elif [ -n "$SUDO_USER" ]; then
    TARGET_USER="$SUDO_USER"
    echo "✅ Detected interactive mode. Target User: $TARGET_USER"
else
    TARGET_USER="loop"
    echo "🤖 Unattended mode detected. Target User: $TARGET_USER"

    # Check if user exists
    if id "$TARGET_USER" &>/dev/null; then
        echo "   User '$TARGET_USER' already exists."
    else
        echo "   Creating user '$TARGET_USER'..."
        useradd -m -s /bin/bash -G sudo "$TARGET_USER"
        echo "$TARGET_USER:loop" | chpasswd
        echo "   User created and added to sudo group."
    fi
fi

# Create loop group if not exists for Polkit rules
if ! getent group loop >/dev/null; then
    groupadd loop
fi
# Add target user to loop group
usermod -aG loop "$TARGET_USER" || echo "Warning: Could not add user to loop group in chroot."


# 3. DEPENDENCIES
echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-tk \
    libwebkit2gtk-4.0-37 \
    openbox \
    lightdm \
    rxvt-unicode \
    git \
    cmake \
    python3-pybind11 \
    build-essential \
    patchelf \
    ccache \
    casper \
    discover \
    laptop-detect \
    policykit-1 \
    dbus-user-session

# 4. CORE INSTALL
echo "🚀 Installing LooP OS..."

# Clean previous install if exists
rm -rf /opt/loop
mkdir -p /opt/loop

# Copy source to /opt/loop
echo "   Copying source to /opt/loop..."
cp -r . /opt/loop/

# Set permissions
chown -R root:root /opt/loop
chmod -R 755 /opt/loop

# Build & Install
cd /opt/loop

echo "   Building C++ extensions..."
python3 setup_extensions.py install

echo "   Installing Python package..."
pip install .

# 5. LINUX SESSION ARCHITECTURE DEPLOYMENT

echo "🖥️  Deploying Session Artifacts..."

# 5.1 Binaries & Scripts
echo "   Installing scripts..."
cp src/loop/scripts/loop-session.sh /usr/local/bin/loop-session
cp src/loop/scripts/loop-ui /usr/local/bin/loop-ui
chmod +x /usr/local/bin/loop-session
chmod +x /usr/local/bin/loop-ui

# 5.2 Session Definition (LightDM)
echo "   Installing Desktop Entry..."
mkdir -p /usr/share/xsessions
cp install/resources/usr/share/xsessions/loop.desktop /usr/share/xsessions/

# 5.3 Systemd Brain Service
echo "   Installing Systemd User Unit..."
mkdir -p /usr/lib/systemd/user
cp install/resources/usr/lib/systemd/user/loop-brain.service /usr/lib/systemd/user/
# Note: User services are enabled per-user or globally via --global.
# We enable it globally for all users.
# if [ "$IS_CHROOT" = false ]; then
#     systemctl --global enable loop-brain.service || true
# fi

# 5.4 Polkit Rules
echo "   Installing Polkit Rules..."
mkdir -p /etc/polkit-1/rules.d
cp install/resources/etc/polkit-1/rules.d/50-loop-agent.rules /etc/polkit-1/rules.d/
chmod 644 /etc/polkit-1/rules.d/50-loop-agent.rules

# 5.5 Openbox Config
# Ensure configuration exists for the session script to load
echo "   Configuring Openbox..."
mkdir -p /etc/xdg/loop
# Create a default rc.xml if not provided (placeholder for now)
if [ ! -f /etc/xdg/loop/openbox_rc.xml ]; then
    if [ -f /etc/xdg/openbox/rc.xml ]; then
        cp /etc/xdg/openbox/rc.xml /etc/xdg/loop/openbox_rc.xml
    else
        # Fallback empty config or rely on openbox defaults
        touch /etc/xdg/loop/openbox_rc.xml
    fi
fi

# 6. USER CONFIGURATION
if [ "$IS_CHROOT" = false ]; then
    TARGET_HOME=$(getent passwd "$TARGET_USER" | cut -d: -f6)
    echo "👤 Initializing user configuration..."
    if [ -d "$TARGET_HOME/.loop" ] || [ -d "$TARGET_HOME/.local/share/loop" ]; then
        echo "   LooP config exists, skipping initialization."
    else
        # Run loop init as target user
        sudo -u "$TARGET_USER" bash -c "export PATH=\$PATH:/usr/local/bin; loop init"
    fi
fi

# 7. SESSION MANAGER CONFIGURATION (LIGHTDM)
echo "💡 Configuring LightDM..."

# Ensure LightDM config directory exists
mkdir -p /etc/lightdm/lightdm.conf.d

# Configure Autologin to use 'loop' session
cat > /etc/lightdm/lightdm.conf.d/50-loop.conf <<EOF
[Seat:*]
autologin-user=$TARGET_USER
autologin-session=loop
user-session=loop
EOF

# Force LightDM as default
echo "   Setting LightDM as default display manager..."
echo "/usr/sbin/lightdm" > /etc/X11/default-display-manager

# Enable LightDM service
if [ "$IS_CHROOT" = true ]; then
    echo "   Enabling LightDM (Chroot Mode)..."
    # Manually link service in chroot where systemctl is unavailable
    ln -sf /lib/systemd/system/lightdm.service /etc/systemd/system/display-manager.service
else
    echo "   Enabling LightDM (Systemd Mode)..."
    systemctl stop gdm3 2>/dev/null || true
    systemctl disable gdm3 2>/dev/null || true
    systemctl enable lightdm
fi

echo "✅ Installation Complete!"
echo "   LooP OS is ready."
