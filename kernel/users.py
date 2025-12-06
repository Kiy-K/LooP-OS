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

    def add_user(self, user, pw):
        if user in self.users:
            return False
        self.users[user] = self._hash(pw)
        return True

    def delete_user(self, user):
        if user in self.users and user != "root": # Protect root
            del self.users[user]
            return True
        return False
