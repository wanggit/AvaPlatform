# Handoff: AI 数字员工平台

## Session Summary

本轮会话把项目从“多租户 SaaS + 超级管理后台/租户后台”回滚并重新收敛为：

> **单组织 AI 数字员工平台 + 一个管理后台**

核心变化：

1. **不做多租户**
   - `Tenant` 不再是核心领域概念。
   - 不再有租户隔离、租户开通、租户配额、跨租户审计。

2. **不再区分两个后台**
   - 删除“超级管理后台 / 租户后台”的产品模型。
   - 合并为一个管理后台。
   - 后台侧边栏分为“运营管理”和“系统配置”两组。

3. **岗位模板只有一种**
   - 不再有 Platform Job Template / Tenant Job Template。
   - 只保留 `Job Template`。
   - Job Template 直接绑定 Department、Skill、Knowledge Source、Tool 白名单、Red Line、模型和 Quota。

4. **Tool Registry 与 Skill 分离**
   - Skill 是 Hermes 能力包，通过 `.zip` Skill Package 上传、审核、发布和分发。
   - Tool 是 Digital Employee 运行时可调用的外部能力或 Platform API 能力。
   - Hermes Built-in Tool 与 Platform 自定义 Business Tool 分开管理。
   - Business Tool 主要用于访问 CRM、工单、邮件、审批、知识检索和内部业务 API 等业务系统。
   - Tool Registry 统一维护 Tool 的元数据、调用方式、鉴权方式、风险等级、读写属性、审批要求和审计要求。
   - Job Template 的工具白名单只能从已发布/启用 Tool 中选择，不能使用自由字符串。
   - Tool Registry 必须区分 `read` / `write` 和风险等级；读工具默认审计，写工具默认审计，高风险写工具默认需要 Approval。
   - 高风险读工具，如未脱敏客户信息、原始审计证据、财务数据，也需要更高审计级别，必要时需要 Approval。
   - Job Template 绑定 Tool 时形成 Tool Entitlement，可进一步限制参数范围，如部门范围、金额上限、草稿模式或业务对象范围。
   - Digital Employee 从 Job Template 继承 Tool Entitlement；员工级配置不能新增模板外 Tool，只能禁用或进一步收窄模板内 Tool。
   - 临时授权高风险 Tool 必须走 Approval、产生 Audit Event 并设置过期时间；MVP 可先不做临时授权。
   - Tool Gateway 返回标准安全错误：`tool_not_allowed`、`tool_disabled`、`credential_unavailable`、`approval_required`、`approval_denied`、`constraint_violation`、`external_system_error`、`tool_timeout`、`rate_limited`、`audit_required_failed`。
   - Tool Gateway 不向 Hermes 返回第三方系统原始报错、密钥、内部堆栈或未脱敏敏感数据。
   - Business Tool MVP 接入形态只支持 `platform_api`、`http_api` 和 `mcp_server` 配置占位。
   - MVP 不支持管理员上传 Python/JS 工具代码、不支持 UI 任意脚本转换、不支持 Hermes 直接执行业务系统 SDK。
   - Knowledge Retrieval Tool 是 Tool Registry 中的内置 Tool，但按 Job Template 的 Knowledge Source 权限动态鉴权。
   - Business Tool 默认通过 Platform Tool Gateway 调用；Hermes Profile 只持有 Tool schema、Platform endpoint 和 Employee Service Token。
   - 第三方系统凭证作为本系统内置 Credential 保存和管理，不接入第三方 Secret Manager；Tool 只引用 `credential_ref`。
   - Credential 不下发到 Hermes Profile，不由 Job Template 维护；轮换 Credential 不需要修改 Job Template。
   - Tool 生命周期为 `draft`、`testing`、`published`、`disabled`、`deprecated`。
   - Tool 发布前需校验 Credential active、schema 完整、write/high_risk 的 Approval/Audit、Gateway 测试或 mock 测试、HTTP 配置完整。
   - Job Template 草稿修改 Tool 不影响运行时；发布新版本后计算受影响员工并执行 Tool sync。
   - Tool sync 更新 Profile 中的 Tool schema、Platform endpoint、allowed tool list，优先 reload tools，失败或不支持时重启 Hermes Instance。
   - Credential 轮换不需要模板发布或 Hermes reload；Tool disabled 后 Gateway 立即拒绝运行时调用并在模板/员工处提示风险。
   - 所有 Business Tool 调用都产生 `tool_call` Audit Event；低风险读工具只记元数据和脱敏摘要，写工具记录业务对象和变更结果，高风险工具记录 evidence_refs。
   - Tool 调用失败必须审计；普通成功调用默认不影响 KPI，越权、拒绝、红线或重复失败可通过 Audit Rule 影响 KPI。
   - 系统配置新增独立菜单 `工具管理`，放在 `Skill 管理` 和 `模型配置` 之间。
   - 工具管理页 MVP：工具列表、新增/编辑 Tool 弹窗、凭证管理、调用审计、Hermes 内置工具视图。
   - Job Template 的工具白名单从 Tool Registry 的 `published` / enabled Tool 选择，不再使用硬编码字符串。

5. **Skill 与 Knowledge Source 的来源**
   - Skill 来自全局 `Skill Library`。
   - 新增或更新 Skill 必须上传一个 `.zip` Skill Package，包内包含该 Skill 的全部文件，至少包含 `SKILL.md`。
   - 平台不维护 Skill 的文件数量，也不在 MVP 中做文件级 Skill 编辑。
   - Knowledge Source 来自外部成熟 `Knowledge Base`，首个标准适配器选择 RAGFlow。
   - MVP 只支持一个活跃 RAGFlow Knowledge Connection；数据模型保留 `connection_id` 扩展位。
   - RAGFlow dataset 同步由管理员手动触发；新 dataset 先进入未登记状态，失联 dataset 只标记不自动删除。
   - 运行时遇到部分失联 Knowledge Source 时跳过并返回 warnings；全部失联时返回 `knowledge_sources_unavailable` 和 `audit_id`。
   - RAGFlow 负责文档上传、解析、分块、索引、检索和来源引用；Platform 只负责 Knowledge Source 引用、岗位绑定授权和运行时检索适配。
   - MVP 中 Platform 不创建 RAGFlow dataset，不代理文档上传，不暴露解析/分块/索引配置。
   - 一个 Job Template 可以绑定多个 Knowledge Source；Digital Employee 运行时只能在这些授权范围内检索。
   - MVP 中 Digital Employee 的知识权限只从 Job Template 继承；员工级别不能新增模板外 Knowledge Source。
   - Job Template 草稿修改不影响员工；发布新版本后，知识权限自动传播到继承该模板的活跃 Digital Employee。
   - Knowledge Source 权限变更实时生效，不需要重启 Hermes Instance；Tool 每次调用 Platform 动态鉴权。
   - Hermes Instance 通过 Knowledge Retrieval Tool 调用 Platform Knowledge Adapter，不直接访问 RAGFlow。
   - Knowledge Retrieval Tool 使用 Platform 签发的 Employee Service Token 鉴权，Token 绑定员工和当前 Profile/Instance。
   - Knowledge Retrieval Tool 返回结果必须包含来源引用和 `audit_id`；MVP 可以不生成综合答案。
   - 知识库页面的检索预览是管理员配置验证，可直接选择 Knowledge Source，但必须记录审计；员工运行时检索仍严格走 Job Template 权限。
   - 因为没有多租户，Job Template 可以直接绑定真实 Knowledge Source，不需要“知识源需求 → 租户知识源”的映射层。

5. **模型统一从 Model Configuration 选择**
   - 模型不再是岗位模板里的自由字符串。
   - `Model Configuration` 维护模型类型、Base URL、API Key、模型名称、上下文大小等信息。
   - Job Template、Digital Employee、Knowledge Base 等所有需要模型的地方都引用 Model Configuration。

6. **配额分层执行**
   - Organization Quota 是硬配额，代表平台级成本或账户风险边界。
   - Department Quota 默认是软配额，超限后触发管理告警，不停止整个部门。
   - Digital Employee Quota 由 Quota Policy 决定软/硬，超限后可以告警或进入 `quota_blocked`。
   - MVP 只执行 Daily Token Quota；月度 Token 消耗只进入 KPI/报表，不参与硬控。
   - 配额结算以模型供应商返回的实际 usage 为准；缺失 usage 时估算并标记 `estimated=true`。
   - Organization 硬配额超限只阻断数据面/模型成本调用，不阻断管理员控制面动作。
   - Digital Employee 硬配额超限时标记 `quota_blocked`，拒绝新的模型成本调用，但不默认杀 Hermes Instance。
   - Hermes Instance 会返回 per-run/session usage；Platform 必须写自己的 Token Ledger，不把 Hermes 内部 session DB 当配额账本。

## Key Decisions

- **Goal-driven delegation over DAG orchestration**
  - ADR: `docs/adr/0001-goal-driven-delegation.md`
  - 数字员工围绕 Goal 自主拆解、查询 Employee Directory、动态委托。

- **Single-organization platform with one admin backend**
  - ADR: `docs/adr/0002-single-organization-single-admin.md`
  - 项目不再按 SaaS 多租户平台设计。

- **Single Job Template model**
  - `Job Template` 是唯一岗位模板概念。
  - 创建 Digital Employee 时选择已发布 Job Template。

- **Single management backend**
  - 运营管理：Dashboard、Employee、Directory、Organization Chart、Goal、KPI
  - 系统配置：Job Template、Department、Skill、Knowledge、Model、Quota、Audit

- **Skill Package as distribution unit**
  - ADR: `docs/adr/0003-skill-package-upload.md`
  - Skill 以 `.zip` 包上传、发布和下发。
  - Skill Package 是版本管理、审核、分发、审计和回滚的最小单元。

- **RAGFlow as first Knowledge Adapter**
  - ADR: `docs/adr/0004-ragflow-as-first-knowledge-adapter.md`
  - Platform 不自建企业知识库。
  - 由于企业文档解析能力优先，首个外部知识库适配器选择 RAGFlow，而不是更轻量的 Dify。
  - MVP 只有一个活跃 RAGFlow Knowledge Connection。
  - Dataset 同步为手动触发，失联 Knowledge Source 不自动删除。
  - 失联 source 运行时不自动解绑；部分失联返回 warnings，全部失联返回可审计错误。

- **Platform-mediated Knowledge Retrieval**
  - ADR: `docs/adr/0005-platform-mediated-knowledge-retrieval.md`
  - Hermes Instance 只拿到 Knowledge Retrieval Tool。
  - RAGFlow API Key 只保存在 Platform 的 Knowledge Connection 中，不下发到员工 Profile。
  - Tool 通过 Employee Service Token 调用 Platform；Token 可在员工停用、模板变更、实例重建时轮换或吊销。
  - 检索结果必须包含来源引用和 `audit_id`，用于审计、复核和 KPI。
  - 管理员 Knowledge Preview 可绕过 Job Template 权限用于配置验证，但必须审计；运行时检索不能绕过权限。
  - 员工级配置不能扩大 Knowledge Source 权限，只能继承模板或缩小模板内范围。
  - 发布新 Job Template Version 会自动更新活跃员工的知识权限，发布前需要提示影响员工数量并记录审计。
  - Knowledge Source 权限变更不触发 Hermes 重启；Skill、模型配置、System Prompt 等 Profile 变更才需要 reload/restart。

- **Quota enforcement differs by level**
  - ADR: `docs/adr/0006-quota-enforcement-levels.md`
  - 平台总配额硬控，部门配额默认软控，员工配额按策略控制。
  - MVP 只执行日 Token 配额；月度只统计。
  - 请求前只做已超限预检，请求后按 provider usage 写 Token Ledger。
  - 平台总配额超限后只阻断会产生新增模型成本的数据面调用；控制面保持可用。
  - 员工硬配额超限后进入 `quota_blocked`；保留 Hermes Instance，管理员可查看、停止、调额和恢复。
  - Hermes 已有 usage 规范化和对外返回能力；Platform 按员工、请求、模型写独立 Token Ledger。

## Updated Documents

- `CONTEXT.md`
  - 改为单组织领域模型。
  - 移除 `Tenant`。
  - 移除 `Platform Job Template` / `Tenant Job Template`。
  - 新增/修正 `Organization`、`Skill Library`。

- `docs/adr/0002-single-organization-single-admin.md`
  - 记录从多租户双后台切换为单组织单后台的决策。

- `docs/adr/0003-skill-package-upload.md`
  - 记录 Skill 以 `.zip` 技能包上传和分发，不维护文件数量、不做文件级编辑。

- `docs/adr/0004-ragflow-as-first-knowledge-adapter.md`
  - 记录不自建知识库，并以 RAGFlow 作为首个标准 Knowledge Adapter。

- `docs/adr/0005-platform-mediated-knowledge-retrieval.md`
  - 记录知识检索必须经由 Platform Knowledge Adapter，不允许 Hermes Instance 直接访问 RAGFlow。

- `docs/adr/0006-quota-enforcement-levels.md`
  - 记录 Organization、Department、Digital Employee 三层配额的软硬执行边界。

- `start.md`
  - 已重写为单组织、单后台技术方案。
  - 删除旧的多租户设计、租户 API、租户 Profile 路径、租户级配额等内容。
  - Skill Library 更新为上传 `.zip` Skill Package，并由 Instance Manager 解压/复制到员工 Profile。
  - Knowledge Base 更新为外部 RAGFlow 接入，不再描述自建 pgvector 知识库。

- `web/`
  - 已合并为一个管理后台原型。
  - Skill 管理页已实现，新增/编辑 Skill 通过上传 `.zip` 技能包完成；岗位模板中的技能从已发布 Skill 列表中选择。
  - 模型配置页已实现，岗位模板和员工创建已从模型配置中选择模型。
  - 知识源接入页已实现：RAGFlow 连接、手动 dataset 同步、Knowledge Source 登记/编辑、失联风险提示、管理员检索预览。
  - `npm run build` 已通过。

## Current Project State

```text
ai-platform/
├── AGENTS.md
├── CONTEXT.md
├── start.md
├── handoff-ai-platform-20260626.md
├── start-proto.sh
├── docs/
│   ├── adr/
│   │   ├── 0001-goal-driven-delegation.md
│   │   ├── 0002-single-organization-single-admin.md
│   │   ├── 0003-skill-package-upload.md
│   │   ├── 0004-ragflow-as-first-knowledge-adapter.md
│   │   ├── 0005-platform-mediated-knowledge-retrieval.md
│   │   ├── 0006-quota-enforcement-levels.md
│   │   └── 0007-audit-rules-are-observability.md
│   └── agents/
│       ├── domain.md
│       ├── issue-tracker.md
│       └── triage-labels.md
├── hermes-agent-2026.6.19/      # 上游源码，只读
└── web/                         # React + Ant Design 原型
    └── src/
        ├── layouts/
        │   └── MainLayout.tsx
        ├── mocks/
        │   └── data.ts
        └── pages/
            ├── Dashboard.tsx
            ├── EmployeeManagement.tsx
            ├── EmployeeDirectory.tsx
            ├── OrganizationChart.tsx
            ├── GoalManagement.tsx
            ├── KPIReports.tsx
            ├── TemplateManagement.tsx
            ├── SkillManagement.tsx
            ├── ToolManagement.tsx
            ├── ModelManagement.tsx
            ├── KnowledgeManagement.tsx
            ├── QuotaManagement.tsx
            ├── AuditManagement.tsx
            ├── DepartmentManagement.tsx
            └── Placeholder.tsx
```

## UI Prototype

运行：

```bash
./start-proto.sh
```

默认地址：

```text
http://localhost:5173/
```

如果 5173 被占用，Vite 会自动切换到下一个端口。

当前页面：

- 概览看板
- 员工管理
- 员工目录
- 组织架构
- 目标管理
- KPI 报告
- 岗位模板
- 部门管理
- Skill 管理
- 模型配置
- 知识源接入
- 配额策略
- 审计规则

## Backend Status

Platform 后端尚未开始实现。

`start.md` 已给出新的后端路线：

1. FastAPI 骨架
2. Job Template CRUD
3. Digital Employee CRUD
4. Employee Directory
5. Instance Manager
6. Goal & Delegation Engine
7. Skill Library
   - Skill 以 `.zip` Skill Package 上传。
   - 后端校验包内至少包含 `SKILL.md`。
   - 发布后由 Instance Manager 解压/复制到员工 Profile。
8. RAGFlow 接入
   - 维护单个活跃 RAGFlow Knowledge Connection，模型保留 `connection_id`。
   - 手动同步 RAGFlow dataset，并登记为 Platform Knowledge Source。
   - 新 dataset 先未登记；失联 dataset 标记为 missing，不自动删除。
   - 运行时对 missing source 做降级处理，返回 warnings 或 `knowledge_sources_unavailable`。
   - 岗位模板可绑定多个 Platform Knowledge Source，不直接暴露 RAGFlow 内部字段。
   - Digital Employee 运行时通过 Knowledge Retrieval Tool 携带 Employee Service Token 调用 Platform Knowledge Adapter 检索。
   - 检索响应必须返回 hits、citation 和 `audit_id`。
9. Model Configuration
10. KPI / Quota / Audit
    - Organization Quota 硬控。
    - Department Quota 默认软控。
    - Digital Employee Quota 按 Quota Policy 告警或进入 `quota_blocked`。
    - 只实现 Daily Token Quota；月度 Token 只做 KPI/报表统计。
    - Token Ledger 以 provider usage 结算；无 usage 时估算并标记。
    - Organization 超限后仍允许管理员登录、查看、停止员工、写审计、发告警和调整配额。
    - Digital Employee 硬配额超限后进入 `quota_blocked`，不默认杀 Hermes Instance。
    - Token Ledger 从 Hermes API 返回 usage 入账；不得用 Hermes session 累计值重复结算。
    - Audit Rule 是记录、分级、通知、复核和 KPI 规则，不替代 Red Line、Approval、Quota 的执行机制。
    - Audit Event 是 append-only；事件主体和原始 payload 不可编辑，只能追加 Audit Disposition。
    - Audit Rule 调整不回写历史事件；历史事件保留命中的 `rule_id` 和 `rule_version`。
    - Audit 采用统一事件模型，通过 `event_type`、subtype 和 payload 区分红线、审批、升级、异常停机、敏感操作等场景。
    - Audit Rule MVP 只支持明确字段条件和固定动作，不支持脚本规则、外部调用或直接运行时执行动作；后续有需求再扩展。
    - Audit 通知 MVP 先做平台内通知；邮件、飞书/钉钉 Webhook 可作为配置占位。通知失败不阻塞业务，也不修改原 Audit Event。
    - Audit Event 默认 KPI 影响：红线、升级、配额阻断、可归因异常停机计入 KPI；审批请求、审批通过、知识预览、模板发布、Skill 变更和普通敏感管理员操作默认只留痕。
    - `abnormal_shutdown` 只表示非预期运行故障；管理员停止、配额阻断、计划重载/重启分别记录为敏感操作、`quota_blocked` 或配置变更事件。
    - Sensitive Operation 分为管理员敏感操作和员工敏感操作；MVP 审计页优先覆盖管理员敏感操作，员工敏感操作先通过 Approval/Tool Audit Event 体现。
    - Audit 默认保留 180 天，高危事件 365 天；规则只能选择 90/180/365/永久。导出审计日志本身是敏感操作，未脱敏导出需要 Admin 权限、二次确认和理由。
    - Audit Rule 编辑页需要轻量测试匹配能力，只预览命中结果、通知/KPI/保留策略，不写事件、不发通知、不改 KPI。
    - MVP 保留一个 `审计规则` 菜单，内部 Tabs 为审计事件、审计规则、通知记录、保留策略；后续量大再拆页面。

## Important Constraints

- `hermes-agent-2026.6.19/` 是上游源码，只读，不要修改。
- 后续不要重新引入 `Tenant` 字段，除非先新增 ADR 明确恢复多组织/SaaS 模型。
- 后续不要把 Skill 管理做成文件数量统计或文件级在线编辑；当前决策是上传、审核、发布和分发完整 `.zip` Skill Package。
- 后续不要自建企业知识库或直接引入 pgvector RAG 服务；当前决策是接入 RAGFlow，并在 Platform 层做 Knowledge Adapter。
- MVP 不在 Platform 中创建 RAGFlow dataset 或代理文档上传；这些操作留在 RAGFlow 控制台。
- 不要把 RAGFlow API Key 下发到 Hermes Profile；Hermes 只能通过 Platform 提供的 Knowledge Retrieval Tool 检索。
- 不要把管理员 Token 写进 Hermes Profile；员工运行时只使用 Employee Service Token。
- 不要在员工管理页增加“额外挂载知识源”能力；知识权限来源是 Job Template。
- 不要让 Job Template 草稿影响运行时；只有发布新版本才会传播知识权限变化。
- 不要为了纯 Knowledge Source 权限变更重启 Hermes；检索时由 Platform 动态鉴权。
- 不要把 Department Quota 超限做成默认停整个部门；部门配额默认只触发管理告警。
- 不要在 MVP 中实现月配额硬控；当前只执行日 Token 配额。
- 不要用请求前 Token 预估值做预扣减或停用员工；配额执行基于已结算 Token Ledger。
- 不要让 Organization 硬配额阻断控制面；超限后仍要允许管理员止损和恢复。
- 不要把员工硬配额超限默认实现成杀 Hermes 进程；应先进入 `quota_blocked` 并拒绝新的模型成本调用。
- 不要把 Hermes 内部 session DB 当作 Platform 配额账本；Platform Token Ledger 才是权威来源。
- 不要把 Audit Rule 做成脚本规则引擎或第二套执行引擎；它只负责记录、分级、通知、复核、KPI 和保留策略。
- `start.md`、`CONTEXT.md`、ADR-0002、ADR-0003、ADR-0004、ADR-0005、ADR-0006、ADR-0007 是当前产品方向的准绳。

## Natural Next Steps

1. 将 Phase 1 拆成 `.scratch/<feature>/issues/` 下的实现 issue。

2. 开始 FastAPI 后端骨架：
   - 数据模型先按单组织设计，不加 tenant_id。
   - `InstanceManager.spawn(employee_id, config)` 不接收 tenant 参数。

4. 对接 Hermes API Server：
   - 验证一个 Digital Employee Profile。
   - 验证 `/v1/runs`、`/health`、session key。

## Suggested Skills

- `/to-issues` — 把 `start.md` Phase 1 拆成 agent-ready issues
- `/implement` — 开始实现 FastAPI 后端骨架
- `/domain-modeling` — 后续新增领域概念时继续维护 `CONTEXT.md`
- `/diagnosing-bugs` — 对接 Hermes Instance 时排查启动和 API 问题
