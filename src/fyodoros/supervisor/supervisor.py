# supervisor/supervisor.py
"""
Service Supervisor.

This module provides the `Supervisor` class, which acts as a process manager.
It handles starting background services, managing autostart configurations,
and interacting with the scheduler.
"""

from fyodoros.kernel.process import Process
from fyodoros.kernel.scheduler import Scheduler


class Supervisor:
    """
    Manages system processes and services.

    Attributes:
        scheduler (Scheduler): The kernel scheduler.
        sys (SyscallHandler): The system call interface.
        services (dict): A registry of running services.
        all_processes (list): A list of all processes known to the supervisor.
    """
    def __init__(self, scheduler, syscall):
        """
        Initialize the Supervisor.

        Args:
            scheduler (Scheduler): The scheduler.
            syscall (SyscallHandler): System call interface.
        """
        self.scheduler = scheduler
        self.sys = syscall
        self.services = {}
        self.all_processes = []

    def register(self, process):
        """
        Register a process with the supervisor.

        Args:
            process (Process): The process to register.
        """
        self.all_processes.append(process)

    def list_processes(self):
        """
        List all registered processes.

        Returns:
            list: List of Process objects.
        """
        return self.all_processes

    def start_service(self, name, generator_fn):
        """
        Start a background service.

        Args:
            name (str): Service name.
            generator_fn (generator): The generator function for the service.
        """
        proc = Process(name, generator_fn)
        self.services[name] = proc
        self.scheduler.add(proc)
        self.register(proc)
        print(f"[supervisor] Service started: {name}")

    def start_autostart_services(self):
        """
        Start services defined in `/etc/fyodoros/services.conf`.
        """
        try:
            content = self.sys.sys_read("/etc/fyodoros/services.conf")
        except:
            return

        services = content.splitlines()
        for svc in services:
            svc = svc.strip()
            if svc == "journal":
                from fyodoros.supervisor.journal_daemon import journal_daemon
                self.start_service("journal", journal_daemon(self.sys))

    def kill_process(self, pid):
        """
        Kill a process by PID.

        Args:
            pid (int): Process ID.

        Returns:
            str: Status message.
        """
        ok = self.sys.sys_kill(pid)
        return "killed" if ok else "no such pid"

    def send_message(self, pid, msg):
        """
        Send a message to a process.

        Args:
            pid (int): Process ID.
            msg (str): Message content.

        Returns:
            str: Status message.
        """
        ok = self.sys.sys_send(pid, msg)
        return "sent" if ok else "failed"

    # new public API
    def run_service(self, name):
        """
        Manually start a known service by name.

        Args:
            name (str): Service name (e.g., "journal").

        Returns:
            str: Status message.
        """
        if name == "journal":
            from fyodoros.supervisor.journal_daemon import journal_daemon
            self.start_service("journal", journal_daemon(self.sys))
            return "journal started"
        return f"service {name} not found"

    def shutdown(self):
        """
        Stop all running services in reverse order (LIFO).
        """
        # Iterate in reverse order of insertion (insertion order is preserved in dicts since Python 3.7)
        for name, proc in reversed(list(self.services.items())):
            print(f"[supervisor] Stopping {name}...")
            # We use kill_process since we don't have a graceful stop protocol for generators yet
            # unless we signal them?
            # For now, we just kill them.
            self.kill_process(proc.pid)
            # Remove from scheduler?
            if proc in self.scheduler.processes:
                self.scheduler.processes.remove(proc)

        self.services.clear()
        # Also clear the all_processes registry
        self.all_processes.clear()
        print("[supervisor] All services stopped.")
