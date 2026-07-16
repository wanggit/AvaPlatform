"""关系型状态持久化细节测试。"""

from app.db.relational_state import _save_digital_employees


class _CaptureConnection:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def execute(self, query: str, _params=()):
        self.queries.append(query)


def test_save_digital_employees_writes_created_at_explicitly():
    """评测临时员工也必须能在旧库结构中稳定持久化。"""
    connection = _CaptureConnection()

    _save_digital_employees(connection, {
        "emp-test": {
            "id": "emp-test",
            "department_id": "dept-test",
            "job_template_version_id": "jtv-test",
            "name": "评测员工",
            "avatar_url": "",
            "lifecycle_state": "active",
            "runtime_state": "healthy",
            "availability_state": "idle",
            "rollout": {"job_id": "rollout-test", "status": "passed", "current_step": "completed"},
        },
    })

    first_insert = connection.queries[0]
    assert "created_at" in first_insert
    assert "now()" in first_insert
