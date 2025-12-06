import json
import os
from pathlib import Path

class PluginRegistry:
    """
    Manages the enabled/disabled state of plugins.
    Config is stored in ~/.fyodor/plugins/config.json
    """
    def __init__(self):
        self.config_dir = Path.home() / ".fyodor" / "plugins"
        self.config_file = self.config_dir / "config.json"
        self.enabled_plugins = set()
        self._load()

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    self.enabled_plugins = set(data.get("enabled", []))
            except Exception as e:
                print(f"[PluginRegistry] Error loading config: {e}")
                self.enabled_plugins = set()
        else:
            self.enabled_plugins = set()

    def _save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, "w") as f:
                json.dump({"enabled": list(self.enabled_plugins)}, f, indent=2)
        except Exception as e:
            print(f"[PluginRegistry] Error saving config: {e}")

    def activate(self, plugin_name):
        if plugin_name not in self.enabled_plugins:
            self.enabled_plugins.add(plugin_name)
            self._save()
            return True
        return False

    def deactivate(self, plugin_name):
        if plugin_name in self.enabled_plugins:
            self.enabled_plugins.remove(plugin_name)
            self._save()
            return True
        return False

    def is_active(self, plugin_name):
        return plugin_name in self.enabled_plugins

    def list_plugins(self):
        return list(self.enabled_plugins)
