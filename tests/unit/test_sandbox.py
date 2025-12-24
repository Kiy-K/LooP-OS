import pytest
from unittest.mock import MagicMock
from loop.kernel.sandbox import AgentSandbox
import os

@pytest.fixture
def sandbox():
    mock_sys = MagicMock()
    # Force python-only implementation for consistency in unit tests
    # or ensure C++ behavior is expected.
    # Since C++ core acts as a jail (rewrites absolute paths), we test for escaping.
    s = AgentSandbox(mock_sys)
    s.core = None # Force Python implementation to test logic in Python
    return s

def test_path_traversal_blocked(sandbox):
    with pytest.raises(PermissionError):
        sandbox._resolve("../../etc/passwd")

    with pytest.raises(PermissionError):
        sandbox._resolve("folder/../../../../root")

def test_symlink_blocked(sandbox, tmp_path):
    # Test escaping via ..
    with pytest.raises(PermissionError):
        sandbox._resolve("../outside")

    # If using Python implementation, absolute paths outside sandbox should block
    # providing we set root properly.
    sandbox.root_path = str(tmp_path)
    with pytest.raises(PermissionError):
         # /etc/shadow is likely outside tmp_path
         sandbox._resolve("/etc/shadow")

def test_run_process_allowed_app(sandbox):
    # For 'malware', it should return Permission Denied.
    result = sandbox.execute("run_process", ["malware"])
    assert "Permission Denied" in result

    # For 'browser', it should try to run (import error expected in mock env, but not permission denied)
    result = sandbox.execute("run_process", ["browser"])
    assert "Permission Denied" not in result
