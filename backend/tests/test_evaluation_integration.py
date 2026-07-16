"""模板评测集成测试：Mock Dashboard + HermesClient，验证完整编排流程。"""

import base64
import io
import logging
import zipfile
from unittest.mock import patch

from app.schemas import (
    CredentialRead,
    JobTemplateVersionRead,
    JobTemplateEvaluationRead,
    KnowledgeConnectionRead,
    KnowledgePreviewHit,
    KnowledgeSourceRead,
    ModelConfigurationRead,
    SkillPackageUpload,
    ToolRead,
)
from app.services import InMemoryStore


def _make_template(store: InMemoryStore) -> JobTemplateVersionRead:
    """在 store 中创建测试模板。"""
    template = JobTemplateVersionRead(
        id="jtv-test-001",
        role="测试岗位",
        version="0.1.0",
        grade="Staff",
        department_id="dept-001",
        model_config_id="model-default-llm",
        description="测试岗位描述",
        system_prompt="你是一个测试助手。",
        skills=[],
        tools=[],
        knowledge_sources=[],
        red_lines=["不得泄露数据"],
        max_goal_risk_level="L2",
        default_goal_budget_tokens=100_000,
        status="draft",
        evaluation=JobTemplateEvaluationRead(
            job_template_version_id="jtv-test-001",
            status="not_evaluated",
        ),
    )
    store.template_versions["jtv-test-001"] = template
    return template


def _add_deepseek_model(store: InMemoryStore, secret: str = "deepseek-secret") -> None:
    store.secret_values["secret-cred-deepseek"] = secret
    store.credentials["cred-deepseek"] = CredentialRead(
        id="cred-deepseek",
        name="DeepSeek 密钥",
        owner_type="platform",
        owner_id="platform",
        owner_name="Platform",
        secret_ref="secret-cred-deepseek",
        secret_mask="de***et",
    )
    store.model_configurations["model-deepseek"] = ModelConfigurationRead(
        id="model-deepseek",
        name="DeepSeek",
        model_type="large_language_model",
        provider="deepseek",
        base_url="https://api.deepseek.com",
        api_key="cred-deepseek",
        model_name="deepseek-chat",
        context_window=64_000,
        enabled=True,
    )


def _skill_zip_base64(files: dict[str, str]) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        for name, content in files.items():
            package.writestr(name, content)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class TestFullEvaluationFlow:
    def test_successful_evaluation(self):
        """完整评测流程：创建 Profile → 写入 SOUL → 启动 Gateway → 执行 Run → 清理。"""
        store = InMemoryStore()
        _make_template(store)

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}) as mock_create,
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}) as mock_soul,
            patch.object(store._dashboard, 'write_gateway_port', return_value=None) as mock_port,
            patch.object(store._dashboard, 'write_profile_env', return_value=None),
            patch.object(store._dashboard, 'write_profile_skill', return_value=None),
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', return_value={"ok": True}) as mock_start,
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}) as mock_stop,
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}) as mock_delete,
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=True),
            patch('app.services.HermesClient') as mock_hermes_cls,
        ):
            mock_hermes = mock_hermes_cls.return_value
            mock_hermes.create_and_wait_run.return_value = {
                "run_id": "run-test-001",
                "status": "completed",
                "output": "分析完成：销售额同比增长 15%。",
            }

            result = store.run_template_evaluation("jtv-test-001", "分析销售数据")

        assert result["status"] == "completed"
        assert "销售额同比增长" in result["hermes_output"]
        assert result["run_id"] == "run-test-001"

        mock_create.assert_called_once()
        mock_soul.assert_called_once()
        mock_start.assert_called_once()
        mock_hermes.create_and_wait_run.assert_called_once()
        mock_stop.assert_called_once()
        mock_delete.assert_called_once()

    def test_gateway_startup_timeout(self):
        """Gateway 启动超时时返回错误，并确保清理资源。"""
        store = InMemoryStore()
        _make_template(store)

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_gateway_port', return_value=None),
            patch.object(store._dashboard, 'write_profile_env', return_value=None),
            patch.object(store._dashboard, 'write_profile_skill', return_value=None),
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}) as mock_stop,
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}) as mock_delete,
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=False),
        ):
            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "error"
        assert "超时" in result["error_message"]
        mock_stop.assert_called_once()
        mock_delete.assert_called_once()

    def test_cleanup_on_exception(self):
        """Dashboard API 异常时确保清理。"""
        store = InMemoryStore()
        _make_template(store)

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_gateway_port', return_value=None),
            patch.object(store._dashboard, 'write_profile_env', return_value=None),
            patch.object(store._dashboard, 'write_profile_skill', return_value=None),
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', side_effect=ValueError("启动失败")),
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}) as mock_stop,
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}) as mock_delete,
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=True),
        ):
            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "error"
        mock_stop.assert_called_once()
        mock_delete.assert_called_once()

    def test_port_exhaustion(self):
        """端口耗尽时不调用 Dashboard。"""
        store = InMemoryStore()
        _make_template(store)

        for _ in range(store.port_pool.total_count):
            store.port_pool.allocate()

        with patch.object(store._dashboard, 'create_profile') as mock_create:
            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "error"
        assert "端口池已耗尽" in result["error_message"]
        mock_create.assert_not_called()

    def test_evaluation_writes_provider_api_key_to_profile_env(self):
        """评测 Profile 启动前必须写入 provider API key 环境变量。"""
        store = InMemoryStore()
        version = _make_template(store)
        _add_deepseek_model(store, secret="real-deepseek-key")
        store.template_versions[version.id] = version.model_copy(update={"model_config_id": "model-deepseek"})

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_gateway_port', return_value=None),
            patch.object(store._dashboard, 'write_profile_env', return_value=None) as mock_env,
            patch.object(store._dashboard, 'write_profile_skill', return_value=None),
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=True),
            patch('app.services.HermesClient') as mock_hermes_cls,
        ):
            mock_hermes_cls.return_value.create_and_wait_run.return_value = {
                "run_id": "run-test-001",
                "status": "completed",
                "output": "ok",
            }

            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "completed"
        mock_env.assert_called_once()
        assert mock_env.call_args.args[1]["DEEPSEEK_API_KEY"] == "real-deepseek-key"

    def test_evaluation_prepares_real_template_capabilities(self):
        """评测应把技能、工具和知识源作为真实运行能力注入 Profile 和 Run。"""
        store = InMemoryStore()
        version = _make_template(store)
        _add_deepseek_model(store, secret="real-deepseek-key")
        skill = store.upload_skill_package(SkillPackageUpload(
            name="客服沟通技能",
            version="1.0.0",
            package_file_name="customer-skill.zip",
            package_content_base64=_skill_zip_base64({
                "SKILL.md": "# 客服沟通技能\n按 SOP 处理客户问题。\n",
                "references/playbook.md": "优先安抚，再查询订单。",
            }),
        ))
        store.skill_packages[skill.id] = skill.model_copy(update={"status": "published"})
        store.tools["tool-crm"] = ToolRead(
            id="tool-crm",
            kind="business",
            name="CRM 查询",
            category="crm",
            access_shape="http_api",
            endpoint_url="http://crm.local/query",
            method="POST",
            owner="客服主管",
            risk_level="low",
            audit_required=True,
            lifecycle_status="published",
            idempotency_policy="request_hash",
        )
        store.credentials["cred-ragflow"] = CredentialRead(
            id="cred-ragflow",
            name="RAGFlow",
            owner_type="integration",
            owner_id="ragflow",
            owner_name="RAGFlow",
            secret_ref="secret-ragflow",
            secret_mask="ra***ow",
        )
        store.secret_values["secret-ragflow"] = "ragflow-key"
        store.knowledge_connections["kc-ragflow"] = KnowledgeConnectionRead(
            id="kc-ragflow",
            name="RAGFlow",
            provider="ragflow",
            base_url="http://ragflow.local",
            credential_id="cred-ragflow",
        )
        store.knowledge_sources["ks-faq"] = KnowledgeSourceRead(
            id="ks-faq",
            connection_id="kc-ragflow",
            external_id="dataset-faq",
            display_name="售后 FAQ",
            status="active",
        )
        store.template_versions[version.id] = version.model_copy(update={
            "model_config_id": "model-deepseek",
            "skills": [skill.id],
            "tools": ["tool-crm"],
            "knowledge_sources": ["ks-faq"],
        })
        captured: dict[str, str] = {}

        class FakeHermes:
            def __init__(self, *_args, **_kwargs):
                pass

            def create_and_wait_run(self, prompt, **_kwargs):
                captured["prompt"] = prompt
                return {"run_id": "run-test-001", "status": "completed", "output": "ok"}

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_gateway_port', return_value=None),
            patch.object(store._dashboard, 'write_profile_env', return_value=None) as mock_env,
            patch.object(store._dashboard, 'install_profile_skill_archive', return_value=["SKILL.md"]) as mock_skill,
            patch.object(store._dashboard, 'write_profile_skill', return_value=None) as mock_runtime_skill,
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', return_value={"ok": True, "pid": 123, "log": "/tmp/gateway.log"}),
            patch.object(store._dashboard, 'stop_spawned_gateway', return_value=True),
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=True),
            patch.object(store, '_retrieve_ragflow_chunks', return_value=[
                KnowledgePreviewHit(
                    id="hit-1",
                    content="退货必须在 7 天内提交申请。",
                    source_name="售后 FAQ",
                    document_name="退货政策",
                    chunk_id="chunk-1",
                    score=0.91,
                    citation="退货政策 / chunk-1",
                )
            ]),
            patch('app.services.HermesClient', FakeHermes),
        ):
            result = store.run_template_evaluation("jtv-test-001", "客户询问退货规则")

        assert result["status"] == "completed"
        mock_skill.assert_called_once()
        mock_runtime_skill.assert_called_once()
        env_values = mock_env.call_args.args[1]
        assert env_values["DEEPSEEK_API_KEY"] == "real-deepseek-key"
        assert env_values["AI_PLATFORM_EMPLOYEE_SERVICE_TOKEN"].startswith("eval-token-")
        assert "退货必须在 7 天内提交申请" in captured["prompt"]
        assert "CRM 查询" in captured["prompt"]
        assert "售后 FAQ" in captured["prompt"]
        assert "AI_PLATFORM_EMPLOYEE_SERVICE_TOKEN" in mock_runtime_skill.call_args.args[2]

    def test_failed_hermes_run_exposes_failure_output(self):
        """Hermes run failed 时页面错误应包含底层失败信息。"""
        store = InMemoryStore()
        _make_template(store)

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_gateway_port', return_value=None),
            patch.object(store._dashboard, 'write_profile_env', return_value=None),
            patch.object(store._dashboard, 'write_profile_skill', return_value=None),
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=True),
            patch('app.services.HermesClient') as mock_hermes_cls,
        ):
            mock_hermes_cls.return_value.create_and_wait_run.return_value = {
                "run_id": "run-failed",
                "status": "failed",
                "output": "Provider 'deepseek' is set in config.yaml but no API key was found.",
            }

            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "error"
        assert "Hermes 运行状态: failed" in result["error_message"]
        assert "Provider 'deepseek'" in result["error_message"]

    def test_evaluation_logs_lifecycle_without_secret(self, caplog):
        """评测日志应覆盖关键阶段，但不能泄露模型密钥。"""
        store = InMemoryStore()
        version = _make_template(store)
        _add_deepseek_model(store, secret="real-deepseek-key")
        store.template_versions[version.id] = version.model_copy(update={"model_config_id": "model-deepseek"})
        caplog.set_level(logging.INFO)

        with (
            patch.object(store._dashboard, 'create_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_soul', return_value={"ok": True}),
            patch.object(store._dashboard, 'write_gateway_port', return_value=None),
            patch.object(store._dashboard, 'write_profile_env', return_value=None),
            patch.object(store._dashboard, 'write_profile_skill', return_value=None),
            patch.object(store._dashboard, 'write_profile_file', return_value=None),
            patch.object(store._dashboard, 'start_gateway', return_value={"ok": True, "pid": 123, "log": "/tmp/gateway.log"}),
            patch.object(store._dashboard, 'stop_spawned_gateway', return_value=True),
            patch.object(store._dashboard, 'stop_gateway', return_value={"ok": True}),
            patch.object(store._dashboard, 'delete_profile', return_value={"ok": True}),
            patch.object(store._dashboard, 'wait_gateway_ready', return_value=True),
            patch('app.services.HermesClient') as mock_hermes_cls,
        ):
            mock_hermes_cls.return_value.create_and_wait_run.return_value = {
                "run_id": "run-test-001",
                "status": "completed",
                "output": "ok",
            }

            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "completed"
        logs = caplog.text
        assert "Template evaluation requested" in logs
        assert "Writing Hermes evaluation profile env" in logs
        assert "DEEPSEEK_API_KEY" in logs
        assert "Hermes evaluation gateway started" in logs
        assert "Hermes evaluation run completed" in logs
        assert "Hermes evaluation profile deleted" in logs
        assert "real-deepseek-key" not in logs
