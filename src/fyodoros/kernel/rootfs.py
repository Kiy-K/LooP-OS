# fyodoros/kernel/rootfs.py
"""
Virtual Root Filesystem.

This module implements the unified filesystem view for FyodorOS.
It routes requests between the in-memory kernel filesystem and the
sandboxed host filesystem based on path location.
"""

import os
from fyodoros.kernel.filesystem import FileSystem
from fyodoros.utils.path import PathResolver


class VirtualRootFS:
    """
    Unified Virtual Root Filesystem.

    Routes I/O operations:
    - Paths starting with /sandbox -> Host Filesystem (via PathResolver)
    - All other paths -> In-Memory RAM Disk (FileSystem)
    """

    def __init__(self, sandbox_root=None):
        """
        Initialize the VirtualRootFS.

        Args:
            sandbox_root (str, optional): The root path for the sandbox on the host.
        """
        self.ramdisk = FileSystem()
        self.resolver = PathResolver(sandbox_root)
        self.sandbox_mount_point = "/sandbox"

        # Ensure sandbox mount point exists in RAM disk for listing
        try:
            self.ramdisk.mkdir(self.sandbox_mount_point, owner="root")
        except FileExistsError:
            pass

    def set_sandbox_root(self, root_path):
        """
        Update the sandbox root path (useful for testing).
        """
        self.resolver = PathResolver(root_path)

    def _is_sandbox_path(self, path):
        """
        Determine if the path targets the sandbox.
        """
        # Clean path
        clean_path = os.path.normpath(path)
        if clean_path.startswith(self.sandbox_mount_point):
            # Extract relative path inside sandbox
            # e.g. /sandbox/foo.txt -> foo.txt
            if clean_path == self.sandbox_mount_point:
                return True, ""
            return True, clean_path[len(self.sandbox_mount_point)+1:]
        return False, clean_path

    def _resolve_host_path(self, rel_path):
        """
        Resolve relative sandbox path to absolute host path.
        """
        return self.resolver.resolve(rel_path)

    # --- Filesystem Operations ---

    def list_dir(self, path="/", uid="root", groups=None):
        """
        List directory contents.
        """
        is_sb, rel_path = self._is_sandbox_path(path)

        if is_sb:
            real_path = self._resolve_host_path(rel_path)
            if os.path.isdir(real_path):
                return os.listdir(real_path)
            elif os.path.isfile(real_path):
                 # Behavior match: return filename if it's a file
                 return [os.path.basename(real_path)]
            else:
                 raise FileNotFoundError(f"Path not found: {path}")

        return self.ramdisk.list_dir(path, uid, groups)

    def read_file(self, path, uid="root", groups=None):
        """
        Read file content.
        """
        is_sb, rel_path = self._is_sandbox_path(path)

        if is_sb:
            real_path = self._resolve_host_path(rel_path)
            if os.path.isfile(real_path):
                with open(real_path, "r") as f:
                    return f.read()
            raise FileNotFoundError(f"File not found: {path}")

        return self.ramdisk.read_file(path, uid, groups)

    def write_file(self, path, data, uid="root", groups=None):
        """
        Write file content.
        """
        is_sb, rel_path = self._is_sandbox_path(path)

        if is_sb:
            real_path = self._resolve_host_path(rel_path)
            # Ensure parent exists
            os.makedirs(os.path.dirname(real_path), exist_ok=True)
            with open(real_path, "w") as f:
                f.write(data)
            return

        self.ramdisk.write_file(path, data, uid, groups)

    def append_file(self, path, data, uid="root", groups=None):
        """
        Append to file.
        """
        is_sb, rel_path = self._is_sandbox_path(path)

        if is_sb:
            real_path = self._resolve_host_path(rel_path)
            os.makedirs(os.path.dirname(real_path), exist_ok=True)
            with open(real_path, "a") as f:
                f.write(data + "\n") # Append logic often adds newline in this system?
                # Checked syscalls.py: yes, it adds newline.
            return

        self.ramdisk.append_file(path, data, uid, groups)

    def delete_file(self, path, uid="root", groups=None):
        """
        Delete file or directory.
        """
        is_sb, rel_path = self._is_sandbox_path(path)

        if is_sb:
            real_path = self._resolve_host_path(rel_path)
            if os.path.isdir(real_path):
                os.rmdir(real_path)
            else:
                os.remove(real_path)
            return

        self.ramdisk.delete_file(path, uid, groups)
