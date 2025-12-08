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

### [0.5.1] - Performance & Security Hardening

FyodorOS v0.5.1 focuses on stability, security, and speed:
- **Startup Speed**: 10x faster startup via lazy loading of heavy cloud modules.
- **Security**: Fixed critical shell login bypass and strengthened sandbox isolation.
- **Stability**: Robust C++ sandbox execution and deadlock prevention.

### [0.5.0] - Cloud Integration

FyodorOS v0.5.0 introduces major cloud capabilities:

#### Docker Integration
- **Build & Run**: Build images and run containers directly from the shell or agent.
- **Agent Control**: Agents can autonomously manage containers (`sys_docker_*` syscalls).
- **CLI Commands**: `fyodor docker run`, `fyodor docker build`, `fyodor docker ps`.

#### Kubernetes Integration
- **Deployment Management**: Deploy, scale, and delete K8s resources.
- **Pod Inspection**: View pod status and logs via CLI or Agent.
- **RBAC**: New `manage_docker` and `manage_k8s` permissions.

### [0.4.1]

#### Comprehensive Documentation
The entire codebase has been thoroughly documented with:
- **Full Docstring Coverage**: Every function, class, and module now includes detailed docstrings following Google Style (Python) and JSDoc (JavaScript) conventions.
- **Improved Code Readability**: Clear explanations of purpose, arguments, and return values for all public APIs.

### [0.4.0]

#### Kernel Networking Layer
The kernel now includes a complete networking layer with fine-grained control and security:

- **Global On/Off Switch**: Control network functionality system-wide using `fyodor network` command
- **Strict Socket Enforcement**: All socket operations are intercepted via monkeypatching and routed through the kernel layer for validation
- **RBAC Integration**: Network access is controlled through role-based permissions:
  - `manage_network`: Permission to enable/disable network globally
  - `use_network`: Permission to create and use network sockets

#### NASM Runtime
Execute native assembly code safely within the FyodorOS environment:

- **C++ FFI Sandbox Extension**: Run NASM assembly code in a fully sandboxed environment with C++ FFI bindings
- **`sys_exec_nasm` Syscall**: New kernel syscall enables safe execution of NASM code from user-space and agent processes

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

### 🛡️ Safety Sandbox (Enhanced in v0.3.5)
Every action taken by the Agent is intercepted by the C++ reinforced `AgentSandbox`.
- **Virtual Filesystem**: The agent is jailed in `~/.fyodor/sandbox`. All paths are virtualized.
- **Path Traversal Protection**: C++ layer prevents escaping the sandbox (e.g., `../../etc/passwd`).
- **Process Isolation**: Commands run with cleared environments and restricted paths.
- **App Whitelisting**: Only authorized "Agent Apps" can be executed.

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
