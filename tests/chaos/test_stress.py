import pytest
import time
import threading
from tests.chaos.utils import Stress
from loop.kernel.process import Process

def dummy_process():
    while True:
        yield

class TestStress:
    """
    Stress Testing Category.
    Goal: Push system to limits and beyond.
    """

    def test_memory_exhaustion(self, kernel):
        """
        Test: Memory Exhaustion
        """
        chunks = []
        try:
            for _ in range(10):
                chunks.append(Stress.consume_memory(10))
        except MemoryError:
            pytest.fail("System crashed under memory pressure")

        assert kernel.sys.sys_net_status() in ["active", "inactive"]

    def test_fd_leak(self, kernel):
        """
        Test: File Descriptor Leak
        """
        files = []
        try:
            for i in range(200):
                kernel.sys.sys_write(f"/file_leak_{i}.txt", "data")

        except OSError:
            pytest.fail("OS Error during FD stress test")

        pass

    def test_cpu_saturation(self, kernel):
        """
        Test: CPU Saturation
        """
        stop_event = threading.Event()

        def burner():
            while not stop_event.is_set():
                _ = 2 ** 100

        t = threading.Thread(target=burner)
        t.start()

        try:
            start = time.time()
            kernel.sys.sys_proc_list()
            latency = time.time() - start
            assert latency < 0.5

        finally:
            stop_event.set()
            t.join()

    def test_process_limit(self, kernel):
        """
        Test: Process Bomb
        Goal: Spawn many processes via Scheduler.
        """
        initial_count = len(kernel.scheduler.processes)

        for i in range(100):
            p = Process(name=f"bomb_{i}", target=dummy_process(), uid="root")
            kernel.scheduler.add(p)

        assert len(kernel.scheduler.processes) == initial_count + 100

        # Verify scheduler can still tick (if it had a tick method) or list them
        assert len(kernel.sys.sys_proc_list()) >= 100
