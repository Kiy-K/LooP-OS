# FyodorOS
[![PyPI version](https://badge.fury.io/py/fyodoros.svg)](https://badge.fury.io/py/fyodoros)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```
███████╗██╗   ██╗ ██████╗ ██████╗  ██████╗ ██████╗
██╔════╝╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔═══██╗██╔══██╗
█████╗   ╚████╔╝ ██║   ██║██║  ██║██║   ██║██████╔╝
██╔══╝    ╚██╔╝  ██║   ██║██║  ██║██║   ██║██╔══██╗
██║        ██║   ╚██████╔╝██████╔╝╚██████╔╝██║  ██║
╚═╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
          The Experimental AI Microkernel
```

**FyodorOS** is a simulated operating system designed from the ground up for **Autonomous AI Agents**. Unlike traditional OSs designed for humans (GUI/CLI) or servers (API), FyodorOS exposes the entire system state as a **Document Object Model (DOM)**, allowing Agents to "perceive" and interact with the kernel natively.

## 🚀 Vision

We believe that for AI Agents to be truly useful and safe, they need an environment built for them. FyodorOS provides:
*   **Structured Observation**: The OS state (Filesystem, Processes, Users) is a queryable DOM tree.
*   **Cognitive Loop**: Built-in ReAct (Reasoning + Acting) loop at the kernel level.
*   **Safety Sandbox**: A strict, rule-based verification layer that constraints Agent actions before execution.
*   **Agent-Native Apps**: Standard tools (`browser`, `explorer`, `calc`) that return structured JSON/DOM instead of plain text, minimizing token usage and parsing errors.
*   **Cloud Integration (v0.5.0)**: Native Docker and Kubernetes support.

## 📝 What's New

### [0.6.0] - Verified System Integrity (Test Sweep Phase 2.3)

FyodorOS v0.6.0 focuses on system integrity and reliability:
- **Verified Core Subsystems**: Successfully passed extensive adversarial tests for Service Manager, Kernel Boot, Sandbox, and Plugin Lifecycle.
- **Boot Determinism**: Confirmed clean, deterministic startup and shutdown cycles.
- **Teardown Correctness**: Implemented proper LIFO (Last-In-First-Out) service shutdown to prevent ghost processes.
- **Sandbox Security Patch**: Fixed a vulnerability where fallback to Python implementation allowed path traversal. Now enforces strict sandbox rooting.

### [0.5.1] - Performance & Security Hardening

FyodorOS v0.5.1 focuses on stability, security, and speed:
- **Startup Speed**: 10x faster startup via lazy loading of heavy cloud dependencies.
- **Security**: Fixed critical shell login bypass and strengthened sandbox isolation.
- **Stability**: Robust C++ sandbox execution and deadlock prevention.

### [0.5.0] - Cloud Integration

FyodorOS v0.5.0 introduces major cloud capabilities:
- **Docker Integration**: Agent control of containers via `sys_docker_*` syscalls.
- **Kubernetes Integration**: Deployment management and pod inspection.

## ✨ Key Features

### 🧠 Kernel-Level Agent
The OS integrates an LLM-powered agent directly into the shell.
- **Command**: `agent "Research the latest news on AI"`
- **Mechanism**: The agent perceives the system via `SystemDOM`, creates a To-Do list, and executes actions in a sandboxed loop.

### 🌐 Agent Browser (Playwright Integration)
FyodorOS includes a specialized browser for agents.
- **DOM Tree Output**: Returns a simplified, semantic JSON representation of web pages.
- **Interaction**: Agents can `click` and `type` using element IDs directly.
- **Efficiency**: Strips unnecessary noise (CSS/Scripts) to save context window.

### 🛡️ Safety Sandbox (Verified v0.6.0)
Every action taken by the Agent is intercepted by the C++ reinforced `AgentSandbox`.
- **Virtual Filesystem**: The agent is jailed in `~/.fyodor/sandbox`. All paths are virtualized.
- **Path Traversal Protection**: C++ layer prevents escaping the sandbox (e.g., `../../etc/passwd`). Verified Python fallback ensures security even without C++ extensions.
- **Process Isolation**: Commands run with cleared environments and restricted paths.
- **App Whitelisting**: Only authorized "Agent Apps" can be executed.

## 🧪 Test Coverage (v0.6.0)

We maintain rigorous test suites to ensure system invariants hold under pressure.
- **Service Manager**: Boot correctness, reverse teardown, failure resilience.
- **Kernel**: Deterministic boot, double-boot isolation, controlled shutdown.
- **Sandbox**: File resolution integrity, IOError containment, leakage prevention.
- **Plugins**: Lifecycle management (init/exec/teardown), fault tolerance.

Tests are run using `pytest`:
```bash
pytest tests/phase2_3/
```

## 🔌 Plugins (New in v0.3.0)
FyodorOS supports a powerful plugin system.
- **Github Integration**: `github` - List repos, create issues, view PRs.
- **Slack Notifier**: `slack_notifier` - Send notifications to Slack.
- **Usage Dashboard**: `usage_dashboard` - Background system monitoring. View with `fyodor dashboard`.
- **Team Collaboration**: `team_collaboration` - RBAC system extending `UserManager`.

### Managing Plugins
```bash
fyodor plugin list
fyodor plugin activate github
fyodor plugin settings github token YOUR_TOKEN
fyodor plugin deactivate github
```

### Developing Plugins (Polyglot Support)
FyodorOS supports Python, C++, and Node.js plugins.

**Create a new plugin:**
```bash
fyodor plugin create my_plugin --lang cpp
```

**Build a plugin:**
```bash
fyodor plugin build my_plugin
```

**Install from Git:**
```bash
fyodor plugin install https://github.com/user/repo
```

## 📦 Installation & Usage

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Kiy-K/FyodorOS.git
    cd fyodoros
    ```

2.  **Install Package**
    You can install FyodorOS as a Python package.

    **Via pip (Recommended):**
    ```bash
    pip install .
    playwright install chromium
    ```

    **Via Conda:**
    ```bash
    conda env create -f environment.yml
    conda activate fyodoros
    playwright install chromium
    ```

3.  **Launch the OS**

    **Option A: Using the CLI (if installed)**
    ```bash
    # 1. Setup (Configure API Keys)
    fyodor setup

    # 2. Start (Auto-login as Guest)
    fyodor start

    # 3. Interactive Login
    fyodor login

    # 4. Login as specific user (e.g. root)
    fyodor login --user root

    # 5. Create a new user
    fyodor user developer secret123

    # 6. Open Launcher Menu (TUI)
    fyodor tui
    ```

    **Option B: Using Convenience Scripts**
    *   **Windows**: Double-click `run.bat`
    *   **Linux/Mac**: Run `./run.sh`

4.  **Interact**
    Inside the FyodorOS Shell:
    ```bash
    # Run a standard command
    guest@fyodoros:/> ls

    # Task the Agent
    guest@fyodoros:/> agent "Create a file named hello.txt in my home folder"

    # Manual Creation
    guest@fyodoros:/> create notes.txt "Meeting at 5pm"

    # Launch App Manually
    guest@fyodoros:/> navigate browser
    ```

## 💡 Use Cases

### 1. Web Research & Summary
**Scenario:** You want the agent to look up information and save it.
**Command:**
```bash
agent "Go to https://example.com, read the main heading, and save it to /home/guest/summary.txt"
```
**Agent Process:**
1.  Calls `run_process("browser", ["navigate", "https://example.com"])`.
2.  Parses the returned DOM tree to find the `<h1>` tag.
3.  Calls `write_file("/home/guest/summary.txt", ...)` to save the data.

### 2. System Management
**Scenario:** You want to add a new user securely.
**Command:**
```bash
agent "Create a new user named 'developer' with password 'secure123'"
```
**Agent Process:**
1.  Checks if user exists using `run_process("user", ["list"])`.
2.  Calls `run_process("user", ["add", "developer", "secure123"])`.
3.  Verifies the addition.

### 3. File Organization
**Scenario:** Organize a messy directory.
**Command:**
```bash
agent "Move all .txt files from /home/guest to /home/guest/documents"
```
**Agent Process:**
1.  Calls `list_dir("/home/guest")`.
2.  Identifies `.txt` files.
3.  Calls `run_process("explorer", ["move", ...])` for each file.

## 🏗️ Architecture

*   **`src/fyodoros/kernel/`**: Core logic including Scheduler, SyscallHandler, and the new **Agent Layer** (`agent.py`, `dom.py`, `sandbox.py`).
*   **`src/fyodoros/bin/`**: User-space applications. These are "Agent-Aware" binaries that output JSON.
*   **`src/fyodoros/shell/`**: The interactive CLI wrapper.
*   **`src/fyodoros/cli.py`**: The launcher and configuration tool.

## 🤝 Contributing

FyodorOS is an experimental sandbox. We welcome contributions to:
- Expand the standard library of Agent Apps.
- Improve the DOM representation of system state.
- Implement more complex Sandbox rules.

---
*Built for the future of Autonomous Computing.*

[![Star History](https://api.star-history.com/svg?repos=Kiy-K/FyodorOS&type=Date)](https://star-history.com/#Kiy-K/FyodorOS&Date)
