# Plugin Development Guide

LooP allows developers to extend its functionality using Plugins. A Plugin is a Python package or module that implements the `loop.plugins.Plugin` interface.

## 1. The Plugin Interface

All plugins must inherit from `loop.plugins.Plugin`.

### API Reference

```python
from loop.plugins import Plugin

class MyPlugin(Plugin):
    """
    Base class for LooP plugins.
    """

    def setup(self, kernel):
        """
        Called when the plugin is loaded by the Kernel.

        Args:
            kernel (Kernel): The running Kernel instance. Use this to access
                             kernel.sys (syscalls), kernel.scheduler, etc.
        """
        pass

    def get_shell_commands(self):
        """
        Return shell commands to register.

        Returns:
            dict: A mapping of { "command_name": function_reference }.
                  The function should accept arbitrary arguments (*args).
        """
        return {}

    def get_agent_tools(self):
        """
        Return tools exposed to the AI Agent.
        (Reserved for future Agent Tool Protocol v1)

        Returns:
            list: A list of tool definitions.
        """
        return []
```

## 2. Creating a Simple Plugin

Create a new Python file (e.g., `my_hello_plugin.py`):

```python
from loop.plugins import Plugin

class HelloPlugin(Plugin):
    def setup(self, kernel):
        print("[HelloPlugin] Initialized!")
        self.kernel = kernel

    def get_shell_commands(self):
        return {
            "hello": self.cmd_hello
        }

    def cmd_hello(self, *args):
        name = args[0] if args else "World"
        return f"Hello, {name} from Plugin!"
```

## 3. Installing & Activating

1.  Ensure your plugin file is in the Python path (or installed via pip).
2.  Use the Fyodor CLI to activate it by its module name.

```bash
# If your file is my_hello_plugin.py in the current directory:
export PYTHONPATH=$PYTHONPATH:.

# Activate
loop plugin activate my_hello_plugin

# Verify
loop plugin list
```

3.  Start the OS and test:

```bash
loop start
# Login as guest...
guest@loop:/> hello Fyodor
Hello, Fyodor from Plugin!
```

## 4. Best Practices

*   **Namespace**: If distributing on PyPI, prefix your package with `loop-plugin-` (e.g., `loop-plugin-git`).
*   **State**: Store plugin state in `self`.
*   **Security**: Remember that plugins run with Kernel privileges in this simulation.
