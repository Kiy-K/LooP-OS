# Changelog

## [0.1.1] - 2025-03-01

### Added
- **Login Hotfix**: Added auto-login fallback to `root` user if interactive login fails.
- **CLI Commands**:
    - `fyodor start`: Auto-login as `guest`.
    - `fyodor login`: Standard interactive login.
    - `fyodor login --user <name>`: Pre-fill username (e.g., `root`).

### Changed
- Refactored `src/fyodoros/shell/shell.py` to support programmatic login arguments.
- Updated `src/fyodoros/__main__.py` to parse command-line arguments and pass them to the shell.
- Updated `src/fyodoros/cli.py` to support `start` (guest) and `login` (interactive) modes.
