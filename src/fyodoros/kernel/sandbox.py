# kernel/sandbox.py
"""
Agent Sandbox Enforcement.

This module restricts the AI Agent's actions to a safe, confined environment.
It leverages a C++ extension (`sandbox_core`) for robust path resolution and
process isolation, ensuring the agent cannot break out of its designated workspace.
"""

import sys
import os
from pathlib import Path
from fyodoros.kernel.confirmation import ConfirmationManager

# Add core path to sys.path
core_path = Path(__file__).parent / "core"
sys.path.append(str(core_path))

try:
    import sandbox_core
except ImportError:
    # print("Warning: C++ Sandbox Core not found. Compilation needed?")
    sandbox_core = None


class AgentSandbox:
    """
    Restricts Agent actions to safe boundaries.

    Now delegates actual filesystem operations to SyscallHandler,
    which uses VirtualRootFS for path resolution and safety.

    Attributes:
        sys (SyscallHandler): The system call handler.
        confirmation (ConfirmationManager): Security confirmation system.
        core (SandboxCore): The C++ sandbox backend instance (for execution).
    """
    def __init__(self, syscall_handler):
        """
        Initialize the AgentSandbox.

        Args:
            syscall_handler (SyscallHandler): The kernel syscall handler.
        """
        self.sys = syscall_handler
        self.confirmation = ConfirmationManager()
        self.root_path = str(Path.home() / ".fyodor" / "sandbox")

        if sandbox_core:
            self.core = sandbox_core.SandboxCore(self.root_path)
        else:
            self.core = None

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

        # NOTE: With VirtualRootFS, we just pass the path to the system call.
        # However, for backward compatibility and clarity, if the agent
        # asks to read "foo.txt", it usually implies relative to the sandbox.
        # But SyscallHandler.sys_ls("/") lists the root of the RAM disk.
        # The agent usually sees the RAM disk now.
        # BUT, if the agent wants to access the sandbox, it must use "/sandbox/..."
        # OR we assume the agent's CWD is /sandbox?

        # In the previous implementation, `_resolve("foo.txt")` mapped to `~/.fyodor/sandbox/foo.txt`.
        # To maintain "Zero-Logic-Drift", we should preserve this behavior IF the agent thinks it's in a sandbox.
        # But the Requirement says "All file I/O must pass through the new rootfs module".

        # If the Agent says "read_file foo.txt", and we pass it to `sys.sys_read("foo.txt")`:
        # - `rootfs` sees "foo.txt". It's not starting with "/sandbox".
        # - It checks RAMDISK. If RAMDISK has "foo.txt" in root, it reads it.
        # - If not, it fails.

        # PREVIOUSLY: `_resolve("foo.txt")` -> HOST `.../sandbox/foo.txt`.

        # So, we MUST prefix paths with `/sandbox/` if we want to target the sandbox,
        # OR `AgentSandbox` needs to prepend it to maintain behavior.

        # Given "Backward Compatibility: Existing users must be migrated safely",
        # existing Agents expect "read_file foo.txt" to read from their sandbox.

        # So I will prepend "/sandbox/" to paths that are not absolute?
        # Or just assume all Agent file ops target `/sandbox` unless specified?
        # The AgentSandbox IS the sandbox. So yes.

        def to_sandbox_path(p):
            # If it already starts with /sandbox, leave it.
            # If it is absolute but not /sandbox, it might be trying to read system files (RAM disk).
            # If the Agent is allowed to read RAM disk (like /var/log), we should let it.
            # But `AgentSandbox` is supposed to restrict to "safe boundaries".
            # The previous `_resolve` FORCED everything into `~/.fyodor/sandbox`.
            # So `read_file /etc/passwd` would try to read `~/.fyodor/sandbox/etc/passwd`.

            # To strictly maintain this behavior:
            # We map everything to `/sandbox/...` in the new VirtualRootFS.
            if str(p).startswith("/"):
                 # Strip leading slash to make it relative to /sandbox
                 # e.g. /etc/hosts -> /sandbox/etc/hosts
                 return f"/sandbox/{str(p).lstrip('/')}"
            return f"/sandbox/{p}"

        if action == "read_file":
            path = to_sandbox_path(args[0])
            try:
                return self.sys.sys_read(path)
            except Exception as e:
                return f"Error: {e}"

        elif action == "write_file":
            path = to_sandbox_path(args[0])
            content = args[1]
            try:
                self.sys.sys_write(path, content)
                return f"Successfully wrote to {args[0]}"
            except Exception as e:
                return f"Error: {e}"

        elif action == "append_file":
            path = to_sandbox_path(args[0])
            content = args[1]
            try:
                self.sys.sys_append(path, content)
                return f"Successfully appended to {args[0]}"
            except Exception as e:
                return f"Error: {e}"

        elif action == "list_dir":
            path = args[0] if args else ""
            target = to_sandbox_path(path)
            try:
                files = self.sys.sys_ls(target)
                return "\n".join(files)
            except Exception as e:
                return f"Error: {e}"

        elif action == "delete_file":
            path = to_sandbox_path(args[0])
            try:
                if self.sys.sys_delete(path):
                    return f"Successfully deleted {args[0]}"
                else:
                    return f"Failed to delete {args[0]}"
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
                    mod = import_module(f"fyodoros.bin.{prog}")
                    if hasattr(mod, "main"):
                        return mod.main(prog_args, self.sys)
                    else:
                        return f"Error: {prog} has no main()"
                except ImportError:
                    # Fallback to C++ Core for real binaries if available
                    if self.core:
                         try:
                             res = self.core.execute(prog, prog_args, {})
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

        return f"Unknown or disallowed action: {action}"
