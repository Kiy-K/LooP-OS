# servicemanager/servicemanager.py
"""
Service Manager.

This module provides the `ServiceManager` class, which handles the lifecycle of system services.
It supports dependency management, graceful shutdown protocols, and advanced timeout handling.
"""

import time
import threading
from graphlib import TopologicalSorter
from typing import Dict, List, Optional, Tuple, Any

from loop.kernel.process import Process
from loop.kernel.scheduler import Scheduler
from loop.servicemanager.types import (
    ServiceType, ServiceMetadata, ShutdownState, ShutdownReport
)


class ServiceManager:
    """
    Manages system processes and services with dependency support and robust teardown.

    Attributes:
        scheduler (Scheduler): The kernel scheduler.
        sys (SyscallHandler): The system call interface.
        services (dict): A registry of running services {name: Process}.
        metadata (dict): Metadata for each service {name: ServiceMetadata}.
        all_processes (list): Legacy list of all processes (for compatibility).
        shutdown_state (ShutdownState): Current phase of shutdown.
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
        self.services: Dict[str, Process] = {}
        self.metadata: Dict[str, ServiceMetadata] = {}
        self.all_processes: List[Process] = []
        self.shutdown_state = ShutdownState.NOT_STARTED

    # ==========================
    # Registry & Dependency API
    # ==========================

    def register(self, process):
        """
        Register a process (Legacy API).
        """
        self.all_processes.append(process)

    def list_processes(self):
        """Legacy API."""
        return self.all_processes

    def start_service(self, name: str, generator_fn, depends_on: List[str] = None,
                      metadata: Optional[ServiceMetadata] = None):
        """
        Start a background service with metadata and dependencies.

        Args:
            name (str): Service name.
            generator_fn (generator): The generator function (if GENERATOR type).
            depends_on (list): Optional list of service names this depends on.
            metadata (ServiceMetadata): Optional full metadata object.
        """
        # Validate dependencies exist (or are at least known?)
        # For now, we allow starting even if deps aren't running, but we store the info.

        # Construct metadata if not provided
        if not metadata:
            metadata = ServiceMetadata(
                name=name,
                type=ServiceType.GENERATOR,
                dependencies=depends_on or []
            )

        # Ensure name matches
        if metadata.name != name:
            metadata.name = name

        # Store metadata
        self.metadata[name] = metadata

        # Create Process
        proc = Process(name, generator_fn)
        self.services[name] = proc

        # Register in Scheduler
        try:
            self.scheduler.add(proc)
        except Exception as e:
            print(f"[servicemanager] Failed to schedule {name}: {e}")
            return

        self.register(proc)
        print(f"[servicemanager] Service started: {name} (Type: {metadata.type.value})")

    def start_autostart_services(self):
        """
        Start services defined in `/etc/loop/services.conf`.
        """
        try:
            content = self.sys.sys_read("/etc/loop/services.conf")
        except:
            return

        services = content.splitlines()
        for svc in services:
            svc = svc.strip()
            if svc == "journal":
                from loop.servicemanager.journal_daemon import journal_daemon
                self.start_service("journal", journal_daemon(self.sys))

    # ==========================
    # Operations
    # ==========================

    def run_service(self, name: str) -> str:
        """
        Manually start a known service by name (Legacy wrapper).
        """
        if name == "journal":
            from loop.servicemanager.journal_daemon import journal_daemon
            self.start_service("journal", journal_daemon(self.sys))
            return "journal started"
        return f"service {name} not found"

    def kill_process(self, pid: int) -> str:
        """
        Kill a process by PID (Legacy wrapper).
        """
        ok = self.sys.sys_kill(pid)
        return "killed" if ok else "no such pid"

    def send_message(self, pid: int, msg: str) -> str:
        """Legacy wrapper."""
        ok = self.sys.sys_send(pid, msg)
        return "sent" if ok else "failed"

    # ==========================
    # Comprehensive Shutdown
    # ==========================

    def _get_shutdown_order(self) -> List[str]:
        """
        Calculate shutdown order based on dependency graph.
        Services that others depend on should be shut down LAST.
        So we need Reverse Topological Sort of dependencies.

        If A depends on B:
        - Startup: B then A
        - Shutdown: A then B

        Using TopologicalSorter:
        graph = {A: {B}} (A depends on B)
        ts.static_order() returns B, A.
        Reversed: A, B. (Correct shutdown order).
        """
        ts = TopologicalSorter()

        # Add all services
        for name, meta in self.metadata.items():
            # Add dependencies
            # ts.add(node, *predecessors)
            # If A depends on B, B must come before A in topological order.
            # So B is a predecessor of A.
            ts.add(name, *meta.dependencies)

        try:
            # static_order returns generic topological order (Dependencies first)
            # e.g. B, A
            start_order = list(ts.static_order())

            # Filter out services that are not actually running
            # (TopologicalSorter might include deps that aren't active if we added them explicitly,
            # but here we iterate existing metadata)
            running_order = [s for s in start_order if s in self.services]

            # Shutdown order is reverse of startup
            return list(reversed(running_order))

        except Exception as e:
            print(f"[servicemanager] Cycle detected or graph error: {e}. Fallback to LIFO.")
            return list(reversed(list(self.services.keys())))

    def _threaded_timeout_exec(self, func, args=(), kwargs=None, timeout=1.0) -> Tuple[bool, Any]:
        """
        Execute func in a thread with timeout.
        Returns (success, result).
        """
        if kwargs is None: kwargs = {}

        result_container = [None]
        exception_container = [None]

        def target():
            try:
                result_container[0] = func(*args, **kwargs)
            except Exception as e:
                exception_container[0] = e

        t = threading.Thread(target=target)
        t.daemon = True
        t.start()
        t.join(timeout)

        if t.is_alive():
            return False, None

        if exception_container[0]:
            raise exception_container[0]

        return True, result_container[0]

    def _stop_service_single(self, name: str, force: bool = False):
        """
        Stop a single service using its metadata policies.
        """
        proc = self.services.get(name)
        if not proc: return

        meta = self.metadata.get(name)
        timeout = meta.force_timeout if force else meta.graceful_timeout if meta else 5.0

        # In this simulation, services are mostly Generators or processes managed by Syscalls.
        # "Stopping" usually means removing from scheduler or sending SIGTERM.

        print(f"[servicemanager] Stopping {name} (Force={force})...")

        # Attempt kill/stop
        # We wrap the syscall in the timeout executor just in case it hangs
        # (e.g. if sys_kill waits on a mutex or external IO)
        success, _ = self._threaded_timeout_exec(
            self.sys.sys_kill, args=(proc.pid,), timeout=timeout
        )

        if not success:
            print(f"[servicemanager] Timeout killing {name}")
            # If force was already True, we can't do much more but scrub state.

        # Cleanup State
        if proc in self.scheduler.processes:
            self.scheduler.processes.remove(proc)

    def shutdown(self, timeout: float = 30.0, grace_period: float = 5.0, force: bool = False) -> ShutdownReport:
        """
        Coordinated system shutdown with configurable behavior.

        Args:
            timeout (float): Total maximum time for shutdown.
            grace_period (float): Time for warning phase.
            force (bool): Skip graceful phase.

        Returns:
            ShutdownReport
        """
        print(f"[servicemanager] Initiating shutdown (timeout={timeout}s, grace={grace_period}s)")
        report = ShutdownReport()
        start_time = time.time()

        self.shutdown_state = ShutdownState.WARNING

        # 1. Warning Phase (if not forced)
        if not force:
            # We would notify plugins here if we had reference, but that's handled by Kernel usually.
            # But wait, User Req 6: "Plugin System Integration... PluginLoader methods"
            # The ServiceManager doesn't own PluginLoader. The Kernel does.
            # The Kernel calls PluginLoader.on_shutdown_warning.
            # Here we just sleep/wait if we are managing services that listen to warnings?
            # Since our services are simple processes, we might just wait the grace period.
            time.sleep(grace_period)

        # 2. Shutdown Phase
        self.shutdown_state = ShutdownState.FORCE if force else ShutdownState.GRACEFUL

        order = self._get_shutdown_order()

        for name in order:
            # Check global timeout
            if time.time() - start_time > timeout:
                print("[servicemanager] Global shutdown timeout exceeded!")
                report.errors["global"] = "Timeout exceeded"
                break

            try:
                self._stop_service_single(name, force=force)
                report.success.append(name)
            except Exception as e:
                print(f"[servicemanager] Error stopping {name}: {e}")
                report.failed.append(name)
                report.errors[name] = str(e)

        # 3. Final Cleanup
        self.shutdown_state = ShutdownState.CLEANUP

        # Scrub any remaining
        remaining = [p for p in self.services.values() if p in self.scheduler.processes]
        for proc in remaining:
            self.scheduler.processes.remove(proc)

        self.services.clear()
        self.all_processes.clear()

        report.total_time = time.time() - start_time
        self.shutdown_state = ShutdownState.COMPLETE
        print("[servicemanager] Shutdown complete.")
        return report

    def emergency_shutdown(self):
        """Immediate force kill all."""
        self.shutdown(timeout=5.0, grace_period=0, force=True)
