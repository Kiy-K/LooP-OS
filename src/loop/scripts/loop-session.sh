#!/bin/bash
# src/loop/scripts/loop-session.sh
# The Session Orchestrator for LooP OS

# 1. Environment Setup
if [ -f "$HOME/.config/loop/env" ]; then
    source "$HOME/.config/loop/env"
fi

# Ensure PATH includes loop
export PATH=$PATH:/usr/local/bin

# 2. Start/Check Kernel (Brain)
# Try to start systemd service
if systemctl --user is-active --quiet loop-brain.service; then
    echo "[LooP Session] Brain is already running."
else
    echo "[LooP Session] Starting Brain..."
    systemctl --user start loop-brain.service || \
    loop kernel start --daemon &
fi

# 3. Window Manager (Face)
# We execute Openbox directly, which replaces this script as the session leader.
# The startup command launches the UI wrapper.
exec openbox --config-file /etc/xdg/loop/openbox_rc.xml --startup "/usr/local/bin/loop-ui"
