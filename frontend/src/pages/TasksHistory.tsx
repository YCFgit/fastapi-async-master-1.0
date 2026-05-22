// frontend/src/pages/TasksHistory.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { fetchTaskSummaries, fetchTaskDetail, deleteTask } from '@/lib/tasks-api';
import { fetchTaskTypes } from '@/lib/task-types-api';
import { TaskSummary, TaskSummaryListResponse, TaskDetail, TaskState, TaskTypeConfigResponse } from '@/lib/types';
import { useI18n } from '@/lib/i18n';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { format } from 'date-fns';
import { ChevronUp, Clock, Search, Trash2, Eye, EyeOff } from 'lucide-react';

const inputStyle: React.CSSProperties = {
  background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)',
  color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '13px',
  borderRadius: '8px', padding: '8px 12px', outline: 'none', transition: 'border-color 0.2s, box-shadow 0.2s',
};

const TasksHistory: React.FC = () => {
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tasksResponse, setTasksResponse] = useState<TaskSummaryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState<TaskSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null);
  const [expandedTaskDetail, setExpandedTaskDetail] = useState<TaskDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [taskTypes, setTaskTypes] = useState<TaskTypeConfigResponse[]>([]);

  const [filters, setFilters] = useState({
    task_id: searchParams.get('task_id') || '',
    status: searchParams.get('status') || 'all',
    task_type: searchParams.get('task_type') || 'all',
    page: parseInt(searchParams.get('page') || '1', 10),
  });

  const loadTasks = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const filterParams: Record<string, unknown> = { ...filters, page_size: 10, sort_by: 'created_at', sort_order: 'desc' };
      if (filters.status === 'all' || filters.status === '') filterParams.status = undefined;
      if (filters.task_type === 'all' || filters.task_type === '') filterParams.task_type = undefined;
      if (filters.task_id && filters.task_id.trim().length > 0) filterParams.task_id = filters.task_id.trim();
      else filterParams.task_id = undefined;
      const data = await fetchTaskSummaries(filterParams);
      setTasksResponse(data);
    } catch (err: unknown) { setError(err instanceof Error ? err.message : 'An error occurred'); }
    finally { setLoading(false); }
  }, [filters]);

  useEffect(() => {
    loadTasks();
    setSearchParams(Object.fromEntries(Object.entries(filters).map(([key, value]) => [key, String(value)])));
  }, [loadTasks, filters, setSearchParams]);

  useEffect(() => {
    const loadTaskTypes = async () => {
      try { setTaskTypes(await fetchTaskTypes(false)); } catch (e) { console.error('Failed to load task types:', e); }
    };
    loadTaskTypes();
  }, []);

  const handleFilterChange = (key: string, value: string | number) => setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));
  const handlePageChange = (newPage: number) => setFilters((prev) => ({ ...prev, page: newPage }));
  const shouldShowPagination = useMemo(() => tasksResponse && tasksResponse.total_pages > 1, [tasksResponse]);

  const getStateColor = (state: TaskState): string => {
    const map: Record<string, string> = { PENDING: 'var(--text-muted)', ACTIVE: 'var(--accent-green)', COMPLETED: 'var(--accent-blue)', FAILED: 'var(--accent-amber)', SCHEDULED: 'var(--accent-purple)', DLQ: 'var(--accent-red)' };
    return map[state] || 'var(--text-muted)';
  };

  const renderStateBadge = (state: TaskState) => {
    const color = getStateColor(state);
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style={{ background: `${color}18`, border: `1px solid ${color}33`, color, fontFamily: 'var(--font-mono)' }}>{t(`state.${state}`)}</span>;
  };

  const getTaskType = (task: TaskSummary) => task.task_type || 'summarize';

  const renderTaskTypeBadge = (taskType: string) => {
    const typeConfig = taskTypes.find((t) => t.type_id === taskType);
    return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium" style={{ background: 'var(--accent-blue-glow)', border: '1px solid rgba(77,171,247,0.2)', color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>{typeConfig ? typeConfig.name : taskType}</span>;
  };

  const calculateDuration = (task: TaskSummary | TaskDetail): string => {
    if (task.completed_at) return `${((new Date(task.completed_at).getTime() - new Date(task.created_at).getTime()) / 1000).toFixed(1)}s`;
    return 'N/A';
  };

  const handleDeleteConfirm = async () => {
    if (!taskToDelete) return;
    setDeleting(true);
    try { await deleteTask(taskToDelete.task_id); setDeleteModalOpen(false); setTaskToDelete(null); await loadTasks(); }
    catch (err: unknown) { setError(err instanceof Error ? err.message : 'Failed to delete task'); }
    finally { setDeleting(false); }
  };

  const toggleTaskDetails = async (taskId: string) => {
    if (expandedTaskId === taskId) { setExpandedTaskId(null); setExpandedTaskDetail(null); }
    else {
      setExpandedTaskId(taskId); setLoadingDetail(true);
      try { setExpandedTaskDetail(await fetchTaskDetail(taskId)); }
      catch (err: unknown) { setError(err instanceof Error ? err.message : 'Failed to fetch task details'); }
      finally { setLoadingDetail(false); }
    }
  };

  const renderTaskDetailsCard = (task: TaskSummary) => {
    if (expandedTaskId !== task.task_id) return null;
    return (
      <TableRow>
        <TableCell colSpan={6} className="p-0">
          <div className="p-6 space-y-6" style={{ background: 'var(--bg-tertiary)', borderTop: '1px solid var(--border-dim)' }}>
            <div className="flex justify-between items-center pb-4" style={{ borderBottom: '1px solid var(--border-dim)' }}>
              <h4 className="font-semibold text-sm" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{t('history.taskDetails')}</h4>
              <button onClick={() => { setExpandedTaskId(null); setExpandedTaskDetail(null); }} className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                <ChevronUp className="w-3 h-3" /> {t('history.collapse')}
              </button>
            </div>
            {loadingDetail ? (
              <div className="text-center py-8"><p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('history.loadingDetails')}</p></div>
            ) : expandedTaskDetail ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pb-4" style={{ borderBottom: '1px solid var(--border-dim)' }}>
                  <div>
                    <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>{t('history.taskInfo')}</h5>
                    <div className="space-y-2 text-xs" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.typeLabel')}</span> {expandedTaskDetail.task_type || 'N/A'}</div>
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.contentLabel')}</span> {expandedTaskDetail.content?.length || 0} chars</div>
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.hasResult')}</span> {expandedTaskDetail.result ? 'Yes' : 'No'}</div>
                    </div>
                  </div>
                  <div>
                    <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>{t('history.timing')}</h5>
                    <div className="space-y-2 text-xs" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.createdLabel')}</span> {format(new Date(expandedTaskDetail.created_at), 'PPpp')}</div>
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.updatedLabel')}</span> {format(new Date(expandedTaskDetail.updated_at), 'PPpp')}</div>
                      {expandedTaskDetail.completed_at && <div><span style={{ color: 'var(--text-muted)' }}>{t('history.completedLabel')}</span> {format(new Date(expandedTaskDetail.completed_at), 'PPpp')}</div>}
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.durationLabel')}</span> {calculateDuration(expandedTaskDetail)}</div>
                    </div>
                  </div>
                  <div>
                    <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-mono)' }}>{t('history.retryInfo')}</h5>
                    <div className="space-y-2 text-xs" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      <div><span style={{ color: 'var(--text-muted)' }}>{t('history.retryLabel')}</span> {expandedTaskDetail.retry_count} / {expandedTaskDetail.max_retries}</div>
                      {expandedTaskDetail.last_error && <div><span style={{ color: 'var(--text-muted)' }}>{t('history.errorLabel')}</span> <span style={{ color: 'var(--accent-red)' }}>{expandedTaskDetail.last_error}</span></div>}
                    </div>
                  </div>
                  <div>
                    <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-purple)', fontFamily: 'var(--font-mono)' }}>{t('history.params')}</h5>
                    {expandedTaskDetail.params && Object.keys(expandedTaskDetail.params).length > 0 ? (
                      <pre className="rounded p-2 text-xs overflow-auto max-h-32" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{JSON.stringify(expandedTaskDetail.params, null, 2)}</pre>
                    ) : <span className="text-xs" style={{ color: 'var(--text-dim)' }}>{t('history.noParams')}</span>}
                  </div>
                </div>
                <div>
                  <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>{t('history.stateHistory')}</h5>
                  <div className="rounded-md p-4 max-h-48 overflow-y-auto" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)' }}>
                    <div className="space-y-2">
                      {expandedTaskDetail.state_history.map((entry, index) => (
                        <div key={index} className="flex items-center justify-between py-1" style={{ borderBottom: index < expandedTaskDetail.state_history.length - 1 ? '1px solid var(--border-dim)' : 'none' }}>
                          <div>{renderStateBadge(entry.state as TaskState)}</div>
                          <span className="text-xs" style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>{format(new Date(entry.timestamp as string), 'PPpp')}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                {expandedTaskDetail.error_history && expandedTaskDetail.error_history.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{t('history.errorHistory')}</h5>
                    <div className="space-y-3">
                      {expandedTaskDetail.error_history.map((error, index) => (
                        <div key={index} className="p-3 rounded-md" style={{ background: 'var(--accent-red-glow)', border: '1px solid rgba(255,71,87,0.2)' }}>
                          <div className="text-xs"><div className="font-medium" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>Error #{index + 1}</div>
                          <pre className="text-xs mt-1 whitespace-pre-wrap" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{JSON.stringify(error, null, 2)}</pre></div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {expandedTaskDetail.state === TaskState.COMPLETED && expandedTaskDetail.result && (
                  <div>
                    <h5 className="font-semibold text-xs mb-3" style={{ color: 'var(--accent-green)', fontFamily: 'var(--font-mono)' }}>{t('history.taskResult')}</h5>
                    <div className="rounded-md p-4 max-h-64 overflow-y-auto" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-dim)' }}>
                      <pre className="text-sm whitespace-pre-wrap" style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{String(expandedTaskDetail.result)}</pre>
                    </div>
                  </div>
                )}
              </>
            ) : <div className="text-center py-8"><p style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{t('history.failedDetails')}</p></div>}
          </div>
        </TableCell>
      </TableRow>
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{t('history.title')}</h1>
        <Clock className="w-4 h-4" style={{ color: 'var(--accent-blue)' }} />
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          <input placeholder={t('history.search')} value={filters.task_id} onChange={(e) => handleFilterChange('task_id', e.target.value)} style={{ ...inputStyle, maxWidth: '320px' }} />
        </div>
        <Select value={filters.status} onValueChange={(v: string) => handleFilterChange('status', v)}>
          <SelectTrigger className="w-[180px]" style={{ ...inputStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' } as React.CSSProperties}><SelectValue placeholder={t('history.filterStatus')} /></SelectTrigger>
          <SelectContent style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '8px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 9999 }}>
            <SelectItem value="all" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{t('history.allStatuses')}</SelectItem>
            {Object.values(TaskState).map((state) => <SelectItem key={state} value={state} style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{t(`state.${state}`)}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filters.task_type} onValueChange={(v: string) => handleFilterChange('task_type', v)}>
          <SelectTrigger className="w-[180px]" style={{ ...inputStyle, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' } as React.CSSProperties}><SelectValue placeholder={t('history.filterType')} /></SelectTrigger>
          <SelectContent style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', borderRadius: '8px', boxShadow: '0 8px 32px rgba(0,0,0,0.5)', zIndex: 9999 }}>
            <SelectItem value="all" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{t('history.allTypes')}</SelectItem>
            {taskTypes.map((type) => <SelectItem key={type.type_id} value={type.type_id} style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>{type.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {loading && <p className="text-sm" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('history.loading')}</p>}
      {error && <p className="text-sm" style={{ color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>{error}</p>}

      {tasksResponse && (
        <>
          <div className="rounded-xl overflow-hidden" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-dim)' }}>
            <Table>
              <TableHeader>
                <TableRow style={{ borderBottom: '1px solid var(--border-dim)' }}>
                  <TableHead style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{t('history.taskId')}</TableHead>
                  <TableHead style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{t('history.status')}</TableHead>
                  <TableHead style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{t('history.type')}</TableHead>
                  <TableHead style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{t('history.created')}</TableHead>
                  <TableHead style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{t('history.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasksResponse.tasks.map((task: TaskSummary) => (
                  <React.Fragment key={task.task_id}>
                    <TableRow style={{ borderBottom: '1px solid var(--border-dim)', background: expandedTaskId === task.task_id ? 'var(--bg-elevated)' : 'transparent' }}>
                      <TableCell><span className="text-xs" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{task.task_id.substring(0, 8)}...</span></TableCell>
                      <TableCell>{renderStateBadge(task.state)}</TableCell>
                      <TableCell>{renderTaskTypeBadge(getTaskType(task))}</TableCell>
                      <TableCell><span className="text-xs" style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{format(new Date(task.created_at), 'MMM dd HH:mm')}</span></TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          <button onClick={() => toggleTaskDetails(task.task_id)} className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                            {expandedTaskId === task.task_id ? <><EyeOff className="w-3 h-3" /> {t('history.hide')}</> : <><Eye className="w-3 h-3" /> {t('history.view')}</>}
                          </button>
                          <button onClick={() => { setTaskToDelete(task); setDeleteModalOpen(true); }} className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ background: 'var(--accent-red-glow)', border: '1px solid rgba(255,71,87,0.2)', color: 'var(--accent-red)', fontFamily: 'var(--font-mono)' }}>
                            <Trash2 className="w-3 h-3" /> {t('history.delete')}
                          </button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {renderTaskDetailsCard(task)}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-xs" style={{ color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              {(() => {
                const total = tasksResponse.total_items; const onPage = tasksResponse.tasks.length; const pg = tasksResponse.page; const sz = tasksResponse.page_size;
                if (total === 0) return t('history.noTasks');
                const start = ((pg - 1) * sz) + 1; const end = start + onPage - 1;
                if (onPage === 1) return t('history.showingSingle', { start, total });
                return t('history.showingRange', { start, end, total });
              })()}
            </p>
            {shouldShowPagination && (
              <div className="flex items-center gap-2">
                <button onClick={() => handlePageChange(filters.page - 1)} disabled={filters.page <= 1} className="px-3 py-1.5 rounded-lg text-xs" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: filters.page <= 1 ? 'var(--text-dim)' : 'var(--text-primary)', fontFamily: 'var(--font-mono)', cursor: filters.page <= 1 ? 'not-allowed' : 'pointer', opacity: filters.page <= 1 ? 0.5 : 1 }}>{t('history.previous')}</button>
                <span className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t('history.pageInfo', { current: filters.page, total: tasksResponse.total_pages })}</span>
                <button onClick={() => handlePageChange(filters.page + 1)} disabled={filters.page >= tasksResponse.total_pages} className="px-3 py-1.5 rounded-lg text-xs" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-default)', color: filters.page >= tasksResponse.total_pages ? 'var(--text-dim)' : 'var(--text-primary)', fontFamily: 'var(--font-mono)', cursor: filters.page >= tasksResponse.total_pages ? 'not-allowed' : 'pointer', opacity: filters.page >= tasksResponse.total_pages ? 0.5 : 1 }}>{t('history.next')}</button>
              </div>
            )}
          </div>
        </>
      )}

      <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('history.deleteTitle')}</DialogTitle>
            <DialogDescription>{t('history.deleteConfirm')} <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-red)' }}>{taskToDelete?.task_id}</span>?<br /><br />{t('history.deleteDesc')}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <button onClick={() => setDeleteModalOpen(false)} disabled={deleting} className="px-4 py-2 rounded-lg text-sm" style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{t('history.cancel')}</button>
            <button onClick={handleDeleteConfirm} disabled={deleting} className="px-4 py-2 rounded-lg text-sm font-medium" style={{ background: deleting ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, var(--accent-red-dim), var(--accent-red))', color: deleting ? 'var(--text-muted)' : '#fff', fontFamily: 'var(--font-mono)', boxShadow: deleting ? 'none' : '0 0 16px rgba(255,71,87,0.2)' }}>{deleting ? t('history.deleting') : t('history.deleteTitle')}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TasksHistory;
