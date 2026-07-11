from __future__ import annotations

"""探测平台依赖的中间件和外部运行时健康状态。"""

import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
import psycopg

from app.config import settings


@dataclass(frozen=True)
class DependencyProbe:
    name: str
    status: str
    detail: str


def probe_postgres() -> DependencyProbe:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as connection:
            with connection.cursor() as cursor:
                cursor.execute("select 1")
                cursor.fetchone()
        return DependencyProbe("postgres", "healthy", "connected")
    except Exception as exc:
        return DependencyProbe("postgres", "unhealthy", str(exc))


def probe_redis() -> DependencyProbe:
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=2) as connection:
            connection.sendall(b"*1\r\n$4\r\nPING\r\n")
            response = connection.recv(16)
        if response.startswith(b"+PONG"):
            return DependencyProbe("redis", "healthy", "pong")
        return DependencyProbe("redis", "unhealthy", response.decode("utf-8", errors="replace"))
    except Exception as exc:
        return DependencyProbe("redis", "unhealthy", str(exc))


def probe_minio() -> DependencyProbe:
    try:
        response = httpx.get(f"{settings.minio_endpoint.rstrip('/')}/minio/health/live", timeout=2, trust_env=False)
        response.raise_for_status()
        return DependencyProbe("minio", "healthy", f"http {response.status_code}")
    except Exception as exc:
        return DependencyProbe("minio", "unhealthy", str(exc))


def probe_ragflow() -> DependencyProbe:
    try:
        response = httpx.get(settings.ragflow_base_url, timeout=2, trust_env=False)
        return DependencyProbe("ragflow", "healthy", f"http {response.status_code}")
    except Exception as exc:
        return DependencyProbe("ragflow", "unhealthy", str(exc))


def probe_ollama() -> DependencyProbe:
    try:
        response = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2, trust_env=False)
        response.raise_for_status()
        return DependencyProbe("ollama", "healthy", f"http {response.status_code}")
    except Exception as exc:
        return DependencyProbe("ollama", "unhealthy", str(exc))


def probe_hermes() -> DependencyProbe:
    headers = {"Authorization": f"Bearer {settings.hermes_api_key}"} if settings.hermes_api_key else {}
    try:
        response = httpx.get(f"{settings.hermes_base_url.rstrip('/')}/health", headers=headers, timeout=2, trust_env=False)
        response.raise_for_status()
        return DependencyProbe("hermes", "healthy", f"http {response.status_code}")
    except Exception as exc:
        return DependencyProbe("hermes", "unhealthy", str(exc))


def probe_dependencies() -> list[DependencyProbe]:
    return [
        probe_postgres(),
        probe_redis(),
        probe_minio(),
        probe_ragflow(),
        probe_ollama(),
        probe_hermes(),
    ]
