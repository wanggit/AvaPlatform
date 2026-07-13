"""封装 Hermes API Server 的正式 HTTP 调用。"""

import time
from typing import Any

import httpx


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
        with self._client() as client:
            response = client.post("/v1/runs", json=payload)
            response.raise_for_status()
            return response.json()

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._client() as client:
            response = client.get(f"/v1/runs/{run_id}")
            response.raise_for_status()
            return response.json()

    def get_run_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._client() as client:
            response = client.get(f"/v1/runs/{run_id}/events")
            response.raise_for_status()
            body = response.json()
            return body["events"] if isinstance(body, dict) and "events" in body else body

    def approve_run(self, run_id: str, approval_id: str, approved: bool, reason: str | None = None) -> dict[str, Any]:
        with self._client() as client:
            response = client.post(
                f"/v1/runs/{run_id}/approval",
                json={"approval_id": approval_id, "approved": approved, "reason": reason},
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
    ) -> dict[str, Any]:
        """创建运行并轮询直到完成，返回包含完整输出的结果。"""
        run = self.create_run(prompt, metadata=metadata, max_tokens=max_tokens)
        run_id = run.get("run_id") or run.get("id") or ""
        if not run_id:
            raise ValueError("Hermes 未返回有效的 run_id")

        deadline = time.monotonic() + max_wait_seconds
        terminal_statuses = {"completed", "failed", "error", "stopped", "cancelled"}

        while time.monotonic() < deadline:
            run = self.get_run(run_id)
            status = run.get("status", "")
            if status in terminal_statuses:
                # 收集 events 中的文本输出拼成完整回复
                output_parts: list[str] = []

                # 优先从 run 的 output/response 字段取
                direct_output = run.get("output") or run.get("response") or run.get("result")
                if direct_output and isinstance(direct_output, str) and direct_output.strip():
                    output_parts.append(direct_output)

                # 也尝试从 events 中收集文本
                try:
                    events = self.get_run_events(run_id)
                    for event in events if isinstance(events, list) else []:
                        if isinstance(event, dict):
                            delta = event.get("delta") or event.get("text") or event.get("content") or ""
                            if isinstance(delta, str) and delta.strip():
                                output_parts.append(delta)
                except (httpx.HTTPError, ValueError):
                    pass  # events 获取失败不影响主流程

                if not output_parts:
                    output_parts.append(str(run))

                run["output"] = "".join(output_parts)
                return run

            time.sleep(poll_interval_seconds)

        # 超时：返回最后一次轮询结果
        run["output"] = f"[评测超时] Hermes 运行 {run_id} 在 {max_wait_seconds}s 内未完成，当前状态: {run.get('status', 'unknown')}"
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

    def create_profile(
        self,
        name: str,
        *,
        model_provider: str = "",
        model_name: str = "",
        clone_from: str | None = None,
        no_skills: bool = False,
    ) -> dict:
        """创建新的 Hermes Profile。"""
        body: dict[str, object] = {
            "name": name,
            "clone_from_default": clone_from is None,
            "no_skills": no_skills,
        }
        if clone_from:
            body["clone_from"] = clone_from
            body["clone_from_default"] = False
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

    # ── Gateway 生命周期 ──────────────────────────────────────

    def start_gateway(self, profile: str) -> dict:
        """启动指定 Profile 的 Gateway 服务。"""
        return self._request("POST", f"/api/gateway/start?profile={profile}")

    def stop_gateway(self, profile: str) -> dict:
        """停止指定 Profile 的 Gateway 服务。"""
        return self._request("POST", f"/api/gateway/stop?profile={profile}")

    def gateway_status(self, profile: str | None = None) -> dict:
        """查询 Gateway 运行状态。"""
        path = "/api/status"
        if profile:
            path += f"?profile={profile}"
        return self._request("GET", path)

    def wait_gateway_ready(self, port: int, timeout_seconds: float = 60.0) -> bool:
        """轮询 Gateway 健康检查端点，直到就绪或超时。

        返回 True 表示 Gateway 已就绪，False 表示超时。
        """
        deadline = time.monotonic() + timeout_seconds
        url = f"http://127.0.0.1:{port}/health"
        while time.monotonic() < deadline:
            try:
                response = httpx.get(url, timeout=5, trust_env=False)
                if response.status_code == 200:
                    return True
            except httpx.HTTPError:
                pass  # 连接被拒绝，继续等待
            time.sleep(2.0)
        return False
