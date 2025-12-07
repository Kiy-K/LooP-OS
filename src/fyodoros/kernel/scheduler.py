# kernel/scheduler.py
"""
Process Scheduler.

This module implements a simple round-robin scheduler for managing process execution.
"""

from fyodoros.kernel.process import ProcessState

class Scheduler:
    """
    Manages and schedules processes.

    Attributes:
        processes (list): List of active Process objects.
        current_process (Process): The currently executing process.
        running (bool): Flag indicating if the scheduler loop is active.
        exit_reason (str): Reason for stopping the scheduler (e.g., 'REBOOT', 'SHUTDOWN').
    """
    def __init__(self):
        """
        Initialize the Scheduler.
        """
        self.processes = []
        self.current_process = None
        self.running = True # Control flag for the loop
        self.exit_reason = "REBOOT" # Default to reboot if stopped, unless specified

    def add(self, process):
        """
        Add a process to the scheduler.

        Args:
            process (Process): The process to add.
        """
        self.processes.append(process)

    def run(self):
        """
        Start the scheduling loop.

        Iterates through the list of processes and calls `run_step()` on each
        active process. Handles process termination and signals (SIGKILL, SIGTERM).
        """
        self.running = True
        while self.running and self.processes:
            # Create a copy to allow modification during iteration (e.g. kill)
            for proc in list(self.processes):
                self.current_process = proc

                # handle signals
                if proc.signal == "SIGKILL":
                    proc.state = ProcessState.TERMINATED
                    print(f"[scheduler] {proc.pid} killed")
                    self.processes.remove(proc)
                    continue

                if proc.signal == "SIGTERM":
                    proc.state = ProcessState.TERMINATED
                    print(f"[scheduler] {proc.pid} terminated")
                    self.processes.remove(proc)
                    continue

                # If process is not ready/running, skip (unless we have wait logic)
                # ProcessState.READY or ProcessState.RUNNING are actionable
                if proc.state not in [ProcessState.READY, ProcessState.RUNNING, ProcessState.THINKING]:
                    if proc.state == ProcessState.TERMINATED:
                         self.processes.remove(proc)
                    continue

                # Run a step
                proc.run_step()

                if proc.state == ProcessState.TERMINATED:
                    self.processes.remove(proc)
                    # print(f"[scheduler] {proc.pid} exited")

                self.current_process = None
