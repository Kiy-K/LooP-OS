# Changelog

## [0.3.5] - Unreleased
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
