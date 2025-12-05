# fyodoros.py
from kernel.kernel import Kernel    
from kernel import Scheduler, SyscallHandler
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
    k = Kernel()
    k.start()
    boot_splash()

    scheduler = Scheduler()
    syscall = SyscallHandler()
    supervisor = Supervisor(scheduler, syscall)
    shell = Shell(syscall, supervisor)

    # LOGIN FIRST
    while not shell.login():
        pass

    shell_proc = Process("shell", shell.run(), uid=shell.current_user)
    scheduler.add(shell_proc)
    supervisor.register(shell_proc)
    scheduler.run()


if __name__ == "__main__":
    main()
# --- IGNORE ---