import time
from collections import deque
from enum import Enum, auto

class ProcessState(Enum):
    READY = auto()
    RUNNING = auto()
    WAITING = auto()
    THINKING = auto()   # AI Specific: Waiting for LLM
    TERMINATED = auto()

class Process:
    def __init__(self, name, target, uid="root", args=None, env=None):
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

        # === AI Hardware Abstraction (The "Fyodor" Touch) ===
        # Re-adding these so your 'ps' command doesn't crash!
        self.tokens_used = 0      # "Compute usage"
        self.context_window = []  # "RAM" for agents
        self.cpu_time = 0         # Wall clock time

    def send(self, msg):
        """Send IPC message to this process."""
        self.inbox.append(msg)

    def receive(self):
        """Receive IPC message from this process."""
        return self.inbox.pop(0) if self.inbox else None

    def deliver_signal(self, sig):
        """Deliver a signal to this process."""
        self.signal = sig
        # Simple signal handler lookup
        handler_name = f"SIG_{self.signal}"
        if self.env and handler_name in self.env:
             # In a real generator OS, we'd inject this call.
             # For v0.1, we just flag it.
             pass

    def run_step(self):
        """
        Run a single step. Processes are generators.
        The scheduler calls run_step repeatedly.
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
        """Simulates CPU cycles/billing for AI."""
        self.tokens_used += amount
        self.state = ProcessState.THINKING

    def __repr__(self):
        return f"<Process {self.name} pid={self.pid} state={self.state.name}>"