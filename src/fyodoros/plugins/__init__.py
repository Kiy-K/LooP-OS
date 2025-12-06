from abc import ABC, abstractmethod

class Plugin(ABC):
    """
    Base class for FyodorOS plugins.
    """
    def __init__(self):
        pass

    @abstractmethod
    def setup(self, kernel):
        """
        Called when the plugin is loaded.
        Use this to interact with the kernel (e.g., register syscalls).
        """
        pass

    def get_shell_commands(self):
        """
        Return a dictionary of shell commands provided by this plugin.
        Format: {"command_name": function_reference}
        """
        return {}

    def get_agent_tools(self):
        """
        Return a list of tool definitions for the agent.
        """
        return []
