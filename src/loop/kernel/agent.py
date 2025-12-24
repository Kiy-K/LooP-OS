# kernel/agent.py
"""
AI Agent for LooP.

This module implements a ReAct (Reasoning and Acting) agent that can
interact with the LooP kernel to perform tasks autonomously.
"""

import json
import hashlib
import time
import inspect
from loop.kernel.dom import SystemDOM
from loop.kernel.sandbox import AgentSandbox
from loop.kernel.llm import LLMProvider
from loop.kernel.resource_monitor import ResourceMonitor
from loop.utils.error_recovery import ErrorRecovery
from loop.utils.logging import ActionLogger


class ReActAgent:
    """
    A ReAct-based AI agent that interacts with the OS.

    The agent uses an LLM to reason about tasks, plan steps, and execute
    actions via a sandboxed interface.

    Attributes:
        sys (SyscallHandler): The system call handler.
        dom (SystemDOM): The Document Object Model representation of the system.
        sandbox (AgentSandbox): The sandboxed execution environment.
        llm (LLMProvider): The Large Language Model provider.
        max_turns (int): Maximum number of reasoning turns allowed per task.
        history (list): History of interactions in the current task.
        todo_list (list): List of planned steps.
        extra_tools (dict): Dictionary of dynamically registered tools {name: {'func': func, 'desc': desc}}.
    """

    def __init__(self, syscall_handler, model="gpt-3.5-turbo"):
        """
        Initialize the ReActAgent.

        Args:
            syscall_handler (SyscallHandler): The kernel syscall handler.
            model (str, optional): The name of the LLM model to use. Defaults to "gpt-3.5-turbo".
        """
        self.sys = syscall_handler
        self.dom = SystemDOM(syscall_handler)
        self.resource_monitor = ResourceMonitor()
        self.action_logger = ActionLogger()
        self.model = model

        # Use existing sandbox from syscall handler if available, otherwise create new.
        if hasattr(syscall_handler, 'sandbox') and syscall_handler.sandbox:
            self.sandbox = syscall_handler.sandbox
        else:
            self.sandbox = AgentSandbox(syscall_handler)

        self.llm = LLMProvider(model=model)

        self.max_turns = 10
        self.history = []
        self.todo_list = []
        self.extra_tools = {}

        # Initialize Plugins (if available)
        if hasattr(self.sys, 'plugin_loader') and self.sys.plugin_loader:
             try:
                 self.sys.plugin_loader.load_all_plugins(self)
             except Exception as e:
                 print(f"[Agent] Failed to load plugins: {e}")

    def register_tool(self, func, description_override=None):
        """
        Registers a new tool for the agent to use.

        Args:
            func (callable): The function to register.
            description_override (str, optional): A description of the tool.
                                                  If None, uses the function's docstring.
        """
        name = func.__name__
        # Clean up description
        desc = description_override or func.__doc__ or "No description provided."
        desc = desc.strip().replace("\n", " ")

        # Parse arguments to generate a signature hint
        sig = inspect.signature(func)
        params = [str(p) for p in sig.parameters.values()]
        signature = f"{name}({', '.join(params)})"

        self.extra_tools[name] = {
            "func": func,
            "description": f"{signature} <-- {desc}"
        }
        print(f"[Agent] Registered tool: {name}")

    def inject_context(self, message: str):
        """
        Injects a context message into the agent's short-term memory (history).
        Used when the environment changes asynchronously (e.g., wake signal).
        """
        print(f"[Agent] Context Injected: {message[:100]}...")
        self.history.append(f"System Note: {message}")

    def run(self, task):
        """
        Executes the ReAct loop for a given task.

        Args:
            task (str): The task description from the user.

        Returns:
            str: The final result or status of the task.
        """
        print(f"[Agent] Starting task: {task}")
        self.history = [] # Reset history per task
        self.todo_list = []

        # Generate Task ID
        task_id = hashlib.md5(f"{task}{time.time()}".encode()).hexdigest()[:8]

        # Auto-recall memory
        try:
            # Check if sys_memory_search exists (in case running on old syscalls)
            if hasattr(self.sys, 'sys_memory_search'):
                memories = self.sys.sys_memory_search(task, limit=3)
                if memories:
                    mem_str = "\n".join([f"- {m['content']} (Meta: {m['metadata']})" for m in memories])
                    print(f"[Agent] Recalled relevant memories:\n{mem_str}")
                    self.history.append(f"System Note: Relevant past memories:\n{mem_str}")
        except Exception as e:
            print(f"[Agent] Memory recall failed: {e}")

        loop_count = 0
        while loop_count < self.max_turns:
            loop_count += 1
            print(f"[Agent] Turn {loop_count}...")

            # 0. Check Limits
            limit_error = self.resource_monitor.check_limits()
            if limit_error:
                print(f"[Agent] Resource Limit Reached: {limit_error}")
                return f"Stopped: {limit_error}"

            # 1. Observe / Think
            state = self.dom.get_state()
            prompt = self._construct_prompt(task, state)

            # Count input tokens (approx)
            input_chars = len(prompt)
            input_tokens = input_chars // 4

            # Wrap LLM call with retry logic
            try:
                response = self._generate_with_retry(prompt)
            except Exception as e:
                print(f"[Agent] LLM Generation Failed: {e}")
                return f"Error: LLM Generation Failed after retries: {e}"

            # Count output tokens
            output_chars = len(response)
            output_tokens = output_chars // 4

            self.resource_monitor.track_tokens(self.model, input_tokens, output_tokens)

            print(f"[Agent] Response:\n{response}\n")

            self.history.append(f"Turn {loop_count} Output:\n{response}")

            # 2. Parse
            thought, todo, action, args = self._parse_response(response)

            if todo:
                self.todo_list = todo

            # 3. Act
            if action:
                start_act = time.time()
                result = None

                if action == "done":
                    print("[Agent] Task completed.")
                    # Log final step
                    self.action_logger.log_action(task_id, loop_count, thought, "done", [], "Success", 0, input_tokens+output_tokens)
                    return "Task Completed"

                # Check Extra Tools first
                if action in self.extra_tools:
                    try:
                        func = self.extra_tools[action]["func"]
                        result = func(*args)
                    except Exception as e:
                        result = f"Error executing tool {action}: {e}"
                else:
                    # Execute via Sandbox
                    result = self.sandbox.execute(action, args)

                duration = (time.time() - start_act) * 1000

                # Log Action
                self.action_logger.log_action(task_id, loop_count, thought, action, args, result, duration, input_tokens+output_tokens)

                display_result = str(result)[:500] + "... [Truncated]" if len(str(result)) > 500 else str(result)
                print(f"[Agent] Execution Result: {display_result}")
                self.history.append(f"Turn {loop_count} Result: {result}")
            else:
                self.history.append(f"Turn {loop_count} Result: No action parsed.")

        return "Max turns reached."

    @ErrorRecovery.retry_with_backoff(retries=3, backoff_in_seconds=1)
    def _generate_with_retry(self, prompt):
        return self.llm.generate(prompt)

    def _construct_prompt(self, task, state):
        """
        Constructs the prompt for the LLM.

        Args:
            task (str): The current task.
            state (str): The current system state (DOM).

        Returns:
            str: The fully constructed prompt.
        """
        history_text = "\n".join(self.history[-3:]) # Keep last 3 turns

        # Build registered tools list
        extra_tools_list = ""
        if self.extra_tools:
            extra_tools_list = "\n- ".join([t["description"] for t in self.extra_tools.values()])
            extra_tools_list = "- " + extra_tools_list

        return f"""
You are an AI Agent inside LooP.
Your goal is to complete the user's Task.

SYSTEM STATE (DOM):
{state}

CURRENT TODO LIST:
{self.todo_list}

HISTORY:
{history_text}

TASK: {task}

INSTRUCTIONS:
1. Analyze the state and history.
2. Update your ToDo list if needed.
3. Choose a single Action to perform.
4. Output MUST be a valid JSON object with no markdown formatting:
{{
  "thought": "<your reasoning>",
  "todo": ["<step 1>", "<step 2>"],
  "action": {{
      "name": "<function_name>",
      "args": [<arg1>, <arg2>]
  }}
}}

AVAILABLE ACTIONS:
- list_dir(path)
- read_file(path)
- write_file(path, content)
- append_file(path, content)
- run_process(app_name, args) <-- Use this to run apps: 'browser', 'calc', 'explorer', 'system', 'user'.
- read_screen() <-- Scans the active window for UI elements. Returns a JSON DOM. Use this BEFORE interacting.
- interact(uid, action, payload=None) <-- Interact with a UI element using its UID. Params: uid, action (click/type), payload.
- sys_memory_store(content, metadata) <-- Store useful facts for later.
- sys_memory_search(query) <-- Search for past information.
- sys_memory_recall(query) <-- Same as search.
- sys_memory_delete(key_id_or_query) <-- Delete memory.
- sys_docker_build(path, tag, dockerfile="Dockerfile")
- sys_docker_run(image, name=None, ports=None, env=None)
- sys_docker_stop(container_id)
- sys_docker_logs(container_id)
- sys_k8s_deploy(name, image, replicas=1, namespace="default")
- sys_k8s_scale(name, replicas, namespace="default")
- sys_k8s_delete(name, namespace="default")
- sys_k8s_logs(pod_name, namespace="default")
- launch_app(app_name) <-- Launch a host application by name (e.g., 'Launch Chrome').
- done()  <-- Call this when the task is complete.
{extra_tools_list}

Do not interact with system files (/kernel, /bin, /etc).
"""

    def _parse_response(self, text):
        """
        Parses Thought, ToDo, and Action from the LLM output.

        Args:
            text (str): The raw output from the LLM.

        Returns:
            tuple: A tuple containing:
                - thought (str): The agent's reasoning.
                - todo_list (list): The list of todo items.
                - action_name (str): The name of the action to execute.
                - action_args (list): The arguments for the action.
        """
        thought = ""
        todo = []
        action = None
        args = []

        try:
            json_str = text.strip()
            # Remove markdown code blocks
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            elif json_str.startswith("```"):
                json_str = json_str[3:]

            if json_str.endswith("```"):
                json_str = json_str[:-3]

            # Locate strict JSON block
            start = json_str.find("{")
            end = json_str.rfind("}")

            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
                data = json.loads(json_str)

                thought = data.get("thought", "")
                todo = data.get("todo", [])

                # Check for action object
                if "action" in data:
                    action_data = data["action"]
                    if isinstance(action_data, dict):
                        action = action_data.get("name")
                        args = action_data.get("args", [])

        except (json.JSONDecodeError, AttributeError):
            # Deterministic failure behavior
            pass

        return thought, todo, action, args
