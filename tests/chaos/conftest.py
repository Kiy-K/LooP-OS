import pytest
import os
import shutil
import json
import time
import uuid
import sys
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from loop.kernel.kernel import Kernel
from loop.kernel.users import UserManager
from loop.kernel.scheduler import Scheduler
from loop.kernel.network import NetworkManager
from loop.kernel.syscalls import SyscallHandler
from loop.kernel.sandbox import AgentSandbox
from loop.servicemanager.servicemanager import ServiceManager

# Constants
SANDBOX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sandbox'))
REPORT_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chaos_report.json'))
REPORT_HTML_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'chaos_report.html'))

@pytest.fixture(scope="session", autouse=True)
def cleanup_sandbox():
    """Ensure sandbox is clean before and after tests."""
    if os.path.exists(SANDBOX_ROOT):
        shutil.rmtree(SANDBOX_ROOT)
    os.makedirs(SANDBOX_ROOT)
    yield
    # Cleanup after session
    if os.path.exists(SANDBOX_ROOT):
        shutil.rmtree(SANDBOX_ROOT)

@pytest.fixture
def mock_fs_root():
    """Provides a root directory for file operations."""
    return SANDBOX_ROOT

@pytest.fixture
def kernel(mock_fs_root):
    """
    Initializes a Kernel instance with isolated components.
    """
    # 1. Setup isolated UserManager
    user_manager = UserManager()
    # Mock _save and _load to avoid writing to real users.json
    user_manager._save = MagicMock()
    user_manager._load = MagicMock()
    user_manager.users = {"root": {"password": "mock_hash", "roles": ["admin"]}}

    # Populate with synthetic users
    for i in range(100):
        # We manually update the dictionary since we mocked save/load
        user_name = f"user_{i}"
        user_manager.users[user_name] = {"password": "mock_hash", "roles": ["user"]}

        if i % 10 == 0:
            # Grant admin role to simulate permission granting
            user_manager.users[user_name]["roles"].append("admin")

    # 2. Setup Scheduler
    scheduler = Scheduler()

    # 3. Setup NetworkManager (mocked for safety)
    network_manager = NetworkManager(user_manager)
    network_manager._save_state = MagicMock()
    network_manager._load_state = MagicMock(return_value={"enabled": True})

    # 4. SyscallHandler
    syscall_handler = SyscallHandler(scheduler, user_manager, network_manager)

    # 5. AgentSandbox (Pointing to our test dir)
    sandbox = AgentSandbox(syscall_handler)
    # Monkeypatch sandbox root to be our test dir
    sandbox.root_path = mock_fs_root
    syscall_handler.set_sandbox(sandbox)

    # 6. ServiceManager
    service_manager = ServiceManager(scheduler, syscall_handler)

    # 7. Kernel
    kernel_instance = Kernel(
        scheduler=scheduler,
        user_manager=user_manager,
        network_manager=network_manager,
        syscall_handler=syscall_handler,
        sandbox=sandbox,
        service_manager=service_manager
    )

    # Populate synthetic files in sandbox
    for i in range(100):
        fname = os.path.join(mock_fs_root, f"file_{i}.txt")
        with open(fname, "w") as f:
            f.write(f"Content of file {i}")

    return kernel_instance

# --- Reporting Infrastructure ---

class ChaosReport:
    def __init__(self):
        self.data = {
            "test_run_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "os": "LooP (Simulated)",
                "python_version": sys.version.split()[0],
            },
            "results": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration_seconds": 0
            },
            "failures": []
        }
        self.start_time = time.time()

    def add_result(self, nodeid, outcome, duration, error=None):
        self.data["results"]["total_tests"] += 1
        if outcome == "passed":
            self.data["results"]["passed"] += 1
        elif outcome == "failed":
            self.data["results"]["failed"] += 1
            self.data["failures"].append({
                "test": nodeid,
                "error": str(error) if error else "Unknown failure",
                "duration": duration
            })
        elif outcome == "skipped":
            self.data["results"]["skipped"] += 1

    def finalize(self):
        self.data["results"]["duration_seconds"] = time.time() - self.start_time

        # Write JSON
        with open(REPORT_JSON_PATH, "w") as f:
            json.dump(self.data, f, indent=2)

        # Write HTML
        self._write_html()

    def _write_html(self):
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LooP Chaos Test Report</title>
            <style>
                body {{ font-family: sans-serif; margin: 20px; }}
                .summary {{ background: #f0f0f0; padding: 10px; border-radius: 5px; }}
                .passed {{ color: green; }}
                .failed {{ color: red; }}
                .failure-box {{ border: 1px solid red; padding: 10px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h1>LooP Chaos Test Report</h1>
            <div class="summary">
                <p><strong>Run ID:</strong> {self.data['test_run_id']}</p>
                <p><strong>Timestamp:</strong> {self.data['timestamp']}</p>
                <p><strong>Total Tests:</strong> {self.data['results']['total_tests']}</p>
                <p><strong>Passed:</strong> <span class="passed">{self.data['results']['passed']}</span></p>
                <p><strong>Failed:</strong> <span class="failed">{self.data['results']['failed']}</span></p>
                <p><strong>Duration:</strong> {self.data['results']['duration_seconds']:.2f}s</p>
            </div>

            <h2>Failures</h2>
            {'<p>No failures.</p>' if not self.data['failures'] else ''}
            {''.join([
                f'<div class="failure-box"><h3>{f["test"]}</h3><pre>{f["error"]}</pre></div>'
                for f in self.data['failures']
            ])}
        </body>
        </html>
        """
        with open(REPORT_HTML_PATH, "w") as f:
            f.write(html_content)

# Global report instance
_report = ChaosReport()

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == 'call':
        error_msg = None
        if report.failed:
            # Try to get failure info
            if report.longrepr:
                error_msg = str(report.longrepr)

        _report.add_result(item.nodeid, report.outcome, report.duration, error_msg)

def pytest_sessionfinish(session, exitstatus):
    """Generate final report."""
    _report.finalize()
    print(f"\n[ChaosReport] JSON Report: {REPORT_JSON_PATH}")
    print(f"[ChaosReport] HTML Report: {REPORT_HTML_PATH}")
