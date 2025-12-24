import pytest
import shutil
import uuid
import os
import sys
import psutil
from unittest.mock import MagicMock

# Allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tests.cleanup import cleanup_manager, master_cleanup, verify_clean_state

# --- Hooks ---

def pytest_configure(config):
    """Setup before test session"""
    print("\n🧹 Pre-test cleanup...")
    master_cleanup(aggressive=True)
    print("✅ System ready for testing\n")

def pytest_unconfigure(config):
    """Cleanup after test session"""
    print("\n🧹 Post-test cleanup...")
    success = master_cleanup(aggressive=False)
    verify_clean_state()
    if not success:
        print("⚠️  Some cleanup steps failed - manual intervention may be required")

# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def test_cleanup():
    """Auto-cleanup after each test"""
    yield
    # Cleanup after test
    cleanup_manager.cleanup_all()

@pytest.fixture(scope="session", autouse=True)
def session_cleanup():
    """Cleanup at end of session"""
    yield
    print("\n🧹 Final session cleanup...")
    master_cleanup(aggressive=True)

@pytest.fixture(scope="function")
def isolated_filesystem(tmp_path):
    """Provides isolated filesystem, guarantees cleanup"""
    test_dir = tmp_path / "test_fs"
    test_dir.mkdir()

    # Register for cleanup
    cleanup_manager.register_artifact(
        artifact_type="directory",
        identifier=str(test_dir),
        cleanup_fn=lambda: shutil.rmtree(test_dir, ignore_errors=True)
    )

    yield test_dir

    # Explicit cleanup in fixture teardown
    try:
        shutil.rmtree(test_dir)
    except Exception as e:
        print(f"Warning: Failed to cleanup {test_dir}: {e}")

@pytest.fixture(scope="function")
def test_processes():
    """Tracks spawned processes, kills them on teardown"""
    processes = []

    def spawn(popen_obj):
        """
        Registers a subprocess.Popen object (or similar with pid attribute) for cleanup.
        Returns the object.
        """
        processes.append(popen_obj)
        # Register individual cleanup
        cleanup_manager.register_artifact(
            artifact_type="process",
            identifier=f"pid:{popen_obj.pid}",
            cleanup_fn=lambda: _kill_proc(popen_obj)
        )
        return popen_obj

    def _kill_proc(proc):
        try:
            if hasattr(proc, 'kill'):
                proc.kill()
            elif hasattr(proc, 'terminate'):
                proc.terminate()
        except:
            pass

    yield spawn

    # Fixture teardown: kill all spawned processes
    for proc in processes:
        _kill_proc(proc)

@pytest.fixture(scope="function")
def test_user():
    """Creates temporary user, removes on teardown"""
    from loop.kernel.users import UserManager

    username = f"test_user_{uuid.uuid4().hex[:8]}"
    um = UserManager()

    # Best effort user creation
    try:
        if "root" not in um.users:
             um.users["root"] = {"password": "mock", "roles": ["admin"]}

        um.add_user(username, "test_password", requestor="root")
    except Exception:
        pass

    cleanup_manager.register_artifact(
        artifact_type="user",
        identifier=username,
        cleanup_fn=lambda: UserManager().delete_user(username, requestor="root")
    )

    yield username

    # Cleanup
    try:
        UserManager().delete_user(username, requestor="root")
    except:
        pass
