
import pytest
import time
from unittest.mock import MagicMock
from loop.servicemanager.servicemanager import ServiceManager, ServiceMetadata
from loop.servicemanager.types import ServiceType, ShutdownState
from loop.kernel.scheduler import Scheduler
from loop.kernel.process import Process

def mock_gen():
    yield

class TestComprehensiveServiceManager:

    @pytest.fixture
    def setup(self):
        scheduler = Scheduler()
        syscall = MagicMock()
        sm = ServiceManager(scheduler, syscall)
        return sm, scheduler, syscall

    def test_dependency_ordering(self, setup):
        sm, _, _ = setup

        # A depends on B
        # B depends on C
        # Start in random order
        sm.start_service("A", mock_gen(), depends_on=["B"])
        sm.start_service("C", mock_gen())
        sm.start_service("B", mock_gen(), depends_on=["C"])

        # Check shutdown order (should be A -> B -> C)
        order = sm._get_shutdown_order()
        assert order == ["A", "B", "C"]

    def test_cycle_detection_fallback(self, setup):
        sm, _, _ = setup

        # A depends on B
        # B depends on A
        sm.start_service("A", mock_gen(), depends_on=["B"])
        sm.start_service("B", mock_gen(), depends_on=["A"])

        # Should not crash, but fallback to LIFO
        order = sm._get_shutdown_order()
        assert len(order) == 2
        assert "A" in order
        assert "B" in order

    def test_service_metadata_storage(self, setup):
        sm, _, _ = setup
        meta = ServiceMetadata(
            name="test",
            type=ServiceType.PLUGIN,
            graceful_timeout=1.0
        )
        sm.start_service("test", mock_gen(), metadata=meta)

        assert "test" in sm.metadata
        assert sm.metadata["test"].type == ServiceType.PLUGIN
        assert sm.metadata["test"].graceful_timeout == 1.0

    def test_robust_shutdown_report(self, setup):
        sm, scheduler, syscall = setup

        # Mock syscall kill to work
        syscall.sys_kill.return_value = True

        sm.start_service("svc1", mock_gen())
        sm.start_service("svc2", mock_gen())

        report = sm.shutdown(timeout=1.0, grace_period=0.1)

        assert report.success == ["svc2", "svc1"] # LIFO if no deps
        assert len(report.failed) == 0
        assert sm.shutdown_state == ShutdownState.COMPLETE
        assert len(sm.services) == 0

    def test_force_shutdown_timeout(self, setup):
        sm, scheduler, syscall = setup

        # Mock sys_kill to hang for 2 seconds
        def slow_kill(pid):
            time.sleep(2)
            return True
        syscall.sys_kill.side_effect = slow_kill

        # Set small timeout
        meta = ServiceMetadata(name="slow_svc", type=ServiceType.EXTERNAL, graceful_timeout=0.1, force_timeout=0.1)
        sm.start_service("slow_svc", mock_gen(), metadata=meta)

        # Shutdown with 1s global timeout
        start = time.time()
        report = sm.shutdown(timeout=1.0, grace_period=0, force=True)

        # Should finish ~0.1s (force timeout) not 2s
        duration = time.time() - start
        assert duration < 1.0

        # But wait, my implementation of `_stop_service_single` uses `_threaded_timeout_exec`.
        # If the thread hangs, we return False (timeout).
        # We don't mark it as "failed" in terms of exception, but we print "Timeout killing".
        # The shutdown continues.

        # Verify it handled it gracefully
        assert sm.shutdown_state == ShutdownState.COMPLETE

    def test_shutdown_state_machine(self, setup):
        sm, _, _ = setup
        assert sm.shutdown_state == ShutdownState.NOT_STARTED
        sm.shutdown(grace_period=0)
        assert sm.shutdown_state == ShutdownState.COMPLETE
