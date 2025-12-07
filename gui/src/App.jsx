import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import { Command } from "@tauri-apps/api/shell";
import "./App.css";

/**
 * Main application component for the FyodorOS Desktop GUI.
 *
 * Displays a dashboard with the current kernel status and provides a button
 * to launch the kernel subprocess via Tauri's IPC.
 *
 * @returns {JSX.Element} The rendered React component.
 */
function App() {
  const [status, setStatus] = useState("Idle");
  const [output, setOutput] = useState("");

  /**
   * Invokes the 'start_kernel' command in the Tauri backend.
   * Updates the status state with the result or error.
   */
  async function startKernel() {
    setStatus("Starting Kernel...");
    try {
        // We use the custom command defined in Rust to spawn the kernel
        // Alternatively we can use Tauri shell API if configured
        const msg = await invoke("start_kernel");
        setStatus(msg);
    } catch (e) {
        setStatus("Error: " + e);
    }
  }

  return (
    <div className="container">
      <h1>FyodorOS Dashboard</h1>

      <div className="card">
        <p>Status: {status}</p>
        <button onClick={startKernel}>
            Launch Kernel Subprocess
        </button>
      </div>

      <div className="logs">
          <pre>{output}</pre>
      </div>
    </div>
  );
}

export default App;
