class TTY:
    def write(self, text):
        # always flush prints
        print(text, end="", flush=True)

    def read(self, prompt=""):
        # blocking input
        return input(prompt)