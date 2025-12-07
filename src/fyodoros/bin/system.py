# bin/system.py
"""
System Information Application.

Provides system statistics (hardware, kernel info) in JSON format.
"""

import json

def main(args, sys):
    """
    System App entry point.

    Args:
        args (list): Unused.
        sys (SyscallHandler): System interface to retrieve state.

    Returns:
        str: JSON string containing system info.
    """
    state = sys.sys_get_state()

    # Mock hardware info
    hardware = {
        "cpu": "FyodorOS Virtual CPU",
        "memory": "16GB Mock RAM",
        "disk": "Virtual Filesystem"
    }

    # Kernel info
    kernel_info = {
        "version": "0.1.0",
        "processes_running": len(state["processes"]),
        "users_logged_in": 1 # Mock
    }

    return json.dumps({
        "hardware": hardware,
        "kernel": kernel_info,
        "os": "FyodorOS"
    }, indent=2)
