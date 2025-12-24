from abc import ABC, abstractmethod
import queue
import asyncio

class IOAdapter(ABC):
    """
    Abstract Base Class for Input/Output operations.
    Decouples the Kernel/Shell from the console (TTY).
    """
    @abstractmethod
    def write(self, text: str):
        """Write text to the output."""
        pass

    @abstractmethod
    def read(self, prompt: str = "", password: bool = False) -> str:
        """Read input from the user (blocking or via event)."""
        pass

    @abstractmethod
    def flush(self):
        """Flush the output stream."""
        pass

    def signal(self, name: str):
        """Send a control signal to the frontend (e.g. WAKE)."""
        pass

    def get_signal(self):
        """Retrieve a pending signal (non-blocking)."""
        return None


class CLIAdapter(IOAdapter):
    """
    Adapter for standard Command Line Interface (stdin/stdout).
    """
    def write(self, text: str):
        print(text, end="", flush=True)

    def read(self, prompt: str = "", password: bool = False) -> str:
        from rich.prompt import Prompt
        # Use Rich for better prompt handling (including passwords)
        if password:
            return Prompt.ask(prompt, password=True)
        return Prompt.ask(prompt)

    def flush(self):
        import sys
        sys.stdout.flush()

    def signal(self, name: str):
        # CLI doesn't support wake signals in the same way, but we can log it for debug
        pass


class APIAdapter(IOAdapter):
    """
    Adapter for API/Web usage.
    Captures output into a queue for consumption by WebSocket/Response.
    Input is handled via an input queue (populated by API calls).
    Supports a separate signal channel for control events.
    """
    def __init__(self):
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self.signal_queue = queue.Queue()
        self._buffer = []

    def write(self, text: str):
        # We might want to stream lines or chunks
        self.output_queue.put(text)

    def read(self, prompt: str = "", password: bool = False) -> str:
        # Send the prompt to output so the UI knows we are waiting
        # For password prompts in API mode, we might want to flag it?
        # Currently the UI just shows a text field.
        if prompt:
            self.write(prompt)

        # Block until input is received from the API
        # Note: This blocks the thread. The Shell must run in a separate thread.
        return self.input_queue.get()

    def flush(self):
        pass

    def signal(self, name: str):
        """External method to send a signal to the API/Frontend."""
        self.signal_queue.put(name)

    def input(self, text: str):
        """External method to inject input from the API."""
        self.input_queue.put(text)

    def get_output(self, block=False, timeout=None):
        """External method to retrieve output."""
        try:
            return self.output_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def get_signal(self, block=False, timeout=None):
        """External method to retrieve signals."""
        try:
            return self.signal_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None
