# shell/shell.py

import time
from fyodoros.kernel.process import Process
from importlib import import_module
from fyodoros.kernel.agent import ReActAgent

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
      - agent <task>
    """

    def __init__(self, syscall, supervisor=None):
        self.sys = syscall
        self.supervisor = supervisor
        self.cwd = "/"
        self.running = True
        self.current_user = None
        self.agent = None
        self.plugin_commands = {}

    def register_plugin_commands(self, commands):
        """
        Register commands provided by plugins.
        """
        self.plugin_commands.update(commands)

    # ========== INPUT HANDLING ==========
    def _readline(self, prompt):
        print(prompt, end="", flush=True)
        return input().strip()

    def login(self, auto_user=None, auto_pass=None):
        # We use standard input/print here because we might not have a running process yet
        # or we are the shell process.

        user = auto_user
        pw = auto_pass

        # If only user provided, ask for password
        if user and not pw:
             print("FyodorOS Login")
             print(f"Username: {user}")
             print("Password: ", end="")
             pw = input()

        # If neither, interactive
        if not user:
            print("FyodorOS Login")
            print("Username: ", end="")
            user = input()
            print("Password: ", end="")
            pw = input()

        if self.sys.sys_login(user, pw):
            print(f"Welcome {user}!")
            self.current_user = user
            return True

        print("Login failed. Auto-logging in as root.")
        self.current_user = "root"
        return True

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

            elif op == "create":
                if len(args) < 1: return "Usage: create <filename>"
                filename = args[0]
                if "." not in filename:
                    filename += ".txt"
                content = " ".join(args[1:]) if len(args) > 1 else ""
                self.sys.sys_write(filename, content)
                return f"Created {filename}"

            elif op == "navigate":
                if len(args) < 1 or args[0] in ["--help", "help", "list"]:
                    return "Available apps: browser, calc, explorer, system, user\nUsage: navigate <app> [args]"

                app_name = args[0]
                # Allow 'navigate browser' to map to 'run browser' logic
                # We reuse _run_program but need to adjust args to match 'run <prog> args' signature expected by _run_program
                # _run_program expects [prog, arg1, arg2...]
                return self._run_program(args)

            elif op == "agent":
                if len(args) < 1:
                    return "Usage: agent <task description>"
                task = " ".join(args)

                # Lazy Init Agent
                if not self.agent:
                    print("[Shell] Initializing Agent Layer...")
                    self.agent = ReActAgent(self.sys)

                print(f"[Shell] Dispatching task to Agent: '{task}'")
                return self.agent.run(task)

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
                    "  agent <task>      - give a task to the AI Agent\n"
                    "  create <file>     - create a file (default .txt)\n"
                    "  navigate <app>    - run a user app (browser, etc)\n"
                )

            elif op in self.plugin_commands:
                # Execute plugin command
                try:
                    return self.plugin_commands[op](*args)
                except Exception as e:
                    return f"Plugin command failed: {e}"

            else:
                return f"Unknown command: {op}"

        except Exception as e:
            return f"[error] {e}"

    # ========== PROGRAM EXECUTION ==========
    def _run_program(self, args):
        program = args[0]
        prog_args = args[1:]

        try:
            mod = import_module(f"fyodoros.bin.{program}")
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
