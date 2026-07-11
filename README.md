# AvaPlatform

AvaPlatform 是一个面向企业内部场景的 **AI 数字员工平台**。它不是单个聊天机器人，而是在 Hermes Agent 之上构建的管理与治理层，用来把 AI 能力包装成可配置、可上岗、可审批、可审计、可度量的“数字员工”。

平台当前按单组织模式设计，重点覆盖岗位模板、数字员工生命周期、目标运行、工具网关、知识源接入、预算控制、审批中心、审计规则和 KPI 报表等能力。

## 项目目标

企业真正需要的不是一个可以随意自主行动的 Agent，而是一套能在企业制度内工作的数字化劳动力系统：

- 用岗位模板定义职责、权限、系统提示词、工具和知识边界。
- 创建数字员工时只实例化已发布且评测通过的岗位模板。
- 通过上岗流程、冒烟测试和管理员启用控制运行风险。
- 所有目标、工具调用、审批、预算阻断和敏感操作都有审计记录。
- 通过预算、KPI 和模板效果报表追踪业务结果，而不是只看模型调用。

## 当前能力

### 管理后台

前端位于 `web/`，使用 React、TypeScript、Vite 和 Ant Design。已实现的主要页面包括：

- 概览看板：员工、目标、预算、告警和模板评测概览。
- 员工管理：创建数字员工、查看生命周期、上岗、停用、冒烟测试。
- 目标管理：创建 Goal Run、查看预算、执行图、工作项和交付物。
- 审批中心：集中处理工具调用、预算、交付物等人工审批。
- 岗位模板：维护模板版本、系统提示词、技能、工具、知识源和模板评测。
- 工具管理：登记业务工具、凭证、风险等级、审批和审计要求。
- 知识管理：配置 RAGFlow 知识连接、知识源和管理员检索预览。
- 配额管理：组织总预算、目标预算策略和 token 用量分析。
- 审计规则：审计事件、规则、通知、处理结论和导出记录。
- 模型、技能、部门、组织架构、员工目录和 KPI 报表页面。

### 后端 API

后端位于 `backend/`，使用 FastAPI 和 Pydantic，提供平台控制面的 REST API。当前包含：

- 岗位模板、模板评测和发布门禁。
- 数字员工创建、组织归属、运行状态、上岗和停用。
- Goal Run、Work Item、Artifact 和交付物验收。
- Platform Tool Gateway：工具白名单、审批、幂等策略和审计。
- 知识检索网关与 RAGFlow 适配层。
- 预算、token ledger、用量分析和 KPI 报表。
- 审批、审计事件、审计规则和通知记录。
- 模型配置、技能包、凭证、部门和组织基础数据。

后端默认可以以内存状态运行，也包含 PostgreSQL 持久化状态层和本地开发中间件配置。

## 核心概念

- **Job Template（岗位模板）**：数字员工的岗位蓝图，定义职责、人设、系统提示词、工具、知识源、默认预算和最高目标风险等级。
- **Template Evaluation（模板评测）**：岗位模板上线前的评测门禁。只有已发布且评测通过的模板版本才能创建数字员工。
- **Digital Employee（数字员工）**：某个岗位模板实例化后的 AI 工作体，拥有业务生命周期、运行时状态和可用性状态。
- **Employee Rollout（员工上岗流程）**：创建员工后进入配置、冒烟测试、待上岗、管理员启用的流程，不是提交表单后立即投入生产。
- **Goal Run（目标运行）**：一次业务目标的可恢复执行过程，承载预算、执行图、工作项、审批等待和交付物。
- **Platform Tool Gateway（平台工具网关）**：业务工具统一入口。平台校验员工身份、岗位权限、审批要求、审计要求和幂等策略后再访问真实业务系统。
- **Knowledge Source（知识源）**：外部知识库中的授权检索范围。数字员工只能访问岗位模板允许的知识源。
- **Audit Event（审计事件）**：平台内关键操作和运行时风险的只追加记录，用于追责、复核和合规。

更完整的领域词汇见 [CONTEXT.md](CONTEXT.md)。

## 技术栈

- 前端：React 19、TypeScript、Vite、Ant Design、Oxlint。
- 后端：Python 3.12、FastAPI、Pydantic、SQLAlchemy、pytest。
- 本地中间件：PostgreSQL/pgvector、Redis、MinIO。
- 外部集成：Hermes Agent、RAGFlow、OpenAI-compatible model endpoint。

## 目录结构

```text
.
├── backend/                  # FastAPI 平台后端、领域服务、数据库适配和测试
├── web/                      # React 管理后台
├── infra/                    # 本地开发中间件 compose 配置
├── docs/                     # ADR、验证计划、运营策略和 agent 工作流文档
├── openspec/                 # 需求变更、设计和规格说明
├── .codex/skills/            # 本仓库使用的 Codex/OpenSpec 工作流技能
├── platform-dev.sh           # 本地一键启动/停止脚本
├── CONTEXT.md                # 项目领域语言和概念边界
└── AGENTS.md                 # 给代码代理的工作区约束
```

`hermes-agent-2026.6.19/` 是本地上游源码参考目录，按约定只读且不提交到仓库。

## 快速启动

### 1. 准备环境

需要本机安装：

- Python 3.12
- Node.js 与 npm
- Docker 或兼容的容器运行时
- 已配置好的 Hermes profile wrapper，例如 `~/.local/bin/aiplatform`

复制后端环境变量示例：

```bash
cp backend/.env.example backend/.env
```

按需填写模型、RAGFlow、Hermes 等真实 API Key。不要把 `backend/.env` 提交到仓库。

### 2. 启动本地中间件

```bash
docker compose -f infra/ai-platform.compose.yml up -d
```

默认端口：

- PostgreSQL: `127.0.0.1:15432`
- Redis: `127.0.0.1:16379`
- MinIO API: `127.0.0.1:19000`
- MinIO Console: `127.0.0.1:19001`

### 3. 安装依赖

后端：

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e .
cd ..
```

前端：

```bash
cd web
npm install
cd ..
```

### 4. 启动平台

如果 Hermes wrapper、后端虚拟环境和前端依赖都已准备好，可以使用：

```bash
./platform-dev.sh start
```

默认服务地址：

- 前端：`http://127.0.0.1:5173/`
- 后端：`http://127.0.0.1:8010/api/v1`
- Hermes API Server：`http://127.0.0.1:8642`

查看状态和日志：

```bash
./platform-dev.sh status
./platform-dev.sh logs
```

停止服务：

```bash
./platform-dev.sh stop
```

也可以手动启动：

```bash
cd backend
. .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

```bash
cd web
VITE_API_BASE_URL=http://127.0.0.1:8010/api/v1 npm run dev
```

## 开发与验证

前端：

```bash
cd web
npm run lint
npm run build
```

后端：

```bash
cd backend
. .venv/bin/activate
python -m pytest tests
```

当前测试覆盖包括：

- 服务目录和基础 API。
- 模板评测、员工创建和生命周期。
- 执行网关、工具调用、预算阻断和审计。
- 端到端模板、员工、目标、审批、交付物和审计流程。
- Hermes 集成边界。

## 安全与配置约定

- `.env`、虚拟环境、`node_modules`、构建产物和本地运行状态都通过 `.gitignore` 排除。
- 真实 API Key 只放在本地环境变量、部署密钥或 `backend/.env` 中。
- `backend/.env.example` 只保留开发占位配置。
- 业务系统凭证由平台 Credential 模型引用，不应下发到 Hermes Profile。
- 业务工具默认通过 Platform Tool Gateway 调用，避免员工实例直接持有第三方系统密钥。

## 当前边界

这是一个平台原型/MVP 代码库，重点验证控制面、治理边界和端到端业务闭环。当前不承诺：

- 多租户隔离。
- 完整生产部署方案。
- 自动模板评测执行引擎。
- 完整权限系统和细粒度 RBAC。
- 企业级密钥托管、审计归档和高可用部署。
- 对所有 Hermes 内置工具的生产级管控。

这些方向已经在 `docs/adr/`、`docs/e2e-verification-plan.md` 和 `openspec/` 中留有设计上下文。

## 相关文档

- [CONTEXT.md](CONTEXT.md)：领域语言、概念边界和命名约定。
- [docs/adr/](docs/adr/)：架构决策记录。
- [docs/e2e-verification-plan.md](docs/e2e-verification-plan.md)：端到端验证计划。
- [docs/self-operation-marketing-strategy.md](docs/self-operation-marketing-strategy.md)：自运营与市场策略。
- [openspec/changes/formalize-digital-employee-platform-requirements/](openspec/changes/formalize-digital-employee-platform-requirements/)：平台需求规格、设计和任务拆分。
