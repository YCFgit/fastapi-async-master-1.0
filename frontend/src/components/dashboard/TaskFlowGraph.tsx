// frontend/src/components/dashboard/TaskFlowGraph.tsx
import React, { useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ReactFlow, Node, Edge, addEdge, Connection,
  useNodesState, useEdgesState, Controls, Background, BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { QueueStatus } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { ActiveNode, CompletedNode, PrimaryQueueNode, ScheduledQueueNode, RetryNode, FailedNode, DeadLetterNode } from './CustomNodes';

const nodeTypes = {
  active: ActiveNode, completed: CompletedNode, primaryQueue: PrimaryQueueNode,
  scheduledQueue: ScheduledQueueNode, retry: RetryNode, failed: FailedNode, deadLetter: DeadLetterNode,
};

interface TaskFlowGraphProps { queueStatus: QueueStatus | null; }

const TaskFlowGraph: React.FC<TaskFlowGraphProps> = ({ queueStatus }) => {
  const navigate = useNavigate();
  const { t } = useI18n();

  const getFilterParams = (nodeId: string): string => {
    const filterMap: Record<string, string> = {
      completed: 'status=COMPLETED', failed: 'status=FAILED', active: 'status=ACTIVE',
      primaryQueue: 'queue=primary', scheduledQueue: 'queue=scheduled',
      retryQueue: 'queue=retry', deadLetter: 'status=DLQ',
    };
    return filterMap[nodeId] || '';
  };

  const getNodeCount = useCallback((nodeId: string): number => {
    if (!queueStatus) return 0;
    const countMap: Record<string, number> = {
      completed: queueStatus.states.COMPLETED || 0, failed: queueStatus.states.FAILED || 0,
      active: queueStatus.states.ACTIVE || 0, primaryQueue: queueStatus.queues.primary || 0,
      scheduledQueue: queueStatus.queues.scheduled || 0, retryQueue: queueStatus.queues.retry || 0,
      deadLetter: queueStatus.queues.dlq || 0,
    };
    return countMap[nodeId] || 0;
  }, [queueStatus]);

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    const count = getNodeCount(node.id);
    if (count > 0) {
      const filterParams = getFilterParams(node.id);
      if (filterParams) navigate(`/tasks-history?${filterParams}`);
    }
  }, [navigate, getNodeCount]);

  const initialNodes: Node[] = useMemo(() => [
    {
      id: 'submit', type: 'input', position: { x: 330, y: 50 },
      data: { label: <div className="text-center"><div className="text-xs font-medium" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('flow.submit')}</div></div> },
      style: { background: 'linear-gradient(135deg, rgba(77,171,247,0.15), var(--bg-tertiary))', border: '1px solid rgba(77,171,247,0.3)', borderRadius: '8px', width: 140, height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', boxShadow: '0 0 12px rgba(77,171,247,0.1)' },
    },
    { id: 'primaryQueue', type: 'primaryQueue', position: { x: 330, y: 150 }, data: { label: t('flow.primary'), count: queueStatus?.queues.primary || 0 } },
    { id: 'active', type: 'active', position: { x: 330, y: 250 }, data: { label: t('flow.active'), count: queueStatus?.states.ACTIVE || 0 } },
    { id: 'completed', type: 'completed', position: { x: 100, y: 250 }, data: { label: t('flow.completed'), count: queueStatus?.states.COMPLETED || 0 } },
    { id: 'failed', type: 'failed', position: { x: 560, y: 250 }, data: { label: t('flow.failed'), count: queueStatus?.states.FAILED || 0 } },
    { id: 'deadLetter', type: 'deadLetter', position: { x: 790, y: 250 }, data: { label: t('flow.deadLetter'), count: queueStatus?.queues.dlq || 0 } },
    { id: 'scheduledQueue', type: 'scheduledQueue', position: { x: 560, y: 400 }, data: { label: t('flow.scheduled'), count: queueStatus?.queues.scheduled || 0 } },
    { id: 'retryQueue', type: 'retry', position: { x: 330, y: 400 }, data: { label: t('flow.retry'), count: queueStatus?.queues.retry || 0 } },
  ], [queueStatus, t]);

  const initialEdges: Edge[] = useMemo(() => [
    { id: 'submit-primary', source: 'submit', target: 'primaryQueue', targetHandle: 'top-target', animated: true, style: { stroke: '#4dabf7', strokeWidth: 2, strokeDasharray: '5,5' } },
    { id: 'primary-active', source: 'primaryQueue', sourceHandle: 'bottom-source', target: 'active', targetHandle: 'top-target', animated: true, style: { stroke: '#00ff88', strokeWidth: 2 } },
    { id: 'active-completed', source: 'active', sourceHandle: 'left-source', target: 'completed', targetHandle: 'right-target', animated: true, style: { stroke: '#4dabf7', strokeWidth: 2 } },
    { id: 'active-failed', source: 'active', sourceHandle: 'right-source', target: 'failed', targetHandle: 'left-target', animated: true, style: { stroke: '#ffb800', strokeWidth: 2 } },
    { id: 'failed-scheduled', source: 'failed', sourceHandle: 'bottom-source', target: 'scheduledQueue', targetHandle: 'top-target', animated: true, style: { stroke: '#b197fc', strokeWidth: 2, strokeDasharray: '5,5' } },
    { id: 'failed-deadLetter', source: 'failed', sourceHandle: 'right-source', target: 'deadLetter', targetHandle: 'left-target', animated: true, style: { stroke: '#ff4757', strokeWidth: 2, strokeDasharray: '5,5' } },
    { id: 'scheduled-retry', source: 'scheduledQueue', sourceHandle: 'left-source', target: 'retryQueue', targetHandle: 'right-target', animated: true, style: { stroke: '#ffb800', strokeWidth: 2, strokeDasharray: '5,5' } },
    { id: 'retry-active', source: 'retryQueue', sourceHandle: 'top-source', target: 'active', targetHandle: 'bottom-target', animated: true, style: { stroke: '#ffb800', strokeWidth: 2, strokeDasharray: '5,5' } },
  ], []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  React.useEffect(() => { setNodes(initialNodes); }, [initialNodes, setNodes]);

  return (
    <div className="h-96 w-full rounded-lg overflow-hidden" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-dim)' }}>
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect} onNodeClick={handleNodeClick} fitView attributionPosition="bottom-left" style={{ background: 'transparent' }}>
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="var(--border-dim)" />
      </ReactFlow>
    </div>
  );
};

export default TaskFlowGraph;
