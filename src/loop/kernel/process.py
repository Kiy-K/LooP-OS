# kernel/process.py
"""
Process Management.

This module defines the `Process` class and `ProcessState` enum, which represent
running programs in the system. Processes are implemented as Python generators
to allow for cooperative multitasking.
"""

import time
from collections import deque
from enum import Enum, auto


class ProcessState(Enum):
    """
    Enumeration of possible process states.
    """
    READY = auto()
    RUNNING = auto()
    WAITING = auto()
    THINKING = auto()   # AI Specific: Waiting for LLM
    TERMINATED = auto()


class Process:
    """
    Represents a process in the OS.

    Attributes:
        name (str): The name of the process.
        target (generator): The generator function representing the process execution.
        state (ProcessState): The current state of the process.
        pid (int): The process ID.
        created_at (float): Timestamp when the process was created.
        uid (str): User ID of the process owner.
        args (list): Arguments passed to the process.
        env (dict): Environment variables for the process.
        inbox (list): Queue for incoming IPC messages.
        signal (str): Last received signal.
        exit_code (int): Exit code of the process.
        tokens_used (int): Simulated compute usage (AI tokens).
        context_window (list): Simulated RAM for AI agents.
        cpu_time (float): Total wall clock time consumed by the process.
    """

    def __init__(self, name, target, uid="root", args=None, env=None):
        """
        Initialize a new Process.

        Args:
            name (str): Name of the process.
            target (generator): The generator object to run.
            uid (str, optional): User ID. Defaults to "root".
            args (list, optional): Process arguments.
            env (dict, optional): Process environment variables.
        """
        self.name = name
        self.target = target # Generator
        self.state = ProcessState.READY

        # PID generation (Time based is fine for v0.1)
        self.pid = int(time.time() * 1000) % 1000000

        self.created_at = time.time()
        self.uid = uid
        self.args = args or []
        self.env = env or {}

        # === IPC & Signals (From your code) ===
        self.inbox = []
        self.signal = None
        self.exit_code = None

        # === AI Hardware Abstraction (The "LooP" Touch) ===
        # Re-adding these so your 'ps' command doesn't crash!
        self.tokens_used = 0      # "Compute usage"
        self.context_window = []  # "RAM" for agents
        self.cpu_time = 0         # Wall clock time

    def send(self, msg):
        """
        Send an IPC message to this process.

        Args:
            msg (any): The message to send.
        """
        self.inbox.append(msg)

    def receive(self):
        """
        Receive an IPC message from this process's inbox.

        Returns:
            any: The message, or None if inbox is empty.
        """
        return self.inbox.pop(0) if self.inbox else None

    def deliver_signal(self, sig):
        """
        Deliver a signal to this process.

        Args:
            sig (str): The signal identifier.
        """
        self.signal = sig
        # Simple signal handler lookup
        handler_name = f"SIG_{self.signal}"
        if self.env and handler_name in self.env:
             # In a real generator OS, we'd inject this call.
             # For v0.1, we just flag it.
             pass

    def run_step(self):
        """
        Run a single execution step.

        Since processes are generators, this calls `next()` on the generator.
        It manages state transitions (RUNNING -> READY or TERMINATED) and
        catches exceptions.
        """
        if self.state == ProcessState.TERMINATED:
            return

        start_time = time.time()
        self.state = ProcessState.RUNNING

        try:
            # Execute until the process yields control
            next(self.target)

            # If we get here, the process yielded successfully
            if self.state == ProcessState.RUNNING:
                self.state = ProcessState.READY

        except StopIteration:
            self.state = ProcessState.TERMINATED
            self.exit_code = 0
        except Exception as e:
            print(f"[process {self.pid}] Error in process: {e}")
            self.state = ProcessState.TERMINATED
            self.exit_code = 1
        finally:
            self.cpu_time += (time.time() - start_time)

    def charge_tokens(self, amount):
        """
        Simulate charging AI tokens (compute usage).

        Args:
            amount (int): The amount of tokens to charge.
        """
        self.tokens_used += amount
        self.state = ProcessState.THINKING

    def __repr__(self):
        """
        Return a string representation of the Process.

        Returns:
            str: String representation.
        """
        return f"<Process {self.name} pid={self.pid} state={self.state.name}>"
