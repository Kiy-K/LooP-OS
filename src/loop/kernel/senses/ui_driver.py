"""
UI Driver for LooP.

This module converts native OS windows into a standardized JSON DOM tree
and maintains a registry of UI elements.
"""

import sys
import platform
import logging
import uuid

# Platform-specific imports will be handled dynamically or mocked
# to ensure the kernel can load on any system, even if the driver is inactive.

logger = logging.getLogger("loop.senses.ui_driver")

class ElementRegistry:
    """
    Registry to map UIDs to native UI elements.
    Ensures safety by using unique IDs per scan or globally unique IDs.
    """
    _instance = None
    _registry = {}
    _current_scan_id = None
    _counter = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ElementRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def start_scan(cls):
        """
        Starts a new scan session.
        Generates a new scan ID and clears old registry references
        (or keeps them but invalidates them if we wanted to be fancy,
         but for now we clear to save memory, assuming the Agent uses the latest scan).

        To prevent race conditions where an Agent acts on an old scan ID,
        we could return the scan_id to the agent.
        However, simply not reusing small integer UIDs is safer and easier.
        """
        cls._registry = {}
        # We don't reset _counter to 0. We keep incrementing.
        # This ensures that ID 1 from Scan A is never ID 1 from Scan B.
        cls._current_scan_id = str(uuid.uuid4())

    @classmethod
    def register(cls, native_element):
        """
        Registers a native element and returns a UID.

        Args:
            native_element: The native UI wrapper object.

        Returns:
            int: The assigned UID.
        """
        cls._counter += 1
        uid = cls._counter
        cls._registry[uid] = native_element
        return uid

    @classmethod
    def get(cls, uid):
        """
        Retrieves a native element by UID.

        Args:
            uid (int): The UID to look up.

        Returns:
            object: The native element, or None if not found.
        """
        return cls._registry.get(uid)

    @classmethod
    def clear(cls):
        """
        Clears the registry.
        """
        cls._registry = {}


class UIDriver:
    """
    Driver to scan active windows and generate a DOM tree.
    """

    def __init__(self):
        self.os_type = platform.system()
        self.registry = ElementRegistry()

    def scan_active_window(self):
        """
        Scans the active window and returns a JSON-compatible DOM tree.

        Returns:
            dict: The DOM tree representing the active window.
        """
        # Start a new scan session.
        # This invalidates all previous UIDs because we clear the registry map.
        self.registry.start_scan()

        try:
            if self.os_type == "Windows":
                return self._scan_windows()
            elif self.os_type == "Darwin":  # macOS
                return self._scan_macos()
            elif self.os_type == "Linux":
                return self._scan_linux()
            else:
                return {"error": f"Unsupported OS: {self.os_type}"}
        except Exception as e:
            logger.error(f"UI Scan failed: {e}")
            return {
                "window": "Unknown",
                "error": "Cannot read accessibility tree",
                "children": []
            }

    def _scan_windows(self):
        """
        Windows implementation using `uiautomation`.
        """
        try:
            import uiautomation as auto
        except ImportError:
            return {"error": "uiautomation not installed"}

        window = auto.GetForegroundWindow()
        if not window:
            return {"window": "Unknown", "children": []}

        tree = {
            "window": window.Name,
            "children": self._walk_windows_tree(window)
        }
        return tree

    def _walk_windows_tree(self, element):
        """
        Recursively walks the Windows UI tree.
        """
        children = []
        import uiautomation as auto

        # We only want actionable elements or containers
        # Using GetChildren() from uiautomation

        for child in element.GetChildren():
            # Filter invisible elements if needed, but for now take all

            node = {
                "role": child.ControlTypeName,
                "text": child.Name,
            }

            # If actionable, register it
            # Simplified logic: Buttons, Edits, ListItems are actionable
            # Or we can just register everything that is visible/enabled
            if child.IsEnabled:
                uid = self.registry.register(child)
                node["uid"] = uid

            # Recursion
            # Limit depth? For now, full tree.
            node["children"] = self._walk_windows_tree(child)
            children.append(node)

        return children

    def _scan_macos(self):
        """
        macOS implementation using `atomacos` or similar.
        """
        # Placeholder for macOS logic
        try:
            import atomacos
        except ImportError:
            return {"error": "atomacos not installed"}

        # Basic implementation sketch
        app = atomacos.get_frontmost_apps()[0]
        window = app.windows()[0] # Assuming single window for active app

        tree = {
            "window": window.AXTitle,
            "children": self._walk_macos_tree(window)
        }
        return tree

    def _walk_macos_tree(self, element):
        children = []
        # atomacos logic...
        # This is a placeholder as I cannot verify macOS env
        return children

    def _scan_linux(self):
        """
        Linux implementation using `pyatspi`.
        """
        try:
            import pyatspi
        except ImportError:
             return {"error": "pyatspi not installed"}

        # pyatspi logic is complex, involves registry.getDesktop(0)
        # Placeholder
        return {"error": "Linux UI scanning not fully implemented yet"}
