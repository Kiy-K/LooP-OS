# QA Checklist v0.8.0

This document serves as the final "Go/No-Go" gauge before tagging the release.

## 1. Smoke Test (The "Splash" Check)

*   **Action:** Launch the App.
*   **Verify:**
    *   Does the Splash screen appear instantly?
    *   Does the Main Window load within 5 seconds?
*   **Fail Condition:** White screen hang > 10s.

## 2. Persistence Test (The "Reboot" Check)

*   **Why:** Verifies `rootfs` paths are correct in the Frozen binary.
*   **Action:**
    1.  Ask Agent: *"Remember that my API key is 12345"*
    2.  Close App.
    3.  Re-open App.
    4.  Ask Agent: *"What is my API key?"*
*   **Verify:** Agent retrieves the memory (e.g., responds with "12345").

## 3. The NASM Gauntlet (The "Metal" Check)

*   **Why:** Verifies `nasm` subprocess spawning isn't blocked by OS permissions.
*   **Action:** Run this specific prompt:
    ```text
    Write a NASM program that calculates 10 + 20 and returns the result as the exit code. Run it.
    ```
*   **Verify:** Output shows "Exit Code: 30".

## 4. Panic Protocol (Troubleshooting)

Detailed instructions on where to find logs if the app crashes silently:

*   **Windows:** `%APPDATA%\loop\var\logs\kernel.log`
*   **Mac/Linux:** `~/.loop/var/logs/kernel.log`
