# fyodoros/__main__.py
"""
Entry point for FyodorOS.

This module initializes the kernel, shell, and other core components,
then enters the main execution loop. It handles boot arguments and
reboot logic.
"""

import sys
import argparse
from fyodoros.kernel.kernel import Kernel
from fyodoros.kernel import Scheduler, SyscallHandler
from fyodoros.kernel.users import UserManager
from fyodoros.shell.shell import Shell
from fyodoros.supervisor.supervisor import Supervisor
from fyodoros.kernel.process import Process
from fyodoros.kernel.plugin_loader import PluginLoader

def boot_splash():
    """
    Displays the ASCII art boot splash screen.
    """
    print("""
███████╗██╗   ██╗ ██████╗ ██████╗  ██████╗ ██████╗
██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗
█████╗   ╚████╔╝ ██║   ██║██║  ██║██║   ██║██████╔╝
██╔══╝    ╚██╔╝  ██║   ██║██║  ██║██║   ██║██╔══██╗
██║        ██║   ╚██████╔╝██████╔╝╚██████╔╝██║  ██║
╚═╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
          FYODOR — Experimental AI Microkernel
    """)


def main():
    """
    Main function to bootstrap and run FyodorOS.

    It parses command-line arguments, initializes the kernel and shell,
    and runs the scheduler loop. It also handles the reboot cycle.
    """
    parser = argparse.ArgumentParser(description="FyodorOS Kernel")
    parser.add_argument("--user", help="Auto-login username (or pre-fill)")
    parser.add_argument("--password", help="Auto-login password")
    args = parser.parse_args()

    while True: # Reboot loop
        boot_splash()

        # Initialize Core Components
        # We can use Kernel class which now orchestrates this, but maintaining manual control for __main__ loop is fine
        # provided we hook everything up.

        # Using manual init for transparency in this "Simulated Microkernel" entry point
        # scheduler = Scheduler()
        # user_manager = UserManager()
        # syscall = SyscallHandler(scheduler, user_manager)

        # Initialize Supervisor & Shell
        # supervisor = Supervisor(scheduler, syscall)
        # shell = Shell(syscall, supervisor)

        # Load Plugins
        # Create a mock Kernel-like object or pass the syscall handler context?
        # PluginLoader expects 'kernel' object to pass to plugin.setup(kernel).
        # We should pass an object that exposes what plugins need.
        # Ideally, we pass the 'syscall' handler or a facade.
        # Existing Kernel class passes 'self'.

        # Let's instantiate the Kernel class just to serve as the context,
        # OR better: make a simple context object.
        # But actually, the Kernel class in `kernel.py` already does all this init!
        # Why duplicate?
        # The issue is `Kernel.start()` runs the shell loop blocking.
        # Here we want the Reboot loop.

        # Best approach: Use Kernel class but don't call start().
        kernel = Kernel() # This inits Scheduler, Syscall, PluginLoader

        # We need to access components from kernel instance
        scheduler = kernel.scheduler
        syscall = kernel.sys
        supervisor = kernel.supervisor

        # Shell needs to be created
        shell = Shell(syscall, supervisor)

        # Register plugin commands
        shell.register_plugin_commands(kernel.plugin_loader.get_all_shell_commands())

        # Login Loop
        # Pass args to login
        while not shell.login(auto_user=args.user, auto_pass=args.password):
            pass

        # Create Shell Process
        shell_proc = Process("shell", shell.run(), uid=shell.current_user)
        scheduler.add(shell_proc)
        supervisor.register(shell_proc)

        # Autostart services
        supervisor.start_autostart_services()

        # Run Scheduler
        try:
            scheduler.run()
        except KeyboardInterrupt:
            print("\n[kernel] Forced shutdown.")
            sys.exit(0)

        # Check exit reason
        if hasattr(scheduler, "exit_reason") and scheduler.exit_reason == "SHUTDOWN":
            break

if __name__ == "__main__":
    main()
