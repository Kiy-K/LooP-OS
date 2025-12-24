"""
Supervisor Module.

Manages host processes for the Shell.
Delegates low-level operations to psutil.
"""

import os
import psutil
import logging

logger = logging.getLogger("loop.kernel.shell.supervisor")

class Supervisor:
    """
    Manages host processes.
    """

    def __init__(self):
        self.current_user = self._get_current_user()

    def _get_current_user(self):
        """Gets the username of the current process."""
        try:
            return psutil.Process().username()
        except Exception:
            return None

    def get_process_list(self):
        """
        Returns a list of processes owned by the current user.

        Returns:
            list[dict]: A simplified list of processes.
        """
        procs = []
        try:
            # Pre-fetch attributes for speed
            for p in psutil.process_iter(['pid', 'name', 'username', 'memory_info']):
                try:
                    # Filter by user ownership to hide system daemons
                    if self.current_user and p.info['username'] != self.current_user:
                        continue

                    mem_mb = 0
                    if p.info['memory_info']:
                         mem_mb = round(p.info['memory_info'].rss / (1024 * 1024), 2)

                    procs.append({
                        "pid": p.info['pid'],
                        "name": p.info['name'],
                        "memory_mb": mem_mb
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.error(f"Failed to list processes: {e}")
            return []

        # Sort by memory usage descending? Or name?
        # Requirement didn't specify, but memory descending is usually useful.
        # Let's keep it simple (iterator order) for now to save cycles, or name.
        return procs

    def kill_process(self, pid):
        """
        Kills a process by PID.

        Args:
            pid (int): The process ID.

        Returns:
            dict: Success status or error.
        """
        # Safety Checks
        if pid == os.getpid():
            return {"success": False, "error": "Safety Restriction: Cannot kill self (loop-kernel)."}

        # On Windows/some envs, parent might be 0 or None, but usually ppid is safe to check
        if pid == os.getppid():
             return {"success": False, "error": "Safety Restriction: Cannot kill parent process."}

        try:
            p = psutil.Process(pid)
            p.terminate()
            # We could use p.kill() if terminate fails, but terminate is safer.
            return {"success": True, "message": f"Terminated PID {pid}"}
        except psutil.NoSuchProcess:
            return {"success": False, "error": "Process not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": "Permission Denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}
