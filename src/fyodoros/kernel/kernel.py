# kernel/kernel.py
"""
Kernel Core.

This module defines the `Kernel` class, which aggregates the core components of the
OS (scheduler, users, network, etc.) and initializes them.
"""

from .tty import TTY
from .syscalls import SyscallHandler
from .scheduler import Scheduler
from .users import UserManager
from .network import NetworkManager, NetworkGuard
from .sandbox import AgentSandbox
from fyodoros.supervisor.supervisor import Supervisor
from fyodoros.kernel.plugin_loader import PluginLoader

class Kernel:
    """
    The central Kernel class.

    Initializes and manages the lifecycle of core OS components.

    Attributes:
        tty (TTY): Terminal device.
        scheduler (Scheduler): Process scheduler.
        user_manager (UserManager): User authentication and management.
        network_manager (NetworkManager): Network state management.
        network_guard (NetworkGuard): Security enforcement for network access.
        sys (SyscallHandler): System call interface.
        sandbox (AgentSandbox): Sandboxed environment for agents.
        supervisor (Supervisor): Process and service supervisor.
        plugin_loader (PluginLoader): Plugin management system.
    """
    def __init__(self):
        """
        Initialize the Kernel and all its subsystems.
        """
        # low-level output/input
        self.tty = TTY()

        # Core Components
        self.scheduler = Scheduler()
        self.user_manager = UserManager()
        self.network_manager = NetworkManager(self.user_manager)

        # Security Guards
        self.network_guard = NetworkGuard(self.network_manager)
        self.network_guard.enable()

        # system call interface (has access to this kernel)
        self.sys = SyscallHandler(self.scheduler, self.user_manager, self.network_manager)

        # Sandbox (requires syscall handler)
        self.sandbox = AgentSandbox(self.sys)
        self.sys.set_sandbox(self.sandbox)

        # Supervisor
        self.supervisor = Supervisor(self.scheduler, self.sys)

        # Plugins
        self.plugin_loader = PluginLoader(self)
        self.plugin_loader.load_active_plugins()

    def start(self):
        """
        Start the Kernel.

        Initializes the Shell, registers plugin commands, and begins execution.
        Note: This method is blocking.
        """
        from fyodoros.shell.shell import Shell
        shell = Shell(self.sys, self.supervisor)

        # Inject plugin commands
        shell.register_plugin_commands(self.plugin_loader.get_all_shell_commands())

        # Note: This start implementation is blocking and basic, mainly for testing.
        # The robust implementation is in __main__.py
        shell.run()
