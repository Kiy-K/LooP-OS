# kernel/syscalls.py

import time
from kernel.filesystem import FileSystem
from kernel.users import UserManager

class SyscallHandler:
    def __init__(self, scheduler=None, user_manager=None):
        self.fs = FileSystem()
        self.scheduler = scheduler
        self.user_manager = user_manager or UserManager()

    def set_scheduler(self, scheduler):
        self.scheduler = scheduler

    # Authentication
    def sys_login(self, user, password):
        if self.user_manager.authenticate(user, password):
            # If we are in a process context, update its UID?
            # Usually login spawns a NEW shell with that UID.
            # But here the shell asks to login.
            # We return True, and the shell updates its state.
            return True
        return False

    def sys_user_list(self):
        return self.user_manager.list_users()

    def sys_user_add(self, user, password):
        # Only root can add users?
        if self._get_current_uid() != "root": return False
        return self.user_manager.add_user(user, password)

    def sys_user_delete(self, user):
        if self._get_current_uid() != "root": return False
        return self.user_manager.delete_user(user)

    def _get_current_uid(self):
        if self.scheduler and self.scheduler.current_process:
            return self.scheduler.current_process.uid
        return "root" # Kernel/System context

    # Filesystem
    def sys_ls(self, path="/"):
        uid = self._get_current_uid()
        return self.fs.list_dir(path, uid)

    def sys_read(self, path):
        uid = self._get_current_uid()
        return self.fs.read_file(path, uid)

    def sys_write(self, path, data):
        uid = self._get_current_uid()
        self.fs.write_file(path, data, uid)
        self.sys_log(f"[fs] write {path} by {uid}")
        return True

    def sys_append(self, path, text):
        uid = self._get_current_uid()
        self.fs.append_file(path, text, uid)
        return True

    def sys_delete(self, path):
        # Need to implement delete in FS first?
        # Checking filesystem.py... it doesn't have delete.
        # But SyscallHandler should expose it if we add it.
        # Wait, I cannot modify filesystem.py easily if I didn't plan it?
        # Actually I can.
        # Let's assume FS needs update too.
        # For now, I'll implement a workaround or update FS.
        # Since FS is in memory, I can just traverse and del.
        uid = self._get_current_uid()
        # Permission check
        # We need to resolve parent and remove child.
        # Let's do it directly here or modify FS.
        # Ideally modify FS.

        try:
            # Re-implementing delete logic here for speed if FS lacks it
            # But wait, self.fs is FileSystem instance.
            # I should add delete to FileSystem.
            # I will modify filesystem.py in next step or use this hack?
            # Better to be clean.
            # I'll modify filesystem.py in the plan step.
            # Wait, I can't modify filesystem.py in this "overwrite syscalls" block.
            # So I will assume I will modify filesystem.py next.
            self.fs.delete_file(path, uid)
            self.sys_log(f"[fs] delete {path} by {uid}")
            return True
        except Exception as e:
            return False

    def sys_kill(self, pid, sig="SIGTERM"):
        if not self.scheduler: return False

        # Permission check? Only root or owner can kill?
        current_uid = self._get_current_uid()

        for p in self.scheduler.processes:
            if p.pid == pid:
                if current_uid != "root" and p.uid != current_uid:
                     self.sys_log(f"kill denied for {current_uid} on {pid}")
                     return False

                p.deliver_signal(sig)
                self.sys_log(f"signal {sig} to {pid}")
                return True
        return False

    def sys_send(self, pid, message):
        if not self.scheduler: return False
        for p in self.scheduler.processes:
            if p.pid == pid:
                p.send(message)
                return True
        return False

    def sys_recv(self):
        if not self.scheduler or not self.scheduler.current_process:
            return None
        proc = self.scheduler.current_process
        return proc.receive()

    def sys_proc_list(self):
        if not self.scheduler: return []
        out = []
        for p in self.scheduler.processes:
            out.append({
                "pid": p.pid,
                "name": p.name,
                "state": p.state.name,
                "cpu": p.cpu_time,
                "uid": p.uid
            })
        return out

    # System Control
    def sys_shutdown(self):
        self.sys_log("System shutdown requested.")
        if self.scheduler:
            self.scheduler.running = False
            self.scheduler.exit_reason = "SHUTDOWN"
        return True

    def sys_reboot(self):
        self.sys_log("System reboot requested.")
        if self.scheduler:
            self.scheduler.running = False
            self.scheduler.exit_reason = "REBOOT"
        return "REBOOT"

    # Agent / DOM
    def sys_get_state(self):
        """
        Returns a structured representation of the system state.
        Useful for Agents.
        """
        state = {
            "processes": self.sys_proc_list(),
            "cwd": self.sys_ls("/") # Root for now, but should be caller CWD if known
            # CWD is a shell concept, not kernel.
            # But we can perhaps introspect the process env if we stored CWD there?
        }
        # Try to get CWD from current process if it's the shell
        if self.scheduler and self.scheduler.current_process:
             # If the process has 'cwd' in env?
             pass
        return state

    # Logging
    def sys_log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {msg}"
        # print(f"[syslog] {line}")
        # Log to file (root permission implied for system logs)
        try:
            self.fs.append_file("/var/log/journal/kernel.log", line, "root")
        except:
            pass # Boot time issues
        return True
