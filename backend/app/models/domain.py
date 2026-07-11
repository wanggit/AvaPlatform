from __future__ import annotations

"""平台核心领域实体的 SQLAlchemy ORM 定义。"""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uuid_pk() -> str:
    return str(uuid4())


class LifecycleState(StrEnum):
    PROVISIONING = "provisioning"
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    DISABLED = "disabled"
    ROLLOUT_FAILED = "rollout_failed"
    NEEDS_REVIEW = "needs_review"


class RuntimeState(StrEnum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class AvailabilityState(StrEnum):
    IDLE = "idle"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"


class GoalRiskLevel(StrEnum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    departments: Mapped[list[Department]] = relationship(back_populates="organization")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    organization: Mapped[Organization] = relationship(back_populates="departments")
    employees: Mapped[list[DigitalEmployee]] = relationship(back_populates="department")


class DigitalEmployee(Base):
    __tablename__ = "digital_employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), nullable=False)
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("digital_employees.id"))
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(120))
    avatar_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    lifecycle_state: Mapped[str] = mapped_column(String(40), default=LifecycleState.PROVISIONING.value, nullable=False)
    runtime_state: Mapped[str] = mapped_column(String(40), default=RuntimeState.NOT_STARTED.value, nullable=False)
    availability_state: Mapped[str] = mapped_column(String(40), default=AvailabilityState.UNAVAILABLE.value, nullable=False)
    profile_path: Mapped[str | None] = mapped_column(String(1000))
    instance_port: Mapped[int | None] = mapped_column(Integer)
    max_goal_risk_level: Mapped[str] = mapped_column(String(4), default=GoalRiskLevel.L2.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    department: Mapped[Department] = relationship(back_populates="employees")
    manager: Mapped[DigitalEmployee | None] = relationship(remote_side=[id])


class JobTemplate(Base):
    __tablename__ = "job_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(160), nullable=False)
    grade: Mapped[str] = mapped_column(String(30), nullable=False)
    is_pilot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pilot_scenario: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    versions: Mapped[list[JobTemplateVersion]] = relationship(back_populates="template")


class JobTemplateVersion(Base):
    __tablename__ = "job_template_versions"
    __table_args__ = (UniqueConstraint("job_template_id", "version", name="uq_template_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_id: Mapped[str] = mapped_column(ForeignKey("job_templates.id"), nullable=False)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    model_config_id: Mapped[str] = mapped_column(ForeignKey("model_configurations.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    max_goal_risk_level: Mapped[str] = mapped_column(String(4), nullable=False)
    default_goal_budget_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    red_lines: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    template: Mapped[JobTemplate] = relationship(back_populates="versions")


class TemplateEvaluation(Base):
    __tablename__ = "template_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="not_evaluated", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evaluator: Mapped[str | None] = mapped_column(String(120))
    summary: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime)


class TemplateEvaluationCase(Base):
    __tablename__ = "template_evaluation_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    evaluation_id: Mapped[str] = mapped_column(ForeignKey("template_evaluations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, nullable=False)
    actual_result: Mapped[str | None] = mapped_column(Text)
    assertions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="not_evaluated", nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)


class EmployeeRolloutJob(Base):
    __tablename__ = "employee_rollout_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    employee_id: Mapped[str] = mapped_column(ForeignKey("digital_employees.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="running", nullable=False)
    current_step: Mapped[str] = mapped_column(String(80), nullable=False)
    failure_class: Mapped[str | None] = mapped_column(String(80))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    repair_suggestion: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class EmployeeRolloutStep(Base):
    __tablename__ = "employee_rollout_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    rollout_job_id: Mapped[str] = mapped_column(ForeignKey("employee_rollout_jobs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)


class InstanceSmokeTest(Base):
    __tablename__ = "instance_smoke_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    employee_id: Mapped[str] = mapped_column(ForeignKey("digital_employees.id"), nullable=False)
    rollout_job_id: Mapped[str | None] = mapped_column(ForeignKey("employee_rollout_jobs.id"))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    hermes_run_id: Mapped[str | None] = mapped_column(String(120))
    token_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    tested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    masked_value: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_type: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    credential_id: Mapped[str] = mapped_column(ForeignKey("credentials.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    context_window: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_tokens: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class SkillPackage(Base):
    __tablename__ = "skill_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class SkillVersion(Base):
    __tablename__ = "skill_versions"
    __table_args__ = (UniqueConstraint("skill_package_id", "version", name="uq_skill_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    skill_package_id: Mapped[str] = mapped_column(ForeignKey("skill_packages.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    zip_object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    entry_file: Mapped[str] = mapped_column(String(240), default="SKILL.md", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class JobTemplateSkillBinding(Base):
    __tablename__ = "job_template_skill_bindings"
    __table_args__ = (UniqueConstraint("job_template_version_id", "skill_version_id", name="uq_template_skill"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    skill_version_id: Mapped[str] = mapped_column(ForeignKey("skill_versions.id"), nullable=False)


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    managed_by: Mapped[str] = mapped_column(String(40), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)


class ToolVersion(Base):
    __tablename__ = "tool_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tools.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    endpoint_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    schema_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    read_write: Mapped[str] = mapped_column(String(20), nullable=False)
    credential_id: Mapped[str | None] = mapped_column(ForeignKey("credentials.id"))
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    audit_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_constraints: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class ToolIdempotencyPolicy(Base):
    __tablename__ = "tool_idempotency_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    tool_version_id: Mapped[str] = mapped_column(ForeignKey("tool_versions.id"), nullable=False, unique=True)
    key_strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    key_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    duplicate_action: Mapped[str] = mapped_column(String(80), nullable=False)
    external_object_field: Mapped[str | None] = mapped_column(String(120))


class JobTemplateToolBinding(Base):
    __tablename__ = "job_template_tool_bindings"
    __table_args__ = (UniqueConstraint("job_template_version_id", "tool_version_id", name="uq_template_tool"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    tool_version_id: Mapped[str] = mapped_column(ForeignKey("tool_versions.id"), nullable=False)
    entitlement_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class KnowledgeConnection(Base):
    __tablename__ = "knowledge_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    provider: Mapped[str] = mapped_column(String(40), default="ragflow", nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    credential_id: Mapped[str] = mapped_column(ForeignKey("credentials.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="connected", nullable=False)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    connection_id: Mapped[str] = mapped_column(ForeignKey("knowledge_connections.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    external_dataset_id: Mapped[str] = mapped_column(String(240), nullable=False)
    external_dataset_name: Mapped[str] = mapped_column(String(240), nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)
    sync_status: Mapped[str] = mapped_column(String(40), default="active", nullable=False)


class RetrievalPolicy(Base):
    __tablename__ = "retrieval_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    knowledge_source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id"), nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    score_threshold: Mapped[int | None] = mapped_column(Integer)
    citation_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class KnowledgeAuditLog(Base):
    __tablename__ = "knowledge_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("digital_employees.id"))
    knowledge_source_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_sources.id"))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    citations: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    audit_id: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class GoalRun(Base):
    __tablename__ = "goal_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    root_owner_id: Mapped[str] = mapped_column(ForeignKey("digital_employees.id"), nullable=False)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="created", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(4), nullable=False)
    budget_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    token_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    budget_status: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    goal_run_id: Mapped[str] = mapped_column(ForeignKey("goal_runs.id"), nullable=False)
    parent_work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    owner_employee_id: Mapped[str] = mapped_column(ForeignKey("digital_employees.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    delegation_reason: Mapped[str | None] = mapped_column(Text)
    acceptance_status: Mapped[str | None] = mapped_column(String(40))
    token_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hermes_run_id: Mapped[str | None] = mapped_column(String(120))
    trace_context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ExecutionGraphEdge(Base):
    __tablename__ = "execution_graph_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    goal_run_id: Mapped[str] = mapped_column(ForeignKey("goal_runs.id"), nullable=False)
    from_work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id"), nullable=False)
    to_work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id"), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(40), nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    goal_run_id: Mapped[str] = mapped_column(ForeignKey("goal_runs.id"), nullable=False)
    produced_by_work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(1000))
    version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    validation_status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)
    requires_acceptance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ArtifactAcceptance(Base):
    __tablename__ = "artifact_acceptances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(120), nullable=False)
    business_result_ref: Mapped[str | None] = mapped_column(String(240))
    note: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class OrganizationQuotaPolicy(Base):
    __tablename__ = "organization_quota_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    daily_token_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_threshold_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    enforcement_mode: Mapped[str] = mapped_column(String(40), default="hard", nullable=False)
    blocked_data_plane_calls: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_control_plane_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class GoalBudgetPolicy(Base):
    __tablename__ = "goal_budget_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    default_budget_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_threshold_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    overage_action: Mapped[str] = mapped_column(String(80), nullable=False)
    approvers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class TokenLedgerEntry(Base):
    __tablename__ = "token_ledger_entries"
    __table_args__ = (UniqueConstraint("request_id", "model_config_id", name="uq_token_ledger_request_model"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    goal_run_id: Mapped[str | None] = mapped_column(ForeignKey("goal_runs.id"))
    work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    employee_id: Mapped[str] = mapped_column(ForeignKey("digital_employees.id"), nullable=False)
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    model_config_id: Mapped[str] = mapped_column(ForeignKey("model_configurations.id"), nullable=False)
    job_template_version_id: Mapped[str | None] = mapped_column(ForeignKey("job_template_versions.id"))
    purpose: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    request_id: Mapped[str] = mapped_column(String(120), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class UsageAnalyticsSnapshot(Base):
    __tablename__ = "usage_analytics_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    dimension_type: Mapped[str] = mapped_column(String(40), nullable=False)
    dimension_id: Mapped[str] = mapped_column(String(120), nullable=False)
    period: Mapped[str] = mapped_column(String(40), nullable=False)
    goal_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked_goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class BusinessOutcomeMetricDefinition(Base):
    __tablename__ = "business_outcome_metric_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40))
    collection_method: Mapped[str] = mapped_column(String(240), nullable=False)
    review_period: Mapped[str | None] = mapped_column(String(80))


class JobTemplateMetricBinding(Base):
    __tablename__ = "job_template_metric_bindings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    job_template_version_id: Mapped[str] = mapped_column(ForeignKey("job_template_versions.id"), nullable=False)
    metric_definition_id: Mapped[str] = mapped_column(ForeignKey("business_outcome_metric_definitions.id"), nullable=False)
    target_value: Mapped[str | None] = mapped_column(String(120))


class BusinessOutcomeMetricMeasurement(Base):
    __tablename__ = "business_outcome_metric_measurements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    metric_definition_id: Mapped[str] = mapped_column(ForeignKey("business_outcome_metric_definitions.id"), nullable=False)
    goal_run_id: Mapped[str | None] = mapped_column(ForeignKey("goal_runs.id"))
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"))
    measured_value: Mapped[str] = mapped_column(String(120), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    collected_by: Mapped[str | None] = mapped_column(String(120))
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(ForeignKey("digital_employees.id"))
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(120))
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditRule(Base):
    __tablename__ = "audit_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    condition_summary: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    output_severity: Mapped[str] = mapped_column(String(40), nullable=False)
    notify: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    receivers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kpi_affecting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_days: Mapped[str] = mapped_column(String(40), default="180", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditRuleEvaluation(Base):
    __tablename__ = "audit_rule_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    audit_event_id: Mapped[str] = mapped_column(ForeignKey("audit_events.id"), nullable=False)
    audit_rule_id: Mapped[str] = mapped_column(ForeignKey("audit_rules.id"), nullable=False)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    audit_event_id: Mapped[str | None] = mapped_column(ForeignKey("audit_events.id"))
    approval_request_id: Mapped[str | None] = mapped_column(ForeignKey("approval_requests.id"))
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_pk)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(4), nullable=False)
    requester: Mapped[str] = mapped_column(String(120), nullable=False)
    approver: Mapped[str] = mapped_column(String(120), nullable=False)
    goal_run_id: Mapped[str | None] = mapped_column(ForeignKey("goal_runs.id"))
    work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"))
    audit_event_id: Mapped[str | None] = mapped_column(ForeignKey("audit_events.id"))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
