# fyodoros.py
import sys
from kernel.kernel import Kernel
from kernel import Scheduler, SyscallHandler
from kernel.users import UserManager
from shell.shell import Shell
from supervisor.supervisor import Supervisor
from kernel.process import Process

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


def main():
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
        # We need a temporary way to login before starting the scheduler fully?
        # Or shell.login() handles it. shell.login() is blocking.
        while not shell.login():
            pass

        # Create Shell Process
        # We assume shell.current_user is set after login
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

        # Check if reboot was requested
        # We can check a flag in syscall or just loop.
        # If scheduler.run() returned, it means it finished (empty) or was stopped.
        # If it was stopped for reboot, we loop.
        # If shutdown, we break.
        # But scheduler.run() loops while self.running is True.
        # If sys_reboot called -> running=False. Loop continues.
        # If sys_shutdown called -> running=False. We need to know if it was shutdown or reboot.
        # We can check syscall flag or return value from scheduler if we modified it.
        # But scheduler doesn't return value.
        # We'll check a flag we set in syscall/scheduler?
        # Let's rely on a convention or just ask the user?
        # Actually, let's look at SyscallHandler.sys_reboot. It returns "REBOOT" string but that goes to the caller (shell).
        # We can add a flag to scheduler to indicate exit reason.

        # For now, let's assume if it exits, we check a global or similar?
        # Or better, we can check scheduler.running.
        # Wait, scheduler.running is False when it exits.
        # We need a separate flag 'reboot_requested'.

        # Hack: sys_reboot can set a flag on the scheduler instance if we add it.
        # But SyscallHandler has reference to scheduler.
        pass

        # For this implementation, I will just loop forever (Reboot behavior)
        # unless explicit exit.
        # To support shutdown, I should check something.
        # I'll add 'exit_reason' to Scheduler.
        if hasattr(scheduler, "exit_reason") and scheduler.exit_reason == "SHUTDOWN":
            break

if __name__ == "__main__":
    main()
