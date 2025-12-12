# kernel/action_logger.py
"""
Action Replay & Debugging Logger.

Logs every agent action to a JSON Lines file for debugging and replay.
"""

import json
import time
from pathlib import Path

class ActionLogger:
    """
    Logs agent actions and reasoning.
    """
    def __init__(self):
        self.log_dir = Path.home() / ".fyodor" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "actions.jsonl"

    def log_action(self, task_id, step, thought, action_name, args, result, duration_ms, tokens=0):
        """
        Log an action entry.
        """
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task_id": task_id,
            "step": step,
            "reasoning": thought,
            "action": action_name,
            "args": args,
            "result": str(result), # Ensure serializable
            "tokens_used": tokens,
            "duration_ms": duration_ms
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_logs(self, task_id=None, limit=None):
        """
        Retrieve logs, optionally filtered by task_id.
        """
        logs = []
        if not self.log_file.exists():
            return logs

        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if task_id and entry.get("task_id") != task_id:
                        continue
                    logs.append(entry)
                except:
                    continue

        if limit:
            return logs[-limit:]
        return logs

    def get_last_task_id(self):
        """
        Get the ID of the most recent task.
        """
        if not self.log_file.exists():
            return None

        # Read last line efficiently? For now just read all.
        last_id = None
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    last_id = entry.get("task_id")
                except:
                    continue
        return last_id
