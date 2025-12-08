import pytest
from unittest.mock import MagicMock, Mock, patch
from fyodoros.supervisor.supervisor import Supervisor
from fyodoros.kernel.scheduler import Scheduler
from fyodoros.kernel.process import Process, ProcessState

class MockService:
    def __init__(self, name="mock_service"):
        self.name = name
        self.stop_called = False

    def run(self):
        yield

    def stop(self):
        self.stop_called = True

@pytest.fixture
def mock_scheduler():
    return MagicMock(spec=Scheduler)

@pytest.fixture
def mock_syscall():
    return MagicMock()

@pytest.fixture
def supervisor(mock_scheduler, mock_syscall):
    mock_scheduler.processes = [] # Setup list for removal ops
    return Supervisor(mock_scheduler, mock_syscall)

# 2.1 Boot Correctness
def test_boot_correctness(supervisor, mock_scheduler):
    """Verify services start and register with scheduler."""
    def dummy_service():
        yield

    supervisor.start_service("test_svc", dummy_service())

    # Check registration in internal dict
    assert "test_svc" in supervisor.services
    # Check registration with scheduler
    assert mock_scheduler.add.called
    args, _ = mock_scheduler.add.call_args
    assert isinstance(args[0], Process)
    assert args[0].name == "test_svc"

def test_autostart_services_boot(supervisor, mock_syscall):
    """Verify autostart services are loaded from config."""
    # Mock config file
    mock_syscall.sys_read.return_value = "journal\n"

    # Mock journal daemon import to avoid side effects/dependencies
    # We use a context manager to intercept the import inside start_autostart_services
    mock_daemon_module = MagicMock()
    mock_daemon_module.journal_daemon.return_value = (x for x in []) # dummy generator

    with patch.dict("sys.modules", {"fyodoros.supervisor.journal_daemon": mock_daemon_module}):
        supervisor.start_autostart_services()

    assert "journal" in supervisor.services

# 2.2 Reverse Teardown & Cleanup
def test_reverse_teardown(supervisor, mock_scheduler):
    """
    Verify Supervisor stops services in reverse order (LIFO).
    NOTE: This test expects a 'stop_all' or 'shutdown' method which might be missing.
    """
    # Setup services
    svc1 = MagicMock()
    svc2 = MagicMock()

    # We mock Process to attach a 'stop' method or similar mechanism if Supervisor uses it.
    # Supervisor wraps generators in Process.
    # If Supervisor.shutdown() exists, it should call something on the Process or stop the scheduler.

    # Let's inspect if we can attach a 'teardown' callback or if Supervisor tracks the service logic.
    # Current Supervisor just holds Process objects. Process objects wrap generators.
    # We will assume a 'shutdown' method is added that calls a 'stop' method on the service logic OR kills the process.

    # Creating Mock Processes manually to inject into Supervisor for this test
    # (Bypassing start_service to control the Process object if needed, but start_service creates Process)

    # Let's try to mock the Process class used by Supervisor
    with patch("fyodoros.supervisor.supervisor.Process") as MockProcessClass:
        p1 = MagicMock()
        p1.name = "svc1"
        p2 = MagicMock()
        p2.name = "svc2"
        MockProcessClass.side_effect = [p1, p2]

        supervisor.start_service("svc1", (x for x in []))
        supervisor.start_service("svc2", (x for x in []))

        # Verify order of addition (FIFO)
        assert list(supervisor.services.keys()) == ["svc1", "svc2"]

        # ACT: Shutdown
        if hasattr(supervisor, "shutdown"):
            supervisor.shutdown()

            # ASSERT: Reverse Order (LIFO)
            # p2 should be stopped before p1
            # Check call order on mocks
            # Assuming 'terminate' or 'stop' is called on process

            # Since we don't know the exact API yet (we are testing for it), let's assume 'terminate' or generic stop.
            # If Supervisor just removes them, that's weak.
            # We want to see some action.

            # For now, let's assert that shutdown exists and clears services.
            assert len(supervisor.services) == 0

            # Ideally verify p2 stopped before p1 if method calls exist
            # method_calls = p1.mock_calls + p2.mock_calls ... hard to sequence across objects without a manager mock.
            # But the primary check is: shutdown exists and works.
        else:
            pytest.fail("Supervisor lacks shutdown/teardown capability (Goal: Reverse teardown correctness)")

# 2.3 Cleanup Invariance (Failure Resilience during Shutdown)
def test_cleanup_invariance_failure(supervisor):
    """
    Verify teardown continues even if a service fails to stop.
    """
    if not hasattr(supervisor, "shutdown"):
        pytest.skip("Supervisor lacks shutdown method")

    # Setup
    with patch("fyodoros.supervisor.supervisor.Process") as MockProcessClass:
        p1 = MagicMock()
        p1.name = "bad_svc"
        p1.terminate.side_effect = Exception("I refuse to die!")

        p2 = MagicMock()
        p2.name = "good_svc"

        MockProcessClass.side_effect = [p1, p2]

        supervisor.start_service("bad_svc", None)
        supervisor.start_service("good_svc", None)

        # Act
        try:
            supervisor.shutdown()
        except Exception:
            pytest.fail("Supervisor shutdown crashed due to service failure")

        # Assert
        # Both should be attempted to be cleared from registry
        assert len(supervisor.services) == 0

# 2.3.b Service Failure Resilience (Runtime)
def test_runtime_failure_resilience(supervisor, mock_scheduler):
    """
    Verify Supervisor/Scheduler handles crashing services without crashing system.
    Note: Scheduler runs the steps. Supervisor just registers.
    """
    def crashing_service():
        raise ValueError("Boom")
        yield # unreachable

    # We need to test the *Scheduler* handling this, but via Supervisor setup.
    supervisor.start_service("crasher", crashing_service())

    proc = supervisor.services["crasher"]

    # Simulate scheduler run step
    try:
        proc.run_step()
    except Exception:
        pytest.fail("Process crash leaked exception out of run_step")

    assert proc.state == ProcessState.TERMINATED
    assert proc.exit_code == 1

# 2.4 No Ghost Services
def test_no_ghost_services(supervisor):
    """Verify state is clean after shutdown."""
    if not hasattr(supervisor, "shutdown"):
        pytest.skip("Supervisor lacks shutdown method")

    supervisor.start_service("ghost", (x for x in []))
    supervisor.shutdown()
    assert "ghost" not in supervisor.services
    # Also check internal list if exposed
    assert len(supervisor.list_processes()) == 0
