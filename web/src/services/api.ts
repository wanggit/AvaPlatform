// 后端 API 访问层：封装请求、响应映射和前端提交 payload 转换。
import type {
  AuditEvent,
  AuditEventType,
  AuditNotificationRecord,
  AuditRule,
  AlertMessage,
  CredentialRecord,
  Department,
  DigitalEmployee,
  Goal,
  GoalBudgetPolicy,
  GoalRiskLevel,
  JobTemplate,
  KnowledgeConnection,
  KnowledgeSource,
  ModelConfig,
  ModelType,
  OrganizationQuotaPolicy,
  SkillDefinition,
  TemplateEvaluation,
  TemplateOutcomeReport,
  ToolDefinition,
  UsageAnalyticsRow,
  TokenLedgerEntry,
} from '../types/domain';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8010/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    throw new Error(body?.detail ?? `${response.status} ${response.statusText}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export type CreateDigitalEmployeeFormValues = {
  name: string;
  nickname?: string;
  avatarUrl: string;
  department: string;
  managerId?: string;
  templateId: string;
  notes?: string;
};

export function buildCreateDigitalEmployeePayload(values: CreateDigitalEmployeeFormValues) {
  return {
    name: values.name,
    nickname: values.nickname,
    avatar_url: values.avatarUrl,
    department_id: values.department,
    manager_id: values.managerId,
    job_template_version_id: values.templateId,
    notes: values.notes,
  };
}

export type CreateGoalRunFormValues = {
  title: string;
  description: string;
  rootOwnerId: string;
  riskLevel: GoalRiskLevel;
  budgetTokens?: number;
  deadline: string;
};

export function buildCreateGoalRunPayload(
  values: CreateGoalRunFormValues,
  context: {
    ownerName?: string;
    ownerTemplateId?: string;
    defaultBudgetTokens?: number;
  },
) {
  return {
    title: values.title,
    goal_type: 'manual',
    description: values.description,
    owner: values.rootOwnerId,
    root_responsible: context.ownerName ?? values.rootOwnerId,
    budget_tokens: values.budgetTokens ?? context.defaultBudgetTokens ?? 200000,
    policy: {
      risk_level: values.riskLevel,
      deadline: values.deadline,
      template_id: context.ownerTemplateId ?? '',
    },
  };
}

const nowText = () => new Date().toLocaleString('zh-CN', { hour12: false });

const departmentNameById: Record<string, string> = {
  'dept-customer-service': '客服部',
  'dept-sales': '销售部',
  'dept-market': '市场部',
  'dept-product': '产品部',
  'dept-operations': '运营部',
  'dept-hr': '人力资源部',
};

const departmentIdByName = Object.entries(departmentNameById).reduce<Record<string, string>>((acc, [id, name]) => {
  acc[name] = id;
  return acc;
}, {});

function updateDepartmentDirectory(departments: BackendDepartment[]) {
  departments.forEach((department) => {
    departmentNameById[department.id] = department.name;
    departmentIdByName[department.name] = department.id;
  });
}

export function toDepartmentId(value: string): string {
  return departmentIdByName[value] ?? value;
}

export function toDepartmentName(value: string): string {
  return departmentNameById[value] ?? value;
}

type BackendDepartment = {
  id: string;
  name: string;
  description?: string;
  employee_count: number;
  template_count: number;
};

export function mapDepartment(department: BackendDepartment): Department {
  return {
    id: department.id,
    name: department.name,
    description: department.description ?? '',
    employeeCount: department.employee_count,
    templateCount: department.template_count,
  };
}

type BackendEvaluation = {
  status: 'not_evaluated' | 'passed' | 'failed' | 'warning' | 'expired';
  score: number;
  case_count: number;
  passed_case_count: number;
  summary: string;
};

type BackendTemplate = {
  id: string;
  role: string;
  version: string;
  grade: JobTemplate['grade'];
  department_id: string;
  model_config_id: string;
  description: string;
  system_prompt: string;
  max_goal_risk_level: GoalRiskLevel;
  default_goal_budget_tokens: number;
  skills: string[];
  tools: string[];
  knowledge_sources: string[];
  red_lines: string[];
  metric_bindings: Record<string, unknown>[];
  is_pilot: boolean;
  pilot_scenario?: string;
  status: JobTemplate['status'];
  evaluation: BackendEvaluation;
};

function mapEvaluation(evaluation: BackendEvaluation): TemplateEvaluation {
  return {
    status: evaluation.status === 'not_evaluated' || evaluation.status === 'expired' ? 'not_run' : evaluation.status,
    score: evaluation.score,
    caseCount: evaluation.case_count,
    passedCaseCount: evaluation.passed_case_count,
    summary: evaluation.summary,
  };
}

export function mapTemplate(template: BackendTemplate): JobTemplate {
  return {
    id: template.id,
    role: template.role,
    grade: template.grade,
    departmentId: template.department_id,
    department: toDepartmentName(template.department_id),
    description: template.description,
    systemPrompt: template.system_prompt,
    model: template.model_config_id,
    skills: template.skills,
    knowledgeSources: template.knowledge_sources,
    toolsets: template.tools,
    redLines: template.red_lines,
    defaultGoalBudgetTokens: template.default_goal_budget_tokens,
    maxGoalRiskLevel: template.max_goal_risk_level,
    evaluation: mapEvaluation(template.evaluation),
    metricBindings: template.metric_bindings.map((metric, index) => ({
      id: String(metric.id ?? `metric-${index}`),
      name: String(metric.name ?? '业务结果指标'),
      source: 'manual_or_imported',
      unit: String(metric.unit ?? ''),
      target: String(metric.target_value ?? metric.target ?? '-'),
      actual: String(metric.actual ?? '-'),
      collectionMethod: String(metric.collection_method ?? metric.collectionMethod ?? '人工录入'),
    })),
    isPilot: template.is_pilot,
    pilotScenario: template.pilot_scenario,
    status: template.status,
    version: template.version,
  };
}

type BackendEmployee = {
  id: string;
  name: string;
  nickname?: string;
  avatar_url?: string;
  notes?: string;
  manager_id?: string;
  role: string;
  grade: DigitalEmployee['grade'];
  department_id: string;
  job_template_version_id: string;
  lifecycle_state: DigitalEmployee['lifecycleState'] | 'archived';
  runtime_state: DigitalEmployee['runtimeState'];
  availability_state: DigitalEmployee['availabilityState'];
  max_goal_risk_level: GoalRiskLevel;
  active_goal_count: number;
  rollout: {
    job_id: string;
    current_step: DigitalEmployee['rollout']['currentStep'];
    status: DigitalEmployee['rollout']['status'];
    last_smoke_test_status: DigitalEmployee['rollout']['lastSmokeTest']['status'];
    summary: string;
  };
};

export function mapEmployee(employee: BackendEmployee): DigitalEmployee {
  return {
    id: employee.id,
    name: employee.name,
    nickname: employee.nickname,
    avatarUrl: employee.avatar_url,
    notes: employee.notes,
    managerId: employee.manager_id,
    role: employee.role,
    grade: employee.grade,
    departmentId: employee.department_id,
    department: toDepartmentName(employee.department_id),
    description: employee.notes ?? employee.role,
    lifecycleState: employee.lifecycle_state === 'archived' ? 'disabled' : employee.lifecycle_state,
    runtimeState: employee.runtime_state,
    availabilityState: employee.availability_state,
    skills: [],
    model: '',
    templateId: employee.job_template_version_id,
    maxGoalRiskLevel: employee.max_goal_risk_level,
    activeGoalCount: employee.active_goal_count,
    rollout: {
      jobId: employee.rollout.job_id,
      currentStep: employee.rollout.current_step,
      status: employee.rollout.status,
      startedAt: nowText(),
      lastSmokeTest: {
        status: employee.rollout.last_smoke_test_status,
        mode: 'real_probe',
        summary: employee.rollout.summary,
      },
    },
    instancePort: 0,
    tokenUsedToday: 0,
    monthlyTokenUsed: 0,
    redLineTriggers: 0,
  };
}

const modelTypeToUi: Record<string, ModelType> = {
  large_language_model: 'llm',
  embedding_model: 'embedding',
  rerank_model: 'rerank',
  vision_model: 'vision',
  speech_model: 'audio',
};

const modelTypeToBackend: Record<ModelType, string> = {
  llm: 'large_language_model',
  embedding: 'embedding_model',
  rerank: 'rerank_model',
  vision: 'vision_model',
  audio: 'speech_model',
};

type BackendModel = {
  id: string;
  name: string;
  model_type: string;
  provider: string;
  base_url: string;
  api_key_credential_id: string;
  model_name: string;
  context_window: number;
  enabled: boolean;
  last_test_message?: string;
};

export function mapModel(model: BackendModel): ModelConfig {
  return {
    id: model.id,
    name: model.name,
    type: modelTypeToUi[model.model_type] ?? 'llm',
    provider: model.provider,
    modelName: model.model_name,
    baseUrl: model.base_url,
    apiKey: model.api_key_credential_id,
    contextWindow: model.context_window,
    status: model.enabled ? 'active' : 'disabled',
    description: model.last_test_message ?? '来自 Platform 后端模型配置。',
  };
}

export function modelPayload(model: Partial<ModelConfig> & Pick<ModelConfig, 'name' | 'type' | 'provider' | 'baseUrl' | 'modelName' | 'contextWindow'>, credentialId: string) {
  return {
    name: model.name,
    model_type: modelTypeToBackend[model.type],
    provider: model.provider,
    base_url: model.baseUrl,
    api_key_credential_id: credentialId,
    model_name: model.modelName,
    context_window: model.contextWindow,
    enabled: model.status !== 'disabled',
    metadata: {},
  };
}

type BackendSkill = {
  id: string;
  name: string;
  version: string;
  package_file_name: string;
  status: SkillDefinition['status'];
  description?: string;
};

export function mapSkill(skill: BackendSkill): SkillDefinition {
  return {
    id: skill.id,
    name: skill.name,
    displayName: skill.name,
    category: '平台技能',
    version: skill.version,
    description: skill.description ?? '来自后端上传的技能包。',
    status: skill.status,
    entryFile: 'SKILL.md',
    packageFile: skill.package_file_name,
    updatedAt: nowText(),
  };
}

type BackendTool = {
  id: string;
  kind: 'business';
  name: string;
  category?: string;
  access_shape?: 'http_api' | 'platform_adapter';
  endpoint_url?: string;
  method?: ToolDefinition['endpointConfig']['method'];
  request_schema: Record<string, unknown>;
  response_schema: Record<string, unknown>;
  owner?: string;
  credential_id?: string;
  hermes_registry_id?: string;
  read_write?: 'read_only' | 'write' | 'mixed';
  default_constraints: string[];
  risk_level: ToolDefinition['riskLevel'] | 'critical';
  audit_required: boolean;
  approval_required: boolean;
  idempotency_policy?: string;
  lifecycle_status: 'draft' | 'published' | 'archived';
  test_status?: ToolDefinition['lastTestStatus'];
  last_test_message?: string;
};

export function mapTool(tool: BackendTool): ToolDefinition {
  return {
    toolId: tool.id,
    name: tool.name,
    displayName: tool.name,
    category: tool.category ?? '业务工具',
    description: '来自 Platform 后端工具注册表。',
    managedBy: 'platform',
    integrationType: tool.access_shape === 'platform_adapter' ? 'platform_api' : tool.access_shape ?? 'http_api',
    credentialRef: tool.credential_id,
    endpointConfig: {
      baseUrl: tool.endpoint_url,
      path: tool.endpoint_url,
      method: tool.method,
    },
    schemaConfig: {
      request: JSON.stringify(tool.request_schema ?? {}, null, 2),
      response: JSON.stringify(tool.response_schema ?? {}, null, 2),
    },
    riskLevel: tool.risk_level === 'critical' ? 'high' : tool.risk_level,
    readWrite: tool.read_write === 'read_only' ? 'read' : 'write',
    requiresApproval: tool.approval_required,
    auditRequired: tool.audit_required,
    defaultConstraints: tool.default_constraints,
    idempotencyPolicy: tool.idempotency_policy,
    status: tool.lifecycle_status === 'archived' ? 'deprecated' : tool.lifecycle_status,
    lastTestStatus: tool.test_status ?? 'not_tested',
    lastTestedAt: tool.last_test_message,
    boundTemplateCount: 0,
    version: '1.0.0',
  };
}

type BackendCredential = {
  id: string;
  name: string;
  owner_name: string;
  secret_mask: string;
  description?: string;
};

export function mapCredential(credential: BackendCredential): CredentialRecord {
  return {
    credentialId: credential.id,
    name: credential.name,
    type: 'api_key',
    owner: credential.owner_name,
    maskedValue: credential.secret_mask,
    status: 'active',
    updatedAt: nowText(),
  };
}

type BackendKnowledgeConnection = {
  id: string;
  provider: 'ragflow';
  name: string;
  base_url: string;
  credential_id: string;
  health_status: 'unknown' | 'healthy' | 'unhealthy';
};

export function mapKnowledgeConnection(connection: BackendKnowledgeConnection): KnowledgeConnection {
  return {
    id: connection.id,
    provider: connection.provider,
    name: connection.name,
    baseUrl: connection.base_url,
    apiKeyRef: connection.credential_id,
    status: connection.health_status === 'unhealthy' ? 'disconnected' : 'connected',
    lastTestedAt: nowText(),
    lastSyncedAt: nowText(),
  };
}

type BackendKnowledgeSource = {
  id: string;
  connection_id: string;
  external_id: string;
  display_name: string;
  source_type: string;
  authorization_scope: string[];
  retrieval_settings: Record<string, unknown>;
  status: 'draft' | 'active' | 'syncing' | 'failed' | 'archived';
  sync_metadata?: {
    document_count?: number;
    chunk_count?: number;
  };
};

export function mapKnowledgeSource(source: BackendKnowledgeSource): KnowledgeSource {
  return {
    id: source.id,
    name: source.display_name,
    category: source.authorization_scope[0] ? toDepartmentName(source.authorization_scope[0]) : '通用',
    description: `${source.source_type} / ${source.external_id}`,
    connectionId: source.connection_id,
    externalDatasetName: source.display_name,
    externalDatasetId: source.external_id,
    documentCount: source.sync_metadata?.document_count ?? 0,
    chunkCount: source.sync_metadata?.chunk_count ?? 0,
    status: source.status === 'active' ? 'active' : 'disabled',
    syncStatus: source.status === 'active' ? 'active' : 'missing',
    lastSyncedAt: nowText(),
    boundTemplateCount: 0,
  };
}

type BackendQuota = {
  id: string;
  monthly_token_limit: number;
  warning_threshold_percent: number;
};

export function mapQuota(quota: BackendQuota): OrganizationQuotaPolicy {
  return {
    id: quota.id,
    dailyTokenLimit: quota.monthly_token_limit,
    warningThresholdPercent: quota.warning_threshold_percent,
    timezone: 'Asia/Shanghai',
    enforcementMode: 'hard',
    blockedDataPlaneCalls: ['模型调用', '工具写入', '知识检索'],
    allowedControlPlaneActions: ['查看', '审批', '停用员工'],
    updatedAt: nowText(),
  };
}

type BackendGoalBudgetPolicy = {
  id: string;
  job_template_version_id: string;
  default_budget_tokens: number;
  warning_threshold_percent: number;
  overage_action: GoalBudgetPolicy['overageAction'];
  approvers: string[];
};

export function mapGoalBudgetPolicy(policy: BackendGoalBudgetPolicy): GoalBudgetPolicy {
  return {
    id: policy.id,
    templateId: policy.job_template_version_id,
    defaultBudgetTokens: policy.default_budget_tokens,
    warningThresholdPercent: policy.warning_threshold_percent,
    overageAction: policy.overage_action,
    approvers: policy.approvers,
    updatedAt: nowText(),
  };
}

type BackendLedger = {
  id: string;
  goal_run_id: string;
  work_item_id: string;
  employee_id: string;
  department_id?: string;
  model_id?: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  trace_ref?: string;
};

export function mapLedger(entry: BackendLedger): TokenLedgerEntry {
  return {
    id: entry.id,
    goalRunId: entry.goal_run_id,
    workItemId: entry.work_item_id,
    employeeId: entry.employee_id,
    department: toDepartmentName(entry.department_id ?? 'default'),
    modelConfigId: entry.model_id ?? '-',
    hermesInstanceId: entry.employee_id,
    promptTokens: entry.input_tokens,
    completionTokens: entry.output_tokens,
    cacheReadTokens: 0,
    cacheWriteTokens: 0,
    reasoningTokens: 0,
    totalTokens: entry.total_tokens,
    estimated: false,
    occurredAt: nowText(),
    requestId: entry.trace_ref ?? entry.id,
  };
}

type BackendUsage = {
  total_tokens: number;
  by_department: Record<string, number>;
  by_employee: Record<string, number>;
  by_job_template: Record<string, number>;
};

type BackendGoalRun = {
  id: string;
  title: string;
  goal_type: string;
  description: string;
  owner: string;
  root_responsible: string;
  budget_tokens: number;
  policy: Record<string, unknown>;
  status: 'draft' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  used_tokens: number;
};

export function mapGoal(goal: BackendGoalRun): Goal {
  const statusMap: Record<BackendGoalRun['status'], Goal['status']> = {
    draft: 'created',
    running: 'in_progress',
    paused: 'budget_blocked',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
  };
  return {
    id: goal.id,
    title: goal.title,
    description: goal.description,
    templateId: String(goal.policy?.job_template_version_id ?? goal.policy?.template_id ?? ''),
    rootOwnerId: goal.owner,
    rootOwnerName: goal.root_responsible,
    status: statusMap[goal.status],
    riskLevel: 'L2',
    budgetTokens: goal.budget_tokens,
    tokenUsed: goal.used_tokens,
    budgetStatus: goal.status === 'paused' ? 'budget_blocked' : goal.used_tokens / goal.budget_tokens > 0.8 ? 'warning' : 'normal',
    deadline: '-',
    createdAt: nowText(),
    workItems: [],
    executionEdges: [],
    artifacts: [],
  };
}

type BackendTemplateOutcomeReport = {
  id: string;
  template_id: string;
  template_role: string;
  version: string;
  period: string;
  goal_runs: number;
  completion_rate: number;
  first_pass_acceptance_rate: number;
  rework_rate: number;
  average_cycle_hours: number;
  token_cost: number;
  business_metrics: Array<{
    id: string;
    name: string;
    source: 'platform_native' | 'tool_business_system' | 'manual_or_imported';
    unit: string;
    target: string;
    actual: string;
    collection_method: string;
  }>;
  evaluation_status: TemplateEvaluation['status'];
};

export function mapTemplateOutcomeReport(report: BackendTemplateOutcomeReport): TemplateOutcomeReport {
  return {
    id: report.id,
    templateId: report.template_id,
    templateRole: report.template_role,
    version: report.version,
    period: report.period,
    goalRuns: report.goal_runs,
    completionRate: report.completion_rate,
    firstPassAcceptanceRate: report.first_pass_acceptance_rate,
    reworkRate: report.rework_rate,
    averageCycleHours: report.average_cycle_hours,
    tokenCost: report.token_cost,
    businessMetrics: report.business_metrics.map((metric) => ({
      id: metric.id,
      name: metric.name,
      source: metric.source,
      unit: metric.unit,
      target: metric.target,
      actual: metric.actual,
      collectionMethod: metric.collection_method,
    })),
    evaluationStatus: report.evaluation_status,
  };
}

export function mapUsageRows(usage: BackendUsage): UsageAnalyticsRow[] {
  const rows: UsageAnalyticsRow[] = [];
  Object.entries(usage.by_department).forEach(([id, tokens]) => rows.push({
    id: `department-${id}`,
    dimensionType: 'department',
    name: toDepartmentName(id),
    goalRuns: 0,
    tokens,
    estimatedTokens: 0,
    blockedGoals: 0,
    trend: 'flat',
  }));
  Object.entries(usage.by_employee).forEach(([id, tokens]) => rows.push({
    id: `employee-${id}`,
    dimensionType: 'employee',
    name: id,
    goalRuns: 0,
    tokens,
    estimatedTokens: 0,
    blockedGoals: 0,
    trend: 'flat',
  }));
  Object.entries(usage.by_job_template).forEach(([id, tokens]) => rows.push({
    id: `template-${id}`,
    dimensionType: 'template',
    name: id,
    goalRuns: 0,
    tokens,
    estimatedTokens: 0,
    blockedGoals: 0,
    trend: 'flat',
  }));
  return rows;
}

type BackendAuditEvent = {
  id: string;
  event_type: string;
  payload: Record<string, string | number | boolean>;
  dispositions?: Array<{
    id: string;
    status: AuditEvent['dispositions'][number]['status'];
    note: string;
    reviewer: string;
  }>;
};

export function mapAuditEvent(event: BackendAuditEvent): AuditEvent {
  return {
    eventId: event.id,
    eventType: event.event_type.includes('approval') ? 'approval_decided' : event.event_type.includes('tool') ? 'tool_call' : 'sensitive_operation',
    subtype: event.event_type,
    severity: 'medium',
    actorType: 'system',
    actorId: 'platform',
    ruleId: 'backend',
    ruleVersion: '1',
    kpiAffecting: false,
    reviewRequired: false,
    occurredAt: nowText(),
    payload: event.payload,
    evidenceRefs: [event.id],
    dispositions: (event.dispositions ?? []).map((disposition) => ({
      ...disposition,
      createdAt: nowText(),
    })),
  };
}

type BackendAuditRule = {
  id: string;
  name: string;
  event_type: string;
  severity: AuditRule['outputSeverity'];
  notification_targets: string[];
  requires_review: boolean;
  retention_days: number;
  enabled: boolean;
};

type BackendAlert = {
  id: string;
  type: AlertMessage['type'];
  message: string;
  time: string;
  resolved: boolean;
};

export function mapAlert(alert: BackendAlert): AlertMessage {
  return {
    id: alert.id,
    type: alert.type,
    message: alert.message,
    time: alert.time,
    resolved: alert.resolved,
  };
}

type BackendAuditNotification = {
  id: string;
  event_id: string;
  rule_id: string;
  channel: AuditNotificationRecord['channel'];
  receiver: string;
  status: AuditNotificationRecord['status'];
  failure_reason?: string;
  created_at: string;
};

export function mapAuditNotification(notification: BackendAuditNotification): AuditNotificationRecord {
  return {
    id: notification.id,
    eventId: notification.event_id,
    ruleId: notification.rule_id,
    channel: notification.channel,
    receiver: notification.receiver,
    status: notification.status,
    failureReason: notification.failure_reason,
    createdAt: notification.created_at,
  };
}

export function mapAuditRule(rule: BackendAuditRule): AuditRule {
  const eventType = ([
    'tool_call',
    'red_line_triggered',
    'approval_requested',
    'approval_decided',
    'escalation_created',
    'abnormal_shutdown',
    'sensitive_operation',
    'budget_blocked',
    'knowledge_preview',
    'template_published',
    'skill_package_changed',
    'artifact_acceptance',
    'notification_failed',
  ] as AuditEventType[]).includes(rule.event_type as AuditEventType) ? rule.event_type as AuditEventType : 'sensitive_operation';
  return {
    id: rule.id,
    name: rule.name,
    description: `匹配后端事件：${rule.event_type}`,
    eventTypes: [eventType],
    conditionSummary: [`event_type = ${rule.event_type}`],
    outputSeverity: rule.severity,
    notify: rule.notification_targets.length > 0,
    receivers: rule.notification_targets,
    reviewRequired: rule.requires_review,
    kpiAffecting: false,
    retentionDays: rule.retention_days === 90 || rule.retention_days === 180 || rule.retention_days === 365 ? rule.retention_days : 'permanent',
    enabled: rule.enabled,
    version: '1',
    updatedAt: nowText(),
  };
}

export async function fetchPlatformData() {
  const [
    templates,
    departments,
    employees,
    models,
    skills,
    tools,
    credentials,
    connections,
    sources,
    quota,
    goalBudgetPolicies,
    ledger,
    usage,
    auditEvents,
    auditRules,
    auditNotifications,
    alerts,
    goals,
    templateOutcomeReports,
  ] = await Promise.all([
    api.get<BackendTemplate[]>('/job-template-versions'),
    api.get<BackendDepartment[]>('/departments'),
    api.get<BackendEmployee[]>('/digital-employees'),
    api.get<BackendModel[]>('/model-configurations'),
    api.get<BackendSkill[]>('/skill-packages'),
    api.get<BackendTool[]>('/tools'),
    api.get<BackendCredential[]>('/credentials'),
    api.get<BackendKnowledgeConnection[]>('/knowledge-connections'),
    api.get<BackendKnowledgeSource[]>('/knowledge-sources'),
    api.get<BackendQuota>('/quota/organization'),
    api.get<BackendGoalBudgetPolicy[]>('/quota/goal-budgets'),
    api.get<BackendLedger[]>('/usage/token-ledger'),
    api.get<BackendUsage>('/usage/analytics'),
    api.get<BackendAuditEvent[]>('/audit/events'),
    api.get<BackendAuditRule[]>('/audit/rules'),
    api.get<BackendAuditNotification[]>('/audit/notifications'),
    api.get<BackendAlert[]>('/alerts'),
    api.get<BackendGoalRun[]>('/goal-runs'),
    api.get<BackendTemplateOutcomeReport[]>('/reports/template-outcomes'),
  ]);
  updateDepartmentDirectory(departments);

  return {
    departments: departments.map(mapDepartment),
    templates: templates.map(mapTemplate),
    employees: employees.map(mapEmployee),
    models: models.map(mapModel),
    skills: skills.map(mapSkill),
    tools: tools.map(mapTool),
    credentials: credentials.map(mapCredential),
    knowledgeConnection: connections[0] ? mapKnowledgeConnection(connections[0]) : undefined,
    knowledgeSources: sources.map(mapKnowledgeSource),
    quota: mapQuota(quota),
    goalBudgetPolicies: goalBudgetPolicies.map(mapGoalBudgetPolicy),
    tokenLedger: ledger.map(mapLedger),
    usageRows: mapUsageRows(usage),
    auditEvents: auditEvents.map(mapAuditEvent),
    auditRules: auditRules.map(mapAuditRule),
    auditNotifications: auditNotifications.map(mapAuditNotification),
    alertMessages: alerts.map(mapAlert),
    goals: goals.map(mapGoal),
    templateOutcomeReports: templateOutcomeReports.map(mapTemplateOutcomeReport),
  };
}

export { API_BASE_URL };
