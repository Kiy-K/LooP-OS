# Permissions Guide

LooP "Ghost Mode" requires specific permissions to listen for Global Hotkeys and inspect other windows.

## macOS

On macOS, you must grant **Accessibility** permissions to the terminal or application running LooP.

1.  Open **System Settings**.
2.  Go to **Privacy & Security** > **Accessibility**.
3.  Click the **+** button.
4.  Add your Terminal application (e.g., Terminal, iTerm2, VSCode).
5.  Ensure the toggle is **ON**.

*If you are running from source, you may need to re-grant permissions if the Python executable changes.*

### Troubleshooting

If you see `pynput` errors or the listener fails to start:
*   Ensure `pynput` is installed: `pip install pynput`
*   Verify Accessibility permissions are granted.
*   On macOS, `pynput` cannot monitor the keyboard if the "Secure Input" mode is enabled by another application (e.g., a password field is focused).

## Windows

Typically, no special permissions are required if running as a standard user. However, some anti-virus software may flag keyboard hooks.

## Linux

*   **X11:** Should work out of the box.
*   **Wayland:** Global hotkeys are restricted. You may need to use a specific Wayland compositor configuration or switch to X11.
