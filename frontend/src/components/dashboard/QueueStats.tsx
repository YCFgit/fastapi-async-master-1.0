// frontend/src/components/dashboard/QueueStats.tsx
import React from 'react';
import { QueueStatus } from '../../lib/api';
import { useI18n } from '../../lib/i18n';
import { Inbox, RotateCcw, Clock, Skull, TrendingUp } from 'lucide-react';

interface QueueStatsProps {
  queueStatus: QueueStatus | null;
  isConnected: boolean;
}

const QueueStats: React.FC<QueueStatsProps> = ({ queueStatus }) => {
  const { t } = useI18n();
  const formatNumber = (num: number) => num.toLocaleString();

  const queues = [
    {
      label: t('queue.primary'),
      value: queueStatus?.queues.primary ?? 0,
      icon: Inbox,
      color: 'var(--accent-blue)',
      glow: 'var(--accent-blue-glow)',
      desc: t('queue.pendingTasks'),
    },
    {
      label: t('queue.retry'),
      value: queueStatus?.queues.retry ?? 0,
      icon: RotateCcw,
      color: 'var(--accent-amber)',
      glow: 'var(--accent-amber-glow)',
      desc: queueStatus ? t('queue.ratio', { val: (queueStatus.retry_ratio * 100).toFixed(0) }) : '...',
    },
    {
      label: t('queue.scheduled'),
      value: queueStatus?.queues.scheduled ?? 0,
      icon: Clock,
      color: 'var(--accent-purple)',
      glow: 'rgba(177, 151, 252, 0.15)',
      desc: t('queue.awaitingRetry'),
    },
    {
      label: t('queue.dlq'),
      value: queueStatus?.queues.dlq ?? 0,
      icon: Skull,
      color: 'var(--accent-red)',
      glow: 'var(--accent-red-glow)',
      desc: t('queue.deadLetters'),
    },
  ];

  const states = [
    { label: t('state.PENDING'), value: queueStatus?.states.PENDING ?? 0, color: 'var(--text-secondary)' },
    { label: t('state.ACTIVE'), value: queueStatus?.states.ACTIVE ?? 0, color: 'var(--accent-green)' },
    { label: t('state.COMPLETED'), value: queueStatus?.states.COMPLETED ?? 0, color: 'var(--accent-blue)' },
    { label: t('state.FAILED'), value: queueStatus?.states.FAILED ?? 0, color: 'var(--accent-amber)' },
    { label: t('state.DLQ'), value: queueStatus?.states.DLQ ?? 0, color: 'var(--accent-red)' },
  ];

  return (
    <div className="space-y-4">
      {/* Queue depths */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-4 h-4" style={{ color: 'var(--accent-green)' }} />
          <h3
            className="text-sm font-semibold"
            style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
          >
            {t('queue.depth')}
          </h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {queues.map(({ label, value, icon: Icon, color, glow, desc }) => (
            <div
              key={label}
              className="relative overflow-hidden rounded-xl p-4 transition-all duration-300 hover:scale-[1.02]"
              style={{
                background: `linear-gradient(135deg, ${glow}, transparent)`,
                border: `1px solid ${color}22`,
              }}
            >
              <Icon
                className="absolute -right-2 -bottom-2 w-16 h-16 opacity-[0.06]"
                style={{ color }}
              />

              <div className="relative">
                <div className="flex items-center gap-2 mb-2">
                  <Icon className="w-4 h-4" style={{ color }} />
                  <span
                    className="text-xs font-medium"
                    style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
                  >
                    {label}
                  </span>
                </div>
                <p
                  className="text-3xl font-bold data-value"
                  style={{ color, fontFamily: 'var(--font-mono)' }}
                >
                  {queueStatus ? formatNumber(value) : '--'}
                </p>
                <p
                  className="text-xs mt-1"
                  style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
                >
                  {desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* State distribution */}
      <div className="glass-card p-5">
        <h3
          className="text-sm font-semibold mb-4"
          style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
        >
          {t('queue.stateDist')}
        </h3>

        {/* Bar chart */}
        <div className="flex gap-1 h-8 rounded-lg overflow-hidden mb-3" style={{ background: 'var(--bg-tertiary)' }}>
          {states.map(({ label, value, color }) => {
            const total = states.reduce((s, st) => s + st.value, 0);
            const pct = total > 0 ? (value / total) * 100 : 0;
            if (pct === 0) return null;
            return (
              <div
                key={label}
                className="h-full transition-all duration-500 relative group"
                style={{
                  width: `${Math.max(pct, 2)}%`,
                  background: `linear-gradient(180deg, ${color}, ${color}88)`,
                }}
              >
                <div
                  className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-0.5 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-default)',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {label}: {value}
                </div>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4">
          {states.map(({ label, value, color }) => (
            <div key={label} className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-sm" style={{ background: color }} />
              <span
                className="text-xs"
                style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}
              >
                {label}:{' '}
                <span className="data-value font-medium" style={{ color: 'var(--text-primary)' }}>
                  {queueStatus ? formatNumber(value) : '--'}
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default QueueStats;
