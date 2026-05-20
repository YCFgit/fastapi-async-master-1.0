// frontend/src/lib/tasks-api.ts
// API functions for task management

import {
  TaskSubmitRequest,
  TaskResponse,
  TaskDetail,
  TaskListResponse,
  TaskSummaryListResponse,
} from './types';

const API_BASE = '/api/v1/tasks';

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

export async function submitTask(request: TaskSubmitRequest): Promise<TaskResponse> {
  return fetchJson<TaskResponse>(`${API_BASE}/submit`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function fetchTaskSummaries(
  params: Record<string, unknown> = {}
): Promise<TaskSummaryListResponse> {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  const url = `${API_BASE}/summaries/${queryString ? `?${queryString}` : ''}`;

  return fetchJson<TaskSummaryListResponse>(url);
}

export async function fetchTasks(
  params: Record<string, unknown> = {}
): Promise<TaskListResponse> {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  const url = `${API_BASE}/${queryString ? `?${queryString}` : ''}`;

  return fetchJson<TaskListResponse>(url);
}

export async function fetchTaskDetail(taskId: string): Promise<TaskDetail> {
  return fetchJson<TaskDetail>(`${API_BASE}/${taskId}`);
}

export async function deleteTask(taskId: string): Promise<{ task_id: string; message: string }> {
  return fetchJson<{ task_id: string; message: string }>(`${API_BASE}/${taskId}`, {
    method: 'DELETE',
  });
}

export async function retryTask(
  taskId: string,
  resetRetryCount: boolean = false
): Promise<TaskResponse> {
  return fetchJson<TaskResponse>(`${API_BASE}/${taskId}/retry`, {
    method: 'POST',
    body: JSON.stringify({ reset_retry_count: resetRetryCount }),
  });
}
