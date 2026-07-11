// 前端领域类型定义：约束页面、服务层和后端映射之间的数据结构。
export interface Department {
  id: string;
  name: string;
  description: string;
  employeeCount: number;
  templateCount?: number;
}

export type GoalRiskLevel = 'L1' | 'L2' | 'L3' | 'L4';

export interface DigitalEmployee {
  id: string;
  name: string;
  nickname?: string;
  avatarUrl?: string;
  notes?: string;
  managerId?: string;
  role: string;
  grade: 'Staff' | 'Lead' | 'Manager' | 'Director';
  departmentId?: string;
  department: string;
  description: string;
  lifecycleState: 'provisioning' | 'pending_activation' | 'active' | 'disabled' | 'rollout_failed' | 'needs_review';
  runtimeState: 'not_started' | 'starting' | 'healthy' | 'unhealthy' | 'recovering' | 'stopped';
  availabilityState: 'idle' | 'busy' | 'unavailable';
  skills: string[];
  model: string;
  templateId: string;
  maxGoalRiskLevel: GoalRiskLevel;
  activeGoalCount: number;
  rollout: {
    jobId: string;
    currentStep: 'profile_render' | 'token_issue' | 'instance_start' | 'smoke_test' | 'pending_activation' | 'completed' | 'failed';
    status: 'not_started' | 'running' | 'passed' | 'failed' | 'manual_passed';
    startedAt: string;
    endedAt?: string;
    failureClass?: 'transient_infrastructure' | 'configuration_error';
    failureReason?: string;
    repairSuggestion?: string;
    lastSmokeTest: {
      status: 'not_run' | 'passed' | 'failed' | 'manual_passed';
      mode: 'real_probe' | 'manual';
      testedAt?: string;
      summary: string;
    };
  };
  instancePort: number;
  tokenUsedToday: number;
  monthlyTokenUsed: number;
  redLineTriggers: number;
}

export interface WorkItem {
  id: string;
  title: string;
  ownerEmployeeId: string;
  ownerEmployeeName: string;
  parentWorkItemId?: string;
  status: 'pending' | 'in_progress' | 'waiting_approval' | 'waiting_acceptance' | 'completed' | 'blocked';
  delegationReason: string;
  artifact?: string;
  acceptanceStatus?: 'not_submitted' | 'submitted' | 'accepted' | 'rework_requested';
  tokenUsed: number;
}

export interface ExecutionEdge {
  from: string;
  to: string;
  type: 'delegates' | 'handoff' | 'requires_acceptance';
}

export interface GoalArtifact {
  id: string;
  name: string;
  producedByWorkItemId: string;
  acceptanceStatus: 'submitted' | 'accepted' | 'rework_requested';
  reviewer: string;
}

export interface Goal {
  id: string;
  title: string;
  description: string;
  templateId: string;
  rootOwnerId: string;
  rootOwnerName: string;
  status: 'created' | 'in_progress' | 'needs_approval' | 'needs_acceptance' | 'budget_blocked' | 'completed' | 'failed' | 'cancelled';
  riskLevel: GoalRiskLevel;
  budgetTokens: number;
  tokenUsed: number;
  budgetStatus: 'normal' | 'warning' | 'budget_blocked';
  deadline: string;
  createdAt: string;
  completedAt?: string;
  workItems: WorkItem[];
  executionEdges: ExecutionEdge[];
  artifacts: GoalArtifact[];
}

export type ModelType = 'llm' | 'embedding' | 'rerank' | 'vision' | 'audio';

export interface ModelConfig {
  id: string;
  name: string;
  type: ModelType;
  provider: string;
  modelName: string;
  baseUrl: string;
  apiKey: string;
  contextWindow: number;
  maxOutputTokens?: number;
  status: 'active' | 'disabled';
  isDefault?: boolean;
  description: string;
}

export interface SkillDefinition {
  id: string;
  name: string;
  displayName: string;
  category: string;
  version: string;
  description: string;
  status: 'draft' | 'published';
  entryFile: string;
  packageFile: string;
  updatedAt: string;
}

export interface KnowledgeConnection {
  id: string;
  provider: 'ragflow';
  name: string;
  baseUrl: string;
  apiKeyRef: string;
  status: 'connected' | 'disconnected';
  lastTestedAt: string;
  lastSyncedAt: string;
}

export interface KnowledgeSource {
  id: string;
  name: string;
  category: string;
  description: string;
  connectionId: string;
  externalDatasetName: string;
  externalDatasetId: string;
  documentCount: number;
  chunkCount: number;
  status: 'active' | 'disabled';
  syncStatus: 'active' | 'missing' | 'unregistered';
  lastSyncedAt?: string;
  boundTemplateCount: number;
}

export interface KnowledgePreviewHit {
  id: string;
  content: string;
  sourceName: string;
  documentName: string;
  chunkId: string;
  score: number;
  citation: string;
}

export interface TemplateEvaluation {
  status: 'not_run' | 'passed' | 'failed' | 'warning';
  score: number;
  caseCount: number;
  passedCaseCount: number;
  lastRunAt?: string;
  summary: string;
}

export interface BusinessOutcomeMetricBinding {
  id: string;
  name: string;
  source: 'platform_native' | 'tool_business_system' | 'manual_or_imported';
  unit: string;
  target: string;
  actual: string;
  collectionMethod: string;
}

export interface JobTemplate {
  id: string;
  role: string;
  grade: 'Staff' | 'Lead' | 'Manager' | 'Director';
  departmentId?: string;
  department: string;
  description: string;
  systemPrompt: string;
  model: string;
  skills: string[];
  knowledgeSources: string[];
  toolsets: string[];
  redLines: string[];
  defaultGoalBudgetTokens: number;
  maxGoalRiskLevel: GoalRiskLevel;
  evaluation: TemplateEvaluation;
  metricBindings: BusinessOutcomeMetricBinding[];
  isPilot: boolean;
  pilotScenario?: string;
  status: 'published' | 'draft';
  version: string;
}

export interface TemplateOutcomeReport {
  id: string;
  templateId: string;
  templateRole: string;
  version: string;
  period: string;
  goalRuns: number;
  completionRate: number;
  firstPassAcceptanceRate: number;
  reworkRate: number;
  averageCycleHours: number;
  tokenCost: number;
  businessMetrics: BusinessOutcomeMetricBinding[];
  evaluationStatus: TemplateEvaluation['status'];
}

export interface OrganizationQuotaPolicy {
  id: string;
  dailyTokenLimit: number;
  warningThresholdPercent: number;
  timezone: string;
  enforcementMode: 'hard';
  blockedDataPlaneCalls: string[];
  allowedControlPlaneActions: string[];
  updatedAt: string;
}

export interface GoalBudgetPolicy {
  id: string;
  templateId: string;
  defaultBudgetTokens: number;
  warningThresholdPercent: number;
  overageAction: 'block_goal_model_calls' | 'alert_only';
  approvers: string[];
  updatedAt: string;
}

export interface TokenLedgerEntry {
  id: string;
  goalRunId: string;
  workItemId?: string;
  employeeId: string;
  department: string;
  modelConfigId: string;
  hermesInstanceId: string;
  hermesSessionId?: string;
  hermesRunId?: string;
  promptTokens: number;
  completionTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  reasoningTokens: number;
  totalTokens: number;
  estimated: boolean;
  occurredAt: string;
  requestId: string;
}

export interface UsageAnalyticsRow {
  id: string;
  dimensionType: 'department' | 'employee' | 'template';
  name: string;
  goalRuns: number;
  tokens: number;
  estimatedTokens: number;
  blockedGoals: number;
  trend: 'up' | 'down' | 'flat';
}

export type ToolManagedBy = 'platform';
export type ToolIntegrationType = 'platform_api' | 'http_api';
export type ToolRiskLevel = 'low' | 'medium' | 'high';
export type ToolReadWrite = 'read' | 'write';
export type ToolStatus = 'draft' | 'testing' | 'published' | 'disabled' | 'deprecated';
export type CredentialType = 'api_key' | 'oauth_token' | 'basic_auth' | 'webhook_secret';

export interface CredentialRecord {
  credentialId: string;
  name: string;
  type: CredentialType;
  owner: string;
  maskedValue: string;
  status: 'active' | 'rotated' | 'disabled';
  rotatedAt?: string;
  updatedAt: string;
}

export interface ToolDefinition {
  toolId: string;
  name: string;
  displayName: string;
  category: string;
  description: string;
  managedBy: ToolManagedBy;
  integrationType: ToolIntegrationType;
  credentialRef?: string;
  endpointConfig: {
    baseUrl?: string;
    path?: string;
    method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  };
  schemaConfig: {
    request: string;
    response: string;
  };
  riskLevel: ToolRiskLevel;
  readWrite: ToolReadWrite;
  requiresApproval: boolean;
  auditRequired: boolean;
  defaultConstraints: string[];
  idempotencyPolicy?: string;
  status: ToolStatus;
  lastTestStatus: 'passed' | 'failed' | 'not_tested';
  lastTestedAt?: string;
  boundTemplateCount: number;
  version: string;
}

export type AuditSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AuditEventType =
  | 'tool_call'
  | 'red_line_triggered'
  | 'approval_requested'
  | 'approval_decided'
  | 'escalation_created'
  | 'abnormal_shutdown'
  | 'sensitive_operation'
  | 'budget_blocked'
  | 'knowledge_preview'
  | 'template_published'
  | 'skill_package_changed'
  | 'artifact_acceptance'
  | 'notification_failed';

export interface AuditDisposition {
  id: string;
  status: 'false_positive' | 'confirmed' | 'handled' | 'no_action_needed' | 'escalated';
  note: string;
  reviewer: string;
  createdAt: string;
}

export interface AuditEvent {
  eventId: string;
  eventType: AuditEventType;
  subtype?: string;
  severity: AuditSeverity;
  actorType: 'admin' | 'employee' | 'system';
  actorId: string;
  employeeId?: string;
  department?: string;
  resourceType?: string;
  resourceId?: string;
  ruleId: string;
  ruleVersion: string;
  kpiAffecting: boolean;
  reviewRequired: boolean;
  occurredAt: string;
  payload: Record<string, string | number | boolean>;
  evidenceRefs: string[];
  dispositions: AuditDisposition[];
}

export interface AuditRule {
  id: string;
  name: string;
  description: string;
  eventTypes: AuditEventType[];
  conditionSummary: string[];
  outputSeverity: AuditSeverity;
  notify: boolean;
  receivers: string[];
  reviewRequired: boolean;
  kpiAffecting: boolean;
  retentionDays: 90 | 180 | 365 | 'permanent';
  enabled: boolean;
  version: string;
  updatedAt: string;
}

export interface AuditNotificationRecord {
  id: string;
  eventId: string;
  ruleId: string;
  channel: 'in_app' | 'email' | 'feishu' | 'dingtalk';
  receiver: string;
  status: 'sent' | 'pending' | 'failed' | 'not_configured';
  failureReason?: string;
  createdAt: string;
}

export interface AlertMessage {
  id: string;
  type: 'redline' | 'budget' | 'escalation';
  message: string;
  time: string;
  resolved: boolean;
}

export const gradeColorMap: Record<string, string> = {
  Staff: 'blue',
  Lead: 'purple',
  Manager: 'orange',
  Director: 'red',
};

export const modelTypeLabelMap: Record<ModelType, string> = {
  llm: '大语言模型',
  embedding: '向量模型',
  rerank: '排序模型',
  vision: '视觉模型',
  audio: '语音模型',
};
