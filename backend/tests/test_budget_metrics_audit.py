"""覆盖预算、业务指标、审计规则和通知告警的后端行为。"""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.fixtures import reset_with_catalog


def client() -> TestClient:
    reset_with_catalog()
    return TestClient(create_app())


def create_employee(api: TestClient) -> str:
    return api.post("/api/v1/digital-employees", json={
        "name": "客服小星",
        "nickname": "小星",
        "avatar_url": "https://example.com/avatar.png",
        "department_id": "dept-customer-service",
        "manager_id": None,
        "job_template_version_id": "jtv-customer-support-v1",
        "notes": "预算测试员工",
    }).json()["id"]


def service_token(api: TestClient, employee_id: str) -> str:
    return api.post(f"/api/v1/digital-employees/{employee_id}/service-token").json()["token"]


def create_goal(api: TestClient, budget_tokens: int = 1000) -> str:
    return api.post("/api/v1/goal-runs", json={
        "title": "处理客户升级投诉",
        "goal_type": "customer_case",
        "description": "整理证据并输出处理建议。",
        "owner": "客服主管",
        "root_responsible": "客服主管",
        "budget_tokens": budget_tokens,
        "policy": {},
    }).json()["id"]


def create_work_item(api: TestClient, goal_id: str, employee_id: str) -> str:
    return api.post("/api/v1/work-items", json={
        "goal_run_id": goal_id,
        "assignee_employee_id": employee_id,
        "title": "整理客户上下文",
        "input_payload": {"ticket_id": "T-001"},
    }).json()["id"]


def call_tool(api: TestClient, token: str, goal_id: str, work_id: str, token_cost: int, payload: dict | None = None) -> TestClient:
    return api.post("/api/v1/gateway/tool-calls", json={
        "employee_service_token": token,
        "goal_run_id": goal_id,
        "work_item_id": work_id,
        "tool_id": "knowledge_base",
        "payload": payload or {"query": "退款政策"},
        "token_cost": token_cost,
    })


def test_organization_quota_blocks_new_work_and_sets_warning() -> None:
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api, budget_tokens=100)
    work_id = create_work_item(api, goal_id, employee_id)

    api.put("/api/v1/quota/organization", json={
        "monthly_token_limit": 10,
        "warning_threshold_percent": 50,
        "over_limit_action": "block_new_work",
    })

    blocked = call_tool(api, token, goal_id, work_id, token_cost=11)
    assert blocked.status_code == 409
    assert "组织配额" in blocked.json()["detail"]
    assert api.get("/api/v1/quota/organization").json()["warning_active"] is True


def test_goal_budget_policies_are_managed_as_first_class_records() -> None:
    api = client()

    policies = api.get("/api/v1/quota/goal-budgets").json()
    customer_policy = next(policy for policy in policies if policy["job_template_version_id"] == "jtv-customer-support-v1")

    updated = api.patch(f"/api/v1/quota/goal-budgets/{customer_policy['id']}", json={
        "default_budget_tokens": 180000,
        "warning_threshold_percent": 70,
        "overage_action": "alert_only",
        "approvers": ["客服主管"],
    })

    assert updated.status_code == 200
    assert updated.json()["default_budget_tokens"] == 180000
    assert updated.json()["warning_threshold_percent"] == 70
    assert api.get("/api/v1/job-template-versions/jtv-customer-support-v1").json()["default_goal_budget_tokens"] == 180000


def test_goal_budget_blocks_dispatch_and_pauses_goal() -> None:
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api, budget_tokens=5)
    work_id = create_work_item(api, goal_id, employee_id)

    blocked = call_tool(api, token, goal_id, work_id, token_cost=10)

    assert blocked.status_code == 409
    assert "目标预算" in blocked.json()["detail"]
    assert api.get(f"/api/v1/goal-runs/{goal_id}").json()["status"] == "paused"
    assert any(item["id"] == f"budget-{goal_id}" for item in api.get("/api/v1/alerts").json())


def test_token_ledger_and_usage_analytics_capture_dimensions() -> None:
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api)
    work_id = create_work_item(api, goal_id, employee_id)

    assert call_tool(api, token, goal_id, work_id, token_cost=12).status_code == 200

    ledger = api.get("/api/v1/usage/token-ledger").json()
    assert ledger[0]["employee_id"] == employee_id
    assert ledger[0]["department_id"] == "dept-customer-service"
    assert ledger[0]["job_template_version_id"] == "jtv-customer-support-v1"

    analytics = api.get("/api/v1/usage/analytics").json()
    assert analytics["total_tokens"] == 12
    assert analytics["by_employee"][employee_id] == 12
    assert analytics["by_goal_run"][goal_id] == 12


def test_metric_definition_binding_and_measurement() -> None:
    api = client()

    metric = api.post("/api/v1/metrics/definitions", json={
        "name": "投诉一次解决率",
        "target_value": ">= 85%",
        "collection_method": "manual",
        "data_source": "客服主管人工复核",
        "review_cycle": "weekly",
    }).json()

    binding = api.put("/api/v1/job-template-versions/jtv-customer-support-v1/metric-bindings", json={
        "metric_definition_ids": [metric["id"]],
    })
    assert binding.status_code == 200

    measurement = api.post("/api/v1/metrics/measurements", json={
        "metric_definition_id": metric["id"],
        "value": "88%",
        "period": "2026-W27",
        "evidence_uri": "s3://metrics/customer-service/week-27.csv",
        "reviewer": "客服主管",
    })
    assert measurement.status_code == 201
    assert measurement.json()["value"] == "88%"

    reports = api.get("/api/v1/reports/template-outcomes").json()
    report = next(item for item in reports if item["template_id"] == "jtv-customer-support-v1")
    assert report["template_role"] == "客服工单协调员工"
    assert report["business_metrics"][0]["actual"] == "88%"


def test_audit_events_are_append_only_and_rules_create_review_tasks() -> None:
    api = client()
    employee_id = create_employee(api)
    token = service_token(api, employee_id)
    goal_id = create_goal(api)
    work_id = create_work_item(api, goal_id, employee_id)
    call_tool(api, token, goal_id, work_id, token_cost=3)

    event = next(item for item in api.get("/api/v1/audit/events").json() if item["event_type"] == "tool_call_executed")
    rule = api.post("/api/v1/audit/rules", json={
        "name": "工具调用复核",
        "event_type": "tool_call_executed",
        "severity": "medium",
        "notification_targets": ["审计负责人"],
        "requires_review": True,
        "escalation_policy": "24 小时未处理升级",
        "retention_days": 365,
    }).json()

    evaluation = api.post(f"/api/v1/audit/rules/{rule['id']}/evaluate/{event['id']}")
    assert evaluation.status_code == 200
    assert evaluation.json()["matched"] is True
    assert evaluation.json()["notifications"] == ["审计负责人"]
    assert evaluation.json()["review_task_id"] is not None
    notifications = api.get("/api/v1/audit/notifications").json()
    assert notifications[0]["event_id"] == event["id"]
    assert notifications[0]["rule_id"] == rule["id"]
    assert notifications[0]["receiver"] == "审计负责人"
    assert any(item["id"].startswith("audit-") for item in api.get("/api/v1/alerts").json())

    patched_rule = api.patch(f"/api/v1/audit/rules/{rule['id']}", json={"enabled": False})
    assert patched_rule.status_code == 200
    assert patched_rule.json()["enabled"] is False

    disposition = api.post(f"/api/v1/audit/events/{event['id']}/dispositions", json={
        "status": "handled",
        "note": "已复核工具调用证据。",
        "reviewer": "审计负责人",
    })
    assert disposition.status_code == 200
    assert disposition.json()["dispositions"][0]["status"] == "handled"

    export_event = api.post("/api/v1/audit/events", json={
        "event_type": "sensitive_operation",
        "payload": {"subtype": "audit_export_masked", "reason": "例行复核"},
    })
    assert export_event.status_code == 201
