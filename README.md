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
*   **Long-Term Memory (v0.7.0)**: Persistent semantic storage allowing agents to learn and recall information.

## 📝 What's New

### [0.7.0] - Persistent Memory & Performance

FyodorOS v0.7.0 introduces a major capability for Autonomous Agents: **Memory**.
- **Semantic Storage**: Agents can now store and recall information using `sys_memory_*` syscalls, backed by ChromaDB.
- **Auto-Recall**: The Agent loop automatically searches for relevant past memories before starting a new task, enabling context-aware execution.
- **Persistence**: Memory state is preserved in `~/.fyodor/memory` across system reboots.
- **Optimization**: Significant performance improvements in filesystem path resolution (`sys_ls`).

### [0.6.0] - Verified System Integrity (Test Sweep Phase 2.3)

FyodorOS v0.6.0 focuses on system integrity and reliability:
- **Verified Core Subsystems**: Successfully passed extensive adversarial tests for Service Manager, Kernel Boot, Sandbox, and Plugin Lifecycle.
- **Boot Determinism**: Confirmed clean, deterministic startup and shutdown cycles.
- **Advanced Service Manager**: New ServiceManager architecture supports DAG-based dependencies and 3-Phase Shutdown.

## ✨ Key Features

### 🧠 Kernel-Level Agent
The OS integrates an LLM-powered agent directly into the shell.
- **Command**: `agent "Research the latest news on AI"`
- **Mechanism**: The agent perceives the system via `SystemDOM`, creates a To-Do list, and executes actions in a sandboxed loop.

### 💾 Persistent Memory
The Agent now remembers.
- **Semantic Recall**: Uses vector embeddings (ChromaDB) to find relevant past interactions.
- **Auto-Injection**: Relevant context is automatically injected into the Agent's prompt.
- **Commands**: `sys_memory_store`, `sys_memory_search`, `sys_memory_delete`.

### 🌐 Agent Browser (Playwright Integration)
FyodorOS includes a specialized browser for agents.
- **DOM Tree Output**: Returns a simplified, semantic JSON representation of web pages.
- **Interaction**: Agents can `click` and `type` using element IDs directly.
- **Efficiency**: Strips unnecessary noise (CSS/Scripts) to save context window.

### 🛡️ Safety Sandbox (Verified v0.6.0)
Every action taken by the Agent is intercepted by the C++ reinforced `AgentSandbox`.
- **Virtual Filesystem**: The agent is jailed in `~/.fyodor/sandbox`. All paths are virtualized.
- **Path Traversal Protection**: C++ layer prevents escaping the sandbox.
- **App Whitelisting**: Only authorized "Agent Apps" can be executed.

## 🧪 Test Coverage (v0.6.0)

We maintain rigorous test suites to ensure system invariants hold under pressure.
- **Service Manager**: Boot correctness, reverse teardown, failure resilience.
- **Kernel**: Deterministic boot, double-boot isolation, controlled shutdown.
- **Sandbox**: File resolution integrity, IOError containment, leakage prevention.

Tests are run using `pytest`:
```bash
pytest tests/phase2_3/
```

## 🔌 Plugins (New in v0.3.0)
FyodorOS supports a powerful plugin system.
- **Github Integration**: `github` - List repos, create issues, view PRs.
- **Slack Notifier**: `slack_notifier` - Send notifications to Slack.
- **Usage Dashboard**: `usage_dashboard` - Background system monitoring. View with `fyodor dashboard`.

### Developing Plugins (Polyglot Support)
FyodorOS supports Python, C++, and Node.js plugins.

**Create a new plugin:**
```bash
fyodor plugin create my_plugin --lang cpp
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

    # 4. Open Launcher Menu (TUI)
    fyodor tui
    ```

4.  **Interact**
    Inside the FyodorOS Shell:
    ```bash
    # Run a standard command
    guest@fyodoros:/> ls

    # Task the Agent
    guest@fyodoros:/> agent "Create a file named hello.txt in my home folder"

    # Manual Creation
    guest@fyodoros:/> create notes.txt "Meeting at 5pm"
    ```

## 💡 Use Cases

### 1. Web Research & Memory
**Scenario:** You want the agent to look up information and remember it for later.
**Command:**
```bash
agent "Find the current stock price of AAPL and save it to memory"
```
**Agent Process:**
1.  Calls `run_process("browser", ["navigate", ...])`.
2.  Parses the page for the price.
3.  Calls `sys_memory_store("AAPL price is $200", {"symbol": "AAPL"})`.
4.  Later, if you ask "What is the AAPL price?", the agent will recall this.

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

## 🏗️ Architecture

*   **`src/fyodoros/kernel/`**: Core logic including Scheduler, SyscallHandler, MemoryManager, and the new **Agent Layer**.
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
