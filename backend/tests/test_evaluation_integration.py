"""模板评测集成测试：Mock Dashboard + HermesClient，验证完整编排流程。"""

import base64
import io
import logging
import threading
import time
import zipfile
from unittest.mock import patch

import pytest

from app.schemas import (
    ApprovalDecision,
    TemplateEvaluationRunRequest,
    TemplateEvaluationRunRead,
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
from app.services import ConflictError, InMemoryStore, PostgresBackedStore


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

    def test_async_evaluation_run_tracks_progress_and_result(self):
        """异步评测运行应立即返回运行记录，并持续暴露进度与最终结果。"""
        store = InMemoryStore()
        _make_template(store)
        started = threading.Event()
        release = threading.Event()

        def fake_run_template_evaluation(_store, version_id, task_description, progress_callback=None):
            assert version_id == "jtv-test-001"
            assert task_description == "异步评测任务"
            if progress_callback:
                progress_callback("running", "Fake Gateway 已就绪。", {"stage": "gateway_ready"})
            started.set()
            assert release.wait(timeout=2)
            return {
                "run_id": "run-async-001",
                "task_description": task_description,
                "hermes_output": "异步评测完成。",
                "status": "completed",
                "error_message": None,
            }

        with patch.object(InMemoryStore, "run_template_evaluation", fake_run_template_evaluation):
            run = store.start_template_evaluation_run(
                "jtv-test-001",
                TemplateEvaluationRunRequest(task_description="异步评测任务"),
            )
            assert run.status == "queued"
            assert started.wait(timeout=2)

            running = store.get_template_evaluation_run("jtv-test-001", run.id)
            assert running is not None
            assert running.status == "running"
            assert any(step.message == "Fake Gateway 已就绪。" for step in running.steps)

            with pytest.raises(ConflictError, match=run.id):
                store.start_template_evaluation_run(
                    "jtv-test-001",
                    TemplateEvaluationRunRequest(task_description="并发评测任务"),
                )

            release.set()
            deadline = time.monotonic() + 2
            completed = store.get_template_evaluation_run("jtv-test-001", run.id)
            while completed and completed.status != "completed" and time.monotonic() < deadline:
                time.sleep(0.01)
                completed = store.get_template_evaluation_run("jtv-test-001", run.id)

        assert completed is not None
        assert completed.status == "completed"
        assert completed.hermes_run_id == "run-async-001"
        assert "异步评测完成" in completed.hermes_output
        assert completed.completed_at is not None

    def test_async_evaluation_completed_run_never_persists_empty_output(self):
        """即使底层完成结果为空，运行记录也要保留可排查的原始结果。"""
        store = InMemoryStore()
        _make_template(store)
        run = TemplateEvaluationRunRead(
            id="evalrun-empty-output",
            job_template_version_id="jtv-test-001",
            task_description="空输出评测任务",
            started_at="2026-07-16 10:00:00",
            updated_at="2026-07-16 10:00:00",
        )
        store.template_evaluation_runs[run.id] = run
        store._finish_template_evaluation_run(run.id, {
            "run_id": "run-empty-output",
            "status": "completed",
            "hermes_output": "",
        })

        completed = store.get_template_evaluation_run("jtv-test-001", run.id)

        assert completed is not None
        assert completed.status == "completed"
        assert completed.hermes_output.strip()
        assert "run-empty-output" in completed.hermes_output

    def test_async_evaluation_terminal_progress_keeps_run_pollable_until_output_is_saved(self):
        """Hermes 完成进度不能先把运行记录置为终态，否则前端会停轮询并显示空输出占位。"""
        store = InMemoryStore()
        _make_template(store)
        run = TemplateEvaluationRunRead(
            id="evalrun-progress-race",
            job_template_version_id="jtv-test-001",
            task_description="竞态评测任务",
            status="running",
            started_at="2026-07-16 10:00:00",
            updated_at="2026-07-16 10:00:00",
        )
        store.template_evaluation_runs[run.id] = run

        store._append_template_evaluation_run_step(
            run.id,
            "completed",
            "Hermes 评测 Run 已完成。",
            {"hermes_run_id": "run-progress-race", "output_chars": 120},
        )

        progress_only = store.get_template_evaluation_run("jtv-test-001", run.id)
        assert progress_only is not None
        assert progress_only.status == "running"
        assert progress_only.hermes_output == ""

        store._finish_template_evaluation_run(run.id, {
            "run_id": "run-progress-race",
            "status": "completed",
            "hermes_output": "最终评测报告。",
        })

        completed = store.get_template_evaluation_run("jtv-test-001", run.id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.hermes_output == "最终评测报告。"

    def test_async_evaluation_error_uses_hermes_output_when_error_message_missing(self):
        """底层只返回非完成输出时，失败运行也必须保留可展示的错误详情。"""
        store = InMemoryStore()
        _make_template(store)
        run = TemplateEvaluationRunRead(
            id="evalrun-timeout-output",
            job_template_version_id="jtv-test-001",
            task_description="超时评测任务",
            started_at="2026-07-16 10:00:00",
            updated_at="2026-07-16 10:00:00",
        )
        store.template_evaluation_runs[run.id] = run
        store._finish_template_evaluation_run(run.id, {
            "run_id": "run-timeout-output",
            "status": "running",
            "hermes_output": "[评测超时] Hermes 运行 run-timeout-output 在 300.0s 内未完成，当前状态: running",
        })

        completed = store.get_template_evaluation_run("jtv-test-001", run.id)

        assert completed is not None
        assert completed.status == "error"
        assert completed.error_message is not None
        assert "评测超时" in completed.error_message
        assert completed.steps[-1].details["error_message"] == completed.error_message

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

    def test_completed_hermes_run_with_pending_background_work_returns_error(self):
        """Hermes 只返回后台子任务已启动时，不能把评测当作完成。"""
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
                "run_id": "run-background-only",
                "status": "completed",
                "output": "四个维度正在并行搜索分析，稍后全部结果返回后我会为你整合成一份完整的调研报告。请稍候。",
            }

            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "error"
        assert "未返回最终评测结果" in result["error_message"]
        assert "稍后全部结果返回" in result["hermes_output"]

    def test_completed_hermes_run_with_empty_output_returns_error(self):
        """Hermes completed 但 output 为空时，也不能把评测当作完成。"""
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
                "run_id": "run-empty-output",
                "status": "completed",
                "output": "",
            }

            result = store.run_template_evaluation("jtv-test-001", "测试")

        assert result["status"] == "error"
        assert "未返回最终评测结果" in result["error_message"]
        assert "run-empty-output" in result["hermes_output"]

    def test_evaluation_prompt_requires_final_synchronous_output(self):
        """评测 Prompt 必须禁止后台委派，并要求当前 Run 内返回最终结果。"""
        store = InMemoryStore()
        prompt = store._render_evaluation_run_prompt(
            "分析腾讯 AI 布局",
            {"goal_run_id": "goal-test", "work_item_id": "work-test"},
            [],
            [],
            [],
        )

        assert "禁止使用后台或异步子任务" in prompt
        assert "不得返回“稍后汇总”" in prompt
        assert "必须在当前 Hermes Run 内返回最终评测结果" in prompt

    def test_evaluation_waiting_for_hermes_approval_creates_platform_approval(self):
        """Hermes 评测等待自身审批时，必须同步成平台审批中心待办。"""
        store = InMemoryStore()
        _make_template(store)

        class FakeHermes:
            def __init__(self, *_args, **_kwargs):
                pass

            def create_and_wait_run(self, _prompt, **kwargs):
                callback = kwargs.get("on_waiting_for_approval")
                if callback:
                    callback({"run_id": "run-needs-approval", "status": "waiting_for_approval"})
                return {
                    "run_id": "run-needs-approval",
                    "status": "waiting_for_approval",
                    "output": "[评测超时] Hermes 运行 run-needs-approval 等待审批。",
                }

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
            patch('app.services.HermesClient', FakeHermes),
        ):
            result = store.run_template_evaluation("jtv-test-001", "触发需要审批的评测动作")

        approvals = store.list_approvals(status="pending", approval_type="sensitive_operation")
        assert result["status"] == "error"
        assert approvals
        assert approvals[0].context["source"] == "hermes_evaluation_run"
        assert approvals[0].context["hermes_run_id"] == "run-needs-approval"

    def test_evaluation_approval_registration_persists_immediately(self):
        """后台评测线程创建 Hermes 审批后必须立即持久化，避免被轮询重载覆盖。"""
        store = InMemoryStore()
        version = _make_template(store)
        snapshots: list[dict] = []

        def fake_save_relational_state():
            snapshots.append({
                approval_id: approval.model_dump(mode="json")
                for approval_id, approval in store.approvals.items()
            })

        store._persistence_enabled = True
        store._save_relational_state = fake_save_relational_state

        approval = store._register_hermes_evaluation_approval(
            version=version,
            profile_name="eval-jtv-test-001",
            port=8192,
            run={"run_id": "run-needs-approval", "status": "waiting_for_approval"},
            hermes_base_url="http://127.0.0.1:8192",
            hermes_api_key="eval-api-key",
        )

        assert approval is not None
        assert snapshots
        assert approval.id in snapshots[-1]
        assert snapshots[-1][approval.id]["context"]["hermes_run_id"] == "run-needs-approval"

    def test_evaluation_approval_runtime_survives_state_reload(self):
        """审批列表轮询重载数据库状态时，不能丢失恢复 Hermes Run 所需的运行上下文。"""
        store = InMemoryStore()
        store._state_loading = False
        store._load_model_dict = PostgresBackedStore._load_model_dict.__get__(store, InMemoryStore)
        version = _make_template(store)
        approval = store._register_hermes_evaluation_approval(
            version=version,
            profile_name="eval-jtv-test-001",
            port=8192,
            run={"run_id": "run-needs-approval", "status": "waiting_for_approval"},
            hermes_base_url="http://127.0.0.1:8192",
            hermes_api_key="eval-api-key",
        )
        assert approval is not None
        runtime = dict(store._hermes_approval_runtime)

        PostgresBackedStore._restore_state(store, {
            "approvals": {
                approval.id: approval.model_dump(mode="json"),
            },
        })

        assert approval.id in store.approvals
        assert store._hermes_approval_runtime == runtime

    def test_deciding_hermes_evaluation_approval_resolves_hermes_run(self):
        """审批中心处理 Hermes 评测审批时，必须恢复对应 Hermes Run。"""
        store = InMemoryStore()
        version = _make_template(store)
        approval = store._register_hermes_evaluation_approval(
            version=version,
            profile_name="eval-jtv-test-001",
            port=8192,
            run={"run_id": "run-needs-approval", "status": "waiting_for_approval"},
            hermes_base_url="http://127.0.0.1:8192",
            hermes_api_key="eval-api-key",
        )
        calls: list[dict[str, object]] = []

        class FakeHermes:
            def __init__(self, base_url, api_key=None, **_kwargs):
                calls.append({"base_url": base_url, "api_key": api_key})

            def approve_run(self, run_id, approval_id, approved, reason=None, *, choice=None):
                calls.append({
                    "run_id": run_id,
                    "approval_id": approval_id,
                    "approved": approved,
                    "reason": reason,
                    "choice": choice,
                })
                return {"resolved": 1}

        assert approval is not None
        with patch('app.services.HermesClient', FakeHermes):
            updated = store.decide_approval(
                approval.id,
                "approved",
                ApprovalDecision(decision_by="平台管理员", reason="允许本次评测操作"),
            )

        assert updated is not None
        assert updated.status == "approved"
        assert calls[0] == {"base_url": "http://127.0.0.1:8192", "api_key": "eval-api-key"}
        assert calls[1]["run_id"] == "run-needs-approval"
        assert calls[1]["approval_id"] == approval.id
        assert calls[1]["approved"] is True
        assert calls[1]["choice"] == "once"
        assert approval.id not in store._hermes_approval_runtime

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
