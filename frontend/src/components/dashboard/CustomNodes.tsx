// frontend/src/components/dashboard/CustomNodes.tsx
import React from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';

interface StatusNodeData {
  count: number;
  label: string;
}

interface HandleProps {
  type: 'source' | 'target';
  position: Position;
  id: string;
  style?: React.CSSProperties;
}

interface StatusNodeProps {
  data: StatusNodeData;
  handles: HandleProps[];
  color: string;
  glow: string;
  icon?: string;
}

const StatusNode: React.FC<StatusNodeProps> = ({ data, handles, color, glow }) => {
  return (
    <div
      className="rounded-lg p-3 w-[140px] h-[80px] flex flex-col justify-center text-center transition-all duration-200 cursor-pointer hover:scale-105"
      style={{
        background: `linear-gradient(135deg, ${glow}, var(--bg-tertiary))`,
        border: `1px solid ${color}33`,
        boxShadow: `0 0 12px ${glow}`,
      }}
    >
      {handles.map((handle) => (
        <Handle
          key={handle.id}
          type={handle.type}
          position={handle.position}
          id={handle.id}
          style={{
            width: 8,
            height: 8,
            border: '2px solid var(--bg-primary)',
            background: color,
            ...handle.style,
          }}
        />
      ))}
      <div>
        <div
          className="text-xs font-medium mb-1"
          style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
        >
          {data.label}
        </div>
        <div
          className="text-xl font-bold data-value"
          style={{ color, fontFamily: 'var(--font-mono)' }}
        >
          {data.count || 0}
        </div>
      </div>
    </div>
  );
};

// Color definitions
const greenColor = 'var(--accent-green)';
const greenGlow = 'rgba(0, 255, 136, 0.08)';
const blueColor = 'var(--accent-blue)';
const blueGlow = 'rgba(77, 171, 247, 0.08)';
const amberColor = 'var(--accent-amber)';
const amberGlow = 'rgba(255, 184, 0, 0.08)';
const redColor = 'var(--accent-red)';
const redGlow = 'rgba(255, 71, 87, 0.08)';
const purpleColor = 'var(--accent-purple)';
const purpleGlow = 'rgba(177, 151, 252, 0.08)';

export const ActiveNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={greenColor}
    glow={greenGlow}
    handles={[
      { type: 'target', position: Position.Top, id: 'top-target' },
      { type: 'target', position: Position.Bottom, id: 'bottom-target' },
      { type: 'source', position: Position.Left, id: 'left-source' },
      { type: 'source', position: Position.Right, id: 'right-source' },
    ]}
  />
);

export const CompletedNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={blueColor}
    glow={blueGlow}
    handles={[{ type: 'target', position: Position.Right, id: 'right-target' }]}
  />
);

export const PrimaryQueueNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={greenColor}
    glow={greenGlow}
    handles={[
      { type: 'target', position: Position.Top, id: 'top-target' },
      { type: 'source', position: Position.Bottom, id: 'bottom-source' },
    ]}
  />
);

export const ScheduledQueueNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={purpleColor}
    glow={purpleGlow}
    handles={[
      { type: 'target', position: Position.Top, id: 'top-target' },
      { type: 'source', position: Position.Left, id: 'left-source' },
    ]}
  />
);

export const RetryNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={amberColor}
    glow={amberGlow}
    handles={[
      { type: 'target', position: Position.Right, id: 'right-target' },
      { type: 'source', position: Position.Top, id: 'top-source' },
    ]}
  />
);

export const FailedNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={amberColor}
    glow={amberGlow}
    handles={[
      { type: 'target', position: Position.Left, id: 'left-target' },
      { type: 'source', position: Position.Right, id: 'right-source' },
      { type: 'source', position: Position.Bottom, id: 'bottom-source' },
    ]}
  />
);

export const DeadLetterNode: React.FC<NodeProps> = ({ data }) => (
  <StatusNode
    data={data as unknown as StatusNodeData}
    color={redColor}
    glow={redGlow}
    handles={[{ type: 'target', position: Position.Left, id: 'left-target' }]}
  />
);
