import pytest
from unittest.mock import MagicMock
from fyodoros.kernel.agent import ReActAgent
from fyodoros.kernel.syscall import SyscallHandler
from fyodoros.kernel.sandbox import AgentSandbox

def test_agent_e2e_flow(tmp_path):
    sys_handler = SyscallHandler()
    sys_handler.sandbox = AgentSandbox(sys_handler)
    # Force Python implementation to respect root_path change
    sys_handler.sandbox.core = None

    # Update root path to tmp dir and sync with SyscallHandler
    sys_handler.sandbox.root_path = str(tmp_path)
    sys_handler.set_sandbox(sys_handler.sandbox) # Sync root path

    # White-list the write_file action for this test (medium risk)
    sys_handler.sandbox.confirmation.whitelist_action("write_file")

    mock_llm_response = """
    {
        "thought": "I will write a file.",
        "todo": ["write file"],
        "action": {
            "name": "write_file",
            "args": ["test.txt", "Hello World"]
        }
    }
    """

    agent = ReActAgent(sys_handler)
    # Ensure agent shares the same sandbox instance (it does by default init logic, but let's be safe)
    agent.sandbox = sys_handler.sandbox

    agent.llm = MagicMock()
    agent.llm.generate.side_effect = [
        mock_llm_response,
        '{"thought": "Done", "todo": [], "action": {"name": "done", "args": []}}'
    ]

    agent.run("Create a hello world file")

    assert (tmp_path / "test.txt").exists()
    assert (tmp_path / "test.txt").read_text() == "Hello World"
