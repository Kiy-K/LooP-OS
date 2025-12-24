# kernel/plugins/loader.py
"""
Plugin Loader System.

This module handles the dynamic loading and initialization of plugins
from the `~/.loop/plugins/` directory.
"""

import sys
import importlib.util
import json
from pathlib import Path

class PluginLoader:
    """
    Manages loading of installed plugins.
    """
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.plugins_dir = Path.home() / ".loop" / "plugins"
        self.loaded_plugins = {}

    def load_all_plugins(self, agent):
        """
        Iterates through the plugin directory and loads all valid plugins.

        Args:
            agent (ReActAgent): The agent instance to register tools with.
        """
        if not self.plugins_dir.exists():
            return

        for entry in self.plugins_dir.iterdir():
            if entry.is_dir():
                manifest_path = entry / "manifest.json"
                if manifest_path.exists():
                    try:
                        self._load_plugin(entry, manifest_path, agent)
                    except Exception as e:
                        print(f"[PluginLoader] Failed to load {entry.name}: {e}")

    def _load_plugin(self, plugin_dir: Path, manifest_path: Path, agent):
        """
        Loads a single plugin.
        """
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        name = manifest.get("name", plugin_dir.name)
        entrypoint = manifest.get("entrypoint", "main.py")
        permissions = manifest.get("permissions", [])

        # Security Checks
        if "motor" in permissions or "filesystem" in permissions or "network" in permissions:
            print(f"[PluginLoader] WARNING: Plugin '{name}' requests high-risk permissions: {permissions}")
            # In v1.1.0 we just log; v1.2.0 will prompt user.

        # Dependency Injection
        dependencies_dir = plugin_dir / "dependencies"
        if dependencies_dir.exists():
            sys.path.insert(0, str(dependencies_dir))

        # Import Module
        module_path = plugin_dir / entrypoint
        if not module_path.exists():
            print(f"[PluginLoader] Entrypoint {entrypoint} not found for {name}")
            return

        spec = importlib.util.spec_from_file_location(f"loop_plugin_{name}", module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"loop_plugin_{name}"] = module
        spec.loader.exec_module(module)

        # Register
        if hasattr(module, "register"):
            module.register(agent)
            self.loaded_plugins[name] = module
            print(f"[PluginLoader] Loaded and registered plugin: {name}")
        else:
            print(f"[PluginLoader] Plugin {name} has no register() function.")

    def list_loaded_plugins(self):
        """
        Returns a list of loaded plugin names.
        """
        return list(self.loaded_plugins.keys())
