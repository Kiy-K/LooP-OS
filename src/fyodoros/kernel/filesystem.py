# kernel/filesystem.py
"""
In-Memory Filesystem.

This module implements a simple in-memory filesystem with support for files,
directories, and basic permissions. It emulates a standard Unix-like hierarchy.
"""

import time


class Permissions:
    """
    Represents file or directory permissions.

    Attributes:
        owner (str): The user who owns the node.
        group (str): The group who owns the node.
        mode (str): Owner permission mode (e.g., 'rw', 'r').
        group_mode (str): Group permission mode.
        world_mode (str): World permission mode.
    """
    def __init__(self, owner="root", mode="rw", group="root", group_mode="r", world_mode="r"):
        """
        Initialize Permissions.

        Args:
            owner (str, optional): The owner's username. Defaults to "root".
            mode (str, optional): Owner permission string. Defaults to "rw".
            group (str, optional): The owner's group. Defaults to "root".
            group_mode (str, optional): Group permission string. Defaults to "r".
            world_mode (str, optional): World permission string. Defaults to "r".
        """
        self.owner = owner
        self.group = group
        self.mode = mode  # Owner mode
        self.group_mode = group_mode
        self.world_mode = world_mode


class FileNode:
    """
    Represents a file in the filesystem.

    Attributes:
        name (str): The name of the file.
        data (str): The content of the file.
        permissions (Permissions): Access permissions.
    """
    def __init__(self, name, data="", owner="root", mode="rw", group="root", group_mode="r", world_mode="r"):
        """
        Initialize a FileNode.

        Args:
            name (str): File name.
            data (str, optional): Initial content. Defaults to "".
            owner (str, optional): Owner username. Defaults to "root".
            mode (str, optional): Owner permission mode. Defaults to "rw".
            group (str, optional): Group name. Defaults to "root".
            group_mode (str, optional): Group permission mode. Defaults to "r".
            world_mode (str, optional): World permission mode. Defaults to "r".
        """
        self.name = name
        self.data = data
        self.permissions = Permissions(owner, mode, group, group_mode, world_mode)

    def __repr__(self):
        return f"<File {self.name} perm={self.permissions.mode}>"


class DirectoryNode:
    """
    Represents a directory in the filesystem.

    Attributes:
        name (str): The name of the directory.
        children (dict): A dictionary mapping names to child nodes (Files or Directories).
        permissions (Permissions): Access permissions.
    """
    def __init__(self, name, owner="root", mode="rw", group="root", group_mode="r", world_mode="r"):
        """
        Initialize a DirectoryNode.

        Args:
            name (str): Directory name.
            owner (str, optional): Owner username. Defaults to "root".
            mode (str, optional): Owner permission mode. Defaults to "rw".
            group (str, optional): Group name. Defaults to "root".
            group_mode (str, optional): Group permission mode. Defaults to "r".
            world_mode (str, optional): World permission mode. Defaults to "r".
        """
        self.name = name
        self.children = {}
        self.permissions = Permissions(owner, mode, group, group_mode, world_mode)

    def __repr__(self):
        return f"<Dir {self.name}>"


class FileSystem:
    """
    In-memory filesystem implementation.

    Manages a tree of DirectoryNode and FileNode objects, starting from a root.
    Provides methods for common filesystem operations like reading, writing,
    listing, and creating directories, with basic permission checks.

    Attributes:
        root (DirectoryNode): The root directory of the filesystem.
    """

    def __init__(self):
        """
        Initialize the FileSystem with a default directory structure.
        Creates /usr, /etc, /bin, /var, /home, etc.
        """
        self.root = DirectoryNode("/")

        # boot FS structure
        self.mkdir("/usr", "root")
        self.mkdir("/etc", "root")
        self.mkdir("/bin", "root")
        self.mkdir("/var", "root")
        self.mkdir("/var/log", "root")
        self.mkdir("/var/log/journal", "root")
        self.mkdir("/home")
        self.mkdir("/home/guest", uid="root", owner="guest", group="guest")
        self.mkdir("/home/root", uid="root", owner="root", group="root")

    def _check_perm(self, node, uid, op, groups=None):
        """
        Check if a user has permission to perform an operation on a node.

        Args:
            node (FileNode or DirectoryNode): The target node.
            uid (str): The user ID attempting the operation.
            op (str): The operation ('r' for read, 'w' for write).
            groups (list[str], optional): The groups the user belongs to.

        Returns:
            bool: True if permitted, False otherwise.
        """
        if uid == "root":
            return True

        groups = groups or []
        perm_str = ""

        # 1. Owner check
        if node.permissions.owner == uid:
            perm_str = node.permissions.mode
        # 2. Group check
        elif node.permissions.group in groups:
            perm_str = node.permissions.group_mode
        # 3. World check
        else:
            perm_str = node.permissions.world_mode

        # Check operation in resolved permission string
        if op in perm_str:
            return True
        # Also handle 'rw' containing 'r' and 'w'
        if 'rw' in perm_str:
            return True

        return False

    def get_node_type(self, path):
        """
        Get the type of the node ('file', 'dir', or None if not found).
        Used for efficient checks without raising exceptions.

        Args:
            path (str): The path to check.

        Returns:
            str | None: 'file' or 'dir', or None if not found.
        """
        try:
            node = self._resolve(path)
            if isinstance(node, DirectoryNode):
                return 'dir'
            elif isinstance(node, FileNode):
                return 'file'
        except KeyError:
            pass
        return None

    def list_dir(self, path="/", uid="root", groups=None):
        """
        List the contents of a directory.

        Args:
            path (str): The directory path. Defaults to "/".
            uid (str): The requesting user ID.
            groups (list[str], optional): The user's groups.

        Returns:
            list[str]: A list of filenames in the directory.

        Raises:
            PermissionError: If access is denied.
            ValueError: If the path is not a directory.
        """
        node = self._resolve(path)
        if isinstance(node, DirectoryNode):
            if self._check_perm(node, uid, 'r', groups):
                return list(node.children.keys())
            raise PermissionError(f"Permission denied: {path}")
        raise ValueError("Not a directory")

    def read_file(self, path, uid="root", groups=None):
        """
        Read the contents of a file.

        Args:
            path (str): The file path.
            uid (str): The requesting user ID.
            groups (list[str], optional): The user's groups.

        Returns:
            str: The file content.

        Raises:
            PermissionError: If access is denied.
            ValueError: If the path is not a file.
        """
        node = self._resolve(path)
        if isinstance(node, FileNode):
            if self._check_perm(node, uid, 'r', groups):
                return node.data
            raise PermissionError(f"Permission denied: {path}")
        raise ValueError("Not a file")

    def write_file(self, path, data, uid="root", groups=None):
        """
        Write data to a file. Overwrites existing content or creates a new file.

        Args:
            path (str): The file path.
            data (str): The content to write.
            uid (str): The requesting user ID.
            groups (list[str], optional): The user's groups.

        Raises:
            PermissionError: If write access is denied.
            ValueError: If the path is a directory.
        """
        # Check if file exists to check permissions, or parent to check create permissions
        try:
            node = self._resolve(path)
            # File exists, check write perm
            if isinstance(node, FileNode):
                if self._check_perm(node, uid, 'w', groups):
                    node.data = data
                    return
                raise PermissionError(f"Permission denied: {path}")
            else:
                 raise ValueError("Path is a directory")
        except KeyError:
            # File doesn't exist, check parent write perm to create
            parent, name = self._split(path)
            if self._check_perm(parent, uid, 'w', groups):
                group = groups[0] if groups else "root"
                parent.children[name] = FileNode(name, data, owner=uid, group=group)
            else:
                raise PermissionError(f"Permission denied: {path}")

    def append_file(self, path, text, uid="root", groups=None):
        """
        Append text to a file. Creates the file if it doesn't exist.

        Args:
            path (str): The file path.
            text (str): The text to append (a newline is added automatically).
            uid (str): The requesting user ID.
            groups (list[str], optional): The user's groups.

        Raises:
            PermissionError: If write access is denied.
        """
        try:
            node = self._resolve(path)
            if isinstance(node, FileNode):
                if self._check_perm(node, uid, 'w', groups):
                    node.data += text + "\n"
                    return
                raise PermissionError(f"Permission denied: {path}")
        except KeyError:
            # Create new
            parent, name = self._split(path)
            if self._check_perm(parent, uid, 'w', groups):
                group = groups[0] if groups else "root"
                parent.children[name] = FileNode(name, text + "\n", owner=uid, group=group)
            else:
                raise PermissionError(f"Permission denied: {path}")

    def mkdir(self, path, uid="root", owner=None, group=None, groups=None):
        """
        Create a directory.

        Args:
            path (str): The directory path to create.
            uid (str): The requesting user ID (must have write perm on parent).
            owner (str, optional): The owner of the new directory. Defaults to uid.
            group (str, optional): The group of the new directory.
            groups (list[str], optional): The requesting user's groups.

        Raises:
            PermissionError: If creation is not allowed.
            FileExistsError: If path already exists.
        """
        try:
            self._resolve(path)
            # Already exists
            raise FileExistsError(f"Directory already exists: {path}")
        except KeyError:
            pass

        parent, name = self._split(path)
        if self._check_perm(parent, uid, 'w', groups):
            new_owner = owner if owner else uid
            new_group = group if group else (groups[0] if groups else "root")
            parent.children[name] = DirectoryNode(name, owner=new_owner, group=new_group)
        else:
            raise PermissionError(f"Permission denied: {path}")

    def delete_file(self, path, uid="root", groups=None):
        """
        Deletes a file or directory.

        Args:
            path (str): The path to delete.
            uid (str): The requesting user ID.
            groups (list[str], optional): The user's groups.

        Raises:
            FileNotFoundError: If the path does not exist.
            PermissionError: If deletion is not allowed.
            OSError: If attempting to delete a non-empty directory.
        """
        try:
            parent, name = self._split(path)
        except KeyError:
            raise FileNotFoundError(f"Path not found: {path}")

        if name not in parent.children:
             raise FileNotFoundError(f"File not found: {path}")

        # Check permission on PARENT to delete child
        if self._check_perm(parent, uid, 'w', groups):
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
        """
        Resolve a path string to a node in the filesystem tree.

        Args:
            path (str): The path to resolve.

        Returns:
            FileNode or DirectoryNode: The resolved node.

        Raises:
            KeyError: If the path does not exist.
        """
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
        """
        Split a path into its parent node and the leaf name.

        Args:
            path (str): The path to split.

        Returns:
            tuple: (DirectoryNode parent, str name).

        Raises:
            KeyError: If the parent path does not exist.
        """
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
