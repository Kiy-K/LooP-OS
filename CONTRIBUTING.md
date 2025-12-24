# Contributing to LooP

First off, thank you for considering contributing to LooP! 🎉

LooP is an experimental AI microkernel, and we welcome contributions from developers interested in operating systems, AI agents, and low-level programming.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Guidelines](#coding-guidelines)
- [Submitting Changes](#submitting-changes)
- [Testing](#testing)
- [Documentation](#documentation)

## 📜 Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [khoitruong071510@gmail.com](mailto:khoitruong071510@gmail.com).

## 🤝 How Can I Contribute?

### Reporting Bugs

Found a bug? Help us improve LooP:

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (OS, Python version, LooP version)
   - Relevant logs or error messages

### Suggesting Enhancements

Have an idea for LooP? We'd love to hear it!

1. **Check existing issues/discussions** first
2. **Open an issue** with:
   - Clear use case
   - Why this enhancement would be useful
   - Possible implementation approach (optional)

### Contributing Code

We welcome contributions in several areas:

#### 🔧 Core Kernel
- Syscall implementations
- Process scheduling improvements
- Memory management
- Security enhancements

#### 🤖 Agent Layer
- New agent capabilities
- ReAct loop optimizations
- SystemDOM enhancements
- Tool integrations

#### 🔌 Plugins
- New plugin implementations
- Plugin system improvements
- Cross-language plugin support

#### 📱 Applications
- New agent-native apps
- Improvements to existing apps (browser, explorer, etc.)
- GUI components

#### 📚 Documentation
- README improvements
- Code documentation
- Tutorials and guides
- Architecture documentation

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- C++ compiler (for extensions)
- NASM (included in the project)
- Git

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/Kiy-K/LooP.git
cd LooP

# Add upstream remote
git remote add upstream https://github.com/Kiy-K/LooP.git
```

### Install Development Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
pip install -r requirements.txt
playwright install chromium

# Install development tools
pip install pytest black flake8 mypy
```

### Build C++ Extensions

```bash
# Build the sandbox and other C++ components
python setup_core.py build_ext --inplace
```

### Verify Installation

```bash
# Run LooP
loop start

# You should see the LooP shell
```

## 📁 Project Structure

```
LooP/
├── src/loop/
│   ├── kernel/          # Core kernel components
│   │   ├── agent.py     # Agent ReAct loop
│   │   ├── dom.py       # SystemDOM implementation
│   │   ├── sandbox.py   # C++ sandbox integration
│   │   ├── syscall_handler.py
│   │   └── scheduler.py
│   ├── bin/             # Agent-native applications
│   │   ├── browser.py
│   │   ├── explorer.py
│   │   └── calc.py
│   ├── shell/           # Interactive shell
│   ├── plugins/         # Plugin system
│   └── cli.py           # CLI entry point
├── build/               # C++ build artifacts
├── tools/               # NASM and other tools
├── tests/               # Test suite
└── docs/                # Documentation

```

## 💻 Coding Guidelines

### Python Style

We follow PEP 8 with some flexibility:

```python
# Use meaningful variable names
def execute_syscall(syscall_name: str, args: list) -> dict:
    """Execute a system call and return result."""
    pass

# Type hints are encouraged
from typing import Optional, Dict, List

# Docstrings for public functions
def create_process(name: str, binary: str) -> Optional[int]:
    """
    Create a new process in the kernel.
    
    Args:
        name: Process name
        binary: Path to executable
        
    Returns:
        Process ID if successful, None otherwise
    """
    pass
```

### C++ Style

For C++ extensions:

```cpp
// Clear function names
bool ValidatePath(const std::string& path);

// Document complex logic
// Prevents path traversal attacks by normalizing and checking bounds
std::string SanitizePath(const std::string& input) {
    // Implementation
}
```

### Code Formatting

```bash
# Format Python code
black src/

# Check for issues
flake8 src/
mypy src/
```

### Naming Conventions

- **Python**: `snake_case` for functions/variables, `PascalCase` for classes
- **C++**: `PascalCase` for functions, `snake_case` for variables
- **Files**: `snake_case.py` or `snake_case.cpp`

## 🔄 Submitting Changes

### Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

2. **Make your changes**
   - Write clear, focused commits
   - Follow coding guidelines
   - Add tests if applicable
   - Update documentation

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: brief description of changes"
   ```

   Commit message prefixes:
   - `Add:` - New features
   - `Fix:` - Bug fixes
   - `Update:` - Changes to existing features
   - `Docs:` - Documentation changes
   - `Refactor:` - Code refactoring
   - `Test:` - Adding/updating tests

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Provide a clear description of changes
   - Reference any related issues

### Pull Request Guidelines

**Title:** Clear and descriptive
```
Add kernel networking layer with RBAC
Fix sandbox path traversal vulnerability
Update agent ReAct loop for better reasoning
```

**Description should include:**
- What changes were made
- Why these changes were needed
- How to test the changes
- Any breaking changes
- Screenshots/demos (if applicable)

**Example:**
```markdown
## Changes
- Added network syscall layer with socket enforcement
- Implemented RBAC permissions for network access
- Added `loop network` CLI command

## Why
Agents need controlled network access without compromising security.

## Testing
1. Install updated LooP
2. Run `loop network on`
3. Create agent with network permission
4. Verify socket operations are intercepted

## Breaking Changes
None - this is an additive feature.
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_kernel.py

# Run with coverage
pytest --cov=src/loop tests/
```

### Writing Tests

```python
# tests/test_syscall.py
import pytest
from loop.kernel.syscall_handler import SyscallHandler

def test_create_file():
    """Test file creation syscall"""
    handler = SyscallHandler()
    result = handler.sys_create_file("/test/file.txt", "content")
    assert result["success"] == True
    assert result["path"] == "/test/file.txt"

def test_sandbox_protection():
    """Test path traversal protection"""
    handler = SyscallHandler()
    with pytest.raises(SecurityError):
        handler.sys_read_file("../../etc/passwd")
```

### Manual Testing

```bash
# Start LooP in test mode
loop start --test

# Try your changes
guest@loop:/> your-command-here
```

## 📖 Documentation

### Code Documentation

```python
def sys_exec_nasm(self, code: str) -> dict:
    """
    Execute NASM assembly code in sandboxed environment.
    
    This syscall compiles and runs NASM code through the C++ FFI
    sandbox extension. All execution is isolated and monitored.
    
    Args:
        code: NASM assembly source code
        
    Returns:
        dict: Execution result with keys:
            - success (bool): Whether execution succeeded
            - output (str): Program output
            - exit_code (int): Process exit code
            
    Raises:
        SandboxError: If code violates sandbox constraints
        CompilationError: If NASM compilation fails
        
    Example:
        >>> syscall = SyscallHandler()
        >>> result = syscall.sys_exec_nasm('''
        ...     section .text
        ...     global _start
        ...     _start:
        ...         mov eax, 42
        ... ''')
        >>> print(result['exit_code'])
        42
    """
    pass
```

### README/Guide Updates

When adding new features:
- Update main README.md
- Add examples to relevant sections
- Update CHANGELOG.md
- Consider adding to documentation site (if applicable)

## 🎯 Areas We'd Love Help With

### High Priority
- [ ] Desktop GUI development (Tauri + React)
- [ ] More agent-native applications
- [ ] Security audits and improvements
- [ ] Performance optimizations
- [ ] Cross-platform testing

### Good First Issues
- [ ] Documentation improvements
- [ ] Bug fixes in existing features
- [ ] Test coverage improvements
- [ ] Code cleanup and refactoring

### Advanced Contributions
- [ ] Multi-agent orchestration
- [ ] Distributed LooP nodes
- [ ] Additional runtime languages (Rust, Go)
- [ ] Advanced scheduling algorithms
- [ ] GPU acceleration for agents

## 💬 Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Email**: khoitruong071510@gmail.com for private inquiries

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Mentioned in the README (for significant contributions)

## 📄 License

By contributing to LooP, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to LooP!**

Together, we're building the future of autonomous computing. 🚀
