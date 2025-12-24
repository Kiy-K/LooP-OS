
import time
import sys
import os

def benchmark_startup():
    start = time.time()
    # We import the main entry point components
    import loop.kernel.kernel
    import loop.shell.shell
    import loop.kernel.syscalls
    end = time.time()
    print(f"Startup Import Time: {end - start:.4f}s")

if __name__ == "__main__":
    benchmark_startup()
