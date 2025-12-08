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
#include <poll.h>

namespace py = pybind11;
namespace fs = std::filesystem;

/**
 * @brief SandboxCore provides a secure execution environment for agents.
 *
 * It handles path resolution to prevent traversal attacks and manages process
 * execution with output capture.
 */
class SandboxCore {
public:
    /**
     * @brief Initialize the SandboxCore.
     *
     * @param root_path The absolute path to the sandbox root directory.
     *                  Will be created if it does not exist.
     */
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

    /**
     * @brief Resolves a virtual path to a safe absolute path within the sandbox.
     *
     * Ensures that the resolved path does not escape the sandbox root (e.g., via "..").
     *
     * @param virtual_path The path relative to the sandbox root.
     * @return std::string The absolute path on the host filesystem.
     * @throws std::runtime_error If the path attempts to escape the sandbox.
     */
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

    /**
     * @brief Executes a command within the sandbox.
     *
     * @param cmd The command to execute.
     * @param args A list of arguments for the command.
     * @param env A map of environment variables.
     * @return std::map<std::string, py::object> A dictionary containing 'stdout', 'stderr', and 'return_code'.
     */
    std::map<std::string, py::object> execute(const std::string& cmd, const std::vector<std::string>& args, const std::map<std::string, std::string>& env) {
        // Capture output by default so Agent can see results
        return execute_internal(cmd, args, env, true);
    }

    /**
     * @brief Compiles and runs NASM assembly code.
     *
     * This utility simplifies the process of writing assembly, compiling it with nasm,
     * linking with gcc, and executing the result.
     *
     * @param source The NASM assembly source code.
     * @param output_name The base name for output files (asm, object, executable).
     * @return std::map<std::string, py::object> Result dictionary containing output and return code.
     */
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
                // Use poll to read from both pipes without deadlocking
                struct pollfd fds[2];
                fds[0].fd = pipe_out[0];
                fds[0].events = POLLIN;
                fds[1].fd = pipe_err[0];
                fds[1].events = POLLIN;

                bool out_open = true;
                bool err_open = true;
                char buffer[4096];

                while (out_open || err_open) {
                    int ret = poll(fds, 2, -1);
                    if (ret < 0) {
                         if (errno == EINTR) continue;
                         break;
                    }

                    if (out_open && (fds[0].revents & POLLIN)) {
                        ssize_t count = read(pipe_out[0], buffer, sizeof(buffer));
                        if (count > 0) stdout_str.append(buffer, count);
                        else out_open = false; // EOF or error
                    } else if (out_open && (fds[0].revents & (POLLHUP | POLLERR))) {
                        out_open = false;
                    }

                    if (err_open && (fds[1].revents & POLLIN)) {
                        ssize_t count = read(pipe_err[0], buffer, sizeof(buffer));
                        if (count > 0) stderr_str.append(buffer, count);
                        else err_open = false;
                    } else if (err_open && (fds[1].revents & (POLLHUP | POLLERR))) {
                        err_open = false;
                    }
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
