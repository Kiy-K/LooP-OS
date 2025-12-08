# kernel/kernel.py
"""
Kernel Core.

This module defines the `Kernel` class, which aggregates the core components of the
OS (scheduler, users, network, etc.) and initializes them.
"""

from typing import Optional
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
        shell: The shell instance (optional).
    """
    def __init__(
        self,
        scheduler: Optional[Scheduler] = None,
        user_manager: Optional[UserManager] = None,
        network_manager: Optional[NetworkManager] = None,
        syscall_handler: Optional[SyscallHandler] = None,
        sandbox: Optional[AgentSandbox] = None,
        supervisor: Optional[Supervisor] = None,
        network_guard: Optional[NetworkGuard] = None,
    ):
        """
        Initialize the Kernel and all its subsystems.

        Supports dependency injection. If components are not provided,
        they are initialized with defaults (Legacy Mode).
        """
        # low-level output/input
        self.tty = TTY()

        # Core Components
        self.scheduler = scheduler if scheduler else Scheduler()
        self.user_manager = user_manager if user_manager else UserManager()
        self.network_manager = network_manager if network_manager else NetworkManager(self.user_manager)

        # Security Guards
        self.network_guard = network_guard if network_guard else NetworkGuard(self.network_manager)
        # Only enable if we created it (Legacy) or if it's not enabled?
        # In DI mode, boot() handles enabling. In Legacy, we do it here.
        if not network_guard:
             self.network_guard.enable()

        # system call interface
        self.sys = syscall_handler if syscall_handler else SyscallHandler(self.scheduler, self.user_manager, self.network_manager)

        # Sandbox
        if sandbox:
            self.sandbox = sandbox
            # Ensure syscall handler knows about this sandbox
            # If syscall_handler was passed in, it might already be set, but setting it again is safe.
            self.sys.set_sandbox(self.sandbox)
        else:
            self.sandbox = AgentSandbox(self.sys)
            self.sys.set_sandbox(self.sandbox)

        # Supervisor
        self.supervisor = supervisor if supervisor else Supervisor(self.scheduler, self.sys)

        # Plugins
        self.plugin_loader = PluginLoader(self)
        self.plugin_loader.load_active_plugins()

        # Shell (initialized later)
        self.shell = None

    def start(self):
        """
        Start the Kernel.

        Initializes the Shell (if not already present), registers plugin commands, and begins execution.
        Note: This method is blocking.
        """
        from fyodoros.shell.shell import Shell

        if self.shell:
            shell = self.shell
        else:
            shell = Shell(self.sys, self.supervisor)
            # Inject plugin commands
            shell.register_plugin_commands(self.plugin_loader.get_all_shell_commands())

        # Note: This start implementation is blocking and basic, mainly for testing.
        # The robust implementation is in __main__.py
        shell.run()
