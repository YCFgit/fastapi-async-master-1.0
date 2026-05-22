// frontend/src/pages/Dashboard.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { QueueStatus, SSEMessage, apiService } from '../lib/api';
import { TaskTypeConfigResponse } from '../lib/types';
import { fetchTaskTypes } from '../lib/task-types-api';
import { submitTask } from '../lib/tasks-api';
import { useI18n } from '../lib/i18n';
import TaskFlowGraph from '../components/dashboard/TaskFlowGraph';
import QueueStats from '../components/dashboard/QueueStats';
import WorkerStats from '../components/dashboard/WorkerStats';
import {
  Send,
  Loader2,
  CheckCircle2,
  XCircle,
  Wifi,
  WifiOff,
  AlertTriangle,
  ChevronRight,
} from 'lucide-react';

const Dashboard: React.FC = () => {
  const { t } = useI18n();
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [gatewayHealthy, setGatewayHealthy] = useState<boolean | null>(null);

  // Submit task state
  const [taskTypes, setTaskTypes] = useState<TaskTypeConfigResponse[]>([]);
  const [submitTaskType, setSubmitTaskType] = useState<string>('');
  const [submitContent, setSubmitContent] = useState<string>('');
  const [submitParams, setSubmitParams] = useState<string>('{}');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submitResult, setSubmitResult] = useState<{ success: boolean; message: string } | null>(null);

  const loadTaskTypes = useCallback(async () => {
    try {
      const types = await fetchTaskTypes(false);
      setTaskTypes(types);
      if (types.length > 0 && !submitTaskType) {
        setSubmitTaskType(types[0].type_id);
      }
    } catch (error) {
      console.error('Failed to fetch task types:', error);
    }
  }, [submitTaskType]);

  useEffect(() => {
    loadTaskTypes();
  }, [loadTaskTypes]);

  const handleSubmitTask = async () => {
    if (!submitTaskType || !submitContent.trim()) {
      setSubmitResult({ success: false, message: t('submit.error.empty') });
      return;
    }

    let params: Record<string, unknown> | undefined;
    try {
      params = submitParams.trim() ? JSON.parse(submitParams) : undefined;
    } catch {
      setSubmitResult({ success: false, message: t('submit.error.invalidJson') });
      return;
    }

    setSubmitting(true);
    setSubmitResult(null);

    try {
      const result = await submitTask({
        task_type: submitTaskType,
        content: submitContent,
        params,
      });
      setSubmitResult({
        success: true,
        message: `Task submitted: ${result.task_id}`,
      });
      setSubmitContent('');
      setSubmitParams('{}');
    } catch (err: unknown) {
      setSubmitResult({
        success: false,
        message: err instanceof Error ? err.message : t('submit.error.failed'),
      });
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const health = await apiService.getHealth();
        setGatewayHealthy(health.status === 'healthy');
      } catch {
        setGatewayHealthy(false);
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let eventSource: EventSource | null = null;

    const connectSSE = () => {
      try {
        eventSource = apiService.createSSEConnection(
          (data: SSEMessage) => {
            setLastUpdate(new Date());
            switch (data.type) {
              case 'initial_status':
              case 'queue_update':
                if (data.queue_depths && data.state_counts && data.retry_ratio !== undefined) {
                  setQueueStatus({
                    queues: data.queue_depths,
                    states: data.state_counts,
                    retry_ratio: data.retry_ratio,
                  });
                }
                setIsConnected(true);
                break;
              case 'heartbeat':
                setLastUpdate(new Date());
                setIsConnected(true);
                break;
              case 'fatal_error':
                setIsConnected(false);
                break;
            }
          },
          () => {
            setIsConnected(false);
            setTimeout(() => {
              if (eventSource?.readyState === EventSource.CLOSED) connectSSE();
            }, 5000);
          }
        );
        eventSource.onopen = () => setIsConnected(true);
      } catch {
        setIsConnected(false);
      }
    };

    connectSSE();
    return () => { if (eventSource) eventSource.close(); };
  }, []);

  const inputStyle: React.CSSProperties = {
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-default)',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
    fontSize: '13px',
    borderRadius: '8px',
    padding: '10px 14px',
    outline: 'none',
    width: '100%',
    transition: 'border-color 0.2s, box-shadow 0.2s',
  };

  const inputFocusStyle: React.CSSProperties = {
    borderColor: 'var(--accent-green)',
    boxShadow: '0 0 0 2px var(--accent-green-glow)',
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Status bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1
            className="text-xl font-bold"
            style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
          >
            {t('dashboard.title')}
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {/* Connection status */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs"
            style={{
              background: isConnected ? 'var(--accent-green-glow)' : 'var(--accent-red-glow)',
              border: `1px solid ${isConnected ? 'rgba(0,255,136,0.2)' : 'rgba(255,71,87,0.2)'}`,
              fontFamily: 'var(--font-mono)',
              color: isConnected ? 'var(--accent-green)' : 'var(--accent-red)',
            }}
          >
            {isConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {isConnected ? t('status.live') : t('status.offline')}
          </div>

          {/* Gateway status */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs"
            style={{
              background:
                gatewayHealthy === null
                  ? 'var(--bg-tertiary)'
                  : gatewayHealthy
                  ? 'var(--accent-green-glow)'
                  : 'var(--accent-red-glow)',
              border: `1px solid ${
                gatewayHealthy === null
                  ? 'var(--border-default)'
                  : gatewayHealthy
                  ? 'rgba(0,255,136,0.2)'
                  : 'rgba(255,71,87,0.2)'
              }`,
              fontFamily: 'var(--font-mono)',
              color:
                gatewayHealthy === null
                  ? 'var(--text-muted)'
                  : gatewayHealthy
                  ? 'var(--accent-green)'
                  : 'var(--accent-red)',
            }}
          >
            {gatewayHealthy === null ? '...' : gatewayHealthy ? t('status.healthy') : t('status.unhealthy')}
          </div>

          {/* Last update */}
          {lastUpdate && (
            <span
              className="text-xs"
              style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
            >
              {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Submit Task Card */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Send className="w-4 h-4" style={{ color: 'var(--accent-green)' }} />
          <h3
            className="text-sm font-semibold"
            style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
          >
            {t('submit.title')}
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
          {/* Task Type */}
          <div className="md:col-span-3">
            <label
              className="block text-xs mb-1.5"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            >
              {t('submit.typeId')}
            </label>
            <select
              style={{
                ...inputStyle,
                cursor: 'pointer',
                appearance: 'none' as const,
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238b9ab5' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
                backgroundRepeat: 'no-repeat',
                backgroundPosition: 'right 12px center',
                paddingRight: '32px',
              }}
              value={submitTaskType}
              onChange={(e) => setSubmitTaskType(e.target.value)}
            >
              {taskTypes.length === 0 ? (
                <option value="">{t('submit.noTypes')}</option>
              ) : (
                taskTypes.map((type) => (
                  <option key={type.type_id} value={type.type_id}>
                    {type.type_id}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Content */}
          <div className="md:col-span-5">
            <label
              className="block text-xs mb-1.5"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            >
              {t('submit.content')}
            </label>
            <textarea
              style={{ ...inputStyle, resize: 'vertical' as const, minHeight: '42px' }}
              rows={1}
              value={submitContent}
              onChange={(e) => setSubmitContent(e.target.value)}
              placeholder={t('submit.contentPlaceholder')}
              onFocus={(e) => Object.assign(e.target.style, inputFocusStyle)}
              onBlur={(e) => {
                e.target.style.borderColor = 'var(--border-default)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Params */}
          <div className="md:col-span-2">
            <label
              className="block text-xs mb-1.5"
              style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
            >
              {t('submit.params')}
            </label>
            <input
              type="text"
              style={inputStyle}
              value={submitParams}
              onChange={(e) => setSubmitParams(e.target.value)}
              placeholder={t('submit.paramsPlaceholder')}
              onFocus={(e) => Object.assign(e.target.style, inputFocusStyle)}
              onBlur={(e) => {
                e.target.style.borderColor = 'var(--border-default)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          {/* Submit button */}
          <div className="md:col-span-2 flex flex-col">
            <label className="block text-xs mb-1.5 invisible" style={{ fontFamily: 'var(--font-mono)' }}>&nbsp;</label>
            <button
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200"
              style={{
                background: submitting
                  ? 'var(--bg-tertiary)'
                  : 'linear-gradient(135deg, var(--accent-green-dim), var(--accent-green))',
                color: submitting ? 'var(--text-muted)' : '#000',
                fontFamily: 'var(--font-mono)',
                cursor: submitting || taskTypes.length === 0 ? 'not-allowed' : 'pointer',
                opacity: submitting || taskTypes.length === 0 ? 0.5 : 1,
                boxShadow: submitting ? 'none' : '0 0 16px rgba(0, 255, 136, 0.2)',
              }}
              onClick={handleSubmitTask}
              disabled={submitting || taskTypes.length === 0}
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              {submitting ? t('submit.sending') : t('submit.execute')}
            </button>
          </div>
        </div>

        {/* Result */}
        {submitResult && (
          <div
            className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg text-xs animate-fade-in"
            style={{
              background: submitResult.success ? 'var(--accent-green-glow)' : 'var(--accent-red-glow)',
              border: `1px solid ${submitResult.success ? 'rgba(0,255,136,0.2)' : 'rgba(255,71,87,0.2)'}`,
              color: submitResult.success ? 'var(--accent-green)' : 'var(--accent-red)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            {submitResult.success ? (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 flex-shrink-0" />
            )}
            <span className="truncate">{submitResult.message}</span>
          </div>
        )}
      </div>

      {/* Queue Stats */}
      <QueueStats queueStatus={queueStatus} isConnected={isConnected} />

      {/* Task Flow Graph */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <ChevronRight className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
          <h3
            className="text-sm font-semibold"
            style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
          >
            {t('flow.title')}
          </h3>
        </div>
        <TaskFlowGraph queueStatus={queueStatus} />
      </div>

      {/* Worker Stats */}
      <WorkerStats isConnected={isConnected} />

      {/* Connection warning */}
      {!isConnected && (
        <div
          className="flex items-center gap-3 px-4 py-3 rounded-lg animate-fade-in"
          style={{
            background: 'var(--accent-amber-glow)',
            border: '1px solid rgba(255, 184, 0, 0.2)',
          }}
        >
          <AlertTriangle className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--accent-amber)' }} />
          <div>
            <p
              className="text-sm font-medium"
              style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)' }}
            >
              {t('connection.lost')}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              {t('connection.lostDesc')}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
