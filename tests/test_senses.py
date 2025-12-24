
import pytest
import unittest.mock
import threading
import time
import sys
from unittest.mock import MagicMock, patch

# Mock pyautogui BEFORE importing motor so it can be imported
sys.modules["pyautogui"] = MagicMock()

from loop.kernel.senses.ui_driver import UIDriver, ElementRegistry
from loop.kernel.senses.motor import Motor, StaleElementException, SafetyInterruption
from loop.kernel.syscall import SyscallHandler

class TestSenses:
    def setup_method(self):
        ElementRegistry.clear()
        # Ensure Motor has the mock
        self.mock_pyautogui = sys.modules["pyautogui"]

    @patch('platform.system')
    def test_ui_scan_unsupported_os(self, mock_system):
        mock_system.return_value = "UnknownOS"
        driver = UIDriver()
        result = driver.scan_active_window()
        assert "error" in result
        assert "Unsupported OS" in result["error"]

    def test_registry_scan_id(self):
        ElementRegistry.start_scan()
        sid1 = ElementRegistry._current_scan_id
        assert sid1 is not None

        ElementRegistry.start_scan()
        sid2 = ElementRegistry._current_scan_id
        assert sid1 != sid2

    def test_registry(self):
        obj = {"name": "test"}
        uid = ElementRegistry.register(obj)
        assert uid > 0
        assert ElementRegistry.get(uid) == obj
        ElementRegistry.clear()
        assert ElementRegistry.get(uid) is None

    def test_motor_execute_valid(self):
        motor = Motor()
        # Verify motor picked up the mock from sys.modules
        assert motor.pyautogui is not None

        obj = MagicMock()
        # Mock BoundingRectangle as an object with .center()
        obj.BoundingRectangle.center.return_value = (100, 200)

        uid = ElementRegistry.register(obj)

        # Test Click
        assert motor.execute_action(uid, "click") is True
        motor.pyautogui.click.assert_called_with(100, 200)

        # Test Type
        assert motor.execute_action(uid, "type", "hello") is True
        motor.pyautogui.write.assert_called_with("hello")

    def test_motor_get_center_tuple(self):
        motor = Motor()

        obj = MagicMock()
        # Mock BoundingRectangle as a tuple (left, top, right, bottom)
        obj.BoundingRectangle = (0, 0, 100, 100)

        uid = ElementRegistry.register(obj)
        assert motor.execute_action(uid, "click") is True
        motor.pyautogui.click.assert_called_with(50, 50)

    def test_motor_execute_stale(self):
        motor = Motor()

        with pytest.raises(StaleElementException):
            motor.execute_action(999, "click")

    def test_kill_switch_interruption(self):
        motor = Motor()
        motor._emergency_stop = True

        with pytest.raises(SafetyInterruption):
            motor.execute_action(1, "click")

    def test_syscall_integration(self):
        handler = SyscallHandler()
        # Mock the internal driver and motor
        handler.ui_driver = MagicMock()
        handler.motor = MagicMock()

        handler.ui_driver.scan_active_window.return_value = {"window": "Test"}
        assert handler.sys_ui_scan() == {"window": "Test"}

        handler.motor.execute_action.return_value = True
        assert handler.sys_ui_act(1, "click") == {"success": True}

        handler.motor.execute_action.side_effect = StaleElementException("Stale")
        result = handler.sys_ui_act(1, "click")
        assert result["success"] is False
        assert "Stale" in result["error"]

if __name__ == "__main__":
    pytest.main()
