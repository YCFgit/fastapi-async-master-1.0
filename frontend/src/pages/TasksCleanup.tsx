// frontend/src/pages/TasksCleanup.tsx
import React from 'react';
import { Trash2, AlertTriangle, Database } from 'lucide-react';
import { useI18n } from '../lib/i18n';

const TasksCleanup: React.FC = () => {
  const { t } = useI18n();

  const features = [
    { icon: Database, title: t('cleanup.dataTitle'), desc: t('cleanup.dataDesc'), color: 'var(--accent-blue)' },
    { icon: AlertTriangle, title: t('cleanup.dlqTitle'), desc: t('cleanup.dlqDesc'), color: 'var(--accent-amber)' },
    { icon: Trash2, title: t('cleanup.bulkTitle'), desc: t('cleanup.bulkDesc'), color: 'var(--accent-red)' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
          {t('cleanup.title')}
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {t('cleanup.desc')}
        </p>
      </div>

      <div className="glass-card p-8">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-14 w-14 rounded-xl" style={{ background: 'var(--accent-red-glow)', border: '1px solid rgba(255,71,87,0.2)' }}>
            <Trash2 className="h-7 w-7" style={{ color: 'var(--accent-red)' }} />
          </div>
          <h3 className="mt-4 text-lg font-semibold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {t('cleanup.heading')}
          </h3>
          <p className="mt-2 text-sm max-w-sm mx-auto" style={{ color: 'var(--text-secondary)' }}>
            {t('cleanup.description')}
          </p>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
            {features.map(({ icon: Icon, title, desc, color }) => (
              <div key={title} className="rounded-lg p-4 transition-all duration-200 hover:scale-[1.02]" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-dim)' }}>
                <Icon className="h-5 w-5 mx-auto mb-2" style={{ color }} />
                <h4 className="text-sm font-medium" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{title}</h4>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium" style={{ background: 'var(--accent-blue-glow)', border: '1px solid rgba(77,171,247,0.2)', color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>
              {t('cleanup.comingSoon')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TasksCleanup;
