import pytest
from unittest.mock import Mock, patch
from fyodoros.kernel.scheduler import Scheduler
from fyodoros.kernel.process import Process, ProcessState

# Helper generator for processes
def dummy_process_target():
    yield
    yield
    return

@pytest.fixture
def scheduler():
    # Scheduler __init__ takes no arguments in the code I read
    s = Scheduler()
    return s

def test_add_process(scheduler):
    p = Process("test_proc", dummy_process_target(), "root")
    scheduler.add(p)
    assert p in scheduler.processes
    assert scheduler.processes[0].name == "test_proc"

def test_run_processes(scheduler):
    # Define a process that runs 2 steps then finishes
    steps_executed = 0
    def tracking_process():
        nonlocal steps_executed
        steps_executed += 1
        yield
        steps_executed += 1
        # StopIteration implicit

    p = Process("tracker", tracking_process(), "root")
    scheduler.add(p)

    # Manually run loop logic or trust run()?
    # run() is a loop while self.running is True.
    # To test it without infinite loop, we can make the process set running=False

    def stopper_process():
        scheduler.running = False
        yield

    p_stop = Process("stopper", stopper_process(), "root")
    scheduler.add(p_stop)

    # Run scheduler
    # tracker yields once (step 1). stopper sets running=False.
    # Scheduler loop breaks?
    # In one pass: tracker runs (yields), stopper runs (sets False).
    # Next check `while self.running` is False.

    scheduler.run()

    # Tracker should have run at least once
    assert steps_executed >= 1

def test_process_termination_signal(scheduler):
    p = Process("term_me", dummy_process_target(), "root")
    scheduler.add(p)

    # Signal SIGTERM
    p.deliver_signal("SIGTERM")

    # Scheduler loop should remove it
    # We need to run scheduler for one iteration
    # Hack: Inject a stopper process
    def stopper():
        scheduler.running = False
        yield

    scheduler.add(Process("stopper", stopper(), "root"))
    scheduler.run()

    assert p not in scheduler.processes
    assert p.state == ProcessState.TERMINATED

def test_scheduler_signals_kill(scheduler):
    p = Process("kill_me", dummy_process_target(), "root")
    scheduler.add(p)
    p.deliver_signal("SIGKILL")

    # Run one pass
    def stopper():
        scheduler.running = False
        yield
    scheduler.add(Process("stopper", stopper(), "root"))
    scheduler.run()

    assert p not in scheduler.processes
