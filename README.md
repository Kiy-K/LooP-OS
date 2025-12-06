# FyodorOS

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

### 🛡️ Safety Sandbox
Every action taken by the Agent is intercepted by the `AgentSandbox`.
- **System Protection**: Prevents writes to `/kernel`, `/bin`, and `/etc`.
- **App Whitelisting**: Only authorized "Agent Apps" can be executed.
- **Transparency**: All actions are logged and verifiable.

## 📦 Installation & Usage

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-org/fyodoros.git
    cd fyodoros
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

3.  **Run the OS**
    ```bash
    python3 fyodoros.py
    ```
    *Note: Set `OPENAI_API_KEY` environment variable for real LLM integration. Otherwise, the system uses a Mock LLM.*

4.  **Interact**
    Inside the FyodorOS Shell:
    ```bash
    # Run a standard command
    guest@fyodoros:/> ls

    # Task the Agent
    guest@fyodoros:/> agent "Create a file named hello.txt in my home folder"

    # Launch Agent Apps manually
    guest@fyodoros:/> run browser navigate https://example.com
    ```

## 🏗️ Architecture

*   **`kernel/`**: Core logic including Scheduler, SyscallHandler, and the new **Agent Layer** (`agent.py`, `dom.py`, `sandbox.py`).
*   **`bin/`**: User-space applications. These are "Agent-Aware" binaries that output JSON.
*   **`shell/`**: The interactive CLI wrapper.
*   **`supervisor/`**: Manages background services.

## 🤝 Contributing

FyodorOS is an experimental sandbox. We welcome contributions to:
- Expand the standard library of Agent Apps.
- Improve the DOM representation of system state.
- Implement more complex Sandbox rules.

---
*Built for the future of Autonomous Computing.*
