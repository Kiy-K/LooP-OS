import React, { useEffect } from 'react';

export interface SystemStats {
  cpu: number;
  memory: string; // e.g., "3.4GB"
  kernel: string; // "ONLINE", "OFFLINE"
}

interface SystemHUDProps {
  version: string;
  agentState: string;
  stats: SystemStats;
  ws: React.MutableRefObject<WebSocket | null>;
  isConnected: boolean;
}

export const SystemHUD: React.FC<SystemHUDProps> = ({
  version,
  agentState,
  stats,
  ws,
  isConnected
}) => {

  useEffect(() => {
    if (!isConnected) return;

    const poll = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ action: "telemetry" }));
      }
    }, 2000);

    return () => clearInterval(poll);
  }, [isConnected, ws]);

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 h-6 bg-background border-t border-border flex items-center justify-between px-2 text-[10px] font-mono z-50"
      role="status"
      aria-label="System Status"
    >
      {/* Left: Version */}
      <div className="flex items-center space-x-4 text-muted" title={`Version ${version}`}>
        <span className="font-bold text-primary">{version}</span>
        {isConnected ? (
           <span className="text-green-500" title="System Connected" aria-label="System Connected">
             <span aria-hidden="true">●</span> CONNECTED
           </span>
        ) : (
           <span className="text-red-500" title="System Disconnected" aria-label="System Disconnected">
             <span aria-hidden="true">○</span> DISCONNECTED
           </span>
        )}
      </div>

      {/* Center: Agent State */}
      <div
        className="absolute left-1/2 transform -translate-x-1/2 font-medium tracking-widest uppercase text-primary"
        aria-live="polite"
        title="Current Agent Activity"
        aria-label={`Agent status: ${agentState}`}
      >
        [{agentState}]
      </div>

      {/* Right: System Stats */}
      <div className="flex items-center space-x-3 text-muted" aria-label="System Resources">
        <span title="CPU Usage">
          CPU: <span className="text-primary">{stats.cpu}%</span>
        </span>
        <span className="text-border" aria-hidden="true">|</span>
        <span title="Memory Usage">
          MEM: <span className="text-primary">{stats.memory}</span>
        </span>
        <span className="text-border" aria-hidden="true">|</span>
        <span title="Kernel Status">
          KERNEL: <span className={stats.kernel === 'ONLINE' ? 'text-green-500' : 'text-red-500'}>{stats.kernel}</span>
        </span>
      </div>
    </footer>
  );
};
