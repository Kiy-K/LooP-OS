import React, { useState, useEffect, useRef } from "react";
import { SystemHUD, SystemStats } from "./components/SystemHUD";
import { CortexView } from "./components/CortexView";
import { AgentStream, StreamEvent } from "./components/AgentStream";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Idle");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [stats, setStats] = useState<SystemStats>({ cpu: 0, memory: "0GB", kernel: "OFFLINE" });
  const [inputCmd, setInputCmd] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isGhostMode, setIsGhostMode] = useState(false);

  const ws = useRef<WebSocket | null>(null);

  // Kernel Connection Logic
  async function connectToKernel() {
      setStatus("Connecting...");
      let retries = 0;
      const maxRetries = 20;

      const interval = setInterval(async () => {
          try {
              const res = await fetch("http://localhost:8000/health");
              if (res.ok) {
                  clearInterval(interval);
                  setStatus("Connected");
                  setIsConnected(true);
                  setupWebSocket();
              }
          } catch (e) {
              retries++;
              if (retries > maxRetries) {
                  clearInterval(interval);
                  setStatus("Failed to connect");
              }
          }
      }, 500);
  }

  function setupWebSocket() {
      if (ws.current) ws.current.close();
      ws.current = new WebSocket("ws://localhost:8000/ws");

      ws.current.onopen = () => {
          console.log("WS Open");
          setStatus("Online");
          setStats(prev => ({ ...prev, kernel: "ONLINE" }));
      };

      ws.current.onmessage = (event) => {
          const raw = event.data;

          // Try to parse as JSON first
          try {
              const data = JSON.parse(raw);

              // Handle Telemetry Response
              // Assuming backend sends { type: "telemetry", data: { ... } } OR
              // we blindly check for fields.
              // Since we don't control backend structure fully yet, we'll try to sniff it.
              // If the message has "cpu" or "memory" at the top level, treat as stats.
              if (data.cpu !== undefined || data.memory !== undefined) {
                  setStats({
                      cpu: data.cpu || 0,
                      memory: data.memory || "0GB",
                      kernel: "ONLINE"
                  });
                  if (data.ghost_mode !== undefined) setIsGhostMode(data.ghost_mode);
                  return; // Don't add telemetry to the stream
              }

              // Handle Structured Agent Output
              // If it's a generic JSON object intended for the stream
              addEvent('json', data);

          } catch (e) {
              // Not JSON? Treat as text/markdown
              addEvent('text', raw);
          }
      };

      ws.current.onclose = () => {
          setStatus("Disconnected");
          setIsConnected(false);
          setStats(prev => ({ ...prev, kernel: "OFFLINE" }));
      };
  }

  function addEvent(type: 'text' | 'json', content: any) {
      const newEvent: StreamEvent = {
          id: Date.now(),
          type,
          content,
          timestamp: new Date().toLocaleTimeString([], { hour12: false })
      };
      setEvents(prev => [...prev, newEvent]);
  }

  async function sendCommand(e: React.FormEvent) {
      e.preventDefault();
      if (!inputCmd) return;

      // Optimistic Update
      addEvent('text', `> ${inputCmd}`);

      try {
          await fetch("http://localhost:8000/exec", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({command: inputCmd})
          });
      } catch (e) {
          addEvent('text', `Error: ${e}`);
      }
      setInputCmd("");
  }

  // Initial connection
  useEffect(() => {
      connectToKernel();
      return () => {
          if (ws.current) ws.current.close();
      };
  }, []);

  return (
    <div className="flex h-screen w-screen bg-background overflow-hidden text-primary font-sans">

      {/* LEFT: Cortex Sidebar */}
      <CortexView isGhostMode={isGhostMode} />

      {/* CENTER: Main Content */}
      <div className="flex-1 flex flex-col relative">

          {/* Header Area (Optional, or just part of stream) */}
          <div className="h-12 border-b border-border flex items-center px-4 bg-surface z-10">
              <div className="font-mono font-bold text-lg tracking-tight">LOOP<span className="text-zinc-500">OS</span></div>
              <div className="ml-auto text-xs text-muted font-mono bg-zinc-900 px-2 py-1 rounded">
                  WS: {isConnected ? "CONNECTED" : "WAITING"}
              </div>
          </div>

          {/* Stream Area */}
          <AgentStream events={events} />

          {/* Input Area */}
          <div className="p-4 bg-background border-t border-border pb-8"> {/* Extra padding for HUD */}
              <form onSubmit={sendCommand} className="relative">
                  <span className="absolute left-3 top-3 text-zinc-500 font-mono">$</span>
                  <input
                    type="text"
                    value={inputCmd}
                    onChange={(e) => setInputCmd(e.target.value)}
                    className="w-full bg-surface border border-border text-primary font-mono pl-8 pr-4 py-2 focus:outline-none focus:border-zinc-500 transition-colors"
                    placeholder="Enter command or natural language..."
                    autoFocus
                  />
              </form>
          </div>

      </div>

      {/* BOTTOM: HUD */}
      <SystemHUD
        version="v0.9.5"
        agentState={status}
        stats={stats}
        ws={ws}
        isConnected={isConnected}
      />

    </div>
  );
}

export default App;
