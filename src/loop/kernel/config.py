# src/loop/kernel/config.py
"""
Configuration Loader for LooP.

Handles parsing of 'loop.conf' and provides safe defaults.
"""

import configparser
import os
from typing import Dict, Any

DEFAULT_CONFIG = {
    "kernel": {
        "debug": "false",
        "network_enabled": "true",
        "gui_enabled": "false",
        "log_level": "INFO",
    },
    "filesystem": {
        "mounts": "/tmp,/var/log",
    },
    "security": {
        "rbac_enabled": "true",
    },
}

class ConfigLoader:
    """
    Loads and parses system configuration.
    """

    def __init__(self, config_path: str = "loop.conf"):
        self.config_path = config_path
        self._config = configparser.ConfigParser()
        self._loaded = False

    def load(self) -> Dict[str, Any]:
        """
        Loads the configuration from file. If file is missing, loads defaults.
        """
        if os.path.exists(self.config_path):
            try:
                self._config.read(self.config_path)
                self._loaded = True
            except configparser.Error as e:
                print(f"[Config] Error parsing config file: {e}. Using defaults.")
                self._load_defaults()
        else:
            print(f"[Config] Config file '{self.config_path}' not found. Using defaults.")
            self._load_defaults()

        return self._to_dict()

    def _load_defaults(self):
        """Populates the config parser with default values."""
        self._config.read_dict(DEFAULT_CONFIG)
        self._loaded = True

    def _to_dict(self) -> Dict[str, Any]:
        """Converts the internal ConfigParser to a dictionary."""
        result = {}
        for section in self._config.sections():
            result[section] = dict(self._config.items(section))

        # Ensure defaults are present if sections are missing in the file
        for section, items in DEFAULT_CONFIG.items():
            if section not in result:
                result[section] = items.copy()
            else:
                for key, value in items.items():
                    if key not in result[section]:
                        result[section][key] = value

        return result

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Helper to get a value with a fallback."""
        if not self._loaded:
            self.load()
        return self._config.get(section, key, fallback=fallback)
