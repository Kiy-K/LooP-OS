
import pytest
import queue
from loop.kernel.io import CLIAdapter, APIAdapter

def test_cli_adapter(capsys):
    adapter = CLIAdapter()
    adapter.write("Hello World")
    captured = capsys.readouterr()
    assert captured.out == "Hello World"

def test_api_adapter_write():
    adapter = APIAdapter()
    adapter.write("Output Line 1")
    adapter.write("Output Line 2")

    assert adapter.get_output() == "Output Line 1"
    assert adapter.get_output() == "Output Line 2"
    assert adapter.get_output() is None

def test_api_adapter_input():
    adapter = APIAdapter()

    # Simulate blocking read in a thread? No, let's just pre-fill queue
    adapter.input("ls -la")

    result = adapter.read(prompt="> ")
    assert result == "ls -la"

    # Prompt should be in output
    assert adapter.get_output() == "> "
