// frontend/src/components/layout/Layout.tsx
import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, Clock, Trash2, Settings, Terminal, Zap, Globe } from 'lucide-react';
import { useI18n } from '../../lib/i18n';

const Layout: React.FC = () => {
  const { lang, setLang, t } = useI18n();

  const navItems = [
    { to: '/', icon: Activity, label: t('nav.dashboard') },
    { to: '/task-types', icon: Settings, label: t('nav.taskTypes') },
    { to: '/tasks-history', icon: Clock, label: t('nav.history') },
    { to: '/tasks-cleanup', icon: Trash2, label: t('nav.cleanup') },
  ];

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header
        className="sticky top-0 z-40"
        style={{
          background: 'var(--bg-secondary)',
          backdropFilter: 'blur(16px)',
          borderBottom: '1px solid var(--border-dim)',
        }}
      >
        <div className="w-full px-6 py-3 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, var(--accent-green-glow), var(--accent-blue-glow))',
                border: '1px solid var(--border-default)',
              }}
            >
              <Zap className="w-5 h-5" style={{ color: 'var(--accent-green)' }} />
            </div>
            <div>
              <h1
                className="text-lg font-bold tracking-tight leading-none"
                style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
              >
                {t('app.name')}
              </h1>
              <p
                className="text-xs mt-0.5"
                style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
              >
                <Terminal className="w-3 h-3 inline mr-1" style={{ verticalAlign: '-2px' }} />
                {t('app.version')}
              </p>
            </div>
          </div>

          {/* Right side: status + language switcher */}
          <div className="flex items-center gap-4">
            {/* System status */}
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full animate-pulse-glow"
                style={{ background: 'var(--accent-green)' }}
              />
              <span
                className="text-xs"
                style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}
              >
                {t('system.online')}
              </span>
            </div>

            {/* Language switcher */}
            <button
              onClick={() => setLang(lang === 'en' ? 'zh' : 'en')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all duration-200 hover:opacity-80"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
                cursor: 'pointer',
              }}
              title={lang === 'en' ? '切换到中文' : 'Switch to English'}
            >
              <Globe className="w-3.5 h-3.5" style={{ color: 'var(--accent-blue)' }} />
              {lang === 'en' ? '中文' : 'EN'}
            </button>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav
        style={{
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-dim)',
        }}
      >
        <div className="w-full px-6">
          <div className="flex gap-1">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all duration-200 relative ${
                    isActive ? '' : 'hover:bg-black/[0.04]'
                  }`
                }
                style={({ isActive }) => ({
                  color: isActive ? 'var(--accent-green)' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-sans)',
                  borderBottom: isActive ? '2px solid var(--accent-green)' : '2px solid transparent',
                  background: isActive ? 'var(--accent-green-glow)' : 'transparent',
                })}
              >
                <Icon className="w-4 h-4" />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 w-full px-6 py-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer
        className="py-3 px-6 text-center"
        style={{
          borderTop: '1px solid var(--border-dim)',
          background: 'var(--bg-secondary)',
        }}
      >
        <p
          className="text-xs"
          style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}
        >
          {t('app.footer')}
        </p>
      </footer>
    </div>
  );
};

export default Layout;
