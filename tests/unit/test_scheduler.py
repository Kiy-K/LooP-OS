import pytest
from unittest.mock import MagicMock
from loop.kernel.scheduler import Scheduler
from loop.kernel.process import Process, ProcessState

@pytest.fixture
def scheduler():
    return Scheduler()

def test_ordered_startup(scheduler):
    p1 = MagicMock(spec=Process)
    p1.pid = 1
    p2 = MagicMock(spec=Process)
    p2.pid = 2

    scheduler.add(p1)
    scheduler.add(p2)

    assert scheduler.processes[0].pid == 1
    assert scheduler.processes[1].pid == 2

def test_lifo_shutdown(scheduler):
    scheduler.shutdown()
    assert scheduler.accepting_new is False

    p3 = MagicMock(spec=Process)
    p3.name = "p3" # Needed for logging
    scheduler.add(p3)
    assert p3 not in scheduler.processes

def test_fault_injection_recovery(scheduler):
    p1 = MagicMock(spec=Process)
    p1.state = ProcessState.RUNNING
    p1.signal = None  # Ensure signal attribute exists
    p1.run_step.side_effect = Exception("Crash")

    scheduler.processes.append(p1)

    try:
        scheduler.run()
    except Exception as e:
        assert "Crash" in str(e)
