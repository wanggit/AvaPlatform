"""模板评测单元测试：SOUL 渲染、并发锁、异常清理。"""

import pytest

from app.schemas import (
    JobTemplateVersionRead,
    JobTemplateEvaluationRead,
    SkillPackageRead,
    ToolRead,
    KnowledgeSourceRead,
)
from app.services import InMemoryStore, ConflictError


def _make_template(**overrides) -> JobTemplateVersionRead:
    """创建测试用模板版本。"""
    defaults = dict(
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
        red_lines=["不得泄露用户数据"],
        max_goal_risk_level="L2",
        default_goal_budget_tokens=100_000,
        status="draft",
        evaluation=JobTemplateEvaluationRead(
            job_template_version_id="jtv-test-001",
            status="not_evaluated",
        ),
    )
    defaults.update(overrides)
    return JobTemplateVersionRead(**defaults)


class TestSoulRendering:
    def test_basic_soul(self):
        """基本 SOUL.md 渲染：岗位名、职级、描述、提示词、红线。"""
        store = InMemoryStore()
        template = _make_template()
        soul = store._render_evaluation_soul(template)

        assert "# 测试岗位 (Staff)" in soul
        assert "## 岗位说明" in soul
        assert "测试岗位描述" in soul
        assert "## 系统提示词" in soul
        assert "你是一个测试助手。" in soul
        assert "## 红线" in soul
        assert "- 不得泄露用户数据" in soul

    def test_soul_with_skills(self):
        """SOUL.md 包含技能列表。"""
        store = InMemoryStore()
        store.skill_packages["skill-1"] = SkillPackageRead(
            id="skill-1", name="数据分析", version="1.0",
            package_file_name="data.zip", manifest={},
        )
        template = _make_template(skills=["skill-1"])
        soul = store._render_evaluation_soul(template)

        assert "## 可用技能" in soul
        assert "数据分析 v1.0" in soul

    def test_soul_with_tools(self):
        """SOUL.md 包含工具白名单。"""
        store = InMemoryStore()
        store.tools["tool-1"] = ToolRead(
            id="tool-1", name="CRM 查询", kind="business",
            lifecycle_status="published", access_shape="http_api",
            endpoint_url="http://crm/api", method="GET",
            risk_level="low", audit_required=False, test_status="not_tested",
        )
        template = _make_template(tools=["tool-1"])
        soul = store._render_evaluation_soul(template)

        assert "## 工具白名单" in soul
        assert "CRM 查询" in soul

    def test_soul_with_knowledge(self):
        """SOUL.md 包含知识源。"""
        store = InMemoryStore()
        store.knowledge_sources["ks-1"] = KnowledgeSourceRead(
            id="ks-1", connection_id="kc-1",
            external_id="ds-1", display_name="产品手册",
            status="active",
        )
        template = _make_template(knowledge_sources=["ks-1"])
        soul = store._render_evaluation_soul(template)

        assert "## 知识源" in soul
        assert "产品手册" in soul

    def test_soul_without_optional_fields(self):
        """无描述、无技能、无工具、无知识、无红线的模板。"""
        store = InMemoryStore()
        template = _make_template(
            description="",
            system_prompt="",
            skills=[],
            tools=[],
            knowledge_sources=[],
            red_lines=[],
        )
        soul = store._render_evaluation_soul(template)

        assert "## 岗位说明" not in soul
        assert "## 系统提示词" not in soul
        assert "## 可用技能" not in soul
        assert "## 工具白名单" not in soul
        assert "## 红线" not in soul


class TestEvalConcurrency:
    def test_concurrent_eval_blocked(self):
        """同一模板并发评测应被拒绝。"""
        store = InMemoryStore()
        store.template_versions["jtv-test-001"] = _make_template()

        lock = store._eval_lock_for("jtv-test-001")
        assert lock.acquire(blocking=False)  # 第一次获取成功

        # 第二次获取应失败（锁已被持有）
        assert not lock.acquire(blocking=False)

        lock.release()

    def test_different_templates_independent(self):
        """不同模板的评测锁互不影响。"""
        store = InMemoryStore()
        lock_a = store._eval_lock_for("jtv-a")
        lock_b = store._eval_lock_for("jtv-b")

        assert lock_a.acquire(blocking=False)
        assert lock_b.acquire(blocking=False)  # 不同模板，可以同时评测

        lock_a.release()
        lock_b.release()

    def test_run_eval_rejects_concurrent(self):
        """run_template_evaluation 在并发时抛出 ConflictError。"""
        store = InMemoryStore()
        store.template_versions["jtv-test-001"] = _make_template()

        # 先手动获取锁模拟正在评测
        lock = store._eval_lock_for("jtv-test-001")
        lock.acquire(blocking=False)

        try:
            with pytest.raises(ConflictError, match="正在评测中"):
                store.run_template_evaluation("jtv-test-001", "测试任务")
        finally:
            lock.release()
