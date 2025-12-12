
import pytest
import shutil
import tempfile
import time
from unittest.mock import Mock, patch
from fyodoros.kernel.memory import MemoryManager
from fyodoros.kernel.resource_monitor import ResourceMonitor
from fyodoros.utils.error_recovery import ErrorRecovery
from fyodoros.kernel.confirmation import ConfirmationManager
from fyodoros.kernel.action_logger import ActionLogger
from pathlib import Path

# --- Memory Tests ---
def test_memory_manager():
    # Use a temp dir for memory
    with tempfile.TemporaryDirectory() as tmpdir:
        mm = MemoryManager(persistence_path=tmpdir)

        # Test Store
        doc_id = mm.store("The sky is blue", {"source": "observation"})
        assert doc_id is not None

        # Test Retrieve
        results = mm.recall("sky")
        assert len(results) >= 1
        assert results[0]["content"] == "The sky is blue"
        assert results[0]["metadata"]["source"] == "observation"

        # Test Clear
        mm.clear()
        assert mm.count() == 0

# --- Resource Monitor Tests ---
def test_resource_monitor():
    rm = ResourceMonitor()

    # Test tracking
    rm.track_tokens("gpt-3.5-turbo", 1000, 100)
    # Input cost: 1000/1000 * 0.0015 = 0.0015
    # Output cost: 100/1000 * 0.002 = 0.0002
    # Total: 0.0017
    stats = rm.get_stats()
    assert stats["tokens"] == 1100
    assert abs(stats["cost"] - 0.0017) < 0.0001

    # Test limits (mocking usage)
    rm.usage["total_cost"] = 100.0 # Way over budget
    error = rm.check_limits()
    assert error is not None and "Budget exceeded" in error

# --- Error Recovery Tests ---
def test_error_recovery_retry():
    mock_func = Mock(side_effect=[ValueError("Fail 1"), ValueError("Fail 2"), "Success"])

    @ErrorRecovery.retry(max_attempts=3, backoff_factor=0.1)
    def test_func():
        return mock_func()

    res = test_func()
    assert res == "Success"
    assert mock_func.call_count == 3

def test_error_recovery_fallback():
    @ErrorRecovery.fallback(lambda: "Fallback")
    def fail_func():
        raise Exception("Boom")

    assert fail_func() == "Fallback"

# --- Confirmation Tests ---
def test_confirmation_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = ConfirmationManager()
        cm.config_path = Path(tmpdir) / "trust.json"

        # Test Risk Assessment
        assert cm.assess_risk("delete_file") == "HIGH"
        assert cm.assess_risk("write_file") == "MEDIUM"
        assert cm.assess_risk("list_dir") == "LOW"

        # Test Whitelist
        assert cm.request_approval("list_dir", []) is True

        # Mock interactive confirm for HIGH risk
        with patch("rich.prompt.Confirm.ask", return_value=True) as mock_ask:
            assert cm.request_approval("delete_file", ["/tmp/test"]) is True
            mock_ask.assert_called_once()

        # Whitelist action
        cm.whitelist_action("delete_file")
        assert cm.request_approval("delete_file", ["/tmp/test"]) is True

# --- Action Logger Tests ---
def test_action_logger():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ActionLogger()
        logger.log_dir = Path(tmpdir)
        logger.log_file = logger.log_dir / "actions.jsonl"

        logger.log_action("task1", 1, "thinking", "act", [], "ok", 100)

        logs = logger.get_logs("task1")
        assert len(logs) == 1
        assert logs[0]["action"] == "act"
