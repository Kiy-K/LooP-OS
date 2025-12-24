import pytest
import json
from loop.kernel.agent import ReActAgent

class MockSyscallHandler:
    def __init__(self):
        self.sandbox = None

@pytest.fixture
def agent():
    return ReActAgent(MockSyscallHandler())

def test_parse_valid_run_process(agent):
    # Use JSON input as the parser strictly expects JSON
    response = """
    {
        "thought": "I need to run the calculator.",
        "todo": ["Run calc"],
        "action": {
            "name": "run_process",
            "args": ["calc", "5", "+", "5"]
        }
    }
    """
    thought, todo, action, args = agent._parse_response(response)
    assert action == "run_process"
    assert args == ["calc", "5", "+", "5"]
    assert "calculator" in thought

def test_parse_nested_json_arg(agent):
    # Simulate an agent passing a JSON string as an argument
    nested_json = json.dumps({"port": 8080})
    response = f"""
    {{
        "thought": "Deploying container",
        "todo": [],
        "action": {{
            "name": "sys_docker_run",
            "args": ["nginx", null, "{nested_json.replace('"', '\\"')}"]
        }}
    }}
    """
    thought, todo, action, args = agent._parse_response(response)
    assert action == "sys_docker_run"
    assert args[0] == "nginx"
    assert isinstance(args[2], str)
    assert "port" in args[2]

def test_parse_malformed_json(agent):
    response = """
    Thought: I will try to act.
    Action: { name: run_process "args": [] }
    """
    thought, todo, action, args = agent._parse_response(response)
    assert action is None
    assert args == []
