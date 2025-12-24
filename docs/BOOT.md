# Boot Subsystem Documentation

## Overview

The Boot Subsystem in LooP v0.6.0 introduces a centralized, deterministic initialization sequence. This ensures that all core components (security, filesystem, network) are brought up in a correct and auditable order before the user shell or agent is launched.

## Boot Sequence

The boot process is orchestrated by `src/loop/kernel/init.py` via the `boot()` function. The sequence is as follows:

1.  **Configuration Loading**: `loop.conf` is parsed using `ConfigLoader`. Defaults are applied if the file is missing.
2.  **Filesystem Mounts**: Virtual filesystem mount points are prepared based on configuration.
3.  **Security Initialization**: `UserManager` is initialized to handle RBAC and authentication.
4.  **Core Services**: `Scheduler` and `NetworkManager` are initialized.
5.  **Syscall Handler**: The `SyscallHandler` is created, linking core services.
6.  **Network Guard**: `NetworkGuard` is engaged if network is disabled in config.
7.  **Shared Sandbox**: A single `AgentSandbox` instance is created and shared between the Kernel and the Agent.
8.  **Supervisor**: The process supervisor is initialized.
9.  **Kernel Assembly**: The `Kernel` object is instantiated via Dependency Injection with all prepared components.
10. **Startup Process**: The Shell (or GUI) process is prepared and attached to the Kernel.

## Configuration

The `loop.conf` file controls the boot parameters:

```ini
[kernel]
debug=true
network_enabled=true
gui_enabled=false

[filesystem]
mounts=/tmp,/var/log

[security]
rbac_enabled=true
```

## Architecture

*   **Entry Point**: `src/loop/kernel/init.py`
*   **Config Loader**: `src/loop/kernel/config.py`
*   **Kernel Injection**: `src/loop/kernel/kernel.py` now accepts components in `__init__`.

## Testing

*   Unit tests for boot logic are located in `tests/test_boot.py` (functional) and `tests/test_init.py` (stubs).
*   The sequence is designed to be easily mocked for isolated testing.
