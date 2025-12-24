# kernel/users.py
"""
User Management System.

This module handles user accounts, password hashing (via Argon2), and
Role-Based Access Control (RBAC). It persists user data to a JSON file.
"""

import hashlib
from argon2 import PasswordHasher
import json
import os
from pathlib import Path
from loop.kernel import rootfs


class UserManager:
    """
    Manages user authentication and authorization.

    Attributes:
        DB_FILE (Path): The path to the JSON database file (~/.loop/etc/users.json).
        _ph (PasswordHasher): Argon2 password hasher instance.
        users (dict): In-memory cache of user data.
    """
    # Use absolute path resolved via rootfs logic (though manually constructed here for class attr)
    # Ideally, we should not define this at class level if it depends on runtime env,
    # but rootfs.LOOP_ROOT is constant per run.
    DB_FILE = rootfs.LOOP_ROOT / "etc" / "users.json"
    _ph = PasswordHasher()

    def __init__(self):
        """
        Initialize the UserManager.
        Loads users from the database or creates default users (root, guest).
        """
        self.users = {}
        # Pre-calculate a dummy hash for constant-time authentication failures
        self._dummy_hash = self._hash("dummy_password_for_timing_mitigation")

        # Ensure the directory exists
        self.DB_FILE.parent.mkdir(parents=True, exist_ok=True)

        self._load()

        # Ensure default users exist
        defaults = {
            "root": "root",
            "guest": "guest"
        }
        changed = False
        for u, pw in defaults.items():
            if u not in self.users:
                self.users[u] = {"password": self._hash(pw), "roles": ["admin"] if u == "root" else ["user"]}
                changed = True

        if changed:
            self._save()

    def _hash(self, pw):
        """
        Hash a password using Argon2.

        Args:
            pw (str): The plaintext password.

        Returns:
            str: The password hash.
        """
        return self._ph.hash(pw)

    def _verify(self, hash_val, pw):
        """
        Verify a password against an Argon2 hash.

        Args:
            hash_val (str): The stored hash.
            pw (str): The input password.

        Returns:
            bool: True if matches, False otherwise.
        """
        try:
            return self._ph.verify(hash_val, pw)
        except Exception:
            return False


    def _load(self):
        """
        Load users from the JSON database file.
        Handles migration from older formats if necessary.
        """
        if self.DB_FILE.exists():
            try:
                with open(self.DB_FILE, "r") as f:
                    data = json.load(f)
                    # Migration for old format (user: hash) to new format (user: {password: hash, roles: []})
                    self.users = {}
                    for u, v in data.items():
                        if isinstance(v, str):
                            self.users[u] = {"password": v, "roles": ["admin"] if u == "root" else ["user"]}
                        else:
                            self.users[u] = v
            except Exception as e:
                print(f"[UserManager] Error loading users: {e}")
                self.users = {}

    def _save(self):
        """
        Save the current user data to the JSON database file.
        Restricts file permissions to 600 (read/write by owner only).
        """
        try:
            # Ensure directory exists before saving (redundant but safe)
            self.DB_FILE.parent.mkdir(parents=True, exist_ok=True)

            with open(self.DB_FILE, "w") as f:
                json.dump(self.users, f, indent=2)

            # Secure the file: Read/Write for owner only
            os.chmod(self.DB_FILE, 0o600)
        except Exception as e:
            print(f"[UserManager] Error saving users: {e}")

    def authenticate(self, user, pw):
        """
        Authenticate a user.

        Args:
            user (str): Username.
            pw (str): Password.

        Returns:
            bool: True if valid credentials, False otherwise.
        """
        # Reload to ensure we have latest updates from CLI tools
        self._load()
        if user not in self.users:
            # Perform a dummy verification to mitigate timing attacks (user enumeration)
            self._verify(self._dummy_hash, pw)
            return False
        user_data = self.users[user]
        hash_val = user_data if isinstance(user_data, str) else user_data.get("password")
        if not hash_val:
            # Even if password field is missing (corrupted?), we should probably delay
            self._verify(self._dummy_hash, pw)
            return False
        return self._verify(hash_val, pw)

    def get_roles(self, user):
        """
        Get the roles assigned to a user.

        Args:
            user (str): Username.

        Returns:
            list[str]: List of role names.
        """
        self._load()
        if user in self.users:
            return self.users[user].get("roles", [])
        return []

    def add_role(self, user, role):
        """
        Add a role to a user.

        Args:
            user (str): Username.
            role (str): Role to add.

        Returns:
            bool: True if role added, False if user not found.
        """
        self._load()
        if user in self.users:
            if role not in self.users[user]["roles"]:
                self.users[user]["roles"].append(role)
                self._save()
                return True
        return False

    def remove_role(self, user, role):
        """
        Remove a role from a user.

        Args:
            user (str): Username.
            role (str): Role to remove.

        Returns:
            bool: True if role removed, False if user not found.
        """
        self._load()
        if user in self.users:
            if role in self.users[user]["roles"]:
                self.users[user]["roles"].remove(role)
                self._save()
                return True
        return False

    def has_permission(self, user, action):
        """
        Check if user has permission for action.

        Args:
            user (str): Username.
            action (str): The action to perform.

        Returns:
            bool: True if permitted, False otherwise.
        """
        # Default behavior: root has all permissions
        if user == "root":
            return True

        roles = self.get_roles(user)
        if "admin" in roles:
            return True

        # Default restrictions
        if action == "manage_network":
            return False

        if action == "use_network":
             # "regular user have specific permission to use network"
             # Implies we should allow if they have the role.
             # Current roles are "admin" or "user".
             return "user" in roles

        if action == "execute_code":
            # Allow users to execute code (sandbox protected)
            return "user" in roles

        # This will be extended by TeamCollaboration plugin via monkeypatching or similar
        return False

    def list_users(self):
        """
        List all registered users.

        Returns:
            list[str]: A list of usernames.
        """
        self._load()
        return list(self.users.keys())

    def add_user(self, user, pw, requestor="root"):
        """
        Add a new user.

        Args:
            user (str): New username.
            pw (str): Password.
            requestor (str, optional): User requesting the action. Defaults to "root".

        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.has_permission(requestor, "create_user"):
            return False

        self._load()
        if user in self.users:
            return False
        self.users[user] = {"password": self._hash(pw), "roles": ["user"]}
        self._save()
        return True

    def delete_user(self, user, requestor="root"):
        """
        Delete a user.

        Args:
            user (str): Username to delete.
            requestor (str, optional): User requesting the action.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.has_permission(requestor, "delete_user"):
            return False

        self._load()
        if user in self.users and user != "root": # Protect root
            del self.users[user]
            self._save()
            return True
        return False
