
import pytest
import unittest.mock
import sys
from unittest.mock import MagicMock, patch

# Pre-patch libraries
sys.modules["pyautogui"] = MagicMock()
sys.modules["pynput"] = MagicMock()
sys.modules["pynput.keyboard"] = MagicMock()

from loop.kernel.syscall import SyscallHandler
from loop.kernel.senses.ui_driver import UIDriver

class TestSyscallScanCache:
    def setup_method(self):
        self.handler = SyscallHandler()
        self.handler.ui_driver = MagicMock()

    def test_sys_ui_scan_caches_result(self):
        # Mock the driver return value
        mock_scan = {"window": "TestWindow", "children": []}
        self.handler.ui_driver.scan_active_window.return_value = mock_scan

        # Verify initial state
        assert self.handler.last_ui_scan is None

        # Perform scan
        result = self.handler.sys_ui_scan()

        # Verify result and cache
        assert result == mock_scan
        assert self.handler.last_ui_scan == mock_scan

if __name__ == "__main__":
    pytest.main()
