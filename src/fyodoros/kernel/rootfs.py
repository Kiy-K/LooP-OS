# src/fyodoros/kernel/rootfs.py
"""
Virtual Root Filesystem.
"""

import os
from pathlib import Path
from functools import lru_cache

# 1. FYODOR_ROOT constant
# Renamed to .loop as part of Project Phoenix (LooP OS)
FYODOR_ROOT = Path.home() / ".loop"
# Cache the resolved root path to avoid repeated syscalls
_RESOLVED_ROOT = None


class SecurityError(Exception):
    """Raised when a path traversal attempt is detected."""
    pass

def init_structure():
    """
    Creates the required directory structure on the disk.
    """
    directories = [
        FYODOR_ROOT / "bin",
        FYODOR_ROOT / "etc",
        FYODOR_ROOT / "home",
        FYODOR_ROOT / "var" / "logs",
        FYODOR_ROOT / "var" / "memory",
        FYODOR_ROOT / "sandbox",
        FYODOR_ROOT / "plugins",
    ]

    for d in directories:
        d.mkdir(parents=True, exist_ok=True)

def get_resolved_root() -> Path:
    """
    Returns the resolved absolute path of FYODOR_ROOT.
    Uses caching to avoid repeated filesystem calls.
    """
    global _RESOLVED_ROOT
    if _RESOLVED_ROOT is None:
        _RESOLVED_ROOT = FYODOR_ROOT.resolve()
    return _RESOLVED_ROOT


@lru_cache(maxsize=1024)
def resolve(virtual_path: str) -> Path:
    """
    Resolves a virtual path to a safe absolute path within FYODOR_ROOT.

    PERFORMANCE: This function is cached to avoid repeated disk hits (stat/readlink)
    for path resolution.

    SECURITY NOTE:
    Caching 'resolve' implies we assume the symlink topology of the resolved path
    does not change frequently. In a single-agent environment where the agent
    cannot create symlinks (no sys_symlink), this is generally safe.
    However, if an external process modifies symlinks inside ~/.fyodor while
    the agent is running, this cache might return a path that was safe
    but is now unsafe (TOCTOU). Given the threat model (Agent inside sandbox),
    this optimization is acceptable.

    Args:
        virtual_path (str): The virtual path (e.g., "/home/notes.txt").

    Returns:
        Path: The absolute path on the host system.

    Raises:
        SecurityError: If the resolved path is outside FYODOR_ROOT.
    """
    # Normalize input: Ensure it looks like a relative path to join safely
    # If path starts with /, strictly speaking path.join with absolute path ignores previous part.
    # So we must strip leading /
    clean_path = virtual_path.lstrip("/")

    # Resolve absolute path
    target_path = (FYODOR_ROOT / clean_path).resolve()

    # Get cached root path
    root_abs = get_resolved_root()

    # Security Check: Ensure containment
    try:
        # commonpath raises ValueError if paths are on different drives
        # It ensures strict prefix checking
        if os.path.commonpath([root_abs, target_path]) != str(root_abs):
            raise SecurityError(f"Path traversal detected: {virtual_path} -> {target_path}")
    except ValueError:
        raise SecurityError(f"Path traversal detected (drive mismatch): {virtual_path}")

    return target_path
