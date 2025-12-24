# kernel/llm.py
"""
LLM Provider Abstraction.

This module provides a unified interface for interacting with various Large Language Models
(LLMs) such as OpenAI, Gemini, and Anthropic. It also includes a mock provider for
testing and offline development.
"""

import os
import json


class LLMProvider:
    """
    A unified interface for different LLM providers.

    Handles initialization, authentication, and generation of responses from
    OpenAI, Gemini, Anthropic, or a mock backend.

    Attributes:
        provider (str): The name of the provider (e.g., 'openai', 'gemini').
        model (str): The specific model name to use.
        is_mock (bool): True if running in mock mode.
        client (object): The underlying client object for the API.
    """

    def __init__(self, model=None):
        """
        Initialize the LLMProvider.

        Args:
            model (str, optional): Specific model to use. If None, uses a default based on provider.
        """
        self.provider = os.environ.get("LLM_PROVIDER", "mock").lower()
        self.model = model or self._default_model_for_provider()
        self.is_mock = False
        self.client = None

        self._init_client()

    def _default_model_for_provider(self):
        """
        Get the default model name for the current provider.

        Returns:
            str: The default model name.
        """
        if self.provider == "openai":
            return "gpt-4o"
        elif self.provider == "gemini":
            return "gemini-pro"
        elif self.provider == "anthropic":
            return "claude-3-sonnet-20240229"
        else:
            return "mock"

    def _init_client(self):
        """
        Initialize the API client for the selected provider.
        Sets is_mock to True if initialization fails or API keys are missing.
        """
        if self.provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                print("[LLM] OPENAI_API_KEY missing. Falling back to mock.")
                self.is_mock = True
                return
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            except ImportError:
                print("[LLM] openai module missing. Falling back to mock.")
                self.is_mock = True

        elif self.provider == "gemini":
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                print("[LLM] GOOGLE_API_KEY missing. Falling back to mock.")
                self.is_mock = True
                return
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.client = genai
            except ImportError:
                print("[LLM] google-generativeai missing. Falling back to mock.")
                self.is_mock = True

        elif self.provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("[LLM] ANTHROPIC_API_KEY missing. Falling back to mock.")
                self.is_mock = True
                return
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                print("[LLM] anthropic module missing. Falling back to mock.")
                self.is_mock = True

        else:
            self.is_mock = True

    def generate(self, prompt, stop=None):
        """
        Generate a response from the LLM.

        Args:
            prompt (str): The prompt to send to the LLM.
            stop (list, optional): List of stop sequences.

        Returns:
            str: The generated text response.
        """
        if self.is_mock:
            return self._mock_response(prompt)

        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are the Kernel Agent for LooP."},
                        {"role": "user", "content": prompt}
                    ],
                    stop=stop
                )
                return response.choices[0].message.content

            elif self.provider == "gemini":
                # Google GenAI
                model = self.client.GenerativeModel(self.model)
                # Gemini doesn't support system prompts in same way for all models, usually prepend or use config.
                # Just prepend system prompt.
                full_prompt = f"You are the Kernel Agent for LooP.\n\n{prompt}"
                response = model.generate_content(full_prompt)
                return response.text

            elif self.provider == "anthropic":
                # Anthropic uses 'system' param
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    system="You are the Kernel Agent for LooP.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.content[0].text

        except Exception as e:
            return f"LLM Error ({self.provider}): {e}"

    def _mock_response(self, prompt):
        """
        Simple deterministic responses for testing based on keywords.

        Args:
            prompt (str): The input prompt.

        Returns:
            str: A mocked response.
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
