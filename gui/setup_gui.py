#!/usr/bin/env python3
"""
GUI Setup Script.

This script automates the installation and compilation of the LooP Desktop GUI.
It checks for necessary dependencies (Node.js/npm, Rust/Cargo), installs NPM packages,
and builds the Tauri application in release mode.
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    """
    Main entry point for the GUI setup script.
    """
    gui_dir = Path(__file__).parent.resolve()
    print(f"Installing LooP GUI in {gui_dir}...")

    # Check for npm
    try:
        subprocess.check_call(["npm", "--version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: 'npm' not found. Please install Node.js.")
        sys.exit(1)

    # Check for cargo
    try:
        subprocess.check_call(["cargo", "--version"], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: 'cargo' not found. Please install Rust.")
        sys.exit(1)

    # Install NPM dependencies
    print("Installing NPM dependencies...")
    subprocess.check_call(["npm", "install"], cwd=gui_dir)

    # Build Tauri App
    print("Building Tauri App (Release)...")
    try:
        subprocess.check_call(["npm", "run", "tauri", "build"], cwd=gui_dir)
        print("Build complete.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
