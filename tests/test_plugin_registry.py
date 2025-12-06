import pytest
import json
import shutil
from pathlib import Path
from fyodoros.plugins.registry import PluginRegistry

# Fixture to provide a registry with a temporary config directory
@pytest.fixture
def registry(tmp_path):
    # Override the config path for the registry instance
    # Since PluginRegistry sets path in __init__, we might need to subclass or patch it.
    # But wait, looking at registry.py code:
    # self.config_dir = Path.home() / ".fyodor" / "plugins"
    # It's hardcoded. Ideally we should be able to pass it.
    # For testing without changing source code too much, we can patch `Path.home`
    # or subclass. Let's try subclassing for the test.

    class TestRegistry(PluginRegistry):
        def __init__(self, config_path):
            self.config_dir = config_path / ".fyodor" / "plugins"
            self.config_file = self.config_dir / "config.json"
            self.enabled_plugins = set()
            self._load()

    return TestRegistry(tmp_path)

def test_activate_deactivate(registry):
    # Initial state
    assert not registry.is_active("my_plugin")

    # Activate
    assert registry.activate("my_plugin") is True
    assert registry.is_active("my_plugin") is True

    # Activate again (should return False as already active)
    assert registry.activate("my_plugin") is False
    assert registry.is_active("my_plugin") is True

    # Deactivate
    assert registry.deactivate("my_plugin") is True
    assert registry.is_active("my_plugin") is False

    # Deactivate again
    assert registry.deactivate("my_plugin") is False

def test_list_plugins(registry):
    assert registry.list_plugins() == []

    registry.activate("plugin_a")
    registry.activate("plugin_b")

    plugins = registry.list_plugins()
    assert len(plugins) == 2
    assert "plugin_a" in plugins
    assert "plugin_b" in plugins

def test_config_persistence(registry, tmp_path):
    # Activate a plugin
    registry.activate("persistent_plugin")

    # Verify file exists
    config_file = tmp_path / ".fyodor" / "plugins" / "config.json"
    assert config_file.exists()

    with open(config_file, "r") as f:
        data = json.load(f)
        assert "persistent_plugin" in data["enabled"]

    # Create a NEW registry instance pointing to the same path
    class TestRegistry(PluginRegistry):
        def __init__(self, config_path):
            self.config_dir = config_path / ".fyodor" / "plugins"
            self.config_file = self.config_dir / "config.json"
            self.enabled_plugins = set()
            self._load()

    new_registry = TestRegistry(tmp_path)
    assert new_registry.is_active("persistent_plugin")

def test_edge_cases(registry):
    # Empty string name (technically valid in set, but let's see)
    registry.activate("")
    assert registry.is_active("")

    # Deactivating non-existent
    assert registry.deactivate("ghost_plugin") is False

    # Check robustness against manual file corruption
    # (We can't easily test this without mocking open() raising exception inside _load)
    pass
