// frontend/src/lib/types.ts
// TypeScript types matching the backend Pydantic schemas

export enum TaskState {
  PENDING = "PENDING",
  ACTIVE = "ACTIVE",
  COMPLETED = "COMPLETED",
  FAILED = "FAILED",
  SCHEDULED = "SCHEDULED",
  DLQ = "DLQ",
}

export enum AuthType {
  NONE = "none",
  BEARER = "bearer",
  API_KEY = "api_key",
  BASIC = "basic",
}

export interface TaskTypeConfig {
  type_id: string;
  name: string;
  description?: string;
  api_base_url: string;
  api_endpoint: string;
  http_method: string;
  request_template?: string;
  request_headers?: Record<string, string>;
  response_jsonpath?: string;
  error_jsonpath?: string;
  status_jsonpath?: string;
  response_parser?: string;
  auth_type: AuthType;
  auth_config?: Record<string, string>;
  timeout: number;
  max_retries: number;
  retry_on_status?: string;
  retry_schedule?: string;
  rate_limit_requests?: number;
  rate_limit_interval?: number;
  circuit_breaker_enabled: boolean;
  circuit_breaker_fail_max?: number;
  circuit_breaker_reset_timeout?: number;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TaskTypeConfigResponse {
  type_id: string;
  name: string;
  description?: string;
  api_base_url: string;
  api_endpoint: string;
  http_method: string;
  request_template?: string;
  request_headers?: Record<string, string>;
  response_jsonpath?: string;
  error_jsonpath?: string;
  status_jsonpath?: string;
  response_parser?: string;
  auth_type: AuthType;
  timeout: number;
  max_retries: number;
  retry_on_status?: string;
  retry_schedule?: string;
  rate_limit_requests?: number;
  rate_limit_interval?: number;
  circuit_breaker_enabled: boolean;
  circuit_breaker_fail_max?: number;
  circuit_breaker_reset_timeout?: number;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface TaskTypeTestResult {
  success: boolean;
  status_code?: number;
  response_time_ms?: number;
  request_sent?: Record<string, unknown>;
  response_body?: unknown;
  extracted_result?: unknown;
  error?: string;
}

export interface TaskSubmitRequest {
  task_type: string;
  content: string;
  params?: Record<string, unknown>;
  callback_url?: string;
  priority?: number;
}

export interface TaskResponse {
  task_id: string;
  state: TaskState;
}

export interface TaskDetail {
  task_id: string;
  state: TaskState;
  task_type?: string;
  content: string;
  params?: Record<string, unknown>;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  error_type?: string;
  http_status?: number;
  retry_after?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  result?: unknown;
  error_history: Record<string, unknown>[];
  state_history: Record<string, unknown>[];
}

export interface TaskSummary {
  task_id: string;
  state: TaskState;
  task_type?: string;
  retry_count: number;
  max_retries: number;
  last_error?: string;
  error_type?: string;
  http_status?: number;
  retry_after?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  content_length?: number;
  has_result: boolean;
  error_history: Record<string, unknown>[];
  state_history: Record<string, unknown>[];
}

export interface TaskListResponse {
  tasks: TaskDetail[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  status?: TaskState;
}

export interface TaskSummaryListResponse {
  tasks: TaskSummary[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  status?: TaskState;
}

export interface QueueStatus {
  queues: Record<string, number>;
  states: Record<string, number>;
  retry_ratio: number;
}

export interface HealthStatus {
  status: string;
  components: Record<string, unknown>;
  note?: string;
  timestamp: string;
}

export interface SSEMessage {
  type: string;
  queue_depths?: Record<string, number>;
  state_counts?: Record<string, number>;
  retry_ratio?: number;
  message?: string;
}

export interface CircuitBreakerStatus {
  state: string;
  fail_count?: number;
  success_count?: number;
  note?: string;
  container_id?: string;
}

export interface WorkerDetail {
  worker_id: string;
  worker_name?: string;
  status: string;
  circuit_breaker: CircuitBreakerStatus;
  last_heartbeat?: string | number;
  timestamp?: string | number;
  error?: string;
}

export interface WorkerStatus {
  total_workers: number;
  healthy_workers: number;
  stale_workers: number;
  overall_status: string;
  worker_details: WorkerDetail[];
}
