# system_call.py

"""
System call interface exposed to external programs / agents.
"""

from kernel.syscalls import SyscallHandler

class SystemCallInterface:
    def __init__(self, syscall: SyscallHandler):
        self.sys = syscall

    # Exposed to agents
    def ls(self, path="/"):
        return self.sys.sys_ls(path)

    def read(self, path):
        return self.sys.sys_read(path)

    def write(self, path, data):
        return self.sys.sys_write(path, data)

    def log(self, msg):
        return self.sys.sys_log(msg)
# --- IGNORE ---