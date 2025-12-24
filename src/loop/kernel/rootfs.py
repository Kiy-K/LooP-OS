# src/loop/kernel/rootfs.py
"""
Virtual Root Filesystem.
"""

import os
import shutil
import platformdirs
from pathlib import Path
from functools import lru_cache

# 1. LOOP_ROOT constant
# Using platformdirs for future-proofing, but sticking to ~/.loop for v0.1.0 simplicity
# as requested.
# Ideally this would be: LOOP_ROOT = Path(platformdirs.user_data_dir("loop", "loop-os"))
LOOP_ROOT = Path.home() / ".loop"
LEGACY_ROOT = Path.home() / ".fyodor"

# Cache the resolved root path to avoid repeated syscalls
_RESOLVED_ROOT = None


class SecurityError(Exception):
    """Raised when a path traversal attempt is detected."""
    pass

def check_migration():
    """
    Checks for legacy ~/.fyodor directory and renames it to ~/.loop if needed.
    """
    if LEGACY_ROOT.exists() and not LOOP_ROOT.exists():
        print(f"Migrating legacy data: {LEGACY_ROOT} -> {LOOP_ROOT}")
        try:
            shutil.move(str(LEGACY_ROOT), str(LOOP_ROOT))
        except Exception as e:
            print(f"Error migrating legacy data: {e}")
            # Fallback: Create new root if move fails
            LOOP_ROOT.mkdir(parents=True, exist_ok=True)
    elif LEGACY_ROOT.exists() and LOOP_ROOT.exists():
        print(f"Found both {LEGACY_ROOT} and {LOOP_ROOT}. Keeping {LOOP_ROOT}.")
        # Optional: Rename legacy to .bak?
        # For now, just leaving it alone to avoid data loss.

def init_structure():
    """
    Creates the required directory structure on the disk.
    """
    check_migration()

    directories = [
        LOOP_ROOT / "bin",
        LOOP_ROOT / "etc",
        LOOP_ROOT / "home",
        LOOP_ROOT / "var" / "logs",
        LOOP_ROOT / "var" / "memory",
        LOOP_ROOT / "sandbox",
        LOOP_ROOT / "plugins",
    ]

    for d in directories:
        d.mkdir(parents=True, exist_ok=True)

def get_resolved_root() -> Path:
    """
    Returns the resolved absolute path of LOOP_ROOT.
    Uses caching to avoid repeated filesystem calls.
    """
    global _RESOLVED_ROOT
    if _RESOLVED_ROOT is None:
        # Ensure directory exists before resolving to avoid errors on fresh install
        LOOP_ROOT.mkdir(parents=True, exist_ok=True)
        _RESOLVED_ROOT = LOOP_ROOT.resolve()
    return _RESOLVED_ROOT


@lru_cache(maxsize=1024)
def resolve(virtual_path: str) -> Path:
    """
    Resolves a virtual path to a safe absolute path within LOOP_ROOT.

    PERFORMANCE: This function is cached to avoid repeated disk hits (stat/readlink)
    for path resolution.

    SECURITY NOTE:
    Caching 'resolve' implies we assume the symlink topology of the resolved path
    does not change frequently. In a single-agent environment where the agent
    cannot create symlinks (no sys_symlink), this is generally safe.
    However, if an external process modifies symlinks inside ~/.loop while
    the agent is running, this cache might return a path that was safe
    but is now unsafe (TOCTOU). Given the threat model (Agent inside sandbox),
    this optimization is acceptable.

    Args:
        virtual_path (str): The virtual path (e.g., "/home/notes.txt").

    Returns:
        Path: The absolute path on the host system.

    Raises:
        SecurityError: If the resolved path is outside LOOP_ROOT.
    """
    # Normalize input: Ensure it looks like a relative path to join safely
    # If path starts with /, strictly speaking path.join with absolute path ignores previous part.
    # So we must strip leading /
    clean_path = virtual_path.lstrip("/")

    # Resolve absolute path
    # We use get_resolved_root() as base to ensure we are working with the resolved path
    root_abs = get_resolved_root()
    target_path = (root_abs / clean_path).resolve()

    # Security Check: Ensure containment
    try:
        # commonpath raises ValueError if paths are on different drives
        # It ensures strict prefix checking
        if os.path.commonpath([root_abs, target_path]) != str(root_abs):
            raise SecurityError(f"Path traversal detected: {virtual_path} -> {target_path}")
    except ValueError:
        raise SecurityError(f"Path traversal detected (drive mismatch): {virtual_path}")

    return target_path
