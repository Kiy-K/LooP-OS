# kernel/syscalls.py
"""
System Call Handler.

This module acts as the interface between user-space (processes/agents) and
kernel-space resources (filesystem, network, process management).
It handles permission checking and dispatches requests to the appropriate subsystems.
"""

import time
import json
import os
from fyodoros.kernel.filesystem import FileSystem
from fyodoros.kernel.users import UserManager
from fyodoros.kernel.network import NetworkManager
from fyodoros.kernel.cloud.docker_interface import DockerInterface
from fyodoros.kernel.cloud.k8s_interface import KubernetesInterface
from fyodoros.kernel.memory import MemoryManager


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
        self.memory_manager = MemoryManager()
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

    def _get_current_groups(self):
        """
        Get the groups (roles) of the currently running process.
        """
        uid = self._get_current_uid()
        if uid == "root":
            return ["root", "admin"]
        return self.user_manager.get_roles(uid)

    # Filesystem Helpers
    def _resolve_sandbox_path(self, path):
        """
        Check if path targets the sandbox.
        Returns (is_sandbox, real_path)
        """
        if self.sandbox:
            # AgentSandbox._resolve returns absolute paths rooted at sandbox.root_path
            # We check if the incoming path starts with that root.
            root = self.sandbox.root_path
            if path.startswith(root):
                return True, path
        return False, path

    # Filesystem
    def sys_ls(self, path="/"):
        """
        List directory contents.

        Args:
            path (str): The path to list.

        Returns:
            list[str]: List of filenames.
        """
        # Check Sandbox First
        is_sb, real_path = self._resolve_sandbox_path(path)
        if is_sb and os.path.exists(real_path):
            if os.path.isdir(real_path):
                return os.listdir(real_path)
            else:
                return [os.path.basename(real_path)]

        # Fallback to In-Memory
        uid = self._get_current_uid()
        node_type = self.fs.get_node_type(path)

        groups = self._get_current_groups()
        if node_type == 'dir':
            return self.fs.list_dir(path, uid, groups)
        elif node_type == 'file':
            # Verify read permission by trying to read?
            # Or just assume ls permission implies seeing the name.
            # But standard ls requires access to parent.
            # self.fs.list_dir checks 'r' on directory.
            # Here we just return the name if it exists as file.
            return [path.split("/")[-1]]
        elif node_type is None:
            # Not found
            raise FileNotFoundError(f"Path not found: {path}")

        # Should not happen
        raise ValueError("Unknown node type")

    def sys_read(self, path):
        """
        Read a file.

        Args:
            path (str): File path.

        Returns:
            str: File content.
        """
        is_sb, real_path = self._resolve_sandbox_path(path)
        if is_sb and os.path.exists(real_path) and os.path.isfile(real_path):
            with open(real_path, 'r') as f:
                return f.read()

        uid = self._get_current_uid()
        groups = self._get_current_groups()
        return self.fs.read_file(path, uid, groups)

    def sys_write(self, path, data):
        """
        Write to a file.

        Args:
            path (str): File path.
            data (str): Content to write.

        Returns:
            bool: True.
        """
        is_sb, real_path = self._resolve_sandbox_path(path)
        if is_sb:
            # Check parent existence for sandbox
            parent = os.path.dirname(real_path)
            if not os.path.exists(parent):
                os.makedirs(parent)
            with open(real_path, 'w') as f:
                f.write(data)
            self.sys_log(f"[fs-sandbox] write {path}")
            return True

        uid = self._get_current_uid()
        groups = self._get_current_groups()
        # Explicitly passing groups to match FileSystem API and Test Expectations
        self.fs.write_file(path, data, uid, groups)
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
        is_sb, real_path = self._resolve_sandbox_path(path)
        if is_sb:
            parent = os.path.dirname(real_path)
            if not os.path.exists(parent):
                os.makedirs(parent)
            with open(real_path, 'a') as f:
                f.write(text + "\n")
            return True

        uid = self._get_current_uid()
        groups = self._get_current_groups()
        self.fs.append_file(path, text, uid, groups)
        return True

    def sys_delete(self, path):
        """
        Delete a file.

        Args:
            path (str): File path.

        Returns:
            bool: True if successful, False otherwise.
        """
        is_sb, real_path = self._resolve_sandbox_path(path)
        if is_sb:
            try:
                if os.path.isdir(real_path):
                    os.rmdir(real_path) # Only empty
                else:
                    os.remove(real_path)
                self.sys_log(f"[fs-sandbox] delete {path}")
                return True
            except Exception:
                return False

        uid = self._get_current_uid()
        groups = self._get_current_groups()
        try:
            self.fs.delete_file(path, uid, groups)
            self.sys_log(f"[fs] delete {path} by {uid}")
            return True
        except Exception as e:
            # We swallow exception here but maybe we should log it?
            # Or better, return failure.
            # The original code swallowed it.
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

        try:
            return self.sandbox.execute("run_nasm", [source_code])
        except Exception as e:
            return {"error": str(e)}

    # Docker Integration
    def _check_docker_permission(self):
        """Helper to check docker permissions."""
        user = self._get_current_uid()
        if user == "root":
            return True
        return self.user_manager.has_permission(user, "manage_docker")

    def sys_docker_login(self, username, password, registry="https://index.docker.io/v1/"):
        """
        Log in to a Docker registry.

        Args:
            username (str): Username.
            password (str): Password.
            registry (str, optional): Registry URL.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        try:
            return self.docker_interface.login(username, password, registry)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_docker_logout(self, registry="https://index.docker.io/v1/"):
        """
        Log out from a Docker registry.

        Args:
            registry (str, optional): Registry URL.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        try:
            return self.docker_interface.logout(registry)
        except Exception as e:
             return {"success": False, "error": str(e)}

    def sys_docker_build(self, path, tag, dockerfile="Dockerfile"):
        """
        Build a Docker image.

        Args:
            path (str): Build context path.
            tag (str): Image tag.
            dockerfile (str, optional): Dockerfile name.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        try:
            return self.docker_interface.build_image(path, tag, dockerfile)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_docker_run(self, image, name=None, ports=None, env=None):
        """
        Run a Docker container.

        Args:
            image (str): Image name.
            name (str, optional): Container name.
            ports (dict/str, optional): Port mapping.
            env (dict/str, optional): Environment variables.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}

        # Agent might send JSON strings
        try:
            if isinstance(ports, str):
                ports = json.loads(ports)
            if isinstance(env, str):
                env = json.loads(env)
            return self.docker_interface.run_container(image, name, ports, env)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON format for ports/env: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_docker_ps(self, all=False):
        """
        List Docker containers.

        Args:
            all (bool, optional): List all containers.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        try:
            return self.docker_interface.list_containers(all=all)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_docker_stop(self, container_id):
        """
        Stop a Docker container.

        Args:
            container_id (str): Container ID or name.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        try:
            return self.docker_interface.stop_container(container_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_docker_logs(self, container_id, tail=100):
        """
        Get Docker container logs.

        Args:
            container_id (str): Container ID or name.
            tail (int, optional): Number of lines.

        Returns:
            dict: Success status or error.
        """
        if not self._check_docker_permission():
            return {"success": False, "error": "Permission Denied: manage_docker required"}
        try:
            return self.docker_interface.get_logs(container_id, tail)
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Kubernetes Integration
    def _check_k8s_permission(self):
        """Helper to check k8s permissions."""
        user = self._get_current_uid()
        if user == "root":
            return True
        return self.user_manager.has_permission(user, "manage_k8s")

    def sys_k8s_deploy(self, name, image, replicas=1, namespace="default"):
        """
        Deploy to Kubernetes.

        Args:
            name (str): Deployment name.
            image (str): Container image.
            replicas (int, optional): Replica count.
            namespace (str, optional): Namespace.

        Returns:
            dict: Success status or error.
        """
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        try:
            return self.k8s_interface.create_deployment(name, image, replicas, namespace)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_k8s_scale(self, name, replicas, namespace="default"):
        """
        Scale a Kubernetes deployment.

        Args:
            name (str): Deployment name.
            replicas (int): New replica count.
            namespace (str, optional): Namespace.

        Returns:
            dict: Success status or error.
        """
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        try:
            return self.k8s_interface.scale_deployment(name, replicas, namespace)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_k8s_delete(self, name, namespace="default"):
        """
        Delete a Kubernetes deployment.

        Args:
            name (str): Deployment name.
            namespace (str, optional): Namespace.

        Returns:
            dict: Success status or error.
        """
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        try:
            return self.k8s_interface.delete_deployment(name, namespace)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_k8s_get_pods(self, namespace="default"):
        """
        Get Kubernetes pods.

        Args:
            namespace (str, optional): Namespace.

        Returns:
            dict: Success status or error.
        """
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        try:
            return self.k8s_interface.get_pods(namespace)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sys_k8s_logs(self, pod_name, namespace="default"):
        """
        Get logs from a Kubernetes pod.

        Args:
            pod_name (str): Pod name.
            namespace (str, optional): Namespace.

        Returns:
            dict: Success status or error.
        """
        if not self._check_k8s_permission():
            return {"success": False, "error": "Permission Denied: manage_k8s required"}
        try:
            return self.k8s_interface.get_pod_logs(pod_name, namespace)
        except Exception as e:
            return {"success": False, "error": str(e)}

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

    # Memory System
    def sys_memory_store(self, content, metadata=None):
        """
        Store a memory in the vector database.

        Args:
            content (str): The content to store.
            metadata (dict, optional): Metadata.

        Returns:
            str: Document ID.
        """
        return self.memory_manager.store(content, metadata)

    def sys_memory_search(self, query, limit=5):
        """
        Search memories.

        Args:
            query (str): The search query.
            limit (int): Max results.

        Returns:
            list: Matching memories.
        """
        return self.memory_manager.recall(query, n_results=limit)

    def sys_memory_recall(self, query, limit=5):
        """
        Alias for memory search (to match requirements).
        """
        return self.sys_memory_search(query, limit)
