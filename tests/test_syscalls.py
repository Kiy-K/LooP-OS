import pytest
from unittest.mock import Mock, patch
from fyodoros.kernel.syscalls import SyscallHandler
from fyodoros.kernel.users import UserManager

@pytest.fixture
def syscall_handler():
    # Mock dependencies
    # SyscallHandler.__init__ takes (scheduler, user_manager, network_manager)
    # The error showed "takes from 1 to 4 positional arguments but 5 were given"
    # because I passed 4 args + self = 5.
    # The signature is `__init__(self, scheduler=None, user_manager=None, network_manager=None)`
    # My previous call: `SyscallHandler(mock_fs, mock_proc, mock_net, mock_user_manager)` was definitely wrong
    # because `mock_fs` is not an argument!

    mock_scheduler = Mock()
    mock_user_manager = Mock(spec=UserManager)
    mock_net = Mock()

    # Configure default mock behaviors
    mock_user_manager.authenticate.return_value = True
    mock_user_manager.has_permission.return_value = True

    handler = SyscallHandler(scheduler=mock_scheduler, user_manager=mock_user_manager, network_manager=mock_net)

    # Mock the internal filesystem if needed, but SyscallHandler creates its own FileSystem()
    # We should mock `fyodoros.kernel.syscalls.FileSystem` if we want to mock FS calls.
    # Or replace handler.fs with a mock after init.
    handler.fs = Mock()

    return handler

def test_sys_ls(syscall_handler):
    syscall_handler.fs.list_dir.return_value = ["file1", "file2"]
    syscall_handler.fs.get_node_type.return_value = "dir"

    result = syscall_handler.sys_ls("/home")
    assert result == ["file1", "file2"]

    # Test reading non-existent
    syscall_handler.fs.get_node_type.return_value = None
    with pytest.raises(FileNotFoundError):
        syscall_handler.sys_ls("/nonexistent")

def test_sys_write_read(syscall_handler):
    # Ensure _get_current_uid returns a string "root" instead of a Mock object
    # In SyscallHandler._get_current_uid:
    # if self.scheduler and self.scheduler.current_process:
    #    return self.scheduler.current_process.uid

    # The fixture sets syscall_handler.scheduler = Mock()
    # So self.scheduler.current_process is a Mock()
    # So self.scheduler.current_process.uid is a Mock()

    # Fix: Set the uid explicitly
    syscall_handler.scheduler.current_process.uid = "root"

    # sys_write
    syscall_handler.sys_write("/test.txt", "data")
    # Updated expectation: FS now expects groups arg
    syscall_handler.fs.write_file.assert_called_with("/test.txt", "data", "root", ['root', 'admin'])

    # sys_read
    syscall_handler.fs.read_file.return_value = "data"
    assert syscall_handler.sys_read("/test.txt") == "data"
    # Updated expectation: FS now expects groups arg
    syscall_handler.fs.read_file.assert_called_with("/test.txt", "root", ['root', 'admin'])

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
