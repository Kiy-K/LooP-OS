"""
App Launcher for LooP.

Handles scanning the host system for applications and launching them.
Uses fuzzy matching to resolve user queries like "open code" to "code.exe".
"""

import os
import sys
import platform
import subprocess
import difflib
import logging
from pathlib import Path

logger = logging.getLogger("loop.kernel.shell.launcher")

class AppLauncher:
    """
    Scans for applications and launches them.
    """

    def __init__(self):
        self.os_type = platform.system()
        self.apps_cache = {} # Map name -> path
        self._scan_apps()

    def _scan_apps(self):
        """
        Scans common locations for applications.
        """
        self.apps_cache = {}

        # 1. Scan PATH (Basic CLI tools)
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        for d in path_dirs:
            if not os.path.exists(d):
                continue
            try:
                # Limit scan to executables
                for f in os.listdir(d):
                    full_path = os.path.join(d, f)
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                        name = f.lower()
                        # Strip extension for key
                        base_name = os.path.splitext(name)[0]
                        self.apps_cache[base_name] = full_path
                        self.apps_cache[name] = full_path # Store full name too
            except Exception:
                continue

        # 2. OS Specific Scans (Start Menu / Applications)
        if self.os_type == "Windows":
            self._scan_windows_apps()
        elif self.os_type == "Darwin":
            self._scan_macos_apps()
        elif self.os_type == "Linux":
            self._scan_linux_apps()

    def _scan_windows_apps(self):
        """
        Scans Start Menu folders.
        """
        # Common Start Menu (All Users)
        common_start = Path(os.environ.get("ProgramData", "C:\\ProgramData")) / "Microsoft/Windows/Start Menu/Programs"
        # User Start Menu
        user_start = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs"

        for root_dir in [common_start, user_start]:
            if not root_dir.exists():
                continue
            for root, dirs, files in os.walk(root_dir):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name = f[:-4].lower() # Remove .lnk
                        # Store the LNK path, letting Windows shell execute it
                        self.apps_cache[name] = os.path.join(root, f)

    def _scan_macos_apps(self):
        """
        Scans /Applications and /System/Applications.
        """
        app_dirs = ["/Applications", "/System/Applications", os.path.expanduser("~/Applications")]
        for d in app_dirs:
            if not os.path.exists(d):
                continue
            try:
                for f in os.listdir(d):
                    if f.endswith(".app"):
                        name = f[:-4].lower()
                        self.apps_cache[name] = os.path.join(d, f)
            except Exception:
                pass

    def _scan_linux_apps(self):
        """
        Scans /usr/share/applications for .desktop files.
        """
        app_dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
        for d in app_dirs:
            if not os.path.exists(d):
                continue
            try:
                for f in os.listdir(d):
                    if f.endswith(".desktop"):
                        name = f[:-8].lower() # Remove .desktop
                        # For Linux, we store just the name (desktop ID)
                        # to be used with `gtk-launch`
                        self.apps_cache[name] = name
            except Exception:
                pass

    def find_app(self, query):
        """
        Fuzzy finds an app by name.

        Args:
            query (str): The app name to search for (e.g., "code", "chrome").

        Returns:
            str: The path to the executable, or None.
        """
        query = query.lower()
        if query in self.apps_cache:
            return self.apps_cache[query]

        # Fuzzy match
        matches = difflib.get_close_matches(query, self.apps_cache.keys(), n=1, cutoff=0.4)
        if matches:
            return self.apps_cache[matches[0]]

        return None

    def launch(self, app_path):
        """
        Launches the application.
        """
        try:
            if self.os_type == "Windows":
                # os.startfile is the correct way to launch .lnk files on Windows
                os.startfile(app_path)
            elif self.os_type == "Darwin":
                # open -a might be better if it's just a name, but for paths "open" works
                subprocess.Popen(["open", app_path])
            elif self.os_type == "Linux":
                # If it's a path (contains /), run it. If not, assume it's a desktop ID for gtk-launch
                if "/" not in app_path:
                     subprocess.Popen(["gtk-launch", app_path])
                else:
                    subprocess.Popen([app_path], start_new_session=True)

            return {"success": True, "message": f"Launched {app_path}"}
        except Exception as e:
            logger.error(f"Failed to launch {app_path}: {e}")
            return {"success": False, "error": str(e)}
