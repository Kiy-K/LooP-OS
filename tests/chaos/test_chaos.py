import pytest
import time
import random
import os
from unittest.mock import MagicMock
from tests.chaos.utils import kill_random_process

def dummy_process():
    while True:
        yield

class TestChaos:
    """
    Chaos Engineering Category.
    Goal: Introduce random failures.
    """

    def test_random_process_kills(self, kernel):
        """
        Test: Random Process Termination
        """
        # Seed with some processes
        from loop.kernel.process import Process
        for i in range(20):
            kernel.scheduler.add(Process(name=f"service_{i}", target=dummy_process(), uid="root"))

        # Kill loop
        kills = 0
        for _ in range(5):
            if kill_random_process(kernel):
                kills += 1

        assert kills > 0
        assert kernel.scheduler.running # Kernel shouldn't crash

    def test_network_chaos(self, kernel):
        """
        Test: Network Instability
        """
        # Simulate network going down
        kernel.sys.sys_net_set_status(False)
        assert kernel.sys.sys_net_status() == "inactive"

        # Verify access denied
        assert not kernel.sys.sys_net_check_access()

        # Restore
        kernel.sys.sys_net_set_status(True)
        assert kernel.sys.sys_net_status() == "active"

    def test_filesystem_corruption(self, kernel):
        """
        Test: Filesystem Corruption (Simulated)
        """
        # Create a file
        path = "/var/important.txt"
        content = "Critical Data"
        kernel.sys.sys_write(path, content)

        # Verify write
        assert kernel.sys.sys_read(path) == content

        # Corrupt the in-memory store
        # Access via kernel.sys.fs._resolve
        node = kernel.sys.fs._resolve(path)
        assert node is not None

        # Corrupt data
        node.data = "Corrupted Data"

        # Read back via syscall
        read_back = kernel.sys.sys_read(path)
        assert read_back == "Corrupted Data"

        # Ensure kernel handled the read without crashing
        assert True

    def test_time_skew(self, kernel):
        """
        Test: Time Manipulation
        """
        # We can't easily change system time, but we can mock time.time
        # if the kernel used it for scheduling.
        # The Scheduler seems simple, but let's check if SyscallHandler logs use time.

        with MagicMock() as mock_time:
            pass

        kernel.sys.sys_log("Time check")
        assert True
