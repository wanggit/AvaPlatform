"""覆盖岗位模板评测发布和数字员工生命周期规则。"""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.fixtures import reset_with_catalog


def client() -> TestClient:
    reset_with_catalog()
    return TestClient(create_app())


def employee_payload(template_id: str = "jtv-customer-support-v1") -> dict:
    return {
        "name": "客服小星",
        "nickname": "小星",
        "avatar_url": "https://example.com/avatar.png",
        "department_id": "dept-customer-service",
        "manager_id": None,
        "job_template_version_id": template_id,
        "notes": "测试员工",
    }


def test_create_employee_requires_published_and_passed_template() -> None:
    api = client()

    response = api.post("/api/v1/digital-employees", json=employee_payload("jtv-sales-draft-v1"))

    assert response.status_code == 409
    assert "已发布" in response.json()["detail"]


def test_department_crud_and_reference_delete_guard() -> None:
    api = client()

    departments = api.get("/api/v1/departments").json()
    customer_service = next(item for item in departments if item["id"] == "dept-customer-service")
    assert customer_service["template_count"] > 0

    blocked = api.delete("/api/v1/departments/dept-customer-service")
    assert blocked.status_code == 409

    created = api.post("/api/v1/departments", json={
        "name": "法务部",
        "description": "负责合同与合规协同。",
    })
    assert created.status_code == 201
    department_id = created.json()["id"]

    patched = api.patch(f"/api/v1/departments/{department_id}", json={"description": "负责合同、合规与风控协同。"})
    assert patched.status_code == 200
    assert patched.json()["description"] == "负责合同、合规与风控协同。"

    deleted = api.delete(f"/api/v1/departments/{department_id}")
    assert deleted.status_code == 204


def test_create_employee_starts_rollout_job() -> None:
    api = client()

    response = api.post("/api/v1/digital-employees", json=employee_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["lifecycle_state"] == "provisioning"
    assert body["runtime_state"] == "not_started"
    assert body["availability_state"] == "unavailable"
    assert body["rollout"]["current_step"] == "profile_render"
    assert body["rollout"]["status"] == "running"


def test_create_employee_accepts_avatar_alias() -> None:
    api = client()
    payload = employee_payload()
    payload["avatar"] = payload.pop("avatar_url")

    response = api.post("/api/v1/digital-employees", json=payload)

    assert response.status_code == 201
    assert response.json()["avatar_url"] == "https://example.com/avatar.png"


def test_activate_employee_computes_availability() -> None:
    api = client()
    employee_id = api.post("/api/v1/digital-employees", json=employee_payload()).json()["id"]

    response = api.post(f"/api/v1/digital-employees/{employee_id}/activate")

    assert response.status_code == 200
    body = response.json()
    assert body["lifecycle_state"] == "active"
    assert body["runtime_state"] == "healthy"
    assert body["availability_state"] == "idle"


def test_runtime_unhealthy_makes_active_employee_unavailable() -> None:
    api = client()
    employee_id = api.post("/api/v1/digital-employees", json=employee_payload()).json()["id"]
    api.post(f"/api/v1/digital-employees/{employee_id}/activate")

    response = api.patch(f"/api/v1/digital-employees/{employee_id}/runtime", json={"runtime_state": "unhealthy"})

    assert response.status_code == 200
    assert response.json()["availability_state"] == "unavailable"


def test_manager_assignment_updates_employee_record() -> None:
    api = client()
    manager_id = api.post("/api/v1/digital-employees", json={**employee_payload(), "name": "客服组长"}).json()["id"]
    employee_id = api.post("/api/v1/digital-employees", json=employee_payload()).json()["id"]

    response = api.patch(f"/api/v1/digital-employees/{employee_id}/manager", json={"manager_id": manager_id})

    assert response.status_code == 200
    assert response.json()["manager_id"] == manager_id
