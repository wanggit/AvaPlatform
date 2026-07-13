# AI 数字员工平台

企业级单组织 AI 数字员工平台，在 Hermes Agent 之上提供岗位模板、多 Agent 协作、组织架构、管理后台等 Platform 层能力。

## Language

**Organization（组织）**:
使用平台的一家企业或业务主体。当前产品只服务一个 Organization，不提供多租户隔离。
_Avoid_: Tenant, account

**Platform API（平台接口服务）**:
Platform 的 FastAPI 后端入口，承载管理后台 API、员工运行时回调、工具网关、知识检索、审批、预算、审计和指标查询。第一阶段它是模块化单体，不按能力拆成多个微服务。
_Avoid_: microservice per domain, Hermes API

**Platform Worker（平台后台工作进程）**:
Platform 的异步执行进程，消费队列任务并执行员工上岗、Hermes Profile 渲染、Hermes Instance 启停和冒烟测试、知识同步、审批恢复、预算统计、审计规则评估等后台动作。
_Avoid_: frontend job, Hermes process

**Runtime Manager（运行时管理器）**:
Platform 内负责 Hermes Profile 和 Hermes Instance 生命周期的模块。它通过 `HermesDashboardClient` 调用 Hermes Dashboard API（默认 9119 端口）创建/删除独立 Profile、写入 SOUL.md、设置模型、启动/停止 Gateway，并通过健康检查轮询确认 Gateway 就绪。每个 Digital Employee 对应一个持久 Profile，评测流程创建临时 Profile 并在完成后清理。
_Avoid_: manual shell script, user default Hermes profile

**Hermes Profile（Hermes 配置档案）**:
Hermes Agent 的独立配置目录（`~/.hermes/profiles/<name>/`），包含 `config.yaml`、`SOUL.md`、skills、sessions 等完整运行时状态。每个 Digital Employee 对应一个 Hermes Profile，评测流程中临时 Profile 命名格式为 `eval-<version_id>-<timestamp>`。
_Avoid_: user account, agent config

**Hermes Gateway（Hermes 网关）**:
Hermes Agent 的运行时进程，监听指定端口提供 `/v1/runs` API。每个 Gateway 绑定一个 Profile。Platform 通过 `HermesDashboardClient.start_gateway(profile)` 启动、`stop_gateway(profile)` 停止。评测期间为临时 Profile 启动独立 Gateway，端口由 PortPool 分配（默认 8100-8199）。
_Avoid_: Hermes server, agent process

**PortPool（端口池）**:
Platform 内管理评测临时 Gateway 端口分配的工具类（`app/runtime/port_pool.py`）。线程安全，支持 allocate/release/available_count。端口耗尽时抛出 RuntimeError 并提示等待。
_Avoid_: hardcoded port, random port

**HermesDashboardClient（Hermes 控制台客户端）**:
封装 Hermes Dashboard REST API（默认 9119 端口）的 Python 客户端（`app/integrations/hermes.py`），提供 Profile CRUD、SOUL.md 读写、模型设置和 Gateway 启停等方法。与 `HermesClient`（Run 执行）分工明确。
_Avoid_: direct subprocess call, raw HTTP

**Platform Development Middleware（平台开发中间件）**:
本项目开发环境专用的 PostgreSQL、Redis 和 MinIO/S3 兼容对象存储实例。它们不能隐式复用其他项目或 RAGFlow 自带依赖；RAGFlow 作为外部知识库服务接入。
_Avoid_: shared random local database, RAGFlow internal services

**Application（应用）**:
一个具体的业务场景入口，组织一组页面、工具和默认配置范围。Application 不拥有 Job Template；Job Template 是可被不同业务场景复用的岗位蓝图。
_Avoid_: App, module, scenario

**Job Template（岗位模板）**:
一份定义了某类 Digital Employee 全部配置的蓝图——System Prompt（人设+职责+红线）、Grade（职级）、部门、可用工具、绑定知识源、默认 Goal Budget 和最高 Goal Risk Level。实例化一个 Template 即创建一个 Digital Employee，并进入员工上岗流程。
_Avoid_: Employee template, role template, 角色模板, 员工模板

**System Prompt（系统提示词 / 人设）**:
Job Template 中定义岗位身份、职责边界、工作风格和红线约束的核心字段。创建或更新 Digital Employee 时，Platform 必须把发布版本中的 System Prompt 下发到对应 Hermes Instance/Profile：持久身份写入该员工 Hermes Profile 的 `SOUL.md`，运行时覆盖可通过 Hermes `ephemeral_system_prompt` 注入。它不是普通用户消息，也不应由员工级配置扩大职责边界。
_Avoid_: user prompt, task prompt, description only

**Job Template Version（岗位模板版本）**:
Job Template 发布时形成的不可变配置快照。草稿修改不会影响 Digital Employee；发布新版本后，继承该模板的 Digital Employee 使用新的模板配置。
_Avoid_: template draft, template revision

**Template Evaluation（模板评测）**:
针对某个 Job Template Version 的上线前评测。评测通过创建临时 Hermes Profile、写入 SOUL.md（system_prompt + skills + tools + knowledge_sources + red_lines）、启动独立 Gateway、执行评测任务、收集 Hermes 输出、清理临时资源的全流程完成。创建 Digital Employee 时只能选择已发布且 Template Evaluation 通过的 Job Template Version；未运行、运行中或失败的版本都不能用于创建员工。
实现位置：`services.py:run_template_evaluation`，依赖 `HermesDashboardClient`（Profile/Gateway 管理）和 `PortPool`（端口分配）。
_Avoid_: employee test set, manual demo

**Template Evaluation Run（模板评测运行）**:
对某个 Job Template Version 执行一次评测计划的记录。MVP 中评测由管理员输入任务描述，系统创建临时 Hermes 环境执行，管理员查看 Hermes 输出后人工标记 pass/fail。评测结果记录在 `JobTemplateEvaluationRead` 中（status、score、summary、cases）。同一模板版本同时只能有一个评测运行（模板级并发锁）。
_Avoid_: employee smoke test, production run

**Pilot Job Template（试点岗位模板）**:
MVP 内置或演示用的 Job Template，用来验证一个明确业务场景的价值。它不是抽象岗位库，也不是行业通用模板承诺。
_Avoid_: generic role library, template marketplace

**Grade（职级）**:
Job Template 的自带属性，从小到大：Staff（一线）→ Lead（组长）→ Manager（部门经理）→ Director（总监）。职级决定了该岗位的协作权限——能否委托、审批、查看团队 KPI、创建目标等。能力逐级继承。
_Avoid_: Level, role, rank

**Digital Employee（数字员工）**:
平台层最核心的业务概念——一个在企业内承担特定岗位职责的 AI 工作体。每个 Digital Employee 拥有一份持久化的 Profile（文件系统存储）和一个运行时的 Hermes Instance（独立进程）。三者一一对应。
_Avoid_: Agent, bot, worker

**Employee Lifecycle State（员工生命周期状态）**:
Digital Employee 在 Platform 控制面中的业务生命周期，如 `provisioning`、`pending_activation`、`active`、`disabled`、`rollout_failed`、`needs_review`。它决定员工是否可以被创建、启用、停用、接收 Goal 或进入人工处理。它不表示 Hermes 进程是否健康，也不表示员工当前是否空闲。
_Avoid_: runtime status, process status

**Hermes Instance Runtime State（Hermes 实例运行状态）**:
某个 Digital Employee 对应 Hermes Instance 的进程和健康状态，如 `not_started`、`starting`、`healthy`、`unhealthy`、`recovering`、`stopped`。它由 Instance Manager 通过进程管理和健康检查维护。一个员工可以处于 `active` 生命周期但实例临时 `unhealthy`；也可以处于 `pending_activation` 但实例刚完成冒烟测试尚未停止。已上岗员工实例不健康时，Platform 暂停调度并按次数上限自动恢复；超过上限后生成 Abnormal Shutdown 审计事件并进入人工处理。
_Avoid_: employee status, business lifecycle

**Employee Availability State（员工可用性状态）**:
已上岗员工面向调度和员工目录展示的工作负载状态，如空闲、忙碌、不可用。它由 Employee Lifecycle State、Hermes Instance Runtime State、当前 Goal / Work Item、预算阻断和维护状态共同推导，不应作为唯一事实源。`active` 员工的 Hermes Instance 为 `unhealthy` 或 `recovering` 时，可用性必须为不可用，调度器不能分配新 Goal。
_Avoid_: lifecycle state, runtime state

**Employee Instance Configuration（员工实例配置）**:
Digital Employee 的实例级属性，如员工姓名、昵称、头像、所属部门、直属上级、备注、是否禁用模板内某些 Knowledge Source 或 Tool，以及实例资源策略。MVP 创建员工时只填写基础实例属性；Knowledge Source / Tool 的收窄放到员工详情页或权限配置中维护。它不能扩大 Job Template Version 定义的能力和风险边界：不能扩大 System Prompt 职责、新增模板外 Skill、Tool 或 Knowledge Source、提高最高 Goal Risk Level，或提高默认 Goal Budget。
_Avoid_: template override, capability override

**Employee Rollout（员工上岗流程）**:
Digital Employee 从创建到可承接 Goal 的生命周期流程。MVP 中点击“创建数字员工”不会立即上岗，而是创建员工记录和异步 Employee Rollout Job，状态进入“创建 -> 配置中 -> 冒烟测试 -> 待上岗 -> 上岗运行”。只有通过实例冒烟测试后，管理员手动启用，员工才可接收 Goal、调用运行时能力并产生业务用量。待上岗状态不要求 Hermes Instance 常驻运行，Platform 可以停止实例或保持冷待机。
_Avoid_: instant activation, auto deploy

**Employee Rollout Job（员工上岗任务）**:
创建 Digital Employee 后由后台队列异步执行的任务，负责渲染 Profile、分发 Skill、注入 Tool 和 Knowledge Retrieval 配置、签发 Employee Service Token、启动 Hermes Instance、执行 Instance Smoke Test 并回写状态。失败分为临时基础设施失败和配置错误：前者可以按退避策略自动重试，后者必须管理员修复后手动重新配置或重新执行冒烟测试。页面应展示任务进度、失败分类、失败原因、日志摘要和修复建议。
_Avoid_: synchronous modal submit, one-shot create

**Instance Smoke Test（实例冒烟测试）**:
员工上岗流程中的最小实例级验证，确认 Platform 已正确渲染 Profile、写入 System Prompt、分发 Skill、注入工具和知识检索配置、签发 Employee Service Token、启动 Hermes Instance，并通过基础健康检查。MVP 中它必须包含一次受控 Hermes API / 模型真实调用：使用测试 session、低 token 上限、短超时并禁止工具调用，用来验证模型配置和 Profile 加载可用。测试通过后实例可以停止或冷待机。它不是 Template Evaluation 的替代品，不维护完整岗位测试集。
_Avoid_: template evaluation, full QA

**Smoke/Test Run（冒烟/试运行）**:
用于创建员工、上岗或演示时验证实例连通性的测试调用。它不创建业务 Goal Run，不产生 Work Item，不进入正式 KPI 或业务产物统计；Token Ledger 和 Audit Event 可以标记为 `test` / `smoke`，用于成本和审计追踪但不混入业务绩效。
_Avoid_: business goal, production work

**Activation（上岗 / 启用）**:
管理员将已通过实例冒烟测试的 Digital Employee 切换为可运行状态的动作。Activation 是显式控制面操作，必须记录 Audit Event；未上岗员工不能接收新的 Goal Run。启用时 Platform 应启动或复用 Hermes Instance，并执行轻量健康检查。
_Avoid_: creation, provisioning

**Knowledge Entitlement（知识权限）**:
Digital Employee 对 Knowledge Source 的访问授权。MVP 中知识权限只从 Job Template 继承，不能在员工级别新增模板外 Knowledge Source。
_Avoid_: per-employee knowledge override, direct dataset grant

**Profile（员工档案）**:
Digital Employee 的持久化态，存在于独立 Hermes Profile 目录下，包含 config.yaml、`SOUL.md`、skills/、memory/、sessions/、state.db。`SOUL.md` 是 Hermes 的持久身份入口，由 Job Template 的 System Prompt 渲染生成。
_Avoid_: config dir, employee directory

**Instance（实例）**:
Digital Employee 的运行时态——一个独立 Hermes 进程，占用一个端口，提供 OpenAI 兼容 HTTP API。
_Avoid_: process, runtime, worker process

**Skill（技能）**:
一个可分发的 Hermes 能力单元，定义 Agent 如何完成某类任务。Skill 以 Skill Package 上传和发布，包内至少包含 Hermes 原生 `SKILL.md`。
_Avoid_: capability, plugin

**Skill Package（技能包）**:
一个 `.zip` 文件，包含某个 Skill 的全部文件，如 `SKILL.md`、脚本、引用资料、模板和素材。Platform 不维护文件数量，也不把 Skill 拆成文件级配置。
_Avoid_: individual skill file, file count

**Skill Library（技能库）**:
Platform 层的 Skill 中央仓库——上传、审核、发布、版本管理 Skill Package。Job Template 只能绑定已发布 Skill；创建或更新 Digital Employee 时，Platform 将绑定的 Skill 分发到目标 Profile。
_Avoid_: Shared Skill Market, skill store, skill registry

**Tool（工具）**:
Digital Employee 运行时可调用的外部能力或 Platform API 能力，如工单查询、CRM 更新、邮件发送、知识检索、Web 搜索、文件读写、审批发起。Tool 代表运行时接口权限，不等同于 Skill。
_Avoid_: skill, capability package

**Business Tool（业务工具）**:
Platform 自定义的 Tool，主要用于访问企业业务系统或 Platform API，如 CRM、工单、邮件、审批、知识检索和内部业务接口。Business Tool 默认通过 Platform Tool Gateway 调用，不把第三方系统凭证下发到 Hermes Profile。
_Avoid_: Hermes built-in tool, direct third-party key

**Hermes Built-in Tool（Hermes 内置工具）**:
Hermes Agent 自带的通用工具能力，如本地文件、Shell、Web/Search 等运行时能力。它不等同于 Platform 管理的 Business Tool；是否开放给岗位仍需由 Job Template 的 Tool 白名单控制。它可以通过 Hermes Profile、pre/post tool-call hook 和 middleware 做审计与预置约束，但不经过 Platform Tool Gateway。Platform 只能登记、启停和标注 Hermes 已存在的内置工具，不能在页面中创建不存在的 Hermes 内置工具实现。
_Avoid_: business tool

**Tool Registry（工具注册表）**:
Platform 统一维护 Tool 的位置，记录 Tool 的元数据、调用方式、鉴权方式、风险等级、读写属性、审批要求、审计要求和幂等策略。Job Template 的工具白名单只能从已启用 Tool 中选择。
_Avoid_: hardcoded tool list, tool string

**Tool Idempotency Policy（工具幂等策略）**:
Platform 管理 Tool 的必填发布条件，定义 Tool Gateway 如何识别重复调用、生成或透传 idempotency key、记录外部业务对象 ID、判断是否可安全重放，以及重复请求返回已有结果还是拒绝。默认由 Platform Tool Gateway 生成幂等键，至少包含 `employee_id + goal_run_id + work_item_id + tool_id + request_hash`；外部系统强制要求幂等键字段时，Gateway 再做透传或映射。除 Hermes Built-in Tool 外，所有 Platform 管理 Tool 都必须配置幂等策略；外部写 Tool 不能证明幂等时不得发布。
_Avoid_: best-effort retry, blind replay

**Tool Entitlement（工具授权）**:
Job Template 对某个 Tool 的绑定授权，包含是否允许使用以及参数边界，如部门范围、金额上限、只读/可写、是否只能创建草稿等。Digital Employee 从 Job Template 继承 Tool Entitlement；员工级配置不能新增模板外 Tool，只能禁用或收窄模板内 Tool。
_Avoid_: raw tool name, unrestricted tool access

**Platform Tool Gateway（平台工具网关）**:
Business Tool 的统一运行时调用入口。Hermes Instance 携带 Employee Service Token 调用 Platform Tool Gateway；Platform 校验员工身份、岗位模板 Tool 白名单、Tool 状态、审批要求、审计要求和 Tool Idempotency Policy 后，再访问真实业务系统。
_Avoid_: direct CRM call, direct third-party tool call

**Credential（凭证）**:
Platform 在本系统内置保存和管理的密钥记录，用于访问外部业务系统，如 API Key、OAuth token、Basic Auth、Webhook secret。Tool 只引用 Credential，不保存明文；Credential 不下发到 Hermes Profile，也不由 Job Template 维护。
_Avoid_: external secret manager, plaintext key in profile

**Knowledge Base（知识库）**:
Organization 级别的企业知识系统，由外部成熟知识库承载文档、解析、分块、索引和检索能力。Platform 不自建知识库，只接入外部知识系统并管理岗位授权。
_Avoid_: RAG, document store, vector db

**Knowledge Source（知识源）**:
外部 Knowledge Base 中可被 Platform 引用和授权的一个检索范围，如 dataset、collection 或 knowledge base。一个 Job Template 可以绑定多个 Knowledge Source；该岗位的 Digital Employee 只能在这些授权范围内检索。
_Avoid_: collection, index, corpus

**External Dataset Sync（外部数据集同步）**:
Platform 从外部 Knowledge Base 拉取可用数据集清单的配置动作。MVP 中同步由管理员手动触发；同步发现失联数据集时只标记状态，不自动删除 Knowledge Source。
_Avoid_: auto import, background crawler

**Knowledge Connection（知识库连接）**:
Platform 连接外部 Knowledge Base 的配置，包含服务地址、认证信息引用和连接状态。MVP 只有一个活跃 Knowledge Connection；它不是文档仓库本身，也不拥有文档内容。
_Avoid_: knowledge instance, vector database

**Knowledge Adapter（知识适配器）**:
Platform 与外部 Knowledge Base 之间的集成层。它把岗位模板绑定的 Knowledge Source 转换为运行时检索调用，并向 Digital Employee 暴露统一查询能力。
_Avoid_: RAG engine, vector service

**Knowledge Retrieval Tool（知识检索工具）**:
Digital Employee 用来查询授权 Knowledge Source 的内置 Tool。它只访问 Platform 的 Knowledge Adapter，不直接访问外部 Knowledge Base，并按 Job Template 的 Knowledge Source 权限动态鉴权。
_Avoid_: direct RAGFlow tool, vector search tool

**Knowledge Preview（知识预览）**:
管理员在管理后台中验证 Knowledge Source 检索效果的配置动作。它不是 Digital Employee 的运行时检索，可直接选择 Knowledge Source，但必须记录审计。
_Avoid_: employee retrieval, production query

**Knowledge Citation（知识引用）**:
一次知识检索命中的来源说明，指向具体 Knowledge Source、文档、片段或页码。Digital Employee 使用知识检索结果时必须保留引用。
_Avoid_: source text, reference note

**Employee Service Token（员工服务令牌）**:
Platform 签发给某个 Digital Employee 运行时实例的最小权限凭证。它用于调用员工运行时接口，不包含外部系统密钥，可随员工停用、模板变更或实例重建被轮换或吊销。
_Avoid_: RAGFlow key, user token, API key

**Model Configuration（模型配置）**:
平台可调用模型的一条配置，包含模型类型、Base URL、API Key、模型名称、上下文大小等信息。Job Template、Knowledge Base 等需要模型的地方都引用 Model Configuration。
_Avoid_: model string, provider config

**LLM Model Configuration（大语言模型配置）**:
模型类型为大语言模型的 Model Configuration。开发环境可使用 OpenAI 兼容供应方配置，真实 API Key 只进入本地环境变量或部署密钥，不写入仓库。
_Avoid_: hardcoded LLM key

**Embedding Model Configuration（向量模型配置）**:
模型类型为向量模型的 Model Configuration。开发环境可以使用本机 Ollama 已安装的向量模型；当 Platform API 在容器内运行时，访问宿主机 Ollama 需要使用可达的宿主机地址。
_Avoid_: inline embedding model string

**Rerank Model Configuration（排序模型配置）**:
模型类型为排序模型的 Model Configuration，用于知识检索结果重排。MVP 可以先关闭 Rerank，但数据模型和配置页面保留该模型类型。
_Avoid_: mandatory first-day rerank service

**Goal（目标）**:
一切工作的起点。分配给某个 Root Goal Owner 的业务意图，包含预期产出、截止时间和验收标准。
_Avoid_: Task, mission, objective

**Goal Risk Level（目标风险等级）**:
Goal 或 Goal Run 的业务风险分级，从 L1 信息辅助到 L4 高风险决策。它决定自动化程度、委托边界、审批和验收要求。
_Avoid_: tool risk level, severity

**Root Goal Owner（根目标负责人）**:
对 Goal 最终结果持续负责的 Digital Employee。即使发生 Delegation，Root Goal Owner 也不会转移。
_Avoid_: current assignee, final worker

**Goal Run（目标运行）**:
一次 Goal 的可恢复执行过程。它承载状态、预算、动态执行图、审批等待、Artifact 和追踪信息。
_Avoid_: session, conversation

**Work Item（工作项）**:
Platform 在 Goal Run 中创建的受控子任务。它有明确的负责人、执行者、目标、验收标准、输入引用、预算、状态和 Artifact。
_Avoid_: sub goal, free-form task

**Runtime Interrupted Work Item（运行中断工作项）**:
Work Item 执行期间 Hermes Instance 中断、超时、重启或健康检查失败导致的可恢复异常状态。Platform 必须记录 Hermes run/session 引用、错误原因、已产生 Artifact 或 Tool 调用痕迹，并由 Goal Run 状态机决定重试、重新排队或转人工处理。MVP 不依赖 Hermes session 自动恢复业务状态。
_Avoid_: automatic session resume, invisible retry

**Delegation（委托）**:
一种受 Platform 管控的运行时协作机制。Digital Employee 可以提出把 Work Item 分配给其他员工，但 Platform 负责授权、创建、调度和追踪。
_Avoid_: handoff, assign

**Handoff（责任转交）**:
将某个业务事项的后续责任从一个负责人转交给另一个负责人。Handoff 会改变当前责任主体，不是 MVP 的默认多员工协作机制。
_Avoid_: delegation, escalation

**Workflow（工作流）**:
由 Platform 代码或配置控制顺序的固定业务流程。它适合退款、合同、权限变更等强顺序和强合规场景，不由 Agent 自由规划步骤。
_Avoid_: dynamic delegation, execution graph

**Execution Graph（执行图）**:
Goal Run 中由 Work Item、依赖关系、Artifact 和状态构成的运行时图。它不是管理员预设的静态 DAG，而是由 Platform 维护的动态执行事实。
_Avoid_: delegation chain, preset DAG

**Delegation Policy（委托策略）**:
限制 Delegation 复杂度和风险的规则集合，如深度、扇出、节点数、并发、重试、预算、Deadline、跨部门和再委托权限。
_Avoid_: delegation log, workflow config

**Employee Directory（员工目录）**:
Organization 下所有 Digital Employee 的公开名录。每个条目包含：姓名、岗位、Grade、职责描述、Skill 列表、当前状态（空闲/忙碌）。所有员工可查询，用于做出委托决策。
_Avoid_: roster, org chart, address book

**Artifact（产物）**:
Digital Employee 完成工作后的有形成果——报告、表格、分析结果等文件。是 Goal 完成与否的客观依据，也是 KPI 评估的输入。
_Avoid_: deliverable, output

**Artifact Acceptance（产物验收）**:
对 Artifact 是否满足验收标准的结果判断。它发生在产物提交之后，决定 Work Item 或 Goal 能否完成。
_Avoid_: approval, sign-off

**Business Outcome Metric（业务结果指标）**:
衡量 Pilot Job Template 是否产生业务价值的指标，如周期缩短、人工节省、采纳率、错误率或客户体验变化。它不同于纯技术用量指标。
_Avoid_: token metric, raw KPI counter

**Metric Binding（指标绑定）**:
Job Template Version 对 Business Outcome Metric 的绑定关系，固定指标口径、来源、基线、目标和归因窗口。
_Avoid_: dashboard filter, ad hoc report

**Red Line（红线）**:
定义在 Job Template 中的绝对禁止行为（如不得编造数据、不得泄露内部文档）。触发后 Platform 拦截并告警，计入 KPI。
_Avoid_: guardrail, policy

**Approval（审批）**:
主动设计的流程控制节点。Digital Employee 在执行关键动作前请求人类批准，由业务责任人、部门负责人、Tool Owner、平台管理员或运维负责人按规则批准或驳回。MVP 先通过 Platform 内部审批中心处理，后续可接入飞书、钉钉、邮件等外部通知。正常流程，不计入红线。
_Avoid_: acceptance, review, sign-off

**Escalation（升级）**:
Agent 无法处理时的异常流转——将工作移交给人类代替完成。属于安全事件，触发告警并计入 KPI。
_Avoid_: handoff, transfer

**Audit Event（审计事件）**:
Platform 对关键事实的不可篡改记录。红线触发、审批、升级、异常停机和敏感操作都必须产生 Audit Event，用于复核、告警、KPI 和追责。事件主体一旦产生不可编辑，只能追加复核或处理结论。
_Avoid_: log line, notification

**Audit Rule（审计规则）**:
定义 Audit Event 如何分级、通知、复核和计入 KPI 的规则。Audit Rule 不替代 Red Line、Approval、Organization Quota、Goal Budget 等执行机制。
_Avoid_: workflow rule, enforcement rule

**Audit Disposition（审计处理结论）**:
管理员或负责人对 Audit Event 追加的处理结果，如误报、已确认、已处理、无需处理或升级处理。Disposition 不修改原始 Audit Event。
_Avoid_: edit audit event, change log

**Abnormal Shutdown（异常停机）**:
Hermes Instance 的非预期运行故障，如进程意外退出、连续健康检查失败、启动/重启失败或被系统 OOM 杀掉。管理员手动停止、预算阻断和模板发布导致的重载不属于 Abnormal Shutdown。
_Avoid_: admin stop, quota block, planned restart

**Sensitive Operation（敏感操作）**:
需要审计留痕的高风险操作，包括管理员查看未脱敏证据、导出审计日志、修改关键配置、启停员工、调整预算、解除预算阻断、轮换员工服务令牌，以及员工尝试执行外部写操作。
_Avoid_: normal read, routine view

**KPI（绩效指标）**:
衡量 Digital Employee 工作效果的一组量化指标：目标完成率、响应时效、协作贡献、红线触发次数、Token 消耗、转人工率和业务结果指标。平台自动评分，Manager 及以上职级可查看。Admin 可依据评分结果对不达标员工下线。
_Avoid_: metric, score, performance indicator

**Quota（配额）**:
Organization 级 Token 消耗总上限。MVP 中 Quota 只用于平台整体成本硬控，Department 和 Digital Employee 只做用量统计。
_Avoid_: budget, limit, allowance

**Organization Quota（组织配额）**:
Organization 级每日 Token 硬上限。超限后阻断新的模型成本调用，但控制面仍保持可用。
_Avoid_: department quota, employee quota

**Goal Budget（目标预算）**:
单个 Goal Run 的 Token 执行上限。它限制 Delegation 扩散造成的单目标成本失控。
_Avoid_: work item budget, employee quota

**Budget Blocked（预算阻断）**:
Organization Quota 或 Goal Budget 超限后进入的受控阻断状态。Platform 拒绝新的模型成本调用，但保留查看、停止、调整预算和审计能力。
_Avoid_: killed, process stopped

**Usage Analytics（用量分析）**:
按 Department、Digital Employee、Goal 和 Work Item 等维度统计 Token 使用情况。MVP 中这些维度不产生独立配额阻断。
_Avoid_: department quota, employee quota

**Token Ledger（Token 台账）**:
Platform 记录模型调用实际 Token 消耗的权威流水账。Organization Quota 和 Goal Budget 的结算以 Hermes 返回的调用 usage 为主要输入；缺失 usage 时使用估算值并标记。
_Avoid_: token counter, usage cache
