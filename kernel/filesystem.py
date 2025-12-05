# kernel/filesystem.py

import time

class Permissions:
    def __init__(self, owner="root", mode="rw"):
        self.owner = owner
        self.mode = mode  # rw, r, rwx (for future)


class FileNode:
    def __init__(self, name, data="", owner="root", mode="rw"):
        self.name = name
        self.data = data
        self.permissions = Permissions(owner, mode)

    def __repr__(self):
        return f"<File {self.name} perm={self.permissions.mode}>"


class DirectoryNode:
    def __init__(self, name, owner="root", mode="rw"):
        self.name = name
        self.children = {}
        self.permissions = Permissions(owner, mode)

    def __repr__(self):
        return f"<Dir {self.name}>"


class FileSystem:
    """
    In-memory filesystem with directories, files, permissions.
    """

    def __init__(self):
        self.root = DirectoryNode("/")

        # boot FS structure
        self.mkdir("/usr")
        self.mkdir("/etc")
        self.mkdir("/bin")
        self.mkdir("/var")
        self.mkdir("/var/log")
        self.mkdir("/var/log/journal")

    def list_dir(self, path="/"):
        node = self._resolve(path)
        if isinstance(node, DirectoryNode):
            return list(node.children.keys())
        raise ValueError("Not a directory")

    def read_file(self, path):
        node = self._resolve(path)
        if isinstance(node, FileNode):
            return node.data
        raise ValueError("Not a file")

    def write_file(self, path, data):
        parent, name = self._split(path)
        parent.children[name] = FileNode(name, data)

    def append_file(self, path, text):
        parent, name = self._split(path)
        if name not in parent.children:
            parent.children[name] = FileNode(name, "")
        parent.children[name].data += text + "\n"

    def mkdir(self, path):
        parent, name = self._split(path)
        parent.children[name] = DirectoryNode(name)

    # ===== Helpers =====
    def _resolve(self, path):
        parts = [p for p in path.split("/") if p]
        node = self.root
        for p in parts:
            node = node.children[p]
        return node

    def _split(self, path):
        parts = [p for p in path.split("/") if p]
        parent_parts = parts[:-1]
        name = parts[-1]

        node = self.root
        for p in parent_parts:
            node = node.children[p]

        return node, name
# --- IGNORE ---