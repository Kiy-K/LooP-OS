
import time
import sys
import os

def benchmark_startup():
    start = time.time()
    # We import the main entry point components
    import fyodoros.kernel.kernel
    import fyodoros.shell.shell
    import fyodoros.kernel.syscalls
    end = time.time()
    print(f"Startup Import Time: {end - start:.4f}s")

if __name__ == "__main__":
    benchmark_startup()
