"""把平台岗位模板和员工配置渲染为 Hermes Profile 文件。"""

from dataclasses import dataclass, field
from pathlib import Path
import shutil


def _yaml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace('"', '\\"') + '"'


def _dump_yaml(data: dict, indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_yaml(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.append(_dump_yaml(item, indent + 4))
                else:
                    lines.append(f"{prefix}  - {_yaml_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class ProfileRenderInput:
    employee_id: str
    job_template_version_id: str
    system_prompt: str
    model_config: dict
    employee_service_token_ref: str
    tool_allowlist: list[dict] = field(default_factory=list)
    knowledge_sources: list[dict] = field(default_factory=list)
    budget_context: dict = field(default_factory=dict)
    audit_context: dict = field(default_factory=dict)
    callback_url: str | None = None
    skill_package_paths: list[Path] = field(default_factory=list)


class HermesProfileRenderer:
    def render(self, target_dir: Path, payload: ProfileRenderInput) -> Path:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "skills").mkdir(exist_ok=True)
        (target_dir / "platform").mkdir(exist_ok=True)

        (target_dir / "SOUL.md").write_text(payload.system_prompt.strip() + "\n", encoding="utf-8")
        (target_dir / "config.yaml").write_text(
            _dump_yaml({
                "model": payload.model_config,
                "platform_toolsets": {
                    "api_server": {
                        "enabled": True,
                        "tool_allowlist": [tool["tool_id"] for tool in payload.tool_allowlist],
                    },
                },
            }),
            encoding="utf-8",
        )
        (target_dir / ".env").write_text("HERMES_PROFILE_MANAGED_BY=ai-platform\n", encoding="utf-8")
        (target_dir / "platform" / "employee.yaml").write_text(
            _dump_yaml({
                "employee_id": payload.employee_id,
                "job_template_version_id": payload.job_template_version_id,
                "employee_service_token_ref": payload.employee_service_token_ref,
                "tool_allowlist": payload.tool_allowlist,
                "knowledge_sources": payload.knowledge_sources,
                "budget_context": payload.budget_context,
                "audit_context": payload.audit_context,
                "callback_url": payload.callback_url,
            }),
            encoding="utf-8",
        )

        for skill_path in payload.skill_package_paths:
            destination = target_dir / "skills" / skill_path.name
            if skill_path.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(skill_path, destination)
            elif skill_path.is_file():
                shutil.copy2(skill_path, destination)

        return target_dir
