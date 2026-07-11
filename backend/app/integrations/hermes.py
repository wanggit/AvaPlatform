"""封装 Hermes API Server 的正式 HTTP 调用。"""

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
