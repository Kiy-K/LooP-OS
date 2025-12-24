# kernel/kernel.py
"""
Kernel Core.

This module defines the `Kernel` class, which aggregates the core components of the
OS (scheduler, users, network, etc.) and initializes them.
"""

from typing import Optional
from .io import IOAdapter, CLIAdapter
from .syscall import SyscallHandler
from .scheduler import Scheduler
from .users import UserManager
from .network import NetworkManager, NetworkGuard
from .sandbox import AgentSandbox
from loop.servicemanager.servicemanager import ServiceManager
from loop.kernel.plugins.loader import PluginLoader
from loop.kernel.senses.listener import BackgroundListener


class LoopKernel:
    """
    The central LoopKernel class.

    Initializes and manages the lifecycle of core OS components.

    Attributes:
        io (IOAdapter): Input/Output interface.
        scheduler (Scheduler): Process scheduler.
        user_manager (UserManager): User authentication and management.
        network_manager (NetworkManager): Network state management.
        network_guard (NetworkGuard): Security enforcement for network access.
        sys (SyscallHandler): System call interface.
        sandbox (AgentSandbox): Sandboxed environment for agents.
        service_manager (ServiceManager): Process and service supervisor.
        plugin_loader (PluginLoader): Plugin management system.
        listener (BackgroundListener): Global hotkey listener.
        shell: The shell instance (optional).
    """
    def __init__(
        self,
        scheduler: Optional[Scheduler] = None,
        user_manager: Optional[UserManager] = None,
        network_manager: Optional[NetworkManager] = None,
        syscall_handler: Optional[SyscallHandler] = None,
        sandbox: Optional[AgentSandbox] = None,
        service_manager: Optional[ServiceManager] = None,
        network_guard: Optional[NetworkGuard] = None,
        io_adapter: Optional[IOAdapter] = None,
    ):
        """
        Initialize the LoopKernel and all its subsystems.

        Supports dependency injection. If components are not provided,
        they are initialized with defaults (Legacy Mode).
        """
        # low-level output/input
        self.io = io_adapter if io_adapter else CLIAdapter()

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

        # Service Manager
        self.service_manager = service_manager if service_manager else ServiceManager(self.scheduler, self.sys)

        # Plugins
        # Use existing loader if syscall has one, else create new
        if hasattr(self.sys, 'plugin_loader'):
            self.plugin_loader = self.sys.plugin_loader
            self.plugin_loader.kernel = self # Attach kernel back ref
        else:
            self.plugin_loader = PluginLoader(self)

        # NOTE: We do not load plugins here immediately because they might require an Agent instance.
        # They are loaded lazily or when agent starts.
        # However, for Shell commands, we might need them?
        # The new architecture focuses on Agent tools. Shell commands from plugins are not explicitly mentioned in v1.1.0 directives.
        # Assuming v1.1.0 focuses on Agent tools, we defer loading until Agent is ready or shell requests it.
        # But wait, old kernel loaded them. If we want backward compat, we might need to load them but what about 'agent' arg?
        # The new loader requires `load_all_plugins(agent)`.
        # So we cannot load them here without an agent.

        # Background Listener (Senses)
        self.listener = BackgroundListener(self.sys, self.io)

        # Agent (Optional, persistent)
        self.agent = None

        # Shell (initialized later)
        self.shell = None

    def start(self):
        """
        Start the LoopKernel.

        Initializes the Shell (if not already present), registers plugin commands, and begins execution.
        Note: This method is blocking.
        """
        # Start the background listener
        self.listener.start()

        from loop.shell.shell import Shell

        if self.shell:
            shell = self.shell
        else:
            shell = Shell(self.sys, self.service_manager, self.io)
            # Inject plugin commands - Logic removed as new loader doesn't support get_all_shell_commands yet
            # If needed, plugins should expose shell commands via a different mechanism or updated loader.
            # For v1.1.0 we focus on Agent tools.

        # Note: This start implementation is blocking and basic, mainly for testing.
        # The robust implementation is in __main__.py
        try:
            shell.run()
        finally:
            self.shutdown()

    def shutdown(self):
        """
        Gracefully shut down the kernel and its subsystems.
        Enforces correct teardown order: Scheduler -> Plugins -> Services -> Network.
        Follows the 3-phase shutdown protocol (Warning -> Graceful -> Force).
        """
        self.io.write("\n--- LooP Shutdown Sequence ---\n")

        # 1. Stop Scheduler from accepting new tasks
        if self.scheduler:
            self.scheduler.shutdown()
            # If we were fully threaded, we'd call scheduler.stop() here too,
            # but since we might be running inside it or it drives us, we just lock the gate.

        # 2. Warning Phase (Broadcast to plugins)
        # We define a grace period (e.g. 3s)
        grace_period = 3.0
        # Plugin hooks removed/deferred in v1.1.0 simplified loader.
        # if self.plugin_loader:
        #    self.plugin_loader.on_shutdown_warning(grace_period)

        # 3. Teardown Plugins (Graceful)
        # if self.plugin_loader:
        #    self.plugin_loader.on_shutdown()

        # 4. Stop Services (The big wait)
        if self.service_manager:
            # We pass the rest of the grace period logic to service manager
            self.service_manager.shutdown(timeout=10.0, grace_period=0) # We already warned plugins

        # 5. Disable Network Guard (Release patches)
        if self.network_guard:
            self.network_guard.disable()

        # 6. Stop Listener
        if self.listener:
            self.listener.stop()

        self.io.write("[Kernel] Shutdown complete.\n")
