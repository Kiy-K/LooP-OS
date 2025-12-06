# kernel/llm.py

import os
import json

class LLMProvider:
    def __init__(self, model="gpt-4"):
        self.model = model
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.is_mock = self.api_key is None

        if not self.is_mock:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("[LLM] openai module not found, falling back to mock.")
                self.is_mock = True

    def generate(self, prompt, stop=None):
        if self.is_mock:
            return self._mock_response(prompt)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are the Kernel Agent for FyodorOS."},
                    {"role": "user", "content": prompt}
                ],
                stop=stop
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"LLM Error: {e}"

    def _mock_response(self, prompt):
        """
        Simple deterministic responses for testing based on keywords.
        """
        prompt_lower = prompt.lower()

        if "test_file.txt" in prompt_lower:
            return """
Thought: The user wants to create a test file. I should check if the directory exists first, then write the file.
ToDo:
1. Check /home/guest exists.
2. Write "Hello World" to /home/guest/test_file.txt.
Action: write_file("/home/guest/test_file.txt", "Hello World")
            """.strip()

        return """
Thought: I need to understand the request.
ToDo:
1. List current directory.
Action: list_dir("/")
        """.strip()
