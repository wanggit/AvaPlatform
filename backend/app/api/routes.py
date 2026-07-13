"""集中定义前端调用的 REST API，并把 HTTP 错误转换为业务可读提示。"""

from fastapi import APIRouter, HTTPException, Response

from app.schemas import (
    AvailabilityState,
    AlertRead,
    ApprovalDecision,
    ApprovalRequestRead,
    ArtifactAcceptanceCreate,
    ArtifactAcceptanceRead,
    ArtifactCreate,
    ArtifactRead,
    AuditDispositionCreate,
    AuditEventCreate,
    AuditEventRead,
    AuditNotificationRead,
    AuditRuleCreate,
    AuditRuleEvaluationRead,
    AuditRulePatch,
    AuditRuleRead,
    BusinessToolCreate,
    CredentialCreate,
    CredentialPatch,
    CredentialRead,
    DelegationRequest,
    DepartmentCreate,
    DepartmentPatch,
    DepartmentRead,
    DigitalEmployeeCreate,
    DigitalEmployeeRead,
    EmployeeOrganizationPatch,
    EmployeeRuntimePatch,
    EmployeeServiceTokenRead,
    ExecutionGraphEdgeRead,
    GoalBudgetPolicyCreate,
    GoalBudgetPolicyPatch,
    GoalBudgetPolicyRead,
    GoalRunCreate,
    GoalRunRead,
    JobTemplateEvaluationRead,
    JobTemplateEvaluationUpdate,
    JobTemplateVersionCreate,
    JobTemplateVersionPatch,
    JobTemplateVersionRead,
    KnowledgeConnectionCreate,
    KnowledgeConnectionPatch,
    KnowledgeConnectionRead,
    KnowledgeConnectionTestResult,
    KnowledgePreviewRequest,
    KnowledgePreviewResult,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
    KnowledgeSourcePatch,
    KnowledgeSourceRead,
    KnowledgeSourceRegister,
    JobTemplateMetricBindingCreate,
    JobTemplateMetricBindingRead,
    MetricDefinitionCreate,
    MetricDefinitionRead,
    MetricMeasurementCreate,
    MetricMeasurementRead,
    ModelConfigurationCreate,
    ModelConfigurationPatch,
    ModelConfigurationRead,
    ModelConnectionTestResult,
    SkillPackagePatch,
    SkillPackageRead,
    SkillPackageUpload,
    TemplateSkillBindingCreate,
    TemplateSkillBindingRead,
    TemplateEvaluationRunRequest,
    TemplateEvaluationRunResponse,
    OrganizationQuotaPolicyCreate,
    OrganizationQuotaPolicyRead,
    TemplateOutcomeReportRead,
    ToolGatewayCall,
    ToolGatewayResult,
    ToolPatch,
    ToolRead,
    TokenLedgerEntryRead,
    UsageAnalyticsRead,
    WorkItemCreate,
    WorkItemRead,
)
from app.runtime.dependencies import probe_dependencies
from app.services import ConflictError, store

router = APIRouter(prefix="/api/v1")


@router.get("/system/dependencies")
def system_dependencies() -> dict:
    probes = probe_dependencies()
    return {
        "status": "healthy" if all(probe.status == "healthy" for probe in probes) else "degraded",
        "dependencies": [probe.__dict__ for probe in probes],
    }


@router.get("/alerts", response_model=list[AlertRead])
def list_alerts() -> list[AlertRead]:
    return store.list_alerts()


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments() -> list[DepartmentRead]:
    return store.list_departments()


@router.post("/departments", response_model=DepartmentRead, status_code=201)
def create_department(payload: DepartmentCreate) -> DepartmentRead:
    return store.create_department(payload)


@router.get("/departments/{department_id}", response_model=DepartmentRead)
def get_department(department_id: str) -> DepartmentRead:
    department = store.get_department(department_id)
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    return department


@router.patch("/departments/{department_id}", response_model=DepartmentRead)
def patch_department(department_id: str, payload: DepartmentPatch) -> DepartmentRead:
    department = store.patch_department(department_id, payload)
    if not department:
        raise HTTPException(status_code=404, detail="部门不存在")
    return department


@router.delete("/departments/{department_id}", status_code=204)
def delete_department(department_id: str) -> Response:
    try:
        deleted = store.delete_department(department_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="部门不存在")
    return Response(status_code=204)


@router.get("/credentials", response_model=list[CredentialRead])
def list_credentials() -> list[CredentialRead]:
    return store.list_credentials()


@router.post("/credentials", response_model=CredentialRead, status_code=201)
def create_credential(payload: CredentialCreate) -> CredentialRead:
    return store.create_credential(payload)


@router.get("/credentials/{credential_id}", response_model=CredentialRead)
def get_credential(credential_id: str) -> CredentialRead:
    credential = store.get_credential(credential_id)
    if not credential:
        raise HTTPException(status_code=404, detail="凭据不存在")
    return credential


@router.patch("/credentials/{credential_id}", response_model=CredentialRead)
def patch_credential(credential_id: str, payload: CredentialPatch) -> CredentialRead:
    credential = store.patch_credential(credential_id, payload)
    if not credential:
        raise HTTPException(status_code=404, detail="凭据不存在")
    return credential


@router.delete("/credentials/{credential_id}", status_code=204)
def delete_credential(credential_id: str) -> Response:
    try:
        deleted = store.delete_credential(credential_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="凭据不存在")
    return Response(status_code=204)


@router.get("/model-configurations", response_model=list[ModelConfigurationRead])
def list_model_configurations(enabled: bool | None = None, model_type: str | None = None) -> list[ModelConfigurationRead]:
    return store.list_model_configurations(enabled=enabled, model_type=model_type)


@router.post("/model-configurations", response_model=ModelConfigurationRead, status_code=201)
def create_model_configuration(payload: ModelConfigurationCreate) -> ModelConfigurationRead:
    try:
        return store.create_model_configuration(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/model-configurations/{model_id}", response_model=ModelConfigurationRead)
def get_model_configuration(model_id: str) -> ModelConfigurationRead:
    model = store.get_model_configuration(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return model


@router.patch("/model-configurations/{model_id}", response_model=ModelConfigurationRead)
def patch_model_configuration(model_id: str, payload: ModelConfigurationPatch) -> ModelConfigurationRead:
    try:
        model = store.patch_model_configuration(model_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return model


@router.delete("/model-configurations/{model_id}", status_code=204)
def delete_model_configuration(model_id: str) -> Response:
    try:
        if not store.delete_model_configuration(model_id):
            raise HTTPException(status_code=404, detail="模型配置不存在")
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/model-configurations/{model_id}/enable", response_model=ModelConfigurationRead)
def enable_model_configuration(model_id: str) -> ModelConfigurationRead:
    model = store.set_model_enabled(model_id, True)
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return model


@router.post("/model-configurations/{model_id}/disable", response_model=ModelConfigurationRead)
def disable_model_configuration(model_id: str) -> ModelConfigurationRead:
    try:
        model = store.set_model_enabled(model_id, False)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not model:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return model


@router.post("/model-configurations/{model_id}/test", response_model=ModelConnectionTestResult)
def test_model_configuration(model_id: str) -> ModelConnectionTestResult:
    result = store.test_model_connection(model_id)
    if not result:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return result


@router.post("/skill-packages", response_model=SkillPackageRead, status_code=201)
def upload_skill_package(payload: SkillPackageUpload) -> SkillPackageRead:
    try:
        return store.upload_skill_package(payload)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/skill-packages", response_model=list[SkillPackageRead])
def list_skill_packages() -> list[SkillPackageRead]:
    return store.list_skill_packages()


@router.patch("/skill-packages/{skill_id}", response_model=SkillPackageRead)
def patch_skill_package(skill_id: str, payload: SkillPackagePatch) -> SkillPackageRead:
    skill = store.patch_skill_package(skill_id, payload)
    if not skill:
        raise HTTPException(status_code=404, detail="技能包不存在")
    return skill


@router.post("/skill-packages/{skill_id}/publish", response_model=SkillPackageRead)
def publish_skill_package(skill_id: str) -> SkillPackageRead:
    skill = store.publish_skill_package(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能包不存在")
    return skill


@router.post("/skill-packages/{skill_id}/unpublish", response_model=SkillPackageRead)
def unpublish_skill_package(skill_id: str) -> SkillPackageRead:
    try:
        skill = store.unpublish_skill_package(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not skill:
        raise HTTPException(status_code=404, detail="技能包不存在")
    return skill


@router.delete("/skill-packages/{skill_id}", status_code=204)
def delete_skill_package(skill_id: str):
    try:
        deleted = store.delete_skill_package(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="技能包不存在")


@router.put("/job-template-versions/{version_id}/skill-bindings", response_model=TemplateSkillBindingRead)
def bind_skills_to_template(version_id: str, payload: TemplateSkillBindingCreate) -> TemplateSkillBindingRead:
    try:
        return store.bind_skills_to_template(version_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/tools", response_model=list[ToolRead])
def list_tools() -> list[ToolRead]:
    return store.list_tools()


@router.post("/tools/business", response_model=ToolRead, status_code=201)
def create_business_tool(payload: BusinessToolCreate) -> ToolRead:
    try:
        return store.create_business_tool(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/tools/{tool_id}", response_model=ToolRead)
def patch_tool(tool_id: str, payload: ToolPatch) -> ToolRead:
    try:
        tool = store.patch_tool(tool_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


@router.post("/tools/{tool_id}/test", response_model=ToolRead)
def test_tool(tool_id: str) -> ToolRead:
    tool = store.test_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


@router.post("/tools/{tool_id}/publish", response_model=ToolRead)
def publish_tool(tool_id: str) -> ToolRead:
    try:
        tool = store.publish_tool(tool_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    return tool


@router.delete("/tools/{tool_id}", status_code=204)
def delete_tool(tool_id: str) -> Response:
    if not store.delete_tool(tool_id):
        raise HTTPException(status_code=404, detail="工具不存在")
    return Response(status_code=204)


@router.get("/knowledge-connections", response_model=list[KnowledgeConnectionRead])
def list_knowledge_connections() -> list[KnowledgeConnectionRead]:
    return store.list_knowledge_connections()


@router.post("/knowledge-connections", response_model=KnowledgeConnectionRead, status_code=201)
def create_knowledge_connection(payload: KnowledgeConnectionCreate) -> KnowledgeConnectionRead:
    try:
        return store.create_knowledge_connection(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/knowledge-connections/{connection_id}", response_model=KnowledgeConnectionRead)
def patch_knowledge_connection(connection_id: str, payload: KnowledgeConnectionPatch) -> KnowledgeConnectionRead:
    try:
        connection = store.patch_knowledge_connection(connection_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not connection:
        raise HTTPException(status_code=404, detail="知识连接不存在")
    return connection


@router.delete("/knowledge-connections/{connection_id}", status_code=204)
def delete_knowledge_connection(connection_id: str) -> Response:
    if not store.delete_knowledge_connection(connection_id):
        raise HTTPException(status_code=404, detail="知识连接不存在")
    return Response(status_code=204)


@router.post("/knowledge-connections/{connection_id}/test", response_model=KnowledgeConnectionTestResult)
def test_knowledge_connection(connection_id: str) -> KnowledgeConnectionTestResult:
    result = store.test_knowledge_connection(connection_id)
    if not result:
        raise HTTPException(status_code=404, detail="知识连接不存在")
    return result


@router.get("/knowledge-connections/{connection_id}/discover", response_model=list[KnowledgeSourceRead])
def discover_knowledge_sources(connection_id: str) -> list[KnowledgeSourceRead]:
    sources = store.discover_knowledge_sources(connection_id)
    if sources is None:
        raise HTTPException(status_code=404, detail="知识连接不存在")
    return sources


@router.get("/knowledge-sources", response_model=list[KnowledgeSourceRead])
def list_knowledge_sources() -> list[KnowledgeSourceRead]:
    return store.list_knowledge_sources()


@router.post("/knowledge-connections/{connection_id}/sources", response_model=KnowledgeSourceRead, status_code=201)
def register_knowledge_source(connection_id: str, payload: KnowledgeSourceRegister) -> KnowledgeSourceRead:
    try:
        return store.register_knowledge_source(connection_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/knowledge-sources/{source_id}", response_model=KnowledgeSourceRead)
def patch_knowledge_source(source_id: str, payload: KnowledgeSourcePatch) -> KnowledgeSourceRead:
    source = store.patch_knowledge_source(source_id, payload)
    if not source:
        raise HTTPException(status_code=404, detail="知识源不存在")
    return source


@router.post("/goal-runs", response_model=GoalRunRead, status_code=201)
def create_goal_run(payload: GoalRunCreate) -> GoalRunRead:
    return store.create_goal_run(payload)


@router.get("/goal-runs", response_model=list[GoalRunRead])
def list_goal_runs() -> list[GoalRunRead]:
    return store.list_goal_runs()


@router.get("/goal-runs/{goal_run_id}", response_model=GoalRunRead)
def get_goal_run(goal_run_id: str) -> GoalRunRead:
    goal = store.get_goal_run(goal_run_id)
    if not goal:
        raise HTTPException(status_code=404, detail="目标运行不存在")
    return goal


@router.post("/goal-runs/{goal_run_id}/resume", response_model=GoalRunRead)
def resume_goal_run(goal_run_id: str) -> GoalRunRead:
    goal = store.resume_goal_run(goal_run_id)
    if not goal:
        raise HTTPException(status_code=404, detail="目标运行不存在")
    return goal


@router.post("/work-items", response_model=WorkItemRead, status_code=201)
def create_work_item(payload: WorkItemCreate) -> WorkItemRead:
    try:
        return store.create_work_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/work-items/delegations", response_model=WorkItemRead, status_code=201)
def delegate_work_item(payload: DelegationRequest) -> WorkItemRead:
    try:
        return store.delegate_work_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/goal-runs/{goal_run_id}/execution-edges", response_model=list[ExecutionGraphEdgeRead])
def list_execution_edges(goal_run_id: str) -> list[ExecutionGraphEdgeRead]:
    return store.list_execution_edges(goal_run_id)


@router.post("/digital-employees/{employee_id}/service-token", response_model=EmployeeServiceTokenRead)
def issue_employee_service_token(employee_id: str) -> EmployeeServiceTokenRead:
    token = store.issue_employee_service_token(employee_id)
    if not token:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return token


@router.post("/gateway/tool-calls", response_model=ToolGatewayResult)
def call_tool_gateway(payload: ToolGatewayCall) -> ToolGatewayResult:
    try:
        return store.call_tool_gateway(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/approvals", response_model=list[ApprovalRequestRead])
def list_approvals(
    status: str | None = None,
    approval_type: str | None = None,
    risk_level: str | None = None,
    goal_run_id: str | None = None,
    assignee: str | None = None,
) -> list[ApprovalRequestRead]:
    return store.list_approvals(
        status=status,
        approval_type=approval_type,
        risk_level=risk_level,
        goal_run_id=goal_run_id,
        assignee=assignee,
    )


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestRead)
def approve_request(approval_id: str, payload: ApprovalDecision) -> ApprovalRequestRead:
    approval = store.decide_approval(approval_id, "approved", payload)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return approval


@router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestRead)
def reject_request(approval_id: str, payload: ApprovalDecision) -> ApprovalRequestRead:
    approval = store.decide_approval(approval_id, "rejected", payload)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return approval


@router.post("/approvals/{approval_id}/needs-info", response_model=ApprovalRequestRead)
def request_approval_info(approval_id: str, payload: ApprovalDecision) -> ApprovalRequestRead:
    approval = store.decide_approval(approval_id, "needs_info", payload)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return approval


@router.post("/approvals/{approval_id}/expire", response_model=ApprovalRequestRead)
def expire_request(approval_id: str, payload: ApprovalDecision) -> ApprovalRequestRead:
    approval = store.decide_approval(approval_id, "expired", payload)
    if not approval:
        raise HTTPException(status_code=404, detail="审批请求不存在")
    return approval


@router.post("/gateway/knowledge/search", response_model=KnowledgeRetrievalResult)
def retrieve_knowledge(payload: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
    try:
        return store.retrieve_knowledge(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/knowledge/preview", response_model=KnowledgePreviewResult)
def preview_knowledge_retrieval(payload: KnowledgePreviewRequest) -> KnowledgePreviewResult:
    try:
        return store.preview_knowledge_retrieval(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/artifacts", response_model=ArtifactRead, status_code=201)
def create_artifact(payload: ArtifactCreate) -> ArtifactRead:
    try:
        return store.create_artifact(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/artifacts/{artifact_id}/acceptance", response_model=ArtifactAcceptanceRead)
def accept_artifact(artifact_id: str, payload: ArtifactAcceptanceCreate) -> ArtifactAcceptanceRead:
    acceptance = store.accept_artifact(artifact_id, payload)
    if not acceptance:
        raise HTTPException(status_code=404, detail="产物不存在")
    return acceptance


@router.get("/quota/organization", response_model=OrganizationQuotaPolicyRead)
def get_organization_quota() -> OrganizationQuotaPolicyRead:
    return store.get_organization_quota()


@router.put("/quota/organization", response_model=OrganizationQuotaPolicyRead)
def update_organization_quota(payload: OrganizationQuotaPolicyCreate) -> OrganizationQuotaPolicyRead:
    return store.update_organization_quota(payload)


@router.get("/quota/goal-budgets", response_model=list[GoalBudgetPolicyRead])
def list_goal_budget_policies() -> list[GoalBudgetPolicyRead]:
    return store.list_goal_budget_policies()


@router.post("/quota/goal-budgets", response_model=GoalBudgetPolicyRead, status_code=201)
def create_goal_budget_policy(payload: GoalBudgetPolicyCreate) -> GoalBudgetPolicyRead:
    try:
        return store.create_goal_budget_policy(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/quota/goal-budgets/{policy_id}", response_model=GoalBudgetPolicyRead)
def patch_goal_budget_policy(policy_id: str, payload: GoalBudgetPolicyPatch) -> GoalBudgetPolicyRead:
    policy = store.patch_goal_budget_policy(policy_id, payload)
    if not policy:
        raise HTTPException(status_code=404, detail="目标预算策略不存在")
    return policy


@router.get("/usage/token-ledger", response_model=list[TokenLedgerEntryRead])
def list_token_ledger() -> list[TokenLedgerEntryRead]:
    return store.list_token_ledger()


@router.get("/usage/analytics", response_model=UsageAnalyticsRead)
def usage_analytics() -> UsageAnalyticsRead:
    return store.usage_analytics()


@router.post("/metrics/definitions", response_model=MetricDefinitionRead, status_code=201)
def create_metric_definition(payload: MetricDefinitionCreate) -> MetricDefinitionRead:
    return store.create_metric_definition(payload)


@router.put("/job-template-versions/{version_id}/metric-bindings", response_model=JobTemplateMetricBindingRead)
def bind_metrics_to_template(version_id: str, payload: JobTemplateMetricBindingCreate) -> JobTemplateMetricBindingRead:
    try:
        return store.bind_metrics_to_template(version_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/metrics/measurements", response_model=MetricMeasurementRead, status_code=201)
def record_metric_measurement(payload: MetricMeasurementCreate) -> MetricMeasurementRead:
    try:
        return store.record_metric_measurement(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/reports/template-outcomes", response_model=list[TemplateOutcomeReportRead])
def list_template_outcome_reports() -> list[TemplateOutcomeReportRead]:
    return store.list_template_outcome_reports()


@router.get("/audit/events", response_model=list[AuditEventRead])
def list_audit_events() -> list[AuditEventRead]:
    return store.list_audit_events()


@router.post("/audit/events", response_model=AuditEventRead, status_code=201)
def create_audit_event(payload: AuditEventCreate) -> AuditEventRead:
    return store.create_audit_event(payload)


@router.post("/audit/events/{audit_event_id}/dispositions", response_model=AuditEventRead)
def add_audit_disposition(audit_event_id: str, payload: AuditDispositionCreate) -> AuditEventRead:
    event = store.add_audit_disposition(audit_event_id, payload)
    if not event:
        raise HTTPException(status_code=404, detail="审计事件不存在")
    return event


@router.get("/audit/rules", response_model=list[AuditRuleRead])
def list_audit_rules() -> list[AuditRuleRead]:
    return store.list_audit_rules()


@router.post("/audit/rules", response_model=AuditRuleRead, status_code=201)
def create_audit_rule(payload: AuditRuleCreate) -> AuditRuleRead:
    return store.create_audit_rule(payload)


@router.patch("/audit/rules/{rule_id}", response_model=AuditRuleRead)
def patch_audit_rule(rule_id: str, payload: AuditRulePatch) -> AuditRuleRead:
    rule = store.patch_audit_rule(rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="审计规则不存在")
    return rule


@router.post("/audit/rules/{rule_id}/evaluate/{audit_event_id}", response_model=AuditRuleEvaluationRead)
def evaluate_audit_rule(rule_id: str, audit_event_id: str) -> AuditRuleEvaluationRead:
    try:
        return store.evaluate_audit_rule(rule_id, audit_event_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/audit/notifications", response_model=list[AuditNotificationRead])
def list_audit_notifications() -> list[AuditNotificationRead]:
    return store.list_audit_notifications()


@router.get("/job-template-versions", response_model=list[JobTemplateVersionRead])
def list_job_template_versions() -> list[JobTemplateVersionRead]:
    return store.list_job_template_versions()


@router.post("/job-template-versions", response_model=JobTemplateVersionRead, status_code=201)
def create_job_template_version(payload: JobTemplateVersionCreate) -> JobTemplateVersionRead:
    try:
        return store.create_job_template_version(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/job-template-versions/{version_id}", response_model=JobTemplateVersionRead)
def get_job_template_version(version_id: str) -> JobTemplateVersionRead:
    version = store.get_job_template_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="岗位模板版本不存在")
    return version


@router.patch("/job-template-versions/{version_id}", response_model=JobTemplateVersionRead)
def patch_job_template_version(version_id: str, payload: JobTemplateVersionPatch) -> JobTemplateVersionRead:
    try:
        version = store.patch_job_template_version(version_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not version:
        raise HTTPException(status_code=404, detail="岗位模板版本不存在")
    return version


@router.post("/job-template-versions/{version_id}/publish", response_model=JobTemplateVersionRead)
def publish_job_template_version(version_id: str) -> JobTemplateVersionRead:
    version = store.get_job_template_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="岗位模板版本不存在")
    if version.evaluation.status != "passed":
        raise HTTPException(status_code=409, detail="岗位模板版本必须先通过模板评测才能发布")
    version = store.set_job_template_version_status(version_id, "published")
    return version


@router.post("/job-template-versions/{version_id}/archive", response_model=JobTemplateVersionRead)
def archive_job_template_version(version_id: str) -> JobTemplateVersionRead:
    version = store.set_job_template_version_status(version_id, "archived")
    if not version:
        raise HTTPException(status_code=404, detail="岗位模板版本不存在")
    return version


@router.delete("/job-template-versions/{version_id}", status_code=204)
def delete_job_template_version(version_id: str) -> None:
    try:
        deleted = store.delete_job_template_version(version_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="岗位模板版本不存在")


@router.get("/job-template-versions/{version_id}/evaluation", response_model=JobTemplateEvaluationRead)
def get_template_evaluation(version_id: str) -> JobTemplateEvaluationRead:
    evaluation = store.get_template_evaluation(version_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="岗位模板评测不存在")
    return evaluation


@router.put("/job-template-versions/{version_id}/evaluation", response_model=JobTemplateEvaluationRead)
def update_template_evaluation(version_id: str, payload: JobTemplateEvaluationUpdate) -> JobTemplateEvaluationRead:
    evaluation = store.update_template_evaluation(version_id, payload)
    if not evaluation:
        raise HTTPException(status_code=404, detail="岗位模板版本不存在")
    return evaluation


@router.post("/job-template-versions/{version_id}/evaluation/run", response_model=TemplateEvaluationRunResponse)
def run_template_evaluation(version_id: str, payload: TemplateEvaluationRunRequest) -> TemplateEvaluationRunResponse:
    result = store.run_template_evaluation(version_id, payload.task_description)
    return TemplateEvaluationRunResponse(**result)


@router.get("/digital-employees", response_model=list[DigitalEmployeeRead])
def list_digital_employees() -> list[DigitalEmployeeRead]:
    return store.list_digital_employees()


@router.post("/digital-employees", response_model=DigitalEmployeeRead, status_code=201)
def create_digital_employee(payload: DigitalEmployeeCreate) -> DigitalEmployeeRead:
    try:
        return store.create_digital_employee(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/digital-employees/{employee_id}", response_model=DigitalEmployeeRead)
def get_digital_employee(employee_id: str) -> DigitalEmployeeRead:
    employee = store.get_digital_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.patch("/digital-employees/{employee_id}/organization", response_model=DigitalEmployeeRead)
def patch_employee_organization(employee_id: str, payload: EmployeeOrganizationPatch) -> DigitalEmployeeRead:
    try:
        employee = store.patch_employee_organization(employee_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.patch("/digital-employees/{employee_id}/manager", response_model=DigitalEmployeeRead)
def patch_employee_manager(employee_id: str, payload: EmployeeOrganizationPatch) -> DigitalEmployeeRead:
    try:
        employee = store.patch_employee_organization(employee_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.patch("/digital-employees/{employee_id}/runtime", response_model=DigitalEmployeeRead)
def patch_employee_runtime(employee_id: str, payload: EmployeeRuntimePatch) -> DigitalEmployeeRead:
    employee = store.patch_employee_runtime(employee_id, payload)
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.post("/digital-employees/{employee_id}/smoke-test", response_model=DigitalEmployeeRead)
def rerun_employee_smoke_test(employee_id: str) -> DigitalEmployeeRead:
    employee = store.rerun_employee_smoke_test(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.post("/digital-employees/{employee_id}/activate", response_model=DigitalEmployeeRead)
def activate_employee(employee_id: str) -> DigitalEmployeeRead:
    employee = store.set_employee_lifecycle(employee_id, "active")
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.post("/digital-employees/{employee_id}/disable", response_model=DigitalEmployeeRead)
def disable_employee(employee_id: str) -> DigitalEmployeeRead:
    employee = store.set_employee_lifecycle(employee_id, "disabled")
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.post("/digital-employees/{employee_id}/archive", response_model=DigitalEmployeeRead)
def archive_employee(employee_id: str) -> DigitalEmployeeRead:
    employee = store.set_employee_lifecycle(employee_id, "archived")
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return employee


@router.get("/digital-employees/{employee_id}/availability", response_model=AvailabilityState)
def get_employee_availability(employee_id: str) -> AvailabilityState:
    employee = store.get_digital_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="数字员工不存在")
    return AvailabilityState(availability_state=employee.availability_state)
