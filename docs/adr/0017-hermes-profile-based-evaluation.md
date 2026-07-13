# ADR 0017: 基于 Hermes Profile 的模板评测方案

**日期**: 2026-07-12
**状态**: 已决策，待实现
**决策者**: 平台团队

---

## 背景

岗位模板新建后默认为"未评测"状态。模板评测是发布和创建数字员工的前置门禁——只有评测通过的模板才能发布，只有已发布且评测通过的模板才能创建数字员工（`services.py:create_digital_employee` 已实现此校验）。

当前代码的问题：

1. **评测只是数据存储**：`GET/PUT /job-template-versions/{id}/evaluation` 仅限于读写评测结果，没有任何实际执行逻辑。
2. **评测完全不走 Hermes**：`run_template_evaluation` 之前只调用 `HermesClient.create_run("任务描述")`，模板中绑定的 system_prompt、技能、工具、知识源、红线全部不生效。
3. **前端无评测入口**：模板列表和详情页都没有"开始评测"按钮。

核心架构决策：**每个数字员工 = 一个 Hermes Profile 实例**。因此评测必须创建临时 Profile、启动 Gateway、执行任务、获取结果、清理资源——这是一条和数字员工运行时完全相同的路径，评测就是数字员工生命周期的一次预演。

---

## Hermes Agent 提供的 API 全景

Hermes Agent 有两个独立的 HTTP 服务：

### 1. Dashboard API（`hermes_cli/web_server.py`，默认端口 9119）

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/api/profiles` | 创建 Profile（支持 clone、model、no_skills） |
| `GET` | `/api/profiles` | 列出所有 Profile |
| `DELETE` | `/api/profiles/{name}` | 删除 Profile（`yes=True` 跳过确认） |
| `GET` | `/api/profiles/{name}/soul` | 读取 SOUL.md |
| `PUT` | `/api/profiles/{name}/soul` | 写入 SOUL.md |
| `PUT` | `/api/profiles/{name}/model` | 设置模型（provider + model） |
| `POST` | `/api/gateway/start?profile={name}` | 启动指定 Profile 的 Gateway |
| `POST` | `/api/gateway/stop?profile={name}` | 停止指定 Profile 的 Gateway |
| `GET` | `/api/status` | 获取 Gateway 运行状态 |

### 2. Gateway API Server（`gateway/platforms/api_server.py`，按 Profile 配置端口）

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/v1/runs` | 发起 Agent Run（`input` + `instructions` + `session_id`） |
| `GET` | `/v1/runs/{run_id}` | 查询 Run 状态和输出 |
| `GET` | `/v1/runs/{run_id}/events` | 获取 Run 事件流（含 text delta） |
| `GET` | `/health` | 健康检查 |
| `GET` | `/v1/models` | 列出可用模型 |

关键发现：`/v1/runs` 的 `instructions` 字段可以覆盖 system prompt，但技能、工具、知识源跟随 Profile 的配置——这正是我们需要方案 A 的原因。

### 3. CLI 命令（等价于 Dashboard API 的底层实现）

```bash
hermes -p <profile> gateway start    # 等价于 POST /api/gateway/start?profile=
hermes -p <profile> gateway stop     # 等价于 POST /api/gateway/stop?profile=
hermes profile create <name>         # 等价于 POST /api/profiles
hermes profile delete -y <name>      # 等价于 DELETE /api/profiles/{name}
```

---

## 方案对比

| | 方案 B（已实现） | 方案 A（目标） |
|---|---|---|
| **原理** | 模板配置拼成一段文本，作为 prompt 前缀发给共享 Gateway | 创建独立 Hermes Profile，启动专用 Gateway，执行 Run |
| **system_prompt** | ✅ 以文本形式生效 | ✅ 通过 SOUL.md 完全生效 |
| **技能（Skills）** | ❌ 只是文本描述 | ✅ Hermes 加载实际技能包 |
| **工具（Tools）** | ❌ 只是文本描述 | ✅ Hermes 注册实际工具 |
| **知识源（Knowledge）** | ❌ 只是文本描述 | ✅ Hermes 配置知识检索 |
| **红线（Red Lines）** | ❌ 只是文本描述 | ✅ 可写入 SOUL.md 约束 |
| **评测真实性** | 弱——LLM 看到能力描述但不拥有能力 | 强——和数字员工运行行为完全一致 |
| **复杂度** | 低（只改一个方法） | 中高（Profile 生命周期 + Gateway 启停 + 端口管理） |
| **可复用性** | 低——评测专用 | 高——Profile/Gateway 管理是所有数字员工的基础设施 |

**决策：采用方案 A。** 原因：评测不只是为了通过门禁，更是验证模板配置在真实 Hermes 环境下的行为。方案 B 的文本拼接方式无法暴露技能加载失败、工具注册错误、知识源连接异常等问题。

---

## 方案 A 详细设计

### 完整评测流程

```
POST /job-template-versions/{id}/evaluation/run
  Body: { "task_description": "帮我分析上季度销售数据..." }

Platform Backend 执行步骤：
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  1. 分配端口                                                  │
│     port = port_pool.allocate()                              │
│     profile_name = f"eval-{version_id[:20]}-{timestamp}"     │
│                                                              │
│  2. 创建临时 Profile                                          │
│     POST {dashboard}/api/profiles                            │
│     { name: profile_name, model: {provider, model},          │
│       clone_from_default: false, no_skills: false }          │
│                                                              │
│  3. 写入 SOUL.md                                              │
│     PUT {dashboard}/api/profiles/{profile_name}/soul          │
│     { content: 渲染后的 system_prompt + red_lines }          │
│                                                              │
│  4. 设置模型                                                  │
│     PUT {dashboard}/api/profiles/{profile_name}/model         │
│     { provider: "deepseek", model: "deepseek-v4-pro" }       │
│                                                              │
│  5. 配置端口（写 profile 的 config.yaml）                      │
│     修改 gateway.bind 为 0.0.0.0:{port}                       │
│                                                              │
│  6. 启动 Gateway                                              │
│     POST {dashboard}/api/gateway/start?profile={profile_name}│
│                                                              │
│  7. 等待就绪                                                  │
│     poll GET http://127.0.0.1:{port}/health                  │
│     每 2 秒一次，最多等 60 秒                                   │
│                                                              │
│  8. 执行评测任务                                              │
│     hermes = HermesClient(f"http://127.0.0.1:{port}", ...)   │
│     result = hermes.create_and_wait_run(task_description)    │
│                                                              │
│  9. 停止 Gateway                                              │
│     POST {dashboard}/api/gateway/stop?profile={profile_name} │
│                                                              │
│  10. 清理 Profile                                            │
│      DELETE {dashboard}/api/profiles/{profile_name}          │
│                                                              │
│  11. 释放端口                                                 │
│      port_pool.release(port)                                 │
│                                                              │
│  12. 返回结果                                                 │
│      { run_id, hermes_output, status }                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 错误处理

每一步都可能失败，需要保证临时资源一定被清理：

```python
def run_template_evaluation(self, version_id: str, task_description: str) -> dict:
    port = None
    profile_name = None
    try:
        port = self.port_pool.allocate()
        profile_name = f"eval-{version_id[:20]}-{int(time.time())}"
        
        self.hermes_dashboard.create_profile(name=profile_name, ...)
        self.hermes_dashboard.write_soul(profile_name, system_prompt)
        self.hermes_dashboard.set_model(profile_name, provider, model)
        self.hermes_dashboard.write_config(profile_name, {"gateway.bind": f"0.0.0.0:{port}"})
        self.hermes_dashboard.start_gateway(profile_name)
        self._wait_gateway_ready(port, timeout=60)
        
        hermes = HermesClient(f"http://127.0.0.1:{port}", ...)
        return hermes.create_and_wait_run(task_description)
        
    except Exception as exc:
        # 返回错误，但仍然清理资源
        raise
    finally:
        # 清理顺序：Gateway → Profile → Port
        if profile_name:
            try: self.hermes_dashboard.stop_gateway(profile_name)
            except: pass
            try: self.hermes_dashboard.delete_profile(profile_name)
            except: pass
        if port:
            self.port_pool.release(port)
```

### 并发控制

同一模板版本不能同时评测（Profile 名会冲突）。使用模板级锁：

```python
self._eval_locks: dict[str, threading.Lock] = {}

def run_template_evaluation(self, version_id, task_description):
    lock = self._eval_locks.setdefault(version_id, threading.Lock())
    if not lock.acquire(blocking=False):
        raise ConflictError("该模板版本正在评测中，请等待当前评测完成")
    try:
        # ... 执行评测流程
    finally:
        lock.release()
```

### 端口池管理

```python
class PortPool:
    def __init__(self, start: int = 8100, end: int = 8199):
        self._available = set(range(start, end + 1))
        self._lock = threading.Lock()
    
    def allocate(self) -> int:
        with self._lock:
            return self._available.pop()
    
    def release(self, port: int) -> None:
        with self._lock:
            self._available.add(port)
```

---

## 改动文件清单

| 文件 | 改动 | 量级 |
|---|---|---|
| `backend/app/config.py` | 新增 `hermes_dashboard_url`、`eval_port_range_start/end` | 🟢 小 |
| `backend/app/integrations/hermes.py` | 新增 `HermesDashboardClient` 类（Profile CRUD + Gateway 启停 + 健康轮询）；保留 `HermesClient`（Run 执行） | 🟡 中 |
| `backend/app/services.py` | 重写 `run_template_evaluation` 为完整编排流程；新增 `PortPool` 和并发锁 | 🟡 中 |
| `backend/app/schemas.py` | 无需改动（已有 `TemplateEvaluationRunRequest/Response`） | — |
| `backend/app/api/routes.py` | 无需改动（已有 `POST .../evaluation/run` 端点 + publish 门禁） | — |
| `web/src/pages/TemplateManagement.tsx` | 已有评测按钮和弹窗，评测执行时间变长需更新 loading 提示 | 🟢 小 |

---

## HermesDashboardClient API 设计

```python
class HermesDashboardClient:
    """封装 Hermes Dashboard REST API，管理 Profile 和 Gateway 生命周期。"""
    
    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
    
    # Profile 管理
    def create_profile(self, name: str, *, model_provider: str, model_name: str,
                       clone_from: str | None = None, no_skills: bool = False) -> dict
    def delete_profile(self, name: str) -> dict
    def write_soul(self, name: str, content: str) -> dict
    def set_model(self, name: str, provider: str, model: str) -> dict
    def list_profiles(self) -> list[dict]
    
    # Gateway 生命周期
    def start_gateway(self, profile: str) -> dict
    def stop_gateway(self, profile: str) -> dict
    def wait_gateway_ready(self, port: int, timeout_seconds: float = 60) -> bool
    def gateway_status(self, profile: str | None = None) -> dict
```

---

## 评测结果与模板的关系

评测执行完成后，管理员在前端查看 Hermes 输出，人工判断通过/不通过，然后调用已有的 `PUT /job-template-versions/{id}/evaluation` 提交评审结论。

评测结果 `JobTemplateEvaluationRead` 存储：
- `status`: `passed` | `failed`
- `score`: 0-100
- `summary`: 管理员评审说明
- `cases`: 评测用例列表（包含任务描述、Hermes 输出、评审结论）
- `evaluator`: 评审人

---

## 后续扩展

1. **数字员工上线**：`create_digital_employee` → 创建独立 Profile → 写入 SOUL.md → 启动 Gateway → 冒烟测试 → 标记 active。此流程与评测流程共享 `HermesDashboardClient`。
2. **数字员工停用/销毁**：`set_employee_lifecycle(disabled)` → 停止 Gateway → 可选删除 Profile。
3. **模板更新推送到员工**：模板发布新版本 → 更新所有继承该模板的员工的 SOUL.md → 重启 Gateway。
4. **批量评测**：支持多任务描述批量执行，汇总得分。
5. **评测历史**：`TemplateEvaluationRun` 独立存储所有执行记录，支持对比和回归。

---

## 引用

- [ADR 0016: Template Evaluation before employee rollout](./0016-template-evaluation-before-employee-rollout.md)
- Hermes Dashboard API: `hermes_cli/web_server.py`
- Hermes Gateway API Server: `gateway/platforms/api_server.py`
- Hermes Profile 管理: `hermes_cli/profiles.py`
- Hermes Gateway 管理: `hermes_cli/gateway.py`
- Hermes Service Manager: `hermes_cli/service_manager.py`
