// frontend/src/lib/task-types-api.ts
// API functions for task type management

import {
  TaskTypeConfig,
  TaskTypeConfigResponse,
  TaskTypeTestResult,
} from './types';

const API_BASE = '/api/v1/task-types';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

export async function fetchTaskTypes(
  includeInactive: boolean = true
): Promise<TaskTypeConfigResponse[]> {
  const params = new URLSearchParams();
  params.append('include_inactive', String(includeInactive));

  return fetchJson<TaskTypeConfigResponse[]>(`${API_BASE}/?${params.toString()}`);
}

export async function fetchTaskType(typeId: string): Promise<TaskTypeConfigResponse> {
  return fetchJson<TaskTypeConfigResponse>(`${API_BASE}/${typeId}`);
}

export async function createTaskType(
  config: TaskTypeConfig
): Promise<TaskTypeConfigResponse> {
  return fetchJson<TaskTypeConfigResponse>(`${API_BASE}/`, {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export async function updateTaskType(
  typeId: string,
  config: TaskTypeConfig
): Promise<TaskTypeConfigResponse> {
  return fetchJson<TaskTypeConfigResponse>(`${API_BASE}/${typeId}`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

export async function deleteTaskType(typeId: string): Promise<void> {
  await fetch(`${API_BASE}/${typeId}`, {
    method: 'DELETE',
  });
}

export async function activateTaskType(typeId: string): Promise<TaskTypeConfigResponse> {
  return fetchJson<TaskTypeConfigResponse>(`${API_BASE}/${typeId}/activate`, {
    method: 'POST',
  });
}

export async function deactivateTaskType(typeId: string): Promise<TaskTypeConfigResponse> {
  return fetchJson<TaskTypeConfigResponse>(`${API_BASE}/${typeId}/deactivate`, {
    method: 'POST',
  });
}

export async function testTaskType(typeId: string): Promise<TaskTypeTestResult> {
  return fetchJson<TaskTypeTestResult>(`${API_BASE}/${typeId}/test`, {
    method: 'POST',
  });
}
