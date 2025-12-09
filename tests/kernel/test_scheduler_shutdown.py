
import pytest
from fyodoros.kernel.scheduler import Scheduler
from fyodoros.kernel.process import Process

class TestSchedulerShutdown:

    def test_shutdown_rejects_new_processes(self):
        scheduler = Scheduler()
        proc = Process("test_proc", None)

        # Verify normal addition works
        scheduler.add(proc)
        assert len(scheduler.processes) == 1

        # Initiate shutdown
        scheduler.shutdown()
        assert scheduler.accepting_new is False

        # Attempt to add new process
        proc2 = Process("test_proc_2", None)
        scheduler.add(proc2)

        # Verify rejection
        assert len(scheduler.processes) == 1
        assert proc2 not in scheduler.processes
