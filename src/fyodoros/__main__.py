# fyodoros/__main__.py
import sys
from fyodoros.kernel.kernel import Kernel
from fyodoros.kernel import Scheduler, SyscallHandler
from fyodoros.kernel.users import UserManager
from fyodoros.shell.shell import Shell
from fyodoros.supervisor.supervisor import Supervisor
from fyodoros.kernel.process import Process

def boot_splash():
    print("""
███████╗██╗   ██╗ ██████╗ ██████╗  ██████╗ ██████╗
██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗
█████╗   ╚████╔╝ ██║   ██║██║  ██║██║   ██║██████╔╝
██╔══╝    ╚██╔╝  ██║   ██║██║  ██║██║   ██║██╔══██╗
██║        ██║   ╚██████╔╝██████╔╝╚██████╔╝██║  ██║
╚═╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
          FYODOR — Experimental AI Microkernel
    """)


import argparse

def main():
    parser = argparse.ArgumentParser(description="FyodorOS Kernel")
    parser.add_argument("--user", help="Auto-login username (or pre-fill)")
    parser.add_argument("--password", help="Auto-login password")
    args = parser.parse_args()

    while True: # Reboot loop
        boot_splash()

        # Initialize Core Components
        scheduler = Scheduler()
        user_manager = UserManager()
        syscall = SyscallHandler(scheduler, user_manager)

        # Initialize Supervisor & Shell
        supervisor = Supervisor(scheduler, syscall)
        shell = Shell(syscall, supervisor)

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
