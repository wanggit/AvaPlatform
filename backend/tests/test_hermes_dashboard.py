"""HermesDashboardClient 单元测试（使用 httpx MockTransport）。"""

import json

import httpx
import pytest

from app.integrations.hermes import HermesDashboardClient


def _mock_transport(handler):
    """创建 httpx.MockTransport，根据 handler 函数返回响应。"""
    class Transport(httpx.BaseTransport):
        def handle_request(self, request):
            status, body = handler(request.method, str(request.url), request.content)
            return httpx.Response(
                status_code=status,
                json=body if isinstance(body, dict) else {"detail": str(body)},
                request=request,
            )
    return Transport()


class TestHermesDashboardClient:
    def test_create_profile(self):
        """测试创建 Profile。"""
        def handler(method, url, _content):
            if method == "POST" and url.endswith("/api/profiles"):
                return 200, {"ok": True, "name": "test-profile", "path": "/tmp/test"}
            return 404, "not found"

        client = HermesDashboardClient("http://127.0.0.1:9119")
        # 注入 mock transport
        client._request = lambda method, path, json_body=None: _dispatch(handler, method, f"http://127.0.0.1:9119{path}", json_body)

        result = client.create_profile("test-profile", model_provider="deepseek", model_name="v4")
        assert result["ok"] is True
        assert result["name"] == "test-profile"

    def test_delete_profile(self):
        """测试删除 Profile。"""
        def handler(method, url, _content):
            if method == "DELETE" and "/api/profiles/test-profile" in url:
                return 200, {"ok": True}
            return 404, "not found"

        client = _make_client(handler)
        result = client.delete_profile("test-profile")
        assert result["ok"] is True

    def test_write_soul(self):
        """测试写入 SOUL.md。"""
        def handler(method, url, content):
            if method == "PUT" and "/api/profiles/test/soul" in url:
                body = json.loads(content) if content else {}
                assert "content" in body
                return 200, {"ok": True}
            return 404, "not found"

        client = _make_client(handler)
        result = client.write_soul("test", "You are a helpful assistant.")
        assert result["ok"] is True

    def test_set_model(self):
        """测试设置模型。"""
        def handler(method, url, content):
            if method == "PUT" and "/api/profiles/test/model" in url:
                body = json.loads(content) if content else {}
                assert body["provider"] == "deepseek"
                assert body["model"] == "v4"
                return 200, {"ok": True}
            return 404, "not found"

        client = _make_client(handler)
        result = client.set_model("test", "deepseek", "v4")
        assert result["ok"] is True

    def test_start_gateway(self):
        """测试启动 Gateway。"""
        def handler(method, url, _content):
            if method == "POST" and "/api/gateway/start?profile=test" in url:
                return 200, {"ok": True, "pid": 12345}
            return 404, "not found"

        client = _make_client(handler)
        result = client.start_gateway("test")
        assert result["ok"] is True

    def test_stop_gateway(self):
        """测试停止 Gateway。"""
        def handler(method, url, _content):
            if method == "POST" and "/api/gateway/stop?profile=test" in url:
                return 200, {"ok": True}
            return 404, "not found"

        client = _make_client(handler)
        result = client.stop_gateway("test")
        assert result["ok"] is True

    def test_api_error_propagates(self):
        """测试 Dashboard API 错误时抛出 ValueError。"""
        def handler(_method, _url, _content):
            return 500, {"detail": "Internal error"}

        client = _make_client(handler)
        with pytest.raises(ValueError, match="Dashboard API 错误"):
            client.list_profiles()


def _make_client(handler):
    """创建带 mock transport 的 HermesDashboardClient。"""
    client = HermesDashboardClient("http://127.0.0.1:9119")
    client._request = _make_dispatcher(handler)
    return client


def _dispatch(handler, method, url, json_body):
    """模拟 _request 调用。"""
    content = json.dumps(json_body).encode() if json_body else None
    status, body = handler(method, url, content)
    if status >= 400:
        raise ValueError(f"Dashboard API 错误 ({status}): {body}")
    return body


def _make_dispatcher(handler):
    return lambda method, path, json_body=None: _dispatch(handler, method, f"http://127.0.0.1:9119{path}", json_body)
