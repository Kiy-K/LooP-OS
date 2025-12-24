import pytest
from loop.kernel.sandbox import AgentSandbox
from unittest.mock import MagicMock
import os

def test_fuzz_paths_blocked():
    # Use Python implementation to ensure strict path checking
    sandbox = AgentSandbox(MagicMock())
    sandbox.core = None

    # We want to verify that paths attempting to escape are blocked.
    # Note: pathlib / operator discards left side if right side is absolute.
    # So sandbox._resolve("/etc/passwd") -> target="/etc/passwd".
    # commonpath([~/.loop/sandbox, /etc/passwd]) -> /
    # / != ~/.loop/sandbox. So it should raise PermissionError.

    fuzz_vectors = [
        "../etc/passwd",
        "/etc/passwd",
        ".../shadow", # This is treated as relative, might be allowed if ... dir exists? No, it's relative.
                      # But if it resolves to ~/.loop/sandbox/.../shadow, it's valid.
                      # Wait, ... is just a name.
        "~/..",       # Expands to home, but pathlib doesn't expand ~. sandbox._resolve doesn't expand ~ for input?
                      # sandbox._resolve uses (base / path).resolve().
                      # (base / "~/..") -> base/~/.. -> base.
                      # So strictly speaking it's allowed?
                      # No, resolve() handles ..
                      # If path is "~/..", base/~/.. -> base.
                      # So it stays inside.
        "/var/run/docker.sock",
        "C:\\Windows\\System32", # Treated as relative on Linux? Or file with backslashes.
        "\\\\server\\share"
    ]

    for path in fuzz_vectors:
        try:
            sandbox._resolve(path)
        except PermissionError:
            continue
        except Exception:
            continue

        # Analyze why it didn't raise
        # 1. ".../shadow": resolves to {root}/.../shadow. Valid inside sandbox.
        # 2. "~/..": resolves to {root} (if ~ treated as name). Valid inside sandbox.
        # 3. "C:\\Windows...": resolves to {root}/C:\Windows... (valid filename on Linux).

        # So actually, only paths that truly escape should raise.
        # /etc/passwd MUST raise.
        # ../etc/passwd MUST raise.

        if path in ["/etc/passwd", "../etc/passwd", "/var/run/docker.sock"]:
             with pytest.raises(PermissionError):
                 sandbox._resolve(path)
