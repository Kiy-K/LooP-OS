# shell/shell.py

import time
import kernel
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
        self.kernel = kernel
        self.sys = kernel.sys # syscall interface
        self.sys = syscall
        self.supervisor = supervisor
        self.cwd = "/"
        self.running = True

    # ========== INPUT HANDLING ==========
    def _readline(self, prompt):
        print(prompt, end="", flush=True)
        return input().strip()

    def login(self):
        tty = self.sys.tty

        tty.write("FyodorOS Login\n")
        tty.write("Username: ")
        user = input("> ")
        tty.write("Password: ")
        pw = input("> ")

        if self.users.authenticate(user, pw):
            tty.write(f"Welcome {user}!\n")
            self.current_user = user
            return True

        tty.write("Login failed.\n")
        return False

    # ========== COMMAND EXECUTION ==========
    def run(self):
        tty = self.kernel.tty
        """Generator for scheduling."""
        while self.running:
            cmd = self._readline("> ")
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
                return "\n".join(self.sys.sys_ls(self.cwd))

            elif op == "cat":
                if len(args) < 1: return "Usage: cat <file>"
                return self.sys.sys_read(args[0])

            elif op == "write":
                if len(args) < 2: return "Usage: write <file> <text>"
                path, text = args[0], " ".join(args[1:])
                self.sys.sys_write(path, text)
                return f"Written to {path}"

            elif op == "run":
                if len(args) < 1: return "Usage: run <program> [args]"
                return self._run_program(args)

            elif op == "ps":
                procs = self.supervisor.list_processes()
                out = []
                for p in procs:
                    out.append(f"{p.pid[:6]}  {p.name}  {p.state.name}")
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
                return self.supervisor.kill_process(int(args[0]))

            elif op == "send":
                if len(args) < 2:
                    return "Usage: send <pid> <message>"
                return self.supervisor.send_message(int(args[0]), " ".join(args[1:]))

            elif op == "recv":
                return self.sys.sys_recv()

            elif op == "proc":
                return self.sys.sys_proc_list()

            elif op == "help":
                return (
                    "Commands:\n"
                    "  ls                - list directory\n"
                    "  cat <file>        - read file\n"
                    "  write <f> <text>  - write file\n"
                    "  run <prog> args   - run program in /bin\n"
                    "  ps                - list processes\n"
                    "  reboot            - restart OS\n"
                    "  help              - show this\n"
                    "  journal           - show system logs\n"
                    "  run-service <svc> - start background service\n"
                )

            elif op == "reboot":
                self.running = False
                return "[shell] Reboot requested."

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
        except:
            return f"Program not found: {program}"

        if not hasattr(mod, "main"):
            return f"Program {program} has no main()"

        return mod.main(prog_args, self.sys)
# --- IGNORE ---