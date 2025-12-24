"""
Window Manager Module.

Handles focusing and managing application windows.
Abstracts platform-specific libraries (uiautomation, atomacos).
"""

import sys
import platform
import logging

logger = logging.getLogger("loop.kernel.shell.window_manager")

class WindowManager:
    """
    Manages application windows.
    """

    def __init__(self):
        self.os_type = platform.system()

    def focus_window(self, query):
        """
        Focuses a window by title (str) or PID (int).

        Args:
            query (str|int): The window title or process ID.

        Returns:
            dict: Success status or error.
        """
        try:
            if self.os_type == "Windows":
                return self._focus_windows(query)
            elif self.os_type == "Darwin":
                return self._focus_macos(query)
            else:
                return {"success": False, "error": f"Window management not supported on {self.os_type}"}
        except ImportError as e:
            return {"success": False, "error": f"Missing dependency: {e.name}. Please install required libraries."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _focus_windows(self, query):
        """
        Windows implementation using uiautomation.
        """
        import uiautomation as auto

        target = None

        if isinstance(query, int):
            # Focus by PID
            # We iterate top-level windows to find one matching PID
            raw_root = auto.GetRootControl()
            for win in raw_root.GetChildren():
                if win.ProcessId == query:
                    target = win
                    break
        else:
            # Focus by Title (SubString match)
            target = auto.WindowControl(searchDepth=1, Name=query, SubName=True)
            if not target.Exists(0, 0):
                target = None

        if target:
            # Check if minimized and restore if needed.
            # WindowVisualState: 0=Normal, 1=Maximized, 2=Minimized
            try:
                pattern = target.GetWindowPattern()
                if pattern:
                    if pattern.CurrentWindowVisualState == auto.WindowVisualState.Minimized:
                        pattern.SetWindowVisualState(auto.WindowVisualState.Normal)
            except Exception:
                # Fallback if pattern fails (some windows don't support WindowPattern)
                # Just call ShowWindow(Restore) which is generally safe
                try:
                    target.ShowWindow(auto.SW.Restore)
                except:
                    pass

            target.SetFocus()
            return {"success": True, "message": f"Focused window: {target.Name}"}
        else:
            return {"success": False, "error": "Window not found"}

    def _focus_macos(self, query):
        """
        MacOS implementation using atomacos.
        """
        import atomacos

        target_app = None

        if isinstance(query, int):
            # By PID
            for app in atomacos.running_applications():
                if app.pid == query:
                    target_app = app
                    break
        else:
            # By Name
            try:
                target_app = atomacos.get_app(query)
            except:
                pass

        if target_app:
            target_app.activate()
            return {"success": True, "message": f"Activated app: {target_app.bundle_id}"}

        return {"success": False, "error": "App/Window not found"}
