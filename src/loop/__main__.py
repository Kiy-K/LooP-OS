# loop/__main__.py
"""
Entry point for LooP.

This module initializes the kernel, shell, and other core components,
then enters the main execution loop. It handles boot arguments and
reboot logic.
"""

import sys
import argparse
from loop.kernel.init import boot
from loop.kernel.process import Process


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
          LOOP — Experimental AI Microkernel
    """)


def main():
    """
    Main function to bootstrap and run LooP.

    It parses command-line arguments, initializes the kernel and shell,
    and runs the scheduler loop. It also handles the reboot cycle.

    Arguments:
        None (uses argparse to read sys.argv)
            --user: Auto-login username.
            --password: Auto-login password.
    """
    parser = argparse.ArgumentParser(description="LooP Kernel")
    parser.add_argument("--user", help="Auto-login username (or pre-fill)")
    parser.add_argument("--password", help="Auto-login password")
    args = parser.parse_args()

    while True: # Reboot loop
        boot_splash()

        # Initialize Core Components via Boot Sequence
        kernel = boot()

        # We need to access components from kernel instance
        scheduler = kernel.scheduler
        supervisor = kernel.supervisor
        shell = kernel.shell # Boot sequence creates this

        if not shell:
            # Fallback if boot didn't create shell (e.g. config issue)
            # This shouldn't happen with current boot() impl but safety first
            from loop.shell.shell import Shell
            shell = Shell(kernel.sys, supervisor)
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
