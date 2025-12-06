# kernel/users.py

import hashlib
import json
import os

class UserManager:
    DB_FILE = "users.json"

    def __init__(self):
        self.users = {}
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
        return hashlib.sha256(pw.encode()).hexdigest()

    def _load(self):
        if os.path.exists(self.DB_FILE):
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
        try:
            with open(self.DB_FILE, "w") as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"[UserManager] Error saving users: {e}")

    def authenticate(self, user, pw):
        # Reload to ensure we have latest updates from CLI tools
        self._load()
        if user not in self.users:
            return False
        user_data = self.users[user]
        if isinstance(user_data, str): # Should be handled by load, but just in case
            return user_data == self._hash(pw)
        return user_data.get("password") == self._hash(pw)

    def get_roles(self, user):
        self._load()
        if user in self.users:
            return self.users[user].get("roles", [])
        return []

    def add_role(self, user, role):
        self._load()
        if user in self.users:
            if role not in self.users[user]["roles"]:
                self.users[user]["roles"].append(role)
                self._save()
                return True
        return False

    def remove_role(self, user, role):
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
        This can be hooked by plugins.
        """
        # Default behavior: root has all permissions
        if user == "root":
            return True

        # This will be extended by TeamCollaboration plugin via monkeypatching or similar
        return True

    def list_users(self):
        self._load()
        return list(self.users.keys())

    def add_user(self, user, pw, requestor="root"):
        """
        Add a new user.
        Args:
            user: New username
            pw: Password
            requestor: User requesting the action (default: root for backward compatibility/CLI)
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
            user: Username to delete
            requestor: User requesting the action
        """
        if not self.has_permission(requestor, "delete_user"):
            return False

        self._load()
        if user in self.users and user != "root": # Protect root
            del self.users[user]
            self._save()
            return True
        return False
