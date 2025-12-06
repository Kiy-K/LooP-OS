#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <filesystem>
#include <vector>
#include <string>
#include <iostream>
#include <cstdlib>
#include <unistd.h>
#include <sys/wait.h>
#include <system_error>

namespace py = pybind11;
namespace fs = std::filesystem;

class SandboxCore {
public:
    SandboxCore(const std::string& root_path) {
        // Resolve absolute path of the sandbox root
        try {
            if (!fs::exists(root_path)) {
                fs::create_directories(root_path);
            }
            this->root = fs::canonical(root_path);
        } catch (const std::exception& e) {
            throw std::runtime_error("Failed to initialize sandbox root: " + std::string(e.what()));
        }
    }

    std::string resolve_path(const std::string& virtual_path) {
        fs::path p = virtual_path;

        // Remove leading / to treat it relative to our root
        std::string p_str = p.string();
        if (p_str.length() > 0 && p_str[0] == '/') {
            p_str = p_str.substr(1);
        }

        fs::path relative_p = fs::path(p_str);

        // Construct potential full path
        // We need to prevent ".." escaping.
        fs::path joined = root / relative_p;

        // lexically_normal resolves ".." purely by string manipulation
        // It does not check existence.
        fs::path normalized = joined.lexically_normal();

        // Check if normalized path starts with root
        std::string norm_str = normalized.string();
        std::string root_str = root.string();

        if (norm_str.find(root_str) != 0) {
            throw std::runtime_error("Access Denied: Path escapes sandbox.");
        }

        return norm_str;
    }

    void execute(const std::string& cmd, const std::vector<std::string>& args, const std::map<std::string, std::string>& env) {
        // Prepare arguments
        std::vector<char*> c_args;
        c_args.push_back(const_cast<char*>(cmd.c_str()));
        for (const auto& arg : args) {
            c_args.push_back(const_cast<char*>(arg.c_str()));
        }
        c_args.push_back(nullptr);

        // Prepare environment
        std::vector<char*> c_env;
        std::vector<std::string> env_strs; // Keep strings alive
        for (const auto& pair : env) {
            env_strs.push_back(pair.first + "=" + pair.second);
            c_env.push_back(const_cast<char*>(env_strs.back().c_str()));
        }
        c_env.push_back(nullptr);

        pid_t pid = fork();
        if (pid == 0) {
            // Child process

            // ISOLATION
            // Try to use 'unshare' logic if possible, but implementing complex namespace logic in raw C without
            // helpers is error prone.
            // We'll rely on strict environment clearing and CWD.
            // Also, we set the SID.
            setsid();

            // Set working directory to sandbox root (acting as /)
            chdir(root.c_str());

            // Exec
            execvpe(cmd.c_str(), c_args.data(), c_env.data());

            // If we get here, exec failed
            std::cerr << "Failed to execute command: " << cmd << std::endl;
            exit(1);
        } else if (pid > 0) {
            // Parent
            int status;
            waitpid(pid, &status, 0);
            if (WIFEXITED(status) && WEXITSTATUS(status) != 0) {
                // Command failed, but we don't necessarily want to throw exception to python main process
                // maybe just return status?
                // For now, let's just log it or throw if severe.
                // throw std::runtime_error("Command failed with exit code " + std::to_string(WEXITSTATUS(status)));
            }
        } else {
            throw std::runtime_error("Fork failed");
        }
    }

private:
    fs::path root;
};

PYBIND11_MODULE(sandbox_core, m) {
    py::class_<SandboxCore>(m, "SandboxCore")
        .def(py::init<const std::string&>())
        .def("resolve_path", &SandboxCore::resolve_path)
        .def("execute", &SandboxCore::execute);
}
