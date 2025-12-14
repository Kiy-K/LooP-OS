# src/fyodoros/cli.py
"""
FyodorOS CLI Entry Point.
"""

import sys
import os
import subprocess
import shutil
import argparse
from pathlib import Path
from fyodoros.kernel import boot, rootfs
from fyodoros.shell.shell import Shell
from fyodoros.kernel.agent import ReActAgent
from fyodoros.kernel.llm import LLMProvider

def init(args):
    """
    Initialize the FyodorOS environment.
    Creates directory structure and migrates data.
    """
    print("Initializing FyodorOS...")
    try:
        # Migration: Check for legacy memory location BEFORE creating structure
        # to ensure we can move it cleanly if needed.
        base = Path.home() / ".fyodor"
        legacy_memory = base / "memory"
        target_memory = base / "var" / "memory"

        # Determine if we need to migrate
        migrated = False
        if legacy_memory.exists() and legacy_memory.is_dir():
            if not target_memory.exists():
                # Safe to move
                # Ensure parent var exists first?
                # init_structure does that, but we haven't run it yet.
                target_memory.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(legacy_memory), str(target_memory))
                print(f"[Migration] Moved legacy memory from {legacy_memory} to {target_memory}")
                migrated = True
            elif not any(target_memory.iterdir()):
                # Target exists but is empty (maybe from a partial run)
                target_memory.rmdir()
                shutil.move(str(legacy_memory), str(target_memory))
                print(f"[Migration] Moved legacy memory from {legacy_memory} to {target_memory}")
                migrated = True
            else:
                print(f"[Migration] Warning: Target {target_memory} exists and is not empty. Skipping migration.")

        # Legacy Plugins (if any) - requirement said "Do the same for plugins if necessary"
        # Assuming legacy plugins were in ~/.fyodor/plugins and we want them there?
        # rootfs.init_structure creates ~/.fyodor/plugins.
        # If they were somewhere else? The prompt doesn't specify legacy location for plugins.
        # Assuming they were in ~/.fyodor/plugins already or not relevant.

        # Execute Structure Creation
        rootfs.init_structure()

        print(f"FyodorOS v0.7.1 initialized at {rootfs.FYODOR_ROOT}")

    except Exception as e:
        print(f"Initialization failed: {e}")
        sys.exit(1)

def start(args):
    """
    Start the FyodorOS Shell (Default).
    """
    print("Booting FyodorOS Shell...")
    try:
        kernel = boot.boot()
        # In CLI mode, we use the default CLIAdapter which kernel creates if None passed
        # boot() currently doesn't pass io_adapter, so kernel defaults to CLIAdapter

        # We need to manually start the shell run loop, or let kernel.start() do it
        # kernel.start() does exactly this.
        kernel.start()
    except Exception as e:
        print(f"Startup failed: {e}")
        sys.exit(1)

def serve(args):
    """
    Start the FyodorOS API Server.
    """
    # Pre-Flight Check for API Keys
    api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]
    found_keys = [key for key in api_keys if os.environ.get(key)]

    if not found_keys:
        print("\n[WARNING] No LLM API Keys detected (OPENAI_API_KEY, etc).")
        print("          The Agent may crash or fail to execute tasks.")
        print("          Please pass keys via -e OPENAI_API_KEY=... or .env file.\n")
    else:
        print(f"[Info] Detected API Keys: {', '.join(found_keys)}")

    print(f"Starting FyodorOS Server on {args.host}:{args.port}...")
    print(f"PORT: {args.port}")
    try:
        import uvicorn
        # We run the app defined in fyodoros.server.main
        uvicorn.run("fyodoros.server.main:app", host=args.host, port=args.port, reload=False)
    except ImportError:
        print("Error: uvicorn is not installed. Please install it to use server mode.")
        sys.exit(1)
    except Exception as e:
        print(f"Server failed: {e}")
        sys.exit(1)

def agent(args):
    """
    Run the AI Agent with a specific task.
    """
    task = args.prompt
    print(f"Starting Agent with task: {task}")
    try:
        kernel = boot.boot()
        llm = LLMProvider()
        agent_instance = ReActAgent(llm, kernel.sys)

        print(f"\n--- Agent Task: {task} ---\n")
        result = agent_instance.run(task)
        print(f"\n--- Result ---\n{result}")

    except Exception as e:
        print(f"Agent execution failed: {e}")
        sys.exit(1)

def check_frozen_status():
    """Returns True if the application is frozen (compiled), False otherwise."""
    return getattr(sys, 'frozen', False)

def check_rootfs_write():
    """Tries to write a temp file to ~/.fyodor/tmp. Returns True if successful."""
    try:
        test_path = Path.home() / ".fyodor" / "tmp" / "test_write"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text("ok")
        content = test_path.read_text()
        success = (content == "ok")
        test_path.unlink(missing_ok=True)
        return success
    except Exception:
        return False

def check_nasm():
    """Runs nasm -v. Returns True if successful."""
    try:
        subprocess.run(["nasm", "-v"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def doctor(args):
    """
    Self-diagnosis tool to check system health and environment.
    """
    print("Running FyodorOS Doctor...\n")

    # 1. Execution Mode
    is_frozen = check_frozen_status()
    mode = "Frozen Binary" if is_frozen else "Python Script"
    print(f"[Mode]      {mode}")

    # 2. RootFS Access
    if check_rootfs_write():
        print("[RootFS]    Write/Read OK")
    else:
        print("[RootFS]    Read mismatch or Failed")

    # 3. NASM Runtime
    if check_nasm():
        print("[NASM]      Assembly Engine Available")
    else:
        print("[NASM]      Warning: Assembly Engine Disabled (nasm not found)")

    # 4. Sidecar Handshake
    sidecar_port = os.environ.get("FYODOR_SIDECAR_PORT")
    if sidecar_port:
        print(f"[Sidecar]   FYODOR_SIDECAR_PORT detected: {sidecar_port}")
    else:
        print("[Sidecar]   No Tauri environment detected (Standalone)")

def main():
    """Main entry point for the CLI script."""
    parser = argparse.ArgumentParser(description="FyodorOS Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init
    parser_init = subparsers.add_parser("init", help="Initialize the environment")
    parser_init.set_defaults(func=init)

    # start
    parser_start = subparsers.add_parser("start", help="Start the shell")
    parser_start.set_defaults(func=start)

    # serve
    parser_serve = subparsers.add_parser("serve", help="Start the API server")
    parser_serve.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind server to")
    parser_serve.add_argument("--port", type=int, default=8000, help="Port to run server on")
    parser_serve.set_defaults(func=serve)

    # agent
    parser_agent = subparsers.add_parser("agent", help="Run the AI Agent")
    parser_agent.add_argument("prompt", help="The task for the agent")
    parser_agent.set_defaults(func=agent)

    # doctor
    parser_doctor = subparsers.add_parser("doctor", help="Run self-diagnosis")
    parser_doctor.set_defaults(func=doctor)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
