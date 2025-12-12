# kernel/resource_monitor.py
"""
Resource Limits & Cost Tracking.

This module tracks resource usage (CPU, Memory, Network, Tokens) and
enforces limits configured in ~/.fyodor/config/limits.json.
"""

import json
import time
import psutil
from pathlib import Path
from collections import defaultdict

class ResourceMonitor:
    """
    Monitors system resource usage and enforces limits.
    """
    def __init__(self):
        self.config_path = Path.home() / ".fyodor" / "config" / "limits.json"
        self.stats_path = Path.home() / ".fyodor" / "run" / "resources.json"
        self.limits = self._load_limits()
        self.usage = self._load_stats()

        if "start_time" not in self.usage:
             self.usage["start_time"] = time.time()
        self.start_time = self.usage["start_time"]

        # Pricing per 1k tokens (approximate)
        self.pricing = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "mock": {"input": 0.0, "output": 0.0}
        }

    def _load_stats(self):
        """
        Load persisted stats or return default.
        """
        if self.stats_path.exists():
            try:
                with open(self.stats_path, "r") as f:
                    return defaultdict(float, json.load(f))
            except:
                pass
        return defaultdict(float)

    def _save_stats(self):
        """
        Persist stats to file.
        """
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.stats_path, "w") as f:
            json.dump(self.usage, f)

    def _load_limits(self):
        """
        Load limits from config file.
        """
        defaults = {
            "max_cpu_percent": 80.0,
            "max_memory_percent": 80.0,
            "max_tokens_per_task": 5000,
            "budget_per_session_usd": 1.0,
            "timeout_seconds": 300
        }

        if not self.config_path.exists():
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(defaults, f, indent=2)
            return defaults

        try:
            with open(self.config_path, "r") as f:
                return {**defaults, **json.load(f)}
        except:
            return defaults

    def check_system_health(self):
        """
        Check if system resources are within safe limits.

        Returns:
            bool: True if healthy, False if overloaded.
        """
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        if cpu > self.limits["max_cpu_percent"]:
            return False
        if mem > self.limits["max_memory_percent"]:
            return False
        return True

    def track_tokens(self, model, input_tokens, output_tokens):
        """
        Track token usage and calculate cost.
        """
        self.usage["total_tokens"] += (input_tokens + output_tokens)
        self.usage["input_tokens"] += input_tokens
        self.usage["output_tokens"] += output_tokens

        cost = 0.0
        if model in self.pricing:
            cost += (input_tokens / 1000) * self.pricing[model]["input"]
            cost += (output_tokens / 1000) * self.pricing[model]["output"]

        self.usage["total_cost"] += cost
        self._save_stats()

    def check_limits(self):
        """
        Check if usage limits have been exceeded.

        Returns:
            str or None: Error message if limit exceeded, else None.
        """
        if self.usage["total_tokens"] > self.limits["max_tokens_per_task"]:
            return f"Token limit exceeded: {self.usage['total_tokens']} > {self.limits['max_tokens_per_task']}"

        if self.usage["total_cost"] > self.limits["budget_per_session_usd"]:
             return f"Budget exceeded: ${self.usage['total_cost']:.4f} > ${self.limits['budget_per_session_usd']}"

        duration = time.time() - self.start_time
        if duration > self.limits["timeout_seconds"]:
            return f"Timeout exceeded: {duration:.1f}s > {self.limits['timeout_seconds']}s"

        return None

    def get_stats(self):
        """
        Get current stats.
        """
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "tokens": self.usage["total_tokens"],
            "cost": self.usage["total_cost"],
            "duration": time.time() - self.start_time
        }
