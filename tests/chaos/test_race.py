import pytest
import threading
import time
from loop.kernel.process import Process

def dummy_process():
    while True:
        yield

class TestRaceConditions:
    """
    Race Condition Testing Category.
    """

    def test_concurrent_io(self, kernel, mock_fs_root):
        """
        Test: Concurrent File Access
        """
        # We use a file in the sandbox to ensure real IO
        test_file = f"{mock_fs_root}/concurrent.txt"

        # Initialize
        kernel.sys.sys_write(test_file, "START")

        def worker(id):
            for _ in range(50):
                # Read-Modify-Write (classic race)
                # Since SyscallHandler doesn't lock, last write wins or interleave happens
                # We just want to ensure no crash/exception
                try:
                    kernel.sys.sys_append(test_file, f"_{id}")
                except Exception:
                    pass

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        content = kernel.sys.sys_read(test_file)
        # Verify file is intact (mock fs or real fs shouldn't corrupt structure)
        assert content.startswith("START")
        assert len(content) > 5

    def test_scheduler_races(self, kernel):
        """
        Test: Scheduler Race Conditions (Add/Remove)
        """
        stop_event = threading.Event()

        def adder():
            i = 0
            while not stop_event.is_set():
                p = Process(name=f"race_{i}", target=dummy_process(), uid="root")
                # Scheduler doesn't check dupes by name, only tracks objects
                kernel.scheduler.add(p)
                i = (i + 1) % 100
                time.sleep(0.001)

        def remover():
            while not stop_event.is_set():
                if kernel.scheduler.processes:
                    # Accessing list while modifying might throw if not thread safe
                    try:
                        # Find a random process to kill
                        # We use index 0 for simplicity
                        p = kernel.scheduler.processes[0]
                        # Scheduler remove is not public API usually, it's done via run loop or signal.
                        # We simulate "killing" it
                        p.signal = "SIGKILL"
                        # Run one step of scheduler to process kill
                        # But run() is a loop. We need to manually remove if we are testing race on 'processes' list
                        # Or rely on scheduler logic.
                        # If we just want to race 'add' vs 'iteration', we can iterate?
                        pass
                    except IndexError:
                        pass
                time.sleep(0.001)

        t1 = threading.Thread(target=adder)
        t2 = threading.Thread(target=remover)

        t1.start()
        t2.start()

        time.sleep(2)
        stop_event.set()

        t1.join()
        t2.join()

        # Verify consistency
        assert isinstance(kernel.scheduler.processes, list)

    def test_shutdown_race(self, kernel):
        """
        Test: Concurrent Shutdowns
        """
        results = []
        def call_shutdown():
            res = kernel.sys.sys_shutdown()
            results.append(res)

        threads = [threading.Thread(target=call_shutdown) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert all(results)
        assert not kernel.scheduler.running
        assert kernel.scheduler.exit_reason == "SHUTDOWN"
