"""集中管理平台运行所需的环境变量和默认配置。"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """平台后端配置；字段会从 AI_PLATFORM_ 前缀的环境变量读取。"""

    database_url: str = "postgresql://ai_platform:ai_platform_dev_password@127.0.0.1:15432/ai_platform"
    redis_url: str = "redis://127.0.0.1:16379/0"
    minio_endpoint: str = "http://127.0.0.1:19000"
    minio_access_key: str = "ai_platform"
    minio_secret_key: str = "ai_platform_dev_password"
    minio_bucket: str = "ai-platform-artifacts"
    ragflow_base_url: str = "http://127.0.0.1:8080"
    ragflow_api_key: str = ""
    ollama_base_url: str = "http://127.0.0.1:11434"
    default_llm_name: str = "DeepSeek V4 Pro"
    default_llm_provider: str = "deepseek"
    default_llm_base_url: str = "https://api.deepseek.com"
    default_llm_model: str = "deepseek-v4-pro"
    default_llm_api_key: str = ""
    default_llm_context_window: int = 128_000
    hermes_base_url: str = "http://127.0.0.1:8642"
    hermes_api_key: str = ""
    hermes_dashboard_url: str = "http://127.0.0.1:9119"
    eval_port_range_start: int = 8100
    eval_port_range_end: int = 8199
    eval_gateway_start_timeout_seconds: float = 60.0
    eval_run_timeout_seconds: float = 300.0

    model_config = SettingsConfigDict(env_prefix="AI_PLATFORM_", env_file=".env", extra="ignore")


settings = Settings()
