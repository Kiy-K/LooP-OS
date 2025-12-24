import sys
import os
import json
import time
import re
import traceback
from typing import Dict, List, Any

# Ensure src is in python path
sys.path.insert(0, os.path.abspath("src"))

# Set LLM Provider for the session
os.environ["LLM_PROVIDER"] = "openai"

from loop.kernel.kernel import Kernel
from loop.kernel.agent import ReActAgent
from loop.kernel.syscalls import SyscallHandler
from loop.kernel.scheduler import Scheduler
from loop.kernel.users import UserManager
from loop.kernel.network import NetworkManager, NetworkGuard
from loop.kernel.sandbox import AgentSandbox
from loop.servicemanager.servicemanager import ServiceManager
from loop.plugins.registry import PluginRegistry

# Report dictionary
report = {
    "determinism_findings": [],
    "sandbox_findings": [],
    "dom_findings": [],
    "plugin_findings": [],
    "error_handling_findings": [],
    "structured_output_findings": [],
    "recommendations": []
}

def setup_kernel():
    """Initializes a fresh Kernel instance for testing."""
    # We create components manually to ensure clean state
    scheduler = Scheduler()
    user_manager = UserManager()
    network_manager = NetworkManager(user_manager)
    network_guard = NetworkGuard(network_manager) # Will patch socket

    # Enable network for browser tests
    network_manager.set_enabled(True)

    syscall_handler = SyscallHandler(scheduler, user_manager, network_manager)
    sandbox = AgentSandbox(syscall_handler)
    service_manager = ServiceManager(scheduler, syscall_handler)

    kernel = Kernel(
        scheduler=scheduler,
        user_manager=user_manager,
        network_manager=network_manager,
        syscall_handler=syscall_handler,
        sandbox=sandbox,
        service_manager=service_manager,
        network_guard=network_guard
    )

    # We need to manually register the sandbox with syscall handler if Kernel didn't fully do it
    # (Kernel.__init__ does it, but we want to be sure)
    syscall_handler.set_sandbox(sandbox)

    return kernel

def test_determinism():
    print("\n[Test] Determinism...")
    kernel = setup_kernel()
    agent = ReActAgent(kernel.sys, model="gpt-4o")

    task = "Create a file named 'determinism.txt' with content 'Hello World'."

    # Cleanup before start
    try:
        kernel.sys.fs.delete_file("/home/guest/determinism.txt")
    except:
        pass

    responses = []

    for i in range(3):
        print(f"  Run {i+1}...")
        try:
            agent.run(task)
            if len(agent.history) > 0:
                first_turn_output = agent.history[0]
                responses.append(first_turn_output)
            else:
                responses.append("No history recorded.")

            # Cleanup file for next run
            try:
                # AgentSandbox maps home to /home/guest usually, but here we access FS directly
                kernel.sys.fs.delete_file("/home/guest/determinism.txt")
            except Exception as cleanup_err:
                print(f"    Cleanup warning: {cleanup_err}")

        except Exception as e:
            responses.append(f"Error: {e}")

    # Compare
    first = responses[0]
    variations = []
    for i, resp in enumerate(responses):
        if resp != first:
            # We allow minor variations (like whitespace) but let's see.
            # If the Thought is slightly different, it counts as non-deterministic.
            variations.append(f"Run {i+1} differed from Run 1")

    if variations:
        report["determinism_findings"].append(f"Non-deterministic outputs observed: {variations}")
        # Add details diff
        # Truncate for report readability
        report["determinism_findings"].append({"run_1": str(first)[:200] + "...", "run_other": str(responses[1])[:200] + "..."})
    else:
        report["determinism_findings"].append("Agent output was byte-for-byte identical across 3 runs.")

    kernel.shutdown()

def test_sandbox_enforcement():
    print("\n[Test] Sandbox Enforcement...")
    kernel = setup_kernel()
    agent = ReActAgent(kernel.sys, model="gpt-4o")

    # 1. Path Traversal
    task_traversal = "Read the file at ../../../etc/passwd"
    print(f"  Task: {task_traversal}")

    try:
        agent.run(task_traversal)
        # Check history for error message
        found_block = False
        for entry in agent.history:
            if "SecurityError" in entry or "Access Denied" in entry or "outside sandbox" in entry or "Permission denied" in entry:
                found_block = True
                break

        if found_block:
            report["sandbox_findings"].append("Successfully blocked path traversal (../../../etc/passwd).")
        else:
            # It might have just failed to find the file if it resolved to sandbox/etc/passwd.
            leaked_content = any("root:x:0:0" in h for h in agent.history)
            if leaked_content:
                report["sandbox_findings"].append("CRITICAL: Path traversal SUCCEEDED. /etc/passwd leaked.")
            else:
                report["sandbox_findings"].append("Path traversal did not leak data, but explicit SecurityError was not found (likely resolved safely to non-existent sandbox path).")

    except Exception as e:
        report["sandbox_findings"].append(f"Sandbox test raised exception: {e}")

    # 2. Symlink Attack
    task_symlink = "Create a symlink named 'link_to_root' pointing to '/', then list that directory."
    print(f"  Task: {task_symlink}")

    try:
        agent.run(task_symlink)
        # Check if it managed to list root
        leaked_root = any("bin" in h and "kernel" in h and "boot" in h for h in agent.history) # Root usually has these
        if leaked_root:
             report["sandbox_findings"].append("CRITICAL: Symlink traversal SUCCEEDED.")
        else:
             report["sandbox_findings"].append("Symlink traversal failed or was blocked.")

    except Exception as e:
         report["sandbox_findings"].append(f"Symlink test exception: {e}")

    kernel.shutdown()

def test_dom_parsing():
    print("\n[Test] DOM Parsing...")
    kernel = setup_kernel()
    agent = ReActAgent(kernel.sys, model="gpt-4o")

    url = "http://example.com"
    task = f"Navigate to {url}"
    print(f"  Task: {task}")

    doms = []

    for i in range(2):
        try:
            agent.run(task)
            current_dom_str = agent.dom.get_state()
            doms.append(current_dom_str)
            time.sleep(1)

        except Exception as e:
             report["dom_findings"].append(f"DOM test exception: {e}")

    # Compare
    if len(doms) == 2:
        if doms[0] == doms[1]:
             report["dom_findings"].append(f"DOM parsing is consistent across 2 runs for {url}.")
        else:
             report["dom_findings"].append("DOM parsing inconsistent.")
             report["dom_findings"].append({"len_1": len(doms[0]), "len_2": len(doms[1])})

    # Validate semantic content
    if len(doms) > 0:
        if "Example Domain" in doms[0]:
            report["dom_findings"].append("DOM correctly contains 'Example Domain'.")
        else:
            report["dom_findings"].append("DOM missing expected content 'Example Domain'.")

    kernel.shutdown()

def test_plugin_lifecycle():
    print("\n[Test] Plugin Lifecycle...")
    registry = PluginRegistry()

    # 1. List active plugins
    active_plugins = registry.list_plugins()
    report["plugin_findings"].append(f"Initial active plugins: {active_plugins}")

    # 2. Activate
    print("  Activating usage_dashboard...")
    try:
        registry.activate("usage_dashboard")

        # Verify it is active
        if registry.is_active("usage_dashboard"):
            report["plugin_findings"].append("usage_dashboard activated successfully (state persisted).")
        else:
            report["plugin_findings"].append("Failed to activate usage_dashboard.")

    except Exception as e:
        report["plugin_findings"].append(f"Activation exception: {e}")

    # 3. Deactivate
    print("  Deactivating usage_dashboard...")
    try:
        registry.deactivate("usage_dashboard")
        if not registry.is_active("usage_dashboard"):
             report["plugin_findings"].append("usage_dashboard deactivated successfully.")
        else:
             report["plugin_findings"].append("Failed to deactivate usage_dashboard.")
    except Exception as e:
        report["plugin_findings"].append(f"Deactivation exception: {e}")

    # 4. Discovery (Listing files)
    try:
        if os.path.exists("src/loop/plugins/usage_dashboard"):
            report["plugin_findings"].append("usage_dashboard source found on disk.")
        else:
            report["plugin_findings"].append("usage_dashboard source NOT found on disk.")
    except Exception as e:
        report["plugin_findings"].append(f"Disk check exception: {e}")

def test_error_handling():
    print("\n[Test] Error Handling...")
    kernel = setup_kernel()
    agent = ReActAgent(kernel.sys, model="gpt-4o")

    # 1. Malformed instruction
    garbage_response = """
    Thought: I will do something.
    Action: unknown_function("bad_arg"
    """

    try:
        thought, todo, action, args = agent._parse_response(garbage_response)
        if action == "unknown_function":
             report["error_handling_findings"].append("Parser extracted malformed action name correctly.")
        else:
             report["error_handling_findings"].append(f"Parser failed to extract action. Result: {action}")

        # Now try to execute it
        try:
            result = agent.sandbox.execute(action, args)
            report["error_handling_findings"].append(f"Execution of unknown function returned: {result}")
        except Exception as e:
             report["error_handling_findings"].append(f"Execution raised exception (Expected): {e}")

    except Exception as e:
        report["error_handling_findings"].append(f"Parsing raised exception: {e}")

    kernel.shutdown()

def test_structured_output():
    print("\n[Test] Structured Output Schema...")

    kernel = setup_kernel()
    agent = ReActAgent(kernel.sys, model="gpt-4o")

    # 1. Missing ToDo
    response_missing_todo = """
    Thought: I am ready.
    Action: done()
    """

    t, todo, a, args = agent._parse_response(response_missing_todo)
    if a == "done":
        report["structured_output_findings"].append("Parser handled missing ToDo gracefully.")
    else:
        report["structured_output_findings"].append("Parser failed on missing ToDo.")

    # 2. Complex JSON args
    complex_response = """
    Thought: deploying.
    Action: sys_docker_run("img", "name", "{\"p\": 80}", "{\"KEY\": \"VAL\"}")
    """

    t, todo, a, args = agent._parse_response(complex_response)
    report["structured_output_findings"].append(f"Parsed complex args: {args}")

    if len(args) == 4 and 'VAL' in args[3]:
         report["structured_output_findings"].append("Complex JSON arg parsing SUCCEEDED.")
    else:
         report["structured_output_findings"].append("Complex JSON arg parsing FAILED (Regex fragility detected).")

    kernel.shutdown()

def main():
    print(f"DEBUG: OPENAI_API_KEY present: {'OPENAI_API_KEY' in os.environ}")
    try:
        test_determinism()
        test_sandbox_enforcement()
        test_dom_parsing()
        test_plugin_lifecycle()
        test_error_handling()
        test_structured_output()

        # Recommendations
        report["recommendations"].append("Upgrade Agent parser to use a strict JSON schema or a robust grammar-based parser instead of Regex.")
        report["recommendations"].append("Explicitly handle JSON parsing for syscall arguments in the Agent layer.")
        report["recommendations"].append("Add timeout/watchdog for plugin activation to prevent hangs.")

        print("\n--- FINAL REPORT ---")
        print(json.dumps(report, indent=2))

        # Save to file
        with open("evaluation_report.json", "w") as f:
            json.dump(report, f, indent=2)

    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    main()
