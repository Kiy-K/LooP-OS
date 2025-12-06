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
        shell = Shell(self)
        shell.run()
        self.tty.write("Kernel started. Shell is running.\n")
        self.tty.write("Welcome to the simulated OS kernel!\n")
        self.tty.write("Type 'help' for a list of commands.\n")
        shell.run()
