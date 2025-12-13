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

### [0.7.1] - Virtual RootFS & Unified CLI

FyodorOS v0.7.1 introduces a standardized "Virtual RootFS" and a unified CLI.
- **Unified CLI**: The `fyodor` command is now the single entry point.
- **Virtual RootFS**: A strict directory structure rooted at `~/.fyodor/`.
- **Enhanced Security**: All file operations are confined to the virtual root with path traversal protections.

### [0.7.0] - Persistent Memory & Performance

FyodorOS v0.7.0 introduces a major capability for Autonomous Agents: **Memory**.
- **Semantic Storage**: Agents can now store and recall information using `sys_memory_*` syscalls, backed by ChromaDB.
- **Auto-Recall**: The Agent loop automatically searches for relevant past memories before starting a new task, enabling context-aware execution.
- **Persistence**: Memory state is preserved in `~/.fyodor/var/memory` across system reboots.
- **Optimization**: Significant performance improvements in filesystem path resolution (`sys_ls`).

## ✨ Key Features

### 🧠 Kernel-Level Agent
The OS integrates an LLM-powered agent directly into the shell.
- **Command**: `fyodor agent "Research the latest news on AI"`
- **Mechanism**: The agent perceives the system via `SystemDOM`, creates a To-Do list, and executes actions in a sandboxed loop.

### 💾 Persistent Memory
The Agent now remembers.
- **Semantic Recall**: Uses vector embeddings (ChromaDB) to find relevant past interactions.
- **Auto-Injection**: Relevant context is automatically injected into the Agent's prompt.
- **Commands**: `sys_memory_store`, `sys_memory_search`, `sys_memory_delete`.

### 🛡️ Safety Sandbox (Verified v0.6.0)
Every action taken by the Agent is intercepted by the C++ reinforced `AgentSandbox`.
- **Virtual Filesystem**: The agent is jailed in `~/.fyodor/sandbox`. All paths are virtualized.
- **Path Traversal Protection**: C++ layer prevents escaping the sandbox.
- **App Whitelisting**: Only authorized "Agent Apps" can be executed.

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

    **First run:**
    ```bash
    fyodor init
    ```

    **To start:**
    ```bash
    fyodor start
    ```

    **Run Agent Task**
    ```bash
    fyodor agent "Create a file named hello.txt in /home"
    ```

## 🤝 Contributing

FyodorOS is an experimental sandbox. We welcome contributions to:
- Expand the standard library of Agent Apps.
- Improve the DOM representation of system state.
- Implement more complex Sandbox rules.

---
*Built for the future of Autonomous Computing.*

[![Star History](https://api.star-history.com/svg?repos=Kiy-K/FyodorOS&type=Date)](https://star-history.com/#Kiy-K/FyodorOS&Date)
