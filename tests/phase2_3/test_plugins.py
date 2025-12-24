import pytest
from unittest.mock import MagicMock, patch
from loop.kernel.plugin_loader import PluginLoader
from loop.plugins.registry import PluginRegistry

class MockPlugin:
    def setup(self, kernel):
        self.kernel = kernel
        self.active = True

    def get_shell_commands(self):
        return {"foo": lambda: "bar"}

    def get_agent_tools(self):
        return []

    def teardown(self):
        self.active = False

    def on_shutdown(self):
        self.teardown()

@pytest.fixture
def kernel_mock():
    return MagicMock()

@pytest.fixture
def loader(kernel_mock):
    # Mock registry to avoid file I/O
    with patch("loop.kernel.plugin_loader.PluginRegistry") as MockReg:
        reg_instance = MockReg.return_value
        reg_instance.list_plugins.return_value = ["mock_plugin"]
        pl = PluginLoader(kernel_mock)
        return pl

# 5.1 Initialize
def test_plugin_initialize(loader):
    """Verify plugins are loaded and setup() is called."""
    with patch("importlib.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_inst = MockPlugin()
        mock_mod.Plugin.return_value = mock_inst
        mock_import.return_value = mock_mod

        loader.load_active_plugins()

        assert "mock_plugin" in loader.loaded_plugins
        assert mock_inst.kernel == loader.kernel

# 5.2 Execute
def test_plugin_execute(loader):
    """Verify plugin commands are registered."""
    with patch("importlib.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_inst = MockPlugin()
        mock_mod.Plugin.return_value = mock_inst
        mock_import.return_value = mock_mod

        loader.load_active_plugins()

        cmds = loader.get_all_shell_commands()
        assert "foo" in cmds
        assert cmds["foo"]() == "bar"

# 5.3 Teardown
def test_plugin_teardown(loader):
    """Verify plugins can be torn down safely."""
    with patch("importlib.import_module") as mock_import:
        mock_mod = MagicMock()
        mock_inst = MockPlugin()
        mock_mod.Plugin.return_value = mock_inst
        mock_import.return_value = mock_mod

        loader.load_active_plugins()

        # Act
        if hasattr(loader, "teardown"):
            loader.teardown()
            assert mock_inst.active is False
        else:
            pytest.fail("PluginLoader lacks teardown method")

# 5.4 Resilience
def test_plugin_resilience(loader):
    """Verify failure in one plugin doesn't stop others."""
    with patch("importlib.import_module") as mock_import:
        # Plugin 1 fails
        p1 = MagicMock()
        p1.Plugin.side_effect = Exception("Setup failed")

        # Plugin 2 succeeds
        p2 = MagicMock()
        p2_inst = MockPlugin()
        p2.Plugin.return_value = p2_inst

        # Simulate import_module calls
        def side_effect(name):
            if name == "bad": return p1
            if name == "good": return p2
            raise ImportError

        mock_import.side_effect = side_effect

        loader.registry.list_plugins.return_value = ["bad", "good"]

        loader.load_active_plugins()

        assert "good" in loader.loaded_plugins
        assert "bad" not in loader.loaded_plugins
