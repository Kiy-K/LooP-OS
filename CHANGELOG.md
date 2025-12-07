# Changelog

## [0.5.0] - 2024-05-01
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
