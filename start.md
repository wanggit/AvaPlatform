# AI 数字员工平台技术方案

> 基于 Hermes Agent 二次开发，构建单组织、多数字员工、目标驱动协作的 AI 数字员工平台。
>
> 文档版本：v2.1 | 2026-06-27

---

## 1. 当前定位

本平台不是多租户 SaaS。当前产品只服务一个 Organization，用来管理该组织内部的一组 AI 数字员工。

Hermes Agent 仍然作为单个 Digital Employee 的运行时底座。Platform 层负责组织管理能力：岗位模板、部门、组织架构、员工目录、目标委托、KPI、配额、审计、Skill 管理和知识库管理。

核心判断：

- Hermes 是“员工个体”的运行时。
- Platform 是“组织管理系统”。
- 多 Agent 协作不依赖管理员预设的静态 DAG；Digital Employee 可以提出委托，Platform 通过 Delegation Policy 创建受控 Work Item，并维护可追踪、可取消、可恢复的动态 Execution Graph。
- MVP 首批内置/演示岗位模板收敛为三个 Pilot Job Template：企业经营情报员工、客服工单协调员工、销售方案协作员工。

相关 ADR：

- `docs/adr/0001-goal-driven-delegation.md`
- `docs/adr/0002-single-organization-single-admin.md`
- `docs/adr/0003-skill-package-upload.md`
- `docs/adr/0004-ragflow-as-first-knowledge-adapter.md`
- `docs/adr/0005-platform-mediated-knowledge-retrieval.md`
- `docs/adr/0006-quota-enforcement-levels.md`
- `docs/adr/0007-audit-rules-are-observability.md`
- `docs/adr/0008-tool-registry-separates-tools-from-skills.md`
- `docs/adr/0009-job-template-system-prompt-maps-to-hermes-identity.md`
- `docs/adr/0010-platform-controlled-dynamic-execution-graph.md`
- `docs/adr/0011-delegation-handoff-and-workflow-are-distinct.md`
- `docs/adr/0012-mvp-budget-model-is-organization-quota-and-goal-budget.md`
- `docs/adr/0013-artifact-acceptance-is-separate-from-approval.md`
- `docs/adr/0014-platform-persists-goal-run-execution-state.md`
- `docs/adr/0015-goal-risk-level-controls-automation-boundary.md`
- `docs/adr/0016-template-evaluation-before-employee-rollout.md`
- `docs/adr/0017-mvp-starts-with-three-pilot-job-templates.md`
- `docs/adr/0018-business-outcome-metrics-bind-to-template-versions.md`

---

## 2. 领域模型

核心词汇以 `CONTEXT.md` 为准。当前关键概念如下：

| 概念 | 含义 |
|------|------|
| Organization | 使用平台的一家企业或业务主体。当前只服务一个 Organization |
| Digital Employee | 承担特定岗位职责的 AI 工作体 |
| Employee Lifecycle State | 数字员工控制面的业务生命周期状态 |
| Employee Availability State | 数字员工面向调度和员工目录的可用性状态 |
| Employee Rollout | 数字员工从创建到可接收目标的上岗流程 |
| Employee Rollout Job | 后台异步执行的员工上岗任务 |
| Job Template | 创建 Digital Employee 的岗位蓝图 |
| Job Template Version | 岗位模板发布时形成的配置快照 |
| Template Evaluation | 岗位模板版本上线前评测 |
| Pilot Job Template | MVP 内置或演示用试点岗位模板 |
| Knowledge Entitlement | 数字员工从 Job Template 继承的知识访问授权 |
| Grade | Staff → Lead → Manager → Director 的职级体系 |
| Department | 组织内部门，Job Template 和 Digital Employee 可归属部门 |
| Profile | Digital Employee 的持久化档案 |
| Instance | Digital Employee 的运行时 Hermes 进程 |
| Hermes Instance Runtime State | Hermes 实例的进程和健康状态 |
| Instance Smoke Test | 员工上岗前的最小实例级验证 |
| Smoke/Test Run | 不进入正式 Goal 的冒烟或试运行调用 |
| Skill | 可分发的 Hermes 能力单元，来自 Skill Package |
| Skill Package | 包含 `SKILL.md` 和支持文件的 `.zip` 技能包 |
| Skill Library | 全局 Skill Package 上传、审核、发布、版本管理处 |
| Tool | Digital Employee 运行时可调用的外部能力或 Platform API 能力 |
| Business Tool | Platform 自定义、用于访问业务系统或 Platform API 的 Tool |
| Hermes Built-in Tool | Hermes Agent 自带的通用运行时工具能力 |
| Tool Registry | Platform 统一维护 Tool 元数据、调用方式、风险和授权的注册表 |
| Tool Idempotency Policy | Platform 管理 Tool 的幂等调用策略 |
| Tool Entitlement | Job Template 对 Tool 的绑定授权和参数边界 |
| Platform Tool Gateway | Business Tool 的统一运行时调用入口 |
| Credential | 本系统内置保存和管理的业务系统访问凭证 |
| Knowledge Base | 外部成熟企业知识系统 |
| Knowledge Source | 外部知识系统中可绑定到 Job Template 的检索范围 |
| External Dataset Sync | 从外部知识库手动同步 dataset 清单的配置动作 |
| Knowledge Connection | Platform 连接外部知识系统的配置 |
| Knowledge Adapter | Platform 到外部知识系统的统一检索适配层 |
| Knowledge Retrieval Tool | Digital Employee 查询授权 Knowledge Source 的工具 |
| Knowledge Preview | 管理员验证 Knowledge Source 检索效果的配置动作 |
| Knowledge Citation | 知识检索命中的来源引用 |
| Employee Service Token | Digital Employee 运行时调用 Platform 接口的最小权限凭证 |
| Model Configuration | 平台可调用模型的集中配置 |
| Goal | 分配给 Digital Employee 的工作目标 |
| Goal Risk Level | Goal 或 Goal Run 的 L1-L4 业务风险分级 |
| Root Goal Owner | 对 Goal 最终结果持续负责的数字员工 |
| Goal Run | 一次 Goal 的可恢复执行过程 |
| Work Item | Goal Run 中由 Platform 创建的受控子任务 |
| Delegation | 数字员工提出、Platform 授权和调度的工作项委托 |
| Handoff | 业务事项责任主体转交，MVP 暂不作为默认协作机制 |
| Workflow | Platform 控制顺序的固定业务流程 |
| Execution Graph | Platform 维护的运行时动态执行图 |
| Delegation Policy | 控制委托深度、扇出、预算、并发和再委托的规则 |
| Employee Directory | 数字员工公开目录，用于同事发现和委托决策 |
| Artifact | 数字员工完成目标后的产物 |
| Artifact Acceptance | 产物是否满足验收标准的结果判断 |
| Business Outcome Metric | 衡量业务价值的结果指标 |
| Metric Binding | Job Template Version 对业务结果指标的绑定 |
| Red Line | 岗位模板中的绝对禁止行为 |
| Approval | 正常流程中的人工审批 |
| Escalation | Agent 无法处理时的异常升级 |
| KPI | 数字员工绩效指标 |
| Quota | Organization 级 Token 总上限 |
| Organization Quota | 平台整体每日 Token 硬上限 |
| Goal Budget | 单个 Goal Run 的 Token 执行预算 |
| Budget Blocked | 预算超限后的受控阻断状态 |
| Usage Analytics | 按部门、员工、Goal、Work Item 统计 Token 用量 |
| Token Ledger | 模型调用 Token 消耗流水账 |

---

## 3. 架构原则

1. **Hermes 零改造**
   Platform 不 fork Hermes，不改 Hermes 核心。所有集成都通过 Profile 文件和 Hermes API Server。

2. **一个数字员工一个运行时实例**
   每个 Digital Employee 对应一个独立 Profile 和一个独立 Hermes Instance。

   Job Template 的 System Prompt 是该员工的 Hermes 身份来源。创建或更新员工时，Platform 将发布版本的 System Prompt 渲染到该员工 Profile 的 `SOUL.md`，必要时再通过 Hermes `ephemeral_system_prompt` 做运行时覆盖。

3. **单后台**
   不再区分租户后台和超级后台。一个管理后台同时承载运营管理与系统配置。

4. **岗位模板直接绑定资源**
   Job Template 可以直接绑定 Department、Skill、Knowledge Source、模型、Tool 白名单、Red Line、默认 Goal Budget 和可承接最高 Goal Risk Level。

5. **目标驱动、平台受控协作**
   人类给一个 Root Goal Owner 分配 Goal。负责人可以拆解目标、查询 Employee Directory、提出委托；Platform 校验 Delegation Policy 后创建 Work Item 并维护 Execution Graph。MVP 默认只允许一层 Orchestrator-Worker 委托，子员工不得继续委托。

---

## 4. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    管理后台 (React + Ant Design)             │
│                                                             │
│  运营管理: Dashboard / Employee / Directory / Goal / KPI     │
│  系统配置: Template / Department / Skill / Knowledge / Quota │
└───────────────────────────────┬─────────────────────────────┘
                                │ REST / SSE
┌───────────────────────────────▼─────────────────────────────┐
│                      Platform API (FastAPI)                  │
│                                                             │
│  ├ Digital Employee Management                              │
│  ├ Job Template Engine                                      │
│  ├ Employee Directory                                       │
│  ├ Goal & Delegation Engine                                 │
│  ├ Skill Library                                            │
│  ├ Knowledge Adapter / Knowledge Source                     │
│  ├ KPI / Quota / Audit                                      │
│  └ Instance Manager                                         │
└───────────────────────────────┬─────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────┐
│             Platform Store + Outbox + Worker Queue           │
│                                                             │
│  PostgreSQL: Goal Run / Work Item / Artifact / Approval      │
│  Outbox Event: state changes and next actions                │
│  Worker + Redis Queue: invoke Hermes and resume execution    │
└───────────────────────────────┬─────────────────────────────┘
                                │ HTTP
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Hermes Instance  │  │ Hermes Instance  │  │ Hermes Instance  │
│ Digital Employee │  │ Digital Employee │  │ Digital Employee │
│ Profile: cs_rep  │  │ Profile: sales   │  │ Profile: ops_dir │
│ API Server       │  │ API Server       │  │ API Server       │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 5. 管理后台

当前原型位于 `web/`，启动方式：

```bash
./start-proto.sh
```

默认地址：

```text
http://localhost:5173/
```

如果端口占用，Vite 会自动切换到下一个端口。

### 5.1 运营管理

- 概览看板
- 员工管理
- 员工目录
- 组织架构
- 目标管理
- KPI 报告

### 5.2 系统配置

- 岗位模板
- 部门管理
- Skill 管理
- 工具管理
- 模型配置
- 知识源接入
- 配额策略
- 审计规则

### 5.3 当前原型状态

已实现页面：

- `Dashboard.tsx`
- `EmployeeManagement.tsx`
- `EmployeeDirectory.tsx`
- `OrganizationChart.tsx`
- `GoalManagement.tsx`
- `KPIReports.tsx`
- `TemplateManagement.tsx`
- `DepartmentManagement.tsx`
- `ModelManagement.tsx`
- `SkillManagement.tsx`
- `ToolManagement.tsx`
- `KnowledgeManagement.tsx`
- `QuotaManagement.tsx`
- `AuditManagement.tsx`
- `Placeholder.tsx`

`Skill 管理`、`工具管理`、`模型配置`、`知识源接入`、`配额策略` 和 `审计规则` 已实现原型页。`工具管理` 菜单放在 `Skill 管理` 和 `模型配置` 之间，维护 Tool Registry、Credential、Tool 调用审计和 Hermes 内置工具视图。Skill 新增/编辑通过上传 `.zip` 技能包完成，平台不维护文件数量。知识源接入页按 RAGFlow Adapter 边界实现：只做连接、同步、登记/编辑和检索预览，不自建知识库。`配额策略` 页需要调整为 Organization Quota、Goal Budget、Token Ledger 和 Usage Analytics，不再展示 Department / Digital Employee 独立配额阻断。`审计规则` 页覆盖 Audit Event、Audit Rule、通知记录、保留策略、导出审计和规则测试。

员工管理原型待办：新建数字员工弹窗当前还没有头像字段。创建员工时应补充头像或头像上传/选择控件，因为头像属于 Employee Instance Configuration，不属于 Job Template 能力边界。

知识库页面 MVP 范围：

- RAGFlow 连接：维护 Base URL、API Key 引用、连接状态，支持测试连接和同步 datasets。
- Dataset 同步：管理员手动从 RAGFlow 拉取 datasets，供 Platform 登记为 Knowledge Source。
- Knowledge Source 列表：展示平台显示名称、RAGFlow dataset 名称/ID、状态、最近同步时间、已绑定岗位模板数；如 RAGFlow API 可提供，再展示文档数和 chunk 数。
- 登记/编辑 Knowledge Source：从已同步 dataset 中选择，设置平台显示名称、说明、分类和启停状态。
- 检索预览：管理员选择一个或多个 Knowledge Source，输入 query，展示 hits、score、citation 和 `audit_id`。这是配置验证动作，可绕过 Job Template 权限，但必须要求管理员权限并记录审计。
- 不上传文档，不创建 RAGFlow dataset，不暴露解析、分块、embedding、索引配置。

MVP 只允许一个活跃 RAGFlow Knowledge Connection。数据模型保留 `connection_id`，但管理后台不提供多连接切换能力。

Dataset 同步策略：

- MVP 不做后台定时同步，只提供管理员手动“同步 datasets”。
- 新发现的 RAGFlow dataset 进入“未登记”状态，需要管理员登记为 Platform Knowledge Source 后才能被岗位模板绑定。
- 已登记的 Knowledge Source 在同步时更新外部名称、文档数、chunk 数和最近同步时间。
- RAGFlow 中删除、无权限或不可见的 dataset 标记为“失联”，不自动删除。
- 已绑定 Job Template 的 Knowledge Source 失联时，列表和模板发布页必须给出风险提示。

失联运行时策略：

- 单个授权 Knowledge Source 失联时，Knowledge Adapter 跳过该 source，继续检索其他可用 source。
- 响应必须包含 `warnings`，说明哪些 source 不可用。
- 如果本次授权范围内所有 Knowledge Source 都失联，返回可审计错误 `knowledge_sources_unavailable`，并记录 `audit_id`。
- 运行时不自动解绑、不自动删除 Knowledge Source。

配额策略页面 MVP 范围：

- Organization Quota：维护平台每日 Token 总上限和预警阈值，固定硬控；超限后只阻断数据面模型成本调用，控制面保持可用。
- Goal Budget：维护 Goal Run 的默认预算、预警阈值和超限动作；超限后阻断该 Goal Run 的新模型成本调用，等待人工调整预算、取消或结束。
- Usage Analytics：按 Department、Digital Employee、Goal、Work Item 展示用量统计和趋势；MVP 不提供部门或员工独立配额阻断。
- Token Ledger：展示 Hermes 返回 usage 后的平台入账流水，包含员工、部门、模型、Hermes instance/session/run、prompt/completion/cache/reasoning/total tokens 和 `estimated` 标记。
- 执行策略：在页面中显式展示 Organization Quota 和 Goal Budget 的超限动作，避免把 Goal 预算阻断误实现为杀掉 Hermes Instance。

审计规则页面 MVP 范围：

- 审计事件：统一 Audit Event 列表、事件类型/严重级别筛选、详情查看、原始 payload 和 evidence_refs 展示、追加 Audit Disposition。
- 审计规则：规则列表、新建/编辑、启停、固定条件与固定动作配置，不支持脚本规则或外部调用。
- 规则测试：选择一条规则和一条 mock/最近 Audit Event，预览是否命中、输出 severity、通知对象、复核、KPI 和保留期限；测试不写事件、不发通知、不改 KPI。
- 通知记录：展示平台内通知和外部渠道占位状态，邮件/飞书/钉钉可显示未接入。
- 保留策略：展示默认 180 天、高危 365 天，以及 90/180/365/永久的规则覆盖范围。
- 审计导出：导出动作本身生成 `sensitive_operation` Audit Event；未脱敏导出需要理由。

---

## 6. 核心模块设计

### 6.1 Instance Manager

职责：

- 创建 Profile
- 渲染 `config.yaml`
- 签发和轮换 Employee Service Token
- 分发 Skill
- 分配端口
- 启动/停止 Hermes Instance
- 调用 Hermes API Server
- 健康检查
- 创建和调度 Employee Rollout Job
- 执行实例冒烟测试
- 执行委托原语

Profile 路径建议：

```text
~/.hermes/profiles/{employee_slug}/
```

示例结构：

```text
~/.hermes/profiles/
├── cs-rep-xiaoxing/
│   ├── config.yaml
│   ├── .env
│   ├── skills/
│   ├── memory/
│   ├── sessions/
│   └── state.db
├── sales-lead-david/
└── ops-director-tom/
```

核心接口：

```python
class InstanceManager:
    async def enqueue_rollout(self, employee_id: str) -> RolloutJob: ...
    async def spawn(self, employee_id: str, config: dict) -> EmployeeInstance: ...
    async def smoke_test(self, employee_id: str) -> SmokeTestResult: ...
    async def activate(self, employee_id: str) -> None: ...
    async def send_task(self, employee_id: str, message: str, session_key: str | None = None) -> dict: ...
    async def delegate_task(self, from_employee: str, to_employee: str, goal_id: str, sub_goal: str, context: str = "") -> dict: ...
    async def stop(self, employee_id: str) -> None: ...
    async def health_check_all(self) -> dict[str, str]: ...
```

状态模型必须拆分：

- Employee Lifecycle State：Platform 控制面的业务生命周期，如 `provisioning`、`pending_activation`、`active`、`disabled`、`rollout_failed`、`needs_review`。它决定员工是否可启用、停用、接收 Goal 或需要人工处理。
- Hermes Instance Runtime State：Hermes 进程和健康状态，如 `not_started`、`starting`、`healthy`、`unhealthy`、`recovering`、`stopped`。它由 Instance Manager 维护，不能替代员工生命周期。
- Employee Availability State：员工目录和调度展示的可用性，如空闲、忙碌、不可用。它由生命周期、运行时状态、当前 Goal / Work Item、预算阻断和维护状态共同推导。

示例：员工可以是 `active`，但 Hermes Instance `unhealthy`，此时 Employee Availability 应为不可用并触发告警；员工也可以是 `pending_activation`，但刚完成冒烟测试的 Hermes Instance 尚未停止，调度器仍必须拒绝给它分配 Goal。

已上岗员工的运行时恢复策略：

- 当 `lifecycle_state = active` 且 `runtime_state = unhealthy` 时，员工业务生命周期不立即变更，`availability_state` 必须变为 `unavailable`。
- 调度器暂停向该员工分配新的 Goal / Work Item；已有运行中的 Work Item 由 Goal Run 状态机按失败、重试或人工处理策略推进。
- Instance Manager 可以在次数上限内自动重启 Hermes Instance 或重新执行健康检查，期间 `runtime_state = recovering`。
- 恢复成功后 `runtime_state = healthy`，`availability_state` 根据当前负载回到 `idle` 或 `busy`。
- 超过恢复上限后保留 `lifecycle_state = active`，但标记 `needs_review` 或运行异常，生成 `abnormal_shutdown` Audit Event，并通知管理员和直属上级。

Digital Employee 创建后的 Employee Rollout 流程：

1. Platform 校验所选 Job Template Version 已发布且最近一次 Template Evaluation 结果为通过；未运行、运行中或失败的版本直接不允许创建 Digital Employee。
2. Platform 创建 Digital Employee 记录，初始状态为 `provisioning`，此时不能接收 Goal。
3. Platform 创建 Employee Rollout Job 并立即返回页面；弹窗提交不等待 Hermes 启动或模型探测完成。
4. 后台 Worker 执行 Employee Rollout Job，渲染员工 Profile：`config.yaml`、`SOUL.md`、Skill、Tool allowlist、Knowledge Retrieval Tool 配置和模型配置。
5. Worker 签发 Employee Service Token，并只把调用 Platform 所需的最小权限配置写入 Profile。
6. Worker 分配端口并启动独立 Hermes Instance。
7. Worker 对该实例执行 Instance Smoke Test。
8. 冒烟测试通过后，员工状态进入 `pending_activation`；该状态不允许接收 Goal Run，Hermes Instance 可以停止或进入冷待机。
9. 管理员手动点击“上岗/启用”时，Platform 启动或复用 Hermes Instance，并执行轻量健康检查；通过后状态变为 `active`，员工才可接收 Goal Run。
10. 冒烟测试失败时，员工状态进入 `rollout_failed` 或 `needs_review`，保留失败日志和审计事件，不允许接收 Goal。

MVP 不在点击“创建数字员工”后自动上岗。创建、配置、测试和上岗是四个不同控制点；后续如需要低风险模板自动上岗，可以作为独立策略增加。

创建 Digital Employee 成功后不自动创建默认 Goal 或初始业务任务。创建后的验证只允许走 Employee Rollout Job、Instance Smoke Test 或 Smoke/Test Run；这些测试调用必须标记为 `smoke` / `test`，不进入正式 Goal Run、Work Item、业务 KPI 或业务产物统计。Token Ledger 和 Audit Event 可记录测试标记，用于成本、审计和排障。

Employee Rollout Job 要求：

- 必须异步执行，避免创建弹窗阻塞 Hermes 启动和真实模型探测。
- 页面展示当前步骤、开始/结束时间、失败分类、失败原因、修复建议、日志摘要和最近一次冒烟测试结果。
- `rollout_failed` / `needs_review` 员工应提供“重新配置”或“重新执行冒烟测试”操作。
- 重试必须幂等，不能重复创建多个有效 Profile、端口占用或未吊销的 Employee Service Token。

Employee Rollout Job 重试策略：

- 临时基础设施失败可以自动重试：Hermes 启动超时、端口短暂占用后可重新分配、模型 API 短暂超时、Worker 临时异常。
- 配置错误不自动重试：Job Template 配置缺失、模型 API Key 错误、Skill 包缺失或校验失败、Tool / Knowledge Source 引用已停用、System Prompt 渲染失败。
- 配置错误需要管理员修复配置后，手动触发“重新配置”或“重新执行冒烟测试”。
- 自动重试应有次数上限和退避策略；超过上限后进入 `rollout_failed` 或 `needs_review`。

Instance Smoke Test 分为两层：

- 静态配置检查：确认 Profile 目录存在，`SOUL.md` 已写入，Skill 包已分发，Tool allowlist、Knowledge Retrieval Tool、模型配置和 Employee Service Token 已渲染到位。
- Hermes 真实探测：通过 Hermes API Server 发起一次测试 session 调用，使用低 `max_tokens`、短超时、禁止工具调用的最小提示词，验证 Hermes Instance、Profile 加载、模型 Base URL、API Key、模型名称和上下文配置可用。

生产环境上岗前默认必须通过 Hermes 真实探测。开发或演示环境可以保留“手动标记通过”，但该结果必须明确标注为人工通过，不能伪装成真实探测结果。

资源策略：

- `pending_activation` 是控制面状态，不代表 Hermes Instance 必须常驻运行。
- 为节省资源并避免误调用，MVP 默认在冒烟测试通过后停止实例或保持冷待机。
- 如为了演示体验保留短时间运行实例，调度器仍必须按员工状态拒绝向 `pending_activation` 员工分配 Goal。
- Activation 时必须确认实例可用；如果启动或健康检查失败，员工不能进入 `active`。

### 6.2 Job Template Engine

职责：

- 维护 Job Template
- 渲染 Hermes Profile 配置
- 渲染岗位 System Prompt 到 Hermes Profile 的 `SOUL.md`
- 在需要运行时覆盖时，通过 Hermes `ephemeral_system_prompt` 注入岗位 System Prompt
- 绑定 Department、Skill、Knowledge Source、工具白名单、Red Line、默认 Goal Budget 和最高 Goal Risk Level

Job Template 关键字段：

```python
class JobTemplate:
    role: str
    grade: str
    department: str
    description: str
    system_prompt: str
    max_goal_risk_level: str  # L1 | L2 | L3 | L4
    model_config_id: str
    skills: list[str]
    knowledge_sources: list[str]
    toolsets: list[str]
    red_lines: list[str]
    default_goal_budget_tokens: int
    status: str  # draft | published
    version: str
```

创建 Digital Employee 时选择一个已发布且 Template Evaluation 通过的 Job Template Version。员工继承模板配置，只能填写或覆盖 Employee Instance Configuration。MVP 中创建弹窗只收集基础实例属性，避免把创建流程做成权限配置流程。

创建时填写：

- 员工姓名、昵称、头像和备注。
- 所属部门。
- 直属上级。

创建后在员工详情页或权限配置中维护：

- 禁用模板内某些 Knowledge Source，不能新增模板外 Knowledge Source。
- 禁用模板内某些 Tool，或进一步收窄模板内 Tool 参数，不能新增模板外 Tool。
- 实例资源策略，如是否预热。

禁止的员工级覆盖：

- 扩大 System Prompt 职责边界或红线边界。
- 新增模板外 Skill。
- 新增模板外 Tool。
- 新增模板外 Knowledge Source。
- 提高最高 Goal Risk Level。
- 提高默认 Goal Budget。

MVP 中员工级配置不能扩大知识权限。Digital Employee 的 Knowledge Source 访问范围只从 Job Template 继承；如需临时缩小访问范围，可以在员工级别禁用模板内某些 Knowledge Source，但不能新增模板外 Knowledge Source。

发布规则：

- 草稿修改不影响已创建 Digital Employee。
- 发布新 Job Template Version 后，继承该模板且未停用的 Digital Employee 自动使用新的 Knowledge Entitlement。
- 发布前 UI 应提示影响员工数量。
- 发布前应展示最近一次 Template Evaluation 结果；未运行、运行中或失败时不允许发布。
- 发布动作必须记录审计日志，包含 Knowledge Source 变更摘要和受影响员工范围。
- 如员工配置了“缩小模板内范围”，发布后继续保留缩小规则，但最终可访问范围不能超出新版本模板授权。
- System Prompt 变更必须显示差异摘要和受影响员工数量；发布后 Platform 更新继承该模板的员工 Profile `SOUL.md`。
- 仅 Knowledge Source 权限变更不需要重启 Hermes Instance；Knowledge Retrieval Tool 每次调用 Platform 时动态鉴权。
- 只有 Profile 文件实际变化时才需要 reload 或重启，例如 Skill 包更新、模型配置变更、System Prompt 变更。Hermes 会在 session 级缓存 system prompt，因此 System Prompt 变更至少需要新 session、reload 或重启后才保证生效。

Template Evaluation MVP：

- 评测对象是 Job Template Version，不是单个 Digital Employee。
- Template Evaluation Run 是对一个 Job Template Version 执行一次评测计划的记录；`未运行` 只表示该版本还没有产生评测运行结果。
- MVP 的评测计划由测试用例、输入、期望结果、实际结果、人工 pass/fail、失败原因和关键断言记录组成。
- MVP 不要求自动调用 Hermes 执行评测用例；自动评测、版本对比和回归测试属于后续阶段。
- 创建 Digital Employee 时继承模板评测结果；员工级只做必要的实例冒烟测试，如 Profile 渲染、Hermes 启动和基础健康检查。
- 创建 Digital Employee 时只能选择已发布且评测通过的 Job Template Version；未运行、运行中或失败的版本不允许创建员工。
- 创建 Digital Employee 不等于上岗；实例冒烟测试通过后进入待上岗状态，由管理员显式启用后才可接收 Goal。
- 评测用例覆盖：正常问题、模糊问题、无数据问题、冲突知识、越权请求、Prompt Injection、高风险 Tool、知识源失联、Tool 调用失败、审批拒绝、预算超限。
- 评测输出：通过率、失败用例、引用质量、是否越权、是否触发正确审批、是否遵守 Goal Risk Level 边界、是否产生预期 Audit Event。
- Template Evaluation 结果必须记录到模板版本，作为发布确认、员工创建和后续回滚判断的依据。

Pilot Job Template MVP：

MVP 首批只内置或演示三个 Pilot Job Template，用于验证不同业务价值，不先扩展抽象岗位库。

1. 企业经营情报员工
   - 工作：汇总内部经营数据、监测行业和竞争对手、生成管理周报、标记异常、提出需要管理者确认的问题。
   - 边界：只读为主，不替管理层作最终决策。
   - Business Outcome Metric：管理材料准备时间、异常发现时效、引用完整率、管理者采纳率。

2. 客服工单协调员工
   - 工作：分类工单、查询知识库、汇总客户历史、生成回复草稿、推荐转派部门、标记重大投诉。
   - 边界：初期不允许直接退款、承诺赔偿、关闭重大投诉。
   - Business Outcome Metric：首次响应时间、平均处理时间、转派准确率、草稿采用率、重复来询率。

3. 销售方案协作员工
   - 工作：客户研究、历史交流汇总、需求分析、方案初稿、产品资料查询、合规检查、拜访材料准备。
   - 边界：不自动承诺价格、合同条款或最终成交条件。
   - Business Outcome Metric：方案准备周期、销售准备时间、方案采用率、信息错误率、商机转化辅助指标。

Business Outcome Metric MVP：

- Platform 维护 Business Outcome Metric Catalog，记录指标名称、说明、单位、方向、来源类型和适用场景。
- Metric Binding 绑定在 Job Template Version 上，不绑定在可变草稿或单个 Digital Employee 上。
- 每个 Pilot Job Template 至少绑定 3 个 Business Outcome Metric。
- 每个 Pilot Job Template 至少包含 1 个 Platform 原生可计算指标，保证系统能自行产出最低限度价值报告。
- 指标来源分三类：
  - `platform_native`：由 Platform 事件直接计算，如 Goal 完成耗时、Artifact 首次验收通过率、返工率、Token 成本、风险事件数量、审批拒绝次数、Escalation 率。
  - `tool_business_system`：由 Tool Gateway 调用业务系统时记录业务对象 ID、状态和时间戳后计算，如工单首次响应时间、平均处理时长、CRM 更新成功率、邮件草稿采用率、转派准确率。
  - `manual_or_imported`：由管理员人工录入、CSV 或 API 导入，如管理者采纳率、销售方案采用率、客户满意度、增量收入、人工节省时间估算。
- MVP 不做全量 BI。业务系统自动采集只在 Tool Gateway 已经接入的场景里做；未接入系统的业务结果指标先用人工录入或导入。
- Metric Binding 字段至少包含：`metric_id`、`source_type`、`baseline_value`、`target_value`、`direction`、`attribution_window`、`owner`、`reviewer`。

### 6.3 Model Configuration

职责：

- 维护平台可调用的模型
- 按模型类型分类：大语言模型、向量模型、排序模型、视觉模型、语音模型
- 维护 Base URL、API Key、模型名称、上下文大小、最大输出、启停状态
- 为 Job Template、Digital Employee、Knowledge Base、检索重排等功能提供统一模型选择来源

关键字段：

```python
class ModelConfiguration:
    name: str
    type: str  # llm | embedding | rerank | vision | audio
    provider: str
    model_name: str
    base_url: str
    api_key: str
    context_window: int
    max_output_tokens: int | None
    status: str  # active | disabled
    is_default: bool
```

### 6.4 Employee Directory

职责：

- 维护所有 Digital Employee 的公开信息
- 支持按 Skill、Grade、部门、Employee Availability State 搜索
- 给 Goal-driven Delegation 提供同事发现能力

Directory Entry：

```python
class DirectoryEntry:
    employee_id: str
    name: str
    role: str
    grade: str
    department: str
    description: str
    skills: list[str]
    availability_state: str  # idle | busy | unavailable
    lifecycle_state: str
    runtime_state: str
```

### 6.5 Goal Risk Level

Goal Risk Level 是 Goal / Goal Run 的业务风险等级，不等同于 Tool Registry 中单个 Tool 的 `risk_level`。MVP 使用四级：

| 等级 | 名称 | AI 权限边界 | 示例 |
|------|------|-------------|------|
| L1 | 信息辅助 | 查询、总结、起草，不写业务系统 | 知识问答、报告初稿、资料整理 |
| L2 | 工作协同 | 创建内部任务、草稿、催办、转派建议 | 工单草稿、项目催办、会议材料 |
| L3 | 受控执行 | 审批后写业务系统 | 发邮件、修改 CRM、提交工单 |
| L4 | 高风险决策 | AI 只准备材料，最终决定必须由人类作出 | 付款、辞退、签约、法律/财务最终判断 |

执行策略：

- Goal 创建时必须选择 Goal Risk Level；后续可增加自动推断，但不能替代人工确认。
- Job Template 声明可承接的最高 Goal Risk Level；员工不能接收超过模板上限的 Goal。
- Delegation Policy 根据 Goal Risk Level 调整深度、跨部门、审批和验收要求。
- L1 默认允许只读工具和普通 Artifact Acceptance。
- L2 允许创建内部草稿或任务，但外部写操作仍按 Tool Gateway 控制。
- L3 涉及写业务系统，必须通过 Approval、Audit Event 和 Artifact Acceptance。
- L4 不允许 AI 自动作最终决策或直接执行最终动作；只能生成材料、证据、选项和风险说明，由人类决策。

### 6.6 Goal & Delegation Engine

职责：

- 创建 Goal
- 创建和恢复 Goal Run
- 维护动态 Execution Graph
- 校验 Delegation Policy
- 创建和调度 Work Item
- 接收 Artifact
- 执行 Artifact Acceptance
- 记录审批等待、取消、重试和超时
- 完成后触发 KPI 评估
- 持久化 Hermes run/session 引用，但不把 Hermes session 当作业务状态源

Goal Run 状态：

```text
created → planning → running → waiting_approval → blocked
      └──────────────→ completed / failed / cancelled / expired
```

Work Item 状态：

```text
proposed → authorized → assigned → running → submitted → accepted → completed
       └→ rejected / rework_required / blocked / runtime_interrupted / failed_retryable / failed / cancelled / expired
```

运行逻辑：

1. 人类或业务系统显式创建 Goal，指定 Root Goal Owner；员工创建、上岗冒烟或试运行不能自动创建业务 Goal。
2. Platform 创建 Goal Run，并初始化 Goal Risk Level、预算、Deadline、Delegation Policy 和 Execution Graph。
3. Root Goal Owner 收到目标，查询 Employee Directory，并提出 Work Item 委托。
4. Platform 校验员工身份、Job Template 最高风险等级、Goal 状态、委托深度、扇出、预算、并发、数据权限、跨部门策略、环路和审批要求。
5. 校验通过后，Platform 创建 Work Item 并调度目标员工；校验失败时返回可审计的拒绝原因。
6. 被委托员工只能使用自身 Tool Entitlement、Knowledge Entitlement 和 Employee Service Token，不能继承委托方权限。
7. 被委托员工提交 Artifact；Root Goal Owner 或规则验证器执行 Artifact Acceptance 后，Work Item 才能进入 accepted/completed。
8. Artifact Acceptance 失败时，Work Item 进入 rework_required；达到重试上限后进入 failed。
9. Hermes Instance 在执行 Work Item 期间中断时，Platform 将当前 Work Item 标记为 `runtime_interrupted` 或 `failed_retryable`，记录 Hermes run/session 引用、错误原因、已产生 Artifact 和 Tool 调用痕迹。
10. 实例恢复后，Goal Run 状态机决定重试一次、重新排队到同一员工、重新调度给其他合格员工，或转人工处理；MVP 不做复杂断点续跑。
11. Root Goal Owner 汇总已验收 Artifact 并完成 Goal。
12. Platform 记录 KPI、Token Ledger、Audit Event 和 Trace 输入。

MVP 委托边界：

- 默认只允许一层 Orchestrator-Worker 委托。
- 子员工默认不能再次委托。
- Root Goal Owner 始终不变。
- Hermes Instance 不能直接调用另一个 Hermes Instance；委托必须通过 Platform API 或 `delegate_work_item` Business Tool。
- Delegation Policy 默认限制最大深度、单节点子任务数、总 Work Item 数、并发数、重试次数、Goal Budget 和 Deadline。
- Delegation Policy 必须读取 Goal Risk Level；风险越高，越倾向于禁止再委托、要求更强 Artifact Acceptance、限制跨部门，并触发更多 Approval。
- MVP 不实现 Handoff。客服转退款专员、售后转法务等责任主体转交场景后续单独设计，不能混入 Delegation。
- 固定审批、退款、合同签署、权限变更、数据删除等强顺序业务使用 Workflow，由 Platform 决定流程顺序；Agent 只参与局部查询、分析、草稿生成或材料准备。

可靠执行边界：

- Platform 是 Goal Run、Work Item、Artifact、Approval、Budget 和 Trace 的状态源。
- 每次状态变化先写入 Platform Store，再通过 Outbox Event 触发下一步执行。
- Hermes Instance 只作为执行器；Hermes run/session ID 作为引用写入 Goal Run 或 Work Item，不作为业务状态源。
- Worker 从队列中读取待执行动作，调用目标 Hermes Instance，回写执行结果、Artifact、usage、错误和下一步状态。
- 审批等待、预算阻断、Artifact 返工、运行中断、重试、取消和超时都必须由 Platform 状态驱动恢复。
- 运行中断恢复不能假设 Hermes session 能可靠恢复业务状态；重复执行外部写 Tool 前必须依赖 Platform Tool Gateway 的幂等键、审批记录和 Audit Event 判断是否可以重试。
- MVP 使用 PostgreSQL + Outbox Event + Worker + Redis Queue；暂不引入 Temporal。
- 如果后续出现长周期、多补偿、复杂等待和跨系统事务恢复需求，再评估 Temporal 或同类 Durable Execution 引擎。

### 6.7 Skill Library

Skill 的来源是全局 Skill Library。

职责：

- 上传 Skill Package（`.zip`）
- 审核 Skill
- 发布 Skill
- 版本管理
- 绑定到 Job Template
- 分发到 Digital Employee Profile

Platform 不提供文件级 Skill 编辑，不维护文件数量，也不改写 Hermes 原生 `SKILL.md` 内容。Skill Package 是发布、版本管理和下发的最小单元。

Skill Package 约束：

- 必须是 `.zip` 文件。
- 包内至少包含 `SKILL.md`。
- 可包含 `scripts/`、`references/`、`templates/`、`assets/` 等支持文件。
- 平台记录包文件名、入口文件、版本、状态、分类和说明。

Hermes 实际从当前 `HERMES_HOME/skills/` 扫描 Skill。在 Profile 模式下，一个 Digital Employee 的 `HERMES_HOME` 指向该员工自己的 Profile，因此 Skill 下发目标是该员工 Profile 内的 `skills/` 目录。

推荐下发路径：

```text
~/.hermes/profiles/{employee_slug}/skills/{skill_name}/SKILL.md
```

推荐下发流程：

1. 管理员在 Skill Library 中上传 Skill Package。
2. Platform 校验 `.zip` 包至少包含 `SKILL.md`。
3. 管理员发布 Skill。
4. Job Template 只能绑定已发布 Skill。
5. 创建 Digital Employee 时，Instance Manager 解压对应 Skill Package，并把绑定 Skill 复制到员工 Profile 的 `skills/` 目录。
6. 更新 Job Template 或 Skill 版本时，Platform 计算受影响员工，并触发 Profile skill sync。
7. 对运行中的 Hermes Instance，Platform 调用 `/reload-skills` 对应能力或重启 Instance，使新 Skill 被重新扫描。

MVP 推荐使用复制方式分发 Skill 包，而不是符号链接。复制会占用更多磁盘，但可以给每个员工保留 Skill 版本快照，便于审计、回滚和隔离。

关键字段：

```python
class SkillDefinition:
    name: str
    display_name: str
    category: str
    version: str
    description: str
    status: str  # draft | published
    entry_file: str  # usually SKILL.md
    package_file: str  # uploaded .zip filename
```

### 6.8 Tool Registry

Tool Registry 统一维护 Digital Employee 运行时可调用的 Tool。Tool 是接口权限，Skill 是能力包，两者不能混用。

Tool 分类：

- Hermes Built-in Tool：Hermes Agent 自带的通用工具能力，如文件、Shell、Web/Search 等。它不是业务系统集成，但是否开放仍要受 Job Template 的 Tool 白名单控制。
- Business Tool：Platform 自定义的业务工具，主要用于访问 CRM、工单、邮件、审批、知识检索、内部业务 API 等企业系统。

职责：

- 维护 Tool 元数据、分类和说明
- 维护 Tool 调用方式
- 维护 Tool 鉴权方式
- 维护 Tool Idempotency Policy
- 标记 Tool 是否可写、是否高风险、是否需要审批
- 标记 Tool 是否必须产生 Audit Event
- 发布或停用 Tool
- 供 Job Template 选择 Tool 白名单

边界：

- Job Template 不维护自由字符串工具名，只绑定已发布/启用 Tool。
- 创建 Digital Employee 时，Platform 根据 Job Template 的 Tool 白名单给 Hermes Instance 注入可用工具配置。
- Knowledge Retrieval Tool 是 Tool Registry 中的内置 Tool，但它按 Job Template 的 Knowledge Source 权限动态鉴权。
- Tool 绑定变化属于 Profile/runtime 配置变化，通常需要 reload 或重启 Hermes Instance 才能让工具清单重新生效。
- Hermes Built-in Tool 不经过 Platform Tool Gateway，但可以通过 Hermes Profile allowlist、`pre_tool_call` / `post_tool_call` hook 和 middleware 做预置约束、阻断和审计。
- Hermes Built-in Tool 的 MVP 默认约束只维护预置策略标签和说明，不允许管理员编写复杂规则 DSL。
- Platform 只能导入/登记 Hermes 已发现的内置工具并维护启停、风险、读写、审计和约束说明；不能在页面里手工创建不存在的 Hermes Built-in Tool 实现。
- Business Tool 默认统一通过 Platform Tool Gateway 调用；Hermes Profile 中只写 Tool schema、Platform endpoint 和 Employee Service Token。
- 除 Hermes Built-in Tool 外，所有 Platform 管理 Tool 都必须配置 Tool Idempotency Policy；外部写 Tool 无法证明幂等时不得发布。
- 第三方 API Key、CRM token、邮件凭证等业务系统密钥只保存在 Platform，不下发到 Hermes Profile。
- Platform Tool Gateway 校验 Employee Service Token、employee_id、Job Template Tool 白名单、Tool 状态、审批要求、审计要求和幂等策略后，再调用真实业务系统。
- 直连运行时工具不是 MVP 默认方式；如未来需要开放少量本地只读工具，必须显式标记为 `direct_runtime` 并单独评审。

Tool 风险默认规则：

- `read` Tool：只查询业务系统，例如查 CRM 客户、查工单、查订单、查知识。默认需要审计，通常不需要审批。
- `write` Tool：会改变业务系统状态，例如发邮件、改 CRM、提交工单、退款申请、更新客户标签。默认需要审计，高风险写操作需要 Approval。
- `high_risk` Tool：即使是读操作，只要访问未脱敏客户信息、审计原始证据、财务数据等敏感数据，也需要更高审计级别，必要时需要 Approval。

Tool Idempotency Policy：

- 适用范围：所有 Platform 管理 Tool 必须配置；Hermes Built-in Tool 例外，因为它不经过 Platform Tool Gateway，只能通过 Hermes 原生控制点做约束和审计。
- 读 Tool：默认幂等，但仍需声明缓存/重试边界、超时后是否可重试、是否会触发外部审计或计费副作用。
- 写 Tool：必须配置 idempotency key 来源、外部业务对象 ID 提取方式、重复请求处理方式、结果查询方式和不可重放条件。
- idempotency key 默认由 Platform Tool Gateway 生成，推荐组成至少包含 `employee_id + goal_run_id + work_item_id + tool_id + request_hash`。
- 如果外部系统强制要求自己的幂等键字段，Gateway 将 Platform 生成的 key 透传或映射到外部字段；不能把幂等控制权交给 Hermes。
- Tool Gateway 必须保存幂等记录，包含请求摘要、审批记录、外部业务对象 ID、外部响应 ID、状态、审计 ID 和过期时间。
- 重复调用时，Tool Gateway 应返回已有结果、查询外部状态后返回结果，或拒绝并转人工；不能盲目再次执行外部写操作。
- 无法声明幂等策略的外部写 Tool 不允许发布，只能停留在 draft/testing 状态。

Tool Gateway 需要同时考虑 Goal Risk Level 和 Tool Risk Level：

- L1 Goal 不应调用写 Tool。
- L2 Goal 可以创建内部草稿或任务，外部写 Tool 仍按 L3 处理。
- L3 Goal 调用写 Tool 必须经过 Approval 和 Audit。
- L4 Goal 不允许 AI 直接执行最终决策动作；Tool Gateway 只能允许材料准备、证据收集、草稿生成等辅助性 Tool。

Tool Entitlement：

- Job Template 绑定 Tool 时形成 Tool Entitlement。
- Tool Entitlement 不只是“允许/不允许”，还可以收窄参数边界。
- 示例：只能查本部门客户、退款申请金额上限 500 元、只能创建草稿邮件不能直接发送、只能访问指定业务对象类型。
- Digital Employee 从当前发布版 Job Template 继承 Tool Entitlement。
- 员工级配置不能新增模板外 Tool。
- 员工级配置可以禁用模板内某个 Tool，或进一步收窄 Tool 参数。
- 临时授权高风险 Tool 必须通过 Approval，产生 Audit Event，并设置过期时间；MVP 可先不实现临时授权。

Business Tool MVP 接入形态：

- `platform_api`：调用 Platform 自有接口，例如知识检索、审批发起、员工目录查询。MVP 优先支持。
- `http_api`：调用企业业务系统 HTTP API。配置 Base URL、Path、Method、Headers 模板、认证引用、请求 schema、响应 schema。
- `mcp_server`：连接受控 MCP Server，用于后续接入更复杂工具集合。MVP 可以先做配置占位。

MVP 暂不支持：

- 管理员上传 Python/JS 代码作为 Tool。
- 在 UI 中编写任意脚本转换请求或响应。
- Hermes 直接执行业务系统 SDK。

Credential 管理：

- Credential 由本系统内置保存和管理，不接入第三方 Secret Manager。
- Credential 保存第三方业务系统凭证，如 API Key、OAuth token、Basic Auth、Webhook secret。
- Tool Definition 只保存 `credential_ref`，不保存明文密钥。
- Job Template 绑定 Tool 时不能修改 Credential，只能选择 Tool 和配置 Tool Entitlement。
- Hermes Profile 不保存业务系统 Credential。
- Credential 轮换不需要修改 Job Template；后续 Platform Tool Gateway 调用自动使用新凭证。
- Audit Event 只记录 `credential_ref` 和脱敏元数据，不记录密钥值。

Tool 生命周期：

- `draft`：可编辑，不可被 Job Template 绑定。
- `testing`：可做连接测试、schema 测试和 mock 调用。
- `published`：可被 Job Template 绑定。
- `disabled`：运行时不可调用；已绑定模板发布时必须给出风险提示。
- `deprecated`：仍可运行但不建议新增绑定，用于平滑迁移。

Tool 发布前校验：

- 所需 Credential 必须为 active。
- 请求 schema 和响应 schema 完整。
- `write` 或 `high_risk` Tool 必须配置 Approval 和 Audit。
- 除 Hermes Built-in Tool 外，Tool Idempotency Policy 必须完整；外部写 Tool 必须通过幂等测试或 mock 幂等测试。
- Platform Tool Gateway 测试调用通过，至少 mock 调用通过。
- `http_api` Tool 的 Base URL、Path、Method 必须完整。

Tool 白名单传播：

- Job Template 草稿修改 Tool 不影响运行时。
- 发布新 Job Template Version 时，Platform 计算受影响 Digital Employee。
- 发布确认页展示 Tool 增删 diff、风险等级变化，以及是否涉及 `write` / `high_risk` Tool。
- 对活跃员工执行 Tool sync：
  - 更新 Profile 中的 Tool schema、Platform endpoint、allowed tool list。
  - 尝试调用 Hermes reload tools。
  - reload 失败或 Hermes 不支持时，重启 Hermes Instance。
- Credential 轮换不需要 Job Template 发布，也不需要 Hermes reload；Platform Tool Gateway 自动使用新凭证。
- Tool Definition 被 `disabled` 后，Platform Tool Gateway 立即拒绝运行时调用；模板发布页和员工详情显示风险。

Tool 调用审计：

- 每次 Business Tool 调用都产生 `tool_call` Audit Event。
- 默认记录：`employee_id`、`tool_id`、`tool_version`、`template_version`、`request_id`、`started_at`、`ended_at`、`status`、`latency`、`read_write`、`risk_level`、`approval_id`。
- `read/low` Tool：记录元数据和脱敏摘要，不记录完整请求/响应。
- `write` Tool：记录请求摘要、业务对象 ID、变更结果、外部系统返回 ID。
- `high_risk` Tool：记录 `evidence_refs`，保留可复核证据；UI 默认脱敏展示。
- Tool 调用失败也必须记录，尤其是鉴权失败、审批缺失、越权参数、外部系统错误。
- 普通成功 Tool 调用默认不影响 KPI；红线、越权、拒绝、重复失败等异常场景可通过 Audit Rule 影响 KPI。

Tool Gateway 标准错误：

- `tool_not_allowed`：不在 Tool 白名单。
- `tool_disabled`：Tool 已停用。
- `credential_unavailable`：Credential 缺失、禁用或轮换失败。
- `approval_required`：需要审批。
- `approval_denied`：审批拒绝。
- `constraint_violation`：参数超出 Tool Entitlement。
- `external_system_error`：业务系统调用失败。
- `tool_timeout`：超时。
- `rate_limited`：被限流。
- `audit_required_failed`：审计写入失败，高风险 Tool 不允许继续。

Tool Gateway 返回给 Hermes 的错误结构：

```python
class ToolGatewayError:
    error_code: str
    message: str
    retryable: bool
    approval_id: str | None
    audit_id: str
    safe_details: dict
```

不得返回第三方系统原始报错、密钥、内部堆栈或未脱敏敏感数据。

审批执行模式：

- 审批由 Platform 业务规则决定，不由发起调用的 Hermes Agent 自己审批。
- 默认审批人是 Digital Employee 的直属管理者或部门负责人；高风险 Business Tool 可叠加 Tool Owner；高风险 Hermes Built-in Tool（如 terminal/process）由平台管理员或运维负责人审批；临时扩大工具权限需要部门负责人和平台管理员。
- MVP 审批入口为 Platform 内部审批中心，审批单展示员工、岗位模板、Tool、风险等级、参数摘要、触发原因、审计上下文、过期时间和审批意见。飞书、钉钉、邮件等外部通知可后续接入。
- Business Tool 需要审批时，Platform Tool Gateway 创建 Approval Request，返回 `approval_required`、`approval_id` 和 `audit_id` 给 Hermes，不调用真实业务系统。审批通过后由 Hermes 携带 `approval_id` 重试 Tool 调用，Gateway 校验后执行。
- Hermes Built-in Tool 需要审批时，Platform 的 Hermes 插件通过 `pre_tool_call` hook 阻断本次调用并返回安全 Tool result；Hermes 会把 blocked Tool result 追加回模型上下文。审批通过后采用显式重试模式。若后续要做“原地等待审批后继续”，可复用或镜像 Hermes 现有 gateway dangerous-command approval queue，但 MVP 不默认采用阻塞等待。

工具管理页面 MVP 范围：

- 菜单位置：系统配置中独立菜单 `工具管理`，放在 `Skill 管理` 与 `模型配置` 之间。
- `工具列表`：展示 Tool 名称、类型、管理方（Hermes 内置 / Platform）、接入形态、读写、风险、审批、审计、状态、绑定模板数。
- `新增/编辑 Tool`：按接入形态动态展示字段。`hermes_builtin` 是登记流程，只选择 Hermes 已发现工具，Hermes 名称、toolset、读写、说明和 schema 只读展示；Platform 只维护启用/停用/废弃状态、风险等级、审计要求和预置约束策略。`platform_api` 维护 Platform 内部接口；`http_api` 维护 Base URL、Path、Method、Credential 和 schema；`mcp_server` MVP 只登记 server/tool 名称和风险控制元数据。
- `幂等策略`：除 `hermes_builtin` 外必填。页面维护 idempotency key 来源、业务对象 ID 提取、重复调用处理、结果查询方式、不可重放条件和过期时间。写 Tool 未完成幂等配置时不能发布。
- `凭证管理`：本系统内置 Credential 列表，支持创建、编辑、轮换、禁用，显示 masked value。
- `调用审计`：展示 `tool_call` Audit Event，可先做 Audit Event 的过滤视图。
- `Hermes 内置工具`：只做显示、启停和风险标注，不配置第三方 Credential。
- Job Template 的工具白名单从 Tool Registry 中选择 `published` / enabled Tool，不再使用硬编码字符串。

关键字段：

```python
class ToolDefinition:
    tool_id: str
    name: str
    display_name: str
    category: str
    description: str
    invocation_type: str
    auth_type: str
    managed_by: str  # hermes_builtin | platform
    integration_type: str  # hermes_builtin | platform_api | http_api | mcp_server
    credential_ref: str | None
    endpoint_config: dict
    schema_config: dict
    risk_level: str
    read_write: str  # read | write
    requires_approval: bool
    audit_required: bool
    idempotency_policy: ToolIdempotencyPolicy | None  # required unless hermes_builtin
    default_constraints: dict
    status: str  # draft | testing | published | disabled | deprecated
    last_test_status: str
    last_tested_at: datetime | None

class ToolIdempotencyPolicy:
    key_source: str  # platform_generated by default; external_required only maps Gateway key outward
    key_fields: list[str]  # default: employee_id, goal_run_id, work_item_id, tool_id, request_hash
    external_key_mapping: dict | None
    business_object_id_path: str | None
    duplicate_handling: str  # return_existing | query_external_status | reject_for_manual_review
    result_lookup: dict
    non_replayable_conditions: list[str]
    ttl_seconds: int

class ToolEntitlement:
    template_id: str
    tool_id: str
    constraints: dict
    approval_override: bool | None
    audit_override: bool | None

class EmployeeToolOverride:
    employee_id: str
    tool_id: str
    disabled: bool
    narrowed_constraints: dict

class ToolSyncResult:
    employee_id: str
    template_version: str
    added_tools: list[str]
    removed_tools: list[str]
    reload_status: str  # reloaded | restarted | failed

class ToolCallAuditPayload:
    employee_id: str
    tool_id: str
    tool_version: str
    template_version: str
    request_id: str
    status: str
    latency_ms: int
    read_write: str
    risk_level: str
    approval_id: str | None
    summary: dict
    business_object_ids: list[str]
    external_response_id: str | None
    evidence_refs: list[str]

class Credential:
    credential_id: str
    name: str
    type: str  # api_key | oauth_token | basic_auth | webhook_secret
    owner: str
    masked_value: str
    status: str  # active | rotated | disabled
    rotated_at: datetime | None
```

### 6.9 Knowledge Adapter / Knowledge Source

Knowledge Source 的来源是外部 Knowledge Base。Platform 不自建企业知识库；首个标准适配器选择 RAGFlow。

职责：

- 维护 RAGFlow Knowledge Connection
- 同步或登记 RAGFlow dataset 为 Platform Knowledge Source
- 管理多个 Knowledge Source 与 Job Template 的绑定授权
- 通过 Knowledge Retrieval Tool 为 Digital Employee 运行时提供统一检索入口
- 记录检索调用、来源引用和审计信息

外部 Knowledge Base 职责：

- 文档上传
- 文档解析
- 分块
- 向量化和索引
- 检索与来源引用

因为当前是单 Organization，不需要“知识源需求 → 租户真实知识源”的映射层。Job Template 可以直接绑定真实 Knowledge Source。

MVP 边界：

- Platform 不创建 RAGFlow dataset。
- Platform 不代理文档上传。
- Platform 不暴露文档解析、分块、embedding、索引等配置。
- 操作人员在 RAGFlow 控制台完成文档和解析配置。
- Platform 知识库页面只负责连接 RAGFlow、同步或登记 dataset、维护 Platform 展示名和启停状态、提供检索预览，并把一个或多个 Knowledge Source 授权给 Job Template。

RAGFlow 适配边界：

```python
class KnowledgeConnection:
    id: str
    provider: str  # ragflow
    base_url: str
    api_key_ref: str
    status: str  # connected | disconnected

class KnowledgeSource:
    name: str
    connection_id: str
    provider: str  # ragflow
    external_scope_type: str  # dataset
    external_scope_id: str
    sync_status: str  # unregistered | active | missing
    last_synced_at: str | None
    description: str
    status: str  # active | disabled

class KnowledgeAdapter:
    async def list_sources(self) -> list[KnowledgeSource]: ...
    async def retrieve(self, source_ids: list[str], query: str, top_k: int) -> KnowledgeRetrievalResult: ...
```

岗位模板只绑定 Platform 的 Knowledge Source，不直接暴露 RAGFlow 的内部字段。首版 Knowledge Source 映射到 RAGFlow dataset。一个 Job Template 可以绑定多个 Knowledge Source；Digital Employee 运行时只能在模板授权的 source 集合内检索，Knowledge Adapter 负责合并检索结果和保留来源引用。

运行时检索流程：

1. Instance Manager 为每个 Hermes Instance 配置 Knowledge Retrieval Tool。
2. Instance Manager 为该员工运行时签发 Employee Service Token，并写入 Profile 的 Platform Tool 配置。
3. Tool 可以通过 Hermes 原生 Tool 或 MCP Server 暴露，但只调用 Platform API。
4. Hermes Instance 发起检索时，Tool 带上 Employee Service Token、Digital Employee 身份和查询文本调用 Platform Knowledge Adapter。
5. Platform 校验 Employee Service Token，并确认它绑定当前 `employee_id` 和 Profile/Instance。
6. Platform 根据 Digital Employee 当前发布版 Job Template 获取授权 Knowledge Source 集合，并叠加员工级禁用项。
7. Platform 校验请求中的 source 范围，不允许越权访问未绑定的 Knowledge Source。
8. Platform 使用 Knowledge Connection 中的 RAGFlow 凭证调用 RAGFlow。
9. Platform 返回标准化检索结果、来源引用和 `audit_id`。

RAGFlow API Key 不下发到 Hermes Profile。Profile 只持有访问 Platform 检索接口所需的 Employee Service Token。员工停用、岗位模板变更、Profile 重建或 Instance 重建时，Platform 可以轮换或吊销该 Token。

Knowledge Source 权限变更实时生效，不要求重启 Hermes Instance。Knowledge Retrieval Tool 不缓存授权集合；每次检索由 Platform 根据当前发布版 Job Template 动态鉴权。

检索返回结构：

```python
class KnowledgeRetrievalResult:
    answer: str | None
    hits: list[KnowledgeHit]
    warnings: list[KnowledgeWarning]
    audit_id: str

class KnowledgeHit:
    content: str
    source_name: str
    document_name: str
    chunk_id: str
    score: float
    citation: str

class KnowledgeWarning:
    source_id: str
    code: str  # missing | disabled | provider_error
    message: str
```

`citation` 和 `audit_id` 是必填字段。MVP 可以不生成综合答案，但必须返回命中的内容片段、来源引用和审计 ID，方便人工复核、红线判断、KPI 评价和问题追踪。部分 Knowledge Source 不可用时必须返回 `warnings`；全部不可用时返回可审计错误而不是空结果。

检索预览与运行时检索分离：

- `retrieve-preview` 是管理员配置验证接口，可直接选择 Knowledge Source，不按 Job Template 鉴权。
- `retrieve-preview` 必须记录管理员、query、source_ids、命中摘要和 `audit_id`。
- `POST /api/v1/knowledge/retrieve` 是员工运行时接口，必须使用 Employee Service Token，并按当前发布版 Job Template 动态鉴权。
- 预览结果不能作为 Digital Employee 的运行时权限依据。

### 6.10 KPI / Quota / Audit

KPI 输入：

- Goal 完成率
- 按 Goal Risk Level 分组的完成率和错误率
- Business Outcome Metric 达成情况
- 响应时效
- 协作贡献
- Artifact 首次验收通过率
- Artifact 返工率
- Artifact 采用率
- Red Line 触发次数
- Token 消耗
- Escalation 率

预算控制：

- Organization Quota：平台整体每日 Token 硬上限，代表成本或账户风险边界。
- Goal Budget：单个 Goal Run 的 Token 执行预算，防止一个目标通过 Delegation 扩散造成成本失控。
- Department、Digital Employee、Work Item 只作为 Usage Analytics 维度，不在 MVP 中产生独立配额阻断。

预算周期：

- Organization Quota 按平台时区自然日重置。
- Goal Budget 随 Goal Run 创建，直到该 Goal Run 完成、取消、失败或过期。
- 月度 Token 消耗进入 KPI 和报表，但 MVP 不做月配额硬控或员工停用。

策略：

- 接近 Organization Quota 或 Goal Budget 上限时预警。
- 不因接近上限降速。
- Organization Quota 超限后只阻断新的高成本运行时调用。
- Goal Budget 超限后只阻断该 Goal Run 的新模型成本调用。
- 部门、员工和 Work Item 超出历史均值或异常消耗时只告警和进入报表，不做阻断。

Organization Quota 超限后的阻断范围：

- 阻断数据面调用：Digital Employee 新的 LLM 调用、知识检索后的答案生成、自动委托产生的新任务执行。
- 不阻断控制面动作：管理员登录和查看、员工停止/下线、审计日志写入、告警通知、Token Ledger/KPI/历史产物查看、预算调整。
- 原因：超限后仍必须保留管理能力，便于止损、排查和恢复。

Goal Budget 超限后的行为：

- Platform 将 Goal Run 标记为 `budget_blocked` 或 `blocked`，并记录阻断原因。
- 保留 Hermes Instance，不默认杀进程或删除运行时上下文。
- 拒绝该 Goal Run 下新的模型成本调用，包括 Root Goal Owner 继续推理、自动委托产生的新执行、知识检索后的答案生成。
- 允许控制面动作：查看 Goal Run、Execution Graph、Artifact、Trace、Token Ledger，管理员可调整 Goal Budget、取消 Goal 或结束 Goal。
- 原因：保留诊断上下文，避免因预算超限丢失现场；恢复路径也更清晰。

计量规则：

- 请求开始前只做预算预检：如果 Organization Quota 或当前 Goal Budget 已经超限，则按策略阻断或告警。
- 请求中不按预估 Token 预扣减。
- 请求完成后以 Hermes API 返回的 usage 写入 Token Ledger；该 usage 来自模型供应商返回值。
- 如果供应商不返回 usage，Platform 使用估算器补记，并标记 `estimated=true`。
- 预算判断基于已结算用量，不因请求前估算误差停用员工或杀掉 Hermes Instance。

Hermes token usage 接入结论：

- 每个 Digital Employee 是一个独立 Hermes Instance；Platform 调用该 Instance 后，可以从 Hermes API Server 的同步响应、structured run 完成事件或 run status 中获取本次运行的 usage。
- Hermes 内部会把 provider usage 规范化并累加到 session counters，包括 input/output/cache/reasoning/prompt/completion/total 等字段。
- Platform 不能把 Hermes 进程内累计值或 Hermes session DB 当作配额账本；它们是运行时遥测。Platform 必须按 `employee_id + request_id/run_id + model_config_id` 写自己的 Token Ledger，并用幂等键避免重复入账。
- 如果某个 Hermes 调用路径只暴露 session 累计值，Platform Adapter 必须换算为本次调用增量，或改用能返回 per-run usage 的接口，避免重复结算。

Token Ledger 关键字段：

```python
class TokenLedgerEntry:
    employee_id: str
    department: str
    goal_id: str | None
    goal_run_id: str | None
    work_item_id: str | None
    model_config_id: str
    hermes_instance_id: str
    hermes_session_id: str | None
    hermes_run_id: str | None
    prompt_tokens: int
    completion_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int
    total_tokens: int
    estimated: bool
    occurred_at: datetime
    request_id: str
```

Audit 范围：

- Red Line 触发
- Approval
- Escalation
- 员工启停
- 模板变更
- Skill / Knowledge Source 变更

Audit 规则边界：

- Audit Event 是关键事实的不可篡改记录。
- Audit Rule 决定事件严重级别、通知对象、是否进入 KPI、是否需要人工复核。
- Audit Rule 不替代 Red Line、Approval、Organization Quota、Goal Budget 等执行逻辑。
- 红线拦截、审批等待、预算阻断等动作由各自机制执行；审计层负责记录、告警、复核和追踪。
- Audit Event 主体字段、原始 payload、命中的 `rule_id` 和 `rule_version` 产生后不可编辑。
- 管理员只能追加 Audit Disposition，如误报、已确认、已处理、无需处理或升级处理。
- Audit Rule 后续调整不回写历史事件，只影响新事件。
- 敏感证据允许在 UI 中脱敏展示，但原始证据需保留并受权限控制。
- Audit 使用统一事件模型。不同场景通过 `event_type`、可选 subtype 和结构化 `payload` 区分，不为每类事件拆独立表和独立页面。

Audit Event MVP 类型：

- `red_line_triggered`
- `approval_requested`
- `approval_decided`
- `escalation_created`
- `abnormal_shutdown`
- `sensitive_operation`
- `budget_blocked`
- `knowledge_preview`
- `template_published`
- `skill_package_changed`

Audit Event 关键字段：

```python
class AuditEvent:
    event_id: str
    event_type: str
    subtype: str | None
    severity: str
    actor_type: str
    actor_id: str
    employee_id: str | None
    department: str | None
    resource_type: str | None
    resource_id: str | None
    rule_id: str
    rule_version: str
    kpi_affecting: bool
    review_required: bool
    occurred_at: datetime
    payload: dict
    evidence_refs: list[str]
```

Audit Rule MVP 条件范围：

- `event_type`
- `severity`
- `department`
- `employee_id`
- `grade`
- `resource_type`
- `actor_type`
- `contains_sensitive_data`
- `red_line_category`
- `operation_name`
- `business_hours` / 非工作时间
- `estimated_usage`

Audit Rule MVP 动作范围：

- 设置 severity
- 是否通知
- 通知对象
- 是否需要人工复核
- 是否计入 KPI
- 保留期限
- 建议后续动作

MVP 不支持管理员编写 JS/Python/表达式脚本，不支持规则直接调用外部接口，也不支持规则直接执行停员工、改权限、发布模板等运行时动作。后续如果有真实需求，再扩展更强的规则能力。

Audit 通知边界：

- MVP 优先实现平台内通知记录。
- Audit Rule 可配置通知对象：Admin、员工直属上级、部门负责人、指定用户/角色。
- 页面可展示邮件、飞书/钉钉 Webhook 等外部渠道配置，但 MVP 可标记为未接入或待配置。
- 审计通知不阻塞业务流程。
- 通知失败不改变原 Audit Event，可记录为通知状态或单独的 `notification_failed` Audit Event。

Audit Event 默认 KPI 影响：

- 默认计入 KPI：`red_line_triggered`、`escalation_created`、Goal 级 `budget_blocked`、可归因到员工实例或运行配置的 `abnormal_shutdown`。
- 条件计入 KPI：`approval_decided` 且结果为拒绝，拒绝原因是员工越权或证据不足。
- 默认不计入 KPI：`approval_requested`、审批通过的 `approval_decided`、`knowledge_preview`、`template_published`、`skill_package_changed`、普通敏感管理员操作。
- Audit Rule 可以覆盖 `kpi_affecting`，用于特定业务场景。

异常停机定义：

- `abnormal_shutdown` 只表示非预期运行故障：Hermes Instance 进程意外退出、健康检查连续失败、启动/重启失败、系统 OOM 或外部进程管理器杀掉。
- 已上岗员工运行时不健康时，Platform 先暂停调度并尝试有限次数自动恢复；超过恢复上限后生成 `abnormal_shutdown` Audit Event。
- 管理员手动停止员工是 `sensitive_operation`，subtype 为 `employee_stopped_by_admin`。
- 预算硬控是 `budget_blocked`，不归类为异常停机。
- Job Template 发布、Skill 变更或模型配置变更导致的计划重载/重启，不归类为异常停机。
- `abnormal_shutdown` 不自动把员工生命周期改为 `disabled`；是否需要停用由管理员处理。
- `abnormal_shutdown` 是否计入 KPI 取决于 attribution：平台基础设施原因不扣员工 KPI；员工 Profile、Skill 或工具配置导致反复崩溃时，可以计入员工风险指标。

敏感操作范围：

- `admin_sensitive_operation`：
  - 查看未脱敏审计证据
  - 导出审计日志
  - 修改或发布 Job Template
  - 上传或发布 Skill Package
  - 修改 Knowledge Connection 或 API Key 引用
  - 修改 Model Configuration 或 API Key
  - 调整 Organization Quota 或 Goal Budget
  - 启停员工或解除 `budget_blocked`
  - 轮换 Employee Service Token
- `employee_sensitive_operation`：
  - Agent 尝试发送邮件、修改 CRM、提交工单、调用外部写操作等。
- MVP 审计页优先覆盖管理员敏感操作；员工敏感操作先通过 Approval 和 Tool 相关 Audit Event 体现。

审计保留和导出：

- 默认保留 180 天。
- 高严重级别事件保留 365 天：红线、高危敏感操作、可归因异常停机、预算阻断。
- Audit Rule 可配置保留期限，但只从预设值中选择：90 / 180 / 365 / 永久。
- 导出审计日志本身是敏感操作，必须产生 `sensitive_operation` Audit Event。
- 导出内容默认脱敏。
- 导出未脱敏证据需要 Admin 权限、二次确认和填写理由。
- MVP 不做外部归档仓库或 WORM 存储，但后续设计需保留扩展空间。

审计规则测试：

- 编辑 Audit Rule 时可选择一条 mock 或最近 Audit Event 做“测试匹配”。
- 测试结果展示是否命中、命中的条件、计算后的 severity、是否通知、通知对象、是否需要复核、是否计入 KPI、保留期限。
- 测试不写入新 Audit Event，不发通知，不改变 KPI。

审计页面组织：

- MVP 保留一个菜单：`审计规则`。
- 页面内部使用 Tabs：
  - `审计事件`：事件列表、筛选、详情、追加 Disposition、导出。
  - `审计规则`：规则列表、新建/编辑、启停、测试匹配。
  - `通知记录`：平台内通知状态和失败原因。
  - `保留策略`：默认保留策略和规则覆盖情况。
- 后续如果事件量或运维职责扩大，再拆成 `审计中心` 和 `审计规则` 两个页面。

---

## 7. API 草案

### 7.1 员工

```text
GET    /api/v1/employees
POST   /api/v1/employees
GET    /api/v1/employees/{employee_id}
POST   /api/v1/employees/{employee_id}/start
POST   /api/v1/employees/{employee_id}/stop
POST   /api/v1/employees/{employee_id}/tokens/rotate
GET    /api/v1/employees/{employee_id}/health
GET    /api/v1/employees/{employee_id}/kpi
```

### 7.2 岗位模板

```text
GET    /api/v1/job-templates
POST   /api/v1/job-templates
GET    /api/v1/job-templates/{template_id}
PATCH  /api/v1/job-templates/{template_id}
POST   /api/v1/job-templates/{template_id}/publish
POST   /api/v1/job-templates/{template_id}/unpublish
```

### 7.3 目标与委托

```text
GET    /api/v1/goals
POST   /api/v1/goals
GET    /api/v1/goals/{goal_id}
POST   /api/v1/goals/{goal_id}/delegate
POST   /api/v1/goals/{goal_id}/artifacts
POST   /api/v1/goals/{goal_id}/complete
GET    /api/v1/goals/{goal_id}/delegations
```

### 7.4 目录与组织

```text
GET    /api/v1/directory
GET    /api/v1/directory/search
GET    /api/v1/departments
POST   /api/v1/departments
GET    /api/v1/org-chart
```

### 7.5 Skill / Knowledge

```text
GET    /api/v1/skills
POST   /api/v1/skills                  # multipart .zip package + metadata
POST   /api/v1/skills/{skill_id}/publish

GET    /api/v1/knowledge-connections
POST   /api/v1/knowledge-connections
POST   /api/v1/knowledge-connections/{connection_id}/test
POST   /api/v1/knowledge-connections/{connection_id}/sync-datasets
GET    /api/v1/knowledge-sources
POST   /api/v1/knowledge-sources
PATCH  /api/v1/knowledge-sources/{source_id}
POST   /api/v1/knowledge-sources/{source_id}/retrieve-preview
POST   /api/v1/knowledge/retrieve        # called by Knowledge Retrieval Tool with Employee Service Token
```

### 7.6 模型配置

```text
GET    /api/v1/model-configurations
POST   /api/v1/model-configurations
GET    /api/v1/model-configurations/{model_id}
PATCH  /api/v1/model-configurations/{model_id}
POST   /api/v1/model-configurations/{model_id}/enable
POST   /api/v1/model-configurations/{model_id}/disable
```

---

## 8. 部署方案

开发环境：

```text
React 管理后台
FastAPI Platform API
PostgreSQL
Redis
RAGFlow
Knowledge Adapter
Hermes Instances
```

初期可使用 Docker Compose：

```yaml
services:
  platform-api:
    build: ./platform
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://platform:***@postgres/platform
      - REDIS_URL=redis://redis:6379
    volumes:
      - hermes_profiles:/root/.hermes/profiles

  postgres:
    image: postgres:16

  redis:
    image: redis:7-alpine

  ragflow:
    image: infiniflow/ragflow

  knowledge-adapter:
    build: ./knowledge-adapter

volumes:
  hermes_profiles:
```

---

## 9. 落地路线图

### Phase 1：原型与后端骨架

- 固化单后台 UI 原型
- 搭建 FastAPI 项目骨架
- 实现 Job Template CRUD
- 实现 Digital Employee CRUD
- 实现 Employee Directory
- 手动启动 1 个 Hermes Instance 并验证 API 调用

### Phase 2：实例与目标协作

- 实现 Instance Manager
- 实现 Profile 渲染
- 实现 Skill 分发
- 实现 Goal & Delegation Engine
- 实现 PostgreSQL + Outbox Event + Worker + Redis Queue 的可靠执行骨架
- 验证 Goal → Work Item → Artifact submitted → Artifact accepted → 完成

### Phase 3：系统配置能力

- Skill Library
- RAGFlow 接入
- Knowledge Adapter / Knowledge Source
- Model Configuration
- Department / Organization Chart
- KPI
- Quota
- Audit

### Phase 4：产品化

- Docker Compose 部署
- 运行监控
- 实例预热和休眠
- 权限和审批
- 文档和演示数据

---

## 10. 当前状态

已完成：

- 单组织领域模型
- 单后台 UI 原型
- Goal-driven Delegation ADR（已被 Platform-controlled dynamic execution graph ADR 取代）
- Single-organization ADR
- Skill Package upload ADR
- RAGFlow Knowledge Adapter ADR
- Platform-mediated Knowledge Retrieval ADR
- Quota enforcement ADR（已被 MVP budget model ADR 取代）
- Audit rules observability ADR
- Tool Registry separates runtime tools from skills ADR
- Job Template System Prompt maps to Hermes identity ADR
- Platform-controlled dynamic execution graph ADR
- Delegation, Handoff, and Workflow are distinct ADR
- MVP budget model is Organization Quota and Goal Budget ADR
- Artifact Acceptance is separate from Approval ADR
- Platform persists Goal Run execution state ADR
- Goal Risk Level controls automation boundary ADR
- Template Evaluation before employee rollout ADR
- MVP starts with three Pilot Job Templates ADR
- Business Outcome Metrics bind to Job Template Versions ADR
- 三个 Pilot Job Template 范围已确定（企业经营情报、客服工单协调、销售方案协作）
- 配额策略 UI 原型（需按 Organization Quota + Goal Budget 调整）
- 审计规则 UI 原型

未完成：

- Platform 后端代码
- Hermes Instance 实际接入
- Skill Library 真实管理
- RAGFlow 接入
- Knowledge Adapter
- KPI / Quota / Audit 后端逻辑

---

## 11. 风险与注意事项

| 风险 | 影响 | 缓解 |
|------|------|------|
| Hermes 实例资源消耗 | 多员工常驻会消耗内存 | 空闲实例休眠、核心员工预热 |
| Goal 动态执行图失控 | 递归委托、环路、任务爆炸、预算超限、上下文越权、责任不清和 Goal 无法收敛 | 所有委托经过 Platform Gateway；Root Goal Owner 不变；使用结构化 Work Item 和 Execution Graph；限制深度、扇出、总节点数、并发、重试、预算和 Deadline；默认禁止子员工再委托；执行环路检测、权限校验、敏感委托审批、Artifact 验收、Trace、超时取消和故障恢复 |
| Skill 质量不稳定 | 影响员工行为 | Skill 审核、版本管理、回滚 |
| Knowledge Source 质量不稳定 | 导致回答错误 | 来源标注、知识源审核、人工审批 |
| Red Line 漏判 | 安全风险 | Prompt、工具白名单、输出过滤、审计多层防护 |

---

## 12. 文档维护说明

本文档已按 2026-06-26 的会话决策重写为单组织、单后台版本。后续如重新引入多组织或 SaaS 模式，必须新增 ADR，而不是直接把 Tenant 字段加回实现中。
