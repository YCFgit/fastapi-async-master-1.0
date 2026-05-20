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
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';

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
  const [taskTypes, setTaskTypes] = useState<TaskTypeConfigResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formOpen, setFormOpen] = useState(false);
  const [editingType, setEditingType] = useState<TaskTypeConfigResponse | null>(null);
  const [formData, setFormData] = useState<TaskTypeConfig>({ ...defaultFormData });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Delete confirmation
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [typeToDelete, setTypeToDelete] = useState<TaskTypeConfigResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Test result
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

  useEffect(() => {
    loadTaskTypes();
  }, [loadTaskTypes]);

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

  const handleFormClose = () => {
    setFormOpen(false);
    setEditingType(null);
    setFormError(null);
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

  const handleDeleteClick = (taskType: TaskTypeConfigResponse) => {
    setTypeToDelete(taskType);
    setDeleteModalOpen(true);
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

  const renderAuthTypeBadge = (authType: AuthType) => {
    const colorMap: Record<AuthType, string> = {
      [AuthType.NONE]: 'bg-gray-500 border-gray-600',
      [AuthType.BEARER]: 'bg-blue-500 border-blue-600',
      [AuthType.API_KEY]: 'bg-purple-500 border-purple-600',
      [AuthType.BASIC]: 'bg-orange-500 border-orange-600',
    };
    return (
      <Badge className={`${colorMap[authType]} text-white border`}>{authType}</Badge>
    );
  };

  const renderStatusBadge = (enabled: boolean) => {
    return enabled ? (
      <Badge className="bg-green-500 border-green-600 text-white border">Active</Badge>
    ) : (
      <Badge className="bg-gray-500 border-gray-600 text-white border">Inactive</Badge>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Task Types</h1>
          <p className="text-sm text-gray-600 mt-1">
            Manage task type configurations for external API integrations
          </p>
        </div>
        <Button onClick={handleOpenCreate} className="bg-blue-600 hover:bg-blue-700 text-white">
          Register New Type
        </Button>
      </div>

      {/* Error display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="text-center py-8">
          <p className="text-gray-500">Loading task types...</p>
        </div>
      )}

      {/* Table */}
      {!loading && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Auth Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {taskTypes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    No task types registered. Click "Register New Type" to create one.
                  </TableCell>
                </TableRow>
              ) : (
                taskTypes.map((taskType) => (
                  <TableRow key={taskType.type_id}>
                    <TableCell className="font-mono text-sm">{taskType.type_id}</TableCell>
                    <TableCell>
                      <div>
                        <div className="font-medium">{taskType.name}</div>
                        {taskType.description && (
                          <div className="text-xs text-gray-500 mt-1 truncate max-w-xs">
                            {taskType.description}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono">
                        {taskType.http_method}
                      </Badge>
                    </TableCell>
                    <TableCell>{renderAuthTypeBadge(taskType.auth_type)}</TableCell>
                    <TableCell>{renderStatusBadge(taskType.enabled)}</TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleTest(taskType.type_id)}
                          disabled={testing && testTypeId === taskType.type_id}
                        >
                          {testing && testTypeId === taskType.type_id ? 'Testing...' : 'Test'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleOpenEdit(taskType)}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleActive(taskType)}
                          className={
                            taskType.enabled
                              ? 'text-orange-600 hover:text-orange-700 hover:bg-orange-50 border-orange-300'
                              : 'text-green-600 hover:text-green-700 hover:bg-green-50 border-green-300'
                          }
                        >
                          {taskType.enabled ? 'Deactivate' : 'Activate'}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteClick(taskType)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 border-red-300 hover:border-red-400"
                        >
                          Delete
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create/Edit Form Dialog */}
      <Dialog open={formOpen} onOpenChange={setFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingType ? `Edit Task Type: ${editingType.type_id}` : 'Register New Task Type'}
            </DialogTitle>
            <DialogDescription>
              {editingType
                ? 'Update the task type configuration below.'
                : 'Configure a new task type for external API integration.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {formError && (
              <div className="bg-red-50 border border-red-200 rounded p-3">
                <p className="text-red-700 text-sm">{formError}</p>
              </div>
            )}

            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Type ID *
                </label>
                <Input
                  value={formData.type_id}
                  onChange={(e) => handleFormChange('type_id', e.target.value)}
                  placeholder="e.g., translate"
                  disabled={!!editingType}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <Input
                  value={formData.name}
                  onChange={(e) => handleFormChange('name', e.target.value)}
                  placeholder="e.g., Text Translation"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <Input
                value={formData.description || ''}
                onChange={(e) => handleFormChange('description', e.target.value)}
                placeholder="Optional description"
              />
            </div>

            {/* API Configuration */}
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">API Configuration</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    API Base URL *
                  </label>
                  <Input
                    value={formData.api_base_url}
                    onChange={(e) => handleFormChange('api_base_url', e.target.value)}
                    placeholder="https://api.example.com"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Endpoint *
                    </label>
                    <Input
                      value={formData.api_endpoint}
                      onChange={(e) => handleFormChange('api_endpoint', e.target.value)}
                      placeholder="/v1/translate"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      HTTP Method
                    </label>
                    <Select
                      value={formData.http_method}
                      onValueChange={(value) => handleFormChange('http_method', value)}
                    >
                      <SelectTrigger className="bg-white border border-gray-300">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-white border border-gray-300 shadow-lg">
                        {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((method) => (
                          <SelectItem key={method} value={method}>
                            {method}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </div>

            {/* Authentication */}
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Authentication</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Auth Type
                  </label>
                  <Select
                    value={formData.auth_type}
                    onValueChange={(value) => handleFormChange('auth_type', value)}
                  >
                    <SelectTrigger className="bg-white border border-gray-300">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-white border border-gray-300 shadow-lg">
                      {Object.values(AuthType).map((type) => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {formData.auth_type === AuthType.BEARER && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Bearer Token
                    </label>
                    <Input
                      type="password"
                      value={formData.auth_config?.token || ''}
                      onChange={(e) =>
                        handleFormChange('auth_config', { token: e.target.value })
                      }
                      placeholder="Enter bearer token or ${ENV_VAR}"
                    />
                  </div>
                )}

                {formData.auth_type === AuthType.API_KEY && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Header Name
                      </label>
                      <Input
                        value={formData.auth_config?.header_name || ''}
                        onChange={(e) =>
                          handleFormChange('auth_config', {
                            ...formData.auth_config,
                            header_name: e.target.value,
                          })
                        }
                        placeholder="X-API-Key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Header Value
                      </label>
                      <Input
                        type="password"
                        value={formData.auth_config?.header_value || ''}
                        onChange={(e) =>
                          handleFormChange('auth_config', {
                            ...formData.auth_config,
                            header_value: e.target.value,
                          })
                        }
                        placeholder="Enter API key or ${ENV_VAR}"
                      />
                    </div>
                  </div>
                )}

                {formData.auth_type === AuthType.BASIC && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Username
                      </label>
                      <Input
                        value={formData.auth_config?.username || ''}
                        onChange={(e) =>
                          handleFormChange('auth_config', {
                            ...formData.auth_config,
                            username: e.target.value,
                          })
                        }
                        placeholder="Username"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Password
                      </label>
                      <Input
                        type="password"
                        value={formData.auth_config?.password || ''}
                        onChange={(e) =>
                          handleFormChange('auth_config', {
                            ...formData.auth_config,
                            password: e.target.value,
                          })
                        }
                        placeholder="Password"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Template & Response */}
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Template & Response
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Request Template (Jinja2)
                  </label>
                  <textarea
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
                    rows={4}
                    value={formData.request_template || ''}
                    onChange={(e) => handleFormChange('request_template', e.target.value)}
                    placeholder={'{"text": "{{content}}", "target": "{{params.target_lang | default(\'en\')}}"}'}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Variables: {'{{content}}'}, {'{{params.*}}'}, {'{{task_id}}'}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Response JSONPath
                  </label>
                  <Input
                    value={formData.response_jsonpath || ''}
                    onChange={(e) => handleFormChange('response_jsonpath', e.target.value)}
                    placeholder="$.data.result"
                  />
                </div>
              </div>
            </div>

            {/* Retry & Rate Limiting */}
            <div className="border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">
                Retry & Rate Limiting
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Retries
                  </label>
                  <Input
                    type="number"
                    min={0}
                    max={10}
                    value={formData.max_retries}
                    onChange={(e) =>
                      handleFormChange('max_retries', parseInt(e.target.value) || 0)
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Rate Limit Requests
                  </label>
                  <Input
                    type="number"
                    min={1}
                    value={formData.rate_limit_requests || ''}
                    onChange={(e) =>
                      handleFormChange(
                        'rate_limit_requests',
                        e.target.value ? parseInt(e.target.value) : undefined
                      )
                    }
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Rate Limit Interval (s)
                  </label>
                  <Input
                    type="number"
                    min={1}
                    value={formData.rate_limit_interval || ''}
                    onChange={(e) =>
                      handleFormChange(
                        'rate_limit_interval',
                        e.target.value ? parseInt(e.target.value) : undefined
                      )
                    }
                    placeholder="Optional"
                  />
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleFormClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {submitting
                ? 'Saving...'
                : editingType
                ? 'Update Task Type'
                : 'Create Task Type'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Modal */}
      <Dialog open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Task Type</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete task type{' '}
              <span className="font-mono text-sm">{typeToDelete?.type_id}</span>?
              <br />
              <br />
              This will permanently remove the task type configuration. Active tasks of this
              type will continue to process but new tasks cannot be submitted.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteModalOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteConfirm}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {deleting ? 'Deleting...' : 'Delete Task Type'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Result Modal */}
      <Dialog open={testModalOpen} onOpenChange={setTestModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Test Result: {testTypeId}</DialogTitle>
            <DialogDescription>
              {testing ? 'Testing task type configuration...' : 'Test completed'}
            </DialogDescription>
          </DialogHeader>

          {testing ? (
            <div className="text-center py-8">
              <p className="text-gray-500">Sending test request...</p>
            </div>
          ) : testResult ? (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <span className="font-medium">Status:</span>
                <Badge
                  className={
                    testResult.success
                      ? 'bg-green-500 border-green-600 text-white border'
                      : 'bg-red-500 border-red-600 text-white border'
                  }
                >
                  {testResult.success ? 'Success' : 'Failed'}
                </Badge>
              </div>

              {testResult.status_code && (
                <div>
                  <span className="font-medium">HTTP Status:</span>{' '}
                  <span className="font-mono">{testResult.status_code}</span>
                </div>
              )}

              {testResult.response_time_ms && (
                <div>
                  <span className="font-medium">Response Time:</span>{' '}
                  {testResult.response_time_ms}ms
                </div>
              )}

              {testResult.request_sent && (
                <div>
                  <span className="font-medium">Request Sent:</span>
                  <pre className="bg-gray-100 rounded p-2 text-xs mt-1 overflow-auto">
                    {JSON.stringify(testResult.request_sent, null, 2)}
                  </pre>
                </div>
              )}

              {testResult.extracted_result !== undefined && testResult.extracted_result !== null && (
                <div>
                  <span className="font-medium">Extracted Result:</span>
                  <pre className="bg-gray-100 rounded p-2 text-xs mt-1 overflow-auto max-h-48">
                    {JSON.stringify(testResult.extracted_result, null, 2)}
                  </pre>
                </div>
              )}

              {testResult.response_body && (
                <div>
                  <span className="font-medium">Response Body:</span>
                  <pre className="bg-gray-100 rounded p-2 text-xs mt-1 overflow-auto max-h-48">
                    {typeof testResult.response_body === 'string'
                      ? testResult.response_body
                      : JSON.stringify(testResult.response_body, null, 2)}
                  </pre>
                </div>
              )}

              {testResult.error && (
                <div>
                  <span className="font-medium text-red-600">Error:</span>
                  <p className="text-red-600 text-sm mt-1">{testResult.error}</p>
                </div>
              )}
            </div>
          ) : null}

          <DialogFooter>
            <Button variant="outline" onClick={() => setTestModalOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TaskTypeManager;
