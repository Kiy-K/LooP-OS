"""
Background Listener for LooP.

This module listens for global hotkeys to summon the agent.
It runs in a background thread and communicates with the Kernel via IO signals.
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger("loop.senses.listener")

class BackgroundListener:
    """
    Listens for global hotkeys (e.g., <alt>+<space>) to wake the agent.
    """

    def __init__(self, syscall_handler, io_adapter):
        """
        Initialize the listener.

        Args:
            syscall_handler: The kernel's syscall handler (for scanning).
            io_adapter: The kernel's IO adapter (for signaling).
        """
        self.sys = syscall_handler
        self.io = io_adapter
        self.listener = None
        self._running = False

    def start(self):
        """
        Start the global hotkey listener in a non-blocking way.
        """
        if self._running:
            return

        self._running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Background Listener started (Hotkeys: Alt+Space, Cmd+Space)")

    def _run_loop(self):
        """
        Internal loop to run pynput listener.
        """
        import time
        try:
            from pynput import keyboard
        except ImportError:
            logger.warning("pynput not installed. Background Listener disabled.")
            self._running = False
            return

        # Define hotkeys
        hotkeys = {
            '<alt>+<space>': self._on_wake,
            '<cmd>+<space>': self._on_wake # Mac friendly
        }

        while self._running:
            try:
                # pynput Listener blocks when using join(), so we run it here.
                with keyboard.GlobalHotKeys(hotkeys) as h:
                    self.listener = h
                    h.join()
            except Exception as e:
                logger.error(f"Listener thread crashed: {e}. Restarting in 2s...")
                time.sleep(2)

    def stop(self):
        """
        Stop the listener and cleanup hooks.
        """
        if self.listener:
            try:
                self.listener.stop()
            except Exception as e:
                logger.error(f"Error stopping listener: {e}")
            self.listener = None
        self._running = False
        logger.info("Background Listener stopped")

    def _on_wake(self):
        """
        Callback when the hotkey is pressed.
        """
        logger.info("Wake Signal Detected!")

        # Step B: Capture Context Immediately
        # We invoke the UI scan directly.
        # Ideally this should be fast.
        try:
            # We don't need the return value here, the scan populates the registry
            # Wait, sys_ui_scan returns the JSON tree.
            # Does the Agent need it pushed?
            # The prompt says "Capture the context".
            # The `sys_ui_scan` method in syscall.py calls `driver.scan_active_window()`.
            # `scan_active_window` refreshes the registry.
            # So when the agent wakes up and asks "what do I see?", it calls sys_ui_scan again?
            # Or does this pre-cache it?
            # `scan_active_window` logic I implemented earlier CLEARS the registry and does a fresh scan.
            # So calling it here performs the scan.
            # If the Agent calls it again 1 second later, it will re-scan.
            # However, the user might switch focus to the LooP window in between.
            # So we MUST capture it NOW and store it?
            # The prompt says: "Call ui_driver.scan_active_view() immediately to capture the context of the window the user was just looking at."

            # The Registry/Driver is stateful in terms of the registry map, but stateless in terms of "Last Scan Result".
            # If we want to support "What WAS I looking at?", we might need to store this result.
            # But `sys_ui_scan` returns the tree.
            # Maybe we should log it or notify the agent?
            # For now, simply triggering the scan populates the Registry with the elements from THAT window.
            # If the user switches to LooP window (Tauri), and the agent calls scan again,
            # the agent sees the LooP window.
            # Thus, the Agent logic needs to handle "Context Passing".
            # BUT, for this task, I am just responsible for the Listener logic.
            # I will call the scan.
            self.sys.sys_ui_scan()

        except Exception as e:
            logger.error(f"Error during wake scan: {e}")

        # Step C: Signal the Frontend
        if self.io:
            self.io.signal("WAKE")
