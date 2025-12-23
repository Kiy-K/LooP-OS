#!/bin/bash
set -e

# ----------------------------------------------------------------------
# LOOP OS UNINSTALLER
# Reverts changes made by setup_loop.sh
# ----------------------------------------------------------------------

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Please run as root."
  exit 1
fi

echo "🗑️  Uninstalling LooP OS..."

# 1. REMOVE ARTIFACTS
echo "   Removing /opt/loop..."
rm -rf /opt/loop

echo "   Removing /usr/local/bin/loop..."
rm -f /usr/local/bin/loop

# 2. RESTORE OPENBOX CONFIG
OPENBOX_AUTOSTART="/etc/xdg/openbox/autostart"
if [ -f "$OPENBOX_AUTOSTART.bak" ]; then
    echo "   Restoring Openbox autostart backup..."
    mv "$OPENBOX_AUTOSTART.bak" "$OPENBOX_AUTOSTART"
else
    echo "   Removing Openbox autostart (no backup found)..."
    rm -f "$OPENBOX_AUTOSTART"
fi

# 3. RESTORE LIGHTDM CONFIG
echo "   Removing LightDM configuration..."
rm -f /etc/lightdm/lightdm.conf.d/50-loop.conf

# 4. REVERT DISPLAY MANAGER
# Check if GDM3 is available (common Ubuntu default)
if [ -f "/usr/sbin/gdm3" ]; then
    echo "   Reverting to GDM3..."
    echo "/usr/sbin/gdm3" > /etc/X11/default-display-manager

    # Attempt to use systemctl only if running
    if systemctl is-system-running 2>/dev/null; then
        systemctl disable lightdm
        systemctl enable gdm3
    else
         # Fallback for chroot/offline
         ln -sf /lib/systemd/system/gdm3.service /etc/systemd/system/display-manager.service
    fi
else
    echo "⚠️  GDM3 not found. Leaving LightDM enabled but unconfigured."
fi

# NOTE: We intentionally DO NOT remove the 'loop' user or their home directory
# to preserve user data and avoid accidental deletion of important files.

echo "✅ Uninstall Complete."
