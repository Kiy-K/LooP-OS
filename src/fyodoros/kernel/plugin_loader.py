import importlib
from fyodoros.plugins.registry import PluginRegistry

class PluginLoader:
    def __init__(self, kernel):
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
        commands = {}
        for plugin in self.loaded_plugins.values():
            commands.update(plugin.get_shell_commands())
        return commands

    def get_all_agent_tools(self):
        tools = []
        for plugin in self.loaded_plugins.values():
            tools.extend(plugin.get_agent_tools())
        return tools
