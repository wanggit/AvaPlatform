"""平台配置默认值测试。"""

from app.config import Settings


def test_template_evaluation_run_timeout_defaults_to_600_seconds(monkeypatch):
    """岗位模板评测可能运行较久，默认等待 Hermes Run 600 秒。"""
    monkeypatch.delenv("AI_PLATFORM_EVAL_RUN_TIMEOUT_SECONDS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.eval_run_timeout_seconds == 600.0
