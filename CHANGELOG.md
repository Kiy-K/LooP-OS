# Changelog

## [0.8.0] - 2025-12-13 "The Ironclad Update"
### Architecture (Major Breaking Change)
- Migrated from pure Python library to **Tauri + Nuitka** Hybrid Application.
- Introduced **Sidecar Protocol**: Kernel runs as a compiled headless process controlled by React Frontend.
- Implemented **Shadcn/UI** for a professional "IDE-like" interface.

### Added
- `fyodor doctor`: Self-diagnosis tool for frozen binaries.
- `rootfs`: Strict virtualization of the file system (`~/.fyodor/`).
- **CI/CD**: GitHub Actions for automated cross-platform compilation.

### Security
- **Frozen Code**: Kernel source is no longer exposed in plain text.

## [0.7.0] - 2025-12-12
### Added
- **Persistent Memory System**: Integrated `ChromaDB` to provide semantic memory capabilities.
    - **Syscalls**: `sys_memory_store`, `sys_memory_search`, `sys_memory_recall`, `sys_memory_delete`.
    - **Agent Integration**: `ReActAgent` now auto-recalls relevant memories at the start of a task.
    - **Persistence**: Memories are stored in `~/.fyodor/memory` and persist across reboots.
- **Dependencies**: Added `chromadb` to `pyproject.toml` and `environment.yml`.

### Performance
- **Filesystem**: Optimized `sys_ls` to improve path resolution speed and error handling.

## [0.6.0] - 2025-12-09
### Verified
- **System Stability**: Completed "Phase 2.3" destructive test sweep of core subsystems.
- **Boot Integrity**: Confirmed deterministic boot and clean double-boot isolation.
- **Teardown Correctness**: Verified LIFO service shutdown and no ghost state leakage.
- **Sandbox Security**: Confirmed path resolution integrity and error containment.

### Fixed
- **Kernel**: Added graceful `shutdown()` method to orchestrate subsystem teardown.
- **Service Manager**: Renamed from Supervisor; completely re-architected with:
    - **Dependency Management**: DAG-based topological sort for correct startup/shutdown order.
    - **3-Phase Shutdown**: Warning -> Graceful -> Force protocol.
    - **Threaded Timeouts**: Non-blocking shutdown with configurable per-service timeouts.
    - **State Machine**: Explicit state tracking (WARNING, GRACEFUL, FORCE, CLEANUP).
- **Supervisor**: Implemented `shutdown()` to stop services in LIFO order and clear process registry.
- **Plugin Loader**: Implemented `teardown()` and shutdown hooks (`on_shutdown_warning`, `on_shutdown`) to safely stop active plugins.
- **Sandbox**: Patched a security vulnerability where missing C++ core allowed relative path traversal (e.g., `../../etc/passwd`). Added secure Python fallback.

## [0.5.1] - 2025-12-08
### Fixed
- **Critical Security**: Fixed a shell login bypass where failed authentication could fallback to root access.
- **Stability**: Fixed `sys_ls` crash when invoked on file paths.
- **Stability**: Fixed `sys_delete` and `DockerInterface` exception handling.
- **Deadlock**: Fixed a deadlock in the C++ Sandbox Core (`sandbox_core`) when capturing large output from subprocesses.
- **Filesystem**: Fixed `mkdir` logic to correctly raise `FileExistsError` instead of silently succeeding.

### Performance
- **Startup Time**: Reduced kernel startup time by ~90% (from ~1.6s to ~0.15s) by lazy-loading heavy cloud dependencies (`docker`, `kubernetes`).
- **Syscall Optimization**: Optimized `sys_ls` to use efficient type checking instead of exception handling control flow.
- **Sandbox IO**: Optimized `SyscallHandler` to bridge In-Memory and Real Filesystem efficiently for Sandbox paths.

## [0.5.0] - 2025-12-07
### Added
- **Docker Integration**: `sys_docker_*` syscalls, CLI commands, and Agent actions.
- **Kubernetes Integration**: `sys_k8s_*` syscalls, CLI commands, and Agent actions.
- **RBAC Updates**: Added `manage_docker` and `manage_k8s` permissions.
- **Cloud Interface**: `DockerInterface` and `KubernetesInterface` in `kernel.cloud`.

## [0.4.0] - 2025-12-07

### Added

#### Kernel Networking Layer
- **Global On/Off Switch**: Network functionality can now be controlled via `fyodor network` command
- **Strict Socket Enforcement**: Monkeypatching implementation ensures all socket operations go through the kernel layer
- **RBAC Integration**: Network access control through `manage_network` and `use_network` permissions

#### NASM Runtime
- **C++ FFI Sandbox Extension**: Native assembly execution in sandboxed environment
- **`sys_exec_nasm` Syscall**: New system call for executing NASM code from within the kernel

### Examples

#### CLI Network Management
```bash
# Enable/disable network globally
fyodor network on
fyodor network off
```

#### Python Agent Running NASM
```python
# Example of executing NASM code from Python agent
result = sys_exec_nasm("""
    section .text
    global _start
    _start:
        ; Your NASM code here
""")
```

## [0.3.5] - 2025-12-06
### Added
- **Plugin System Enhancements**:
  - Added support for plugin configuration via `fyodor plugin settings`.
  - Added persistent configuration storage in `~/.fyodor/plugins/config.json`.
- **New Plugins**:
  - `github`: Integration with GitHub for listing repos, creating issues, and viewing PRs.
  - `slack_notifier`: Send notifications to Slack webhooks.
  - `usage_dashboard`: Background system usage monitoring with TUI (`fyodor dashboard`).
  - `team_collaboration`: Role-Based Access Control (RBAC) extending the user management system.
- **User Management**:
  - Added role support to users (admin/user).
  - Added permission checking hooks.

### Changed
- `UserManager` now stores roles and passwords in a dictionary structure instead of just password hashes.
- CLI updated to include `dashboard` command.

### Plugin System
- Added **C++ Registry Core** (`registry_core` extension) for high-performance plugin management.
- Added **Plugin Manager** CLI (`fyodor plugin install/build/create`).
- Added Multi-language Support:
  - **Python**: Standard support.
  - **C++**: Auto-compilation via `cmake`.
  - **Node.js**: Auto-dependency installation via `npm`/`bun`.

### Security
- **C++ Sandbox Core**: New isolation layer enforcing virtual filesystem boundaries.
- **Process Isolation**: Agent commands run in restricted environments with sanitized paths and environment variables.
