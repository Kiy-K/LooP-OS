import pytest
import os
from unittest.mock import Mock, patch, mock_open
from loop.kernel.syscall import SyscallHandler
from loop.kernel.users import UserManager


@pytest.fixture
def syscall_handler():
    # Mock dependencies
    mock_scheduler = Mock()
    mock_user_manager = Mock(spec=UserManager)
    mock_net = Mock()

    # Configure default mock behaviors
    mock_user_manager.authenticate.return_value = True
    mock_user_manager.has_permission.return_value = True

    # Ensure default UID is set to avoid Mock object return in _get_current_uid
    mock_scheduler.current_process.uid = "root"

    handler = SyscallHandler(
        scheduler=mock_scheduler,
        user_manager=mock_user_manager,
        network_manager=mock_net,
    )

    return handler


def test_sys_ls(syscall_handler):
    # Mock rootfs resolution and os.listdir
    with patch("loop.kernel.rootfs.resolve") as mock_resolve, \
         patch("os.listdir") as mock_listdir:

        mock_path = Mock()
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = True
        mock_resolve.return_value = mock_path

        mock_listdir.return_value = ["file1", "file2"]

        result = syscall_handler.sys_ls("/home")
        assert result == ["file1", "file2"]

        # Test reading non-existent
        mock_path.exists.return_value = False
        # To simulate raising FileNotFoundError inside sys_ls logic
        # sys_ls calls real_path.exists(), if false it raises FileNotFoundError

        with pytest.raises(FileNotFoundError):
            syscall_handler.sys_ls("/nonexistent")

        # Test listing a file (not a directory)
        mock_path.exists.return_value = True
        mock_path.is_dir.return_value = False
        mock_path.name = "somefile"

        result = syscall_handler.sys_ls("/somefile")
        assert result == ["somefile"]


def test_sys_write_read(syscall_handler):
    # Mock rootfs resolution and open
    with patch("loop.kernel.rootfs.resolve") as mock_resolve, \
         patch("builtins.open", mock_open(read_data="data")) as mock_file:

        mock_path = Mock()
        mock_path.parent.mkdir = Mock()
        mock_resolve.return_value = mock_path

        # sys_write
        syscall_handler.sys_write("/test.txt", "data")

        # Verify open was called with 'w'
        mock_file.assert_any_call(mock_path, "w")
        mock_file().write.assert_any_call("data")

        # sys_read
        assert syscall_handler.sys_read("/test.txt") == "data"

        # Verify open was called with 'r'
        mock_file.assert_any_call(mock_path, "r")


def test_sys_docker_calls(syscall_handler):
    # Setup docker interface mock
    syscall_handler.docker_interface = Mock()
    syscall_handler.docker_interface.run_container.return_value = {"id": "123"}

    # Root should be allowed
    res = syscall_handler.sys_docker_run("alpine")
    assert res == {"id": "123"}

    # Mock user check for non-root
    with patch.object(SyscallHandler, "_get_current_uid", return_value="user"):
        # Deny permission
        syscall_handler.user_manager.has_permission.return_value = False
        res = syscall_handler.sys_docker_run("alpine")
        assert res["success"] is False
        assert "Permission Denied" in res["error"]


def test_sys_reboot(syscall_handler):
    syscall_handler.scheduler.exit_reason = None
    res = syscall_handler.sys_reboot()
    assert res == "REBOOT"
    assert syscall_handler.scheduler.exit_reason == "REBOOT"
