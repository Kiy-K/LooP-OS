#!/bin/bash
set -e

echo "[FyodorOS] Simulating Kiosk Takeover..."

# 1. Define Session (standard X11 session file)
# This is useful if we were replacing the Display Manager config,
# but for this simulation we rely on autostart mostly.
echo "[FyodorOS] Creating /usr/share/xsessions/fyodor.desktop..."
sudo mkdir -p /usr/share/xsessions
cat <<EOF | sudo tee /usr/share/xsessions/fyodor.desktop
[Desktop Entry]
Name=FyodorOS
Exec=fyodor start
Type=Application
EOF

# 2. Autostart Injection (The "Soft" Takeover)
# Since we are already logged into an XFCE session in Webtop,
# we add Fyodor to the autostart list.
echo "[FyodorOS] Injecting Autostart..."
mkdir -p ~/.config/autostart
cat <<EOF > ~/.config/autostart/fyodor.desktop
[Desktop Entry]
Name=FyodorOS
Exec=fyodor start
Type=Application
Terminal=true
EOF

# 3. Suppress XFCE Panel
# Remove the panel from the session so Fyodor is the primary UI.
# Note: This might fail if xfconfd is not running, so we wrap it.
echo "[FyodorOS] Suppressing XFCE Panel..."
if pgrep -x "xfce4-session" > /dev/null; then
    xfconf-query -c xfce4-session -p /sessions/Failsafe/Client0_Command -r || echo "Warning: Could not remove panel from session (key might not exist)"
    # Also kill existing panel if running
    pkill xfce4-panel || true
else
    echo "XFCE session not detected (or not running yet). Skipping panel suppression."
fi

echo "[FyodorOS] Takeover Configuration Complete."
echo "Please restart the container or the X server to apply changes."
