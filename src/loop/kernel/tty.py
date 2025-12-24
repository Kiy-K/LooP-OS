# kernel/tty.py
"""
Terminal Teletype (TTY) Interface.

This module provides a simple interface for text-based input and output,
abstracting the underlying standard I/O streams.
"""

class TTY:
    """
    A TTY device wrapper.

    Provides methods for writing to stdout and reading from stdin.
    """
    def write(self, text):
        """
        Write text to the terminal.

        Args:
            text (str): The text to write.
        """
        # always flush prints
        print(text, end="", flush=True)

    def read(self, prompt=""):
        """
        Read input from the terminal.

        Args:
            prompt (str, optional): The input prompt.

        Returns:
            str: The user input.
        """
        # blocking input
        return input(prompt)
