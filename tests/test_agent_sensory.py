
import pytest
import unittest.mock
import sys
from unittest.mock import MagicMock, patch

# Pre-patch libraries
sys.modules["pyautogui"] = MagicMock()
sys.modules["pynput"] = MagicMock()
sys.modules["pynput.keyboard"] = MagicMock()

from loop.kernel.agent import ReActAgent
from loop.kernel.sandbox import AgentSandbox
from loop.kernel.syscall import SyscallHandler

class TestAgentSensory:
    def setup_method(self):
        self.sys_mock = MagicMock()
        self.agent = ReActAgent(self.sys_mock)
        # Mock sandbox with real class logic
        self.agent.sandbox = AgentSandbox(self.sys_mock)
        # Mock confirmation to always approve
        self.agent.sandbox.confirmation = MagicMock()
        self.agent.sandbox.confirmation.request_approval.return_value = True

    def test_inject_context(self):
        msg = "User just woke you up."
        self.agent.inject_context(msg)
        assert len(self.agent.history) == 1
        assert msg in self.agent.history[0]

    def test_sandbox_read_screen(self):
        self.sys_mock.sys_ui_scan.return_value = {"window": "Test"}

        res = self.agent.sandbox.execute("read_screen", [])

        self.sys_mock.sys_ui_scan.assert_called_once()
        assert res == {"window": "Test"}

    def test_sandbox_interact(self):
        self.sys_mock.sys_ui_act.return_value = {"success": True}

        # Test interact
        res = self.agent.sandbox.execute("interact", [1, "click"])

        self.sys_mock.sys_ui_act.assert_called_with(1, "click", None)
        assert res == {"success": True}

        # Test interact with payload
        res = self.agent.sandbox.execute("interact", [1, "type", "hello"])
        self.sys_mock.sys_ui_act.assert_called_with(1, "type", "hello")

if __name__ == "__main__":
    pytest.main()
