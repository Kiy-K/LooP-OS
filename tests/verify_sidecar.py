import sys
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

def test_sidecar():
    # 1. Find the binary
    # Try multiple common locations for robustness (CI vs Local)
    possible_paths = [
        Path("src-tauri/bin"),
        Path("gui/src-tauri/bin")
    ]

    bin_dir = None
    for p in possible_paths:
        if p.exists():
            bin_dir = p
            break

    if not bin_dir:
        print(f"Directory not found. Checked: {possible_paths}")
        sys.exit(1)

    # Find the kernel binary
    exes = list(bin_dir.glob("loop-kernel-*"))
    if not exes:
         print(f"No binary found in {bin_dir}")
         sys.exit(1)

    exe = exes[0]

    print(f"Launching {exe}...")

    # 2. Spawn process
    # CRITICAL: Use bufsize=1 (line buffered) to read stdout in real-time
    proc = subprocess.Popen(
        [str(exe), "serve", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # 3. Wait for Port
        port = None
        start_time = time.time()
        # 10s timeout
        while time.time() - start_time < 10:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                     break
                time.sleep(0.1)
                continue

            # Print kernel output for debugging
            print(f"[Kernel] {line.strip()}")
            if "PORT:" in line:
                try:
                    port = int(line.split(":")[1].strip())
                    break
                except ValueError:
                    continue

        if not port:
            # Check stderr if failed
            _, stderr = proc.communicate(timeout=1)
            raise TimeoutError(f"Kernel did not output a PORT. Stderr: {stderr}")

        # 4. Ping
        # The server exposes /health, verifying that ensures it's up.
        url = f"http://127.0.0.1:{port}/health"
        print(f"Pinging {url} ...")

        resp = urllib.request.urlopen(url)
        assert resp.status == 200
        print("SUCCESS: Sidecar is alive.")

    finally:
        if proc.poll() is None:
            proc.kill()

if __name__ == "__main__":
    try:
        test_sidecar()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
