# src/fyodoros/cli.py
"""
FyodorOS CLI Entry Point.
"""

import sys
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
        if hasattr(kernel, "shell") and kernel.shell:
            kernel.shell.run()
        else:
            # Fallback
            shell = Shell(kernel.sys, kernel.service_manager)
            shell.run()
    except Exception as e:
        print(f"Startup failed: {e}")
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

    # agent
    parser_agent = subparsers.add_parser("agent", help="Run the AI Agent")
    parser_agent.add_argument("prompt", help="The task for the agent")
    parser_agent.set_defaults(func=agent)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
