# system_call.py

"""
System call interface exposed to external programs / agents.

This module defines the `SystemCallInterface` class, which acts as a wrapper
around the kernel's `SyscallHandler`. It provides a simplified API for
agents and external programs to interact with the system.
"""

from kernel.syscalls import SyscallHandler

class SystemCallInterface:
    """
    Wrapper for system calls exposed to agents and external programs.

    This class limits the surface area of the kernel exposed to external entities
    and provides convenient methods for common operations.

    Attributes:
        sys (SyscallHandler): The underlying kernel system call handler.
    """

    def __init__(self, syscall: SyscallHandler):
        """
        Initialize the SystemCallInterface.

        Args:
            syscall (SyscallHandler): The kernel syscall handler instance to wrap.
        """
        self.sys = syscall

    # Exposed to agents
    def ls(self, path="/"):
        """
        List directory contents.

        Args:
            path (str): The directory path to list. Defaults to "/".

        Returns:
            list[str]: A list of filenames in the directory.
        """
        return self.sys.sys_ls(path)

    def read(self, path):
        """
        Read the contents of a file.

        Args:
            path (str): The path of the file to read.

        Returns:
            str: The content of the file.
        """
        return self.sys.sys_read(path)

    def write(self, path, data):
        """
        Write data to a file.

        Args:
            path (str): The path of the file to write to.
            data (str): The content to write.

        Returns:
            bool: True if the write was successful, False otherwise.
        """
        return self.sys.sys_write(path, data)

    def log(self, msg):
        """
        Log a message to the system log.

        Args:
            msg (str): The message to log.

        Returns:
            bool: True if logging was successful.
        """
        return self.sys.sys_log(msg)

    def get_state(self):
        """
        Retrieve the current system state.

        Returns:
            dict: A dictionary representing the system state (DOM).
        """
        return self.sys.sys_get_state()

    def shutdown(self):
        """
        Initiate system shutdown.

        Returns:
            bool: True if shutdown sequence started.
        """
        return self.sys.sys_shutdown()

    def reboot(self):
        """
        Initiate system reboot.

        Returns:
            bool: True if reboot sequence started.
        """
        return self.sys.sys_reboot()
