// frontend/src/components/dashboard/WorkerStats.tsx
import React, { useState, useEffect, useRef } from 'react';
import { apiService, WorkerStatus, WorkerDetail } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { Server, WifiOff, Loader2, AlertCircle, Zap, CheckCircle, XCircle } from 'lucide-react';

interface WorkerStatsProps {
  isConnected: boolean;
}

const WorkerStats: React.FC<WorkerStatsProps> = ({ isConnected }) => {
  const { t } = useI18n();
  const [workerStatus, setWorkerStatus] = useState<WorkerStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const initialLoadRef = useRef<boolean>(true);

  useEffect(() => {
    const fetchWorkerStats = async () => {
      if (!isConnected) {
        if (initialLoadRef.current) setLoading(false);
        return;
      }
      try {
        if (initialLoadRef.current) setLoading(true);
        else setIsUpdating(true);
        setError(null);
        const response = await apiService.getWorkerStatus();
        setWorkerStatus(response);
        if (initialLoadRef.current) initialLoadRef.current = false;
      } catch (err) {
        console.error('Failed to fetch worker stats:', err);
        setError('Failed to load worker statistics');
        setWorkerStatus(null);
      } finally {
        setLoading(false);
        setIsUpdating(false);
      }
    };
    fetchWorkerStats();
    const interval = isConnected ? setInterval(fetchWorkerStats, 30000) : null;
    return () => { if (interval) clearInterval(interval); };
  }, [isConnected]);

  const getStatusStyle = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy': return { color: 'var(--accent-green)', bg: 'var(--accent-green-glow)', border: 'rgba(0,255,136,0.2)' };
      case 'stale': return { color: 'var(--accent-amber)', bg: 'var(--accent-amber-glow)', border: 'rgba(255,184,0,0.2)' };
      case 'no_heartbeat': case 'error': case 'unhealthy': return { color: 'var(--accent-red)', bg: 'var(--accent-red-glow)', border: 'rgba(255,71,87,0.2)' };
      default: return { color: 'var(--text-muted)', bg: 'var(--bg-tertiary)', border: 'var(--border-default)' };
    }
  };

  const getCircuitBreakerStyle = (state: string) => {
    switch (state.toLowerCase()) {
      case 'closed': return { color: 'var(--accent-green)', bg: 'var(--accent-green-glow)', border: 'rgba(0,255,136,0.2)' };
      case 'half-open': return { color: 'var(--accent-amber)', bg: 'var(--accent-amber-glow)', border: 'rgba(255,184,0,0.2)' };
      case 'open': return { color: 'var(--accent-red)', bg: 'var(--accent-red-glow)', border: 'rgba(255,71,87,0.2)' };
      default: return { color: 'var(--text-muted)', bg: 'var(--bg-tertiary)', border: 'var(--border-default)' };
    }
  };

  const formatLastHeartbeat = (worker: WorkerDetail) => {
    const heartbeat = worker.last_heartbeat || worker.timestamp;
    if (!heartbeat) return 'Never';
    try {
      const timestamp = isNaN(Number(heartbeat)) ? heartbeat : Number(heartbeat) * 1000;
      return new Date(timestamp).toLocaleTimeString();
    } catch { return 'Unknown'; }
  };

  if (!isConnected) {
    return (
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{t('worker.title')}</h3>
        </div>
        <div className="text-center py-8">
          <WifiOff className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-dim)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.noConnection')}</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{t('worker.title')}</h3>
        </div>
        <div className="text-center py-8">
          <Loader2 className="w-8 h-8 mx-auto animate-spin" style={{ color: 'var(--accent-green)' }} />
          <p className="text-sm mt-2" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{t('worker.title')}</h3>
        </div>
        <div className="text-center py-8">
          <AlertCircle className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--accent-red)' }} />
          <p className="text-sm" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{t('worker.title')}</h3>
        </div>
        {isUpdating && (
          <div className="flex items-center gap-2">
            <Loader2 className="w-3 h-3 animate-spin" style={{ color: 'var(--accent-green)' }} />
            <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.updating')}</span>
          </div>
        )}
      </div>

      {workerStatus && (
        <div className="mb-5 p-4 rounded-lg" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-dim)' }}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold data-value" style={{ color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>{workerStatus.total_workers}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.total')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold data-value" style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>{workerStatus.healthy_workers}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.healthy')}</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold data-value" style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)' }}>{workerStatus.stale_workers}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.stale')}</div>
            </div>
            <div className="text-center">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium" style={{
                background: workerStatus.overall_status === 'healthy' ? 'var(--accent-green-glow)' : 'var(--accent-amber-glow)',
                border: `1px solid ${workerStatus.overall_status === 'healthy' ? 'rgba(0,255,136,0.2)' : 'rgba(255,184,0,0.2)'}`,
                color: workerStatus.overall_status === 'healthy' ? 'var(--accent-green)' : 'var(--accent-amber)',
                fontFamily: 'var(--font-mono)',
              }}>
                {workerStatus.overall_status.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      )}

      {!workerStatus || !workerStatus.worker_details || workerStatus.worker_details.length === 0 ? (
        <div className="text-center py-8">
          <Server className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-dim)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.noWorkers')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {workerStatus.worker_details.map((worker: WorkerDetail) => {
            const statusStyle = getStatusStyle(worker.status);
            const cbStyle = getCircuitBreakerStyle(worker.circuit_breaker.state);
            return (
              <div key={worker.worker_id} className="rounded-lg p-4" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-dim)' }}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Zap className="w-4 h-4" style={{ color: statusStyle.color }} />
                    <span className="font-medium text-sm truncate" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                      {worker.worker_name || worker.worker_id}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style={{ background: statusStyle.bg, border: `1px solid ${statusStyle.border}`, color: statusStyle.color, fontFamily: 'var(--font-mono)' }}>
                      {worker.status}
                    </span>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style={{ background: cbStyle.bg, border: `1px solid ${cbStyle.border}`, color: cbStyle.color, fontFamily: 'var(--font-mono)' }}>
                      CB: {worker.circuit_breaker.state}
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                    {t('worker.lastSeen', { val: formatLastHeartbeat(worker) })}
                  </span>
                </div>
                {worker.error && (
                  <div className="mb-3 p-2 rounded text-xs" style={{ background: 'var(--accent-red-glow)', border: '1px solid rgba(255,71,87,0.2)', color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>
                    {worker.error}
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
                    <CheckCircle className="w-4 h-4" style={{ color: 'var(--accent-green)' }} />
                    <div>
                      <div className="text-lg font-bold data-value" style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>{worker.circuit_breaker.success_count || 0}</div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.success')}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
                    <XCircle className="w-4 h-4" style={{ color: 'var(--accent-red)' }} />
                    <div>
                      <div className="text-lg font-bold data-value" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{worker.circuit_breaker.fail_count || 0}</div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('worker.fail')}</div>
                    </div>
                  </div>
                </div>
                {worker.circuit_breaker.note && (
                  <div className="mt-3 p-2 rounded text-xs" style={{ background: 'var(--accent-blue-glow)', border: '1px solid rgba(77,171,247,0.2)', color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>
                    NOTE: {worker.circuit_breaker.note}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default WorkerStats;
