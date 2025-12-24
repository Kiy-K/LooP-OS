#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

namespace py = pybind11;

/**
 * @brief Structure to hold plugin information.
 */
struct PluginInfo {
    std::string name;
    std::string type;
    bool active;
    std::map<std::string, std::string> settings;
};

/**
 * @brief C++ Backend for the Plugin Registry.
 *
 * Provides high-performance in-memory state management for plugins,
 * including activation status and configuration settings.
 */
class RegistryCore {
public:
    /**
     * @brief Initialize the RegistryCore.
     */
    RegistryCore() {}

    /**
     * @brief Register a plugin in the core.
     *
     * @param name The unique name of the plugin.
     * @param type The type of plugin (e.g., 'python', 'cpp', 'node').
     * @param active Initial activation status.
     */
    void add_plugin(const std::string& name, const std::string& type, bool active) {
        if (plugins.find(name) == plugins.end()) {
            plugins[name] = {name, type, active, {}};
        }
    }

    /**
     * @brief Set the activation status of a plugin.
     *
     * @param name The plugin name.
     * @param active True to activate, False to deactivate.
     */
    void set_active(const std::string& name, bool active) {
        if (plugins.find(name) != plugins.end()) {
            plugins[name].active = active;
        }
    }

    /**
     * @brief Check if a plugin is currently active.
     *
     * @param name The plugin name.
     * @return bool True if active.
     */
    bool is_active(const std::string& name) {
        if (plugins.find(name) != plugins.end()) {
            return plugins[name].active;
        }
        return false;
    }

    /**
     * @brief List all currently active plugins.
     *
     * @return std::vector<std::string> List of active plugin names.
     */
    std::vector<std::string> list_plugins() {
        std::vector<std::string> names;
        for (const auto& pair : plugins) {
            if (pair.second.active) {
                names.push_back(pair.first);
            }
        }
        return names;
    }

    /**
     * @brief List all known plugins (active or inactive).
     *
     * @return std::vector<std::string> List of all plugin names.
     */
    std::vector<std::string> list_all_plugins() {
        std::vector<std::string> names;
        for (const auto& pair : plugins) {
            names.push_back(pair.first);
        }
        return names;
    }

    /**
     * @brief Set a configuration setting for a plugin.
     *
     * @param name The plugin name.
     * @param key The setting key.
     * @param value The setting value.
     */
    void set_setting(const std::string& name, const std::string& key, const std::string& value) {
        if (plugins.find(name) != plugins.end()) {
            plugins[name].settings[key] = value;
        }
    }

    /**
     * @brief Retrieve a configuration setting for a plugin.
     *
     * @param name The plugin name.
     * @param key The setting key.
     * @return std::string The value, or empty string if not found.
     */
    std::string get_setting(const std::string& name, const std::string& key) {
        if (plugins.find(name) != plugins.end()) {
            if (plugins[name].settings.count(key)) {
                return plugins[name].settings[key];
            }
        }
        return "";
    }

private:
    std::map<std::string, PluginInfo> plugins;
};

PYBIND11_MODULE(registry_core, m) {
    py::class_<RegistryCore>(m, "RegistryCore")
        .def(py::init<>())
        .def("add_plugin", &RegistryCore::add_plugin)
        .def("set_active", &RegistryCore::set_active)
        .def("is_active", &RegistryCore::is_active)
        .def("list_plugins", &RegistryCore::list_plugins)
        .def("list_all_plugins", &RegistryCore::list_all_plugins)
        .def("set_setting", &RegistryCore::set_setting)
        .def("get_setting", &RegistryCore::get_setting);
}
