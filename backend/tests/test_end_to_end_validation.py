"""覆盖从模板创建到员工执行、审批、交付物验收的端到端链路。"""

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


def skill_zip_base64() -> str:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as package:
        package.writestr("SKILL.md", "# 投诉处理技能\n")
        package.writestr("flows/main.yaml", "name: complaint\n")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_seed_data_contains_three_pilot_templates_with_evaluation_and_metrics() -> None:
    api = client()

    templates = api.get("/api/v1/job-template-versions").json()
    pilots = [template for template in templates if template["is_pilot"]]

    assert len(pilots) >= 3
    assert all(template["evaluation"]["status"] == "passed" for template in pilots)
    assert all(template["evaluation"]["cases"] for template in pilots)
    assert all(template["metric_bindings"] for template in pilots)


def test_end_to_end_template_employee_goal_approval_artifact_and_audit_flow(monkeypatch) -> None:
    def fake_post(url: str, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", url, headers=kwargs.get("headers"))
        return httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": {
                    "chunks": [{
                        "id": "chunk-complaint",
                        "content": "补偿审批必须由人工确认。",
                        "document_id": "doc-complaint",
                        "document_keyword": "complaint.md",
                        "kb_id": "complaint-policy",
                        "similarity": 0.93,
                    }],
                    "doc_aggs": [{"doc_id": "doc-complaint", "doc_name": "complaint.md"}],
                    "total": 1,
                },
            },
        )

    def fake_request(method: str, url: str, **kwargs) -> httpx.Response:
        request = httpx.Request(method, url)
        return httpx.Response(200, request=request, json={"accepted": True, "external_id": "COMP-001"})

    monkeypatch.setattr("app.services.httpx.post", fake_post)
    monkeypatch.setattr("app.services.httpx.request", fake_request)
    api = client()

    model = api.get("/api/v1/model-configurations?enabled=true&model_type=large_language_model").json()[0]
    skill = api.post("/api/v1/skill-packages", json={
        "name": "投诉处理技能",
        "version": "1.0.0",
        "package_file_name": "complaint-skill.zip",
        "package_content_base64": skill_zip_base64(),
    }).json()
    api.post(f"/api/v1/skill-packages/{skill['id']}/publish")

    source = api.post("/api/v1/knowledge-connections/kc-ragflow-dev/sources", json={
        "external_id": "complaint-policy",
        "display_name": "投诉处理政策",
        "source_type": "dataset",
        "authorization_scope": ["dept-customer-service"],
        "retrieval_settings": {"top_k": 5},
    }).json()

    tool = api.post("/api/v1/tools/business", json={
        "name": "创建补偿单",
        "category": "ticket",
        "access_shape": "http_api",
        "endpoint_url": "https://ticket.example.local/api/compensations",
        "method": "POST",
        "owner": "客服主管",
        "risk_level": "high",
        "audit_required": True,
        "approval_required": True,
        "idempotency_policy": "按 employee_id + work_item_id + request_hash 去重。",
    }).json()
    api.post(f"/api/v1/tools/{tool['id']}/publish")

    metric = api.post("/api/v1/metrics/definitions", json={
        "name": "投诉一次解决率",
        "target_value": ">= 85%",
        "collection_method": "manual",
        "data_source": "客服主管人工复核",
        "review_cycle": "weekly",
    }).json()

    template = api.post("/api/v1/job-template-versions", json={
        "role": "投诉处理数字员工",
        "version": "1.0.0",
        "grade": "Staff",
        "department_id": "dept-customer-service",
        "model_config_id": model["id"],
        "description": "处理客户升级投诉。",
        "system_prompt": "你是投诉处理数字员工，必须保留证据、引用知识源，并把补偿动作交给人工审批。",
        "max_goal_risk_level": "L3",
        "default_goal_budget_tokens": 100000,
        "skills": [skill["id"]],
        "tools": [tool["id"]],
        "knowledge_sources": [source["id"]],
        "red_lines": ["不得泄露客户隐私", "不得未经审批创建补偿"],
        "metric_bindings": [metric],
        "is_pilot": True,
        "pilot_scenario": "客户升级投诉闭环处理",
    }).json()
    api.put(f"/api/v1/job-template-versions/{template['id']}/evaluation", json={
        "status": "passed",
        "score": 92,
        "evaluator": "管理员",
        "summary": "试点模板评估通过。",
        "cases": [{
            "title": "投诉补偿审批",
            "input_payload": {"ticket_id": "T-001"},
            "expected_result": "引用知识源并触发补偿审批。",
            "actual_result": "符合预期。",
            "assertions": ["触发审批", "返回引用"],
            "status": "passed",
        }],
    })
    api.post(f"/api/v1/job-template-versions/{template['id']}/publish")

    employee = api.post("/api/v1/digital-employees", json={
        "name": "投诉处理小星",
        "nickname": "小星",
        "avatar_url": "https://example.com/avatar.png",
        "department_id": "dept-customer-service",
        "manager_id": None,
        "job_template_version_id": template["id"],
        "notes": "端到端验证员工",
    }).json()
    token = api.post(f"/api/v1/digital-employees/{employee['id']}/service-token").json()["token"]

    goal = api.post("/api/v1/goal-runs", json={
        "title": "处理 T-001 客户升级投诉",
        "goal_type": "customer_case",
        "description": "整理依据、生成处理建议并创建必要审批。",
        "owner": "客服主管",
        "root_responsible": "客服主管",
        "budget_tokens": 1000,
        "policy": {"max_delegate_depth": 1},
    }).json()
    work = api.post("/api/v1/work-items", json={
        "goal_run_id": goal["id"],
        "assignee_employee_id": employee["id"],
        "title": "处理投诉",
        "input_payload": {"ticket_id": "T-001"},
    }).json()

    knowledge = api.post("/api/v1/gateway/knowledge/search", json={
        "employee_service_token": token,
        "goal_run_id": goal["id"],
        "work_item_id": work["id"],
        "knowledge_source_id": source["id"],
        "query": "补偿审批边界",
    })
    assert knowledge.status_code == 200

    pending = api.post("/api/v1/gateway/tool-calls", json={
        "employee_service_token": token,
        "goal_run_id": goal["id"],
        "work_item_id": work["id"],
        "tool_id": tool["id"],
        "payload": {"ticket_id": "T-001", "amount": 20},
        "token_cost": 8,
    }).json()
    assert pending["status"] == "requires_approval"
    api.post(f"/api/v1/approvals/{pending['approval_id']}/approve", json={
        "decision_by": "客服主管",
        "reason": "补偿金额在授权范围内。",
    })
    executed = api.post("/api/v1/gateway/tool-calls", json={
        "employee_service_token": token,
        "goal_run_id": goal["id"],
        "work_item_id": work["id"],
        "tool_id": tool["id"],
        "payload": {"ticket_id": "T-001", "amount": 20},
        "approval_id": pending["approval_id"],
        "token_cost": 8,
    }).json()
    assert executed["status"] == "executed"

    artifact = api.post("/api/v1/artifacts", json={
        "goal_run_id": goal["id"],
        "work_item_id": work["id"],
        "name": "T-001 投诉处理建议",
        "artifact_type": "document",
        "uri": "s3://platform-artifacts/T-001.md",
        "requires_acceptance": True,
    }).json()
    acceptance = api.post(f"/api/v1/artifacts/{artifact['id']}/acceptance", json={
        "accepted": True,
        "reviewer": "客服主管",
        "business_result": "客户接受处理方案",
    }).json()
    assert acceptance["status"] == "accepted"

    event_types = {event["event_type"] for event in api.get("/api/v1/audit/events").json()}
    assert {
        "job_template_version_status_changed",
        "digital_employee_created",
        "tool_published",
        "tool_call_executed",
        "approval_decided",
        "artifact_acceptance_decided",
    }.issubset(event_types)
