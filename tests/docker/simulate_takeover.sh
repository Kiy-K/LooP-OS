#!/bin/bash
set -e

echo "Simulating FyodorOS Shell Takeover..."

# 1. Create XSession Entry
# This allows the Display Manager (if present) to choose Fyodor
mkdir -p /usr/share/xsessions
cat <<EOF > /usr/share/xsessions/fyodor.desktop
[Desktop Entry]
Name=FyodorOS
Comment=The Operating System for AI Agents
Exec=/usr/local/bin/fyodor start
Type=Application
EOF
echo "[OK] Created /usr/share/xsessions/fyodor.desktop"

# 2. Configure Autostart (Soft Takeover for Webtop/XFCE)
# Webtop runs as user 'abc' usually, home is /config or /home/abc
# We target the 'abc' user if it exists, otherwise current user
TARGET_HOME="/config"
if [ ! -d "$TARGET_HOME" ]; then
    TARGET_HOME="$HOME"
fi

AUTOSTART_DIR="$TARGET_HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat <<EOF > "$AUTOSTART_DIR/fyodor.desktop"
[Desktop Entry]
Type=Application
Name=FyodorOS
Exec=/usr/local/bin/fyodor start
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
echo "[OK] Created $AUTOSTART_DIR/fyodor.desktop"

# 3. Disable XFCE Default Components (Panel, Desktop)
# In a real takeover, we might replace the window manager, but here we just suppress the UI elements
# so Fyodor is the only thing visible.
echo "Disabling XFCE panels and desktop..."

# Option A: Mask the executables (Aggressive, but effective for a test container)
chmod -x /usr/bin/xfce4-panel || true
chmod -x /usr/bin/xfdesktop || true

# Option B: Remove from session (Cleaner, but harder to do without running DBUS session)
# We rely on Option A for the Kiosk container.

echo "[OK] XFCE components disabled."
echo "Takeover simulation setup complete. Restart container to apply."
