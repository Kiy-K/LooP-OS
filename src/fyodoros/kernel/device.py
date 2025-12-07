# kernel/device.py
"""
Device Drivers.

This module contains simple abstractions for hardware devices, such as TTY.
"""

from collections import deque

class TTYDevice:
    """
    A simple TTY (Teletypewriter) device abstraction.

    Handles basic input/output operations, buffering output in a deque.

    Attributes:
        buffer (deque): A buffer to store written text.
    """
    def __init__(self):
        """
        Initialize the TTYDevice.
        """
        self.buffer = deque()

    def write(self, text):
        """
        Write text to the device (stdout) and buffer it.

        Args:
            text (str): The text to write.
        """
        print(text, end="", flush=True)
        self.buffer.append(text)

    def read(self):
        """
        Read the next item from the buffer.

        Returns:
            str: The next buffered item, or an empty string if buffer is empty.
        """
        if self.buffer:
            return self.buffer.popleft()
        return ""
