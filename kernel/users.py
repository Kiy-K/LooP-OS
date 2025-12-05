# kernel/users.py

import hashlib

class UserManager:
    def __init__(self):
        self.users = {
            "root": self._hash("root"),   # default password: root
            "guest": self._hash("guest")
        }

    def _hash(self, pw):
        return hashlib.sha256(pw.encode()).hexdigest()

    def authenticate(self, user, pw):
        if user not in self.users:
            return False
        return self.users[user] == self._hash(pw)

    def list_users(self):
        return list(self.users.keys())
# --- IGNORE ---