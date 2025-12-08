# kernel/plugin_loader.py
"""
Plugin Loader System.

This module handles the dynamic loading and initialization of plugins.
It interfaces with the `PluginRegistry` to determine which plugins to load
and aggregates commands and tools exposed by them.
"""

import importlib
from fyodoros.plugins.registry import PluginRegistry


class PluginLoader:
    """
    Manages the lifecycle of plugins.

    Attributes:
        kernel (Kernel): The kernel instance to pass to plugins during setup.
        registry (PluginRegistry): The registry for managing plugin state.
        loaded_plugins (dict): A dictionary of loaded plugin instances.
    """
    def __init__(self, kernel):
        """
        Initialize the PluginLoader.

        Args:
            kernel (Kernel): The active kernel instance.
        """
        self.kernel = kernel
        self.registry = PluginRegistry()
        self.loaded_plugins = {}

    def load_active_plugins(self):
        """
        Loads all plugins marked as active in the registry.
        """
        for plugin_name in self.registry.list_plugins():
            self._load_plugin(plugin_name)

    def _load_plugin(self, plugin_name):
        """
        Internal method to load a single plugin by name.

        Args:
            plugin_name (str): The name (module path) of the plugin.
        """
        try:
            # Assume plugin_name is a python module path, e.g. "my_plugin"
            module = importlib.import_module(plugin_name)

            # Look for a 'Plugin' class in the module
            if hasattr(module, "Plugin"):
                plugin_instance = module.Plugin()
                plugin_instance.setup(self.kernel)
                self.loaded_plugins[plugin_name] = plugin_instance
                print(f"[PluginLoader] Loaded {plugin_name}")
            else:
                print(f"[PluginLoader] Error: Module {plugin_name} has no 'Plugin' class.")
        except ImportError as e:
            print(f"[PluginLoader] Error loading {plugin_name}: {e}")
        except Exception as e:
            print(f"[PluginLoader] Error initializing {plugin_name}: {e}")

    def get_all_shell_commands(self):
        """
        Retrieve all shell commands registered by loaded plugins.

        Returns:
            dict: A dictionary mapping command names to handler functions.
        """
        commands = {}
        for plugin in self.loaded_plugins.values():
            commands.update(plugin.get_shell_commands())
        return commands

    def get_all_agent_tools(self):
        """
        Retrieve all agent tools registered by loaded plugins.

        Returns:
            list: A list of tool definitions/functions.
        """
        tools = []
        for plugin in self.loaded_plugins.values():
            tools.extend(plugin.get_agent_tools())
        return tools

    def teardown(self):
        """
        Teardown all loaded plugins.
        """
        for plugin_name, plugin_instance in self.loaded_plugins.items():
            if hasattr(plugin_instance, "teardown"):
                try:
                    plugin_instance.teardown()
                    print(f"[PluginLoader] Teardown {plugin_name}")
                except Exception as e:
                    print(f"[PluginLoader] Error tearing down {plugin_name}: {e}")

        self.loaded_plugins.clear()
