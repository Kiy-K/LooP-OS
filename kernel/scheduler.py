# kernel/scheduler.py

class Scheduler:
    def __init__(self):
        self.processes = []

    def add(self, process):
        self.processes.append(process)

    def run(self):
        while True:
            for proc in list(self.processes):

                # handle signals
                if proc.signal == "SIGKILL":
                    proc.state = "zombie"
                    print(f"[scheduler] {proc.pid} killed")
                    self.processes.remove(proc)
                    continue

                if proc.signal == "SIGTERM":
                    proc.state = "zombie"
                    print(f"[scheduler] {proc.pid} terminated")
                    self.processes.remove(proc)
                    continue

                if proc.state != "running":
                    continue

                try:
                    next(proc.gen)
                    proc.cpu_time += 1
                except StopIteration:
                    proc.state = "zombie"
                    self.processes.remove(proc)
                    print(f"[scheduler] {proc.pid} exited")