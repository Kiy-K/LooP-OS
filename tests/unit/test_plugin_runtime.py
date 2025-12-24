import pytest
from unittest.mock import MagicMock, patch
from loop.kernel.plugin_loader import PluginLoader

@pytest.fixture
def plugin_loader():
    kernel_mock = MagicMock()
    return PluginLoader(kernel_mock)

def test_plugin_activate(plugin_loader):
    with patch("importlib.import_module") as mock_import:
        mock_plugin_cls = MagicMock()
        mock_module = MagicMock()
        mock_module.Plugin = mock_plugin_cls
        mock_import.return_value = mock_module

        plugin_loader._load_plugin("test_plugin")

        assert "test_plugin" in plugin_loader.loaded_plugins
        mock_plugin_cls.return_value.setup.assert_called_once()

def test_plugin_execute_stub(plugin_loader):
    mock_plugin = MagicMock()
    mock_plugin.get_shell_commands.return_value = {"cmd": lambda: "ok"}
    plugin_loader.loaded_plugins["test"] = mock_plugin

    cmds = plugin_loader.get_all_shell_commands()
    assert "cmd" in cmds
    assert cmds["cmd"]() == "ok"

def test_plugin_teardown(plugin_loader):
    mock_plugin = MagicMock()
    plugin_loader.loaded_plugins["test"] = mock_plugin

    plugin_loader.teardown()

    mock_plugin.on_shutdown.assert_called_once()
    assert len(plugin_loader.loaded_plugins) == 0
