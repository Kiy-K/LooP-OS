# QA Checklist v0.8.0

This document outlines the manual Quality Assurance protocol for verifying FyodorOS v0.8.0 releases.

## 1. Persistence Test

**Objective:** Verify that user data persists across application restarts.

1.  **Launch** the FyodorOS Desktop application.
2.  **Open** the File Explorer (or use Terminal).
3.  **Create** a new file named `persistence_test.txt` in the home directory.
    *   Command: `create persistence_test.txt`
4.  **Close** the application completely (Quit).
5.  **Re-open** the application.
6.  **Verify** that `persistence_test.txt` still exists.

## 2. Sandbox Test

**Objective:** Verify that the security sandbox prevents unauthorized access to the host filesystem.

1.  **Launch** the application.
2.  **Open** the Terminal/Shell.
3.  **Execute** the following command to attempt reading the host's password file:
    *   Command: `read /etc/passwd`
4.  **Expected Result:** The operation should fail with an "Access Denied" or "File not found" error (depending on path resolution masking).
5.  **Verify:** Ensure no content from the actual `/etc/passwd` file is displayed.

## 3. NASM Test

**Objective:** Verify that the frozen Nuitka binary allows the kernel to spawn the external `nasm` process.

1.  **Launch** the application.
2.  **Open** the Terminal/Shell.
3.  **Execute** the following NASM code snippet via the agent or a specific command:
    *   *Note: If testing via Agent, prompt: "Compile and run a hello world in assembly"*
    *   *Alternatively, run `fyodor doctor` if accessible.*
4.  **Expected Result:** The agent should successfully report execution output (e.g., "Hello World") without crashing or reporting "nasm not found".
