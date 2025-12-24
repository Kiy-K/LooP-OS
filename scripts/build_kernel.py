import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def get_target_triple():
    """
    Determine the Rust-style target triple for the current machine.
    Tauri expects sidecars to be named <binary>-<target-triple><.exe>
    """
    machine = platform.machine().lower()
    system = platform.system().lower()

    # Map machine architecture
    if machine in ['x86_64', 'amd64']:
        arch = 'x86_64'
    elif machine in ['aarch64', 'arm64']:
        arch = 'aarch64'
    else:
        arch = machine # Fallback

    # Map system and abi
    if system == 'windows':
        target = 'pc-windows-msvc'
    elif system == 'linux':
        target = 'unknown-linux-gnu'
    elif system == 'darwin':
        target = 'apple-darwin'
    else:
        target = 'unknown'

    return f"{arch}-{target}"

def build():
    # Configuration
    binary_name = "loop-kernel"
    repo_root = Path(__file__).parent.parent
    src_dir = repo_root / "src"
    output_dir = repo_root / "gui" / "src-tauri" / "bin"

    target_triple = get_target_triple()
    extension = ".exe" if platform.system().lower() == "windows" else ""

    # Generic name for CI (and initial build)
    generic_binary_name = f"{binary_name}{extension}"

    # Target triple name for Tauri (Local Dev)
    triple_binary_name = f"{binary_name}-{target_triple}{extension}"

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[Build] Target Triple: {target_triple}")
    print(f"[Build] Generic Output: {output_dir / generic_binary_name}")

    # Nuitka Command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--assume-yes-for-downloads",
        "--include-package=loop",
        "--include-package-data=loop",
        "--output-dir=" + str(output_dir),
        "--output-filename=" + generic_binary_name,
        "--enable-plugin=pylint-warnings",
        str(src_dir / "loop" / "cli.py") # Entry point
    ]

    print(f"[Build] Running: {' '.join(cmd)}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)

    try:
        subprocess.run(cmd, env=env, check=True)
        print("[Build] Success!")

        # Local Development Helper
        # If not in CI, create the triple-suffixed copy so local 'tauri build' works
        if not os.environ.get("CI"):
            src = output_dir / generic_binary_name
            dst = output_dir / triple_binary_name
            print(f"[Build] Local Dev: Copying to {dst}")
            shutil.copy2(src, dst)

    except subprocess.CalledProcessError as e:
        print(f"[Build] Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
