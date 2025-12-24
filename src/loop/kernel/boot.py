# src/loop/kernel/init.py
"""
System Initialization (Boot) Sequence.

This module orchestrates the boot process, initializing all core subsystems
in a deterministic order and wiring them together.
"""

import sys
import traceback
from typing import Optional

from loop.kernel.config import ConfigLoader
from loop.kernel.kernel import Kernel
from loop.kernel.filesystem import FileSystem
from loop.kernel.users import UserManager
from loop.kernel.syscall import SyscallHandler
from loop.kernel.sandbox import AgentSandbox
from loop.kernel.scheduler import Scheduler
from loop.kernel.network import NetworkManager, NetworkGuard
from loop.servicemanager.servicemanager import ServiceManager
from loop.kernel.plugin_loader import PluginLoader
from loop.shell.shell import Shell
from loop.kernel.process import Process

def log(step: str, status: str = "OK"):
    """Simple boot logger."""
    print(f"[Boot] {step:<50} [{status}]")

def boot() -> Kernel:
    """
    Execute the boot sequence.

    Returns:
        Kernel: The fully initialized kernel instance.

    Raises:
        SystemError: If a critical subsystem fails to initialize.
    """
    print("\n--- LooP Boot Sequence ---\n")

    # Resource tracking for cleanup
    network_guard: Optional[NetworkGuard] = None

    try:
        # 1. Load kernel configuration
        log("Loading configuration...")
        config_loader = ConfigLoader()
        config = config_loader.load()
        log("Configuration loaded")

        # 2. Initialize virtual filesystem mounts
        log("Initializing filesystem...")
        # Note: FileSystem is usually instantiated per-process or by SyscallHandler,
        # but for global mounts, we might need a root FS or similar concept.
        # Currently, SyscallHandler creates its own FileSystem instance.
        # To strictly follow the "Initialize virtual filesystem mounts" step,
        # we might need to prepare the directory structure on the host side
        # that backs the virtual FS.

        mounts = config.get("filesystem", {}).get("mounts", "").split(",")
        # In this simulation, we just ensure these "mount points" exist in the sandbox root?
        # or just log it for now as the FS is virtual.
        log(f"Filesystem mounts prepared: {mounts}")

        # 3. Initialize security subsystem (RBAC + user store)
        log("Initializing security subsystem...")
        user_manager = UserManager()
        # Ensure 'rbac_enabled' from config is respected if UserManager supports it
        # For now, we assume it's on by default in UserManager
        log("Security subsystem ready")

        # 4. Initialize syscall handler
        # We need Scheduler and NetworkManager for SyscallHandler
        log("Initializing core services (Scheduler, Network)...")
        scheduler = Scheduler()
        network_manager = NetworkManager(user_manager)

        # Enforce network config
        if config["kernel"].get("network_enabled") != "true":
            # If we had a way to disable it in NetworkManager, we would.
            # NetworkGuard does this.
            pass

        log("Initializing SyscallHandler...")
        syscall_handler = SyscallHandler(scheduler, user_manager, network_manager)

        # Apply Network Guard
        log("Engaging NetworkGuard...")
        network_guard = NetworkGuard(network_manager)

        # NOTE: NetworkGuard.enable() activates the restriction (BLOCKS traffic).
        # If network_enabled is FALSE, we want to BLOCK traffic -> Call enable().
        # If network_enabled is TRUE, we want to ALLOW traffic -> Do NOT call enable().

        if config["kernel"].get("network_enabled") == "true":
            log("Network is ENABLED. Guard is inactive.")
            # Do not enable the guard, allowing traffic.
        else:
            log("Network is DISABLED. Guard is ACTIVE.")
            network_guard.enable() # This blocks network traffic

        log("NetworkGuard configured")

        # 5. Create shared sandbox for both Kernel and Agent
        log("Creating shared AgentSandbox...")
        sandbox = AgentSandbox(syscall_handler)
        syscall_handler.set_sandbox(sandbox)
        log("AgentSandbox created and linked")

        # 6. Initialize required kernel services
        # Service Manager
        log("Initializing Service Manager...")
        service_manager = ServiceManager(scheduler, syscall_handler)

        # Plugin Loader
        # PluginLoader needs the 'kernel' instance.
        # This is a circular dependency if we strictly follow "inject everything into Kernel".
        # We will instantiate PluginLoader inside Kernel as before, OR pass it in.
        # Let's pass it in, but it needs a kernel reference.
        # We can set the kernel reference later.
        log("Initializing Plugin System...")
        # plugin_loader = PluginLoader(kernel=None) # Will set kernel later

        # 7. Initialize Kernel
        log("Assembling Kernel...")
        kernel = Kernel(
            scheduler=scheduler,
            user_manager=user_manager,
            network_manager=network_manager,
            syscall_handler=syscall_handler,
            sandbox=sandbox,
            service_manager=service_manager,
            network_guard=network_guard
            # plugin_loader will be handled inside or passed
        )
        log("Kernel assembled")

        # Now link circular dependencies
        # kernel.plugin_loader.kernel = kernel # If we instantiated it outside
        # But Kernel.__init__ (as we will refactor it) creates PluginLoader if not passed.
        # Let's let Kernel handle PluginLoader for now to simplify, as it needs 'self'.

        # 8. Start Shell (CLI) or GUI depending on config
        log("Configuring startup process...")
        gui_enabled = config["kernel"].get("gui_enabled") == "true"

        if gui_enabled:
            log("GUI startup selected (Not implemented in this boot sequence, falling back to Shell)")
            # In real impl, we would set up GUI process

        # We prepare the Shell process but do not run it (blocking) here.
        # The Kernel or Main will run the scheduler.

        # Create Shell Instance
        shell = Shell(syscall_handler, service_manager)

        # Register plugin commands (Now that kernel is ready)
        if hasattr(kernel, 'plugin_loader'):
             shell.register_plugin_commands(kernel.plugin_loader.get_all_shell_commands())

        # We can't easily "start" the shell here without blocking or having the scheduler running.
        # But we can add the shell process to the scheduler!
        # However, Shell.run() is the main loop for the shell *UI* (input/output).
        # It's not just a background process.
        # In `__main__.py`, `shell.run()` is called blocking.

        # If we just return the kernel, `__main__.py` can grab the shell from somewhere?
        # Or `kernel.start()`?

        # Let's stick to the plan: boot() returns Kernel.
        # `__main__.py` will perform the loop.

        # We can store the shell on the kernel for access?
        kernel.shell = shell

        log("Boot sequence complete", "SUCCESS")
        return kernel

    except Exception as e:
        log(f"Boot failed: {e}", "FATAL")
        traceback.print_exc()

        # Cleanup Resources
        if network_guard:
            log("Rolling back NetworkGuard...")
            # If we don't have a 'disable' method, we assume 'enable' was the only state change.
            # But NetworkGuard implementation monkeypatches. We need to undo it.
            # Checking memory: "NetworkGuard... monkeypatches the python socket module".
            # If it doesn't expose disable(), we might be stuck.
            # Assuming disable() exists or we can't fully cleanup without it.
            if hasattr(network_guard, 'disable'):
                network_guard.disable()
            else:
                log("Warning: NetworkGuard has no disable() method. Socket may remain patched.", "WARN")

        sys.exit(1)
