"""覆盖工具网关、知识检索网关和员工服务令牌鉴权。"""

import httpx
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fixtures import reset_with_catalog


def client() -> TestClient:
    reset_with_catalog()
    return TestClient(create_app())


def employee_payload(name: str = "客服小星") -> dict:
    return {
        "name": name,
        "nickname": name,
        "avatar_url": "https://example.com/avatar.png",
        "department_id": "dept-customer-service",
        "manager_id": None,
        "job_template_version_id": "jtv-customer-support-v1",
        "notes": "执行测试员工",
    }


def create_employee(api: TestClient, name: str = "客服小星") -> str:
    return api.post("/api/v1/digital-employees", json=employee_payload(name)).json()["id"]


def create_goal(api: TestClient, budget_tokens: int = 1000) -> str:
    return api.post("/api/v1/goal-runs", json={
        "title": "处理客户升级投诉",
        "goal_type": "customer_case",
        "description": "整理证据并输出处理建议。",
        "owner": "客服主管",
        "root_responsible": "客服主管",
        "budget_tokens": budget_tokens,
        "policy": {"max_delegate_depth": 1},
    }).json()["id"]


def create_work_item(api: TestClient, goal_id: str, employee_id: str) -> str:
    return api.post("/api/v1/work-items", json={
        "goal_run_id": goal_id,
        "assignee_employee_id": employee_id,
        "title": "整理客户上下文",
        "input_payload": {"ticket_id": "T-001"},
        "budget_tokens": 500,
    }).json()["id"]


def service_token(api: TestClient, employee_id: str) -> str:
    return api.post(f"/api/v1/digital-employees/{employee_id}/service-token").json()["token"]


def test_goal_run_work_item_and_one_level_delegation_graph() -> None:
    api = client()
    employee_id = create_employee(api)
    delegate_id = create_employee(api, "客服小月")
    goal_id = create_goal(api)
    root_work_id = create_work_item(api, goal_id, employee_id)

    child = api.post("/api/v1/work-items/delegations", json={
        "from_work_item_id": root_work_id,
        "assignee_employee_id": delegate_id,
        "title": "补充退款政策依据",
        "input_payload": {"policy": "refund"},
    })

    assert child.status_code == 201
    assert child.json()["depth"] == 1
    edges = api.get(f"/api/v1/goal-runs/{goal_id}/execution-edges").json()
    assert edges[0]["parent_work_item_id"] == root_work_id
    assert edges[0]["child_work_item_id"] == child.json()["id"]

    blocked = api.post("/api/v1/work-items/delegations", json={
        "from_work_item_id": child.json()["id"],
        "assignee_employee_id": employee_id,
        "title": "不允许二层委派",
        "input_payload": {},
    })
    assert blocked.status_code == 409
    assert "一层委派" in blocked.json()["detail"]


def test_tool_gateway_authorization_budget_and_idempotency() -> None:
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api, budget_tokens=100)
    work_id = create_work_item(api, goal_id, employee_id)

    call = {
        "employee_service_token": token,
        "goal_run_id": goal_id,
        "work_item_id": work_id,
        "tool_id": "knowledge_base",
        "payload": {"query": "退款政策"},
        "token_cost": 10,
    }

    first = api.post("/api/v1/gateway/tool-calls", json=call)
    assert first.status_code == 200
    assert first.json()["status"] == "executed"
    assert first.json()["duplicate"] is False

    duplicate = api.post("/api/v1/gateway/tool-calls", json=call).json()
    assert duplicate["duplicate"] is True
    assert duplicate["idempotency_key"] == first.json()["idempotency_key"]

    over_budget = api.post("/api/v1/gateway/tool-calls", json={**call, "payload": {"query": "新请求"}, "token_cost": 1000})
    assert over_budget.status_code == 409
    assert "目标预算" in over_budget.json()["detail"]


def test_tool_gateway_approval_lifecycle_and_center_filters(monkeypatch) -> None:
    def fake_request(method: str, url: str, **kwargs) -> httpx.Response:
        request = httpx.Request(method, url)
        return httpx.Response(200, request=request, json={"accepted": True, "external_id": "COMP-001"})

    monkeypatch.setattr("app.services.httpx.request", fake_request)
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api)
    work_id = create_work_item(api, goal_id, employee_id)

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
    api.patch("/api/v1/job-template-versions/jtv-customer-support-v1", json={"tools": [tool["id"]]})

    call = {
        "employee_service_token": token,
        "goal_run_id": goal_id,
        "work_item_id": work_id,
        "tool_id": tool["id"],
        "payload": {"amount": 20},
        "token_cost": 5,
    }

    pending = api.post("/api/v1/gateway/tool-calls", json=call).json()
    assert pending["status"] == "requires_approval"

    approvals = api.get(f"/api/v1/approvals?status=pending&approval_type=tool_call&goal_run_id={goal_id}&assignee=客服主管").json()
    assert approvals[0]["id"] == pending["approval_id"]

    approved = api.post(f"/api/v1/approvals/{pending['approval_id']}/approve", json={
        "decision_by": "客服主管",
        "reason": "金额低且证据完整",
    }).json()
    assert approved["status"] == "approved"

    executed = api.post("/api/v1/gateway/tool-calls", json={**call, "approval_id": pending["approval_id"]}).json()
    assert executed["status"] == "executed"


def test_platform_knowledge_retrieval_enforces_employee_authorization(monkeypatch) -> None:
    def fake_post(url: str, **kwargs) -> httpx.Response:
        request = httpx.Request("POST", url, headers=kwargs.get("headers"))
        return httpx.Response(
            200,
            request=request,
            json={
                "code": 0,
                "data": {
                    "chunks": [{
                        "id": "chunk-refund",
                        "content": "退款条件命中片段",
                        "document_id": "doc-refund",
                        "document_keyword": "refund.md",
                        "kb_id": "support_faq",
                        "similarity": 0.9,
                    }],
                    "doc_aggs": [{"doc_id": "doc-refund", "doc_name": "refund.md"}],
                    "total": 1,
                },
            },
        )

    monkeypatch.setattr("app.services.httpx.post", fake_post)
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api)
    work_id = create_work_item(api, goal_id, employee_id)

    result = api.post("/api/v1/gateway/knowledge/search", json={
        "employee_service_token": token,
        "goal_run_id": goal_id,
        "work_item_id": work_id,
        "knowledge_source_id": "ks-faq",
        "query": "客户退款条件是什么？",
        "top_k": 3,
    })

    assert result.status_code == 200
    assert result.json()["citations"][0]["source_id"] == "ks-faq"

    # 已登记但未绑定到该岗位模板的知识源也必须拒绝。
    secret_source = api.post("/api/v1/knowledge-connections/kc-ragflow-dev/sources", json={
        "external_id": "secret_dataset",
        "display_name": "未授权资料",
    }).json()

    denied = api.post("/api/v1/gateway/knowledge/search", json={
        "employee_service_token": token,
        "goal_run_id": goal_id,
        "work_item_id": work_id,
        "knowledge_source_id": secret_source["id"],
        "query": "未授权资料",
    })
    assert denied.status_code == 409
    assert "未被授权" in denied.json()["detail"]


def test_artifact_creation_and_human_acceptance() -> None:
    api = client()
    employee_id = create_employee(api)
    goal_id = create_goal(api)
    work_id = create_work_item(api, goal_id, employee_id)

    artifact = api.post("/api/v1/artifacts", json={
        "goal_run_id": goal_id,
        "work_item_id": work_id,
        "name": "投诉处理建议",
        "artifact_type": "document",
        "uri": "s3://platform-artifacts/customer-case/T-001.md",
        "requires_acceptance": True,
    })

    assert artifact.status_code == 201
    acceptance = api.post(f"/api/v1/artifacts/{artifact.json()['id']}/acceptance", json={
        "accepted": True,
        "reviewer": "客服主管",
        "business_result": "客户接受处理方案",
    })
    assert acceptance.status_code == 200
    assert acceptance.json()["status"] == "accepted"
