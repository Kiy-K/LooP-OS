# kernel/confirmation.py
"""
User Confirmation System.

Manages risk levels and requires explicit user approval for dangerous actions.
"""

import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm, Prompt

class ConfirmationManager:
    """
    Manages action confirmation based on risk level.
    """

    HIGH_RISK = ["delete", "rm", "modify_system", "network_write", "user_add", "user_delete"]
    MEDIUM_RISK = ["create", "write", "move", "network_read"]
    LOW_RISK = ["read", "list", "search"]

    def __init__(self):
        self.config_path = Path.home() / ".fyodor" / "config" / "trust.json"
        self.whitelist = self._load_whitelist()
        self.console = Console()

    def _load_whitelist(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except:
                return {"allowed_actions": []}
        return {"allowed_actions": []}

    def save_whitelist(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.whitelist, f)

    def assess_risk(self, action):
        """
        Determine risk level of an action.
        """
        # Determine based on action keyword
        # Map sandbox actions to risk categories
        # Actions: read_file, write_file, append_file, list_dir, run_process, sys_*

        # Explicit checks for specific actions
        if action == "run_process":
            # Running processes is inherently risky (MEDIUM by default)
            # We could inspect args[0] (app name) if we had args passed here,
            # but assess_risk currently only takes action name.
            # To be safe, we treat run_process as HIGH risk if we can't see args,
            # or update signature. But to avoid breaking signature:
            return "HIGH"

        if "delete" in action or "rm" in action or "user_" in action or "docker_stop" in action or "k8s_delete" in action:
            return "HIGH"

        if "write" in action or "append" in action or "create" in action or "docker_" in action or "k8s_" in action:
            return "MEDIUM"

        return "LOW"

    def request_approval(self, action, args):
        """
        Request user approval for an action.

        Returns:
            bool: True if approved, False otherwise.
        """
        risk = self.assess_risk(action)

        # Check whitelist
        if action in self.whitelist["allowed_actions"]:
            return True

        if risk == "LOW":
            return True

        # For CLI usage, we use Rich prompts.
        # But if this is running in background/kernel, we might block?
        # Requirement: "Add interactive prompt".
        # If the agent is running in the kernel process, and the user is attached via TUI, this works.
        # If fully headless, this might block indefinitely.
        # Assuming interactive session for now.

        self.console.print(f"\n[bold red]SECURITY ALERT ({risk} RISK)[/bold red]")
        self.console.print(f"Agent wants to execute: [cyan]{action}[/cyan]")
        self.console.print(f"Arguments: {args}")

        return Confirm.ask("Do you want to proceed?")

    def whitelist_action(self, action):
        if action not in self.whitelist["allowed_actions"]:
            self.whitelist["allowed_actions"].append(action)
            self.save_whitelist()
            return True
        return False
