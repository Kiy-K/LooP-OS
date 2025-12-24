"""
Motor Control for LooP.

This module executes actions on UI elements identified by UIDs.
It includes a safety Kill Switch (Mouse Shake).
"""

import threading
import time
import math
import logging
from .ui_driver import ElementRegistry

logger = logging.getLogger("loop.senses.motor")

class StaleElementException(Exception):
    pass

class SafetyInterruption(Exception):
    pass

class Motor:
    """
    Handles physical execution of actions (Click, Type, Scroll).
    """

    def __init__(self):
        try:
            import pyautogui
            self.pyautogui = pyautogui
            # Safety defaults
            self.pyautogui.FAILSAFE = True # Dragging mouse to corner throws exception
        except ImportError:
            self.pyautogui = None
            logger.warning("pyautogui not installed. Motor control disabled.")

        self._kill_switch_active = False
        self._emergency_stop = False
        self._monitor_thread = None

    def start_kill_switch(self):
        """Starts the mouse shake detection thread."""
        if not self.pyautogui:
            return

        self._kill_switch_active = True
        self._emergency_stop = False
        self._monitor_thread = threading.Thread(target=self._monitor_shake, daemon=True)
        self._monitor_thread.start()

    def stop_kill_switch(self):
        """Stops the kill switch thread."""
        self._kill_switch_active = False

    def _monitor_shake(self):
        """
        Monitors mouse movement for rapid shaking.
        If detected, triggers emergency stop.
        """
        last_pos = self.pyautogui.position()
        shake_count = 0

        while self._kill_switch_active:
            time.sleep(0.1)
            try:
                current_pos = self.pyautogui.position()
                dist = math.hypot(current_pos[0] - last_pos[0], current_pos[1] - last_pos[1])

                if dist > 500: # High speed movement
                    shake_count += 1
                else:
                    shake_count = max(0, shake_count - 1)

                if shake_count > 5:
                    logger.critical("KILL SWITCH ACTIVATED via Mouse Shake!")
                    self._emergency_stop = True
                    # Reset to allow recovery later if needed, but for now we are stopped.
                    shake_count = 0

                last_pos = current_pos
            except Exception:
                # pyautogui might fail if display is disconnected etc.
                pass

    def execute_action(self, uid, action_type, payload=None):
        """
        Executes an action on a UI element.

        Args:
            uid (int): The UID of the target element.
            action_type (str): 'click', 'type', 'scroll'.
            payload (str, optional): Text to type or other data.

        Raises:
            StaleElementException: If UID is not valid.
            SafetyInterruption: If Kill Switch is active.
            ValueError: If action is unknown.
        """
        try:
            if self._emergency_stop:
                raise SafetyInterruption("Action blocked by Emergency Kill Switch.")

            if not self.pyautogui:
                return False

            element = ElementRegistry.get(uid)
            if not element:
                raise StaleElementException(f"Element with UID {uid} not found. Re-scan required.")

            if action_type == "click":
                self._click(element)
            elif action_type == "type":
                self._type(element, payload)
            elif action_type == "scroll":
                self._scroll(element, payload)
            else:
                raise ValueError(f"Unknown action: {action_type}")

            return True
        finally:
            self._release_modifiers()

    def _release_modifiers(self):
        """
        Explicitly releases modifier keys to prevent 'stuck key' syndrome.
        """
        modifiers = ['ctrl', 'shift', 'alt', 'win', 'command', 'option', 'fn']
        for key in modifiers:
            try:
                # Some keys might not exist on all platforms, pyautogui handles it or we ignore
                self.pyautogui.keyUp(key)
            except Exception:
                pass

    def _click(self, element):
        # Must resolve element to coordinates
        # This depends on the wrapper object from ui_driver
        x, y = self._get_center(element)
        if x is not None and y is not None:
            self.pyautogui.click(x, y)
        else:
            raise ValueError("Could not determine center coordinates for element.")

    def _type(self, element, text):
        if not text:
            return

        # Click to focus first
        self._click(element)
        time.sleep(0.1)
        self.pyautogui.write(text)

    def _scroll(self, element, direction):
        # Click to focus?
        self._click(element)
        amount = 100 if direction == "up" else -100
        self.pyautogui.scroll(amount)

    def _get_center(self, element):
        """
        Extracts center coordinates from the native element.
        Handles different return types from uiautomation or other libs.
        """
        try:
            # uiautomation
            if hasattr(element, "BoundingRectangle"):
                rect = element.BoundingRectangle
                # rect might be a tuple (left, top, right, bottom) or an object with methods
                if hasattr(rect, "center"):
                    return rect.center()
                elif hasattr(rect, "left") and hasattr(rect, "top") and hasattr(rect, "width") and hasattr(rect, "height"):
                    return (rect.left + rect.width // 2, rect.top + rect.height // 2)
                elif isinstance(rect, (list, tuple)) and len(rect) == 4:
                    # (left, top, right, bottom)
                    return ((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)

            # atomacos / others (Placeholder logic)
            if hasattr(element, "AXFrame"):
                 # Assuming AXFrame is similar
                 pass

        except Exception as e:
            logger.error(f"Failed to get center for element: {e}")

        return None, None
