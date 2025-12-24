import React, { useState } from 'react';

// Mock types for tree data
interface FileNode {
  name: string;
  type: 'file' | 'folder';
  children?: FileNode[];
  isOpen?: boolean;
}

interface CortexViewProps {
  files?: FileNode[]; // In future, this will be populated
  memories?: string[];
  isGhostMode?: boolean;
}

const TabButton: React.FC<{
  label: string;
  isActive: boolean;
  onClick: () => void;
}> = ({ label, isActive, onClick }) => (
  <button
    onClick={onClick}
    className={`
      flex-1 py-1 text-[10px] font-mono border-b border-border uppercase tracking-wider
      hover:bg-surface hover:text-primary transition-colors
      ${isActive ? 'bg-surface text-primary border-b-2 border-primary' : 'text-muted bg-transparent'}
    `}
  >
    {label}
  </button>
);

export const CortexView: React.FC<CortexViewProps> = ({
  files = [],
  memories = [],
  isGhostMode = false
}) => {
  const [activeTab, setActiveTab] = useState<'fs' | 'mem' | 'senses'>('fs');

  // Temporary mock data if empty
  const mockFiles: FileNode[] = [
    { name: 'home', type: 'folder', isOpen: true, children: [
        { name: 'documents', type: 'folder', children: [] },
        { name: 'projects', type: 'folder', children: [] },
        { name: 'notes.txt', type: 'file' }
    ]}
  ];
  const displayFiles = files.length > 0 ? files : mockFiles;

  const mockMemories = [
    "Recall: User prefers dark mode",
    "Recall: Project 'Monochrome' initialized",
    "Recall: TypeScript migration complete"
  ];
  const displayMemories = memories.length > 0 ? memories : mockMemories;

  return (
    <div className="flex flex-col h-full w-64 border-r border-border bg-background">
      {/* Header / Tabs */}
      <div className="flex flex-row border-b border-border">
        <TabButton label="FILES" isActive={activeTab === 'fs'} onClick={() => setActiveTab('fs')} />
        <TabButton label="MEM" isActive={activeTab === 'mem'} onClick={() => setActiveTab('mem')} />
        <TabButton label="SENSES" isActive={activeTab === 'senses'} onClick={() => setActiveTab('senses')} />
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto p-2">

        {/* File System View */}
        {activeTab === 'fs' && (
          <div className="font-mono text-xs">
            <div className="text-muted mb-2 uppercase tracking-widest text-[10px]">~/loop/home</div>
            <FileTree nodes={displayFiles} level={0} />
          </div>
        )}

        {/* Memory View */}
        {activeTab === 'mem' && (
          <div className="space-y-2">
             <div className="text-muted mb-2 uppercase tracking-widest text-[10px] font-mono">Recent Embeddings</div>
             {displayMemories.map((mem, idx) => (
               <div key={idx} className="p-2 border border-border bg-surface text-xs text-gray-300 font-mono">
                 <span className="text-zinc-500 mr-2">[{idx}]</span>
                 {mem}
               </div>
             ))}
          </div>
        )}

        {/* Senses View */}
        {activeTab === 'senses' && (
          <div className="space-y-4 font-mono text-xs">
            <div className="p-3 border border-border bg-surface">
              <div className="text-muted uppercase text-[10px] mb-1">Ghost Mode</div>
              <div className="flex items-center justify-between">
                <span>Status</span>
                <span className={isGhostMode ? "text-green-500" : "text-muted"}>
                  {isGhostMode ? "LISTENING" : "STANDBY"}
                </span>
              </div>
            </div>

            <div className="p-3 border border-border bg-surface opacity-50">
              <div className="text-muted uppercase text-[10px] mb-1">Vision</div>
              <div className="flex items-center justify-between">
                <span>Input</span>
                <span>DISABLED</span>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};

// Recursive File Tree Component
const FileTree: React.FC<{ nodes: FileNode[], level: number }> = ({ nodes, level }) => {
  return (
    <ul className={`pl-${level === 0 ? 0 : 4} border-l border-zinc-800 ml-${level === 0 ? 0 : 2}`}>
      {nodes.map((node, i) => (
        <li key={i} className="mb-1">
          <div className="flex items-center group cursor-pointer">
             <span className="text-zinc-600 mr-2 group-hover:text-white">
                {node.type === 'folder' ? '📂' : '📄'}
             </span>
             <span className={`group-hover:text-white ${node.type === 'folder' ? 'text-zinc-300' : 'text-zinc-500'}`}>
                {node.name}
             </span>
          </div>
          {node.children && node.children.length > 0 && (
             <FileTree nodes={node.children} level={level + 1} />
          )}
        </li>
      ))}
    </ul>
  );
}
