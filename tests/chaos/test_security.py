import pytest
import os
from loop.kernel.process import Process

def dummy_process():
    while True:
        yield

class TestSecurity:
    """
    Security Testing Category.
    """

    def test_sandbox_escape(self, kernel, mock_fs_root):
        """
        Test: Path Traversal
        """
        target = "../../../../etc/passwd"

        try:
            content = kernel.sys.sys_read(target)
            if "root:x:0:0" in content:
                pytest.fail("Host /etc/passwd was read! Sandbox escape successful.")
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def test_privilege_escalation(self, kernel):
        """
        Test: Privilege Escalation
        """
        # Create non-root user
        kernel.user_manager.add_user("lowpriv", "pass")

        # Mock current process as lowpriv
        p = Process(name="hacker", target=dummy_process(), uid="lowpriv")
        kernel.scheduler.current_process = p

        # Try to add user (requires root or specific permission)
        # add_user(..., requestor=uid)
        result = kernel.user_manager.add_user("hacked_user", "pass", requestor="lowpriv")
        assert result is False

        # Try to change net status (requires permission)
        # sys_net_set_status uses _get_current_uid() which uses kernel.scheduler.current_process.uid
        result = kernel.sys.sys_net_set_status(False)
        assert result is False

        # Reset
        kernel.scheduler.current_process = None

    def test_nasm_injection(self, kernel):
        """
        Test: NASM Injection
        """
        malicious_code = """
        section .data
        msg db 'Hacked', 0
        """
        # As restricted user
        p = Process(name="script_kiddie", target=dummy_process(), uid="guest")
        kernel.scheduler.current_process = p

        kernel.user_manager.add_user("guest", "pass")
        # Revoke all roles
        kernel.user_manager.users["guest"]["roles"] = []

        res = kernel.sys.sys_exec_nasm(malicious_code)
        assert res.get("error") == "Permission Denied"
