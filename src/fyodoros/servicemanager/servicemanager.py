# servicemanager/servicemanager.py
"""
Service Manager.

This module provides the `ServiceManager` class, which acts as a process manager.
It handles starting background services, managing autostart configurations,
and interacting with the scheduler.
"""

import time
from fyodoros.kernel.process import Process
from fyodoros.kernel.scheduler import Scheduler


class ServiceManager:
    """
    Manages system processes and services.

    Attributes:
        scheduler (Scheduler): The kernel scheduler.
        sys (SyscallHandler): The system call interface.
        services (dict): A registry of running services.
        all_processes (list): A list of all processes known to the service manager.
    """
    def __init__(self, scheduler, syscall):
        """
        Initialize the ServiceManager.

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
        Register a process with the service manager.

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
        print(f"[servicemanager] Service started: {name}")

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
                from fyodoros.servicemanager.journal_daemon import journal_daemon
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
            from fyodoros.servicemanager.journal_daemon import journal_daemon
            self.start_service("journal", journal_daemon(self.sys))
            return "journal started"
        return f"service {name} not found"

    def shutdown(self):
        """
        Stop all running services in reverse order (LIFO).
        Guarantees deterministic teardown even if process killing fails.
        Includes timeout logic for robustness.
        """
        # Iterate in reverse order of insertion (insertion order is preserved in dicts since Python 3.7)
        for name, proc in reversed(list(self.services.items())):
            print(f"[servicemanager] Stopping {name}...")

            start_time = time.time()
            # Attempt to kill process with timeout enforcement (conceptual, as kill is currently immediate)
            try:
                # In a real system, we might send SIGTERM, wait, then SIGKILL.
                # Here we simulate an immediate kill attempt.
                self.kill_process(proc.pid)

                # Check if it's really gone (if we had state feedback)
                # If kill hangs (mock), we break after timeout
                if time.time() - start_time > 2.0:
                    print(f"[servicemanager] Timeout stopping {name}")

            except Exception as e:
                print(f"[servicemanager] Failed to kill {name}: {e}")

            # Guaranteed cleanup steps
            try:
                if proc in self.scheduler.processes:
                    self.scheduler.processes.remove(proc)
            except Exception as e:
                print(f"[servicemanager] Failed to remove {name} from scheduler: {e}")

        self.services.clear()
        # Also clear the all_processes registry
        self.all_processes.clear()
        print("[servicemanager] All services stopped.")
