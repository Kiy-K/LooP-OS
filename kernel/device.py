# kernel/device.py

from collections import deque

class TTYDevice:
    def __init__(self):
        self.buffer = deque()

    def write(self, text):
        print(text, end="", flush=True)
        self.buffer.append(text)

    def read(self):
        if self.buffer:
            return self.buffer.popleft()
        return ""
# --- IGNORE ---