# kernel/scheduler.py
from kernel.process import ProcessState

class Scheduler:
    def __init__(self):
        self.processes = []
        self.current_process = None
        self.running = True # Control flag for the loop
        self.exit_reason = "REBOOT" # Default to reboot if stopped, unless specified

    def add(self, process):
        self.processes.append(process)

    def run(self):
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
