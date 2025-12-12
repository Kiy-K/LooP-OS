# fyodoros/utils/path.py
"""
Path Resolution Utility.

This module handles safe path resolution for the Virtual RootFS, ensuring
paths targeting the sandbox are correctly mapped to the host filesystem,
while preventing escapes.
"""

import os
from pathlib import Path


class PathResolver:
    """
    Resolves paths relative to the sandbox root.
    """
    def __init__(self, sandbox_root=None):
        """
        Initialize the PathResolver.

        Args:
            sandbox_root (str, optional): Absolute path to the sandbox root.
                                          Defaults to `~/.fyodor/sandbox`.
        """
        if sandbox_root:
            self.root = Path(sandbox_root).resolve()
        else:
            self.root = (Path.home() / ".fyodor" / "sandbox").resolve()

    def resolve(self, path):
        """
        Resolve a path safely within the sandbox.

        Args:
            path (str): The relative path to resolve.

        Returns:
            str: The absolute path on the host system.

        Raises:
            PermissionError: If the path attempts to escape the sandbox.
        """
        # 1. Construct absolute target path
        # Treat input as relative to root, even if it looks absolute
        # (similar to how chroot works)
        if str(path).startswith("/"):
            path = str(path).lstrip("/")

        target = (self.root / path).resolve()

        # 2. Use commonpath to strictly verify containment
        try:
            if os.path.commonpath([self.root, target]) != str(self.root):
                 raise PermissionError(f"Sandbox Violation: Path {path} escapes sandbox root {self.root}")
        except ValueError:
             # Occurs if paths are on different drives on Windows
             raise PermissionError(f"Sandbox Violation: Path {path} on different drive than {self.root}")

        return str(target)

    def is_safe(self, path):
        """
        Check if a path is safe without raising exception.
        """
        try:
            self.resolve(path)
            return True
        except PermissionError:
            return False
