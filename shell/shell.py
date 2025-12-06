# shell/shell.py

import time
from kernel.process import Process
from importlib import import_module

class Shell:
    """
    Interactive shell for FyodorOS.
    Supports:
      - ls
      - cat
      - write
      - run <program>
      - ps
      - help
      - reboot
    """

    def __init__(self, syscall, supervisor=None):
        self.sys = syscall
        self.supervisor = supervisor
        self.cwd = "/"
        self.running = True
        self.current_user = None

    # ========== INPUT HANDLING ==========
    def _readline(self, prompt):
        print(prompt, end="", flush=True)
        return input().strip()

    def login(self):
        # We use standard input/print here because we might not have a running process yet
        # or we are the shell process.

        print("FyodorOS Login")
        print("Username: ", end="")
        user = input()
        print("Password: ", end="")
        pw = input()

        if self.sys.sys_login(user, pw):
            print(f"Welcome {user}!")
            self.current_user = user
            return True

        print("Login failed.")
        return False

    # ========== COMMAND EXECUTION ==========
    def run(self):
        """Generator for scheduling."""
        while self.running:
            cmd = self._readline(f"{self.current_user}@fyodoros:{self.cwd}> ")
            output = self.execute(cmd)
            if output:
                print(output)
            yield  # yield back to scheduler

    def execute(self, cmd):
        if not cmd:
            return ""

        parts = cmd.split()
        op = parts[0]
        args = parts[1:]

        try:
            if op == "ls":
                path = args[0] if args else self.cwd
                return "\n".join(self.sys.sys_ls(path))

            elif op == "cat":
                if len(args) < 1: return "Usage: cat <file>"
                return self.sys.sys_read(args[0])

            elif op == "write":
                if len(args) < 2: return "Usage: write <file> <text>"
                path, text = args[0], " ".join(args[1:])
                self.sys.sys_write(path, text)
                return f"Written to {path}"

            elif op == "append":
                if len(args) < 2: return "Usage: append <file> <text>"
                path, text = args[0], " ".join(args[1:])
                self.sys.sys_append(path, text)
                return f"Appended to {path}"

            elif op == "run":
                if len(args) < 1: return "Usage: run <program> [args]"
                return self._run_program(args)

            elif op == "ps":
                # Use syscall instead of supervisor direct access if possible
                procs = self.sys.sys_proc_list()
                out = ["PID    NAME    STATE    UID"]
                for p in procs:
                    out.append(f"{p['pid']:<6} {p['name']:<7} {p['state']:<8} {p['uid']}")
                return "\n".join(out)

            elif op == "run-service":
                if len(args) < 1:
                    return "Usage: run-service <service>"
                return self.supervisor.run_service(args[0])

            elif op == "journal":
                try:
                    return self.sys.sys_read("/var/log/journal/kernel.log")
                except:
                    return "(no logs yet)"

            elif op == "kill":
                if len(args) < 1:
                    return "Usage: kill <pid>"
                ok = self.sys.sys_kill(int(args[0]))
                return "Killed" if ok else "Failed (perm?)"

            elif op == "send":
                if len(args) < 2:
                    return "Usage: send <pid> <message>"
                ok = self.sys.sys_send(int(args[0]), " ".join(args[1:]))
                return "Sent" if ok else "Failed"

            elif op == "recv":
                return self.sys.sys_recv()

            elif op == "shutdown":
                return self.sys.sys_shutdown()

            elif op == "reboot":
                return self.sys.sys_reboot()

            elif op == "dom":
                state = self.sys.sys_get_state()
                return str(state)

            elif op == "help":
                return (
                    "Commands:\n"
                    "  ls                - list directory\n"
                    "  cat <file>        - read file\n"
                    "  write <f> <text>  - write file\n"
                    "  append <f> <text> - append file\n"
                    "  run <prog> args   - run program in /bin\n"
                    "  ps                - list processes\n"
                    "  reboot            - restart OS\n"
                    "  shutdown          - shutdown OS\n"
                    "  help              - show this\n"
                    "  journal           - show system logs\n"
                    "  run-service <svc> - start background service\n"
                    "  dom               - show system state (Agent)\n"
                )

            else:
                return f"Unknown command: {op}"

        except Exception as e:
            return f"[error] {e}"

    # ========== PROGRAM EXECUTION ==========
    def _run_program(self, args):
        program = args[0]
        prog_args = args[1:]

        try:
            mod = import_module(f"bin.{program}")
        except ImportError:
            return f"Program not found: {program}"
        except Exception as e:
            return f"Error loading program: {e}"

        if not hasattr(mod, "main"):
            return f"Program {program} has no main()"

        # Execute program
        # Ideally we should spawn a process for it.
        # But 'run' command here seems to execute it in-place (blocking shell).
        # To make it a process, we should use 'run-service' style or modify 'run' to spawn.
        # For now, keep as is.
        try:
            return mod.main(prog_args, self.sys)
        except Exception as e:
             return f"Program crashed: {e}"
