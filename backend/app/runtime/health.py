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
