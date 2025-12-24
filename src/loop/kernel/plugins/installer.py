# kernel/plugins/installer.py
"""
Plugin Installer.

This module handles the fetching and installation of plugins from Git repositories.
It supports both direct Git URLs and registry-based lookups.
"""

import os
import subprocess
import sys
import shutil
import requests
import json
from pathlib import Path

REGISTRY_URL = "https://raw.githubusercontent.com/Kiy-K/loop-registry/main/plugins.json"

class PluginInstaller:
    """
    Manages installation and uninstallation of plugins.
    """

    def __init__(self):
        self.plugins_dir = Path.home() / ".loop" / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def install_plugin(self, name_or_url: str) -> dict:
        """
        Installs a plugin.

        Args:
            name_or_url (str): The name of the plugin (for registry lookup) or a direct Git URL.

        Returns:
            dict: {"success": bool, "message": str}
        """
        if name_or_url.startswith("http"):
            # Direct Git URL
            repo_url = name_or_url
            plugin_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        else:
            # Registry Lookup
            plugin_name = name_or_url
            repo_url = self._lookup_registry(plugin_name)
            if not repo_url:
                return {"success": False, "message": f"Plugin '{plugin_name}' not found in registry."}

        target_dir = self.plugins_dir / plugin_name

        if target_dir.exists():
            return {"success": False, "message": f"Plugin '{plugin_name}' is already installed."}

        try:
            # 1. Git Clone
            subprocess.check_call(
                ["git", "clone", repo_url, str(target_dir)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 2. Install Dependencies
            requirements_file = target_dir / "requirements.txt"
            dependencies_dir = target_dir / "dependencies"

            if requirements_file.exists():
                dependencies_dir.mkdir(exist_ok=True)
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "--target", str(dependencies_dir)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            return {"success": True, "message": f"Plugin '{plugin_name}' installed successfully."}

        except subprocess.CalledProcessError as e:
            # Cleanup on failure
            if target_dir.exists():
                shutil.rmtree(target_dir)
            return {"success": False, "message": f"Installation failed: {e}"}
        except Exception as e:
             if target_dir.exists():
                shutil.rmtree(target_dir)
             return {"success": False, "message": f"Error: {e}"}

    def uninstall_plugin(self, name: str) -> dict:
        """
        Uninstalls a plugin.

        Args:
            name (str): The name of the plugin directory to remove.

        Returns:
             dict: {"success": bool, "message": str}
        """
        target_dir = self.plugins_dir / name

        if not target_dir.exists():
            return {"success": False, "message": f"Plugin '{name}' not found."}

        try:
            shutil.rmtree(target_dir)
            return {"success": True, "message": f"Plugin '{name}' uninstalled."}
        except Exception as e:
            return {"success": False, "message": f"Error uninstalling '{name}': {e}"}

    def _lookup_registry(self, name: str) -> str:
        """
        Fetches the registry and finds the URL for a plugin name.
        """
        try:
            response = requests.get(REGISTRY_URL, timeout=10)
            if response.status_code == 200:
                registry = response.json()
                # Assuming registry structure: {"plugins": {"name": "url", ...}} or [{"name": "...", "url": "..."}]
                # Let's assume a simple mapping for now based on common patterns, or a list.
                # If it's a list:
                if isinstance(registry, list):
                     for p in registry:
                         if p.get("name") == name:
                             return p.get("url")
                elif isinstance(registry, dict):
                    # Check if 'plugins' key exists or direct mapping
                    plugins = registry.get("plugins", registry)
                    if name in plugins:
                        if isinstance(plugins[name], dict):
                            return plugins[name].get("url")
                        return plugins[name]
            return None
        except Exception as e:
            print(f"Registry lookup failed: {e}")
            return None
