# kernel/syscalls.py

import time
from kernel.filesystem import FileSystem

class SyscallHandler:
    def __init__(self):
        self.fs = FileSystem()

    # Filesystem
    def sys_ls(self, path="/"):
        return self.fs.list_dir(path)

    def sys_read(self, path):
        return self.fs.read_file(path)

    def sys_write(self, path, data):
        self.fs.write_file(path, data)
        self.sys_log(f"[fs] write {path}")
        return True

    def sys_append(self, path, text):
        self.fs.append_file(path, text)
        return True

    def sys_kill(self, pid, sig="SIGTERM"):
        for p in self.scheduler.processes:
            if p.pid == pid:
                p.deliver_signal(sig)
                self.sys_log(f"signal {sig} to {pid}")
                return True
        return False

    def sys_send(self, pid, message):
        for p in self.scheduler.processes:
            if p.pid == pid:
                p.send(message)
                return True
        return False

    def sys_recv(self):
        proc = self.current_process
        return proc.receive()
    
    def sys_proc_list(self):
        out = []
        for p in self.scheduler.processes:
            out.append({
                "pid": p.pid,
                "name": p.name,
                "state": p.state,
                "cpu": p.cpu_time,
                "uid": p.uid
            })
        return out



    # Logging
    def sys_log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {msg}"
        print(f"[syslog] {line}")
        self.fs.append_file("/var/log/journal/kernel.log", line)
        return True
# --- IGNORE ---