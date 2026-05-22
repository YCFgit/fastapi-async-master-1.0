// frontend/src/pages/TaskTypeManager.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  TaskTypeConfig,
  TaskTypeConfigResponse,
  TaskTypeTestResult,
  AuthType,
} from '@/lib/types';
import {
  fetchTaskTypes,
  createTaskType,
  updateTaskType,
  deleteTaskType,
  activateTaskType,
  deactivateTaskType,
  testTaskType,
} from '@/lib/task-types-api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Settings, Plus, TestTube, Edit3, Power, Trash2, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useI18n } from '../lib/i18n';

// Terminal-style input
const TermInput: React.FC<React.InputHTMLAttributes<HTMLInputElement> & { label?: string }> = ({ label, ...props }) => (
  <div>
    {label && (
      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        {label}
      </label>
    )}
    <input
      {...props}
      style={{
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border-default)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        borderRadius: '8px',
        padding: '8px 12px',
        outline: 'none',
        width: '100%',
        transition: 'border-color 0.2s, box-shadow 0.2s',
        ...props.style,
      }}
      onFocus={(e) => {
        e.target.style.borderColor = 'var(--accent-green)';
        e.target.style.boxShadow = '0 0 0 2px var(--accent-green-glow)';
        props.onFocus?.(e);
      }}
      onBlur={(e) => {
        e.target.style.borderColor = 'var(--border-default)';
        e.target.style.boxShadow = 'none';
        props.onBlur?.(e);
      }}
    />
  </div>
);

// Terminal-style select
const TermSelect: React.FC<{
  label?: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}> = ({ label, value, onChange, options }) => (
  <div>
    {label && (
      <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
        {label}
      </label>
    )}
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--border-default)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-mono)',
        fontSize: '13px',
        borderRadius: '8px',
        padding: '8px 12px',
        outline: 'none',
        width: '100%',
        cursor: 'pointer',
        appearance: 'none' as const,
        backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%238b9ab5' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E")`,
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'right 12px center',
        paddingRight: '32px',
      }}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  </div>
);

const defaultFormData: TaskTypeConfig = {
  type_id: '',
  name: '',
  description: '',
  api_base_url: '',
  api_endpoint: '',
  http_method: 'POST',
  request_template: '',
  request_headers: {},
  response_jsonpath: '',
  response_parser: '',
  auth_type: AuthType.NONE,
  auth_config: {},
  timeout: 30,
  max_retries: 3,
  rate_limit_requests: undefined,
  rate_limit_interval: undefined,
  circuit_breaker_enabled: true,
  circuit_breaker_fail_max: undefined,
  circuit_breaker_reset_timeout: undefined,
  enabled: true,
};

const TaskTypeManager: React.FC = () => {
  const { t } = useI18n();
  const [taskTypes, setTaskTypes] = useState<TaskTypeConfigResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [editingType, setEditingType] = useState<TaskTypeConfigResponse | null>(null);
  const [formData, setFormData] = useState<TaskTypeConfig>({ ...defaultFormData });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [typeToDelete, setTypeToDelete] = useState<TaskTypeConfigResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  const [testModalOpen, setTestModalOpen] = useState(false);
  const [testResult, setTestResult] = useState<TaskTypeTestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [testTypeId, setTestTypeId] = useState<string | null>(null);

  const loadTaskTypes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTaskTypes(true);
      setTaskTypes(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadTaskTypes(); }, [loadTaskTypes]);

  const handleOpenCreate = () => {
    setEditingType(null);
    setFormData({ ...defaultFormData });
    setFormError(null);
    setFormOpen(true);
  };

  const handleOpenEdit = (taskType: TaskTypeConfigResponse) => {
    setEditingType(taskType);
    setFormData({
      ...taskType,
      auth_config: {},
      request_headers: taskType.request_headers || {},
    });
    setFormError(null);
    setFormOpen(true);
  };

  const handleFormChange = (field: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setFormError(null);
    try {
      if (editingType) {
        await updateTaskType(editingType.type_id, formData);
      } else {
        await createTaskType(formData);
      }
      setFormOpen(false);
      await loadTaskTypes();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to save task type');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!typeToDelete) return;
    setDeleting(true);
    try {
      await deleteTaskType(typeToDelete.type_id);
      setDeleteModalOpen(false);
      setTypeToDelete(null);
      await loadTaskTypes();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete task type');
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleActive = async (taskType: TaskTypeConfigResponse) => {
    try {
      if (taskType.enabled) {
        await deactivateTaskType(taskType.type_id);
      } else {
        await activateTaskType(taskType.type_id);
      }
      await loadTaskTypes();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to toggle task type status');
    }
  };

  const handleTest = async (typeId: string) => {
    setTestTypeId(typeId);
    setTestResult(null);
    setTesting(true);
    setTestModalOpen(true);
    try {
      const result = await testTaskType(typeId);
      setTestResult(result);
    } catch (err: unknown) {
      setTestResult({
        success: false,
        error: err instanceof Error ? err.message : 'Test failed',
      });
    } finally {
      setTesting(false);
    }
  };

  const getAuthColor = (authType: AuthType) => {
    const map: Record<string, string> = {
      NONE: 'var(--text-muted)',
      BEARER: 'var(--accent-blue)',
      API_KEY: 'var(--accent-purple)',
      BASIC: 'var(--accent-amber)',
    };
    return map[authType] || 'var(--text-muted)';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1
            className="text-xl font-bold"
            style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}
          >
            {t('types.title')}
          </h1>
          <Settings className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
        </div>
        <button
          onClick={handleOpenCreate}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200"
          style={{
            background: 'linear-gradient(135deg, var(--accent-green-dim), var(--accent-green))',
            color: '#000',
            fontFamily: 'var(--font-mono)',
            boxShadow: '0 0 16px rgba(0, 255, 136, 0.2)',
          }}
        >
          <Plus className="w-4 h-4" />
          {t('types.register')}
        </button>
      </div>

      {error && (
        <div
          className="flex items-center gap-2 px-4 py-3 rounded-lg"
          style={{
            background: 'var(--accent-red-glow)',
            border: '1px solid rgba(255,71,87,0.2)',
            color: 'var(--accent-red)',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
          }}
        >
          <XCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-8">
          <Loader2 className="w-8 h-8 mx-auto animate-spin" style={{ color: 'var(--accent-green)' }} />
          <p className="text-sm mt-2" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            {t('types.loading')}
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && (
        <div
          className="rounded-xl overflow-hidden"
          style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-dim)',
          }}
        >
          <table className="w-full text-sm" style={{ fontFamily: 'var(--font-mono)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-dim)' }}>
                <th className="px-4 py-3 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{t('types.typeId')}</th>
                <th className="px-4 py-3 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{t('types.name')}</th>
                <th className="px-4 py-3 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{t('types.method')}</th>
                <th className="px-4 py-3 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{t('types.auth')}</th>
                <th className="px-4 py-3 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{t('types.status')}</th>
                <th className="px-4 py-3 text-left text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{t('types.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {taskTypes.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-dim)' }}>
                    {t('types.empty')}
                  </td>
                </tr>
              ) : (
                taskTypes.map((taskType) => (
                  <tr
                    key={taskType.type_id}
                    className="transition-colors"
                    style={{ borderBottom: '1px solid var(--border-dim)' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td className="px-4 py-3 text-xs" style={{ color: 'var(--text-primary)' }}>
                      {taskType.type_id}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <div className="text-sm" style={{ color: 'var(--text-primary)' }}>{taskType.name}</div>
                        {taskType.description && (
                          <div className="text-xs mt-0.5 truncate max-w-xs" style={{ color: 'var(--text-dim)' }}>
                            {taskType.description}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs"
                        style={{
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border-default)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {taskType.http_method}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs"
                        style={{
                          background: `${getAuthColor(taskType.auth_type)}18`,
                          border: `1px solid ${getAuthColor(taskType.auth_type)}33`,
                          color: getAuthColor(taskType.auth_type),
                        }}
                      >
                        {taskType.auth_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs"
                        style={{
                          background: taskType.enabled ? 'var(--accent-green-glow)' : 'var(--bg-elevated)',
                          border: `1px solid ${taskType.enabled ? 'rgba(0,255,136,0.2)' : 'var(--border-default)'}`,
                          color: taskType.enabled ? 'var(--accent-green)' : 'var(--text-muted)',
                        }}
                      >
                        {taskType.enabled ? t('types.active') : t('types.inactive')}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleTest(taskType.type_id)}
                          disabled={testing && testTypeId === taskType.type_id}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                          style={{
                            background: 'var(--bg-elevated)',
                            border: '1px solid var(--border-default)',
                            color: 'var(--accent-blue)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {testing && testTypeId === taskType.type_id ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <TestTube className="w-3 h-3" />
                          )}
                          {t('types.test')}
                        </button>
                        <button
                          onClick={() => handleOpenEdit(taskType)}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                          style={{
                            background: 'var(--bg-elevated)',
                            border: '1px solid var(--border-default)',
                            color: 'var(--text-secondary)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          <Edit3 className="w-3 h-3" />
                          {t('types.edit')}
                        </button>
                        <button
                          onClick={() => handleToggleActive(taskType)}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                          style={{
                            background: taskType.enabled ? 'var(--accent-amber-glow)' : 'var(--accent-green-glow)',
                            border: `1px solid ${taskType.enabled ? 'rgba(255,184,0,0.2)' : 'rgba(0,255,136,0.2)'}`,
                            color: taskType.enabled ? 'var(--accent-amber)' : 'var(--accent-green)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          <Power className="w-3 h-3" />
                          {taskType.enabled ? t('types.deactivate') : t('types.activate')}
                        </button>
                        <button
                          onClick={() => { setTypeToDelete(taskType); setDeleteModalOpen(true); }}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                          style={{
                            background: 'var(--accent-red-glow)',
                            border: '1px solid rgba(255,71,87,0.2)',
                            color: 'var(--accent-red)',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create/Edit Form Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingType ? t('types.editTitle', { id: editingType.type_id }) : t('types.createTitle')}
            </DialogTitle>
            <DialogDescription>
              {editingType ? t('types.editDesc') : t('types.createDesc')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-4">
            {formError && (
              <div
                className="flex items-center gap-2 p-3 rounded-lg text-xs"
                style={{
                  background: 'var(--accent-red-glow)',
                  border: '1px solid rgba(255,71,87,0.2)',
                  color: 'var(--accent-red)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <XCircle className="w-4 h-4" />
                {formError}
              </div>
            )}

            {/* Basic Info */}
            <div>
              <h3 className="text-xs font-semibold mb-3" style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>
                {t('types.basicInfo')}
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <TermInput label={t('types.typeIdLabel')} value={formData.type_id} onChange={(e) => handleFormChange('type_id', e.target.value)} placeholder={t('types.placeholder.typeId')} disabled={!!editingType} />
                <TermInput label={t('types.nameLabel')} value={formData.name} onChange={(e) => handleFormChange('name', e.target.value)} placeholder={t('types.placeholder.name')} />
              </div>
              <div className="mt-3">
                <TermInput label={t('types.descLabel')} value={formData.description || ''} onChange={(e) => handleFormChange('description', e.target.value)} placeholder={t('types.placeholder.desc')} />
              </div>
            </div>

            {/* API Configuration */}
            <div style={{ borderTop: '1px solid var(--border-dim)', paddingTop: '16px' }}>
              <h3 className="text-xs font-semibold mb-3" style={{ color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>
                {t('types.apiConfig')}
              </h3>
              <div className="space-y-3">
                <TermInput label={t('types.baseUrlLabel')} value={formData.api_base_url} onChange={(e) => handleFormChange('api_base_url', e.target.value)} placeholder={t('types.placeholder.baseUrl')} />
                <div className="grid grid-cols-2 gap-4">
                  <TermInput label={t('types.endpointLabel')} value={formData.api_endpoint} onChange={(e) => handleFormChange('api_endpoint', e.target.value)} placeholder={t('types.placeholder.endpoint')} />
                  <TermSelect
                    label={t('types.methodLabel')}
                    value={formData.http_method}
                    onChange={(v) => handleFormChange('http_method', v)}
                    options={['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(m => ({ value: m, label: m }))}
                  />
                </div>
              </div>
            </div>

            {/* Authentication */}
            <div style={{ borderTop: '1px solid var(--border-dim)', paddingTop: '16px' }}>
              <h3 className="text-xs font-semibold mb-3" style={{ color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)' }}>
                {t('types.authentication')}
              </h3>
              <div className="space-y-3">
                <TermSelect
                  label={t('types.authTypeLabel')}
                  value={formData.auth_type}
                  onChange={(v) => handleFormChange('auth_type', v)}
                  options={Object.values(AuthType).map(t => ({ value: t, label: t }))}
                />
                {formData.auth_type === AuthType.BEARER && (
                  <TermInput label={t('types.bearerToken')} type="password" value={formData.auth_config?.token || ''} onChange={(e) => handleFormChange('auth_config', { token: e.target.value })} placeholder={t('types.placeholder.token')} />
                )}
                {formData.auth_type === AuthType.API_KEY && (
                  <div className="grid grid-cols-2 gap-4">
                    <TermInput label={t('types.headerName')} value={formData.auth_config?.header_name || ''} onChange={(e) => handleFormChange('auth_config', { ...formData.auth_config, header_name: e.target.value })} placeholder={t('types.placeholder.headerName')} />
                    <TermInput label={t('types.headerValue')} type="password" value={formData.auth_config?.header_value || ''} onChange={(e) => handleFormChange('auth_config', { ...formData.auth_config, header_value: e.target.value })} placeholder={t('types.placeholder.headerValue')} />
                  </div>
                )}
                {formData.auth_type === AuthType.BASIC && (
                  <div className="grid grid-cols-2 gap-4">
                    <TermInput label={t('types.username')} value={formData.auth_config?.username || ''} onChange={(e) => handleFormChange('auth_config', { ...formData.auth_config, username: e.target.value })} placeholder={t('types.username')} />
                    <TermInput label={t('types.password')} type="password" value={formData.auth_config?.password || ''} onChange={(e) => handleFormChange('auth_config', { ...formData.auth_config, password: e.target.value })} placeholder={t('types.password')} />
                  </div>
                )}
              </div>
            </div>

            {/* Template & Response */}
            <div style={{ borderTop: '1px solid var(--border-dim)', paddingTop: '16px' }}>
              <h3 className="text-xs font-semibold mb-3" style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)' }}>
                {t('types.templateResponse')}
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs mb-1.5" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {t('types.requestTemplate')}
                  </label>
                  <textarea
                    className="w-full rounded-lg text-xs"
                    rows={4}
                    value={formData.request_template || ''}
                    onChange={(e) => handleFormChange('request_template', e.target.value)}
                    placeholder={'{"text": "{{content}}", "target": "{{params.target_lang | default(\'en\')}}"}'}
                    style={{
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--border-default)',
                      color: 'var(--text-primary)',
                      fontFamily: 'var(--font-mono)',
                      padding: '8px 12px',
                      outline: 'none',
                      resize: 'vertical' as const,
                    }}
                  />
                  <p className="text-xs mt-1" style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                    {t('types.templateVars')}
                  </p>
                </div>
                <TermInput label={t('types.jsonpathLabel')} value={formData.response_jsonpath || ''} onChange={(e) => handleFormChange('response_jsonpath', e.target.value)} placeholder={t('types.placeholder.jsonpath')} />
              </div>
            </div>

            {/* Retry & Rate Limiting */}
            <div style={{ borderTop: '1px solid var(--border-dim)', paddingTop: '16px' }}>
              <h3 className="text-xs font-semibold mb-3" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>
                {t('types.retryRateLimit')}
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <TermInput label={t('types.maxRetries')} type="number" min={0} max={10} value={formData.max_retries} onChange={(e) => handleFormChange('max_retries', parseInt(e.target.value) || 0)} />
                <TermInput label={t('types.rateLimitReqs')} type="number" min={1} value={formData.rate_limit_requests || ''} onChange={(e) => handleFormChange('rate_limit_requests', e.target.value ? parseInt(e.target.value) : undefined)} placeholder={t('types.optional')} />
                <TermInput label={t('types.rateLimitInterval')} type="number" min={1} value={formData.rate_limit_interval || ''} onChange={(e) => handleFormChange('rate_limit_interval', e.target.value ? parseInt(e.target.value) : undefined)} placeholder={t('types.optional')} />
              </div>
            </div>
          </div>

          <DialogFooter>
            <button
              onClick={() => setFormOpen(false)}
              disabled={submitting}
              className="px-4 py-2 rounded-lg text-sm transition-all"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {t('types.cancel')}
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: submitting ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-green-dim), var(--accent-green))',
                color: submitting ? 'var(--text-muted)' : '#000',
                fontFamily: 'var(--font-mono)',
                boxShadow: submitting ? 'none' : '0 0 16px rgba(0,255,136,0.2)',
              }}
            >
              {submitting ? t('types.saving') : editingType ? t('types.update') : t('types.create')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('types.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('types.deleteConfirm')}{' '}
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-red)' }}>{typeToDelete?.type_id}</span>?
              <br /><br />
              {t('types.deleteDesc')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button
              onClick={() => setDeleteModalOpen(false)}
              disabled={deleting}
              className="px-4 py-2 rounded-lg text-sm transition-all"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {t('types.cancel')}
            </button>
            <button
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: deleting ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-red-dim), var(--accent-red))',
                color: deleting ? 'var(--text-muted)' : '#fff',
                fontFamily: 'var(--font-mono)',
                boxShadow: deleting ? 'none' : '0 0 16px rgba(255,71,87,0.2)',
              }}
            >
              {deleting ? t('types.deleting') : t('types.deleteTitle')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Result Modal */}
      <Dialog open={testModalOpen} onOpenChange={setTestModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('types.testTitle', { id: testTypeId || '' })}</DialogTitle>
            <DialogDescription>
              {testing ? t('types.testingDesc') : t('types.testDone')}
            </DialogDescription>
          </DialogHeader>

          {testing ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 mx-auto animate-spin" style={{ color: 'var(--accent-green)' }} />
              <p className="text-sm mt-2" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {t('types.sending')}
              </p>
            </div>
          ) : testResult ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{t('types.testStatus')}</span>
                <span
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                  style={{
                    background: testResult.success ? 'var(--accent-green-glow)' : 'var(--accent-red-glow)',
                    border: `1px solid ${testResult.success ? 'rgba(0,255,136,0.2)' : 'rgba(255,71,87,0.2)'}`,
                    color: testResult.success ? 'var(--accent-green)' : 'var(--accent-red)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {testResult.success ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                  {testResult.success ? t('types.testSuccess') : t('types.testFailed')}
                </span>
              </div>

              {testResult.status_code && (
                <div className="text-xs" style={{ fontFamily: 'var(--font-mono)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{t('types.httpStatus')} </span>
                  <span style={{ color: 'var(--text-primary)' }}>{testResult.status_code}</span>
                </div>
              )}

              {testResult.response_time_ms && (
                <div className="text-xs" style={{ fontFamily: 'var(--font-mono)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{t('types.responseTime')} </span>
                  <span style={{ color: 'var(--text-primary)' }}>{testResult.response_time_ms}ms</span>
                </div>
              )}

              {testResult.request_sent && (
                <div>
                  <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('types.requestSent')}</span>
                  <pre
                    className="rounded p-2 text-xs mt-1 overflow-auto"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-dim)',
                      color: 'var(--text-secondary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {JSON.stringify(testResult.request_sent, null, 2)}
                  </pre>
                </div>
              )}

              {testResult.extracted_result !== undefined && testResult.extracted_result !== null && (
                <div>
                  <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('types.extractedResult')}</span>
                  <pre
                    className="rounded p-2 text-xs mt-1 overflow-auto max-h-48"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-dim)',
                      color: 'var(--accent-green)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {JSON.stringify(testResult.extracted_result, null, 2)}
                  </pre>
                </div>
              )}

              {testResult.response_body != null && (
                <div>
                  <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('types.responseBody')}</span>
                  <pre
                    className="rounded p-2 text-xs mt-1 overflow-auto max-h-48"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-dim)',
                      color: 'var(--text-secondary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {typeof testResult.response_body === 'string'
                      ? testResult.response_body
                      : JSON.stringify(testResult.response_body, null, 2)}
                  </pre>
                </div>
              )}

              {testResult.error && (
                <div>
                  <span className="text-xs font-medium" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{t('types.testError')}</span>
                  <p className="text-xs mt-1" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{testResult.error}</p>
                </div>
              )}
            </div>
          ) : null}

          <DialogFooter>
            <button
              onClick={() => setTestModalOpen(false)}
              className="px-4 py-2 rounded-lg text-sm transition-all"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {t('types.close')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TaskTypeManager;
