#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

namespace py = pybind11;

struct PluginInfo {
    std::string name;
    std::string type;
    bool active;
    std::map<std::string, std::string> settings;
};

class RegistryCore {
public:
    RegistryCore() {}

    void add_plugin(const std::string& name, const std::string& type, bool active) {
        if (plugins.find(name) == plugins.end()) {
            plugins[name] = {name, type, active, {}};
        }
    }

    void set_active(const std::string& name, bool active) {
        if (plugins.find(name) != plugins.end()) {
            plugins[name].active = active;
        }
    }

    bool is_active(const std::string& name) {
        if (plugins.find(name) != plugins.end()) {
            return plugins[name].active;
        }
        return false;
    }

    std::vector<std::string> list_plugins() {
        std::vector<std::string> names;
        for (const auto& pair : plugins) {
            if (pair.second.active) {
                names.push_back(pair.first);
            }
        }
        return names;
    }

    std::vector<std::string> list_all_plugins() {
        std::vector<std::string> names;
        for (const auto& pair : plugins) {
            names.push_back(pair.first);
        }
        return names;
    }

    void set_setting(const std::string& name, const std::string& key, const std::string& value) {
        if (plugins.find(name) != plugins.end()) {
            plugins[name].settings[key] = value;
        }
    }

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
