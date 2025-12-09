
import pytest
from unittest.mock import MagicMock
from fyodoros.servicemanager.servicemanager import ServiceManager
from fyodoros.kernel.process import Process
from fyodoros.kernel.scheduler import Scheduler

# Mock generator function for services
def mock_service_gen():
    yield

class TestServiceManagerShutdown:

    @pytest.fixture
    def scheduler(self):
        return Scheduler()

    @pytest.fixture
    def syscall_handler(self):
        return MagicMock()

    @pytest.fixture
    def service_manager(self, scheduler, syscall_handler):
        return ServiceManager(scheduler, syscall_handler)

    def test_shutdown_cleans_up_even_if_kill_fails(self, service_manager, scheduler, syscall_handler):
        # Setup: Create a service
        service_manager.start_service("test_svc", mock_service_gen())
        proc = service_manager.services["test_svc"]

        # Verify setup
        assert "test_svc" in service_manager.services
        assert proc in scheduler.processes

        # Mock sys_kill to raise an exception
        syscall_handler.sys_kill.side_effect = Exception("Kill failed")

        # Execute shutdown
        service_manager.shutdown()

        # Verify:
        # 1. sys_kill was called
        syscall_handler.sys_kill.assert_called_with(proc.pid)

        # 2. Service is removed from scheduler (crucial requirement)
        assert proc not in scheduler.processes

        # 3. ServiceManager internal state is cleared
        assert len(service_manager.services) == 0
        assert len(service_manager.all_processes) == 0

    def test_shutdown_no_stale_scheduler_entries(self, service_manager, scheduler, syscall_handler):
        # Setup: Start multiple services
        service_manager.start_service("svc1", mock_service_gen())
        service_manager.start_service("svc2", mock_service_gen())

        assert len(scheduler.processes) == 2

        # Execute shutdown
        service_manager.shutdown()

        # Verify scheduler is empty
        assert len(scheduler.processes) == 0
        assert len(service_manager.services) == 0

    def test_shutdown_idempotency(self, service_manager, scheduler):
        # Setup: Start a service
        service_manager.start_service("svc1", mock_service_gen())

        # First shutdown
        service_manager.shutdown()
        assert len(scheduler.processes) == 0
        assert len(service_manager.services) == 0

        # Second shutdown
        try:
            service_manager.shutdown()
        except Exception as e:
            pytest.fail(f"Second shutdown call raised exception: {e}")

        # State remains clean
        assert len(scheduler.processes) == 0
        assert len(service_manager.services) == 0
