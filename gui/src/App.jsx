import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/tauri";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Idle");
  const [output, setOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [cmd, setCmd] = useState("");
  const [isConnected, setIsConnected] = useState(false);

  const ws = useRef(null);
  const outputRef = useRef(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (outputRef.current) {
        outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  async function startKernel() {
    setIsLoading(true);
    setStatus("Starting Kernel...");
    try {
        const msg = await invoke("start_kernel");
        setStatus(msg);
        // Start polling for connection
        connectToKernel();
    } catch (e) {
        setStatus("Error: " + e);
        setIsLoading(false);
    }
  }

  async function connectToKernel() {
      setStatus("Waiting for Kernel API...");
      let retries = 0;
      const maxRetries = 20;

      const interval = setInterval(async () => {
          try {
              const res = await fetch("http://localhost:8000/health");
              if (res.ok) {
                  clearInterval(interval);
                  setStatus("Connected to Kernel");
                  setIsConnected(true);
                  setIsLoading(false);
                  setupWebSocket();
              }
          } catch (e) {
              retries++;
              if (retries > maxRetries) {
                  clearInterval(interval);
                  setStatus("Failed to connect to Kernel API");
                  setIsLoading(false);
              }
          }
      }, 500);
  }

  function setupWebSocket() {
      ws.current = new WebSocket("ws://localhost:8000/ws");

      ws.current.onopen = () => {
          console.log("WS Open");
          setStatus("Online (WS Connected)");
      };

      ws.current.onmessage = (event) => {
          setOutput((prev) => prev + event.data);
      };

      ws.current.onclose = () => {
          setStatus("Disconnected");
          setIsConnected(false);
      };
  }

  async function sendCommand(e) {
      e.preventDefault();
      if (!cmd) return;

      // Local echo (optional, but good for latency)
      // setOutput((prev) => prev + "> " + cmd + "\n");

      try {
          await fetch("http://localhost:8000/exec", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({command: cmd})
          });
      } catch (e) {
          setOutput((prev) => prev + "[Error sending command]\n");
      }
      setCmd("");
  }

  return (
    <div className="container">
      <h1>FyodorOS Dashboard</h1>

      <div className="card">
        <p role="status">Status: {status}</p>
        {!isConnected && (
            <button
            onClick={startKernel}
            disabled={isLoading}
            className={isLoading ? "loading" : ""}
            aria-busy={isLoading}
            >
                {isLoading ? "Starting..." : "Launch Kernel"}
            </button>
        )}
      </div>

      <div className="terminal">
          <pre
            ref={outputRef}
            className="output"
            role="log"
            aria-live="polite"
            tabIndex={0}
            aria-label="Terminal Output"
          >
            {output}
          </pre>
          <form onSubmit={sendCommand} className="input-form">
              <span className="prompt">$</span>
              <input
                type="text"
                value={cmd}
                onChange={(e) => setCmd(e.target.value)}
                disabled={!isConnected}
                autoFocus
                aria-label="Command Input"
                placeholder="Enter command..."
              />
          </form>
      </div>
    </div>
  );
}

export default App;
