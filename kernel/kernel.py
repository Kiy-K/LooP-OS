from .tty import TTY
from .syscalls import SyscallHandler
from .scheduler import Scheduler
from .users import UserManager

class Kernel:
    def __init__(self):
        # low-level output/input
        self.tty = TTY()

        # Core Components
        self.scheduler = Scheduler()
        self.user_manager = UserManager()

        # system call interface (has access to this kernel)
        self.sys = SyscallHandler(self.scheduler, self.user_manager)

    def start(self):
        from shell.shell import Shell
        shell = Shell(self.sys, self.sys.scheduler) # Shell expects (syscall, supervisor/scheduler)
        # Note: Shell init signature is (syscall, supervisor=None).
        # We can pass supervisor if we had one.
        # But wait, Shell stores 'self.sys' and calls methods on it.
        # It expects SyscallHandler.

        # Let's check Shell.__init__ signature again.
        # shell/shell.py: def __init__(self, syscall, supervisor=None):

        # So passing self.sys is correct.
        shell.run()
        self.tty.write("Kernel started. Shell is running.\n")
        self.tty.write("Welcome to the simulated OS kernel!\n")
        self.tty.write("Type 'help' for a list of commands.\n")
        shell.run()
