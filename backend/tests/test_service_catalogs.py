"""覆盖模型、技能、工具和 RAGFlow 知识源目录管理。"""

import base64
import io
import zipfile

import httpx
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fixtures import reset_with_catalog


def client() -> TestClient:
    reset_with_catalog()
    return TestClient(create_app())


def skill_zip_base64(files: dict[str, str]) -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        for name, content in files.items():
            package.writestr(name, content)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_model_configuration_uses_platform_credential_and_selection_filter(monkeypatch) -> None:
    def fake_get(url: str, **kwargs) -> httpx.Response:
        request = httpx.Request("GET", url, headers=kwargs.get("headers"))
        return httpx.Response(200, request=request, json={"models": [{"name": "nomic-embed-text:latest"}]})

    monkeypatch.setattr("app.services.httpx.get", fake_get)
    api = client()
    credential = api.post("/api/v1/credentials", json={
        "name": "Ollama Embedding",
        "owner_type": "platform",
        "owner_id": "platform",
        "owner_name": "Platform",
        "secret_value": "local-dev-secret",
    }).json()

    response = api.post("/api/v1/model-configurations", json={
        "name": "本地向量模型",
        "model_type": "embedding_model",
        "provider": "ollama",
        "base_url": "http://127.0.0.1:11434",
        "api_key_credential_id": credential["id"],
        "model_name": "nomic-embed-text",
        "context_window": 8192,
    })

    assert response.status_code == 201
    model_id = response.json()["id"]
    assert "secret_value" not in credential

    assert api.post(f"/api/v1/model-configurations/{model_id}/test").json()["status"] == "passed"
    assert len(api.get("/api/v1/model-configurations?enabled=true&model_type=embedding_model").json()) == 1

    api.post(f"/api/v1/model-configurations/{model_id}/disable")
    assert api.get("/api/v1/model-configurations?enabled=true&model_type=embedding_model").json() == []


def test_skill_package_upload_requires_zip_with_skill_manifest_and_binds_template() -> None:
    api = client()

    invalid = api.post("/api/v1/skill-packages", json={
        "name": "坏技能",
        "version": "0.1.0",
        "package_file_name": "skill.txt",
        "package_content_base64": base64.b64encode(b"not a zip").decode("ascii"),
    })
    assert invalid.status_code == 400

    uploaded = api.post("/api/v1/skill-packages", json={
        "name": "客服沟通技能",
        "version": "1.0.0",
        "package_file_name": "customer-skill.zip",
        "package_content_base64": skill_zip_base64({"SKILL.md": "# 客服沟通技能\n", "flows/main.yaml": "name: demo\n"}),
    })
    assert uploaded.status_code == 201
    skill_id = uploaded.json()["id"]

    # 重名同版本应返回 409
    duplicate = api.post("/api/v1/skill-packages", json={
        "name": "客服沟通技能",
        "version": "1.0.0",
        "package_file_name": "customer-skill.zip",
        "package_content_base64": skill_zip_base64({"SKILL.md": "# 客服沟通技能\n"}),
    })
    assert duplicate.status_code == 409

    assert api.post(f"/api/v1/skill-packages/{skill_id}/publish").json()["status"] == "published"
    patched = api.patch(f"/api/v1/skill-packages/{skill_id}", json={"description": "更新后的技能说明"})
    assert patched.status_code == 200
    assert patched.json()["description"] == "更新后的技能说明"
    binding = api.put("/api/v1/job-template-versions/jtv-customer-support-v1/skill-bindings", json={
        "skill_package_ids": [skill_id],
    })
    assert binding.status_code == 200
    assert binding.json()["skill_package_ids"] == [skill_id]


def test_business_tool_fields_and_idempotency_publish_gate() -> None:
    api = client()
    credential_id = api.post("/api/v1/credentials", json={
        "name": "工单系统密钥",
        "owner_type": "department",
        "owner_id": "dept-customer-service",
        "owner_name": "客服部",
        "secret_value": "ticket-secret",
    }).json()["id"]

    missing_method = api.post("/api/v1/tools/business", json={
        "name": "创建工单",
        "category": "ticket",
        "access_shape": "http_api",
        "endpoint_url": "https://ticket.example.local/api/tickets",
        "owner": "客服部",
        "credential_id": credential_id,
        "risk_level": "medium",
    })
    assert missing_method.status_code == 409

    tool = api.post("/api/v1/tools/business", json={
        "name": "创建工单",
        "category": "ticket",
        "access_shape": "http_api",
        "endpoint_url": "https://ticket.example.local/api/tickets",
        "method": "POST",
        "owner": "客服部",
        "credential_id": credential_id,
        "risk_level": "medium",
        "audit_required": True,
        "approval_required": True,
    }).json()

    blocked = api.post(f"/api/v1/tools/{tool['id']}/publish")
    assert blocked.status_code == 409
    assert "幂等性" in blocked.json()["detail"]

    idempotent = api.post("/api/v1/tools/business", json={
        "name": "查询客户",
        "category": "crm",
        "access_shape": "http_api",
        "endpoint_url": "https://crm.example.local/api/customers/search",
        "method": "POST",
        "owner": "销售运营",
        "credential_id": credential_id,
        "risk_level": "low",
        "audit_required": True,
        "approval_required": False,
        "idempotency_policy": "按 employee_id + work_item_id + request_hash 去重。",
    }).json()
    assert api.post(f"/api/v1/tools/{idempotent['id']}/publish").json()["lifecycle_status"] == "published"


def test_ragflow_connection_health_discovery_and_source_registration(monkeypatch) -> None:
    def fake_get(url: str, **kwargs) -> httpx.Response:
        request = httpx.Request("GET", url, headers=kwargs.get("headers"))
        return httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": [{
                    "id": "customer-faq",
                    "name": "客户服务 FAQ",
                    "document_count": 3,
                    "chunk_count": 12,
                }],
            },
        )

    def fake_post(url: str, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", url, headers=kwargs.get("headers"))
        return httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": {
                    "chunks": [{
                        "id": "chunk-001",
                        "content": "客户退款需要满足订单状态和时效要求。",
                        "document_id": "doc-001",
                        "document_keyword": "refund.md",
                        "kb_id": "customer-faq",
                        "similarity": 0.91,
                    }],
                    "doc_aggs": [{"doc_id": "doc-001", "doc_name": "refund.md"}],
                    "total": 1,
                },
            },
        )

    monkeypatch.setattr("app.services.httpx.get", fake_get)
    monkeypatch.setattr("app.services.httpx.post", fake_post)
    api = client()
    credential_id = api.post("/api/v1/credentials", json={
        "name": "RAGFlow Key",
        "owner_type": "integration",
        "owner_id": "ragflow",
        "owner_name": "RAGFlow",
        "secret_value": "ragflow-secret",
    }).json()["id"]

    connection = api.post("/api/v1/knowledge-connections", json={
        "name": "RAGFlow",
        "provider": "ragflow",
        "base_url": "http://127.0.0.1:8080",
        "credential_id": credential_id,
    }).json()

    assert api.post(f"/api/v1/knowledge-connections/{connection['id']}/test").json()["status"] == "healthy"
    discovered = api.get(f"/api/v1/knowledge-connections/{connection['id']}/discover").json()
    assert discovered[0]["source_type"] == "dataset"

    source = api.post(f"/api/v1/knowledge-connections/{connection['id']}/sources", json={
        "external_id": "customer-faq",
        "display_name": "客户服务 FAQ",
        "source_type": "dataset",
        "authorization_scope": ["dept-customer-service"],
        "retrieval_settings": {"top_k": 5},
    })

    assert source.status_code == 201
    assert source.json()["connection_id"] == connection["id"]

    preview = api.post("/api/v1/knowledge/preview", json={
        "source_ids": [source.json()["id"]],
        "query": "退款条件是什么？",
        "top_k": 5,
    })
    assert preview.status_code == 200
    assert preview.json()["hits"][0]["content"] == "客户退款需要满足订单状态和时效要求。"
    assert preview.json()["hits"][0]["source_name"] == "客户服务 FAQ"
