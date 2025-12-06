from .tty import TTY
from .syscalls import SyscallHandler
from .scheduler import Scheduler
from .users import UserManager
from fyodoros.supervisor.supervisor import Supervisor
from fyodoros.kernel.plugin_loader import PluginLoader

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

        # Plugins
        self.plugin_loader = PluginLoader(self)
        self.plugin_loader.load_active_plugins()

    def start(self):
        from fyodoros.shell.shell import Shell
        shell = Shell(self.sys, self.supervisor)

        # Inject plugin commands
        shell.register_plugin_commands(self.plugin_loader.get_all_shell_commands())

        # Note: This start implementation is blocking and basic, mainly for testing.
        # The robust implementation is in __main__.py
        shell.run()
