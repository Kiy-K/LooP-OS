# supervisor/journal_daemon.py

import time

def journal_daemon(syscall):
    """Background journaling service."""
    while True:
        syscall.sys_append("/var/log/journal/journal.status", f"beat {time.time()}")
        time.sleep(3)
        yield
# --- IGNORE ---