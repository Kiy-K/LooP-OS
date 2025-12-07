# plugins/__init__.py
"""
Plugin System Interface.

This package defines the base `Plugin` class that all FyodorOS plugins must inherit from.
It provides the standard interface for setup, command registration, and agent tool integration.
"""

from abc import ABC, abstractmethod

class Plugin(ABC):
    """
    Abstract Base Class for FyodorOS plugins.

    All plugins must inherit from this class and implement the `setup` method.
    """
    def __init__(self):
        """
        Initialize the Plugin instance.
        """
        pass

    @abstractmethod
    def setup(self, kernel):
        """
        Called when the plugin is loaded into the kernel.

        Args:
            kernel (Kernel): The active kernel instance. Use this to access system resources.
        """
        pass

    def get_shell_commands(self):
        """
        Register custom shell commands.

        Returns:
            dict: A mapping of command names (str) to handler functions.
                  Example: {"mycmd": self.handle_mycmd}
        """
        return {}

    def get_agent_tools(self):
        """
        Register custom tools for the AI Agent.

        Returns:
            list: A list of tool definitions (structure depends on Agent implementation).
        """
        return []
