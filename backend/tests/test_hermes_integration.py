"""覆盖 Hermes Client、Profile 渲染、运行健康映射和上线 Worker。"""

from pathlib import Path

import httpx
import pytest

from app.integrations.hermes import HermesClient
from app.runtime.health import HealthProbe, runtime_state_from_probe
from app.runtime.profile import HermesProfileRenderer, ProfileRenderInput
from app.security.tokens import EmployeeServiceTokenManager, TokenError
from app.workers.rollout import EmployeeRolloutWorker


def profile_payload(skill_dir: Path | None = None) -> ProfileRenderInput:
    return ProfileRenderInput(
        employee_id="emp-001",
        job_template_version_id="jtv-001",
        system_prompt="你是客服工单协调员工。",
        model_config={"provider": "deepseek", "model": "deepseek-v4-pro"},
        employee_service_token_ref="ref:test",
        tool_allowlist=[{"tool_id": "knowledge_base"}],
        knowledge_sources=[{"source_id": "ks-faq"}],
        budget_context={"goal_budget_tokens": 160000},
        audit_context={"trace": True},
        callback_url="http://platform.local/api/v1/callbacks/hermes",
        skill_package_paths=[skill_dir] if skill_dir else [],
    )


def test_profile_renderer_writes_native_and_platform_files(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill-customer"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

    target = HermesProfileRenderer().render(tmp_path / "profile", profile_payload(skill_dir))

    assert (target / "SOUL.md").read_text(encoding="utf-8").strip() == "你是客服工单协调员工。"
    assert "deepseek-v4-pro" in (target / "config.yaml").read_text(encoding="utf-8")
    assert "employee_id" in (target / "platform" / "employee.yaml").read_text(encoding="utf-8")
    assert (target / "skills" / "skill-customer" / "SKILL.md").exists()


def test_employee_service_token_can_be_verified_and_revoked() -> None:
    manager = EmployeeServiceTokenManager("dev-secret")
    token = manager.issue("emp-001", "profile-001")

    claims = manager.verify(token)
    assert claims.employee_id == "emp-001"

    manager.revoke(token)
    with pytest.raises(TokenError):
        manager.verify(token)


def test_hermes_client_uses_v1_runs_for_smoke_test() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["auth"] = request.headers.get("authorization")
        seen["payload"] = request.read().decode("utf-8")
        return httpx.Response(200, json={"run_id": "run-001", "status": "completed", "usage": {"total_tokens": 3}})

    client = HermesClient("http://hermes.local", api_key="hermes-key", transport=httpx.MockTransport(handler))

    result = client.smoke_test()

    assert seen["path"] == "/v1/runs"
    assert seen["auth"] == "Bearer hermes-key"
    assert "smoke_test" in str(seen["payload"])
    assert result["run_id"] == "run-001"


def test_hermes_client_lists_toolsets_from_api_server() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/toolsets"
        return httpx.Response(200, json=[{"name": "file", "tools": ["read_file"]}])

    client = HermesClient("http://hermes.local", transport=httpx.MockTransport(handler))

    assert client.list_toolsets()[0]["tools"] == ["read_file"]


def test_runtime_health_state_mapping() -> None:
    assert runtime_state_from_probe(HealthProbe(process_running=True, api_reachable=True)) == "healthy"
    assert runtime_state_from_probe(HealthProbe(process_running=True, api_reachable=False, consecutive_failures=1)) == "recovering"
    assert runtime_state_from_probe(HealthProbe(process_running=True, api_reachable=False, consecutive_failures=3)) == "unhealthy"
    assert runtime_state_from_probe(HealthProbe(process_running=False, api_reachable=False, intentionally_stopped=True)) == "stopped"


def test_rollout_worker_renders_profile_starts_runtime_and_smoke_tests(tmp_path: Path) -> None:
    class Runtime:
        def start(self, profile_dir: Path) -> str:
            assert (profile_dir / "SOUL.md").exists()
            return "http://hermes.local"

    class Client:
        def __init__(self, base_url: str) -> None:
            assert base_url == "http://hermes.local"

        def smoke_test(self) -> dict:
            return {"run_id": "run-smoke-001"}

    worker = EmployeeRolloutWorker(
        tmp_path,
        HermesProfileRenderer(),
        EmployeeServiceTokenManager("dev-secret"),
        Runtime(),
        hermes_client_factory=Client,
    )

    result = worker.run(profile_payload())

    assert result.status == "passed"
    assert result.current_step == "pending_activation"
    assert result.smoke_test_run_id == "run-smoke-001"


def test_rollout_worker_captures_smoke_test_failure(tmp_path: Path) -> None:
    class Runtime:
        def start(self, profile_dir: Path) -> str:
            return "http://hermes.local"

    class Client:
        def __init__(self, base_url: str) -> None:
            pass

        def smoke_test(self) -> dict:
            raise RuntimeError("model auth failed")

    worker = EmployeeRolloutWorker(
        tmp_path,
        HermesProfileRenderer(),
        EmployeeServiceTokenManager("dev-secret"),
        Runtime(),
        hermes_client_factory=Client,
    )

    result = worker.run(profile_payload())

    assert result.status == "failed"
    assert result.current_step == "smoke_test"
    assert "model auth failed" in result.failure_reason
