
import React, { useState, useEffect, useRef } from "react";
// Mocking shadcn components as per plan, assuming they exist in typical path
// In a real env, these would be:
// import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable";
// import { ScrollArea } from "@/components/ui/scroll-area";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";

// Since we are mocking the environment and don't have the files, we simulate the layout structure
// using standard divs with Tailwind classes that mirror the intent.

const OSLayout = () => {
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [output, setOutput] = useState([
      { type: 'system', content: 'LooP Kernel v0.8.0 Initialized...' },
      { type: 'system', content: 'Waiting for connection...' }
  ]);
  const [input, setInput] = useState("");

  const scrollRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
      if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
  }, [output]);

  const handleSend = (e) => {
      e.preventDefault();
      if (!input.trim()) return;

      setOutput([...output, { type: 'user', content: `> ${input}` }]);
      setInput("");
      // Logic to send to Tauri/Kernel would go here
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-zinc-950 text-zinc-100 font-sans overflow-hidden">

      {/* Main Workspace Grid */}
      <div className="flex-1 flex overflow-hidden">

        {/* Sidebar (Pane 1) */}
        <div
            style={{ width: sidebarWidth }}
            className="border-r border-zinc-800 flex flex-col bg-zinc-900"
        >
          <div className="p-4 border-b border-zinc-800 font-bold tracking-wider text-sm">
            LOOP<span className="text-emerald-500">OS</span>
          </div>
          <div className="p-2 space-y-1">
             <div className="px-2 py-1.5 text-xs text-zinc-500 font-semibold uppercase">Explorer</div>
             <button className="w-full text-left px-3 py-2 text-sm hover:bg-zinc-800 rounded flex items-center gap-2">
                📂 <span>home</span>
             </button>
             <button className="w-full text-left px-3 py-2 text-sm hover:bg-zinc-800 rounded flex items-center gap-2">
                📄 <span>notes.txt</span>
             </button>
          </div>
        </div>

        {/* Resizer Handle Mock */}
        <div className="w-1 bg-zinc-800 cursor-col-resize hover:bg-zinc-700" />

        {/* Terminal/Chat Area (Pane 2) */}
        <div className="flex-1 flex flex-col bg-zinc-950">

           {/* Header */}
           <div className="h-12 border-b border-zinc-800 flex items-center px-4 justify-between bg-zinc-900/50">
              <span className="text-sm text-zinc-400">root@loop:~</span>
              <div className="flex gap-2">
                 <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50"></div>
                 <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50"></div>
                 <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50"></div>
              </div>
           </div>

           {/* LogStream (ScrollArea) */}
           <div
             className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-sm"
             ref={scrollRef}
           >
              {output.map((line, i) => (
                  <div key={i} className={`
                    ${line.type === 'user' ? 'text-zinc-300' : 'text-emerald-400'}
                  `}>
                      {line.content}
                  </div>
              ))}
           </div>

           {/* Input Area */}
           <div className="p-4 border-t border-zinc-800 bg-zinc-900">
              <form onSubmit={handleSend} className="flex gap-2">
                 <span className="text-emerald-500 font-bold py-2">$</span>
                 <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="flex-1 bg-transparent border-none outline-none text-zinc-100 placeholder-zinc-600 font-mono"
                    placeholder="Enter command..."
                    autoFocus
                 />
              </form>
           </div>
        </div>
      </div>

      {/* Status Bar (Pane 3) */}
      <div className="h-6 bg-zinc-900 border-t border-zinc-800 flex items-center px-3 text-xs text-zinc-500 justify-between">
         <div className="flex gap-4">
            <span>READY</span>
            <span>master*</span>
         </div>
         <div className="flex gap-4">
             <span>CPU: 2%</span>
             <span>MEM: 140MB</span>
             <span>UTF-8</span>
         </div>
      </div>
    </div>
  );
};

export default OSLayout;
