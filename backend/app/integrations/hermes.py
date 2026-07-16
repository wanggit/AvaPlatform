"""封装 Hermes API Server 的正式 HTTP 调用。"""

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)


class HermesClient:
    """面向平台服务层的 Hermes API 客户端。"""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 120,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def _client(self) -> httpx.Client:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else None
        return httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_seconds,
            transport=self._transport,
            headers=headers,
            trust_env=False,
        )

    def health(self) -> dict[str, Any]:
        with self._client() as client:
            response = client.get("/health")
            response.raise_for_status()
            return response.json()

    def list_models(self) -> list[dict[str, Any]]:
        with self._client() as client:
            response = client.get("/v1/models")
            response.raise_for_status()
            body = response.json()
            data = body.get("data") if isinstance(body, dict) else body
            return data if isinstance(data, list) else []

    def capabilities(self) -> dict[str, Any]:
        with self._client() as client:
            response = client.get("/v1/capabilities")
            response.raise_for_status()
            return response.json()

    def list_toolsets(self) -> list[dict[str, Any]]:
        with self._client() as client:
            response = client.get("/v1/toolsets")
            response.raise_for_status()
            body = response.json()
            return body if isinstance(body, list) else body.get("data", [])

    def create_run(self, prompt: str, *, metadata: dict[str, Any] | None = None, max_tokens: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"input": prompt, "metadata": metadata or {}}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        logger.info(
            "Hermes create run request base_url=%s metadata_keys=%s max_tokens=%s",
            self.base_url,
            sorted(payload["metadata"].keys()),
            max_tokens,
        )
        with self._client() as client:
            response = client.post("/v1/runs", json=payload)
            response.raise_for_status()
            body = response.json()
        logger.info(
            "Hermes create run response base_url=%s run_id=%s status=%s",
            self.base_url,
            body.get("run_id") or body.get("id") or "",
            body.get("status", ""),
        )
        return body

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._client() as client:
            response = client.get(f"/v1/runs/{run_id}")
            response.raise_for_status()
            return response.json()

    def get_run_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._client() as client:
            response = client.get(f"/v1/runs/{run_id}/events")
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                return self._parse_sse_events(response.text)
            body = response.json()
            return body["events"] if isinstance(body, dict) and "events" in body else body

    def _parse_sse_events(self, text: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        data_lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                if data_lines:
                    event = self._decode_sse_data(data_lines)
                    if event is not None:
                        events.append(event)
                    data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if data_lines:
            event = self._decode_sse_data(data_lines)
            if event is not None:
                events.append(event)
        return events

    def _decode_sse_data(self, data_lines: list[str]) -> dict[str, Any] | None:
        payload = "\n".join(data_lines).strip()
        if not payload:
            return None
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return {"event": "message.delta", "delta": payload}
        return event if isinstance(event, dict) else {"event": "message.delta", "delta": str(event)}

    def _text_from_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return "".join(self._text_from_value(item) for item in value)
        if isinstance(value, dict):
            for key in ("text", "content", "output_text", "value", "message"):
                text = self._text_from_value(value.get(key))
                if text.strip():
                    return text
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _run_output_text(self, run: dict[str, Any]) -> str:
        for key in ("output", "response", "result", "final_response"):
            text = self._text_from_value(run.get(key))
            if text.strip():
                return text
        message = run.get("message")
        if isinstance(message, dict):
            text = self._text_from_value(message.get("content"))
            if text.strip():
                return text
        return ""

    def _events_output_text(self, events: list[dict[str, Any]]) -> str:
        completed_parts: list[str] = []
        delta_parts: list[str] = []
        for event in events:
            event_name = str(event.get("event") or event.get("type") or "")
            completed_text = self._text_from_value(event.get("output") or event.get("final_response"))
            if event_name in {"run.completed", "response.completed"} and completed_text.strip():
                completed_parts.append(completed_text)
                continue
            delta_text = self._text_from_value(
                event.get("delta")
                or event.get("text")
                or event.get("content")
                or event.get("message")
            )
            if delta_text.strip():
                delta_parts.append(delta_text)
        return "".join(completed_parts or delta_parts)

    def approve_run(
        self,
        run_id: str,
        approval_id: str,
        approved: bool,
        reason: str | None = None,
        *,
        choice: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "approval_id": approval_id,
            "choice": choice or ("once" if approved else "deny"),
        }
        if reason:
            body["reason"] = reason
        with self._client() as client:
            response = client.post(
                f"/v1/runs/{run_id}/approval",
                json=body,
            )
            response.raise_for_status()
            return response.json()

    def stop_run(self, run_id: str, reason: str) -> dict[str, Any]:
        with self._client() as client:
            response = client.post(f"/v1/runs/{run_id}/stop", json={"reason": reason})
            response.raise_for_status()
            return response.json()

    def smoke_test(self) -> dict[str, Any]:
        return self.create_run(
            "请只回复 OK，用于验证 Hermes Profile、模型配置和 API Server 是否可用。",
            metadata={"purpose": "smoke_test"},
            max_tokens=16,
        )

    def create_and_wait_run(
        self,
        prompt: str,
        *,
        metadata: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        poll_interval_seconds: float = 3.0,
        max_wait_seconds: float = 300.0,
        on_waiting_for_approval: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """创建运行并轮询直到完成，返回包含完整输出的结果。"""
        run = self.create_run(prompt, metadata=metadata, max_tokens=max_tokens)
        run_id = run.get("run_id") or run.get("id") or ""
        if not run_id:
            raise ValueError("Hermes 未返回有效的 run_id")

        deadline = time.monotonic() + max_wait_seconds
        terminal_statuses = {"completed", "failed", "error", "stopped", "cancelled"}
        approval_wait_notified = False

        while time.monotonic() < deadline:
            run = self.get_run(run_id)
            status = run.get("status", "")
            if status == "waiting_for_approval":
                if on_waiting_for_approval and not approval_wait_notified:
                    on_waiting_for_approval(run)
                    approval_wait_notified = True
            else:
                approval_wait_notified = False
            if status in terminal_statuses:
                # 收集 events 中的文本输出拼成完整回复
                output_parts: list[str] = []

                # 优先从 run 的 output/response 字段取
                direct_output = self._run_output_text(run)
                if direct_output.strip():
                    output_parts.append(direct_output)

                if not output_parts:
                    # 也尝试从 events 中收集文本
                    try:
                        events = self.get_run_events(run_id)
                        events_output = self._events_output_text(events if isinstance(events, list) else [])
                        if events_output.strip():
                            output_parts.append(events_output)
                    except (httpx.HTTPError, ValueError):
                        pass  # events 获取失败不影响主流程

                if not output_parts:
                    output_parts.append(json.dumps(run, ensure_ascii=False))

                run["output"] = "".join(output_parts)
                logger.info(
                    "Hermes run terminal run_id=%s status=%s output_chars=%s",
                    run_id,
                    status,
                    len(run["output"]),
                )
                return run

            time.sleep(poll_interval_seconds)

        # 超时：返回最后一次轮询结果
        run["output"] = f"[评测超时] Hermes 运行 {run_id} 在 {max_wait_seconds}s 内未完成，当前状态: {run.get('status', 'unknown')}"
        logger.warning(
            "Hermes run wait timeout run_id=%s last_status=%s max_wait_seconds=%s",
            run_id,
            run.get("status", "unknown"),
            max_wait_seconds,
        )
        return run


class HermesDashboardClient:
    """封装 Hermes Dashboard REST API，管理 Profile 和 Gateway 生命周期。

    Dashboard 默认运行在 9119 端口，提供 Profile CRUD、SOUL.md 读写、
    模型设置和 Gateway 启停等管理接口。认证通过 X-Hermes-Session-Token
    头或 Bearer token。
    """

    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._spawned_gateways: dict[str, subprocess.Popen] = {}

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, method: str, path: str, json_body: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            if method == "GET":
                response = httpx.get(url, headers=self._headers(), timeout=30, trust_env=False)
            elif method == "POST":
                response = httpx.post(url, headers=self._headers(), json=json_body, timeout=30, trust_env=False)
            elif method == "PUT":
                response = httpx.put(url, headers=self._headers(), json=json_body, timeout=30, trust_env=False)
            elif method == "DELETE":
                response = httpx.delete(url, headers=self._headers(), timeout=30, trust_env=False)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = exc.response.json().get("detail", "")
            except Exception:
                pass
            raise ValueError(f"Dashboard API 错误 ({exc.response.status_code}): {detail or str(exc)}") from exc
        except httpx.HTTPError as exc:
            raise ValueError(f"Dashboard API 连接失败: {exc}") from exc

    # ── Profile 管理 ──────────────────────────────────────────

    @staticmethod
    def _profile_dir(name: str) -> Path:
        return Path.home() / ".hermes" / "profiles" / name

    @staticmethod
    def _safe_profile_child_name(name: str) -> str:
        cleaned = re.sub(r"[\\/:\0]+", "-", name).strip(" .")
        return cleaned or "skill"

    def create_profile(
        self,
        name: str,
        *,
        model_provider: str = "",
        model_name: str = "",
        clone_from: str | None = None,
        no_skills: bool = False,
    ) -> dict:
        """创建新的 Hermes Profile。

        默认创建空白 Profile（不克隆任何已有 Profile）。
        指定 clone_from="default" 可从默认 Profile 克隆配置。
        """
        clone_from_default = clone_from == "default"
        body: dict[str, object] = {
            "name": name,
            "clone_from_default": clone_from_default,
            "no_skills": no_skills,
        }
        if clone_from and not clone_from_default:
            body["clone_from"] = clone_from
        if model_provider and model_name:
            body["provider"] = model_provider
            body["model"] = model_name
        return self._request("POST", "/api/profiles", body)

    def delete_profile(self, name: str) -> dict:
        """删除指定 Profile。"""
        return self._request("DELETE", f"/api/profiles/{name}")

    def list_profiles(self) -> list[dict]:
        """列出所有 Profile。"""
        result = self._request("GET", "/api/profiles")
        return result.get("profiles", []) if isinstance(result, dict) else []

    def write_soul(self, name: str, content: str) -> dict:
        """写入 Profile 的 SOUL.md（系统提示词）。"""
        return self._request("PUT", f"/api/profiles/{name}/soul", {"content": content})

    def read_soul(self, name: str) -> dict:
        """读取 Profile 的 SOUL.md。"""
        return self._request("GET", f"/api/profiles/{name}/soul")

    def set_model(self, name: str, provider: str, model: str) -> dict:
        """设置 Profile 的模型。"""
        return self._request("PUT", f"/api/profiles/{name}/model", {"provider": provider, "model": model})

    def write_profile_env(self, name: str, values: dict[str, str]) -> None:
        """Update a Profile's .env with secret runtime values."""
        profile_dir = self._profile_dir(name)
        if not profile_dir.exists():
            raise ValueError(f"Profile 目录不存在: {profile_dir}")

        sanitized: dict[str, str] = {}
        for key, value in values.items():
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise ValueError(f"非法环境变量名: {key}")
            if "\n" in value or "\r" in value:
                raise ValueError(f"环境变量 {key} 包含非法换行")
            sanitized[key] = value

        env_path = profile_dir / ".env"
        existing = env_path.read_text().splitlines() if env_path.exists() else []
        written: set[str] = set()
        lines: list[str] = []
        for line in existing:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or "=" not in line:
                lines.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key in sanitized:
                lines.append(f"{key}={sanitized[key]}")
                written.add(key)
            else:
                lines.append(line)

        for key, value in sanitized.items():
            if key not in written:
                lines.append(f"{key}={value}")

        env_path.write_text("\n".join(lines) + "\n")
        try:
            env_path.chmod(0o600)
        except OSError:
            pass
        logger.info(
            "Hermes profile env updated profile=%s env_keys=%s path=%s",
            name,
            sorted(sanitized.keys()),
            env_path,
        )

    def write_profile_file(self, name: str, relative_path: str, content: str) -> Path:
        """Write a UTF-8 text file under a Profile directory."""
        profile_dir = self._profile_dir(name)
        if not profile_dir.exists():
            raise ValueError(f"Profile 目录不存在: {profile_dir}")
        target = (profile_dir / relative_path).resolve()
        try:
            target.relative_to(profile_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"非法 Profile 文件路径: {relative_path}") from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("Hermes profile file written profile=%s path=%s chars=%s", name, target, len(content))
        return target

    def write_profile_skill(self, name: str, skill_name: str, skill_md: str) -> Path:
        """Write a single-file Hermes skill into a Profile."""
        safe_name = self._safe_profile_child_name(skill_name)
        return self.write_profile_file(name, f"skills/{safe_name}/SKILL.md", skill_md)

    def install_profile_skill_archive(self, name: str, skill_name: str, archive_path: Path) -> list[str]:
        """Extract a Hermes skill zip into profile skills/<skill_name>/."""
        profile_dir = self._profile_dir(name)
        if not profile_dir.exists():
            raise ValueError(f"Profile 目录不存在: {profile_dir}")
        if not archive_path.exists():
            raise ValueError(f"技能包文件不存在: {archive_path}")
        if not zipfile.is_zipfile(archive_path):
            raise ValueError(f"技能包不是有效 zip: {archive_path}")

        safe_name = self._safe_profile_child_name(skill_name)
        destination = profile_dir / "skills" / safe_name
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

        installed: list[str] = []
        with zipfile.ZipFile(archive_path) as package:
            for info in package.infolist():
                if info.is_dir():
                    continue
                member_path = Path(info.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValueError(f"技能包包含非法路径: {info.filename}")
                target = (destination / member_path).resolve()
                try:
                    target.relative_to(destination.resolve())
                except ValueError as exc:
                    raise ValueError(f"技能包包含越界路径: {info.filename}") from exc
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, open(target, "wb") as dest:
                    shutil.copyfileobj(source, dest)
                installed.append(info.filename)

        if "SKILL.md" not in installed and not any(path.endswith("/SKILL.md") for path in installed):
            raise ValueError("技能包必须包含 SKILL.md")
        logger.info(
            "Hermes profile skill archive installed profile=%s skill=%s archive=%s files=%s",
            name,
            safe_name,
            archive_path,
            len(installed),
        )
        return installed

    def write_gateway_port(self, name: str, port: int, *, api_key: str = "") -> None:
        """配置 Profile 的 API Server 监听端口。

        Hermes 的 /v1/runs HTTP API 由 ``platforms.api_server`` 平台暴露，
        不是 ``gateway.bind``。Dashboard 没有直接的 config-write API，因此
        直接修改 Profile 目录下的 config.yaml 文件。
        """
        import yaml
        from pathlib import Path

        profile_dir = Path.home() / ".hermes" / "profiles" / name
        config_path = profile_dir / "config.yaml"
        if not config_path.exists():
            raise ValueError(f"Profile 配置不存在: {config_path}")

        try:
            config = yaml.safe_load(config_path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"无法解析 Profile 配置: {exc}") from exc

        platforms = config.setdefault("platforms", {})
        if not isinstance(platforms, dict):
            platforms = {}
            config["platforms"] = platforms
        api_server = platforms.setdefault("api_server", {})
        if not isinstance(api_server, dict):
            api_server = {}
            platforms["api_server"] = api_server
        api_server["enabled"] = True
        extra = api_server.setdefault("extra", {})
        if not isinstance(extra, dict):
            extra = {}
            api_server["extra"] = extra
        extra["host"] = "127.0.0.1"
        extra["port"] = port
        if api_key:
            extra["key"] = api_key

        gateway = config.get("gateway")
        if isinstance(gateway, dict):
            gateway.pop("bind", None)

        config_path.write_text(yaml.safe_dump(config, default_flow_style=False, allow_unicode=True))
        logger.info(
            "Hermes profile api_server configured profile=%s host=%s port=%s api_key_configured=%s config=%s",
            name,
            extra["host"],
            extra["port"],
            bool(api_key),
            config_path,
        )

    @staticmethod
    def _api_server_env_from_profile(profile_dir: Path) -> dict[str, str]:
        """Read API Server config from a copied profile and pin child env."""
        import yaml

        config_path = profile_dir / "config.yaml"
        try:
            config = yaml.safe_load(config_path.read_text()) or {}
        except (OSError, yaml.YAMLError):
            return {}

        platforms = config.get("platforms") if isinstance(config, dict) else None
        api_server = platforms.get("api_server") if isinstance(platforms, dict) else None
        if not isinstance(api_server, dict) or not api_server.get("enabled"):
            return {}
        extra = api_server.get("extra")
        if not isinstance(extra, dict):
            extra = {}

        env = {"API_SERVER_ENABLED": "true"}
        host = extra.get("host")
        port = extra.get("port")
        key = extra.get("key")
        if host:
            env["API_SERVER_HOST"] = str(host)
        if port:
            env["API_SERVER_PORT"] = str(port)
        if key:
            env["API_SERVER_KEY"] = str(key)
        return env

    # ── Gateway 生命周期 ──────────────────────────────────────

    def start_gateway(self, profile: str) -> dict:
        """启动指定 Profile 的 Gateway（直接 spawn 进程，不走 systemd）。

        Hermes ``-p <profile>`` 会把 HERMES_HOME 切到
        ``~/.hermes/profiles/<profile>``，因此 PID 文件天然按 Profile 隔离。
        这里直接启动 Dashboard 创建的 Profile，使 Dashboard 也能看到
        Profile Gateway 的真实运行状态。

        stdout/stderr 写入日志文件，方便排查启动失败原因。
        返回 {"ok": True, "pid": <pid>, "log": "<log_path>", "profile_dir": "<path>"}。
        """
        # 日志路径
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".runtime", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"gateway-{profile}.log")

        default_home = Path.home() / ".hermes"
        src_profile = default_home / "profiles" / profile
        if not src_profile.exists():
            raise ValueError(f"Profile 目录不存在: {src_profile}")

        # 查找 hermes 可执行文件
        hermes_bin = self._find_hermes()
        cmd = [hermes_bin, "-p", profile, "gateway", "run"]

        env = {
            **os.environ,
            "HERMES_NONINTERACTIVE": "1",
            "HERMES_HOME": str(default_home),
            # Template evaluation drives Hermes through /v1/runs and does not use
            # Hermes kanban. A fresh isolated HERMES_HOME can otherwise start the
            # embedded kanban dispatcher against an unprepared board DB and keep
            # failing during gateway boot.
            "HERMES_KANBAN_DISPATCH_IN_GATEWAY": "false",
            **self._api_server_env_from_profile(src_profile),
        }
        api_server_env = {key: env.get(key, "") for key in ("API_SERVER_ENABLED", "API_SERVER_HOST", "API_SERVER_PORT")}

        log_file = open(log_path, "ab", buffering=0)
        log_file.write(f"\n=== Gateway start {profile} at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n".encode())
        log_file.write(f"# HERMES_HOME root={default_home}\n".encode())
        log_file.write(f"# Profile dir={src_profile}\n".encode())
        log_file.write(f"# API Server env={api_server_env}, key_configured={bool(env.get('API_SERVER_KEY'))}\n".encode())
        log_file.write(f"CMD: {' '.join(cmd)}\n".encode())

        logger.info(
            "Starting Hermes profile gateway profile=%s cmd=%s profile_dir=%s log=%s api_server_env=%s api_key_configured=%s",
            profile,
            cmd,
            src_profile,
            log_path,
            api_server_env,
            bool(env.get("API_SERVER_KEY")),
        )
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env,
            )
        except Exception:
            logger.exception("Failed to start Hermes profile gateway profile=%s log=%s", profile, log_path)
            raise
        finally:
            log_file.close()

        self._spawned_gateways[profile] = proc
        logger.info("Hermes profile gateway started profile=%s pid=%s log=%s", profile, proc.pid, log_path)
        return {"ok": True, "pid": proc.pid, "log": log_path, "profile_dir": str(src_profile)}

    def stop_spawned_gateway(self, profile: str, pid: int | None = None, timeout_seconds: float = 10.0) -> bool:
        """Stop a Gateway process started by start_gateway()."""
        proc = self._spawned_gateways.pop(profile, None)
        target_pid = proc.pid if proc is not None else pid
        if not target_pid:
            logger.info("No spawned Hermes gateway pid to stop profile=%s", profile)
            return False
        if proc is not None and proc.poll() is not None:
            logger.info("Spawned Hermes gateway already exited profile=%s pid=%s", profile, target_pid)
            return True

        try:
            os.killpg(os.getpgid(target_pid), signal.SIGTERM)
            logger.info("Sent SIGTERM to Hermes gateway profile=%s pid=%s", profile, target_pid)
        except ProcessLookupError:
            logger.info("Hermes gateway process not found during stop profile=%s pid=%s", profile, target_pid)
            return True
        except OSError as exc:
            logger.warning("Failed to send SIGTERM to Hermes gateway profile=%s pid=%s error=%s", profile, target_pid, exc)
            return False

        if proc is not None:
            try:
                proc.wait(timeout=timeout_seconds)
                logger.info("Hermes gateway stopped profile=%s pid=%s", profile, target_pid)
                return True
            except subprocess.TimeoutExpired:
                logger.warning("Hermes gateway did not stop before timeout; sending SIGKILL profile=%s pid=%s", profile, target_pid)
                try:
                    os.killpg(os.getpgid(target_pid), signal.SIGKILL)
                except ProcessLookupError:
                    return True
                except OSError as exc:
                    logger.warning("Failed to send SIGKILL to Hermes gateway profile=%s pid=%s error=%s", profile, target_pid, exc)
                    return False
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning("Hermes gateway still running after SIGKILL profile=%s pid=%s", profile, target_pid)
                    return False
                logger.info("Hermes gateway killed profile=%s pid=%s", profile, target_pid)
                return True

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                os.kill(target_pid, 0)
            except ProcessLookupError:
                return True
            except OSError:
                return False
            time.sleep(0.2)
        try:
            os.killpg(os.getpgid(target_pid), signal.SIGKILL)
            logger.warning("Hermes gateway killed after stop wait profile=%s pid=%s", profile, target_pid)
            return True
        except ProcessLookupError:
            return True
        except OSError as exc:
            logger.warning("Failed to kill Hermes gateway after stop wait profile=%s pid=%s error=%s", profile, target_pid, exc)
            return False

    @staticmethod
    def _find_hermes() -> str:
        return "hermes"

    def stop_gateway(self, profile: str) -> dict:
        """停止指定 Profile 的 Gateway 进程。

        通过 Dashboard API 的 stop 端点触发（内部调用 hermes gateway stop）。
        """
        return self._request("POST", f"/api/gateway/stop?profile={profile}")

    def gateway_status(self, profile: str | None = None) -> dict:
        """查询 Gateway 运行状态。"""
        path = "/api/status"
        if profile:
            path += f"?profile={profile}"
        return self._request("GET", path)

    def wait_gateway_ready(self, port: int, timeout_seconds: float = 60.0) -> bool:
        """轮询 Gateway API Server 直到就绪或超时。

        /health 不要求 Authorization；/v1/models 在 API_SERVER_KEY 存在时
        需要 Bearer token，不能作为无状态启动探针。
        返回 True 表示 Gateway 已就绪，False 表示超时。
        """
        deadline = time.monotonic() + timeout_seconds
        url = f"http://127.0.0.1:{port}/health"
        attempts = 0
        logger.info("Waiting for Hermes gateway readiness port=%s timeout_seconds=%s url=%s", port, timeout_seconds, url)
        while time.monotonic() < deadline:
            attempts += 1
            try:
                response = httpx.get(url, timeout=5, trust_env=False)
                if response.status_code == 200:
                    logger.info("Hermes gateway ready port=%s attempts=%s", port, attempts)
                    return True
                logger.info("Hermes gateway health not ready port=%s attempt=%s status_code=%s", port, attempts, response.status_code)
            except httpx.HTTPError:
                pass  # 连接被拒绝或超时，继续等待
            time.sleep(2.0)
        logger.warning("Hermes gateway readiness timeout port=%s attempts=%s timeout_seconds=%s", port, attempts, timeout_seconds)
        return False
