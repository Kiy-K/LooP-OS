import threading
import time
import json
import psutil
from pathlib import Path
from loop.plugins import Plugin


class UsageDashboardPlugin(Plugin):
    """
    Usage Dashboard plugin.
    Features: Background logging of system stats.
    """
    def __init__(self):
        """
        Initialize the UsageDashboardPlugin.
        Sets up the log directory and initial state.
        """
        self.running = False
        self.thread = None
        self.log_dir = Path.home() / ".loop" / "dashboard"
        self.log_file = self.log_dir / "stats.json"

    def setup(self, kernel):
        """
        Initialize the plugin with the kernel and start the monitoring thread.

        Args:
            kernel (Kernel): The active kernel instance.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        print("[UsageDashboard] Monitoring started.")

    def _monitor_loop(self):
        """
        Background loop to collect system statistics using `psutil`.
        Persists data to JSON file.
        """
        while self.running:
            try:
                stats = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "memory_percent": psutil.virtual_memory().percent,
                    "boot_time": psutil.boot_time()
                }
                # For simplicity, we just overwrite the current stats file for the TUI to read "live" status.
                # If we wanted history, we'd append to a log or use a time-series DB.
                # Given "dashboard" implies current state usually, or short history.
                # Let's keep a small history list in the file.

                history = []
                if self.log_file.exists():
                    try:
                        with open(self.log_file, "r") as f:
                            history = json.load(f)
                    except:
                        history = []

                history.append(stats)
                # Keep last 100 entries
                if len(history) > 100:
                    history = history[-100:]

                with open(self.log_file, "w") as f:
                    json.dump(history, f)

            except Exception as e:
                print(f"[UsageDashboard] Error in monitor loop: {e}")

            time.sleep(5) # Update every 5 seconds

    def stop(self):
        """
        Stop the monitoring thread.
        """
        self.running = False
        if self.thread:
            self.thread.join()

    def get_shell_commands(self):
        """
        Register shell commands (None for this plugin).

        Returns:
            dict: Empty dictionary.
        """
        return {}

    def get_agent_tools(self):
        """
        Register agent tools (None for this plugin).

        Returns:
            list: Empty list.
        """
        return []
