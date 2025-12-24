# kernel/sandbox.py
"""
Agent Sandbox Enforcement.

This module restricts the AI Agent's actions to a safe, confined environment.
It leverages a C++ extension (`loop_sandbox`) for robust path resolution and
process isolation, ensuring the agent cannot break out of its designated workspace.
"""

import sys
import os
from pathlib import Path
from loop.kernel.confirmation import ConfirmationManager

# Add core path to sys.path
core_path = Path(__file__).parent / "core"
sys.path.append(str(core_path))

try:
    import loop_sandbox
except ImportError:
    print("Warning: C++ Sandbox Core not found. Compilation needed?")
    loop_sandbox = None


class AgentSandbox:
    """
    Restricts Agent actions to safe boundaries using C++ Core.

    Attributes:
        sys (SyscallHandler): The system call handler.
        root_path (str): The absolute path to the sandbox root (`~/.loop/sandbox`).
        core (SandboxCore): The C++ sandbox backend instance.
        confirmation (ConfirmationManager): Security confirmation system.
    """
    def __init__(self, syscall_handler):
        """
        Initialize the AgentSandbox.

        Args:
            syscall_handler (SyscallHandler): The kernel syscall handler.
        """
        self.sys = syscall_handler
        self.root_path = str(Path.home() / ".loop" / "sandbox")
        self.confirmation = ConfirmationManager()

        if loop_sandbox:
            self.core = loop_sandbox.SandboxCore(self.root_path)
        else:
            self.core = None

    def _resolve(self, path):
        """
        Resolve a path safely within the sandbox.

        Args:
            path (str): The relative path to resolve.

        Returns:
            str: The absolute path on the host system.

        Raises:
            PermissionError: If the path attempts to escape the sandbox.
        """
        if self.core:
            try:
                # Returns resolved absolute path on HOST
                return self.core.resolve_path(path)
            except Exception as e:
                raise PermissionError(f"Sandbox Violation: {e}")

        # Fallback: Secure Python Implementation
        # 1. Construct absolute target path
        # 2. Resolve symlinks and '..'
        # 3. Ensure it starts with sandbox root

        base = Path(self.root_path).resolve()
        target = (base / path).resolve()

        # Use commonpath to strictly verify containment (prevents sibling attacks like /var/sandbox_conf)
        try:
            if os.path.commonpath([base, target]) != str(base):
                 raise PermissionError(f"Sandbox Violation: Path {path} escapes sandbox root {base}")
        except ValueError:
             # Occurs if paths are on different drives on Windows, implying escape
             raise PermissionError(f"Sandbox Violation: Path {path} on different drive than {base}")

        return str(target)

    def execute(self, action, args):
        """
        Execute a sandboxed action.

        Args:
            action (str): The action name (e.g., 'read_file', 'run_process').
            args (list): List of arguments for the action.

        Returns:
            str or dict: The result of the action or an error message.
        """
        # Security Confirmation
        if not self.confirmation.request_approval(action, args):
            return "Action Denied by User"

        if action == "read_file":
            path = args[0]
            try:
                real_path = self._resolve(path)
                # We need to bypass syscall handler's internal path logic if possible,
                # or pass the resolved path. Syscall handler might not expect absolute host paths
                # if it thinks it's simulating an OS.
                # However, syscall_handler in this project seems to operate on real OS files directly?
                # Let's check syscall_handler implementation.
                # Assuming sys_read takes a path and opens it.
                return self.sys.sys_read(real_path)
            except Exception as e:
                return f"Error: {e}"

        elif action == "write_file":
            path = args[0]
            content = args[1]
            try:
                real_path = self._resolve(path)
                self.sys.sys_write(real_path, content)
                return f"Successfully wrote to {path}"
            except Exception as e:
                return f"Error: {e}"

        elif action == "append_file":
            path = args[0]
            content = args[1]
            try:
                real_path = self._resolve(path)
                self.sys.sys_append(real_path, content)
                return f"Successfully appended to {path}"
            except Exception as e:
                return f"Error: {e}"

        elif action == "list_dir":
            path = args[0] if args else "/"
            try:
                real_path = self._resolve(path)
                files = self.sys.sys_ls(real_path)
                return "\n".join(files)
            except Exception as e:
                return f"Error: {e}"

        elif action == "run_process":
            # Whitelisted apps for Agent
            allowed_apps = ["browser", "calc", "explorer", "system", "user"]

            prog = args[0]
            prog_args = args[1:] if len(args) > 1 else []

            if prog in allowed_apps:
                try:
                    # Built-in apps run in Python
                    from importlib import import_module
                    mod = import_module(f"loop.bin.{prog}")
                    if hasattr(mod, "main"):
                        return mod.main(prog_args, self.sys)
                    else:
                        return f"Error: {prog} has no main()"
                except ImportError:
                    # Not a built-in, maybe a real binary?
                    # Try executing via C++ Sandbox
                    if self.core:
                         try:
                             # We use empty env for strict isolation
                             # But we might need PATH?
                             # Let's map PATH to a safe bin dir if we had one.
                             res = self.core.execute(prog, prog_args, {})
                             # Return structured output if possible, or just stdout
                             if res["return_code"] == 0:
                                 return res["stdout"]
                             else:
                                 return f"Error (RC {res['return_code']}): {res['stderr']}"
                         except Exception as e:
                             return f"Execution Error: {e}"
                    return f"Error: App {prog} not found."
                except Exception as e:
                    return f"Error running {prog}: {e}"
            else:
                return f"Permission Denied: Agent cannot run '{prog}'. Allowed: {allowed_apps}"

        elif action == "read_screen":
            try:
                # Maps to sys_ui_scan
                return self.sys.sys_ui_scan()
            except Exception as e:
                return f"Error scanning screen: {e}"

        elif action == "interact":
            # Maps to sys_ui_act
            # args: [uid, action, payload=None]
            if len(args) < 2:
                return "Error: interact requires uid and action type (e.g., 'click')"

            uid = args[0]
            act_type = args[1]
            payload = args[2] if len(args) > 2 else None

            try:
                return self.sys.sys_ui_act(uid, act_type, payload)
            except Exception as e:
                return f"Error interacting: {e}"

        elif action == "run_nasm":
            # args[0] = source code
            # args[1] = optional output name (default: "nasm_prog")
            source = args[0]
            name = args[1] if len(args) > 1 else "nasm_prog"

            if self.core:
                try:
                    result = self.core.compile_and_run_nasm(source, name)
                    return result # Dict with stdout, stderr, return_code
                except Exception as e:
                    return {"error": str(e)}
            return {"error": "Sandbox Core not available"}

        elif action == "launch_app":
            app_name = args[0]
            try:
                # Map to sys_app_launch
                return self.sys.sys_app_launch(app_name)
            except Exception as e:
                return f"Error launching app: {e}"

        return f"Unknown or disallowed action: {action}"
