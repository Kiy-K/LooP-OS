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
                self.users[u] = self._hash(pw)
                changed = True

        if changed:
            self._save()

    def _hash(self, pw):
        return hashlib.sha256(pw.encode()).hexdigest()

    def _load(self):
        if os.path.exists(self.DB_FILE):
            try:
                with open(self.DB_FILE, "r") as f:
                    self.users = json.load(f)
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
        return self.users[user] == self._hash(pw)

    def list_users(self):
        self._load()
        return list(self.users.keys())

    def add_user(self, user, pw):
        self._load()
        if user in self.users:
            return False
        self.users[user] = self._hash(pw)
        self._save()
        return True

    def delete_user(self, user):
        self._load()
        if user in self.users and user != "root": # Protect root
            del self.users[user]
            self._save()
            return True
        return False
