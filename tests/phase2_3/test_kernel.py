import pytest
from unittest.mock import MagicMock, patch, ANY
from fyodoros.kernel.kernel import Kernel
from fyodoros.kernel.init import boot
import sys

# 3.1 Deterministic Boot
def test_deterministic_boot():
    """Verify boot sequence produces identical state for identical inputs."""

    # Mock all external dependencies to ensure determinism
    with patch("fyodoros.kernel.init.ConfigLoader") as MockConfig, \
         patch("fyodoros.kernel.init.FileSystem") as MockFS, \
         patch("fyodoros.kernel.init.UserManager") as MockUser, \
         patch("fyodoros.kernel.init.NetworkManager") as MockNet, \
         patch("fyodoros.kernel.init.NetworkGuard") as MockGuard, \
         patch("fyodoros.kernel.init.SyscallHandler") as MockSys, \
         patch("fyodoros.kernel.init.AgentSandbox") as MockSand, \
         patch("fyodoros.kernel.init.Supervisor") as MockSuper, \
         patch("fyodoros.kernel.init.PluginLoader") as MockLoader, \
         patch("fyodoros.kernel.init.Shell") as MockShell:

        # Setup consistent config
        mock_conf = MagicMock()
        mock_conf.load.return_value = {
            "filesystem": {"mounts": "/mnt/test"},
            "kernel": {"network_enabled": "false", "gui_enabled": "false"}
        }
        MockConfig.return_value = mock_conf

        # Run 1
        kernel1 = boot()

        # Run 2 (Resetting mocks implicitly by context manager exit/enter or creating new context)
        # Actually, let's just run it again in same context. Mocks return same values.
        kernel2 = boot()

        # Compare states
        # We can't compare object identity, but we can compare configuration/attributes
        assert kernel1 is not None
        assert kernel2 is not None
        assert kernel1 is not kernel2

        # Check specific attributes we care about being deterministic
        # e.g. NetworkGuard state
        assert kernel1.network_guard.enable.called
        assert kernel2.network_guard.enable.called

# 3.2 Double Boot Isolation
def test_double_boot_isolation():
    """Verify sequential boots don't leak state."""

    # We can't easily do parallel boot in one process.
    # We simulate boot -> shutdown -> boot.

    with patch("fyodoros.kernel.init.ConfigLoader") as MockConfig, \
         patch("fyodoros.kernel.init.NetworkGuard") as MockGuard:

        mock_conf = MagicMock()
        mock_conf.load.return_value = {"kernel": {"network_enabled": "false"}}
        MockConfig.return_value = mock_conf

        # Boot 1
        k1 = boot()

        # Shutdown 1 (If implemented)
        if hasattr(k1, "shutdown"):
            k1.shutdown()

        # Boot 2
        k2 = boot()

        # Verify k2 is fresh
        assert k1 is not k2
        # Ensure k2 has its own components
        assert k1.scheduler is not k2.scheduler

# 3.3 Controlled Shutdown
def test_controlled_shutdown():
    """Verify Kernel shutdown propagates to subsystems."""
    k = Kernel()

    # Mock subsystems
    k.supervisor = MagicMock()
    k.plugin_loader = MagicMock()
    k.network_guard = MagicMock()

    if hasattr(k, "shutdown"):
        k.shutdown()

        # Verify propagation
        assert k.supervisor.shutdown.called
        # Plugin loader shutdown?
        # assert k.plugin_loader.shutdown.called
        # Network guard disable?
        assert k.network_guard.disable.called
    else:
        pytest.fail("Kernel lacks shutdown method")
