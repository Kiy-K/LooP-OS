# kernel/syscalls.py
"""
System Call Handler.

This module acts as the interface between user-space (processes/agents) and
kernel-space resources (filesystem, network, process management).
It handles permission checking and dispatches requests to the appropriate subsystems.
"""

import time
import json
from fyodoros.kernel.filesystem import FileSystem
from fyodoros.kernel.users import UserManager
from fyodoros.kernel.network import NetworkManager
from fyodoros.kernel.cloud.docker_interface import DockerInterface
from fyodoros.kernel.cloud.k8s_interface import KubernetesInterface

class SyscallHandler:
    """
    Handles system calls from processes.

    Attributes:
        fs (FileSystem): The filesystem instance.
        scheduler (Scheduler): The process scheduler.
        user_manager (UserManager): User management system.
        network_manager (NetworkManager): Network management system.
        sandbox (AgentSandbox): The sandbox instance (optional).
    """
    def __init__(self, scheduler=None, user_manager=None, network_manager=None):
        """
        Initialize the SyscallHandler.

        Args:
            scheduler (Scheduler, optional): The process scheduler.
            user_manager (UserManager, optional): User manager instance.
            network_manager (NetworkManager, optional): Network manager instance.
        """
        self.fs = FileSystem()
        self.scheduler = scheduler
        self.user_manager = user_manager or UserManager()
        self.network_manager = network_manager or NetworkManager(self.user_manager)
        self.docker_interface = DockerInterface()
        self.k8s_interface = KubernetesInterface()
        self.sandbox = None

    def set_scheduler(self, scheduler):
        """
        Set the scheduler instance.

        Args:
            scheduler (Scheduler): The scheduler.
        """
        self.scheduler = scheduler

    def set_sandbox(self, sandbox):
        """
        Set the sandbox instance.

        Args:
            sandbox (AgentSandbox): The sandbox.
        """
        self.sandbox = sandbox

    # Authentication
    def sys_login(self, user, password):
        """
        Authenticate a user.

        Args:
            user (str): Username.
            password (str): Password.

        Returns:
            bool: True if authentication successful.
        """
        if self.user_manager.authenticate(user, password):
            return True
        return False

    def sys_user_list(self):
        """
        List all users.

        Returns:
            dict: A dictionary of user info.
        """
        return self.user_manager.list_users()

    def sys_user_add(self, user, password):
        """
        Add a new user. Only 'root' can perform this.

        Args:
            user (str): Username.
            password (str): Password.

        Returns:
            bool: True if successful, False otherwise.
        """
        # Only root can add users?
        if self._get_current_uid() != "root": return False
        return self.user_manager.add_user(user, password)

    def sys_user_delete(self, user):
        """
        Delete a user. Only 'root' can perform this.

        Args:
            user (str): Username to delete.

        Returns:
            bool: True if successful, False otherwise.
        """
        if self._get_current_uid() != "root": return False
        return self.user_manager.delete_user(user)

    def _get_current_uid(self):
        """
        Get the UID of the currently running process.

        Returns:
            str: The UID, or "root" if running in kernel context.
        """
        if self.scheduler and self.scheduler.current_process:
            return self.scheduler.current_process.uid
        return "root" # Kernel/System context

    # Filesystem
    def sys_ls(self, path="/"):
        """
        List directory contents.

        Args:
            path (str): The path to list.

        Returns:
            list[str]: List of filenames.
        """
        uid = self._get_current_uid()
        return self.fs.list_dir(path, uid)

    def sys_read(self, path):
        """
        Read a file.

        Args:
            path (str): File path.

        Returns:
            str: File content.
        """
        uid = self._get_current_uid()
        return self.fs.read_file(path, uid)

    def sys_write(self, path, data):
        """
        Write to a file.

        Args:
            path (str): File path.
            data (str): Content to write.

        Returns:
            bool: True.
        """
        uid = self._get_current_uid()
        self.fs.write_file(path, data, uid)
        self.sys_log(f"[fs] write {path} by {uid}")
        return True

    def sys_append(self, path, text):
        """
        Append text to a file.

        Args:
            path (str): File path.
            text (str): Content to append.

        Returns:
            bool: True.
        """
        uid = self._get_current_uid()
        self.fs.append_file(path, text, uid)
        return True

    def sys_delete(self, path):
        """
        Delete a file.

        Args:
            path (str): File path.

        Returns:
            bool: True if successful, False otherwise.
        """
        uid = self._get_current_uid()
        try:
            self.fs.delete_file(path, uid)
            self.sys_log(f"[fs] delete {path} by {uid}")
            return True
        except Exception as e:
            return False

    def sys_kill(self, pid, sig="SIGTERM"):
        """
        Send a signal to a process.

        Args:
            pid (int): Process ID.
            sig (str): Signal name.

        Returns:
            bool: True if signal sent, False otherwise.
        """
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
        """
        Send an IPC message to a process.

        Args:
            pid (int): Process ID.
            message (any): The message.

        Returns:
            bool: True if sent, False otherwise.
        """
        if not self.scheduler: return False
        for p in self.scheduler.processes:
            if p.pid == pid:
                p.send(message)
                return True
        return False

    def sys_recv(self):
        """
        Receive an IPC message for the current process.

        Returns:
            any: The message, or None.
        """
        if not self.scheduler or not self.scheduler.current_process:
            return None
        proc = self.scheduler.current_process
        return proc.receive()

    def sys_proc_list(self):
        """
        List all running processes.

        Returns:
            list[dict]: A list of process details.
        """
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
        """
        Get current network status.

        Returns:
            str: "active" or "inactive".
        """
        return "active" if self.network_manager.is_enabled() else "inactive"

    def sys_net_set_status(self, status):
        """
        Enable/Disable network.
        Requires root or 'manage_network' permission.

        Args:
            status (str/bool): The new status.

        Returns:
            bool: True if successful, False if denied.
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

        Returns:
            bool: True if allowed.
        """
        user = self._get_current_uid()
        return self.network_manager.check_access(user)

    # Execution
    def sys_exec_nasm(self, source_code):
        """
        Execute NASM code via Sandbox.
        Requires 'execute_code' permission.

        Args:
            source_code (str): The assembly code to run.

        Returns:
            dict: The execution result or error.
        """
        user = self._get_current_uid()
        if user != "root" and not self.user_manager.has_permission(user, "execute_code"):
            return {"error": "Permission Denied"}

        if not self.sandbox:
            return {"error": "Sandbox not available"}

        return self.sandbox.execute("run_nasm", [source_code])

    # Docker Integration
    def _check_docker_permission(self):
        """Helper to check docker permissions."""
        user = self._get_current_uid()
        if user == "root":
            return True
        return self.user_manager.has_permission(user, "manage_docker")

    def sys_docker_login(self, username, password, registry="https://index.docker.io/v1/"):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        return self.docker_interface.login(username, password, registry)

    def sys_docker_logout(self, registry="https://index.docker.io/v1/"):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        return self.docker_interface.logout(registry)

    def sys_docker_build(self, path, tag, dockerfile="Dockerfile"):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        return self.docker_interface.build_image(path, tag, dockerfile)

    def sys_docker_run(self, image, name=None, ports=None, env=None):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}

        # Agent might send JSON strings
        try:
            if isinstance(ports, str):
                ports = json.loads(ports)
            if isinstance(env, str):
                env = json.loads(env)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON format for ports/env: {str(e)}"}

        return self.docker_interface.run_container(image, name, ports, env)

    def sys_docker_ps(self, all=False):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        return self.docker_interface.list_containers(all=all)

    def sys_docker_stop(self, container_id):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        return self.docker_interface.stop_container(container_id)

    def sys_docker_logs(self, container_id, tail=100):
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        return self.docker_interface.get_logs(container_id, tail)

    # Kubernetes Integration
    def _check_k8s_permission(self):
        """Helper to check k8s permissions."""
        user = self._get_current_uid()
        if user == "root":
            return True
        return self.user_manager.has_permission(user, "manage_k8s")

    def sys_k8s_deploy(self, name, image, replicas=1, namespace="default"):
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        return self.k8s_interface.create_deployment(name, image, replicas, namespace)

    def sys_k8s_scale(self, name, replicas, namespace="default"):
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        return self.k8s_interface.scale_deployment(name, replicas, namespace)

    def sys_k8s_delete(self, name, namespace="default"):
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        return self.k8s_interface.delete_deployment(name, namespace)

    def sys_k8s_get_pods(self, namespace="default"):
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        return self.k8s_interface.get_pods(namespace)

    def sys_k8s_logs(self, pod_name, namespace="default"):
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        return self.k8s_interface.get_pod_logs(pod_name, namespace)

    # System Control
    def sys_shutdown(self):
        """
        Initiate system shutdown.

        Returns:
            bool: True.
        """
        self.sys_log("System shutdown requested.")
        if self.scheduler:
            self.scheduler.running = False
            self.scheduler.exit_reason = "SHUTDOWN"
        return True

    def sys_reboot(self):
        """
        Initiate system reboot.

        Returns:
            str: "REBOOT" status.
        """
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

        Returns:
            dict: System state.
        """
        state = {
            "processes": self.sys_proc_list(),
            "cwd": self.sys_ls("/") # Root for now, but should be caller CWD if known
        }
        return state

    # Logging
    def sys_log(self, msg):
        """
        Log a message to the system journal.

        Args:
            msg (str): Message to log.

        Returns:
            bool: True.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {msg}"
        try:
            self.fs.append_file("/var/log/journal/kernel.log", line, "root")
        except:
            pass # Boot time issues
        return True
