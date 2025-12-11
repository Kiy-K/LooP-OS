# kernel/agent.py
"""
AI Agent for FyodorOS.

This module implements a ReAct (Reasoning and Acting) agent that can
interact with the FyodorOS kernel to perform tasks autonomously.
"""

import json
from fyodoros.kernel.dom import SystemDOM
from fyodoros.kernel.sandbox import AgentSandbox
from fyodoros.kernel.llm import LLMProvider


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

        # Use existing sandbox from syscall handler if available, otherwise create new.
        if hasattr(syscall_handler, 'sandbox') and syscall_handler.sandbox:
            self.sandbox = syscall_handler.sandbox
        else:
            self.sandbox = AgentSandbox(syscall_handler)

        self.llm = LLMProvider(model=model)

        self.max_turns = 10
        self.history = []
        self.todo_list = []

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

        loop_count = 0
        while loop_count < self.max_turns:
            loop_count += 1
            print(f"[Agent] Turn {loop_count}...")

            # 1. Observe / Think
            state = self.dom.get_state()
            prompt = self._construct_prompt(task, state)

            response = self.llm.generate(prompt)
            print(f"[Agent] Response:\n{response}\n")

            self.history.append(f"Turn {loop_count} Output:\n{response}")

            # 2. Parse
            thought, todo, action, args = self._parse_response(response)

            if todo:
                self.todo_list = todo

            # 3. Act
            if action:
                if action == "done":
                    print("[Agent] Task completed.")
                    return "Task Completed"

                result = self.sandbox.execute(action, args)
                print(f"[Agent] Execution Result: {result}")
                self.history.append(f"Turn {loop_count} Result: {result}")
            else:
                self.history.append(f"Turn {loop_count} Result: No action parsed.")

        return "Max turns reached."

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

        return f"""
You are an AI Agent inside FyodorOS.
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
4. Output MUST follow this format exactly:

Thought: <your reasoning>
ToDo:
1. <step 1>
2. <step 2>
Action: <function_name>(<args>)

AVAILABLE ACTIONS:
- list_dir(path)
- read_file(path)
- write_file(path, content)
- append_file(path, content)
- run_process(app_name, args) <-- Use this to run apps: 'browser', 'calc', 'explorer', 'system', 'user'.
- sys_docker_build(path, tag, dockerfile="Dockerfile")
- sys_docker_run(image, name=None, ports=None, env=None)  <-- ports/env should be JSON strings if complex, or None
- sys_docker_stop(container_id)
- sys_docker_logs(container_id)
- sys_k8s_deploy(name, image, replicas=1, namespace="default")
- sys_k8s_scale(name, replicas, namespace="default")
- sys_k8s_delete(name, namespace="default")
- sys_k8s_logs(pod_name, namespace="default")
- done()  <-- Call this when the task is complete.

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
