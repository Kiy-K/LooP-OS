"""
Shell Registrar for FyodorOS.

Handles the registration of FyodorOS as the default system shell.
Includes safety mechanisms like generating restore scripts before modification.
"""

import sys
import os
import platform
import logging
from pathlib import Path

logger = logging.getLogger("fyodoros.kernel.shell.registrar")

class ShellRegistrar:
    """
    Manages setting FyodorOS as the default shell.
    """

    def __init__(self):
        self.os_type = platform.system()
        self.executable_path = sys.executable
        # In Nuitka compiled mode, sys.executable is the binary.
        # In source mode, it's python.

        # If running from source, we probably don't want to register 'python.exe' as shell
        # without arguments, but for now we assume this is run from the compiled binary
        # or the user knows what they are doing.

    def register(self):
        """
        Registers FyodorOS as the default shell for the current OS.
        """
        if self.os_type == "Windows":
            return self._register_windows()
        elif self.os_type == "Linux":
            return self._register_linux()
        elif self.os_type == "Darwin":
            return self._register_macos()
        else:
            return {"success": False, "error": f"Unsupported OS: {self.os_type}"}

    def _register_windows(self):
        """
        Windows Registry modification to set Shell.
        """
        try:
            import winreg
        except ImportError:
            return {"success": False, "error": "winreg module not found"}

        # 1. Generate Safety Script
        desktop = Path(os.path.expanduser("~/Desktop"))
        restore_script = desktop / "fyodor-restore.bat"

        try:
            with open(restore_script, "w") as f:
                f.write("@echo off\n")
                f.write("echo Restoring Windows Shell to Explorer...\n")
                f.write('reg add "HKCU\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon" /v Shell /t REG_SZ /d "explorer.exe" /f\n')
                f.write("echo Done. You may need to sign out and sign back in.\n")
                f.write("pause\n")
            logger.info(f"Created restore script at {restore_script}")
        except Exception as e:
            return {"success": False, "error": f"Failed to create restore script: {e}"}

        # 2. Modify Registry
        key_path = r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Shell", 0, winreg.REG_SZ, self.executable_path)
            winreg.CloseKey(key)
            return {"success": True, "message": "FyodorOS registered as Windows Shell. Sign out to apply."}
        except Exception as e:
            return {"success": False, "error": f"Registry modification failed: {e}"}

    def _register_linux(self):
        """
        Creates a .desktop session file for Linux Display Managers.
        """
        # Target: ~/.local/share/xsessions/fyodor.desktop
        # or /usr/share/xsessions/ (requires root, we stick to user local if possible)

        home = Path.home()
        session_dir = home / ".local" / "share" / "xsessions"
        session_dir.mkdir(parents=True, exist_ok=True)

        desktop_file = session_dir / "fyodor.desktop"

        content = f"""[Desktop Entry]
Name=FyodorOS
Comment=The Operating System for Autonomous AI Agents
Exec={self.executable_path}
Type=Application
"""
        try:
            with open(desktop_file, "w") as f:
                f.write(content)
            return {"success": True, "message": f"Created session file at {desktop_file}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to create session file: {e}"}

    def _register_macos(self):
        """
        macOS registration placeholder.
        """
        # macOS shell replacement is complex and usually requires MDM or Kiosk mode configuration.
        return {"success": False, "error": "macOS shell registration is not fully supported yet."}
