# kernel/network.py
"""
Kernel Networking Management.

This module controls network access within FyodorOS. It manages the global network state
(enabled/disabled) and enforces it via monkey-patching the standard `socket` module.
It also integrates with `UserManager` to check user permissions.
"""

import os
import socket
import logging
from fyodoros.kernel.users import UserManager

class NetworkManager:
    """
    Manages the global network state and permission checks.

    State is persisted in the `.env` file to survive reboots.

    Attributes:
        user_manager (UserManager): Instance for permission validation.
        enabled (bool): Current network status.
    """
    ENV_KEY = "FYODOR_NETWORK_STATE"
    ENV_FILE = ".env"

    def __init__(self, user_manager=None):
        """
        Initialize the NetworkManager.

        Args:
            user_manager (UserManager, optional): User manager instance. Defaults to a new UserManager().
        """
        self.user_manager = user_manager or UserManager()
        self.enabled = False
        self._load_state()

    def _load_state(self):
        """
        Load the network state from the .env file or environment variables.
        """
        # Check .env file first (source of truth for live updates)
        state_str = None
        if os.path.exists(self.ENV_FILE):
            try:
                with open(self.ENV_FILE, "r") as f:
                    for line in f:
                        if line.startswith(f"{self.ENV_KEY}="):
                            state_str = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass

        # Fallback to env var (boot configuration)
        if not state_str:
            state_str = os.environ.get(self.ENV_KEY)

        if state_str and state_str.lower() == "on":
            self.enabled = True
        else:
            self.enabled = False

    def is_enabled(self):
        """
        Check if the network is currently enabled.
        Reloads state from disk to ensure freshness.

        Returns:
            bool: True if network is enabled.
        """
        # Reload state to ensure external changes (e.g., CLI) are picked up
        self._load_state()
        return self.enabled

    def set_enabled(self, enabled: bool):
        """
        Set the network state and persist it.

        Args:
            enabled (bool): True to enable, False to disable.
        """
        self.enabled = enabled
        self._save_state()
        # Update current process env so future calls see it
        os.environ[self.ENV_KEY] = "on" if enabled else "off"

    def _save_state(self):
        """
        Save the current state to the .env file.
        """
        # We need to update .env without destroying other keys
        lines = []
        key_found = False
        if os.path.exists(self.ENV_FILE):
            with open(self.ENV_FILE, "r") as f:
                lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.startswith(f"{self.ENV_KEY}="):
                new_lines.append(f"{self.ENV_KEY}={'on' if self.enabled else 'off'}\n")
                key_found = True
            else:
                new_lines.append(line)

        if not key_found:
            # Ensure we start on a new line if the file doesn't end with one
            if new_lines and not new_lines[-1].endswith('\n'):
                new_lines[-1] += '\n'
            new_lines.append(f"{self.ENV_KEY}={'on' if self.enabled else 'off'}\n")

        with open(self.ENV_FILE, "w") as f:
            f.writelines(new_lines)

    def check_access(self, user, permission="use_network"):
        """
        Checks if network is globally enabled AND if user has permission.

        Args:
            user (str): The username attempting access.
            permission (str, optional): The permission required. Defaults to "use_network".

        Returns:
            bool: True if access is granted.
        """
        if not self.enabled:
            return False

        if not self.user_manager.has_permission(user, permission):
            return False

        return True

class NetworkGuard:
    """
    Enforces network policy by monkey-patching the standard `socket` module.
    Blocks all network calls if the network is disabled.

    Attributes:
        manager (NetworkManager): The manager controlling the state.
        active (bool): Whether the guard is currently active (monkey-patched).
    """
    def __init__(self, network_manager):
        """
        Initialize the NetworkGuard.

        Args:
            network_manager (NetworkManager): The network manager instance.
        """
        self.manager = network_manager
        self._original_socket = socket.socket
        self._original_create_connection = socket.create_connection
        self._original_getaddrinfo = socket.getaddrinfo
        self.active = False

    def enable(self):
        """
        Activate the network guard (monkey-patch socket).
        """
        if self.active:
            return

        def guarded_socket(*args, **kwargs):
            if not self.manager.is_enabled():
                raise OSError("Network is disabled by system administrator (NetworkGuard)")
            return self._original_socket(*args, **kwargs)

        def guarded_create_connection(*args, **kwargs):
            if not self.manager.is_enabled():
                raise OSError("Network is disabled by system administrator (NetworkGuard)")
            return self._original_create_connection(*args, **kwargs)

        def guarded_getaddrinfo(*args, **kwargs):
             if not self.manager.is_enabled():
                raise OSError("Network is disabled by system administrator (NetworkGuard)")
             return self._original_getaddrinfo(*args, **kwargs)

        socket.socket = guarded_socket
        socket.create_connection = guarded_create_connection
        socket.getaddrinfo = guarded_getaddrinfo
        self.active = True
        logging.info("[NetworkGuard] Enforced.")

    def disable(self):
        """
        Deactivate the network guard (restore original socket methods).
        """
        if not self.active:
            return
        socket.socket = self._original_socket
        socket.create_connection = self._original_create_connection
        socket.getaddrinfo = self._original_getaddrinfo
        self.active = False
        logging.info("[NetworkGuard] Disabled.")
