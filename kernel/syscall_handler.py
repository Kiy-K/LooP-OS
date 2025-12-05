class SyscallHandler:
    def __init__(self, kernel):
        self.kernel = kernel

    def write(self, text):
        # syscall wrapper around TTY write
        self.kernel.tty.write(text)

    def read(self, prompt=""):
        # syscall wrapper around TTY input
        return self.kernel.tty.read(prompt)
    # Additional syscalls can be added here