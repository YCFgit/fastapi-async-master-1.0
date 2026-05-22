# AsyncTaskFlow v1.0

> 通用 API 任务网关 —— 注册任意 HTTP API，异步提交、可靠执行、自动重试

[English](./README.md) | **中文**

---

## 简介

AsyncTaskFlow 是一个**生产级分布式 API 任务处理系统**。你可以将任意 HTTP API 注册为"任务类型"，然后通过 REST 接口或 Web 界面异步提交任务。系统会自动处理队列调度、限流、重试、熔断等复杂逻辑，让你专注于业务本身。

### 核心特性

- **通用 API 网关** — 支持任意 HTTP API（GET/POST/PUT/PATCH/DELETE），通过 Jinja2 模板 + JSONPath 灵活配置
- **多级队列** — 主队列 → 重试队列 → 调度队列 → 死信队列，完整的任务生命周期管理
- **分布式限流** — 基于 Redis 令牌桶，按任务类型独立限流
- **熔断保护** — 按任务类型隔离的熔断器，防止雪崩
- **优先级调度** — 0-10 级优先级，紧急任务优先处理
- **实时监控** — SSE 推送 + React 仪表盘，实时掌握系统状态
- **中英双语** — 前端界面支持中文/英文切换

### 技术栈

| 层级 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **任务队列** | Celery + Redis |
| **前端** | React + Vite + TypeScript + Tailwind CSS |
| **容器化** | Docker Compose（6 个服务） |
| **数据存储** | Redis 7 |

---

## 快速开始

### 前置条件

- Docker 20.10+
- Docker Compose v2+

### 安装与启动

```bash
# 1. 克隆项目
git clone <repo-url>
cd fastapi-async-master-1.0

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 设置你的 API Key 等配置（可选，使用默认值即可启动）

# 3. 启动所有服务
docker compose up -d --build

# 4. 查看服务状态
docker compose ps
```

### 访问系统

| 地址 | 说明 |
|------|------|
| `http://localhost:3000` | 前端管理界面 |
| `http://localhost:8000/docs` | API 文档（Swagger UI） |
| `http://localhost:8000/health` | 健康检查 |

### 验证安装

```bash
# 检查健康状态
curl http://localhost:8000/health

# 注册一个测试任务类型
curl -X POST http://localhost:8000/api/v1/task-types \
  -H "Content-Type: application/json" \
  -d '{
    "type_id": "httpbin_get",
    "name": "HTTPBin GET Test",
    "api_base_url": "https://httpbin.org",
    "api_endpoint": "/get",
    "http_method": "GET",
    "response_jsonpath": "$.url",
    "max_retries": 2,
    "enabled": true
  }'

# 提交一个测试任务
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "httpbin_get",
    "content": "test content"
  }'

# 查看任务结果
curl http://localhost:8000/api/v1/tasks?task_type=httpbin_get
```

---

## 架构概览

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Frontend   │────▶│   FastAPI    │────▶│    Redis 7    │
│  React/Vite  │     │   REST API   │     │  数据 + 队列   │
│  (port 3000) │     │  (port 8000) │     │  (port 6379)  │
└─────────────┘     └──────────────┘     └──┬────┬────┬──┘
                                            │    │    │
                         ┌──────────────────┘    │    └──────────────┐
                         │                       │                   │
                   ┌─────▼──────┐  ┌─────────────▼──┐  ┌───────────▼───┐
                   │  Consumer   │  │  Worker × 3    │  │  Scheduler    │
                   │  (BLPOP)    │  │  (Celery)      │  │  (Celery Beat)│
                   └─────┬──────┘  └───────┬────────┘  └───────────────┘
                         │                 │
                         └────────┬────────┘
                                  │
                          ┌───────▼───────┐
                          │  HTTP 调用     │
                          │  (外部 API)    │
                          └───────────────┘
```

### 服务组成

| 服务 | 数量 | 说明 |
|------|------|------|
| `redis` | 1 | Redis 7，数据持久化，队列存储 |
| `api` | 1 | FastAPI REST 服务，处理所有 API 请求 |
| `frontend` | 1 | React SPA，Nginx 托管 |
| `worker` | 3 | Celery Worker，执行 HTTP 调用 |
| `scheduler` | 1 | Celery Beat，定时处理重试任务 |
| `reset` | 0 | 工具服务，用于重置 Redis 数据 |

---

## 核心概念

### 任务类型（Task Type）

任务类型定义了"如何调用一个外部 API"。包含：

- API 地址和端点
- HTTP 方法和请求模板（Jinja2）
- 认证方式（Bearer/API Key/Basic）
- 响应提取规则（JSONPath）
- 重试策略和限流配置

### 任务生命周期

```
提交 ──▶ PENDING ──▶ ACTIVE ──▶ COMPLETED
              │          │
              │          └──▶ FAILED ──▶ SCHEDULED ──▶ PENDING (重试)
              │                          │
              │                          └──▶ DLQ (重试耗尽)
              │
              └──▶ DLQ (永久错误/依赖错误)
```

| 状态 | 说明 |
|------|------|
| `PENDING` | 等待执行 |
| `ACTIVE` | 正在执行 |
| `COMPLETED` | 执行成功 |
| `FAILED` | 执行失败（可重试） |
| `SCHEDULED` | 等待重试（延迟中） |
| `DLQ` | 死信（重试耗尽或永久错误） |

### 错误分类

| 错误类型 | 示例 | 处理方式 |
|---------|------|---------|
| **永久错误** | 400, 401, 403, 404, 422 | 直接进入 DLQ |
| **临时错误** | 429, 500, 502, 503, 504 | 进入重试队列 |
| **依赖错误** | 网络超时、DNS 失败、连接拒绝 | 进入 DLQ |

---

## 前端界面

### 仪表盘

- 系统状态总览（SSE 实时连接）
- 快速提交任务表单
- 队列深度统计卡片
- 任务流程可视化图（React Flow）
- Worker 节点状态面板

### 任务类型管理

- 创建/编辑/删除任务类型
- 一键测试配置是否正确
- 激活/停用切换

### 任务历史

- 按状态、类型、ID 搜索过滤
- 分页浏览
- 展开查看详情（时间线、错误记录、结果数据）
- 删除任务

### 中英文切换

点击右上角 🌐 按钮即可切换中英文界面，语言偏好自动保存。

---

## API 接口

### 任务类型

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/task-types` | 列出所有任务类型 |
| `POST` | `/api/v1/task-types` | 创建任务类型 |
| `GET` | `/api/v1/task-types/{type_id}` | 获取任务类型详情 |
| `PUT` | `/api/v1/task-types/{type_id}` | 更新任务类型 |
| `DELETE` | `/api/v1/task-types/{type_id}` | 删除任务类型 |
| `POST` | `/api/v1/task-types/{type_id}/test` | 测试任务类型 |
| `POST` | `/api/v1/task-types/{type_id}/activate` | 激活 |
| `POST` | `/api/v1/task-types/{type_id}/deactivate` | 停用 |

### 任务管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/tasks/submit` | 提交任务 |
| `GET` | `/api/v1/tasks` | 查询任务列表 |
| `GET` | `/api/v1/tasks/summaries` | 查询任务摘要 |
| `GET` | `/api/v1/tasks/{task_id}` | 获取任务详情 |
| `POST` | `/api/v1/tasks/{task_id}/retry` | 重试任务 |
| `POST` | `/api/v1/tasks/requeue-orphaned` | 重入队孤立任务 |
| `DELETE` | `/api/v1/tasks/{task_id}` | 删除任务 |

### 队列与监控

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/queues/status` | 队列状态总览 |
| `GET` | `/api/v1/queues/{name}/tasks` | 列出队列中的任务 |
| `GET` | `/api/v1/queues/dlq` | 获取 DLQ 任务 |
| `GET` | `/api/v1/queues/status/stream` | SSE 实时推送 |
| `GET` | `/api/v1/workers` | Worker 状态 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/live` | K8s 存活探针 |
| `GET` | `/ready` | K8s 就绪探针 |

完整的 API 文档请访问 `http://localhost:8000/docs`。

---

## 配置说明

### 环境变量

```bash
# Redis
REDIS_URL=redis://redis:6379/0

# Worker
WORKER_REPLICAS=3                    # Worker 副本数
CELERY_WORKER_CONCURRENCY=2          # 每个 Worker 并发数

# 任务超时
CELERY_TASK_TIME_LIMIT=900           # 硬超时（秒）
CELERY_TASK_SOFT_TIME_LIMIT=600      # 软超时（秒）

# 重试
MAX_RETRIES=3                        # 默认最大重试次数
MAX_TASK_AGE=7200                    # 任务最大存活时间（秒）

# 限流
DEFAULT_RATE_LIMIT_REQUESTS=100      # 默认限流请求数
DEFAULT_RATE_LIMIT_INTERVAL=60       # 默认限流时间窗（秒）

# 熔断器
CIRCUIT_BREAKER_FAIL_MAX=10          # 触发熔断的失败次数
CIRCUIT_BREAKER_RESET_TIMEOUT=120    # 熔断重置等待时间（秒）

# 日志
LOG_LEVEL=INFO
DEBUG=true
```

### Worker 资源限制

```bash
WORKER_MEMORY_LIMIT=512M             # 内存限制
WORKER_CPU_LIMIT=1.0                 # CPU 限制
WORKER_STOP_GRACE_PERIOD=30s         # 停止宽限期
```

---

## 常用操作

### 查看日志

```bash
# 所有服务
docker compose logs -f

# 指定服务
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f scheduler
```

### 重启服务

```bash
# 重启单个服务
docker compose restart worker

# 重启所有服务
docker compose restart
```

### 扩展 Worker

```bash
# 修改 .env 中的 WORKER_REPLICAS，然后
docker compose up -d --build worker
```

### 重置数据

```bash
# 使用内置工具
docker compose --profile tools run reset

# 或手动清空
docker compose exec redis redis-cli FLUSHDB
```

### 运行测试

```bash
cd src/api && uv run pytest
```

---

## 项目结构

```
fastapi-async-master-1.0/
├── docker-compose.yml          # Docker Compose 编排
├── .env.example                # 环境变量模板
├── src/
│   ├── api/                    # FastAPI 后端
│   │   ├── main.py             # 应用入口
│   │   ├── routers/            # API 路由
│   │   │   ├── health.py       # 健康检查
│   │   │   ├── task_types.py   # 任务类型管理
│   │   │   ├── tasks.py        # 任务管理
│   │   │   ├── queues.py       # 队列监控
│   │   │   ├── workers.py      # Worker 管理
│   │   │   └── redis.py        # Redis 监控
│   │   ├── services/           # 业务逻辑
│   │   ├── models/             # 数据模型
│   │   └── Dockerfile
│   └── worker/                 # Celery Worker
│       ├── tasks.py            # 任务执行逻辑
│       ├── consumer.py         # Redis 队列消费者
│       ├── api_executor.py     # 通用 HTTP 执行器
│       ├── rate_limiter.py     # 分布式限流器
│       ├── circuit_breaker.py  # 熔断器
│       ├── auth_handler.py     # 认证处理
│       └── Dockerfile
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # 通用组件
│   │   └── lib/                # 工具库（API、i18n）
│   ├── Dockerfile
│   └── nginx.conf
├── tests/                      # 测试文件
└── docs/
    └── 使用文档.md              # 详细使用文档
```

---

## 许可证

[MIT License](./LICENSE)
