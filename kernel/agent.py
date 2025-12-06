# kernel/agent.py

import re
from kernel.dom import SystemDOM
from kernel.sandbox import AgentSandbox
from kernel.llm import LLMProvider

class ReActAgent:
    def __init__(self, syscall_handler, model="gpt-3.5-turbo"):
        self.sys = syscall_handler
        self.dom = SystemDOM(syscall_handler)
        self.sandbox = AgentSandbox(syscall_handler)
        self.llm = LLMProvider(model=model)

        self.max_turns = 10
        self.history = []
        self.todo_list = []

    def run(self, task):
        """
        Executes the ReAct loop for a given task.
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
- done()  <-- Call this when the task is complete.

Do not interact with system files (/kernel, /bin, /etc).
"""

    def _parse_response(self, text):
        """
        Parses Thought, ToDo, and Action from the LLM output.
        Returns: (thought, todo_list, action_name, action_args)
        """
        thought = ""
        todo = []
        action = None
        args = []

        # Regex extraction
        # Thought
        m_thought = re.search(r"Thought:\s*(.*?)(?=ToDo:|Action:|$)", text, re.DOTALL)
        if m_thought:
            thought = m_thought.group(1).strip()

        # ToDo
        m_todo = re.search(r"ToDo:\s*(.*?)(?=Action:|$)", text, re.DOTALL)
        if m_todo:
            todo_text = m_todo.group(1).strip()
            # Simple line splitting for todo items
            todo = [line.strip() for line in todo_text.split('\n') if line.strip()]

        # Action
        m_action = re.search(r"Action:\s*(\w+)\((.*?)\)", text, re.DOTALL)
        if m_action:
            action = m_action.group(1)
            args_str = m_action.group(2)
            # Naive arg parsing (handling quotes)
            # We assume args are either quoted strings or simple values.
            # Using eval() is risky but safe-ish if we trust the regex context AND we are sandboxed.
            # But let's try to parse strings manually or use a safer parser.
            # For now, let's use a simple split or regex for args.

            # Try to handle: "arg1", "arg2"
            # match quoted strings
            args = re.findall(r'"(.*?)"', args_str)
            if not args and args_str.strip():
                # Maybe unquoted?
                args = [args_str.strip()]

        return thought, todo, action, args
