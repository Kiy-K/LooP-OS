from .tty import TTY
from .syscalls import SyscallHandler
from .scheduler import Scheduler
from .users import UserManager
from fyodoros.supervisor.supervisor import Supervisor

class Kernel:
    """
    Alternative entry point wrapper, though `fyodoros/__main__.py` is preferred.
    """
    def __init__(self):
        # low-level output/input
        self.tty = TTY()

        # Core Components
        self.scheduler = Scheduler()
        self.user_manager = UserManager()

        # system call interface (has access to this kernel)
        self.sys = SyscallHandler(self.scheduler, self.user_manager)

        # Supervisor
        self.supervisor = Supervisor(self.scheduler, self.sys)

    def start(self):
        from fyodoros.shell.shell import Shell
        shell = Shell(self.sys, self.supervisor)

        # Note: This start implementation is blocking and basic, mainly for testing.
        # The robust implementation is in __main__.py
        shell.run()
