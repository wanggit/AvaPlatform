// oxlint-disable react/only-export-components
// 平台数据上下文：统一加载后端目录数据并向各页面提供刷新能力。
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  type AlertMessage,
  type AuditEvent,
  type AuditNotificationRecord,
  type AuditRule,
  type CredentialRecord,
  type Department,
  type DigitalEmployee,
  type Goal,
  type GoalBudgetPolicy,
  type JobTemplate,
  type KnowledgeConnection,
  type KnowledgeSource,
  type ModelConfig,
  type OrganizationQuotaPolicy,
  type SkillDefinition,
  type TokenLedgerEntry,
  type ToolDefinition,
  type TemplateOutcomeReport,
  type UsageAnalyticsRow,
} from '../types/domain';
import { api, fetchPlatformData, mapAuditEvent, mapAuditRule, mapCredential, mapDepartment, mapGoal, mapGoalBudgetPolicy, mapKnowledgeConnection, mapKnowledgeSource, mapModel, mapQuota, mapSkill, mapTemplate, mapTool, type BackendModel } from './api';

interface PlatformData {
  source: 'backend' | 'unavailable';
  loading: boolean;
  error?: string;
  refresh: () => Promise<void>;
  refreshModels: () => Promise<void>;
  refreshDepartments: () => Promise<void>;
  refreshEmployees: () => Promise<void>;
  refreshTemplates: () => Promise<void>;
  refreshTools: () => Promise<void>;
  refreshCredentials: () => Promise<void>;
  refreshKnowledgeConnection: () => Promise<void>;
  refreshKnowledgeSources: () => Promise<void>;
  refreshAuditEvents: () => Promise<void>;
  refreshAuditRules: () => Promise<void>;
  refreshQuota: () => Promise<void>;
  refreshGoalBudgets: () => Promise<void>;
  refreshGoals: () => Promise<void>;
  refreshSkills: () => Promise<void>;
  templates: JobTemplate[];
  setTemplates: React.Dispatch<React.SetStateAction<JobTemplate[]>>;
  departments: Department[];
  setDepartments: React.Dispatch<React.SetStateAction<Department[]>>;
  employees: DigitalEmployee[];
  setEmployees: React.Dispatch<React.SetStateAction<DigitalEmployee[]>>;
  models: ModelConfig[];
  setModels: React.Dispatch<React.SetStateAction<ModelConfig[]>>;
  skills: SkillDefinition[];
  setSkills: React.Dispatch<React.SetStateAction<SkillDefinition[]>>;
  tools: ToolDefinition[];
  setTools: React.Dispatch<React.SetStateAction<ToolDefinition[]>>;
  credentials: CredentialRecord[];
  setCredentials: React.Dispatch<React.SetStateAction<CredentialRecord[]>>;
  knowledgeConnection: KnowledgeConnection;
  setKnowledgeConnection: React.Dispatch<React.SetStateAction<KnowledgeConnection>>;
  knowledgeSources: KnowledgeSource[];
  setKnowledgeSources: React.Dispatch<React.SetStateAction<KnowledgeSource[]>>;
  organizationQuota: OrganizationQuotaPolicy;
  setOrganizationQuota: React.Dispatch<React.SetStateAction<OrganizationQuotaPolicy>>;
  goalBudgetPolicies: GoalBudgetPolicy[];
  setGoalBudgetPolicies: React.Dispatch<React.SetStateAction<GoalBudgetPolicy[]>>;
  tokenLedger: TokenLedgerEntry[];
  setTokenLedger: React.Dispatch<React.SetStateAction<TokenLedgerEntry[]>>;
  usageAnalytics: UsageAnalyticsRow[];
  setUsageAnalytics: React.Dispatch<React.SetStateAction<UsageAnalyticsRow[]>>;
  goals: Goal[];
  setGoals: React.Dispatch<React.SetStateAction<Goal[]>>;
  templateOutcomeReports: TemplateOutcomeReport[];
  setTemplateOutcomeReports: React.Dispatch<React.SetStateAction<TemplateOutcomeReport[]>>;
  alertMessages: AlertMessage[];
  setAlertMessages: React.Dispatch<React.SetStateAction<AlertMessage[]>>;
  auditEvents: AuditEvent[];
  setAuditEvents: React.Dispatch<React.SetStateAction<AuditEvent[]>>;
  auditRules: AuditRule[];
  setAuditRules: React.Dispatch<React.SetStateAction<AuditRule[]>>;
  auditNotifications: AuditNotificationRecord[];
  setAuditNotifications: React.Dispatch<React.SetStateAction<AuditNotificationRecord[]>>;
}

const PlatformDataContext = createContext<PlatformData | null>(null);

export function PlatformDataProvider({ children }: { children: ReactNode }) {
  const [source, setSource] = useState<'backend' | 'unavailable'>('unavailable');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [templates, setTemplates] = useState<JobTemplate[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [employees, setEmployees] = useState<DigitalEmployee[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [skills, setSkills] = useState<SkillDefinition[]>([]);
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [credentials, setCredentials] = useState<CredentialRecord[]>([]);
  const [knowledgeConnection, setKnowledgeConnection] = useState<KnowledgeConnection>({
    id: '',
    provider: 'ragflow',
    name: 'RAGFlow',
    baseUrl: '',
    apiKeyRef: '',
    status: 'disconnected',
    lastTestedAt: '',
    lastSyncedAt: '',
  });
  const [knowledgeSources, setKnowledgeSources] = useState<KnowledgeSource[]>([]);
  const [organizationQuota, setOrganizationQuota] = useState<OrganizationQuotaPolicy>({
    id: '',
    dailyTokenLimit: 1,
    warningThresholdPercent: 80,
    timezone: 'Asia/Shanghai',
    enforcementMode: 'hard',
    blockedDataPlaneCalls: [],
    allowedControlPlaneActions: [],
    updatedAt: '',
  });
  const [goalBudgetPolicies, setGoalBudgetPolicies] = useState<GoalBudgetPolicy[]>([]);
  const [tokenLedger, setTokenLedger] = useState<TokenLedgerEntry[]>([]);
  const [usageAnalytics, setUsageAnalytics] = useState<UsageAnalyticsRow[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [templateOutcomeReports, setTemplateOutcomeReports] = useState<TemplateOutcomeReport[]>([]);
  const [alertMessages, setAlertMessages] = useState<AlertMessage[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [auditRules, setAuditRules] = useState<AuditRule[]>([]);
  const [auditNotifications, setAuditNotifications] = useState<AuditNotificationRecord[]>([]);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await fetchPlatformData();
      setTemplates(data.templates);
      setDepartments(data.departments);
      setEmployees(data.employees);
      setModels(data.models);
      setSkills(data.skills);
      setTools(data.tools);
      setCredentials(data.credentials);
      if (data.knowledgeConnection) setKnowledgeConnection(data.knowledgeConnection);
      setKnowledgeSources(data.knowledgeSources);
      setOrganizationQuota(data.quota);
      setGoalBudgetPolicies(data.goalBudgetPolicies);
      setTokenLedger(data.tokenLedger);
      setUsageAnalytics(data.usageRows);
      setAuditEvents(data.auditEvents);
      setAuditRules(data.auditRules);
      setAuditNotifications(data.auditNotifications);
      setGoals(data.goals);
      setTemplateOutcomeReports(data.templateOutcomeReports);
      setAlertMessages(data.alertMessages);
      setSource('backend');
      setError(undefined);
    } catch (err) {
      setSource('unavailable');
      setError(err instanceof Error ? err.message : '后端接口加载失败');
    } finally {
      setLoading(false);
    }
  };

  const refreshModels = async () => {
    try {
      const data = await api.get<BackendModel[]>('/model-configurations');
      setModels(data.map(mapModel));
    } catch {
      // 静默失败，保留已有数据
    }
  };

  const refreshDepartments = async () => {
    try {
      const data = await api.get<Parameters<typeof mapDepartment>[0][]>('/departments');
      setDepartments(data.map(mapDepartment));
    } catch { /* 静默失败 */ }
  };

  const refreshEmployees = async () => {
    try {
      const data = await api.get<Parameters<typeof mapEmployee>[0][]>('/digital-employees');
      setEmployees(data.map(mapEmployee));
    } catch { /* 静默失败 */ }
  };

  const refreshTemplates = async () => {
    try {
      const data = await api.get<Parameters<typeof mapTemplate>[0][]>('/job-template-versions');
      setTemplates(data.map(mapTemplate));
    } catch { /* 静默失败 */ }
  };

  const refreshTools = async () => {
    try {
      const data = await api.get<Parameters<typeof mapTool>[0][]>('/tools');
      setTools(data.map(mapTool));
    } catch { /* 静默失败 */ }
  };

  const refreshCredentials = async () => {
    try {
      const data = await api.get<Parameters<typeof mapCredential>[0][]>('/credentials');
      setCredentials(data.map(mapCredential));
    } catch { /* 静默失败 */ }
  };

  const refreshKnowledgeConnection = async () => {
    try {
      const data = await api.get<Parameters<typeof mapKnowledgeConnection>[0][]>('/knowledge-connections');
      if (data[0]) setKnowledgeConnection(mapKnowledgeConnection(data[0]));
    } catch { /* 静默失败 */ }
  };

  const refreshKnowledgeSources = async () => {
    try {
      const data = await api.get<Parameters<typeof mapKnowledgeSource>[0][]>('/knowledge-sources');
      setKnowledgeSources(data.map(mapKnowledgeSource));
    } catch { /* 静默失败 */ }
  };

  const refreshAuditEvents = async () => {
    try {
      const data = await api.get<Parameters<typeof mapAuditEvent>[0][]>('/audit/events');
      setAuditEvents(data.map(mapAuditEvent));
    } catch { /* 静默失败 */ }
  };

  const refreshAuditRules = async () => {
    try {
      const data = await api.get<Parameters<typeof mapAuditRule>[0][]>('/audit/rules');
      setAuditRules(data.map(mapAuditRule));
    } catch { /* 静默失败 */ }
  };

  const refreshQuota = async () => {
    try {
      const data = await api.get<Parameters<typeof mapQuota>[0]>('/quota/organization');
      setOrganizationQuota(mapQuota(data));
    } catch { /* 静默失败 */ }
  };

  const refreshGoalBudgets = async () => {
    try {
      const data = await api.get<Parameters<typeof mapGoalBudgetPolicy>[0][]>('/quota/goal-budgets');
      setGoalBudgetPolicies(data.map(mapGoalBudgetPolicy));
    } catch { /* 静默失败 */ }
  };

  const refreshGoals = async () => {
    try {
      const data = await api.get<Parameters<typeof mapGoal>[0][]>('/goal-runs');
      setGoals(data.map(mapGoal));
    } catch { /* 静默失败 */ }
  };

  const refreshSkills = async () => {
    try {
      const data = await api.get<Parameters<typeof mapSkill>[0][]>('/skill-packages');
      setSkills(data.map(mapSkill));
    } catch { /* 静默失败 */ }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const value = useMemo<PlatformData>(() => ({
    source,
    loading,
    error,
    refresh,
    refreshModels,
    refreshDepartments,
    refreshEmployees,
    refreshTemplates,
    refreshTools,
    refreshCredentials,
    refreshKnowledgeConnection,
    refreshKnowledgeSources,
    refreshAuditEvents,
    refreshAuditRules,
    refreshQuota,
    refreshGoalBudgets,
    refreshGoals,
    refreshSkills,
    templates,
    setTemplates,
    departments,
    setDepartments,
    employees,
    setEmployees,
    models,
    setModels,
    skills,
    setSkills,
    tools,
    setTools,
    credentials,
    setCredentials,
    knowledgeConnection,
    setKnowledgeConnection,
    knowledgeSources,
    setKnowledgeSources,
    organizationQuota,
    setOrganizationQuota,
    goalBudgetPolicies,
    setGoalBudgetPolicies,
    tokenLedger,
    setTokenLedger,
    usageAnalytics,
    setUsageAnalytics,
    goals,
    setGoals,
    templateOutcomeReports,
    setTemplateOutcomeReports,
    alertMessages,
    setAlertMessages,
    auditEvents,
    setAuditEvents,
    auditRules,
    setAuditRules,
    auditNotifications,
    setAuditNotifications,
  }), [source, loading, error, refresh, refreshModels, refreshDepartments, refreshEmployees, refreshTemplates, refreshTools, refreshCredentials, refreshKnowledgeConnection, refreshKnowledgeSources, refreshAuditEvents, refreshAuditRules, refreshQuota, refreshGoalBudgets, refreshGoals, refreshSkills, templates, departments, employees, models, skills, tools, credentials, knowledgeConnection, knowledgeSources, organizationQuota, goalBudgetPolicies, tokenLedger, usageAnalytics, goals, templateOutcomeReports, alertMessages, auditEvents, auditRules, auditNotifications]);

  return <PlatformDataContext.Provider value={value}>{children}</PlatformDataContext.Provider>;
}

export function usePlatformData() {
  const context = useContext(PlatformDataContext);
  if (!context) throw new Error('usePlatformData must be used inside PlatformDataProvider');
  return context;
}
