import unittest
from unittest.mock import MagicMock, call
from loop.kernel.senses.motor import Motor, StaleElementException, ElementRegistry

class TestMotor(unittest.TestCase):
    def setUp(self):
        # Reset registry
        ElementRegistry.clear()

    def test_release_modifiers_called_finally(self):
        motor = Motor()
        motor.pyautogui = MagicMock()
        motor._release_modifiers = MagicMock()

        # Mock internal action methods to avoid logic errors during test
        motor._click = MagicMock()

        # Register a mock element
        element = MagicMock()
        uid = ElementRegistry.register(element)

        # Test success case
        motor.execute_action(uid, "click")
        motor._release_modifiers.assert_called_once()

        # Test error case
        motor._release_modifiers.reset_mock()
        motor._click.side_effect = Exception("Click Failed")

        try:
            motor.execute_action(uid, "click")
        except Exception:
            pass

        motor._release_modifiers.assert_called_once()

    def test_release_modifiers_logic(self):
        motor = Motor()
        motor.pyautogui = MagicMock()

        motor._release_modifiers()

        # Check that keyUp was called for modifiers
        # We can't know exact list order, but check at least one
        calls = [call(key) for key in ['ctrl', 'shift', 'alt', 'win', 'command', 'option', 'fn']]
        motor.pyautogui.keyUp.assert_has_calls(calls, any_order=True)

if __name__ == '__main__':
    unittest.main()
