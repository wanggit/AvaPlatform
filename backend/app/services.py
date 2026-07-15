"""平台核心应用服务，负责领域规则、外部调用编排和持久化状态变更。"""

import base64
import binascii
import hashlib
import io
import json
import logging
import re
import secrets
import threading
import time
import zipfile
from threading import RLock
from typing import Any, Literal

import httpx

from app.config import settings
from app.db.relational_state import load_relational_state, save_relational_state
from app.integrations.hermes import HermesClient, HermesDashboardClient
from app.runtime.port_pool import PortPool

logger = logging.getLogger(__name__)


class ConflictError(ValueError):
    """资源冲突错误（如同名资源已存在），应返回 HTTP 409。"""
    pass
from app.schemas import (
    ApprovalDecision,
    ApprovalRequestRead,
    ArtifactAcceptanceCreate,
    ArtifactAcceptanceRead,
    ArtifactCreate,
    ArtifactRead,
    AlertRead,
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
    EvaluationStatus,
    ExecutionGraphEdgeRead,
    GoalRunCreate,
    GoalRunRead,
    GoalBudgetPolicyCreate,
    GoalBudgetPolicyPatch,
    GoalBudgetPolicyRead,
    JobTemplateEvaluationCase,
    JobTemplateEvaluationRead,
    JobTemplateEvaluationUpdate,
    JobTemplateVersionCreate,
    JobTemplateVersionPatch,
    JobTemplateVersionRead,
    KnowledgeConnectionCreate,
    KnowledgeConnectionPatch,
    KnowledgeConnectionRead,
    KnowledgeConnectionTestResult,
    KnowledgePreviewHit,
    KnowledgePreviewRequest,
    KnowledgePreviewResult,
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResult,
    KnowledgeSourceRead,
    KnowledgeSourceRegister,
    KnowledgeSourcePatch,
    LifecycleStatus,
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
    RolloutState,
    RuntimeStatus,
    SkillPackagePatch,
    SkillPackageRead,
    SkillPackageUpload,
    TemplateSkillBindingCreate,
    TemplateSkillBindingRead,
    BusinessOutcomeMetricBindingRead,
    OrganizationQuotaPolicyCreate,
    OrganizationQuotaPolicyRead,
    ReviewTaskRead,
    TemplateOutcomeReportRead,
    ToolGatewayCall,
    ToolGatewayResult,
    ToolPatch,
    ToolRead,
    TokenLedgerEntryRead,
    UsageAnalyticsRead,
    WorkItemCreate,
    WorkItemRead,
    new_id,
)


def compute_availability(lifecycle_state: LifecycleStatus, runtime_state: RuntimeStatus, active_goal_count: int) -> str:
    if lifecycle_state != "active":
        return "unavailable"
    if runtime_state != "healthy":
        return "unavailable"
    return "busy" if active_goal_count > 0 else "idle"


_PROVIDER_API_KEY_ENV_OVERRIDES = {
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
}


def _provider_api_key_env_var(provider: str) -> str:
    normalized = provider.strip().lower()
    if not normalized:
        raise ValueError("模型供应商未配置，无法推导 API Key 环境变量")
    if normalized in _PROVIDER_API_KEY_ENV_OVERRIDES:
        return _PROVIDER_API_KEY_ENV_OVERRIDES[normalized]
    return f"{re.sub(r'[^a-z0-9]+', '_', normalized).strip('_').upper()}_API_KEY"


def _log_preview(value: str, limit: int = 500) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


class InMemoryStore:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.secret_values: dict[str, str] = {}
        self.credentials: dict[str, CredentialRead] = {}
        self.model_configurations: dict[str, ModelConfigurationRead] = {}
        if settings.default_llm_api_key:
            self.secret_values["secret-cred-default-llm"] = settings.default_llm_api_key
            self.credentials["cred-default-llm"] = CredentialRead(
                id="cred-default-llm",
                name=f"{settings.default_llm_name} 密钥",
                owner_type="platform",
                owner_id="platform",
                owner_name="Platform",
                secret_ref="secret-cred-default-llm",
                secret_mask=self._mask_secret(settings.default_llm_api_key),
                description="默认大语言模型 API Key 引用。",
            )
            self.model_configurations["model-default-llm"] = ModelConfigurationRead(
                id="model-default-llm",
                name=settings.default_llm_name,
                model_type="large_language_model",
                provider=settings.default_llm_provider,
                base_url=settings.default_llm_base_url,
                api_key="cred-default-llm",
                model_name=settings.default_llm_model,
                context_window=settings.default_llm_context_window,
                enabled=True,
                test_status="not_tested",
            )
        if settings.ragflow_api_key:
            self.secret_values["secret-cred-ragflow"] = settings.ragflow_api_key
            self.credentials["cred-ragflow"] = CredentialRead(
                id="cred-ragflow",
                name="RAGFlow API Key",
                owner_type="integration",
                owner_id="ragflow",
                owner_name="RAGFlow",
                secret_ref="secret-cred-ragflow",
                secret_mask=self._mask_secret(settings.ragflow_api_key),
                description="RAGFlow API Key 引用。",
            )
        self.skill_packages: dict[str, SkillPackageRead] = {}
        self.template_skill_bindings: dict[str, TemplateSkillBindingRead] = {}
        self.tools: dict[str, ToolRead] = {}
        self.knowledge_connections: dict[str, KnowledgeConnectionRead] = {}
        if settings.ragflow_api_key:
            self.knowledge_connections["kc-ragflow"] = KnowledgeConnectionRead(
                id="kc-ragflow",
                name="RAGFlow",
                provider="ragflow",
                base_url=settings.ragflow_base_url,
                credential_id="cred-ragflow",
                health_status="unknown",
                sync_metadata={},
            )
        self.knowledge_sources: dict[str, KnowledgeSourceRead] = {}
        self.goal_runs: dict[str, GoalRunRead] = {}
        self.work_items: dict[str, WorkItemRead] = {}
        self.execution_edges: dict[str, ExecutionGraphEdgeRead] = {}
        self.approvals: dict[str, ApprovalRequestRead] = {}
        self.artifacts: dict[str, ArtifactRead] = {}
        self.artifact_acceptances: dict[str, ArtifactAcceptanceRead] = {}
        self.employee_service_tokens: dict[str, str] = {}
        self.idempotency_results: dict[str, ToolGatewayResult] = {}
        self.organization_quota = OrganizationQuotaPolicyRead(
            id="quota-default-org",
            monthly_token_limit=1_000_000,
            warning_threshold_percent=80,
            over_limit_action="block_new_work",
            used_tokens=0,
            warning_active=False,
        )
        self.goal_budget_policies: dict[str, GoalBudgetPolicyRead] = {}
        self.token_ledger: list[TokenLedgerEntryRead] = []
        self.metric_definitions: dict[str, MetricDefinitionRead] = {}
        self.template_metric_bindings: dict[str, JobTemplateMetricBindingRead] = {}
        self.metric_measurements: dict[str, MetricMeasurementRead] = {}
        self.audit_events: list[AuditEventRead] = []
        self.audit_rules: dict[str, AuditRuleRead] = {}
        self.audit_rule_evaluations: dict[str, AuditRuleEvaluationRead] = {}
        self.review_tasks: dict[str, ReviewTaskRead] = {}
        self.departments: dict[str, DepartmentRead] = {}
        self.template_versions: dict[str, JobTemplateVersionRead] = {}
        self.employees: dict[str, DigitalEmployeeRead] = {}

        # 评测基础设施
        self.port_pool = PortPool(
            start=settings.eval_port_range_start,
            end=settings.eval_port_range_end,
        )
        self._eval_locks: dict[str, threading.Lock] = {}
        self._dashboard = HermesDashboardClient(
            settings.hermes_dashboard_url,
            settings.hermes_dashboard_token,
        )

    def _audit(self, event_type: str, payload: dict) -> str:
        audit_id = new_id("audit")
        self.audit_events.append(AuditEventRead(id=audit_id, event_type=event_type, payload=payload))
        return audit_id

    def _eval_lock_for(self, version_id: str) -> threading.Lock:
        """获取模板版本级别的评测锁，防止并发评测。"""
        if version_id not in self._eval_locks:
            self._eval_locks[version_id] = threading.Lock()
        return self._eval_locks[version_id]

    def _mask_secret(self, value: str) -> str:
        if len(value) <= 4:
            return "***"
        return f"{value[:2]}***{value[-2:]}"

    def _require_credential(self, credential_id: str) -> CredentialRead:
        credential = self.credentials.get(credential_id)
        if not credential:
            raise ValueError("凭据不存在")
        return credential

    def _credential_secret(self, credential_id: str | None) -> str | None:
        if not credential_id:
            return None
        credential = self.credentials.get(credential_id)
        if not credential:
            return None
        return self.secret_values.get(credential.secret_ref)

    def _evaluation_profile_env(self, model_config: ModelConfigurationRead | None) -> dict[str, str]:
        if model_config:
            provider = model_config.provider
            secret = self._credential_secret(model_config.api_key)
            if secret is None and model_config.api_key not in self.credentials:
                secret = model_config.api_key or None
            model_label = model_config.name
        else:
            provider = settings.default_llm_provider
            secret = settings.default_llm_api_key or None
            model_label = settings.default_llm_name

        if not secret:
            raise ValueError(f"模型配置「{model_label}」缺少 API Key，无法执行评测。请在模型配置中绑定有效凭据。")

        return {_provider_api_key_env_var(provider): secret}

    def _department_with_counts(self, department: DepartmentRead) -> DepartmentRead:
        employee_count = sum(1 for employee in self.employees.values() if employee.department_id == department.id)
        template_count = sum(1 for template in self.template_versions.values() if template.department_id == department.id)
        return department.model_copy(update={"employee_count": employee_count, "template_count": template_count})

    def list_departments(self) -> list[DepartmentRead]:
        return [self._department_with_counts(department) for department in self.departments.values()]

    def get_department(self, department_id: str) -> DepartmentRead | None:
        department = self.departments.get(department_id)
        return self._department_with_counts(department) if department else None

    def create_department(self, payload: DepartmentCreate) -> DepartmentRead:
        department_id = new_id("dept")
        department = DepartmentRead(id=department_id, **payload.model_dump())
        self.departments[department_id] = department
        self._audit("department_created", {"department_id": department_id})
        return department

    def patch_department(self, department_id: str, payload: DepartmentPatch) -> DepartmentRead | None:
        department = self.departments.get(department_id)
        if not department:
            return None
        data = department.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        updated = DepartmentRead(**data)
        self.departments[department_id] = updated
        self._audit("department_updated", {"department_id": department_id})
        return self._department_with_counts(updated)

    def delete_department(self, department_id: str) -> bool:
        department = self.get_department(department_id)
        if not department:
            return False
        if department.employee_count > 0 or department.template_count > 0:
            raise ValueError("部门仍被数字员工或岗位模板引用，不能删除")
        del self.departments[department_id]
        self._audit("department_deleted", {"department_id": department_id})
        return True

    def list_credentials(self) -> list[CredentialRead]:
        return list(self.credentials.values())

    def get_credential(self, credential_id: str) -> CredentialRead | None:
        return self.credentials.get(credential_id)

    def create_credential(self, payload: CredentialCreate) -> CredentialRead:
        credential_id = new_id("cred")
        secret_ref = f"secret-{credential_id}"
        self.secret_values[secret_ref] = payload.secret_value
        credential = CredentialRead(
            id=credential_id,
            name=payload.name,
            owner_type=payload.owner_type,
            owner_id=payload.owner_id,
            owner_name=payload.owner_name,
            secret_ref=secret_ref,
            secret_mask=self._mask_secret(payload.secret_value),
            description=payload.description,
        )
        self.credentials[credential_id] = credential
        return credential

    def patch_credential(self, credential_id: str, payload: CredentialPatch) -> CredentialRead | None:
        credential = self.credentials.get(credential_id)
        if not credential:
            return None
        data = credential.model_dump()
        patch = payload.model_dump(exclude_unset=True)
        secret_value = patch.pop("secret_value", None)
        if secret_value:
            self.secret_values[credential.secret_ref] = secret_value
            patch["secret_mask"] = self._mask_secret(secret_value)
        data.update(patch)
        updated = CredentialRead(**data)
        self.credentials[credential_id] = updated
        return updated

    def delete_credential(self, credential_id: str) -> bool:
        credential = self.credentials.get(credential_id)
        if not credential:
            return False
        # 检查凭证是否被工具引用
        referencing_tools: list[str] = []
        for tool in self.tools.values():
            if getattr(tool, "credential_id", None) == credential_id:
                referencing_tools.append(f"{tool.name}（{tool.id}）")
        # 检查凭证是否被知识库连接引用
        referencing_connections: list[str] = []
        for conn in self.knowledge_connections.values():
            if getattr(conn, "credential_id", None) == credential_id:
                referencing_connections.append(f"{conn.name}（{conn.id}）")
        all_references = referencing_tools + referencing_connections
        if all_references:
            raise ValueError(
                f"凭证「{credential.name}」仍被以下资源引用，不能删除：\n"
                + "\n".join(f"  - {ref}" for ref in all_references)
            )
        del self.credentials[credential_id]
        self.secret_values.pop(credential.secret_ref, None)
        return True

    def list_model_configurations(self, enabled: bool | None = None, model_type: str | None = None) -> list[ModelConfigurationRead]:
        models = list(self.model_configurations.values())
        if enabled is not None:
            models = [model for model in models if model.enabled is enabled]
        if model_type:
            models = [model for model in models if model.model_type == model_type]
        return models

    def get_model_configuration(self, model_id: str) -> ModelConfigurationRead | None:
        return self.model_configurations.get(model_id)

    def create_model_configuration(self, payload: ModelConfigurationCreate) -> ModelConfigurationRead:
        model_id = new_id("model")
        model = ModelConfigurationRead(id=model_id, test_status="not_tested", **payload.model_dump())
        self.model_configurations[model_id] = model
        return model

    def patch_model_configuration(self, model_id: str, payload: ModelConfigurationPatch) -> ModelConfigurationRead | None:
        model = self.model_configurations.get(model_id)
        if not model:
            return None
        patch = payload.model_dump(exclude_unset=True)
        data = model.model_dump()
        data.update(patch)
        updated = ModelConfigurationRead(**data)
        self.model_configurations[model_id] = updated
        return updated

    def delete_model_configuration(self, model_id: str) -> bool:
        model = self.model_configurations.get(model_id)
        if model is None:
            return False
        if model.enabled:
            raise ConflictError("只有已停用的模型才能删除，请先停用该模型。")
        return self.model_configurations.pop(model_id, None) is not None

    def set_model_enabled(self, model_id: str, enabled: bool) -> ModelConfigurationRead | None:
        model = self.model_configurations.get(model_id)
        if not model:
            return None
        if not enabled:
            referencing = [
                version
                for version in self.template_versions.values()
                if version.model_config_id == model_id
            ]
            if referencing:
                names = "\n".join(f"  - {version.role}（{version.grade}）" for version in referencing)
                raise ConflictError(
                    f"以下岗位模板仍在使用该模型，无法停用：\n{names}\n请先将这些模板切换到其他模型后再操作。"
                )
        updated = model.model_copy(update={"enabled": enabled})
        self.model_configurations[model_id] = updated
        return updated

    def test_model_connection(self, model_id: str) -> ModelConnectionTestResult | None:
        model = self.model_configurations.get(model_id)
        if not model:
            return None
        if not model.base_url.startswith("http") or not model.model_name or not model.api_key:
            status = "failed"
            message = "模型配置缺少基础地址、模型名称或密钥。"
        else:
            try:
                message = self._probe_model_connection(model)
                status = "passed"
            except ValueError as exc:
                status = "failed"
                message = str(exc)
        self.model_configurations[model_id] = model.model_copy(update={"test_status": status, "last_test_message": message})
        return ModelConnectionTestResult(model_config_id=model_id, status=status, message=message)

    def _probe_model_connection(self, model: ModelConfigurationRead) -> str:
        provider = model.provider.lower()
        api_key = model.api_key
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        base_url = model.base_url.rstrip("/")
        try:
            if provider == "ollama":
                response = httpx.get(f"{base_url}/api/tags", timeout=10, trust_env=False)
                response.raise_for_status()
                body = response.json()
                names = [str(item.get("name") or item.get("model")) for item in body.get("models", []) if isinstance(item, dict)]
            else:
                response = httpx.get(f"{base_url}/models", headers=headers, timeout=10, trust_env=False)
                response.raise_for_status()
                body = response.json()
                data = body.get("data") if isinstance(body, dict) else body
                names = [str(item.get("id") or item.get("name")) for item in data or [] if isinstance(item, dict)]
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError(f"模型连接测试失败：{exc}") from exc
        if names and not self._model_name_matches(model.model_name, names):
            raise ValueError(f"模型连接可达，但未发现模型 {model.model_name}。")
        return f"模型连接测试通过，已从 {model.provider} 发现 {len(names)} 个模型。"

    def _model_name_matches(self, model_name: str, discovered_names: list[str]) -> bool:
        return any(name == model_name or name.split(":", 1)[0] == model_name for name in discovered_names)

    def upload_skill_package(self, payload: SkillPackageUpload) -> SkillPackageRead:
        if not payload.package_file_name.endswith(".zip"):
            raise ValueError("技能包必须是 zip 压缩包")
        # 重名检测
        existing = next(
            (s for s in self.skill_packages.values() if s.name == payload.name and s.version == payload.version),
            None,
        )
        if existing:
            raise ConflictError(f"同名同版本的技能包已存在: {payload.name} v{payload.version}")
        try:
            raw = base64.b64decode(payload.package_content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("技能包内容不是有效的 base64") from exc
        with io.BytesIO(raw) as buffer:
            if not zipfile.is_zipfile(buffer):
                raise ValueError("技能包内容不是有效的 zip 文件")
            buffer.seek(0)
            with zipfile.ZipFile(buffer) as package:
                names = [name for name in package.namelist() if not name.endswith("/")]
        if not names:
            raise ValueError("技能包不能为空")
        if not any(name.endswith("SKILL.md") for name in names):
            raise ValueError("技能包必须包含 SKILL.md")
        skill_id = new_id("skill")
        skill = SkillPackageRead(
            id=skill_id,
            name=payload.name,
            version=payload.version,
            package_file_name=payload.package_file_name,
            manifest={"files": names},
            description=payload.description,
        )
        self.skill_packages[skill_id] = skill
        return skill

    def list_skill_packages(self) -> list[SkillPackageRead]:
        return list(self.skill_packages.values())

    def patch_skill_package(self, skill_id: str, payload: SkillPackagePatch) -> SkillPackageRead | None:
        skill = self.skill_packages.get(skill_id)
        if not skill:
            return None
        data = skill.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        updated = SkillPackageRead(**data)
        self.skill_packages[skill_id] = updated
        self._audit("skill_package_updated", {"skill_package_id": skill_id})
        return updated

    def publish_skill_package(self, skill_id: str) -> SkillPackageRead | None:
        skill = self.skill_packages.get(skill_id)
        if not skill:
            return None
        updated = skill.model_copy(update={"status": "published"})
        self.skill_packages[skill_id] = updated
        return updated

    def unpublish_skill_package(self, skill_id: str) -> SkillPackageRead | None:
        skill = self.skill_packages.get(skill_id)
        if not skill:
            return None
        if skill.status != "published":
            raise ValueError("只有已发布的技能才能下架")
        # 检查是否有岗位模板引用了此技能
        referencing_templates = self._find_templates_referencing_skill(skill_id)
        if referencing_templates:
            raise ValueError(f"技能被以下岗位模板引用，无法下架: {', '.join(referencing_templates)}")
        updated = skill.model_copy(update={"status": "draft"})
        self.skill_packages[skill_id] = updated
        self._audit("skill_package_unpublished", {"skill_package_id": skill_id})
        return updated

    def _find_templates_referencing_skill(self, skill_id: str) -> list[str]:
        """查找引用了指定技能的岗位模板名称列表。"""
        referencing: list[str] = []
        for version_id, binding in self.template_skill_bindings.items():
            if skill_id in binding.skill_package_ids:
                version = self.template_versions.get(version_id)
                if version:
                    referencing.append(f"{version.role}({version.id})")
        return referencing

    def delete_skill_package(self, skill_id: str) -> bool:
        skill = self.skill_packages.get(skill_id)
        if not skill:
            return False
        if skill.status == "published":
            raise ValueError("已发布的技能无法删除，请先下架")
        del self.skill_packages[skill_id]
        self._audit("skill_package_deleted", {"skill_package_id": skill_id})
        return True

    def bind_skills_to_template(self, version_id: str, payload: TemplateSkillBindingCreate) -> TemplateSkillBindingRead:
        if version_id not in self.template_versions:
            raise ValueError("岗位模板版本不存在")
        missing = [skill_id for skill_id in payload.skill_package_ids if skill_id not in self.skill_packages]
        if missing:
            raise ValueError("技能包不存在")
        binding = TemplateSkillBindingRead(job_template_version_id=version_id, skill_package_ids=payload.skill_package_ids)
        self.template_skill_bindings[version_id] = binding
        version = self.template_versions[version_id]
        self.template_versions[version_id] = version.model_copy(update={"skills": payload.skill_package_ids})
        return binding

    def list_tools(self) -> list[ToolRead]:
        return list(self.tools.values())

    def create_business_tool(self, payload: BusinessToolCreate) -> ToolRead:
        if payload.credential_id:
            self._require_credential(payload.credential_id)
        if payload.access_shape == "http_api" and not payload.endpoint_url:
            raise ValueError("该接入形态必须填写接口地址")
        if payload.access_shape == "http_api" and not payload.method:
            raise ValueError("HTTP API 工具必须填写请求方法")
        tool_id = new_id("tool")
        tool = ToolRead(id=tool_id, kind="business", lifecycle_status="draft", **payload.model_dump())
        self.tools[tool_id] = tool
        return tool

    def patch_tool(self, tool_id: str, payload: ToolPatch) -> ToolRead | None:
        tool = self.tools.get(tool_id)
        if not tool:
            return None
        patch = payload.model_dump(exclude_unset=True)
        credential_id = patch.get("credential_id")
        if credential_id:
            self._require_credential(credential_id)
        data = tool.model_dump()
        data.update(patch)
        updated = ToolRead(**data)
        self.tools[tool_id] = updated
        self._audit("tool_updated", {"tool_id": tool_id})
        return updated

    def test_tool(self, tool_id: str) -> ToolRead | None:
        tool = self.tools.get(tool_id)
        if not tool:
            return None
        try:
            message = self._probe_tool(tool)
            passed = True
        except ValueError as exc:
            message = str(exc)
            passed = False
        updated = tool.model_copy(update={
            "test_status": "passed" if passed else "failed",
            "last_test_message": message,
        })
        self.tools[tool_id] = updated
        self._audit("tool_tested", {"tool_id": tool_id, "status": updated.test_status})
        return updated

    def _probe_tool(self, tool: ToolRead) -> str:
        if not tool.endpoint_url:
            raise ValueError("工具缺少接口地址。")
        if tool.access_shape == "platform_adapter":
            return "Platform Adapter 地址已登记；实际调用由 Tool Gateway 执行。"
        credential_secret = self._credential_secret(tool.credential_id)
        headers = {"Authorization": f"Bearer {credential_secret}"} if credential_secret else {}
        try:
            response = httpx.request("OPTIONS", tool.endpoint_url, headers=headers, timeout=10, trust_env=False)
        except httpx.HTTPError as exc:
            raise ValueError(f"工具接口连接测试失败：{exc}") from exc
        if response.status_code < 500 or response.status_code in {401, 403, 405}:
            return f"工具接口连接测试完成，服务返回 HTTP {response.status_code}。"
        raise ValueError(f"工具接口连接测试失败，服务返回 HTTP {response.status_code}。")

    def publish_tool(self, tool_id: str) -> ToolRead | None:
        tool = self.tools.get(tool_id)
        if not tool:
            return None
        if tool.kind == "business" and not tool.idempotency_policy:
            raise ValueError("业务工具发布前必须配置幂等性策略")
        updated = tool.model_copy(update={"lifecycle_status": "published"})
        self.tools[tool_id] = updated
        self._audit("tool_published", {"tool_id": tool_id, "kind": tool.kind})
        return updated

    def delete_tool(self, tool_id: str) -> bool:
        tool = self.tools.pop(tool_id, None)
        if not tool:
            return False
        self._audit("tool_deleted", {"tool_id": tool_id})
        return True

    def list_knowledge_connections(self) -> list[KnowledgeConnectionRead]:
        return list(self.knowledge_connections.values())

    def create_knowledge_connection(self, payload: KnowledgeConnectionCreate) -> KnowledgeConnectionRead:
        self._require_credential(payload.credential_id)
        connection_id = new_id("kc")
        connection = KnowledgeConnectionRead(id=connection_id, health_status="unknown", sync_metadata={}, **payload.model_dump())
        self.knowledge_connections[connection_id] = connection
        return connection

    def patch_knowledge_connection(self, connection_id: str, payload: KnowledgeConnectionPatch) -> KnowledgeConnectionRead | None:
        connection = self.knowledge_connections.get(connection_id)
        if not connection:
            return None
        patch = payload.model_dump(exclude_unset=True)
        credential_id = patch.get("credential_id")
        if credential_id:
            self._require_credential(credential_id)
        data = connection.model_dump()
        data.update(patch)
        updated = KnowledgeConnectionRead(**data)
        self.knowledge_connections[connection_id] = updated
        return updated

    def delete_knowledge_connection(self, connection_id: str) -> bool:
        return self.knowledge_connections.pop(connection_id, None) is not None

    def test_knowledge_connection(self, connection_id: str) -> KnowledgeConnectionTestResult | None:
        connection = self.knowledge_connections.get(connection_id)
        if not connection:
            return None
        if not connection.base_url.startswith("http") or connection.credential_id not in self.credentials:
            status = "unhealthy"
            message = "RAGFlow 连接缺少基础地址或凭据。"
        else:
            try:
                count = len(self.discover_knowledge_sources(connection_id) or [])
                status = "healthy"
                message = f"RAGFlow 连接健康，已发现 {count} 个数据集。"
            except ValueError as exc:
                status = "unhealthy"
                message = str(exc)
        self.knowledge_connections[connection_id] = connection.model_copy(update={"health_status": status})
        return KnowledgeConnectionTestResult(connection_id=connection_id, status=status, message=message)

    def discover_knowledge_sources(self, connection_id: str) -> list[KnowledgeSourceRead] | None:
        connection = self.knowledge_connections.get(connection_id)
        if not connection:
            return None
        credential = self.credentials.get(connection.credential_id)
        api_key = self.secret_values.get(credential.secret_ref) if credential else None
        if not api_key:
            raise ValueError("RAGFlow 连接缺少可用凭据")
        try:
            response = httpx.get(
                f"{connection.base_url.rstrip('/')}/api/v1/datasets",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
                trust_env=False,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError(f"RAGFlow 数据集同步失败：{exc}") from exc
        if body.get("code") not in (0, "0", None):
            raise ValueError(f"RAGFlow 数据集同步失败：{body.get('message') or body.get('error') or body.get('code')}")
        datasets = body.get("data") or []
        discovered: list[KnowledgeSourceRead] = []
        for dataset in datasets:
            dataset_id = str(dataset.get("id") or dataset.get("dataset_id") or dataset.get("kb_id") or "")
            if not dataset_id:
                continue
            display_name = str(dataset.get("name") or dataset.get("display_name") or dataset_id)
            discovered.append(KnowledgeSourceRead(
                id=f"discovered-{connection_id}-{dataset_id}",
                connection_id=connection_id,
                external_id=dataset_id,
                display_name=display_name,
                source_type="dataset",
                status="active",
                sync_metadata={
                    "provider": connection.provider,
                    "document_count": dataset.get("document_count") or dataset.get("doc_num") or 0,
                    "chunk_count": dataset.get("chunk_count") or dataset.get("chunk_num") or 0,
                },
            ))
        return discovered

    def register_knowledge_source(self, connection_id: str, payload: KnowledgeSourceRegister) -> KnowledgeSourceRead:
        if connection_id not in self.knowledge_connections:
            raise ValueError("知识连接不存在")
        source_id = new_id("ks")
        source = KnowledgeSourceRead(
            id=source_id,
            connection_id=connection_id,
            status="active",
            sync_metadata={"provider": "ragflow"},
            **payload.model_dump(),
        )
        self.knowledge_sources[source_id] = source
        return source

    def patch_knowledge_source(self, source_id: str, payload: KnowledgeSourcePatch) -> KnowledgeSourceRead | None:
        source = self.knowledge_sources.get(source_id)
        if not source:
            return None
        data = source.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        updated = KnowledgeSourceRead(**data)
        self.knowledge_sources[source_id] = updated
        self._audit("knowledge_source_updated", {"knowledge_source_id": source_id})
        return updated

    def list_knowledge_sources(self) -> list[KnowledgeSourceRead]:
        return list(self.knowledge_sources.values())

    def issue_employee_service_token(self, employee_id: str) -> EmployeeServiceTokenRead | None:
        if employee_id not in self.employees:
            return None
        for token, token_employee_id in self.employee_service_tokens.items():
            if token_employee_id == employee_id:
                return EmployeeServiceTokenRead(employee_id=employee_id, token=token)
        token = f"dev-token-{employee_id}"
        self.employee_service_tokens[token] = employee_id
        return EmployeeServiceTokenRead(employee_id=employee_id, token=token)

    def _authenticate_employee(self, token: str) -> DigitalEmployeeRead:
        employee_id = self.employee_service_tokens.get(token)
        employee = self.employees.get(employee_id or "")
        if not employee:
            raise ValueError("员工服务令牌无效")
        return employee

    def create_goal_run(self, payload: GoalRunCreate) -> GoalRunRead:
        owner = self.employees.get(payload.owner) or next(
            (employee for employee in self.employees.values() if employee.name == payload.owner),
            None,
        ) or next(iter(self.employees.values()), None)
        if not owner:
            raise ValueError("目标负责人必须是已创建的数字员工")
        policy = dict(payload.policy)
        policy.setdefault("job_template_version_id", owner.job_template_version_id)
        policy.setdefault("risk_level", owner.max_goal_risk_level)
        data = payload.model_dump()
        data["owner"] = owner.id
        data["policy"] = policy
        data["root_responsible"] = owner.name
        goal = GoalRunRead(id=new_id("goal"), status="running", **data)
        self.goal_runs[goal.id] = goal
        self._audit("goal_run_created", {"goal_run_id": goal.id})
        return goal

    def list_goal_runs(self) -> list[GoalRunRead]:
        return list(self.goal_runs.values())

    def get_goal_run(self, goal_run_id: str) -> GoalRunRead | None:
        return self.goal_runs.get(goal_run_id)

    def resume_goal_run(self, goal_run_id: str) -> GoalRunRead | None:
        goal = self.goal_runs.get(goal_run_id)
        if not goal:
            return None
        updated = goal.model_copy(update={"status": "running"})
        self.goal_runs[goal_run_id] = updated
        self._audit("goal_run_resumed", {"goal_run_id": goal_run_id})
        return updated

    def create_work_item(self, payload: WorkItemCreate) -> WorkItemRead:
        if payload.goal_run_id not in self.goal_runs:
            raise ValueError("目标运行不存在")
        if payload.assignee_employee_id not in self.employees:
            raise ValueError("执行员工不存在")
        depth = 0
        if payload.parent_work_item_id:
            parent = self.work_items.get(payload.parent_work_item_id)
            if not parent:
                raise ValueError("父工作项不存在")
            depth = parent.depth + 1
            if depth > 1:
                raise ValueError("最小可行版本只允许一层委派")
        work_item = WorkItemRead(
            id=new_id("work"),
            status="pending",
            depth=depth,
            trace_ref=new_id("trace"),
            **payload.model_dump(),
        )
        self.work_items[work_item.id] = work_item
        if payload.parent_work_item_id:
            edge = ExecutionGraphEdgeRead(
                id=new_id("edge"),
                goal_run_id=payload.goal_run_id,
                parent_work_item_id=payload.parent_work_item_id,
                child_work_item_id=work_item.id,
            )
            self.execution_edges[edge.id] = edge
        self._audit("work_item_created", {"goal_run_id": payload.goal_run_id, "work_item_id": work_item.id})
        return work_item

    def delegate_work_item(self, payload: DelegationRequest) -> WorkItemRead:
        parent = self.work_items.get(payload.from_work_item_id)
        if not parent:
            raise ValueError("来源工作项不存在")
        return self.create_work_item(WorkItemCreate(
            goal_run_id=parent.goal_run_id,
            assignee_employee_id=payload.assignee_employee_id,
            title=payload.title,
            input_payload=payload.input_payload,
            parent_work_item_id=parent.id,
            budget_tokens=parent.budget_tokens,
        ))

    def list_execution_edges(self, goal_run_id: str) -> list[ExecutionGraphEdgeRead]:
        return [edge for edge in self.execution_edges.values() if edge.goal_run_id == goal_run_id]

    def _assert_employee_can_use_tool(self, employee: DigitalEmployeeRead, tool_id: str) -> None:
        template = self.template_versions[employee.job_template_version_id]
        allowed = set(template.tools)
        allowed.update({"tool-knowledge-base", "knowledge_base"})
        if tool_id not in allowed:
            raise ValueError("员工未被授权使用该工具")

    def _assert_budget(self, goal_run_id: str, token_cost: int) -> GoalRunRead:
        goal = self.goal_runs.get(goal_run_id)
        if not goal:
            raise ValueError("目标运行不存在")
        if goal.used_tokens + token_cost > goal.budget_tokens:
            self.goal_runs[goal.id] = goal.model_copy(update={"status": "paused"})
            raise ValueError("目标预算不足，已阻止工具调用")
        return goal

    def _assert_organization_quota(self, token_cost: int) -> None:
        projected = self.organization_quota.used_tokens + token_cost
        warning_at = self.organization_quota.monthly_token_limit * self.organization_quota.warning_threshold_percent / 100
        warning_active = projected >= warning_at
        if warning_active != self.organization_quota.warning_active:
            self.organization_quota = self.organization_quota.model_copy(update={"warning_active": warning_active})
            self._audit("organization_quota_warning", {"used_tokens": projected})
        if projected > self.organization_quota.monthly_token_limit and self.organization_quota.over_limit_action == "block_new_work":
            raise ValueError("组织配额已超限，已阻止新工作分发")

    def _idempotency_key(self, call: ToolGatewayCall, employee_id: str) -> str:
        raw = json.dumps({
            "employee_id": employee_id,
            "goal_run_id": call.goal_run_id,
            "work_item_id": call.work_item_id,
            "tool_id": call.tool_id,
            "payload": call.payload,
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def call_tool_gateway(self, call: ToolGatewayCall) -> ToolGatewayResult:
        employee = self._authenticate_employee(call.employee_service_token)
        work_item = self.work_items.get(call.work_item_id)
        if not work_item or work_item.goal_run_id != call.goal_run_id:
            raise ValueError("工作项不存在或不属于目标运行")
        if work_item.assignee_employee_id != employee.id:
            raise ValueError("员工服务令牌与工作项执行人不匹配")
        self._assert_employee_can_use_tool(employee, call.tool_id)
        goal = self._assert_budget(call.goal_run_id, call.token_cost)
        self._assert_organization_quota(call.token_cost)
        tool = self.tools.get(call.tool_id)
        requires_approval = bool(tool and tool.approval_required)
        if requires_approval:
            approval = self.approvals.get(call.approval_id or "")
            if not approval:
                approval_id = new_id("approval")
                pending = ApprovalRequestRead(
                    id=approval_id,
                    approval_type="tool_call",
                    status="pending",
                    risk_level=tool.risk_level if tool else "medium",
                    goal_run_id=call.goal_run_id,
                    work_item_id=call.work_item_id,
                    tool_id=call.tool_id,
                    assignee=tool.owner if tool and tool.owner else "负责人",
                    context={"payload": call.payload},
                )
                self.approvals[approval_id] = pending
                audit_id = self._audit("tool_call_requires_approval", {"approval_id": approval_id, "tool_id": call.tool_id})
                return ToolGatewayResult(status="requires_approval", tool_id=call.tool_id, approval_id=approval_id, audit_id=audit_id)
            if approval.status != "approved":
                audit_id = self._audit("tool_call_rejected_by_approval", {"approval_id": approval.id, "tool_id": call.tool_id})
                return ToolGatewayResult(status="rejected", tool_id=call.tool_id, approval_id=approval.id, audit_id=audit_id)
        key = self._idempotency_key(call, employee.id)
        previous = self.idempotency_results.get(key)
        if previous:
            return previous.model_copy(update={"duplicate": True})
        tool_result = self._execute_tool_call(tool, call)
        self.goal_runs[goal.id] = goal.model_copy(update={"used_tokens": goal.used_tokens + call.token_cost})
        self.organization_quota = self.organization_quota.model_copy(update={
            "used_tokens": self.organization_quota.used_tokens + call.token_cost,
            "warning_active": self.organization_quota.used_tokens + call.token_cost >= self.organization_quota.monthly_token_limit * self.organization_quota.warning_threshold_percent / 100,
        })
        self.token_ledger.append(TokenLedgerEntryRead(
            id=new_id("ledger"),
            department_id=employee.department_id,
            employee_id=employee.id,
            model_id=self.template_versions[employee.job_template_version_id].model_config_id,
            job_template_version_id=employee.job_template_version_id,
            goal_run_id=call.goal_run_id,
            work_item_id=call.work_item_id,
            usage="tool_call",
            total_tokens=call.token_cost,
            trace_ref=work_item.trace_ref,
        ))
        audit_id = self._audit("tool_call_executed", {"goal_run_id": call.goal_run_id, "work_item_id": call.work_item_id, "tool_id": call.tool_id})
        result = ToolGatewayResult(
            status="executed",
            tool_id=call.tool_id,
            idempotency_key=key,
            result=tool_result,
            audit_id=audit_id,
        )
        self.idempotency_results[key] = result
        return result

    def _execute_tool_call(self, tool: ToolRead | None, call: ToolGatewayCall) -> dict[str, Any]:
        if call.tool_id in {"knowledge_base", "tool-knowledge-base"}:
            return {"accepted": True, "message": "知识库工具调用请使用 /gateway/knowledge/search 执行。"}
        if not tool:
            raise ValueError("工具不存在")
        if tool.access_shape not in {"http_api", "platform_adapter"}:
            raise ValueError("当前工具接入形态尚未接入执行适配器")
        if not tool.endpoint_url:
            raise ValueError("工具缺少接口地址")
        headers: dict[str, str] = {}
        if tool.credential_id:
            credential = self.credentials.get(tool.credential_id)
            secret = self.secret_values.get(credential.secret_ref) if credential else None
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
        try:
            response = httpx.request(
                tool.method or "POST",
                tool.endpoint_url,
                json=call.payload,
                headers=headers,
                timeout=15,
                trust_env=False,
            )
            response.raise_for_status()
            if response.content:
                body = response.json()
            else:
                body = {"accepted": True}
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError(f"工具调用失败：{exc}") from exc
        return body if isinstance(body, dict) else {"result": body}

    def list_approvals(
        self,
        status: str | None = None,
        approval_type: str | None = None,
        risk_level: str | None = None,
        goal_run_id: str | None = None,
        assignee: str | None = None,
    ) -> list[ApprovalRequestRead]:
        approvals = list(self.approvals.values())
        if status:
            approvals = [approval for approval in approvals if approval.status == status]
        if approval_type:
            approvals = [approval for approval in approvals if approval.approval_type == approval_type]
        if risk_level:
            approvals = [approval for approval in approvals if approval.risk_level == risk_level]
        if goal_run_id:
            approvals = [approval for approval in approvals if approval.goal_run_id == goal_run_id]
        if assignee:
            approvals = [approval for approval in approvals if approval.assignee == assignee]
        return approvals

    def decide_approval(self, approval_id: str, status: str, payload: ApprovalDecision) -> ApprovalRequestRead | None:
        approval = self.approvals.get(approval_id)
        if not approval:
            return None
        updated = approval.model_copy(update={"status": status, "decision_by": payload.decision_by, "decision_reason": payload.reason})
        self.approvals[approval_id] = updated
        self._audit("approval_decided", {"approval_id": approval_id, "status": status})
        return updated

    def retrieve_knowledge(self, payload: KnowledgeRetrievalRequest) -> KnowledgeRetrievalResult:
        employee = self._authenticate_employee(payload.employee_service_token)
        template = self.template_versions[employee.job_template_version_id]
        if payload.knowledge_source_id not in template.knowledge_sources and payload.knowledge_source_id not in self.knowledge_sources:
            raise ValueError("员工未被授权访问该知识源")
        if payload.goal_run_id not in self.goal_runs or payload.work_item_id not in self.work_items:
            raise ValueError("目标运行或工作项不存在")
        source = self.knowledge_sources.get(payload.knowledge_source_id)
        if not source:
            raise ValueError("知识源不存在")
        connection = self.knowledge_connections.get(source.connection_id)
        if not connection:
            raise ValueError("知识连接不存在")
        hits = self._retrieve_ragflow_chunks(connection, [source], payload.query, payload.top_k)
        audit_id = self._audit("knowledge_retrieved", {
            "goal_run_id": payload.goal_run_id,
            "work_item_id": payload.work_item_id,
            "knowledge_source_id": payload.knowledge_source_id,
            "hit_count": len(hits),
        })
        return KnowledgeRetrievalResult(
            answer="\n\n".join(hit.content for hit in hits) if hits else "RAGFlow 未返回相关片段。",
            citations=[{
                "source_id": payload.knowledge_source_id,
                "title": hit.document_name,
                "chunk_id": hit.chunk_id,
                "score": hit.score,
                "citation": hit.citation,
            } for hit in hits],
            audit_id=audit_id,
        )

    def preview_knowledge_retrieval(self, payload: KnowledgePreviewRequest) -> KnowledgePreviewResult:
        selected_sources = [self.knowledge_sources[source_id] for source_id in payload.source_ids if source_id in self.knowledge_sources]
        missing_source_ids = [source_id for source_id in payload.source_ids if source_id not in self.knowledge_sources]
        warnings = [f"{source_id} 未登记，已跳过。" for source_id in missing_source_ids]
        active_sources = []
        for source in selected_sources:
            if source.status != "active":
                warnings.append(f"{source.display_name} 当前未启用，已跳过。")
                continue
            active_sources.append(source)
        if not active_sources:
            audit_id = self._audit("knowledge_preview", {"source_ids": payload.source_ids, "query": payload.query, "hit_count": 0})
            return KnowledgePreviewResult(audit_id=audit_id, warnings=warnings, hits=[])

        hits: list[KnowledgePreviewHit] = []
        sources_by_connection: dict[str, list[KnowledgeSourceRead]] = {}
        for source in active_sources:
            sources_by_connection.setdefault(source.connection_id, []).append(source)
        for connection_id, connection_sources in sources_by_connection.items():
            connection = self.knowledge_connections.get(connection_id)
            if not connection:
                warnings.extend([f"{source.display_name} 的知识连接不存在，已跳过。" for source in connection_sources])
                continue
            hits.extend(self._retrieve_ragflow_chunks(connection, connection_sources, payload.query, payload.top_k))

        audit_id = self._audit("knowledge_preview", {
            "source_ids": payload.source_ids,
            "query": payload.query,
            "hit_count": len(hits),
        })
        return KnowledgePreviewResult(audit_id=audit_id, warnings=warnings, hits=hits[:payload.top_k])

    def _retrieve_ragflow_chunks(
        self,
        connection: KnowledgeConnectionRead,
        sources: list[KnowledgeSourceRead],
        query: str,
        top_k: int,
    ) -> list[KnowledgePreviewHit]:
        credential = self.credentials.get(connection.credential_id)
        api_key = self.secret_values.get(credential.secret_ref) if credential else None
        if not api_key:
            raise ValueError("RAGFlow 连接缺少可用凭据")
        dataset_ids = [source.external_id for source in sources]
        source_by_external_id = {source.external_id: source for source in sources}
        try:
            response = httpx.post(
                f"{connection.base_url.rstrip('/')}/api/v1/retrieval",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "question": query,
                    "dataset_ids": dataset_ids,
                    "page": 1,
                    "page_size": top_k,
                    "top_k": top_k,
                    "highlight": False,
                },
                timeout=15,
                trust_env=False,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ValueError(f"RAGFlow 检索失败：{exc}") from exc
        if body.get("code") not in (0, "0", None):
            raise ValueError(f"RAGFlow 检索失败：{body.get('message') or body.get('error') or body.get('code')}")
        data = body.get("data") or {}
        doc_names = {
            str(item.get("doc_id")): str(item.get("doc_name") or item.get("doc_id"))
            for item in data.get("doc_aggs") or []
        }
        hits: list[KnowledgePreviewHit] = []
        for index, chunk in enumerate(data.get("chunks") or []):
            dataset_id = chunk.get("dataset_id") or chunk.get("kb_id") or ""
            if isinstance(dataset_id, list):
                dataset_id = dataset_id[0] if dataset_id else ""
            source = source_by_external_id.get(str(dataset_id))
            document_id = str(chunk.get("document_id") or "")
            document_name = doc_names.get(document_id) or str(chunk.get("document_keyword") or document_id or "RAGFlow 文档")
            chunk_id = str(chunk.get("id") or f"chunk-{index + 1}")
            hits.append(KnowledgePreviewHit(
                id=f"preview-{chunk_id}",
                content=str(chunk.get("content") or chunk.get("content_ltks") or ""),
                source_name=source.display_name if source else str(dataset_id or "RAGFlow"),
                document_name=document_name,
                chunk_id=chunk_id,
                score=float(chunk.get("similarity") or 0),
                citation=f"{document_name} / {chunk_id}",
            ))
        return hits

    def create_artifact(self, payload: ArtifactCreate) -> ArtifactRead:
        if payload.goal_run_id not in self.goal_runs or payload.work_item_id not in self.work_items:
            raise ValueError("目标运行或工作项不存在")
        artifact = ArtifactRead(id=new_id("artifact"), status="draft", version=1, **payload.model_dump())
        self.artifacts[artifact.id] = artifact
        self._audit("artifact_created", {"artifact_id": artifact.id, "goal_run_id": payload.goal_run_id})
        return artifact

    def accept_artifact(self, artifact_id: str, payload: ArtifactAcceptanceCreate) -> ArtifactAcceptanceRead | None:
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return None
        status = "accepted" if payload.accepted else "rejected"
        self.artifacts[artifact_id] = artifact.model_copy(update={"status": status})
        acceptance = ArtifactAcceptanceRead(
            id=new_id("acceptance"),
            artifact_id=artifact_id,
            status=status,
            reviewer=payload.reviewer,
            business_result=payload.business_result,
            reason=payload.reason,
        )
        self.artifact_acceptances[acceptance.id] = acceptance
        self._audit("artifact_acceptance_decided", {"artifact_id": artifact_id, "status": status})
        return acceptance

    def get_organization_quota(self) -> OrganizationQuotaPolicyRead:
        return self.organization_quota

    def update_organization_quota(self, payload: OrganizationQuotaPolicyCreate) -> OrganizationQuotaPolicyRead:
        self.organization_quota = OrganizationQuotaPolicyRead(
            id=self.organization_quota.id,
            used_tokens=self.organization_quota.used_tokens,
            warning_active=self.organization_quota.warning_active,
            **payload.model_dump(),
        )
        self._audit("organization_quota_updated", {"quota_id": self.organization_quota.id})
        return self.organization_quota

    def _default_goal_budget_policy(self, version: JobTemplateVersionRead) -> GoalBudgetPolicyRead:
        return GoalBudgetPolicyRead(
            id=f"gbp-{version.id}",
            job_template_version_id=version.id,
            default_budget_tokens=version.default_goal_budget_tokens,
            warning_threshold_percent=80,
            overage_action="block_goal_model_calls",
            approvers=["直属上级", "平台管理员"],
        )

    def list_goal_budget_policies(self) -> list[GoalBudgetPolicyRead]:
        for version in self.template_versions.values():
            self.goal_budget_policies.setdefault(version.id, self._default_goal_budget_policy(version))
        return list(self.goal_budget_policies.values())

    def create_goal_budget_policy(self, payload: GoalBudgetPolicyCreate) -> GoalBudgetPolicyRead:
        if payload.job_template_version_id not in self.template_versions:
            raise ValueError("岗位模板版本不存在")
        policy = GoalBudgetPolicyRead(id=new_id("gbp"), **payload.model_dump())
        self.goal_budget_policies[payload.job_template_version_id] = policy
        self._audit("goal_budget_policy_created", {"policy_id": policy.id, "job_template_version_id": payload.job_template_version_id})
        return policy

    def patch_goal_budget_policy(self, policy_id: str, payload: GoalBudgetPolicyPatch) -> GoalBudgetPolicyRead | None:
        target_key = next(
            (version_id for version_id, policy in self.goal_budget_policies.items() if policy.id == policy_id),
            None,
        )
        if not target_key:
            for version in self.template_versions.values():
                policy = self._default_goal_budget_policy(version)
                if policy.id == policy_id:
                    self.goal_budget_policies[version.id] = policy
                    target_key = version.id
                    break
        if not target_key:
            return None
        data = self.goal_budget_policies[target_key].model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        updated = GoalBudgetPolicyRead(**data)
        self.goal_budget_policies[target_key] = updated
        version = self.template_versions.get(updated.job_template_version_id)
        if version:
            self.template_versions[version.id] = version.model_copy(update={"default_goal_budget_tokens": updated.default_budget_tokens})
        self._audit("goal_budget_policy_updated", {"policy_id": policy_id})
        return updated

    def list_token_ledger(self) -> list[TokenLedgerEntryRead]:
        return self.token_ledger

    def usage_analytics(self) -> UsageAnalyticsRead:
        analytics = UsageAnalyticsRead(total_tokens=sum(entry.total_tokens for entry in self.token_ledger))
        for entry in self.token_ledger:
            if entry.department_id:
                analytics.by_department[entry.department_id] = analytics.by_department.get(entry.department_id, 0) + entry.total_tokens
            analytics.by_employee[entry.employee_id] = analytics.by_employee.get(entry.employee_id, 0) + entry.total_tokens
            if entry.model_id:
                analytics.by_model[entry.model_id] = analytics.by_model.get(entry.model_id, 0) + entry.total_tokens
            if entry.job_template_version_id:
                analytics.by_job_template[entry.job_template_version_id] = analytics.by_job_template.get(entry.job_template_version_id, 0) + entry.total_tokens
            analytics.by_goal_run[entry.goal_run_id] = analytics.by_goal_run.get(entry.goal_run_id, 0) + entry.total_tokens
        return analytics

    def create_metric_definition(self, payload: MetricDefinitionCreate) -> MetricDefinitionRead:
        metric = MetricDefinitionRead(id=new_id("metric"), **payload.model_dump())
        self.metric_definitions[metric.id] = metric
        self._audit("metric_definition_created", {"metric_definition_id": metric.id})
        return metric

    def bind_metrics_to_template(self, version_id: str, payload: JobTemplateMetricBindingCreate) -> JobTemplateMetricBindingRead:
        if version_id not in self.template_versions:
            raise ValueError("岗位模板版本不存在")
        missing = [metric_id for metric_id in payload.metric_definition_ids if metric_id not in self.metric_definitions]
        if missing:
            raise ValueError("业务结果指标不存在")
        binding = JobTemplateMetricBindingRead(job_template_version_id=version_id, metric_definition_ids=payload.metric_definition_ids)
        self.template_metric_bindings[version_id] = binding
        version = self.template_versions[version_id]
        self.template_versions[version_id] = version.model_copy(update={"metric_bindings": [metric.model_dump() for metric in self.metric_definitions.values() if metric.id in payload.metric_definition_ids]})
        return binding

    def record_metric_measurement(self, payload: MetricMeasurementCreate) -> MetricMeasurementRead:
        if payload.metric_definition_id not in self.metric_definitions:
            raise ValueError("业务结果指标不存在")
        measurement = MetricMeasurementRead(id=new_id("measurement"), **payload.model_dump())
        self.metric_measurements[measurement.id] = measurement
        self._audit("metric_measurement_recorded", {"metric_definition_id": payload.metric_definition_id, "measurement_id": measurement.id})
        return measurement

    def list_template_outcome_reports(self) -> list[TemplateOutcomeReportRead]:
        reports: list[TemplateOutcomeReportRead] = []
        for template in self.template_versions.values():
            template_goals = [
                goal for goal in self.goal_runs.values()
                if self._goal_template_id(goal) == template.id
            ]
            goal_ids = {goal.id for goal in template_goals}
            template_artifacts = [
                artifact for artifact in self.artifacts.values()
                if artifact.goal_run_id in goal_ids
            ]
            artifact_ids = {artifact.id for artifact in template_artifacts}
            acceptances = [
                acceptance for acceptance in self.artifact_acceptances.values()
                if acceptance.artifact_id in artifact_ids
            ]
            completed_count = sum(1 for goal in template_goals if goal.status == "completed")
            accepted_count = sum(1 for acceptance in acceptances if acceptance.status == "accepted")
            rejected_count = sum(1 for acceptance in acceptances if acceptance.status == "rejected")
            token_cost = sum(
                entry.total_tokens for entry in self.token_ledger
                if entry.job_template_version_id == template.id
            )
            reports.append(TemplateOutcomeReportRead(
                id=f"report-{template.id}",
                template_id=template.id,
                template_role=template.role,
                version=template.version,
                goal_runs=len(template_goals),
                completion_rate=self._percent(completed_count, len(template_goals)),
                first_pass_acceptance_rate=self._percent(accepted_count, len(acceptances)),
                rework_rate=self._percent(rejected_count, len(acceptances)),
                average_cycle_hours=0,
                token_cost=token_cost,
                business_metrics=self._template_business_metrics(template),
                evaluation_status=self._report_evaluation_status(template.evaluation.status if template.evaluation else None),
            ))
        return reports

    def _goal_template_id(self, goal: GoalRunRead) -> str:
        policy = goal.policy or {}
        return str(policy.get("job_template_version_id") or policy.get("template_id") or "")

    def _percent(self, numerator: int, denominator: int) -> int:
        if denominator <= 0:
            return 0
        return round(numerator / denominator * 100)

    def _report_evaluation_status(self, status: EvaluationStatus | None) -> Literal["not_run", "passed", "failed", "warning"]:
        if status == "passed":
            return "passed"
        if status == "failed":
            return "failed"
        if status == "warning":
            return "warning"
        return "not_run"

    def _template_business_metrics(self, template: JobTemplateVersionRead) -> list[BusinessOutcomeMetricBindingRead]:
        metrics: list[BusinessOutcomeMetricBindingRead] = []
        for index, raw_metric in enumerate(template.metric_bindings):
            metric_id = str(raw_metric.get("id") or raw_metric.get("metric_definition_id") or f"{template.id}-metric-{index}")
            measurement = self._latest_metric_measurement(metric_id)
            metrics.append(BusinessOutcomeMetricBindingRead(
                id=metric_id,
                name=str(raw_metric.get("name") or "业务结果指标"),
                source=self._metric_source(raw_metric.get("source")),
                unit=str(raw_metric.get("unit") or ""),
                target=str(raw_metric.get("target_value") or raw_metric.get("target") or "-"),
                actual=measurement.value if measurement else str(raw_metric.get("actual") or "-"),
                collection_method=str(raw_metric.get("collection_method") or raw_metric.get("collectionMethod") or "人工录入"),
            ))
        return metrics

    def _latest_metric_measurement(self, metric_id: str) -> MetricMeasurementRead | None:
        matched = [measurement for measurement in self.metric_measurements.values() if measurement.metric_definition_id == metric_id]
        return matched[-1] if matched else None

    def _metric_source(self, value: object) -> Literal["platform_native", "tool_business_system", "manual_or_imported"]:
        if value in {"platform_native", "tool_business_system", "manual_or_imported"}:
            return value  # type: ignore[return-value]
        return "manual_or_imported"

    def list_audit_events(self) -> list[AuditEventRead]:
        return self.audit_events

    def create_audit_event(self, payload: AuditEventCreate) -> AuditEventRead:
        event = AuditEventRead(id=new_id("audit"), **payload.model_dump())
        self.audit_events.append(event)
        return event

    def add_audit_disposition(self, audit_event_id: str, payload: AuditDispositionCreate) -> AuditEventRead | None:
        for index, event in enumerate(self.audit_events):
            if event.id != audit_event_id:
                continue
            disposition = {
                "id": new_id("audit-disp"),
                "status": payload.status,
                "note": payload.note,
                "reviewer": payload.reviewer,
            }
            updated = event.model_copy(update={"dispositions": [*event.dispositions, disposition]})
            self.audit_events[index] = updated
            return updated
        return None

    def list_audit_rules(self) -> list[AuditRuleRead]:
        return list(self.audit_rules.values())

    def create_audit_rule(self, payload: AuditRuleCreate) -> AuditRuleRead:
        rule = AuditRuleRead(id=new_id("audit-rule"), enabled=True, **payload.model_dump())
        self.audit_rules[rule.id] = rule
        self._audit("audit_rule_created", {"audit_rule_id": rule.id})
        return rule

    def patch_audit_rule(self, rule_id: str, payload: AuditRulePatch) -> AuditRuleRead | None:
        rule = self.audit_rules.get(rule_id)
        if not rule:
            return None
        data = rule.model_dump()
        data.update(payload.model_dump(exclude_unset=True))
        updated = AuditRuleRead(**data)
        self.audit_rules[rule_id] = updated
        self._audit("audit_rule_updated", {"audit_rule_id": rule_id})
        return updated

    def evaluate_audit_rule(self, rule_id: str, audit_event_id: str) -> AuditRuleEvaluationRead:
        rule = self.audit_rules.get(rule_id)
        if not rule:
            raise ValueError("审计规则不存在")
        event = next((item for item in self.audit_events if item.id == audit_event_id), None)
        if not event:
            raise ValueError("审计事件不存在")
        matched = rule.enabled and event.event_type == rule.event_type
        review_task_id = None
        if matched and rule.requires_review:
            task = ReviewTaskRead(
                id=new_id("review"),
                audit_event_id=audit_event_id,
                audit_rule_id=rule_id,
                assignee=rule.notification_targets[0] if rule.notification_targets else "审计负责人",
            )
            self.review_tasks[task.id] = task
            review_task_id = task.id
        evaluation = AuditRuleEvaluationRead(
            id=new_id("audit-eval"),
            audit_event_id=audit_event_id,
            audit_rule_id=rule_id,
            matched=matched,
            notifications=rule.notification_targets if matched else [],
            review_task_id=review_task_id,
        )
        self.audit_rule_evaluations[evaluation.id] = evaluation
        return evaluation

    def list_audit_notifications(self) -> list[AuditNotificationRead]:
        notifications: list[AuditNotificationRead] = []
        for evaluation in self.audit_rule_evaluations.values():
            if not evaluation.matched:
                continue
            for index, receiver in enumerate(evaluation.notifications):
                notifications.append(AuditNotificationRead(
                    id=f"notification-{evaluation.id}-{index}",
                    event_id=evaluation.audit_event_id,
                    rule_id=evaluation.audit_rule_id,
                    channel="in_app",
                    receiver=receiver,
                    status="pending",
                    created_at="当前周期",
                ))
        return notifications

    def list_alerts(self) -> list[AlertRead]:
        alerts: list[AlertRead] = []
        for goal in self.goal_runs.values():
            if goal.status == "paused":
                alerts.append(AlertRead(
                    id=f"budget-{goal.id}",
                    type="budget",
                    message=f"{goal.title} 已触发预算阻断",
                    time="当前周期",
                    resolved=False,
                ))
        for task in self.review_tasks.values():
            event = next((item for item in self.audit_events if item.id == task.audit_event_id), None)
            alerts.append(AlertRead(
                id=f"audit-{task.id}",
                type="redline",
                message=f"{event.event_type if event else '审计事件'} 需要复核",
                time="当前周期",
                resolved=task.status == "closed",
            ))
        return alerts

    def list_job_template_versions(self) -> list[JobTemplateVersionRead]:
        return list(self.template_versions.values())

    def get_job_template_version(self, version_id: str) -> JobTemplateVersionRead | None:
        return self.template_versions.get(version_id)

    def create_job_template_version(self, payload: JobTemplateVersionCreate) -> JobTemplateVersionRead:
        if payload.department_id not in self.departments:
            raise ValueError("部门不存在")
        version_id = new_id("jtv")
        evaluation = JobTemplateEvaluationRead(job_template_version_id=version_id, status="not_evaluated")
        version = JobTemplateVersionRead(id=version_id, status="draft", evaluation=evaluation, **payload.model_dump())
        self.template_versions[version_id] = version
        self.goal_budget_policies[version_id] = self._default_goal_budget_policy(version)
        self._audit("job_template_version_created", {"job_template_version_id": version_id})
        return version

    def patch_job_template_version(self, version_id: str, payload: JobTemplateVersionPatch) -> JobTemplateVersionRead | None:
        version = self.template_versions.get(version_id)
        if not version:
            return None
        patch = payload.model_dump(exclude_unset=True)
        if patch.get("department_id") and patch["department_id"] not in self.departments:
            raise ValueError("部门不存在")
        data = version.model_dump()
        data.update(patch)
        updated = JobTemplateVersionRead(**data)
        self.template_versions[version_id] = updated
        if "default_goal_budget_tokens" in patch:
            policy = self.goal_budget_policies.get(version_id) or self._default_goal_budget_policy(updated)
            self.goal_budget_policies[version_id] = policy.model_copy(update={"default_budget_tokens": updated.default_goal_budget_tokens})
        return updated

    def set_job_template_version_status(self, version_id: str, status: str) -> JobTemplateVersionRead | None:
        version = self.template_versions.get(version_id)
        if not version:
            return None
        updated = version.model_copy(update={"status": status})
        self.template_versions[version_id] = updated
        self._audit("job_template_version_status_changed", {"job_template_version_id": version_id, "status": status})
        return updated

    def delete_job_template_version(self, version_id: str) -> bool:
        version = self.template_versions.get(version_id)
        if not version:
            return False
        # 检查是否有数字员工引用了此模板
        for emp in self.employees.values():
            if emp.job_template_version_id == version_id:
                raise ValueError(f"数字员工 {emp.role}（{emp.id}）正在使用此模板，请先删除该员工")
        del self.template_versions[version_id]
        self.goal_budget_policies.pop(version_id, None)
        self._audit("job_template_version_deleted", {"job_template_version_id": version_id})
        return True

    def get_template_evaluation(self, version_id: str) -> JobTemplateEvaluationRead | None:
        version = self.template_versions.get(version_id)
        return version.evaluation if version else None

    def update_template_evaluation(self, version_id: str, payload: JobTemplateEvaluationUpdate) -> JobTemplateEvaluationRead | None:
        version = self.template_versions.get(version_id)
        if not version:
            return None
        passed_case_count = sum(1 for case in payload.cases if case.status == "passed")
        evaluation = JobTemplateEvaluationRead(
            job_template_version_id=version_id,
            status=payload.status,
            score=payload.score,
            case_count=len(payload.cases),
            passed_case_count=passed_case_count,
            evaluator=payload.evaluator,
            summary=payload.summary,
            cases=payload.cases,
        )
        self.template_versions[version_id] = version.model_copy(update={"evaluation": evaluation})
        return evaluation

    def _render_evaluation_soul(self, version: JobTemplateVersionRead) -> str:
        """将模板配置渲染为 Hermes Profile 的 SOUL.md 内容。"""
        parts: list[str] = []
        parts.append(f"# {version.role} ({version.grade})\n")
        if version.description:
            parts.append(f"## 岗位说明\n{version.description}\n")
        if version.system_prompt:
            parts.append(f"## 系统提示词\n{version.system_prompt}\n")
        if version.skills:
            parts.append("## 可用技能\n")
            for skill_id in version.skills:
                skill = self.skill_packages.get(skill_id)
                label = f"{skill.name} v{skill.version}" if skill else skill_id
                parts.append(f"- {label}")
            parts.append("")
        if version.tools:
            parts.append("## 工具白名单\n")
            for tool_id in version.tools:
                tool = self.tools.get(tool_id)
                label = tool.name if tool else tool_id
                parts.append(f"- {label}")
            parts.append("")
        if version.knowledge_sources:
            parts.append("## 知识源\n")
            for ks_id in version.knowledge_sources:
                ks = self.knowledge_sources.get(ks_id)
                label = ks.display_name if ks else ks_id
                parts.append(f"- {label}")
            parts.append("")
        if version.red_lines:
            parts.append("## 红线（绝对禁止行为）\n")
            for rl in version.red_lines:
                parts.append(f"- {rl}")
            parts.append("")
        return "\n".join(parts)

    def run_template_evaluation(self, version_id: str, task_description: str) -> dict:
        """全流程模板评测：创建临时 Profile → 启动 Gateway → 执行 Run → 清理资源。

        步骤：
        1. 获取并发锁，防止同一模板同时评测
        2. 分配端口，创建临时 Hermes Profile
        3. 写入 SOUL.md（system_prompt + skills + tools + knowledge + red_lines）
        4. 设置模型，启动 Gateway，等待就绪
        5. 调用 Hermes 执行评测任务
        6. finally 块保证 Gateway、Profile、端口全部清理
        """
        version = self.template_versions.get(version_id)
        if not version:
            raise ValueError("岗位模板版本不存在")

        lock = self._eval_lock_for(version_id)
        if not lock.acquire(blocking=False):
            logger.warning("Template evaluation rejected because another run is active version_id=%s", version_id)
            raise ConflictError("该模板版本正在评测中，请等待当前评测完成后再试。")

        port: int | None = None
        profile_name: str | None = None
        gw_result: dict = {}
        eval_api_key = settings.hermes_api_key or f"eval-{secrets.token_urlsafe(32)}"
        logger.info(
            "Template evaluation requested version_id=%s role=%s task_chars=%s",
            version_id,
            version.role,
            len(task_description),
        )
        try:
            # 1. 分配端口
            port = self.port_pool.allocate()
            profile_name = f"eval-{version_id[:30]}-{int(time.time())}"
            logger.info(
                "Template evaluation profile planning version_id=%s profile=%s port=%s",
                version_id,
                profile_name,
                port,
            )

            self._audit("template_evaluation_profile_creating", {
                "template_version_id": version_id,
                "profile_name": profile_name,
                "port": port,
            })

            # 2. 创建临时 Profile
            model_config = self.model_configurations.get(version.model_config_id)
            provider = model_config.provider if model_config else settings.default_llm_provider
            model = model_config.model_name if model_config else settings.default_llm_model
            logger.info(
                "Creating Hermes evaluation profile version_id=%s profile=%s provider=%s model=%s model_config_id=%s",
                version_id,
                profile_name,
                provider,
                model,
                version.model_config_id,
            )
            self._dashboard.create_profile(
                profile_name,
                model_provider=provider,
                model_name=model,
                no_skills=True,
            )
            logger.info("Hermes evaluation profile created version_id=%s profile=%s", version_id, profile_name)

            # 3. 写入 SOUL.md
            soul_content = self._render_evaluation_soul(version)
            logger.info(
                "Writing Hermes evaluation SOUL version_id=%s profile=%s soul_chars=%s",
                version_id,
                profile_name,
                len(soul_content),
            )
            self._dashboard.write_soul(profile_name, soul_content)
            logger.info("Hermes evaluation SOUL written version_id=%s profile=%s", version_id, profile_name)

            # 4. 写入 Profile 运行时密钥，Hermes Gateway 启动时会加载该 .env
            profile_env = self._evaluation_profile_env(model_config)
            logger.info(
                "Writing Hermes evaluation profile env version_id=%s profile=%s env_keys=%s",
                version_id,
                profile_name,
                sorted(profile_env.keys()),
            )
            self._dashboard.write_profile_env(profile_name, profile_env)

            # 5. 配置 API Server 端口（新 Profile 默认端口会与主 Gateway 冲突）
            logger.info(
                "Configuring Hermes evaluation api_server version_id=%s profile=%s port=%s api_key_configured=%s",
                version_id,
                profile_name,
                port,
                bool(eval_api_key),
            )
            self._dashboard.write_gateway_port(profile_name, port, api_key=eval_api_key)

            # 6. 启动 Gateway
            gw_result = self._dashboard.start_gateway(profile_name)
            gw_log = gw_result.get("log", "未知")
            logger.info(
                "Hermes evaluation gateway started version_id=%s profile=%s port=%s pid=%s log=%s",
                version_id,
                profile_name,
                port,
                gw_result.get("pid"),
                gw_log,
            )

            # 7. 等待 Gateway 就绪
            ready = self._dashboard.wait_gateway_ready(
                port,
                timeout_seconds=settings.eval_gateway_start_timeout_seconds,
            )
            if not ready:
                logger.warning(
                    "Hermes evaluation gateway readiness timeout version_id=%s profile=%s port=%s log=%s",
                    version_id,
                    profile_name,
                    port,
                    gw_log,
                )
                raise RuntimeError(
                    f"Gateway 启动超时（{settings.eval_gateway_start_timeout_seconds}s），"
                    f"端口 {port}，Profile: {profile_name}\n"
                    f"请查看 Gateway 日志: tail -100 {gw_log}"
                )

            self._audit("template_evaluation_gateway_ready", {
                "template_version_id": version_id,
                "profile_name": profile_name,
                "port": port,
            })

            # 8. 执行评测任务
            logger.info(
                "Submitting Hermes evaluation run version_id=%s profile=%s port=%s timeout_seconds=%s",
                version_id,
                profile_name,
                port,
                settings.eval_run_timeout_seconds,
            )
            hermes = HermesClient(
                f"http://127.0.0.1:{port}",
                eval_api_key,
                timeout_seconds=settings.eval_run_timeout_seconds,
            )
            result = hermes.create_and_wait_run(
                task_description,
                metadata={"purpose": "template_evaluation", "template_version_id": version_id},
                max_wait_seconds=settings.eval_run_timeout_seconds,
            )
            run_id = result.get("run_id") or result.get("id") or "unknown"
            output = result.get("output") or json.dumps(result, ensure_ascii=False)
            run_status = result.get("status", "unknown")
            is_completed = run_status == "completed"
            if is_completed:
                logger.info(
                    "Hermes evaluation run completed version_id=%s profile=%s run_id=%s output_chars=%s",
                    version_id,
                    profile_name,
                    run_id,
                    len(output),
                )
            else:
                logger.warning(
                    "Hermes evaluation run ended non-completed version_id=%s profile=%s run_id=%s status=%s output_chars=%s output_preview=%s",
                    version_id,
                    profile_name,
                    run_id,
                    run_status,
                    len(output),
                    _log_preview(output),
                )

            self._audit("template_evaluation_run_completed", {
                "template_version_id": version_id,
                "run_id": run_id,
                "hermes_status": run_status,
                "profile_name": profile_name,
                "port": port,
            })

            return {
                "run_id": run_id,
                "task_description": task_description,
                "hermes_output": output,
                "status": "completed" if is_completed else "error",
                "error_message": None if is_completed else f"Hermes 运行状态: {run_status}\n{output}",
            }

        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            error_msg = str(exc)
            # 提供更友好的错误提示
            if "Connection refused" in error_msg or "ConnectionError" in error_msg:
                error_msg = (
                    f"无法连接 Hermes Dashboard（{settings.hermes_dashboard_url}），"
                    f"请确保已启动 Dashboard：./platform-dev.sh start\n"
                    f"原始错误: {error_msg}"
                )
            logger.exception(
                "Template evaluation failed version_id=%s profile=%s port=%s error=%s",
                version_id,
                profile_name,
                port,
                _log_preview(error_msg),
            )
            self._audit("template_evaluation_run_failed", {
                "template_version_id": version_id,
                "profile_name": profile_name,
                "port": port,
                "error": error_msg,
            })
            return {
                "run_id": "",
                "task_description": task_description,
                "hermes_output": "",
                "status": "error",
                "error_message": error_msg,
            }
        finally:
            # 清理顺序：Gateway → Profile → Port
            if profile_name:
                try:
                    stopped_spawned = self._dashboard.stop_spawned_gateway(profile_name, gw_result.get("pid"))
                    logger.info(
                        "Hermes evaluation spawned gateway cleanup profile=%s pid=%s stopped=%s",
                        profile_name,
                        gw_result.get("pid"),
                        stopped_spawned,
                    )
                except Exception as exc:
                    logger.warning("Hermes evaluation spawned gateway cleanup failed profile=%s error=%s", profile_name, exc)
                try:
                    stop_result = self._dashboard.stop_gateway(profile_name)
                    logger.info("Hermes evaluation dashboard gateway cleanup profile=%s result=%s", profile_name, stop_result)
                except Exception as exc:
                    logger.info("Hermes evaluation dashboard gateway cleanup skipped/failed profile=%s error=%s", profile_name, exc)
                try:
                    delete_result = self._dashboard.delete_profile(profile_name)
                    logger.info("Hermes evaluation profile deleted profile=%s result=%s", profile_name, delete_result)
                except Exception as exc:
                    logger.warning("Hermes evaluation profile delete failed profile=%s error=%s", profile_name, exc)
            if port is not None:
                self.port_pool.release(port)
                logger.info("Hermes evaluation port released version_id=%s profile=%s port=%s", version_id, profile_name, port)
            lock.release()
            logger.info("Template evaluation lock released version_id=%s profile=%s", version_id, profile_name)

    def list_digital_employees(self) -> list[DigitalEmployeeRead]:
        return list(self.employees.values())

    def get_digital_employee(self, employee_id: str) -> DigitalEmployeeRead | None:
        return self.employees.get(employee_id)

    def create_digital_employee(self, payload: DigitalEmployeeCreate) -> DigitalEmployeeRead:
        template = self.template_versions.get(payload.job_template_version_id)
        if not template:
            raise ValueError("岗位模板版本不存在")
        if template.status != "published":
            raise ValueError("只能从已发布岗位模板版本创建数字员工")
        if template.evaluation.status != "passed":
            raise ValueError("岗位模板版本必须先通过模板评测")
        if payload.department_id not in self.departments:
            raise ValueError("部门不存在")

        employee_id = new_id("emp")
        employee = DigitalEmployeeRead(
            id=employee_id,
            role=template.role,
            grade=template.grade,
            lifecycle_state="provisioning",
            runtime_state="not_started",
            availability_state="unavailable",
            max_goal_risk_level=template.max_goal_risk_level,
            rollout=RolloutState(
                job_id=new_id("rollout"),
                current_step="profile_render",
                status="running",
                summary="已创建员工记录，后台 Employee Rollout Job 正在渲染 Profile。",
            ),
            **payload.model_dump(),
        )
        self.employees[employee_id] = employee
        self.employee_service_tokens[f"dev-token-{employee_id}"] = employee_id
        self._audit("digital_employee_created", {"employee_id": employee_id, "job_template_version_id": payload.job_template_version_id})
        return employee

    def patch_employee_organization(self, employee_id: str, payload: EmployeeOrganizationPatch) -> DigitalEmployeeRead | None:
        employee = self.employees.get(employee_id)
        if not employee:
            return None
        patch = payload.model_dump(exclude_unset=True)
        if patch.get("department_id") and patch["department_id"] not in self.departments:
            raise ValueError("部门不存在")
        data = employee.model_dump()
        data.update(patch)
        updated = DigitalEmployeeRead(**data)
        self.employees[employee_id] = updated
        return updated

    def patch_employee_runtime(self, employee_id: str, payload: EmployeeRuntimePatch) -> DigitalEmployeeRead | None:
        employee = self.employees.get(employee_id)
        if not employee:
            return None
        active_goal_count = payload.active_goal_count if payload.active_goal_count is not None else employee.active_goal_count
        availability = compute_availability(employee.lifecycle_state, payload.runtime_state, active_goal_count)
        updated = employee.model_copy(update={
            "runtime_state": payload.runtime_state,
            "active_goal_count": active_goal_count,
            "availability_state": availability,
        })
        self.employees[employee_id] = updated
        return updated

    def rerun_employee_smoke_test(self, employee_id: str) -> DigitalEmployeeRead | None:
        employee = self.employees.get(employee_id)
        if not employee:
            return None
        try:
            smoke = HermesClient(settings.hermes_base_url, settings.hermes_api_key, timeout_seconds=60).smoke_test()
            run_id = smoke.get("run_id") or smoke.get("id") or "unknown"
            updated = employee.model_copy(update={
                "lifecycle_state": "pending_activation",
                "runtime_state": "stopped",
                "availability_state": "unavailable",
                "rollout": RolloutState(
                    job_id=employee.rollout.job_id,
                    current_step="pending_activation",
                    status="passed",
                    last_smoke_test_status="passed",
                    summary=f"Hermes smoke test 已提交并返回运行编号 {run_id}，等待管理员上岗。",
                ),
            })
            self._audit("digital_employee_smoke_tested", {"employee_id": employee_id, "run_id": run_id})
        except httpx.HTTPError as exc:
            updated = employee.model_copy(update={
                "lifecycle_state": "rollout_failed",
                "runtime_state": "unhealthy",
                "availability_state": "unavailable",
                "rollout": RolloutState(
                    job_id=employee.rollout.job_id,
                    current_step="smoke_test",
                    status="failed",
                    last_smoke_test_status="failed",
                    summary=f"Hermes smoke test 失败：{exc}",
                ),
            })
            self._audit("digital_employee_smoke_test_failed", {"employee_id": employee_id, "reason": str(exc)})
        self.employees[employee_id] = updated
        return updated

    def set_employee_lifecycle(self, employee_id: str, lifecycle_state: LifecycleStatus) -> DigitalEmployeeRead | None:
        employee = self.employees.get(employee_id)
        if not employee:
            return None
        runtime_state = employee.runtime_state
        if lifecycle_state == "active" and runtime_state in ("not_started", "stopped"):
            runtime_state = "healthy"
        if lifecycle_state in ("disabled", "archived"):
            runtime_state = "stopped"
        availability = compute_availability(lifecycle_state, runtime_state, employee.active_goal_count)
        updated = employee.model_copy(update={
            "lifecycle_state": lifecycle_state,
            "runtime_state": runtime_state,
            "availability_state": availability,
        })
        self.employees[employee_id] = updated
        self._audit("digital_employee_lifecycle_changed", {"employee_id": employee_id, "lifecycle_state": lifecycle_state})
        return updated


class PostgresBackedStore(InMemoryStore):
    STATE_KEY = "ai-platform-default"
    MUTATING_METHODS = {
        "reset",
        "create_department",
        "patch_department",
        "delete_department",
        "create_credential",
        "patch_credential",
        "delete_credential",
        "create_model_configuration",
        "patch_model_configuration",
        "delete_model_configuration",
        "set_model_enabled",
        "test_model_connection",
        "upload_skill_package",
        "patch_skill_package",
        "publish_skill_package",
        "unpublish_skill_package",
        "delete_skill_package",
        "bind_skills_to_template",
        "create_business_tool",
        "patch_tool",
        "test_tool",
        "publish_tool",
        "delete_tool",
        "create_knowledge_connection",
        "patch_knowledge_connection",
        "delete_knowledge_connection",
        "test_knowledge_connection",
        "register_knowledge_source",
        "patch_knowledge_source",
        "issue_employee_service_token",
        "create_goal_run",
        "resume_goal_run",
        "create_work_item",
        "delegate_work_item",
        "call_tool_gateway",
        "decide_approval",
        "retrieve_knowledge",
        "create_artifact",
        "accept_artifact",
        "update_organization_quota",
        "create_goal_budget_policy",
        "patch_goal_budget_policy",
        "create_metric_definition",
        "bind_metrics_to_template",
        "record_metric_measurement",
        "create_audit_event",
        "add_audit_disposition",
        "create_audit_rule",
        "patch_audit_rule",
        "evaluate_audit_rule",
        "create_job_template_version",
        "patch_job_template_version",
        "delete_job_template_version",
        "set_job_template_version_status",
        "update_template_evaluation",
        "run_template_evaluation",
        "create_digital_employee",
        "patch_employee_organization",
        "patch_employee_runtime",
        "rerun_employee_smoke_test",
        "set_employee_lifecycle",
    }

    def __init__(self) -> None:
        self._state_lock = RLock()
        self._state_loading = False
        self._persistence_enabled = True
        InMemoryStore.reset(self)
        snapshot = load_relational_state()
        if snapshot:
            self._restore_state(snapshot)
        else:
            self._save_relational_state()

    def __getattribute__(self, name: str) -> Any:
        attr = object.__getattribute__(self, name)
        if name.startswith("_") or name == "reset" or not callable(attr):
            return attr
        if name in {"model_dump", "copy"}:
            return attr

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            with object.__getattribute__(self, "_state_lock"):
                persistence_enabled = object.__getattribute__(self, "_persistence_enabled")
                if persistence_enabled:
                    object.__getattribute__(self, "_load_relational_state")()
                should_persist = name in object.__getattribute__(self, "MUTATING_METHODS")
                try:
                    result = attr(*args, **kwargs)
                except Exception:
                    if should_persist and persistence_enabled:
                        object.__getattribute__(self, "_save_relational_state")()
                    raise
                if should_persist and persistence_enabled:
                    object.__getattribute__(self, "_save_relational_state")()
                return result

        return wrapped

    def reset(self, persist: bool = True) -> None:
        with self._state_lock:
            InMemoryStore.reset(self)
            if persist and self._persistence_enabled:
                self._save_relational_state()

    def _dump_model_dict(self, values: dict[str, Any]) -> dict[str, Any]:
        return {key: value.model_dump(mode="json") for key, value in values.items()}

    def _load_model_dict(self, payload: dict[str, Any], key: str, model: type) -> dict[str, Any]:
        if key not in payload:
            return getattr(self, key)
        return {item_key: model(**item_value) for item_key, item_value in payload[key].items()}

    def _save_relational_state(self) -> None:
        payload = {
            "secret_values": self.secret_values,
            "credentials": self._dump_model_dict(self.credentials),
            "model_configurations": self._dump_model_dict(self.model_configurations),
            "skill_packages": self._dump_model_dict(self.skill_packages),
            "template_skill_bindings": self._dump_model_dict(self.template_skill_bindings),
            "tools": self._dump_model_dict(self.tools),
            "knowledge_connections": self._dump_model_dict(self.knowledge_connections),
            "knowledge_sources": self._dump_model_dict(self.knowledge_sources),
            "goal_runs": self._dump_model_dict(self.goal_runs),
            "work_items": self._dump_model_dict(self.work_items),
            "execution_edges": self._dump_model_dict(self.execution_edges),
            "approvals": self._dump_model_dict(self.approvals),
            "artifacts": self._dump_model_dict(self.artifacts),
            "artifact_acceptances": self._dump_model_dict(self.artifact_acceptances),
            "employee_service_tokens": self.employee_service_tokens,
            "idempotency_results": self._dump_model_dict(self.idempotency_results),
            "organization_quota": self.organization_quota.model_dump(mode="json"),
            "goal_budget_policies": self._dump_model_dict(self.goal_budget_policies),
            "token_ledger": [entry.model_dump(mode="json") for entry in self.token_ledger],
            "metric_definitions": self._dump_model_dict(self.metric_definitions),
            "template_metric_bindings": self._dump_model_dict(self.template_metric_bindings),
            "metric_measurements": self._dump_model_dict(self.metric_measurements),
            "audit_events": [event.model_dump(mode="json") for event in self.audit_events],
            "audit_rules": self._dump_model_dict(self.audit_rules),
            "audit_rule_evaluations": self._dump_model_dict(self.audit_rule_evaluations),
            "review_tasks": self._dump_model_dict(self.review_tasks),
            "departments": self._dump_model_dict(self.departments),
            "template_versions": self._dump_model_dict(self.template_versions),
            "employees": self._dump_model_dict(self.employees),
        }
        save_relational_state(payload)

    def _load_relational_state(self) -> None:
        if self._state_loading:
            return
        snapshot = load_relational_state()
        if snapshot:
            self._restore_state(snapshot)

    def _restore_state(self, payload: dict[str, Any]) -> None:
        self._state_loading = True
        try:
            InMemoryStore.reset(self)
            self.secret_values = dict(payload.get("secret_values", self.secret_values))
            self.credentials = self._load_model_dict(payload, "credentials", CredentialRead)
            self.model_configurations = self._load_model_dict(payload, "model_configurations", ModelConfigurationRead)
            self.skill_packages = self._load_model_dict(payload, "skill_packages", SkillPackageRead)
            self.template_skill_bindings = self._load_model_dict(payload, "template_skill_bindings", TemplateSkillBindingRead)
            self.tools = self._load_model_dict(payload, "tools", ToolRead)
            self.knowledge_connections = self._load_model_dict(payload, "knowledge_connections", KnowledgeConnectionRead)
            self.knowledge_sources = self._load_model_dict(payload, "knowledge_sources", KnowledgeSourceRead)
            self.goal_runs = self._load_model_dict(payload, "goal_runs", GoalRunRead)
            self.work_items = self._load_model_dict(payload, "work_items", WorkItemRead)
            self.execution_edges = self._load_model_dict(payload, "execution_edges", ExecutionGraphEdgeRead)
            self.approvals = self._load_model_dict(payload, "approvals", ApprovalRequestRead)
            self.artifacts = self._load_model_dict(payload, "artifacts", ArtifactRead)
            self.artifact_acceptances = self._load_model_dict(payload, "artifact_acceptances", ArtifactAcceptanceRead)
            self.employee_service_tokens = dict(payload.get("employee_service_tokens", {}))
            self.idempotency_results = self._load_model_dict(payload, "idempotency_results", ToolGatewayResult)
            self.organization_quota = OrganizationQuotaPolicyRead(**payload.get("organization_quota", self.organization_quota.model_dump(mode="json")))
            self.goal_budget_policies = self._load_model_dict(payload, "goal_budget_policies", GoalBudgetPolicyRead)
            self.token_ledger = [TokenLedgerEntryRead(**entry) for entry in payload.get("token_ledger", [])]
            self.metric_definitions = self._load_model_dict(payload, "metric_definitions", MetricDefinitionRead)
            self.template_metric_bindings = self._load_model_dict(payload, "template_metric_bindings", JobTemplateMetricBindingRead)
            self.metric_measurements = self._load_model_dict(payload, "metric_measurements", MetricMeasurementRead)
            self.audit_events = [AuditEventRead(**event) for event in payload.get("audit_events", [])]
            self.audit_rules = self._load_model_dict(payload, "audit_rules", AuditRuleRead)
            self.audit_rule_evaluations = self._load_model_dict(payload, "audit_rule_evaluations", AuditRuleEvaluationRead)
            self.review_tasks = self._load_model_dict(payload, "review_tasks", ReviewTaskRead)
            self.departments = self._load_model_dict(payload, "departments", DepartmentRead)
            self.template_versions = self._load_model_dict(payload, "template_versions", JobTemplateVersionRead)
            self.employees = self._load_model_dict(payload, "employees", DigitalEmployeeRead)
        finally:
            self._state_loading = False


store = PostgresBackedStore()


def reset_store() -> None:
    store._persistence_enabled = False
    store.reset(persist=False)
