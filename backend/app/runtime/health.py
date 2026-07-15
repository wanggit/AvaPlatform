"""数字员工运行时健康探测结果到平台状态的映射。"""

from dataclasses import dataclass
from typing import Literal


RuntimeState = Literal["not_started", "starting", "healthy", "unhealthy", "recovering", "stopped"]


@dataclass(frozen=True)
class HealthProbe:
    process_running: bool
    api_reachable: bool
    consecutive_failures: int = 0
    intentionally_stopped: bool = False


def runtime_state_from_probe(probe: HealthProbe, *, max_recoverable_failures: int = 2) -> RuntimeState:
    if probe.intentionally_stopped:
        return "stopped"
    if not probe.process_running:
        return "unhealthy"
    if probe.api_reachable:
        return "healthy"
    if probe.consecutive_failures <= max_recoverable_failures:
        return "recovering"
    return "unhealthy"


@dataclass(frozen=True)
class DependencyHealth:
    """平台依赖服务的健康状态汇总。"""

    hermes_gateway_reachable: bool = False
    hermes_dashboard_reachable: bool = False
    database_reachable: bool = False

    @property
    def all_healthy(self) -> bool:
        return (
            self.hermes_gateway_reachable
            and self.hermes_dashboard_reachable
            and self.database_reachable
        )

    @property
    def missing_dependencies(self) -> list[str]:
        """返回不可达的依赖列表（中文描述）。"""
        missing: list[str] = []
        if not self.hermes_gateway_reachable:
            missing.append("Hermes Gateway（8642 端口）")
        if not self.hermes_dashboard_reachable:
            missing.append("Hermes Dashboard（9119 端口）")
        if not self.database_reachable:
            missing.append("数据库")
        return missing
