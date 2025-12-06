# Changelog

## [0.2.0] - 2025-03-02

### Added
- **Launcher TUI**: `fyodor tui` provides an interactive menu for managing the OS.
- **Multi-Provider LLM Support**: Support for OpenAI, Gemini, and Anthropic backends.
- **User Persistence**: User accounts are now saved to `users.json` and persist across reboots.
- **New CLI Commands**:
    - `fyodor user <name> [pass]`: Create new users directly from the host CLI.
    - `fyodor setup`: Robust interactive configuration for API keys.
- **New Shell Commands**:
    - `create <filename>`: Quickly create files (defaults to `.txt`).
    - `navigate <app>`: Launch apps like browser or calculator manually.

### Changed
- Refactored project structure to `src/fyodoros` package.
- Updated `LLMProvider` to read `LLM_PROVIDER` from `.env`.
- Improved `.env` file handling in `cli.py` to support quoted values and comments.

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
