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
#include <fstream>
#include <map>
#include <sstream>

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
        // Basic execute without output capture
        execute_internal(cmd, args, env, false);
    }

    // Compiles and runs NASM code
    // Returns {stdout: string, stderr: string, return_code: int}
    std::map<std::string, py::object> compile_and_run_nasm(const std::string& source, const std::string& output_name) {
        std::string asm_file = output_name + ".asm";
        std::string obj_file = output_name + ".o";
        std::string exe_file = output_name;

        // Write source to file inside sandbox
        fs::path asm_path = root / asm_file;
        std::ofstream out(asm_path);
        out << source;
        out.close();

        // 1. Compile: nasm -f elf64 <file> -o <obj>
        // We need 'nasm' in PATH or hardcoded. Assuming PATH inside sandbox env or host env.
        // We should execute this in sandbox context.
        std::vector<std::string> nasm_args = {"nasm", "-f", "elf64", asm_file, "-o", obj_file};
        auto res_compile = execute_with_output("nasm", nasm_args, {});

        if (res_compile["return_code"].cast<int>() != 0) {
            return {
                {"stdout", res_compile["stdout"]},
                {"stderr", res_compile["stderr"]},
                {"return_code", res_compile["return_code"]},
                {"stage", py::str("compilation")}
            };
        }

        // 2. Link: gcc <obj> -o <exe> -no-pie
        // Using gcc to link against libc
        std::vector<std::string> link_args = {"gcc", obj_file, "-o", exe_file, "-no-pie"};
        auto res_link = execute_with_output("gcc", link_args, {});

        if (res_link["return_code"].cast<int>() != 0) {
             return {
                {"stdout", res_link["stdout"]},
                {"stderr", res_link["stderr"]},
                {"return_code", res_link["return_code"]},
                {"stage", py::str("linking")}
            };
        }

        // 3. Run: ./<exe>
        std::vector<std::string> run_args = {"./" + exe_file};
        auto res_run = execute_with_output("./" + exe_file, run_args, {});
        res_run["stage"] = py::str("execution");
        return res_run;
    }

private:
    fs::path root;

    std::map<std::string, py::object> execute_with_output(const std::string& cmd, const std::vector<std::string>& args, const std::map<std::string, std::string>& env) {
        return execute_internal(cmd, args, env, true);
    }

    std::map<std::string, py::object> execute_internal(const std::string& cmd, const std::vector<std::string>& args, const std::map<std::string, std::string>& env, bool capture_output) {
        int pipe_out[2]; // stdout
        int pipe_err[2]; // stderr

        if (capture_output) {
            if (pipe(pipe_out) == -1 || pipe(pipe_err) == -1) {
                throw std::runtime_error("Failed to create pipes");
            }
        }

        pid_t pid = fork();
        if (pid == 0) {
            // Child
            setsid();
            chdir(root.c_str());

            if (capture_output) {
                // Redirect stdout
                dup2(pipe_out[1], STDOUT_FILENO);
                close(pipe_out[0]);
                close(pipe_out[1]);

                // Redirect stderr
                dup2(pipe_err[1], STDERR_FILENO);
                close(pipe_err[0]);
                close(pipe_err[1]);
            }

            // Prepare Env
            std::vector<char*> c_env;
            std::vector<std::string> env_strs;

            // Pass through PATH if not present, otherwise commands like 'nasm' won't be found
            // unless we rely on absolute paths or host env.
            // For safety, we usually clear env, but we need basic tools here.
            // If 'env' is empty, we might want to inject PATH.
            bool path_set = false;
            for (const auto& pair : env) {
                env_strs.push_back(pair.first + "=" + pair.second);
                if (pair.first == "PATH") path_set = true;
            }
            if (!path_set) {
                const char* host_path = std::getenv("PATH");
                if (host_path) env_strs.push_back(std::string("PATH=") + host_path);
            }

            for (const auto& s : env_strs) c_env.push_back(const_cast<char*>(s.c_str()));
            c_env.push_back(nullptr);

            // Prepare Args
            std::vector<char*> c_args;
            // args[0] usually is the program name
            for (const auto& arg : args) c_args.push_back(const_cast<char*>(arg.c_str()));
            c_args.push_back(nullptr);

            execvpe(cmd.c_str(), c_args.data(), c_env.data());

            // If failed
            std::cerr << "Exec failed: " << cmd << std::endl;
            exit(127);
        } else if (pid > 0) {
            // Parent
            if (capture_output) {
                close(pipe_out[1]);
                close(pipe_err[1]);
            }

            std::string stdout_str, stderr_str;

            if (capture_output) {
                // Read from pipes
                // Simple implementation: read until EOF.
                // Note: This can deadlock if pipe fills up and we waitpid before reading?
                // Better to read in loop.
                // But for simplicity in this synchronous call:
                // We should read from both fds using select/poll or just read one then other (risk of deadlock if both large).
                // Let's rely on standard small outputs for this task or use simple buffer reading.

                char buffer[1024];
                ssize_t n;
                while ((n = read(pipe_out[0], buffer, sizeof(buffer))) > 0) {
                    stdout_str.append(buffer, n);
                }
                while ((n = read(pipe_err[0], buffer, sizeof(buffer))) > 0) {
                    stderr_str.append(buffer, n);
                }

                close(pipe_out[0]);
                close(pipe_err[0]);
            }

            int status;
            waitpid(pid, &status, 0);

            int rc = 0;
            if (WIFEXITED(status)) rc = WEXITSTATUS(status);
            else rc = -1;

            if (capture_output) {
                return {
                    {"stdout", py::str(stdout_str)},
                    {"stderr", py::str(stderr_str)},
                    {"return_code", py::int_(rc)}
                };
            } else {
                return {};
            }

        } else {
            throw std::runtime_error("Fork failed");
        }
    }
};

PYBIND11_MODULE(sandbox_core, m) {
    py::class_<SandboxCore>(m, "SandboxCore")
        .def(py::init<const std::string&>())
        .def("resolve_path", &SandboxCore::resolve_path)
        .def("execute", &SandboxCore::execute)
        .def("compile_and_run_nasm", &SandboxCore::compile_and_run_nasm);
}
