"""前后端 API 契约和领域读写模型定义。"""

from typing import Literal
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, Field, model_validator


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


TemplateStatus = Literal["draft", "published", "archived"]
EvaluationStatus = Literal["not_evaluated", "passed", "failed", "warning", "expired"]
LifecycleStatus = Literal["provisioning", "pending_activation", "active", "disabled", "rollout_failed", "needs_review", "archived"]
RuntimeStatus = Literal["not_started", "starting", "healthy", "unhealthy", "recovering", "stopped"]
AvailabilityStatus = Literal["idle", "busy", "unavailable"]
CredentialOwnerType = Literal["platform", "department", "employee", "integration"]
ModelType = Literal["large_language_model", "embedding_model", "rerank_model", "vision_model", "speech_model"]
ToolKind = Literal["business"]
BusinessToolAccessShape = Literal["http_api", "platform_adapter"]
ToolLifecycleStatus = Literal["draft", "published", "archived"]
RiskLevel = Literal["low", "medium", "high", "critical"]
KnowledgeConnectionStatus = Literal["unknown", "healthy", "unhealthy"]
KnowledgeSourceStatus = Literal["draft", "active", "syncing", "failed", "archived"]
GoalRunStatus = Literal["draft", "running", "paused", "completed", "failed", "cancelled"]
WorkItemStatus = Literal["pending", "running", "paused", "completed", "failed", "cancelled", "interrupted"]
ApprovalStatus = Literal["pending", "approved", "rejected", "expired", "needs_info"]
ApprovalType = Literal["tool_call", "budget_overrun", "runtime_interruption", "artifact_acceptance", "sensitive_operation"]
ArtifactStatus = Literal["draft", "validation_passed", "validation_failed", "accepted", "rejected"]
QuotaAction = Literal["warn", "block_new_work", "alert_only"]
MetricCollectionMethod = Literal["manual", "api", "external_system"]


class JobTemplateEvaluationCase(BaseModel):
    id: str = Field(default_factory=lambda: new_id("eval-case"))
    title: str
    input_payload: dict = Field(default_factory=dict)
    expected_result: str
    actual_result: str | None = None
    assertions: list[str] = Field(default_factory=list)
    status: Literal["not_evaluated", "passed", "failed"] = "not_evaluated"
    failure_reason: str | None = None


class JobTemplateEvaluationRead(BaseModel):
    job_template_version_id: str
    status: EvaluationStatus
    score: int = 0
    case_count: int = 0
    passed_case_count: int = 0
    evaluator: str | None = None
    summary: str = "未评测。"
    cases: list[JobTemplateEvaluationCase] = Field(default_factory=list)


class JobTemplateEvaluationUpdate(BaseModel):
    status: EvaluationStatus
    score: int = 0
    evaluator: str | None = None
    summary: str
    cases: list[JobTemplateEvaluationCase] = Field(default_factory=list)


class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None


class DepartmentPatch(BaseModel):
    name: str | None = None
    description: str | None = None


class DepartmentRead(DepartmentCreate):
    id: str
    employee_count: int = 0
    template_count: int = 0


class JobTemplateVersionCreate(BaseModel):
    role: str
    version: str = "0.1.0"
    grade: Literal["Staff", "Lead", "Manager", "Director"] = "Staff"
    department_id: str
    model_config_id: str
    description: str
    system_prompt: str
    max_goal_risk_level: Literal["L1", "L2", "L3", "L4"] = "L2"
    default_goal_budget_tokens: int = 200_000
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    knowledge_sources: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)
    metric_bindings: list[dict] = Field(default_factory=list)
    is_pilot: bool = False
    pilot_scenario: str | None = None


class JobTemplateVersionPatch(BaseModel):
    role: str | None = None
    department_id: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    max_goal_risk_level: Literal["L1", "L2", "L3", "L4"] | None = None
    default_goal_budget_tokens: int | None = None
    skills: list[str] | None = None
    tools: list[str] | None = None
    knowledge_sources: list[str] | None = None
    red_lines: list[str] | None = None
    metric_bindings: list[dict] | None = None


class JobTemplateVersionRead(JobTemplateVersionCreate):
    id: str
    status: TemplateStatus = "draft"
    evaluation: JobTemplateEvaluationRead


class RolloutState(BaseModel):
    job_id: str
    current_step: Literal["profile_render", "token_issue", "instance_start", "smoke_test", "pending_activation", "completed", "failed"]
    status: Literal["not_started", "running", "passed", "failed", "manual_passed"]
    last_smoke_test_status: Literal["not_run", "passed", "failed", "manual_passed"] = "not_run"
    summary: str


class DigitalEmployeeCreate(BaseModel):
    name: str
    nickname: str | None = None
    avatar_url: str = Field(validation_alias=AliasChoices("avatar_url", "avatar", "avatarUrl"))
    department_id: str
    manager_id: str | None = None
    job_template_version_id: str
    notes: str | None = None


class DigitalEmployeeRead(DigitalEmployeeCreate):
    id: str
    role: str
    grade: str
    lifecycle_state: LifecycleStatus
    runtime_state: RuntimeStatus
    availability_state: AvailabilityStatus
    max_goal_risk_level: str
    active_goal_count: int = 0
    rollout: RolloutState


class EmployeeOrganizationPatch(BaseModel):
    department_id: str | None = None
    manager_id: str | None = None


class EmployeeRuntimePatch(BaseModel):
    runtime_state: RuntimeStatus
    active_goal_count: int | None = None


class AvailabilityState(BaseModel):
    availability_state: AvailabilityStatus


class CredentialCreate(BaseModel):
    name: str
    owner_type: CredentialOwnerType
    owner_id: str
    owner_name: str
    secret_value: str = Field(min_length=1)
    description: str | None = None


class CredentialPatch(BaseModel):
    name: str | None = None
    owner_type: CredentialOwnerType | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    secret_value: str | None = Field(default=None, min_length=1)
    description: str | None = None


class CredentialRead(BaseModel):
    id: str
    name: str
    owner_type: CredentialOwnerType
    owner_id: str
    owner_name: str
    secret_ref: str
    secret_mask: str
    description: str | None = None


class ModelConfigurationCreate(BaseModel):
    name: str
    model_type: ModelType = Field(default="large_language_model", validation_alias=AliasChoices("model_type", "type"))
    provider: str
    base_url: str
    api_key_credential_id: str
    model_name: str
    context_window: int = Field(gt=0)
    metadata: dict = Field(default_factory=dict)
    enabled: bool = True

    @model_validator(mode="before")
    @classmethod
    def normalize_model_type(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        model_type = data.get("model_type", data.get("type"))
        normalized = {
            "llm": "large_language_model",
            "chat": "large_language_model",
            "completion": "large_language_model",
            "embedding": "embedding_model",
            "rerank": "rerank_model",
            "vision": "vision_model",
            "audio": "speech_model",
            "speech": "speech_model",
        }.get(model_type)
        if normalized:
            data = dict(data)
            data["model_type"] = normalized
        return data


class ModelConfigurationPatch(BaseModel):
    name: str | None = None
    model_type: ModelType | None = None
    provider: str | None = None
    base_url: str | None = None
    api_key_credential_id: str | None = None
    model_name: str | None = None
    context_window: int | None = Field(default=None, gt=0)
    metadata: dict | None = None
    enabled: bool | None = None


class ModelConfigurationRead(ModelConfigurationCreate):
    id: str
    test_status: Literal["not_tested", "passed", "failed"] = "not_tested"
    last_test_message: str | None = None


class ModelConnectionTestResult(BaseModel):
    model_config_id: str
    status: Literal["passed", "failed"]
    message: str


class SkillPackageUpload(BaseModel):
    name: str
    version: str
    package_file_name: str | None = Field(default=None, validation_alias=AliasChoices("package_file_name", "packageFileName", "package_file", "packageFile"))
    package_content_base64: str
    description: str | None = None

    @model_validator(mode="after")
    def fill_package_file_name(self) -> "SkillPackageUpload":
        if self.package_file_name:
            return self
        safe_name = "".join(char if char.isalnum() or char in ("-", "_") else "-" for char in self.name).strip("-")
        safe_version = "".join(char if char.isalnum() or char in ("-", "_", ".") else "-" for char in self.version).strip("-")
        self.package_file_name = f"{safe_name or 'skill'}-{safe_version or '1.0.0'}.zip"
        return self


class SkillPackagePatch(BaseModel):
    name: str | None = None
    version: str | None = None
    description: str | None = None


class SkillPackageRead(BaseModel):
    id: str
    name: str
    version: str
    package_file_name: str
    status: Literal["draft", "published"] = "draft"
    manifest: dict = Field(default_factory=dict)
    description: str | None = None


class TemplateSkillBindingCreate(BaseModel):
    skill_package_ids: list[str]


class TemplateSkillBindingRead(BaseModel):
    job_template_version_id: str
    skill_package_ids: list[str]


class BusinessToolCreate(BaseModel):
    name: str
    category: str
    access_shape: BusinessToolAccessShape
    endpoint_url: str | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None
    request_schema: dict = Field(default_factory=dict)
    response_schema: dict = Field(default_factory=dict)
    owner: str
    credential_id: str | None = None
    risk_level: RiskLevel = "medium"
    audit_required: bool = True
    approval_required: bool = False
    idempotency_policy: str | None = None


class ToolPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    access_shape: BusinessToolAccessShape | None = None
    endpoint_url: str | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None
    request_schema: dict | None = None
    response_schema: dict | None = None
    owner: str | None = None
    credential_id: str | None = None
    read_write: Literal["read_only", "write", "mixed"] | None = None
    default_constraints: list[str] | None = None
    risk_level: RiskLevel | None = None
    audit_required: bool | None = None
    approval_required: bool | None = None
    idempotency_policy: str | None = None
    lifecycle_status: ToolLifecycleStatus | None = None


class ToolRead(BaseModel):
    id: str
    kind: ToolKind
    name: str
    category: str | None = None
    access_shape: BusinessToolAccessShape | None = None
    endpoint_url: str | None = None
    method: str | None = None
    request_schema: dict = Field(default_factory=dict)
    response_schema: dict = Field(default_factory=dict)
    owner: str | None = None
    credential_id: str | None = None
    hermes_registry_id: str | None = None
    read_write: Literal["read_only", "write", "mixed"] | None = None
    default_constraints: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
    audit_required: bool
    approval_required: bool = False
    idempotency_policy: str | None = None
    lifecycle_status: ToolLifecycleStatus = "draft"
    test_status: Literal["not_tested", "passed", "failed"] = "not_tested"
    last_test_message: str | None = None


class KnowledgeConnectionCreate(BaseModel):
    name: str
    provider: Literal["ragflow"] = "ragflow"
    base_url: str
    credential_id: str


class KnowledgeConnectionPatch(BaseModel):
    name: str | None = None
    base_url: str | None = None
    credential_id: str | None = None


class KnowledgeConnectionRead(KnowledgeConnectionCreate):
    id: str
    health_status: KnowledgeConnectionStatus = "unknown"
    sync_metadata: dict = Field(default_factory=dict)


class KnowledgeConnectionTestResult(BaseModel):
    connection_id: str
    status: KnowledgeConnectionStatus
    message: str


class KnowledgeSourceRegister(BaseModel):
    external_id: str
    display_name: str
    source_type: Literal["dataset", "collection", "knowledge_base"] = "dataset"
    authorization_scope: list[str] = Field(default_factory=list)
    retrieval_settings: dict = Field(default_factory=dict)


class KnowledgeSourcePatch(BaseModel):
    display_name: str | None = None
    authorization_scope: list[str] | None = None
    retrieval_settings: dict | None = None
    status: KnowledgeSourceStatus | None = None


class KnowledgeSourceRead(KnowledgeSourceRegister):
    id: str
    connection_id: str
    status: KnowledgeSourceStatus = "active"
    sync_metadata: dict = Field(default_factory=dict)


class EmployeeServiceTokenRead(BaseModel):
    employee_id: str
    token: str


class GoalRunCreate(BaseModel):
    title: str = "未命名目标"
    goal_type: str = "manual"
    description: str = ""
    owner: str = ""
    root_responsible: str = ""
    budget_tokens: int = Field(default=200_000, gt=0)
    policy: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_goal_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if "title" not in normalized:
            normalized["title"] = normalized.get("name") or normalized.get("goalTitle") or "未命名目标"
        if "goal_type" not in normalized:
            normalized["goal_type"] = normalized.get("goalType") or "manual"
        if "description" not in normalized:
            normalized["description"] = normalized["title"]
        if "owner" not in normalized:
            normalized["owner"] = normalized.get("rootOwnerId") or normalized.get("owner_id") or normalized.get("root_responsible") or ""
        if "root_responsible" not in normalized:
            normalized["root_responsible"] = normalized.get("rootResponsible") or normalized.get("rootOwnerName") or normalized.get("owner") or ""
        if "budget_tokens" not in normalized:
            normalized["budget_tokens"] = normalized.get("budgetTokens") or normalized.get("budget") or 200_000
        return normalized


class GoalRunRead(GoalRunCreate):
    id: str
    status: GoalRunStatus = "draft"
    used_tokens: int = 0


class WorkItemCreate(BaseModel):
    goal_run_id: str
    assignee_employee_id: str
    title: str
    input_payload: dict = Field(default_factory=dict)
    parent_work_item_id: str | None = None
    budget_tokens: int | None = Field(default=None, gt=0)


class WorkItemRead(WorkItemCreate):
    id: str
    status: WorkItemStatus = "pending"
    depth: int = 0
    trace_ref: str | None = None


class ExecutionGraphEdgeRead(BaseModel):
    id: str
    goal_run_id: str
    parent_work_item_id: str
    child_work_item_id: str
    relation: Literal["delegated_to"] = "delegated_to"


class DelegationRequest(BaseModel):
    from_work_item_id: str
    assignee_employee_id: str
    title: str
    input_payload: dict = Field(default_factory=dict)


class ApprovalRequestRead(BaseModel):
    id: str
    approval_type: ApprovalType
    status: ApprovalStatus = "pending"
    risk_level: RiskLevel = "medium"
    goal_run_id: str | None = None
    work_item_id: str | None = None
    tool_id: str | None = None
    artifact_id: str | None = None
    assignee: str
    context: dict = Field(default_factory=dict)
    decision_by: str | None = None
    decision_reason: str | None = None


class ApprovalDecision(BaseModel):
    decision_by: str
    reason: str | None = None


class ToolGatewayCall(BaseModel):
    employee_service_token: str
    goal_run_id: str
    work_item_id: str
    tool_id: str
    payload: dict = Field(default_factory=dict)
    approval_id: str | None = None
    token_cost: int = Field(default=0, ge=0)


class ToolGatewayResult(BaseModel):
    status: Literal["executed", "requires_approval", "rejected"]
    tool_id: str
    idempotency_key: str | None = None
    duplicate: bool = False
    approval_id: str | None = None
    result: dict = Field(default_factory=dict)
    audit_id: str


class KnowledgeRetrievalRequest(BaseModel):
    employee_service_token: str
    goal_run_id: str
    work_item_id: str
    knowledge_source_id: str
    query: str
    top_k: int = Field(default=5, gt=0, le=20)


class KnowledgeRetrievalResult(BaseModel):
    answer: str
    citations: list[dict] = Field(default_factory=list)
    audit_id: str


class KnowledgePreviewRequest(BaseModel):
    source_ids: list[str] = Field(min_length=1)
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, gt=0, le=20)


class KnowledgePreviewHit(BaseModel):
    id: str
    content: str
    source_name: str
    document_name: str
    chunk_id: str
    score: float
    citation: str


class KnowledgePreviewResult(BaseModel):
    audit_id: str
    warnings: list[str] = Field(default_factory=list)
    hits: list[KnowledgePreviewHit] = Field(default_factory=list)


class ArtifactCreate(BaseModel):
    goal_run_id: str
    work_item_id: str
    name: str
    artifact_type: str
    uri: str
    requires_acceptance: bool = True
    metadata: dict = Field(default_factory=dict)


class ArtifactRead(ArtifactCreate):
    id: str
    status: ArtifactStatus = "draft"
    version: int = 1


class ArtifactAcceptanceCreate(BaseModel):
    accepted: bool
    reviewer: str
    business_result: str | None = None
    reason: str | None = None


class ArtifactAcceptanceRead(BaseModel):
    id: str
    artifact_id: str
    status: Literal["accepted", "rejected"]
    reviewer: str
    business_result: str | None = None
    reason: str | None = None


class OrganizationQuotaPolicyCreate(BaseModel):
    monthly_token_limit: int = Field(gt=0)
    warning_threshold_percent: int = Field(default=80, gt=0, le=100)
    over_limit_action: QuotaAction = "block_new_work"


class OrganizationQuotaPolicyRead(OrganizationQuotaPolicyCreate):
    id: str
    used_tokens: int = 0
    warning_active: bool = False


GoalBudgetOverageAction = Literal["block_goal_model_calls", "alert_only"]


class GoalBudgetPolicyCreate(BaseModel):
    job_template_version_id: str
    default_budget_tokens: int = Field(gt=0)
    warning_threshold_percent: int = Field(default=80, gt=0, le=100)
    overage_action: GoalBudgetOverageAction = "block_goal_model_calls"
    approvers: list[str] = Field(default_factory=list)


class GoalBudgetPolicyPatch(BaseModel):
    default_budget_tokens: int | None = Field(default=None, gt=0)
    warning_threshold_percent: int | None = Field(default=None, gt=0, le=100)
    overage_action: GoalBudgetOverageAction | None = None
    approvers: list[str] | None = None


class GoalBudgetPolicyRead(GoalBudgetPolicyCreate):
    id: str


class TokenLedgerEntryRead(BaseModel):
    id: str
    organization_id: str = "default-org"
    department_id: str | None = None
    employee_id: str
    model_id: str | None = None
    job_template_version_id: str | None = None
    goal_run_id: str
    work_item_id: str
    usage: Literal["prompt", "smoke_test", "tool_call", "work_item"]
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int
    trace_ref: str | None = None


class UsageAnalyticsRead(BaseModel):
    total_tokens: int
    by_department: dict[str, int] = Field(default_factory=dict)
    by_employee: dict[str, int] = Field(default_factory=dict)
    by_model: dict[str, int] = Field(default_factory=dict)
    by_job_template: dict[str, int] = Field(default_factory=dict)
    by_goal_run: dict[str, int] = Field(default_factory=dict)


class MetricDefinitionCreate(BaseModel):
    name: str
    target_value: str | None = None
    collection_method: MetricCollectionMethod
    data_source: str
    review_cycle: str


class MetricDefinitionRead(MetricDefinitionCreate):
    id: str


class JobTemplateMetricBindingCreate(BaseModel):
    metric_definition_ids: list[str]


class JobTemplateMetricBindingRead(BaseModel):
    job_template_version_id: str
    metric_definition_ids: list[str]


class MetricMeasurementCreate(BaseModel):
    metric_definition_id: str
    value: str
    period: str
    evidence_uri: str | None = None
    reviewer: str | None = None
    source_trace: str | None = None


class MetricMeasurementRead(MetricMeasurementCreate):
    id: str


class BusinessOutcomeMetricBindingRead(BaseModel):
    id: str
    name: str
    source: Literal["platform_native", "tool_business_system", "manual_or_imported"] = "manual_or_imported"
    unit: str = ""
    target: str = "-"
    actual: str = "-"
    collection_method: str = "人工录入"


class TemplateOutcomeReportRead(BaseModel):
    id: str
    template_id: str
    template_role: str
    version: str
    period: str = "当前周期"
    goal_runs: int = 0
    completion_rate: int = 0
    first_pass_acceptance_rate: int = 0
    rework_rate: int = 0
    average_cycle_hours: int = 0
    token_cost: int = 0
    business_metrics: list[BusinessOutcomeMetricBindingRead] = Field(default_factory=list)
    evaluation_status: Literal["not_run", "passed", "failed", "warning"] = "not_run"


class AuditEventRead(BaseModel):
    id: str
    event_type: str
    payload: dict = Field(default_factory=dict)
    dispositions: list[dict] = Field(default_factory=list)


class AuditEventCreate(BaseModel):
    event_type: str
    payload: dict = Field(default_factory=dict)


class AuditDispositionCreate(BaseModel):
    status: str
    note: str
    reviewer: str = "管理员"


class AuditRuleCreate(BaseModel):
    name: str
    event_type: str
    severity: RiskLevel = "medium"
    notification_targets: list[str] = Field(default_factory=list)
    requires_review: bool = False
    escalation_policy: str | None = None
    retention_days: int = Field(default=365, gt=0)


class AuditRulePatch(BaseModel):
    name: str | None = None
    event_type: str | None = None
    severity: RiskLevel | None = None
    notification_targets: list[str] | None = None
    requires_review: bool | None = None
    escalation_policy: str | None = None
    retention_days: int | None = Field(default=None, gt=0)
    enabled: bool | None = None


class AuditRuleRead(AuditRuleCreate):
    id: str
    enabled: bool = True


class ReviewTaskRead(BaseModel):
    id: str
    audit_event_id: str
    audit_rule_id: str
    assignee: str
    status: Literal["open", "closed"] = "open"


class AuditRuleEvaluationRead(BaseModel):
    id: str
    audit_event_id: str
    audit_rule_id: str
    matched: bool
    notifications: list[str] = Field(default_factory=list)
    review_task_id: str | None = None


class AuditNotificationRead(BaseModel):
    id: str
    event_id: str
    rule_id: str
    channel: Literal["in_app", "email", "feishu", "dingtalk"] = "in_app"
    receiver: str
    status: Literal["sent", "pending", "failed", "not_configured"] = "pending"
    failure_reason: str | None = None
    created_at: str


class AlertRead(BaseModel):
    id: str
    type: Literal["redline", "budget", "escalation"]
    message: str
    time: str
    resolved: bool = False
