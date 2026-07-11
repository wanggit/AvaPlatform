"""执行数字员工上线流程：渲染 Profile、启动 Hermes 并跑 smoke test。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from app.integrations.hermes import HermesClient
from app.runtime.profile import HermesProfileRenderer, ProfileRenderInput
from app.security.tokens import EmployeeServiceTokenManager


class HermesRuntime(Protocol):
    def start(self, profile_dir: Path) -> str:
        """Start a Hermes instance for the profile and return its API base URL."""


@dataclass(frozen=True)
class RolloutResult:
    status: str
    current_step: str
    profile_dir: Path
    hermes_base_url: str | None = None
    smoke_test_run_id: str | None = None
    failure_reason: str | None = None


class EmployeeRolloutWorker:
    def __init__(
        self,
        profile_root: Path,
        renderer: HermesProfileRenderer,
        token_manager: EmployeeServiceTokenManager,
        runtime: HermesRuntime,
        hermes_client_factory: Callable[[str], HermesClient] | None = None,
    ) -> None:
        self.profile_root = profile_root
        self.renderer = renderer
        self.token_manager = token_manager
        self.runtime = runtime
        self.hermes_client_factory = hermes_client_factory or (lambda base_url: HermesClient(base_url))

    def run(self, payload: ProfileRenderInput) -> RolloutResult:
        profile_dir = self.profile_root / payload.employee_id
        token = self.token_manager.issue(payload.employee_id, profile_dir.name)
        render_payload = ProfileRenderInput(
            **{
                **payload.__dict__,
                "employee_service_token_ref": f"issued:{token[:12]}",
            }
        )
        self.renderer.render(profile_dir, render_payload)

        try:
            base_url = self.runtime.start(profile_dir)
            smoke = self.hermes_client_factory(base_url).smoke_test()
        except Exception as exc:  # noqa: BLE001 - rollout must capture infrastructure and config failures.
            return RolloutResult(
                status="failed",
                current_step="smoke_test",
                profile_dir=profile_dir,
                failure_reason=str(exc),
            )

        return RolloutResult(
            status="passed",
            current_step="pending_activation",
            profile_dir=profile_dir,
            hermes_base_url=base_url,
            smoke_test_run_id=smoke.get("run_id"),
        )
