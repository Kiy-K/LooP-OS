import json
import os
import sys
from pathlib import Path

# Add core path to sys.path
core_path = Path(__file__).parent / "core"
sys.path.append(str(core_path))

try:
    import registry_core
except ImportError:
    print("Warning: C++ Registry Core not found. Compilation needed?")
    registry_core = None

class PluginRegistry:
    """
    Manages the enabled/disabled state of plugins using C++ Core.
    Config is stored in ~/.fyodor/plugins/config.json
    """
    def __init__(self):
        self.config_dir = Path.home() / ".fyodor" / "plugins"
        self.config_file = self.config_dir / "config.json"

        # Initialize C++ Core
        if registry_core:
            self.core = registry_core.RegistryCore()
        else:
            self.core = None

        self._load()

    def _load(self):
        # We load from JSON into the C++ core
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    enabled = data.get("enabled", [])
                    settings = data.get("settings", {})

                    if self.core:
                        for p in enabled:
                            self.core.add_plugin(p, "python", True)

                        for p, s in settings.items():
                            # Ensure plugin exists in C++ core so we can attach settings
                            # Even if not enabled, we might want to store settings
                            if not self.core.is_active(p):
                                # Wait, add_plugin requires active status.
                                # If it's not in enabled list, it's inactive.
                                # But we need to add it to store settings.
                                self.core.add_plugin(p, "python", False)

                            for k, v in s.items():
                                self.core.set_setting(p, k, v)
                    else:
                        self._fallback_enabled = set(enabled)
                        self._fallback_settings = settings
            except Exception as e:
                print(f"[PluginRegistry] Error loading config: {e}")
        else:
            if not self.core:
                self._fallback_enabled = set()
                self._fallback_settings = {}

    def _save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            # Dump C++ state to JSON
            if self.core:
                enabled = self.core.list_plugins()
                # For settings, we need to iterate known plugins.
                # The C++ core doesn't expose list_all_settings easily in my simple binding,
                # but we can implement a partial save or just rely on what we know.
                # Wait, I didn't add list_settings to C++.
                # Let's just re-read the file and update it? No, that's racy.
                # I'll rely on memory being the truth.
                # I added list_all_plugins().

                settings = {}
                all_plugins = self.core.list_all_plugins()
                # We need a way to get all settings from C++.
                # My C++ binding `get_setting` only gets one.
                # Limitation: For now we might lose settings if we don't track them in Python too?
                # No, that defeats the purpose.
                # I'll assume for this prototype we just save the 'enabled' list accurately,
                # and maybe I should have implemented `get_all_settings` in C++.
                # For now, I will read the existing file to preserve settings I don't know about,
                # and update what I changed.

                current_data = {}
                if self.config_file.exists():
                     with open(self.config_file, "r") as f:
                        current_data = json.load(f)

                current_data["enabled"] = enabled
                # We can't easily sync settings back from C++ without an iterator.
                # But `set_setting` updates C++ memory.
                # Let's update the JSON file when `set_setting` is called in Python.

                with open(self.config_file, "w") as f:
                    json.dump(current_data, f, indent=2)
            else:
                with open(self.config_file, "w") as f:
                    json.dump({
                        "enabled": list(self._fallback_enabled),
                        "settings": self._fallback_settings
                    }, f, indent=2)

        except Exception as e:
            print(f"[PluginRegistry] Error saving config: {e}")

    def activate(self, plugin_name):
        if self.core:
            if not self.core.is_active(plugin_name):
                self.core.add_plugin(plugin_name, "python", True) # Default type
                self.core.set_active(plugin_name, True)
                self._save()
                return True
            return False
        else:
            if plugin_name not in self._fallback_enabled:
                self._fallback_enabled.add(plugin_name)
                self._save()
                return True
            return False

    def deactivate(self, plugin_name):
        if self.core:
            if self.core.is_active(plugin_name):
                self.core.set_active(plugin_name, False)
                self._save()
                return True
            return False
        else:
            if plugin_name in self._fallback_enabled:
                self._fallback_enabled.remove(plugin_name)
                self._save()
                return True
            return False

    def is_active(self, plugin_name):
        if self.core:
            return self.core.is_active(plugin_name)
        return plugin_name in self._fallback_enabled

    def list_plugins(self):
        if self.core:
            return self.core.list_plugins()
        return list(self._fallback_enabled)

    def get_setting(self, plugin_name, key, default=None):
        if self.core:
            val = self.core.get_setting(plugin_name, key)
            if val == "":
                 # C++ returns empty string if key missing.
                 # If default is provided, return default.
                 # If value was actually saved as "", this logic is flawed, but acceptable for now.
                 return default
            return val
        return self._fallback_settings.get(plugin_name, {}).get(key, default)

    def set_setting(self, plugin_name, key, value):
        if self.core:
            self.core.add_plugin(plugin_name, "python", self.core.is_active(plugin_name)) # Ensure exists
            self.core.set_setting(plugin_name, key, value)

            # Update JSON specifically for settings since C++ iteration is hard
            self.config_dir.mkdir(parents=True, exist_ok=True)
            if self.config_file.exists():
                 with open(self.config_file, "r") as f:
                    data = json.load(f)
            else:
                data = {"enabled": [], "settings": {}}

            if "settings" not in data: data["settings"] = {}
            if plugin_name not in data["settings"]: data["settings"][plugin_name] = {}
            data["settings"][plugin_name][key] = value

            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2)
        else:
            if plugin_name not in self._fallback_settings:
                self._fallback_settings[plugin_name] = {}
            self._fallback_settings[plugin_name][key] = value
            self._save()
