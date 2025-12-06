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
        self.mkdir("/usr", "root")
        self.mkdir("/etc", "root")
        self.mkdir("/bin", "root")
        self.mkdir("/var", "root")
        self.mkdir("/var/log", "root")
        self.mkdir("/var/log/journal", "root")
        self.mkdir("/home")
        self.mkdir("/home/guest", uid="root", owner="guest")
        self.mkdir("/home/root", uid="root", owner="root")

    def _check_perm(self, node, uid, op):
        """
        Check if uid has permission to perform op ('r' or 'w') on node.
        """
        if uid == "root":
            return True

        # Simple ownership check for now
        if node.permissions.owner == uid:
            if op in node.permissions.mode:
                return True
            # Also handle 'rw' containing 'r' and 'w'
            if 'rw' in node.permissions.mode:
                return True

        # TODO: Group/World permissions
        return False

    def list_dir(self, path="/", uid="root"):
        node = self._resolve(path)
        if isinstance(node, DirectoryNode):
            if self._check_perm(node, uid, 'r'):
                return list(node.children.keys())
            raise PermissionError(f"Permission denied: {path}")
        raise ValueError("Not a directory")

    def read_file(self, path, uid="root"):
        node = self._resolve(path)
        if isinstance(node, FileNode):
            if self._check_perm(node, uid, 'r'):
                return node.data
            raise PermissionError(f"Permission denied: {path}")
        raise ValueError("Not a file")

    def write_file(self, path, data, uid="root"):
        # Check if file exists to check permissions, or parent to check create permissions
        try:
            node = self._resolve(path)
            # File exists, check write perm
            if isinstance(node, FileNode):
                if self._check_perm(node, uid, 'w'):
                    node.data = data
                    return
                raise PermissionError(f"Permission denied: {path}")
            else:
                 raise ValueError("Path is a directory")
        except KeyError:
            # File doesn't exist, check parent write perm to create
            parent, name = self._split(path)
            if self._check_perm(parent, uid, 'w'):
                parent.children[name] = FileNode(name, data, owner=uid)
            else:
                raise PermissionError(f"Permission denied: {path}")

    def append_file(self, path, text, uid="root"):
        try:
            node = self._resolve(path)
            if isinstance(node, FileNode):
                if self._check_perm(node, uid, 'w'):
                    node.data += text + "\n"
                    return
                raise PermissionError(f"Permission denied: {path}")
        except KeyError:
            # Create new
            parent, name = self._split(path)
            if self._check_perm(parent, uid, 'w'):
                parent.children[name] = FileNode(name, text + "\n", owner=uid)
            else:
                raise PermissionError(f"Permission denied: {path}")

    def mkdir(self, path, uid="root", owner=None):
        try:
            self._resolve(path)
            # Already exists
            return
        except KeyError:
            pass

        parent, name = self._split(path)
        if self._check_perm(parent, uid, 'w'):
            new_owner = owner if owner else uid
            parent.children[name] = DirectoryNode(name, owner=new_owner)
        else:
            raise PermissionError(f"Permission denied: {path}")

    def delete_file(self, path, uid="root"):
        """
        Deletes a file or directory.
        """
        try:
            parent, name = self._split(path)
        except KeyError:
            raise FileNotFoundError(f"Path not found: {path}")

        if name not in parent.children:
             raise FileNotFoundError(f"File not found: {path}")

        # Check permission on PARENT to delete child
        if self._check_perm(parent, uid, 'w'):
             # If directory, ensure empty?
             # For simple implementation, recursive delete or strict empty check.
             # Strict empty check for safety.
             target = parent.children[name]
             if isinstance(target, DirectoryNode) and target.children:
                 raise OSError("Directory not empty")

             del parent.children[name]
        else:
            raise PermissionError(f"Permission denied: {path}")

    # ===== Helpers =====
    def _resolve(self, path):
        if path == "/": return self.root
        parts = [p for p in path.split("/") if p]
        node = self.root
        for p in parts:
            if isinstance(node, DirectoryNode) and p in node.children:
                node = node.children[p]
            else:
                raise KeyError(f"Path not found: {path}")
        return node

    def _split(self, path):
        parts = [p for p in path.split("/") if p]
        if not parts:
            return self.root, "" # Should not happen for valid paths with name
        parent_parts = parts[:-1]
        name = parts[-1]

        node = self.root
        for p in parent_parts:
             if isinstance(node, DirectoryNode) and p in node.children:
                node = node.children[p]
             else:
                raise KeyError(f"Parent path not found: {path}")

        return node, name
