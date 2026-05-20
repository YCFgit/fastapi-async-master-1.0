// frontend/src/lib/api.ts
// API service for AsyncTaskFlow

import {
  QueueStatus,
  SSEMessage,
  HealthStatus,
  WorkerStatus,
  WorkerDetail,
} from './types';

const API_BASE = '/api/v1';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  private async fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${url}`, {
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

  // Health
  async getHealth(): Promise<HealthStatus> {
    return this.fetchJson<HealthStatus>('/health');
  }

  // Worker Status
  async getWorkerStatus(): Promise<WorkerStatus> {
    return this.fetchJson<WorkerStatus>(`${API_BASE}/workers/`);
  }

  // Queue Status
  async getQueueStatus(): Promise<QueueStatus> {
    return this.fetchJson<QueueStatus>(`${API_BASE}/queues/status`);
  }

  // SSE Connection
  createSSEConnection(
    onMessage: (data: SSEMessage) => void,
    onError: (error: Event) => void
  ): EventSource {
    const eventSource = new EventSource(`${this.baseUrl}${API_BASE}/queues/status/stream`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEMessage;
        onMessage(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = (error) => {
      onError(error);
    };

    return eventSource;
  }
}

export const apiService = ApiService.prototype ? new ApiService() : new ApiService();

export type { QueueStatus, SSEMessage, HealthStatus, WorkerStatus, WorkerDetail };
