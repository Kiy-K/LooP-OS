import pytest
from unittest.mock import MagicMock
from loop.kernel.syscalls import SyscallHandler

@pytest.fixture
def syscall_handler():
    return SyscallHandler()

def test_run_process_basic(syscall_handler):
    syscall_handler.docker_interface = MagicMock()
    syscall_handler.user_manager = MagicMock()
    syscall_handler.user_manager.has_permission.return_value = True

    # Mock current UID to be root or user with permission
    syscall_handler._get_current_uid = MagicMock(return_value="root")

    result = syscall_handler.sys_docker_run("alpine", "test_runner")

    syscall_handler.docker_interface.run_container.assert_called_once()
    assert result is not None

def test_unknown_app_rejected(syscall_handler):
    syscall_handler.user_manager = MagicMock()
    # Mock generic permission denied
    syscall_handler.user_manager.has_permission.return_value = False

    # Force non-root user
    syscall_handler._get_current_uid = MagicMock(return_value="user")

    result = syscall_handler.sys_docker_run("alpine")
    assert result["success"] is False
    assert "Permission Denied" in result["error"]
