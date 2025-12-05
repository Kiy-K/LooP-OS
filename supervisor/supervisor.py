# supervisor/supervisor.py

from kernel.process import Process
from kernel.scheduler import Scheduler


class Supervisor:
    def __init__(self, scheduler, syscall):
        self.scheduler = scheduler
        self.sys = syscall
        self.services = {}
        self.all_processes = []

    def register(self, process):
        self.all_processes.append(process)

    def list_processes(self):
        return self.all_processes

    def start_service(self, name, generator_fn):
        proc = Process(name, generator_fn)
        self.services[name] = proc
        self.scheduler.add(proc)
        self.register(proc)
        print(f"[supervisor] Service started: {name}")

    def start_autostart_services(self):
        try:
            content = self.sys.sys_read("/etc/fyodoros/services.conf")
        except:
            return

        services = content.splitlines()
        for svc in services:
            svc = svc.strip()
            if svc == "journal":
                from supervisor.journal_daemon import journal_daemon
                self.start_service("journal", journal_daemon(self.sys))
    def kill_process(self, pid):
        ok = self.sys.sys_kill(pid)
        return "killed" if ok else "no such pid"

    def send_message(self, pid, msg):
        ok = self.sys.sys_send(pid, msg)
        return "sent" if ok else "failed"

    # new public API
    def run_service(self, name):
        if name == "journal":
            from supervisor.journal_daemon import journal_daemon
            self.start_service("journal", journal_daemon(self.sys))
            return "journal started"
        return f"service {name} not found"
# --- IGNORE ---