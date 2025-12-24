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
import psutil
from loop.kernel import rootfs
from loop.kernel.users import UserManager
from loop.kernel.network import NetworkManager
from loop.kernel.cloud.docker_interface import DockerInterface
from loop.kernel.cloud.k8s_interface import KubernetesInterface
from loop.kernel.memory import MemoryManager
from loop.kernel.senses.ui_driver import UIDriver
from loop.kernel.senses.motor import Motor, StaleElementException
from loop.kernel.shell.launcher import AppLauncher
from loop.kernel.shell.supervisor import Supervisor
from loop.kernel.shell.window_manager import WindowManager
from loop.kernel.plugins.installer import PluginInstaller
from loop.kernel.plugins.loader import PluginLoader

class SyscallHandler:
    """
    Handles system calls from processes.

    Attributes:
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
        self.scheduler = scheduler
        self.user_manager = user_manager or UserManager()
        self.network_manager = network_manager or NetworkManager(self.user_manager)
        self.docker_interface = DockerInterface()
        self.k8s_interface = KubernetesInterface()
        self.memory_manager = MemoryManager()
        self.ui_driver = UIDriver()
        self.last_ui_scan = None
        self.motor = Motor()
        self.motor.start_kill_switch()

        # Shell Capabilities
        self.launcher = AppLauncher()
        self.supervisor = Supervisor()
        self.window_manager = WindowManager()

        # Plugins
        self.plugin_installer = PluginInstaller()
        self.plugin_loader = PluginLoader() # The loader is mostly used by the kernel, but syscalls might need introspection.

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
        if self._get_current_uid() != "root":
            return False
        return self.user_manager.add_user(user, password)

    def sys_user_delete(self, user):
        """
        Delete a user. Only 'root' can perform this.

        Args:
            user (str): Username to delete.

        Returns:
            bool: True if successful, False otherwise.
        """
        if self._get_current_uid() != "root":
            return False
        return self.user_manager.delete_user(user)

    def _get_current_uid(self):
        """
        Get the UID of the currently running process.

        Returns:
            str: The UID, or "root" if running in kernel context.
        """
        if self.scheduler and self.scheduler.current_process:
            return self.scheduler.current_process.uid
        return "root"  # Kernel/System context

    def _get_current_groups(self):
        """
        Get the groups (roles) of the currently running process.
        """
        uid = self._get_current_uid()
        if uid == "root":
            return ["root", "admin"]
        return self.user_manager.get_roles(uid)

    # Filesystem
    def sys_ls(self, path="/"):
        """
        List directory contents.

        Args:
            path (str): The path to list.

        Returns:
            list[str]: List of filenames.
        """
        try:
            real_path = rootfs.resolve(path)
            if not real_path.exists():
                raise FileNotFoundError(f"Path not found: {path}")

            if real_path.is_dir():
                return os.listdir(real_path)
            else:
                return [real_path.name]
        except Exception as e:
            # Re-raise specific errors or map to FileNotFoundError
            if isinstance(e, FileNotFoundError):
                raise e
            raise FileNotFoundError(f"Path not found or error accessing: {path} ({e})")

    def sys_read(self, path):
        """
        Read a file.

        Args:
            path (str): File path.

        Returns:
            str: File content.
        """
        real_path = rootfs.resolve(path)
        with open(real_path, "r") as f:
            return f.read()

    def sys_write(self, path, data):
        """
        Write to a file.

        Args:
            path (str): File path.
            data (str): Content to write.

        Returns:
            bool: True.
        """
        real_path = rootfs.resolve(path)
        # Ensure parent exists
        real_path.parent.mkdir(parents=True, exist_ok=True)

        with open(real_path, "w") as f:
            f.write(data)

        self.sys_log(f"[fs] write {path} by {self._get_current_uid()}")
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
        real_path = rootfs.resolve(path)
        # Ensure parent exists
        real_path.parent.mkdir(parents=True, exist_ok=True)

        with open(real_path, "a") as f:
            f.write(text + "\n")
        return True

    def sys_delete(self, path):
        """
        Delete a file.

        Args:
            path (str): File path.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            real_path = rootfs.resolve(path)
            if real_path.is_dir():
                os.rmdir(real_path)  # Only empty
            else:
                os.remove(real_path)
            self.sys_log(f"[fs] delete {path} by {self._get_current_uid()}")
            return True
        except Exception:
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
        if not self.scheduler:
            return False

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
        if not self.scheduler:
            return False
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
        List all running processes (Microkernel).

        Returns:
            list[dict]: A list of process details.
        """
        if not self.scheduler:
            return []
        out = []
        for p in self.scheduler.processes:
            out.append(
                {
                    "pid": p.pid,
                    "name": p.name,
                    "state": p.state.name,
                    "cpu": p.cpu_time,
                    "uid": p.uid,
                }
            )
        return out

    def sys_host_proc_list(self):
        """
        List processes running on the Host OS.
        Delegates to Supervisor.
        """
        return self.supervisor.get_process_list()

    def sys_host_proc_kill(self, pid):
        """
        Kill a Host OS process by PID.
        Delegates to Supervisor.
        """
        return self.supervisor.kill_process(pid)

    def sys_host_app_launch(self, app_name):
        """
        Launch a host application by name.
        Delegates to AppLauncher.
        """
        path = self.launcher.find_app(app_name)
        if not path:
             return {"success": False, "error": f"App '{app_name}' not found."}

        return self.launcher.launch(path)

    # Legacy alias, kept for compatibility if needed, but updated to use host syscall logic
    def sys_app_launch(self, app_name):
        return self.sys_host_app_launch(app_name)

    def sys_host_win_focus(self, query):
        """
        Focus a host window by title or PID.
        Delegates to WindowManager.
        """
        return self.window_manager.focus_window(query)

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
        if user != "root" and not self.user_manager.has_permission(
            user, "manage_network"
        ):
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
        if user != "root" and not self.user_manager.has_permission(
            user, "execute_code"
        ):
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

    def sys_docker_login(
        self, username, password, registry="https://index.docker.io/v1/"
    ):
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }
        try:
            # Docker build needs a real host path, resolve it!
            real_path = rootfs.resolve(path)
            return self.docker_interface.build_image(str(real_path), tag, dockerfile)
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }

        # Agent might send JSON strings
        try:
            if isinstance(ports, str):
                ports = json.loads(ports)
            if isinstance(env, str):
                env = json.loads(env)
            return self.docker_interface.run_container(image, name, ports, env)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON format for ports/env: {str(e)}",
            }
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }
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
            return {
                "success": False,
                "error": "Permission Denied: manage_docker required",
            }
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
            return self.k8s_interface.create_deployment(
                name, image, replicas, namespace
            )
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

    # Plugin Management
    def sys_plugin_list(self):
        """
        List all installed plugins (by directory presence).
        """
        # We can iterate the plugins directory directly
        # or ask the installer/loader.
        # Since 'loader' tracks loaded ones, but we want all installed:
        try:
            return [p.name for p in self.plugin_installer.plugins_dir.iterdir() if p.is_dir()]
        except Exception:
            return []

    def sys_plugin_install(self, name_or_url):
        """
        Install a plugin from Registry or Git URL.
        """
        user = self._get_current_uid()
        if user != "root":
             # Eventually check a permission, for now allow root/admin
             pass
        return self.plugin_installer.install_plugin(name_or_url)

    def sys_plugin_uninstall(self, name):
        """
        Uninstall a plugin.
        """
        return self.plugin_installer.uninstall_plugin(name)

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
            "cwd": self.sys_ls("/"),  # Root for now, but should be caller CWD if known
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
            self.sys_append("/var/logs/kernel.log", line)
        except:
            pass  # Boot time issues
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

    def sys_memory_delete(self, key_id=None, query=None):
        """
        Delete a memory by ID or query.
        """
        return self.memory_manager.delete(key_id, query)

    # Deprecated Mouse/Screen calls
    # sys_mouse_move and sys_capture_screen have been removed in v0.8.0
    # in favor of sys_ui_scan and sys_ui_act.

    # UI / Motor Control
    def sys_ui_scan(self):
        """
        Scan the active window and return a DOM tree.
        Stores the result in self.last_ui_scan.
        """
        result = self.ui_driver.scan_active_window()
        self.last_ui_scan = result
        return result

    def sys_ui_act(self, uid, action, payload=None):
        """
        Perform an action on a UI element.

        Args:
            uid (int): The Element UID.
            action (str): 'click', 'type', 'scroll'.
            payload (str): Optional data.

        Returns:
            dict: Success or error.
        """
        try:
            self.motor.execute_action(uid, action, payload)
            return {"success": True}
        except StaleElementException:
            return {"success": False, "error": "Stale Element. Re-scan required."}
        except Exception as e:
            return {"success": False, "error": str(e)}
