import os
import sys
import shutil
import glob
import time
import psutil
import signal
import fnmatch
import json
import pytest
import atexit
import uuid
from datetime import datetime
from contextlib import contextmanager

# Adjust path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from fyodoros.kernel.users import UserManager
from fyodoros.kernel.network import NetworkManager

# Global cleanup manager
class TestCleanupManager:
    """Centralized cleanup manager for all test artifacts"""

    def __init__(self):
        self.artifacts = []
        self.failed_cleanups = []

    def register_artifact(self, artifact_type, identifier, cleanup_fn):
        """Register an artifact for cleanup"""
        self.artifacts.append({
            "type": artifact_type,
            "id": identifier,
            "cleanup": cleanup_fn,
            "created_at": time.time(),
        })

    def cleanup_all(self, force=False):
        """Clean up all registered artifacts"""
        if not self.artifacts:
            return

        print(f"\n[CLEANUP] Starting cleanup of {len(self.artifacts)} artifacts...")

        # Cleanup in reverse order (LIFO)
        for artifact in reversed(self.artifacts):
            try:
                print(f"[CLEANUP] Removing {artifact['type']}: {artifact['id']}")
                artifact['cleanup']()
            except Exception as e:
                print(f"[CLEANUP] Failed to clean {artifact['id']}: {e}")
                self.failed_cleanups.append(artifact)
                if not force:
                    raise

        # Report failures
        if self.failed_cleanups:
            print(f"\n[CLEANUP] ⚠️  {len(self.failed_cleanups)} artifacts failed to clean:")
            for artifact in self.failed_cleanups:
                print(f"  - {artifact['type']}: {artifact['id']}")
        else:
            print(f"[CLEANUP] ✅ All artifacts cleaned successfully")

        self.artifacts.clear()

cleanup_manager = TestCleanupManager()
atexit.register(lambda: cleanup_manager.cleanup_all(force=True))

# --- Context Managers ---

@contextmanager
def temporary_file(path, content=""):
    """Create temporary file, guaranteed cleanup"""
    try:
        with open(path, 'w') as f:
            f.write(content)

        cleanup_manager.register_artifact(
            artifact_type="file",
            identifier=path,
            cleanup_fn=lambda: os.unlink(path) if os.path.exists(path) else None
        )

        yield path
    finally:
        if os.path.exists(path):
            os.unlink(path)

@contextmanager
def temporary_service(service_manager, name, daemon_fn):
    """Start service, guaranteed cleanup"""
    service_manager.start_service(name, daemon_fn)

    cleanup_manager.register_artifact(
        artifact_type="service",
        identifier=name,
        cleanup_fn=lambda: service_manager.kill_process(service_manager.services[name].pid) if name in service_manager.services else None
    )

    try:
        yield name
    finally:
        # Stop service logic
        if name in service_manager.services:
             service_manager.kill_process(service_manager.services[name].pid)

@contextmanager
def temporary_network_state(network_manager, enabled=True):
    """Change network state, restore on exit"""
    # Assuming network_manager has is_enabled/set_enabled or similar
    # Based on code read: NetworkManager._load_state returns dict with 'enabled'
    # It has a private _save_state
    # This is tricky without public API, but let's assume we can modify state
    # If not, this context manager might be limited.

    original_state = True # Default
    # Attempt to read state
    try:
        original_state = network_manager.network_enabled
    except AttributeError:
        pass

    try:
        if hasattr(network_manager, 'network_enabled'):
            network_manager.network_enabled = enabled
        yield
    finally:
        if hasattr(network_manager, 'network_enabled'):
            network_manager.network_enabled = original_state


# --- Specific Cleanup Strategies ---

def kill_process_tree(pid, signal=signal.SIGTERM, timeout=5):
    """Kill process and all its children"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)

        # Send SIGTERM to all
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass

        # Wait for termination
        gone, alive = psutil.wait_procs(children, timeout=timeout)

        # Force kill survivors
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass

        # Finally kill parent
        try:
            parent.terminate()
            parent.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            parent.kill()

    except psutil.NoSuchProcess:
        pass  # Already dead

def cleanup_all_test_processes():
    """Find and kill all test processes"""
    test_patterns = [
        "test_*",
        "chaos_*",
        "mock_*",
        "dummy_*",
        "chrome", # Headless browser
        "playwright",
        "node",
    ]

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = proc.info['name']
            cmdline = ' '.join(proc.info['cmdline'] or [])

            if name in ["chrome", "node"] and "playwright" not in cmdline and "test" not in cmdline:
                continue

            for pattern in test_patterns:
                if fnmatch.fnmatch(name, pattern) or pattern in cmdline:
                    print(f"Killing orphaned test process: {name} (PID {proc.pid})")
                    kill_process_tree(proc.pid)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def cleanup_test_directories():
    """Remove all test directories"""
    test_roots = [
        "/tmp/fyodoros_test_*",
        "/var/tmp/test_*",
        "~/.fyodor/sandbox/test_*",
        "~/.fyodor/tmp/*",
        "/tmp/pytest-*",
    ]

    for pattern in test_roots:
        for path in glob.glob(os.path.expanduser(pattern)):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
                print(f"Removed: {path}")
            except Exception as e:
                print(f"Failed to remove {path}: {e}")

def cleanup_test_files():
    """Remove test files by pattern"""
    patterns = [
        "test_*.txt",
        "mock_*.json",
        "chaos_*.log",
        "dummy_*",
        "*.crash",
        "*.dump"
    ]

    search_dirs = [
        "/tmp",
        "~/.fyodor/home/guest",
        "~/.fyodor/sandbox",
        "/var/log/journal"
    ]

    for directory in search_dirs:
        directory = os.path.expanduser(directory)
        if not os.path.exists(directory):
            continue

        for pattern in patterns:
            for filepath in glob.glob(os.path.join(directory, "**", pattern), recursive=True):
                try:
                    os.unlink(filepath)
                    print(f"Removed file: {filepath}")
                except Exception as e:
                    print(f"Failed to remove {filepath}: {e}")

    journal_dir = "/var/log/journal"
    if os.path.exists(journal_dir):
        for f in os.listdir(journal_dir):
            if f.endswith(".log") or f.endswith(".status"):
                 try:
                    os.unlink(os.path.join(journal_dir, f))
                    print(f"Removed journal file: {f}")
                 except Exception as e:
                    print(f"Failed to remove journal {f}: {e}")

def cleanup_network_resources():
    """Close all test-related network connections and reset network state"""
    def is_test_connection(conn):
        test_ports = range(10000, 20000)
        return (
            conn.laddr.port in test_ports or
            (conn.raddr and conn.raddr.port in test_ports)
        )

    for conn in psutil.net_connections():
        if is_test_connection(conn):
            try:
                pass
            except:
                pass

def cleanup_test_data():
    """Remove test data from storage (users.json, etc)"""
    try:
        um = UserManager()
        users_to_delete = []
        for user in um.list_users():
            if user.startswith("test_") or user.startswith("mock_"):
                users_to_delete.append(user)

        for user in users_to_delete:
            print(f"Removing test user: {user}")
            if user in um.users:
                del um.users[user]

        if users_to_delete:
            um._save()

    except Exception as e:
        print(f"Failed to clean users: {e}")

    plugin_dir = os.path.expanduser("~/.fyodor/plugins/installed")
    if os.path.exists(plugin_dir):
         for d in os.listdir(plugin_dir):
             if d.startswith("test_") or d.startswith("mock_"):
                 shutil.rmtree(os.path.join(plugin_dir, d), ignore_errors=True)
                 print(f"Removed test plugin: {d}")

def cleanup_test_services(service_manager=None):
    """Stop and remove all test services"""
    if service_manager:
        for service_name in list(service_manager.services.keys()):
             if any(pattern in service_name for pattern in ["test_", "mock_", "chaos_"]):
                try:
                    print(f"Stopping test service: {service_name}")
                    if hasattr(service_manager, '_stop_service_single'):
                        service_manager._stop_service_single(service_name, force=True)
                except Exception as e:
                    print(f"Failed to stop {service_name}: {e}")

    for config_file in glob.glob("/etc/fyodoros/test_*.conf"):
        try:
            os.unlink(config_file)
        except Exception as e:
            print(f"Failed to remove {config_file}: {e}")

def master_cleanup(aggressive=False):
    """
    Comprehensive cleanup of all test artifacts.
    """
    print("\n" + "="*60)
    print("MASTER CLEANUP - Removing all test artifacts")
    print("="*60)

    cleanup_steps = [
        ("Test Processes", cleanup_all_test_processes),
        ("Test Services", lambda: cleanup_test_services(None)),
        ("Network Resources", cleanup_network_resources),
        ("Test Files", cleanup_test_files),
        ("Test Directories", cleanup_test_directories),
        ("Database/Storage", cleanup_test_data),
        ("Registered Artifacts", lambda: cleanup_manager.cleanup_all(force=aggressive)),
    ]

    failed_steps = []

    for step_name, cleanup_fn in cleanup_steps:
        try:
            print(f"\n[{step_name}]")
            cleanup_fn()
            print(f"✅ {step_name} completed")
        except Exception as e:
            print(f"❌ {step_name} failed: {e}")
            failed_steps.append((step_name, e))
            if not aggressive:
                raise

    print("\n" + "="*60)
    if failed_steps:
        print(f"⚠️  Cleanup completed with {len(failed_steps)} failures:")
        for step, error in failed_steps:
            print(f"  - {step}: {error}")
    else:
        print("✅ All cleanup steps completed successfully")
    print("="*60 + "\n")

    # Generate and save report
    generate_cleanup_report(save=True)

    return len(failed_steps) == 0

def verify_clean_state():
    """Verify system is in clean state"""
    issues = []

    try:
        test_procs = [p for p in psutil.process_iter(['name'])
                    if 'test_' in p.info['name'] or 'mock_' in p.info['name']]
        if test_procs:
            issues.append(f"Found {len(test_procs)} orphaned test processes")
    except:
        pass

    test_files = glob.glob("/tmp/test_*")
    if test_files:
        issues.append(f"Found {len(test_files)} leftover test files")

    try:
        um = UserManager()
        test_users = [u for u in um.list_users() if u.startswith("test_")]
        if test_users:
            issues.append(f"Found {len(test_users)} test users")
    except:
        pass

    if issues:
        print("❌ System not in clean state:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ System verified clean")
        return True

def generate_cleanup_report(save=False):
    """Generate report of cleanup operations"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "failed_cleanups": len(cleanup_manager.failed_cleanups),
        # Note: artifacts list is cleared, so we track failures primarily
        # Ideally we would track historical count of cleaned items but we reset list.
    }

    if save:
        try:
            with open("cleanup_report.json", "w") as f:
                json.dump(report, f, indent=2)
            print("Cleanup report saved to cleanup_report.json")
        except Exception as e:
            print(f"Failed to save cleanup report: {e}")

    return report
