"""HermesDashboardClient 单元测试（使用 httpx MockTransport）。"""

import json
import logging
import signal
import zipfile

import httpx
import pytest
import yaml

import app.integrations.hermes as hermes_module
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

    def test_write_gateway_port_enables_api_server_platform(self, tmp_path, monkeypatch):
        """评测端口必须写入 Hermes api_server 平台配置。"""
        fake_home = tmp_path / "home"
        profile_dir = fake_home / ".hermes" / "profiles" / "eval-profile"
        profile_dir.mkdir(parents=True)
        (profile_dir / "config.yaml").write_text(
            "model: deepseek-chat\n"
            "platforms:\n"
            "  telegram:\n"
            "    enabled: false\n",
        )
        monkeypatch.setattr(hermes_module.Path, "home", staticmethod(lambda: fake_home))

        client = HermesDashboardClient("http://127.0.0.1:9119")
        client.write_gateway_port("eval-profile", 8192, api_key="eval-secret")

        config = yaml.safe_load((profile_dir / "config.yaml").read_text())
        api_server = config["platforms"]["api_server"]
        assert api_server["enabled"] is True
        assert api_server["extra"]["host"] == "127.0.0.1"
        assert api_server["extra"]["port"] == 8192
        assert api_server["extra"]["key"] == "eval-secret"
        assert "bind" not in config.get("gateway", {})

    def test_write_profile_env_updates_profile_dotenv(self, tmp_path, monkeypatch, caplog):
        """模型密钥必须写入评测 Profile 的 .env。"""
        fake_home = tmp_path / "home"
        profile_dir = fake_home / ".hermes" / "profiles" / "eval-profile"
        profile_dir.mkdir(parents=True)
        (profile_dir / ".env").write_text(
            "EXISTING=value\n"
            "DEEPSEEK_API_KEY=old\n"
            "\n",
        )
        monkeypatch.setattr(hermes_module.Path, "home", staticmethod(lambda: fake_home))
        caplog.set_level(logging.INFO)

        client = HermesDashboardClient("http://127.0.0.1:9119")
        client.write_profile_env("eval-profile", {"DEEPSEEK_API_KEY": "new-secret", "OPENAI_API_KEY": "openai-secret"})

        dotenv = (profile_dir / ".env").read_text().splitlines()
        assert dotenv == [
            "EXISTING=value",
            "DEEPSEEK_API_KEY=new-secret",
            "OPENAI_API_KEY=openai-secret",
        ]
        assert "env_keys=['DEEPSEEK_API_KEY', 'OPENAI_API_KEY']" in caplog.text
        assert "new-secret" not in caplog.text
        assert "openai-secret" not in caplog.text

    def test_install_profile_skill_archive_extracts_safe_zip(self, tmp_path, monkeypatch):
        """评测 Profile 应能安装平台上传的 Hermes skill zip。"""
        fake_home = tmp_path / "home"
        profile_dir = fake_home / ".hermes" / "profiles" / "eval-profile"
        profile_dir.mkdir(parents=True)
        archive = tmp_path / "customer-skill.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("SKILL.md", "# 客服沟通技能\n")
            package.writestr("references/playbook.md", "处理 SOP\n")
        monkeypatch.setattr(hermes_module.Path, "home", staticmethod(lambda: fake_home))

        client = HermesDashboardClient("http://127.0.0.1:9119")
        installed = client.install_profile_skill_archive("eval-profile", "客服沟通技能", archive)

        skill_dir = profile_dir / "skills" / "客服沟通技能"
        assert (skill_dir / "SKILL.md").read_text() == "# 客服沟通技能\n"
        assert (skill_dir / "references" / "playbook.md").read_text() == "处理 SOP\n"
        assert installed == ["SKILL.md", "references/playbook.md"]

    def test_start_gateway_missing_profile(self, tmp_path, monkeypatch):
        """测试启动 Gateway。"""
        # start_gateway 直接 spawn hermes 子进程，不走 Dashboard HTTP API。
        fake_home = tmp_path / "home"
        monkeypatch.setattr(hermes_module.Path, "home", staticmethod(lambda: fake_home))

        client = HermesDashboardClient("http://127.0.0.1:9119")
        with pytest.raises(ValueError, match="Profile 目录不存在"):
            client.start_gateway("test")

    def test_start_gateway_uses_profile_api_server_config(self, tmp_path, monkeypatch):
        """评测 Gateway 应启动 Dashboard 创建的 Profile 并固定 API Server 环境。"""
        fake_home = tmp_path / "home"
        profile_dir = fake_home / ".hermes" / "profiles" / "eval-profile"
        profile_dir.mkdir(parents=True)
        (profile_dir / "config.yaml").write_text(
            "platforms:\n"
            "  api_server:\n"
            "    enabled: true\n"
            "    extra:\n"
            "      host: 127.0.0.1\n"
            "      port: 8192\n"
            "      key: eval-secret\n"
        )

        popen_calls = []

        class FakePopen:
            def __init__(self, cmd, **kwargs):
                popen_calls.append({"cmd": cmd, **kwargs})
                self.pid = 12345

        monkeypatch.setattr(hermes_module.Path, "home", staticmethod(lambda: fake_home))
        monkeypatch.setattr(hermes_module.subprocess, "Popen", FakePopen)
        monkeypatch.setattr(HermesDashboardClient, "_find_hermes", staticmethod(lambda: "hermes"))

        client = HermesDashboardClient("http://127.0.0.1:9119")
        result = client.start_gateway("eval-profile")

        assert result["ok"] is True
        assert result["pid"] == 12345
        assert result["profile_dir"] == str(profile_dir)
        assert popen_calls
        assert popen_calls[0]["cmd"] == ["hermes", "-p", "eval-profile", "gateway", "run"]
        assert popen_calls[0]["start_new_session"] is True
        env = popen_calls[0]["env"]
        assert env["HERMES_HOME"] == str(fake_home / ".hermes")
        assert env["HERMES_KANBAN_DISPATCH_IN_GATEWAY"] == "false"
        assert env["API_SERVER_ENABLED"] == "true"
        assert env["API_SERVER_HOST"] == "127.0.0.1"
        assert env["API_SERVER_PORT"] == "8192"
        assert env["API_SERVER_KEY"] == "eval-secret"

    def test_stop_spawned_gateway_terminates_started_process(self, monkeypatch):
        """平台直接 Popen 的评测 Gateway 必须由平台直接清理。"""
        sent_signals = []

        class FakePopen:
            pid = 12345

            def poll(self):
                return None if not sent_signals else 0

            def wait(self, timeout=None):
                return 0

        monkeypatch.setattr(hermes_module.os, "killpg", lambda pid, sig: sent_signals.append((pid, sig)))
        monkeypatch.setattr(hermes_module.os, "getpgid", lambda pid: pid)

        client = HermesDashboardClient("http://127.0.0.1:9119")
        client._spawned_gateways["eval-profile"] = FakePopen()

        assert client.stop_spawned_gateway("eval-profile") is True
        assert sent_signals == [(12345, signal.SIGTERM)]
        assert "eval-profile" not in client._spawned_gateways

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
