# kernel/sandbox.py

class AgentSandbox:
    """
    Restricts Agent actions to safe boundaries.
    """
    def __init__(self, syscall_handler):
        self.sys = syscall_handler
        self.restricted_paths = ["/kernel", "/bin", "/boot", "/etc", "/var/log"]
        # Allow /home, /tmp (if exists), /var (except log?)

    def is_safe_path(self, path, operation="read"):
        """
        Check if the path is safe for the given operation.
        """
        # Normalize path? For now assume absolute or relative to valid cwd.
        # Ideally we resolve it.

        # Deny writes to system folders
        if operation in ["write", "append", "delete"]:
            for restricted in self.restricted_paths:
                if path.startswith(restricted):
                    # Exception: allow creating non-system files?
                    # No, strict safety for v1.
                    return False
            # Root is restricted
            if path == "/" or path == "":
                return False

        # Reads are generally okay, but maybe restrict reading secrets?
        # For now, allow reads everywhere (transparency).
        return True

    def execute(self, action, args):
        """
        Execute a command if it passes safety checks.
        action: str (e.g., "write_file")
        args: list or dict
        """
        if action == "read_file":
            path = args[0]
            if self.is_safe_path(path, "read"):
                try:
                    return self.sys.sys_read(path)
                except Exception as e:
                    return f"Error: {e}"
            else:
                return f"Permission Denied: Cannot read {path}"

        elif action == "write_file":
            path = args[0]
            content = args[1]
            if self.is_safe_path(path, "write"):
                try:
                    self.sys.sys_write(path, content)
                    return f"Successfully wrote to {path}"
                except Exception as e:
                    return f"Error: {e}"
            else:
                return f"Permission Denied: Cannot write to system path {path}"

        elif action == "append_file":
            path = args[0]
            content = args[1]
            if self.is_safe_path(path, "append"):
                try:
                    self.sys.sys_append(path, content)
                    return f"Successfully appended to {path}"
                except Exception as e:
                    return f"Error: {e}"
            else:
                return f"Permission Denied: Cannot modify system path {path}"

        elif action == "list_dir":
            path = args[0] if args else "/"
            # List is safe
            try:
                files = self.sys.sys_ls(path)
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
                    # We can use the shell's logic to run programs, or import directly.
                    # Since we are in the kernel layer, we should dynamically import from bin.
                    from importlib import import_module
                    mod = import_module(f"bin.{prog}")
                    if hasattr(mod, "main"):
                        # Pass syscall handler so apps can interact with kernel
                        return mod.main(prog_args, self.sys)
                    else:
                        return f"Error: {prog} has no main()"
                except ImportError:
                    return f"Error: App {prog} not found."
                except Exception as e:
                    return f"Error running {prog}: {e}"
            else:
                return f"Permission Denied: Agent cannot run '{prog}'. Allowed: {allowed_apps}"

        return f"Unknown or disallowed action: {action}"
