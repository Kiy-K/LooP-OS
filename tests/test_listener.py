
import pytest
import unittest.mock
import sys
from unittest.mock import MagicMock, patch

# Robust Mock Setup
# Create mocks
mock_pynput = MagicMock()
mock_keyboard = MagicMock()
# Link them so 'from pynput import keyboard' works
mock_pynput.keyboard = mock_keyboard
# Register in sys.modules
sys.modules["pynput"] = mock_pynput
sys.modules["pynput.keyboard"] = mock_keyboard
sys.modules["pyautogui"] = MagicMock()

from loop.kernel.io import APIAdapter
from loop.kernel.senses.listener import BackgroundListener

class TestListener:
    def setup_method(self):
        self.sys_mock = MagicMock()
        self.io_mock = MagicMock()
        self.listener = BackgroundListener(self.sys_mock, self.io_mock)

    def test_start_stop(self):
        # We need to verify that `keyboard.GlobalHotKeys` is called.
        # It is on the mock_keyboard object we created.

        self.listener.start()

        # Check if we hit the ImportError path
        # If GlobalHotKeys is not called, maybe import failed?
        # assert mock_keyboard.GlobalHotKeys.called, "GlobalHotKeys not called. Did import fail?"

        mock_keyboard.GlobalHotKeys.assert_called_once()

        # Verify the listener was started
        listener_instance = mock_keyboard.GlobalHotKeys.return_value
        listener_instance.start.assert_called_once()

        self.listener.stop()
        listener_instance.stop.assert_called_once()

    def test_on_wake(self):
        # Trigger wake logic
        self.listener._on_wake()

        # Verify scan called
        self.sys_mock.sys_ui_scan.assert_called_once()

        # Verify signal sent
        self.io_mock.signal.assert_called_with("WAKE")

    def test_on_wake_scan_error_handling(self):
        # Setup error
        self.sys_mock.sys_ui_scan.side_effect = Exception("Scan Failed")

        # Should not crash
        self.listener._on_wake()

        # Signal should still be sent
        self.io_mock.signal.assert_called_with("WAKE")

class TestIOAdapter:
    def test_signal_queue(self):
        adapter = APIAdapter()
        adapter.signal("TEST_SIG")

        sig = adapter.get_signal()
        assert sig == "TEST_SIG"
        assert adapter.get_signal() is None

if __name__ == "__main__":
    pytest.main()
