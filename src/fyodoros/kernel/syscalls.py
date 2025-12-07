# kernel/syscalls.py

import time
from fyodoros.kernel.filesystem import FileSystem
from fyodoros.kernel.users import UserManager
from fyodoros.kernel.network import NetworkManager

class SyscallHandler:
    def __init__(self, scheduler=None, user_manager=None, network_manager=None):
        self.fs = FileSystem()
        self.scheduler = scheduler
        self.user_manager = user_manager or UserManager()
        self.network_manager = network_manager or NetworkManager(self.user_manager)
        self.sandbox = None

    def set_scheduler(self, scheduler):
        self.scheduler = scheduler

    def set_sandbox(self, sandbox):
        self.sandbox = sandbox

    # Authentication
    def sys_login(self, user, password):
        if self.user_manager.authenticate(user, password):
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
        uid = self._get_current_uid()
        try:
            self.fs.delete_file(path, uid)
            self.sys_log(f"[fs] delete {path} by {uid}")
            return True
        except Exception as e:
            return False

    def sys_kill(self, pid, sig="SIGTERM"):
        if not self.scheduler: return False

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

    # Network Control
    def sys_net_status(self):
        return "active" if self.network_manager.is_enabled() else "inactive"

    def sys_net_set_status(self, status):
        """
        Enable/Disable network.
        Requires root or 'manage_network' permission.
        """
        user = self._get_current_uid()
        if user != "root" and not self.user_manager.has_permission(user, "manage_network"):
            return False

        enable = str(status).lower() in ("true", "1", "on", "yes", "enable")
        self.network_manager.set_enabled(enable)
        self.sys_log(f"Network set to {enable} by {user}")
        return True

    def sys_net_check_access(self):
        """
        Check if current user can access network.
        Returns True/False.
        """
        user = self._get_current_uid()
        return self.network_manager.check_access(user)

    # Execution
    def sys_exec_nasm(self, source_code):
        """
        Execute NASM code via Sandbox.
        Requires 'execute_code' permission.
        """
        user = self._get_current_uid()
        if user != "root" and not self.user_manager.has_permission(user, "execute_code"):
            return {"error": "Permission Denied"}

        if not self.sandbox:
            return {"error": "Sandbox not available"}

        return self.sandbox.execute("run_nasm", [source_code])

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
        }
        return state

    # Logging
    def sys_log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {msg}"
        try:
            self.fs.append_file("/var/log/journal/kernel.log", line, "root")
        except:
            pass # Boot time issues
        return True
