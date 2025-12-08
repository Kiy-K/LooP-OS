# supervisor/journal_daemon.py
"""
Journal Daemon.

A simple background service that logs a heartbeat to the system journal.
"""

import time


def journal_daemon(syscall):
    """
    Background journaling service generator.

    Periodically writes a heartbeat timestamp to `/var/log/journal/journal.status`.

    Args:
        syscall (SyscallHandler): System call interface.

    Yields:
        None: Yields control back to the scheduler.
    """
    while True:
        syscall.sys_append("/var/log/journal/journal.status", f"beat {time.time()}")
        time.sleep(3)
        yield
