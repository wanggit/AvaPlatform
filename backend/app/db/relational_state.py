from __future__ import annotations

"""把内存态领域对象映射到 PostgreSQL 关系表，支撑正式持久化。"""

import json
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.db.init import DEFAULT_ORGANIZATION_ID, create_runtime_support_tables, ensure_default_organization
from app.models.domain import uuid_pk


MANAGED_TABLES = [
    "review_tasks",
    "audit_rule_evaluations",
    "artifact_acceptances",
    "business_outcome_metric_measurements",
    "token_ledger_entries",
    "tool_idempotency_results",
    "artifacts",
    "approval_requests",
    "execution_graph_edges",
    "work_items",
    "goal_runs",
    "employee_service_tokens",
    "instance_smoke_tests",
    "employee_rollout_jobs",
    "audit_events",
    "digital_employees",
    "job_template_metric_bindings",
    "goal_budget_policies",
    "business_outcome_metric_definitions",
    "retrieval_policies",
    "job_template_tool_bindings",
    "job_template_skill_bindings",
    "template_evaluation_cases",
    "template_evaluations",
    "job_template_versions",
    "job_templates",
    "tool_idempotency_policies",
    "tool_versions",
    "tools",
    "skill_versions",
    "skill_packages",
    "knowledge_sources",
    "knowledge_connections",
    "model_configurations",
    "credentials",
    "audit_rules",
    "organization_quota_policies",
    "departments",
]


def load_relational_state() -> dict[str, Any] | None:
    create_runtime_support_tables()
    ensure_default_organization()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        payload = _empty_payload()
        payload["departments"] = _load_departments(connection)
        payload["credentials"], payload["secret_values"] = _load_credentials(connection)
        payload["model_configurations"] = _load_model_configurations(connection)
        payload["skill_packages"] = _load_skill_packages(connection)
        payload["tools"] = _load_tools(connection)
        payload["knowledge_connections"] = _load_knowledge_connections(connection)
        payload["knowledge_sources"] = _load_knowledge_sources(connection)
        payload["template_versions"] = _load_job_template_versions(connection)
        payload["goal_budget_policies"] = _load_goal_budget_policies(connection)
        payload["metric_definitions"] = _load_metric_definitions(connection)
        payload["template_metric_bindings"] = _load_template_metric_bindings(connection)
        payload["audit_rules"] = _load_audit_rules(connection)
        payload["organization_quota"] = _load_organization_quota(connection)
        payload["employees"] = _load_digital_employees(connection)
        payload["employee_service_tokens"] = _load_employee_service_tokens(connection)
        payload["goal_runs"] = _load_goal_runs(connection)
        payload["work_items"] = _load_work_items(connection)
        payload["execution_edges"] = _load_execution_edges(connection)
        payload["approvals"] = _load_approvals(connection)
        payload["artifacts"] = _load_artifacts(connection)
        payload["artifact_acceptances"] = _load_artifact_acceptances(connection)
        payload["token_ledger"] = _load_token_ledger(connection)
        payload["metric_measurements"] = _load_metric_measurements(connection)
        payload["audit_events"] = _load_audit_events(connection)
        payload["audit_rule_evaluations"] = _load_audit_rule_evaluations(connection)
        payload["review_tasks"] = _load_review_tasks(connection)
        payload["idempotency_results"] = _load_tool_idempotency_results(connection)

    has_rows = any(
        payload[key]
        for key in (
            "departments",
            "credentials",
            "model_configurations",
            "skill_packages",
            "tools",
            "knowledge_connections",
            "knowledge_sources",
            "template_versions",
            "employees",
            "goal_runs",
            "work_items",
            "approvals",
            "artifacts",
            "goal_budget_policies",
            "metric_definitions",
            "audit_events",
            "audit_rules",
        )
    )
    return payload if has_rows or payload["organization_quota"] else None


def save_relational_state(payload: dict[str, Any]) -> None:
    create_runtime_support_tables()
    ensure_default_organization()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        _clear_managed_tables(connection)
        _save_departments(connection, payload.get("departments", {}))
        _save_credentials(connection, payload.get("credentials", {}), payload.get("secret_values", {}))
        _save_model_configurations(connection, payload.get("model_configurations", {}))
        _save_skill_packages(connection, payload.get("skill_packages", {}))
        _save_tools(connection, payload.get("tools", {}))
        _save_knowledge(connection, payload.get("knowledge_connections", {}), payload.get("knowledge_sources", {}))
        _save_job_templates(
            connection,
            payload.get("template_versions", {}),
            payload.get("template_skill_bindings", {}),
        )
        _save_goal_budget_policies(connection, payload.get("goal_budget_policies", {}))
        _save_metric_definitions(connection, payload.get("metric_definitions", {}))
        _save_template_metric_bindings(connection, payload.get("template_metric_bindings", {}))
        _save_audit_rules(connection, payload.get("audit_rules", {}))
        _save_organization_quota(connection, payload.get("organization_quota"))
        _save_digital_employees(connection, payload.get("employees", {}))
        _save_employee_service_tokens(connection, payload.get("employee_service_tokens", {}))
        _save_goal_runs(connection, payload.get("goal_runs", {}))
        _save_work_items(connection, payload.get("work_items", {}))
        _save_execution_edges(connection, payload.get("execution_edges", {}))
        _save_approvals(connection, payload.get("approvals", {}))
        _save_artifacts(connection, payload.get("artifacts", {}))
        _save_artifact_acceptances(connection, payload.get("artifact_acceptances", {}))
        _save_token_ledger(connection, payload.get("token_ledger", []))
        _save_metric_measurements(connection, payload.get("metric_measurements", {}))
        _save_audit_events(connection, payload.get("audit_events", []))
        _save_audit_rule_evaluations(connection, payload.get("audit_rule_evaluations", {}))
        _save_review_tasks(connection, payload.get("review_tasks", {}))
        _save_tool_idempotency_results(connection, payload.get("idempotency_results", {}))
        connection.commit()


def _empty_payload() -> dict[str, Any]:
    return {
        "secret_values": {},
        "credentials": {},
        "model_configurations": {},
        "skill_packages": {},
        "template_skill_bindings": {},
        "tools": {},
        "knowledge_connections": {},
        "knowledge_sources": {},
        "goal_runs": {},
        "work_items": {},
        "execution_edges": {},
        "approvals": {},
        "artifacts": {},
        "artifact_acceptances": {},
        "employee_service_tokens": {},
        "idempotency_results": {},
        "organization_quota": None,
        "goal_budget_policies": {},
        "token_ledger": [],
        "metric_definitions": {},
        "template_metric_bindings": {},
        "metric_measurements": {},
        "audit_events": [],
        "audit_rules": {},
        "audit_rule_evaluations": {},
        "review_tasks": {},
        "departments": {},
        "template_versions": {},
        "employees": {},
    }


def _clear_managed_tables(connection: psycopg.Connection) -> None:
    for table in MANAGED_TABLES:
        connection.execute(f"DELETE FROM {table}")


def _load_departments(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute("SELECT id, name, description FROM departments ORDER BY name").fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "employee_count": 0,
            "template_count": 0,
        }
        for row in rows
    }


def _save_departments(connection: psycopg.Connection, departments: dict[str, dict[str, Any]]) -> None:
    for department in departments.values():
        connection.execute(
            """
            INSERT INTO departments (id, organization_id, name, description)
            VALUES (%s, %s, %s, %s)
            """,
            (department["id"], DEFAULT_ORGANIZATION_ID, department["name"], department.get("description")),
        )


def _load_credentials(connection: psycopg.Connection) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    rows = connection.execute(
        "SELECT id, name, owner, type, encrypted_value, masked_value FROM credentials ORDER BY name"
    ).fetchall()
    credentials: dict[str, dict[str, Any]] = {}
    secret_values: dict[str, str] = {}
    for row in rows:
        secret_ref = f"secret-{row['id']}"
        secret_values[secret_ref] = row["encrypted_value"]
        owner_type = "integration" if row["owner"].lower() == "ragflow" else "platform"
        owner_id = "ragflow" if owner_type == "integration" else "platform"
        credentials[row["id"]] = {
            "id": row["id"],
            "name": row["name"],
            "owner_type": owner_type,
            "owner_id": owner_id,
            "owner_name": row["owner"],
            "secret_ref": secret_ref,
            "secret_mask": row["masked_value"],
            "description": None,
        }
    return credentials, secret_values


def _save_credentials(
    connection: psycopg.Connection,
    credentials: dict[str, dict[str, Any]],
    secret_values: dict[str, str],
) -> None:
    for credential in credentials.values():
        secret_value = secret_values.get(credential["secret_ref"], credential["secret_ref"])
        connection.execute(
            """
            INSERT INTO credentials (id, name, owner, type, encrypted_value, masked_value, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                credential["id"],
                credential["name"],
                credential.get("owner_name") or credential.get("owner_id") or "Platform",
                "api_key",
                secret_value,
                credential["secret_mask"],
                "active",
            ),
        )


def _load_model_configurations(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, model_type, provider, base_url, api_key, model_name,
               context_window, status, metadata_json
        FROM model_configurations
        ORDER BY name
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "model_type": row["model_type"],
            "provider": row["provider"],
            "base_url": row["base_url"],
            "api_key": row["api_key"],
            "model_name": row["model_name"],
            "context_window": row["context_window"],
            "metadata": row["metadata_json"] or {},
            "enabled": row["status"] == "active",
            "test_status": "not_tested",
            "last_test_message": None,
        }
        for row in rows
    }


def _save_model_configurations(connection: psycopg.Connection, models: dict[str, dict[str, Any]]) -> None:
    for model in models.values():
        connection.execute(
            """
            INSERT INTO model_configurations (
                id, name, model_type, provider, base_url, api_key, model_name,
                context_window, status, metadata_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                model["id"],
                model["name"],
                model["model_type"],
                model["provider"],
                model["base_url"],
                model["api_key"],
                model["model_name"],
                model["context_window"],
                "active" if model.get("enabled", True) else "disabled",
                Jsonb(model.get("metadata", {})),
            ),
        )


def _load_skill_packages(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT sp.id, sp.name, sp.description, sv.version, sv.zip_object_key, sv.entry_file, sv.status
        FROM skill_packages sp
        JOIN skill_versions sv ON sv.skill_package_id = sp.id
        ORDER BY sp.name
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "version": row["version"],
            "package_file_name": row["zip_object_key"],
            "status": row["status"],
            "manifest": {"entry_file": row["entry_file"]},
            "description": row["description"],
        }
        for row in rows
    }


def _save_skill_packages(connection: psycopg.Connection, skills: dict[str, dict[str, Any]]) -> None:
    for skill in skills.values():
        manifest = skill.get("manifest") or {}
        connection.execute(
            """
            INSERT INTO skill_packages (id, name, display_name, category, description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                skill["id"],
                skill["name"],
                manifest.get("display_name") or skill["name"],
                manifest.get("category") or "通用",
                skill.get("description"),
            ),
        )
        connection.execute(
            """
            INSERT INTO skill_versions (id, skill_package_id, version, zip_object_key, entry_file, status, checksum, published_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CASE WHEN %s = 'published' THEN now() ELSE NULL END)
            """,
            (
                f"{skill['id']}:{skill['version']}",
                skill["id"],
                skill["version"],
                skill["package_file_name"],
                manifest.get("entry_file") or "SKILL.md",
                skill.get("status", "draft"),
                manifest.get("checksum"),
                skill.get("status", "draft"),
            ),
        )


def _load_tools(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT t.id, t.name, t.managed_by, t.integration_type, t.status,
               tv.endpoint_config, tv.schema_config, tv.risk_level, tv.read_write,
               tv.credential_id, tv.requires_approval, tv.audit_required, tv.default_constraints,
               tip.key_strategy
        FROM tools t
        JOIN tool_versions tv ON tv.tool_id = t.id
        LEFT JOIN tool_idempotency_policies tip ON tip.tool_version_id = tv.id
        ORDER BY t.name
        """
    ).fetchall()
    tools: dict[str, dict[str, Any]] = {}
    for row in rows:
        endpoint = row["endpoint_config"] or {}
        schema = row["schema_config"] or {}
        kind = "business"
        tools[row["id"]] = {
            "id": row["id"],
            "kind": kind,
            "name": row["name"],
            "category": None,
            "access_shape": endpoint.get("access_shape"),
            "endpoint_url": endpoint.get("endpoint_url"),
            "method": endpoint.get("method"),
            "request_schema": schema.get("request") or {},
            "response_schema": schema.get("response") or {},
            "owner": None,
            "credential_id": row["credential_id"],
            "hermes_registry_id": endpoint.get("hermes_registry_id"),
            "read_write": row["read_write"],
            "default_constraints": row["default_constraints"] or [],
            "risk_level": row["risk_level"],
            "audit_required": row["audit_required"],
            "approval_required": row["requires_approval"],
            "idempotency_policy": row["key_strategy"],
            "lifecycle_status": row["status"],
            "test_status": "not_tested",
            "last_test_message": None,
        }
    return tools


def _save_tools(connection: psycopg.Connection, tools: dict[str, dict[str, Any]]) -> None:
    for tool in tools.values():
        connection.execute(
            """
            INSERT INTO tools (id, name, display_name, managed_by, integration_type, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                tool["id"],
                tool["name"],
                tool["name"],
                "platform",
                tool.get("access_shape") or tool["kind"],
                tool.get("lifecycle_status", "draft"),
            ),
        )
        version_id = f"{tool['id']}:current"
        connection.execute(
            """
            INSERT INTO tool_versions (
                id, tool_id, version, endpoint_config, schema_config, risk_level, read_write,
                credential_id, requires_approval, audit_required, default_constraints
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                version_id,
                tool["id"],
                "current",
                Jsonb({
                    "access_shape": tool.get("access_shape"),
                    "endpoint_url": tool.get("endpoint_url"),
                    "method": tool.get("method"),
                    "hermes_registry_id": tool.get("hermes_registry_id"),
                }),
                Jsonb({"request": tool.get("request_schema") or {}, "response": tool.get("response_schema") or {}}),
                tool["risk_level"],
                tool.get("read_write") or "read_only",
                tool.get("credential_id"),
                bool(tool.get("approval_required")),
                bool(tool.get("audit_required")),
                Jsonb(tool.get("default_constraints") or []),
            ),
        )
        if tool.get("idempotency_policy"):
            connection.execute(
                """
                INSERT INTO tool_idempotency_policies (
                    id, tool_version_id, key_strategy, key_fields, duplicate_action, external_object_field
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    f"{tool['id']}:idempotency",
                    version_id,
                    tool["idempotency_policy"],
                    Jsonb([]),
                    "return_existing_result",
                    None,
                ),
            )


def _load_knowledge_connections(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        "SELECT id, provider, name, base_url, credential_id, status FROM knowledge_connections ORDER BY name"
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "provider": row["provider"],
            "name": row["name"],
            "base_url": row["base_url"],
            "credential_id": row["credential_id"],
            "health_status": row["status"] if row["status"] in {"unknown", "healthy", "unhealthy"} else "unknown",
            "sync_metadata": {},
        }
        for row in rows
    }


def _load_knowledge_sources(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, connection_id, name, category, description, external_dataset_id,
               external_dataset_name, document_count, chunk_count, status
        FROM knowledge_sources
        ORDER BY name
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "connection_id": row["connection_id"],
            "external_id": row["external_dataset_id"],
            "display_name": row["name"],
            "source_type": "dataset",
            "authorization_scope": [row["category"]],
            "retrieval_settings": {"description": row["description"]} if row["description"] else {},
            "status": row["status"],
            "sync_metadata": {
                "document_count": row["document_count"],
                "chunk_count": row["chunk_count"],
            },
        }
        for row in rows
    }


def _save_knowledge(
    connection: psycopg.Connection,
    connections: dict[str, dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> None:
    for item in connections.values():
        connection.execute(
            """
            INSERT INTO knowledge_connections (id, provider, name, base_url, credential_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                item["id"],
                item.get("provider", "ragflow"),
                item["name"],
                item["base_url"],
                item["credential_id"],
                item.get("health_status", "unknown"),
            ),
        )
    for source in sources.values():
        metadata = source.get("sync_metadata") or {}
        connection.execute(
            """
            INSERT INTO knowledge_sources (
                id, connection_id, name, category, description, external_dataset_id,
                external_dataset_name, document_count, chunk_count, status, sync_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                source["id"],
                source["connection_id"],
                source["display_name"],
                (source.get("authorization_scope") or ["通用"])[0],
                source.get("retrieval_settings", {}).get("description"),
                source["external_id"],
                source["display_name"],
                int(metadata.get("document_count") or 0),
                int(metadata.get("chunk_count") or 0),
                source.get("status", "active"),
                source.get("status", "active"),
            ),
        )


def _load_job_template_versions(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT jtv.id, jt.role, jt.grade, jt.is_pilot, jt.pilot_scenario,
               jtv.department_id, jtv.model_config_id, jtv.version, jtv.status,
               jtv.description, jtv.system_prompt, jtv.max_goal_risk_level,
               jtv.default_goal_budget_tokens, jtv.red_lines,
               te.status AS evaluation_status, te.score, te.evaluator, te.summary
        FROM job_template_versions jtv
        JOIN job_templates jt ON jt.id = jtv.job_template_id
        LEFT JOIN template_evaluations te ON te.job_template_version_id = jtv.id
        ORDER BY jt.role, jtv.version
        """
    ).fetchall()
    skill_bindings = _load_template_skill_ids(connection)
    tool_bindings = _load_template_tool_ids(connection)
    knowledge_bindings = _load_template_knowledge_source_ids(connection)
    metric_bindings = _load_template_metric_dicts(connection)
    evaluation_cases = _load_template_evaluation_cases(connection)
    versions: dict[str, dict[str, Any]] = {}
    for row in rows:
        eval_id = f"eval-{row['id']}"
        cases = evaluation_cases.get(eval_id, [])
        versions[row["id"]] = {
            "id": row["id"],
            "role": row["role"],
            "version": row["version"],
            "grade": row["grade"],
            "department_id": row["department_id"],
            "model_config_id": row["model_config_id"],
            "description": row["description"],
            "system_prompt": row["system_prompt"],
            "max_goal_risk_level": row["max_goal_risk_level"],
            "default_goal_budget_tokens": row["default_goal_budget_tokens"],
            "skills": skill_bindings.get(row["id"], []),
            "tools": tool_bindings.get(row["id"], []),
            "knowledge_sources": knowledge_bindings.get(row["id"], []),
            "red_lines": row["red_lines"] or [],
            "metric_bindings": metric_bindings.get(row["id"], []),
            "is_pilot": row["is_pilot"],
            "pilot_scenario": row["pilot_scenario"],
            "status": row["status"],
            "evaluation": {
                "job_template_version_id": row["id"],
                "status": row["evaluation_status"] or "not_evaluated",
                "score": row["score"] or 0,
                "case_count": len(cases),
                "passed_case_count": sum(1 for c in cases if c.get("status") == "passed"),
                "evaluator": row["evaluator"],
                "summary": row["summary"],
                "cases": cases,
            },
        }
    return versions


def _load_template_skill_ids(connection: psycopg.Connection) -> dict[str, list[str]]:
    rows = connection.execute(
        """
        SELECT jtsb.job_template_version_id, sv.skill_package_id
        FROM job_template_skill_bindings jtsb
        JOIN skill_versions sv ON sv.id = jtsb.skill_version_id
        ORDER BY jtsb.job_template_version_id, sv.skill_package_id
        """
    ).fetchall()
    return _group_ids(rows, "job_template_version_id", "skill_package_id")


def _load_template_tool_ids(connection: psycopg.Connection) -> dict[str, list[str]]:
    rows = connection.execute(
        """
        SELECT jttb.job_template_version_id, tv.tool_id
        FROM job_template_tool_bindings jttb
        JOIN tool_versions tv ON tv.id = jttb.tool_version_id
        ORDER BY jttb.job_template_version_id, tv.tool_id
        """
    ).fetchall()
    return _group_ids(rows, "job_template_version_id", "tool_id")


def _load_template_knowledge_source_ids(connection: psycopg.Connection) -> dict[str, list[str]]:
    rows = connection.execute(
        """
        SELECT job_template_version_id, knowledge_source_id
        FROM retrieval_policies
        ORDER BY job_template_version_id, knowledge_source_id
        """
    ).fetchall()
    return _group_ids(rows, "job_template_version_id", "knowledge_source_id")


def _load_template_metric_dicts(connection: psycopg.Connection) -> dict[str, list[dict[str, Any]]]:
    rows = connection.execute(
        """
        SELECT jtmb.job_template_version_id, bomd.id, bomd.name, jtmb.target_value,
               bomd.collection_method, bomd.source, bomd.review_period
        FROM job_template_metric_bindings jtmb
        JOIN business_outcome_metric_definitions bomd ON bomd.id = jtmb.metric_definition_id
        ORDER BY jtmb.job_template_version_id, bomd.name
        """
    ).fetchall()
    bindings: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        bindings.setdefault(row["job_template_version_id"], []).append({
            "id": row["id"],
            "name": row["name"],
            "target_value": row["target_value"],
            "collection_method": row["collection_method"],
            "data_source": row["source"],
            "review_cycle": row["review_period"] or "",
        })
    return bindings


def _load_template_evaluation_cases(connection: psycopg.Connection) -> dict[str, list[dict[str, Any]]]:
    rows = connection.execute(
        """
        SELECT id, evaluation_id, title, input_payload, expected_result,
               actual_result, assertions, status, failure_reason
        FROM template_evaluation_cases
        ORDER BY evaluation_id, id
        """
    ).fetchall()
    cases_by_eval: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        cases_by_eval.setdefault(row["evaluation_id"], []).append({
            "id": row["id"],
            "title": row["title"],
            "input_payload": row["input_payload"] or {},
            "expected_result": row["expected_result"],
            "actual_result": row["actual_result"],
            "assertions": row["assertions"] or [],
            "status": row["status"],
            "failure_reason": row["failure_reason"],
        })
    return cases_by_eval


def _group_ids(rows: list[dict[str, Any]], parent_key: str, child_key: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row[parent_key], []).append(row[child_key])
    return grouped


def _save_job_templates(
    connection: psycopg.Connection,
    versions: dict[str, dict[str, Any]],
    skill_bindings: dict[str, dict[str, Any]],
) -> None:
    for version in versions.values():
        template_id = f"jt-{version['id']}"
        connection.execute(
            """
            INSERT INTO job_templates (id, organization_id, role, grade, is_pilot, pilot_scenario, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            """,
            (
                template_id,
                DEFAULT_ORGANIZATION_ID,
                version["role"],
                version["grade"],
                bool(version.get("is_pilot")),
                version.get("pilot_scenario"),
                version.get("status", "draft"),
            ),
        )
        connection.execute(
            """
            INSERT INTO job_template_versions (
                id, job_template_id, department_id, model_config_id, version, status,
                description, system_prompt, max_goal_risk_level, default_goal_budget_tokens, red_lines
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                version["id"],
                template_id,
                version.get("department_id"),
                version["model_config_id"],
                version["version"],
                version.get("status", "draft"),
                version["description"],
                version["system_prompt"],
                version.get("max_goal_risk_level", "L2"),
                version.get("default_goal_budget_tokens", 200_000),
                Jsonb(version.get("red_lines") or []),
            ),
        )
        evaluation = version.get("evaluation") or {}
        eval_id = uuid_pk()
        connection.execute(
            """
            INSERT INTO template_evaluations (
                id, job_template_version_id, status, score, evaluator, summary, evaluated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, now())
            """,
            (
                eval_id,
                version["id"],
                evaluation.get("status", "not_evaluated"),
                int(evaluation.get("score") or 0),
                evaluation.get("evaluator"),
                evaluation.get("summary"),
            ),
        )
        for case in evaluation.get("cases") or []:
            connection.execute(
                """
                INSERT INTO template_evaluation_cases (
                    id, evaluation_id, title, input_payload, expected_result,
                    actual_result, assertions, status, failure_reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case["id"],
                    eval_id,
                    case["title"],
                    Jsonb(case.get("input_payload") or {}),
                    case["expected_result"],
                    case.get("actual_result"),
                    Jsonb(case.get("assertions") or []),
                    case.get("status", "not_evaluated"),
                    case.get("failure_reason"),
                ),
            )
        for skill_id in version.get("skills") or skill_bindings.get(version["id"], {}).get("skill_package_ids", []):
            skill_version_id = _current_skill_version_id(connection, skill_id)
            if not skill_version_id:
                continue
            connection.execute(
                """
                INSERT INTO job_template_skill_bindings (id, job_template_version_id, skill_version_id)
                VALUES (%s, %s, %s)
                """,
                (uuid_pk(), version["id"], skill_version_id),
            )
        for tool_id in version.get("tools") or []:
            tool_version_id = _current_tool_version_id(connection, tool_id)
            if not tool_version_id:
                continue
            connection.execute(
                """
                INSERT INTO job_template_tool_bindings (
                    id, job_template_version_id, tool_version_id, entitlement_config
                )
                VALUES (%s, %s, %s, %s)
                """,
                (uuid_pk(), version["id"], tool_version_id, Jsonb({})),
            )
        for source_id in version.get("knowledge_sources") or []:
            connection.execute(
                """
                INSERT INTO retrieval_policies (
                    id, job_template_version_id, knowledge_source_id, top_k, score_threshold, citation_required
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (uuid_pk(), version["id"], source_id, 5, None, True),
            )


def _current_skill_version_id(connection: psycopg.Connection, skill_id: str) -> str | None:
    row = connection.execute(
        """
        SELECT id FROM skill_versions
        WHERE skill_package_id = %s
        ORDER BY published_at DESC NULLS LAST, version DESC
        LIMIT 1
        """,
        (skill_id,),
    ).fetchone()
    return row["id"] if row else None


def _current_tool_version_id(connection: psycopg.Connection, tool_id: str) -> str | None:
    row = connection.execute(
        """
        SELECT id FROM tool_versions
        WHERE tool_id = %s
        ORDER BY version DESC
        LIMIT 1
        """,
        (tool_id,),
        ).fetchone()
    return row["id"] if row else None


def _load_audit_rules(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, description, event_types, output_severity, receivers,
               review_required, retention_days, enabled
        FROM audit_rules
        ORDER BY name
        """
    ).fetchall()
    rules: dict[str, dict[str, Any]] = {}
    for row in rows:
        event_types = row["event_types"] or ["sensitive_operation"]
        rules[row["id"]] = {
            "id": row["id"],
            "name": row["name"],
            "event_type": event_types[0],
            "severity": row["output_severity"],
            "notification_targets": row["receivers"] or [],
            "requires_review": row["review_required"],
            "escalation_policy": row["description"],
            "retention_days": int(row["retention_days"]),
            "enabled": row["enabled"],
        }
    return rules


def _save_audit_rules(connection: psycopg.Connection, rules: dict[str, dict[str, Any]]) -> None:
    for rule in rules.values():
        connection.execute(
            """
            INSERT INTO audit_rules (
                id, name, description, version, event_types, condition_summary, output_severity,
                notify, receivers, review_required, kpi_affecting, retention_days, enabled
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                rule["id"],
                rule["name"],
                rule.get("escalation_policy"),
                "1",
                Jsonb([rule["event_type"]]),
                Jsonb([f"event_type = {rule['event_type']}"]),
                rule.get("severity", "medium"),
                bool(rule.get("notification_targets")),
                Jsonb(rule.get("notification_targets") or []),
                bool(rule.get("requires_review")),
                False,
                str(rule.get("retention_days", 365)),
                bool(rule.get("enabled", True)),
            ),
        )


def _load_organization_quota(connection: psycopg.Connection) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT id, daily_token_limit, warning_threshold_percent, enforcement_mode
        FROM organization_quota_policies
        WHERE organization_id = %s
        LIMIT 1
        """,
        (DEFAULT_ORGANIZATION_ID,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "monthly_token_limit": row["daily_token_limit"],
        "warning_threshold_percent": row["warning_threshold_percent"],
        "over_limit_action": row["enforcement_mode"],
        "used_tokens": 0,
        "warning_active": False,
    }


def _save_organization_quota(connection: psycopg.Connection, quota: dict[str, Any] | None) -> None:
    if not quota:
        return
    connection.execute(
        """
        INSERT INTO organization_quota_policies (
            id, organization_id, daily_token_limit, warning_threshold_percent,
            enforcement_mode, blocked_data_plane_calls, allowed_control_plane_actions
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            quota["id"],
            DEFAULT_ORGANIZATION_ID,
            quota["monthly_token_limit"],
            quota["warning_threshold_percent"],
            quota.get("over_limit_action", "block_new_work"),
            Jsonb(["模型调用", "工具写入", "知识检索"]),
            Jsonb(["查看", "审批", "停用员工"]),
        ),
    )


def _load_goal_budget_policies(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, job_template_version_id, default_budget_tokens,
               warning_threshold_percent, overage_action, approvers
        FROM goal_budget_policies
        ORDER BY job_template_version_id
        """
    ).fetchall()
    return {
        row["job_template_version_id"]: {
            "id": row["id"],
            "job_template_version_id": row["job_template_version_id"],
            "default_budget_tokens": row["default_budget_tokens"],
            "warning_threshold_percent": row["warning_threshold_percent"],
            "overage_action": row["overage_action"],
            "approvers": row["approvers"] or [],
        }
        for row in rows
    }


def _save_goal_budget_policies(connection: psycopg.Connection, policies: dict[str, dict[str, Any]]) -> None:
    for policy in policies.values():
        connection.execute(
            """
            INSERT INTO goal_budget_policies (
                id, job_template_version_id, default_budget_tokens,
                warning_threshold_percent, overage_action, approvers
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                policy["id"],
                policy["job_template_version_id"],
                policy["default_budget_tokens"],
                policy["warning_threshold_percent"],
                policy.get("overage_action", "block_goal_model_calls"),
                Jsonb(policy.get("approvers") or []),
            ),
        )


def _load_metric_definitions(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, name, unit, collection_method, source, review_period
        FROM business_outcome_metric_definitions
        ORDER BY name
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "target_value": row["unit"],
            "collection_method": row["collection_method"],
            "data_source": row["source"],
            "review_cycle": row["review_period"] or "",
        }
        for row in rows
    }


def _save_metric_definitions(connection: psycopg.Connection, metrics: dict[str, dict[str, Any]]) -> None:
    for metric in metrics.values():
        connection.execute(
            """
            INSERT INTO business_outcome_metric_definitions (
                id, name, source, unit, collection_method, review_period
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                metric["id"],
                metric["name"],
                metric["data_source"],
                metric.get("target_value"),
                metric["collection_method"],
                metric["review_cycle"],
            ),
        )


def _load_template_metric_bindings(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT job_template_version_id, metric_definition_id
        FROM job_template_metric_bindings
        ORDER BY job_template_version_id, metric_definition_id
        """
    ).fetchall()
    grouped = _group_ids(rows, "job_template_version_id", "metric_definition_id")
    return {
        version_id: {
            "job_template_version_id": version_id,
            "metric_definition_ids": metric_ids,
        }
        for version_id, metric_ids in grouped.items()
    }


def _save_template_metric_bindings(
    connection: psycopg.Connection,
    bindings: dict[str, dict[str, Any]],
) -> None:
    for binding in bindings.values():
        version_id = binding["job_template_version_id"]
        for metric_id in binding.get("metric_definition_ids") or []:
            connection.execute(
                """
                INSERT INTO job_template_metric_bindings (
                    id, job_template_version_id, metric_definition_id, target_value
                )
                VALUES (%s, %s, %s, %s)
                """,
                (f"jtmb-{version_id}-{metric_id}", version_id, metric_id, None),
            )


def _load_digital_employees(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT de.id, de.name, de.nickname, de.avatar_url, de.department_id, de.manager_id,
               de.job_template_version_id, de.notes, de.lifecycle_state, de.runtime_state,
               de.availability_state, de.max_goal_risk_level, jt.role, jt.grade,
               erj.id AS rollout_job_id, erj.status AS rollout_status, erj.current_step,
               erj.failure_reason, ist.status AS smoke_status, ist.summary AS smoke_summary
        FROM digital_employees de
        JOIN job_template_versions jtv ON jtv.id = de.job_template_version_id
        JOIN job_templates jt ON jt.id = jtv.job_template_id
        LEFT JOIN LATERAL (
            SELECT id, status, current_step, failure_reason
            FROM employee_rollout_jobs
            WHERE employee_id = de.id
            ORDER BY started_at DESC
            LIMIT 1
        ) erj ON true
        LEFT JOIN LATERAL (
            SELECT status, summary
            FROM instance_smoke_tests
            WHERE employee_id = de.id
            ORDER BY tested_at DESC
            LIMIT 1
        ) ist ON true
        ORDER BY de.name
        """
    ).fetchall()
    active_counts = _load_active_goal_counts(connection)
    employees: dict[str, dict[str, Any]] = {}
    for row in rows:
        rollout_status = _api_rollout_status(row["rollout_status"])
        current_step = row["current_step"] or "completed"
        employees[row["id"]] = {
            "id": row["id"],
            "name": row["name"],
            "nickname": row["nickname"],
            "avatar_url": row["avatar_url"],
            "department_id": row["department_id"],
            "manager_id": row["manager_id"],
            "job_template_version_id": row["job_template_version_id"],
            "notes": row["notes"],
            "role": row["role"],
            "grade": row["grade"],
            "lifecycle_state": row["lifecycle_state"],
            "runtime_state": row["runtime_state"],
            "availability_state": row["availability_state"],
            "max_goal_risk_level": row["max_goal_risk_level"],
            "active_goal_count": active_counts.get(row["id"], 0),
            "rollout": {
                "job_id": row["rollout_job_id"] or f"rollout-{row['id']}",
                "current_step": current_step if current_step in {
                    "profile_render", "token_issue", "instance_start", "smoke_test",
                    "pending_activation", "completed", "failed",
                } else "completed",
                "status": rollout_status,
                "last_smoke_test_status": _api_smoke_status(row["smoke_status"]),
                "summary": row["smoke_summary"] or row["failure_reason"] or "员工运行记录已从数据库恢复。",
            },
        }
    return employees


def _load_active_goal_counts(connection: psycopg.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT root_owner_id, count(*) AS active_count
        FROM goal_runs
        WHERE status IN ('running', 'created')
        GROUP BY root_owner_id
        """
    ).fetchall()
    return {row["root_owner_id"]: int(row["active_count"]) for row in rows}


def _api_rollout_status(status: str | None) -> str:
    if status in {"not_started", "running", "passed", "failed", "manual_passed"}:
        return status
    if status in {"completed", "success"}:
        return "passed"
    return "not_started"


def _api_smoke_status(status: str | None) -> str:
    if status in {"not_run", "passed", "failed", "manual_passed"}:
        return status
    return "not_run"


def _save_digital_employees(connection: psycopg.Connection, employees: dict[str, dict[str, Any]]) -> None:
    for employee in employees.values():
        connection.execute(
            """
            INSERT INTO digital_employees (
                id, organization_id, department_id, manager_id, job_template_version_id,
                name, nickname, avatar_url, notes, lifecycle_state, runtime_state,
                availability_state, max_goal_risk_level
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                employee["id"],
                DEFAULT_ORGANIZATION_ID,
                employee["department_id"],
                employee.get("manager_id"),
                employee["job_template_version_id"],
                employee["name"],
                employee.get("nickname"),
                employee["avatar_url"],
                employee.get("notes"),
                employee["lifecycle_state"],
                employee["runtime_state"],
                employee["availability_state"],
                employee.get("max_goal_risk_level", "L2"),
            ),
        )
    for employee in employees.values():
        rollout = employee.get("rollout") or {}
        connection.execute(
            """
            INSERT INTO employee_rollout_jobs (
                id, employee_id, status, current_step, failure_reason, repair_suggestion
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                rollout.get("job_id") or f"rollout-{employee['id']}",
                employee["id"],
                rollout.get("status", "not_started"),
                rollout.get("current_step", "completed"),
                rollout.get("summary") if rollout.get("status") == "failed" else None,
                None,
            ),
        )
        smoke_status = rollout.get("last_smoke_test_status", "not_run")
        if smoke_status != "not_run":
            connection.execute(
                """
                INSERT INTO instance_smoke_tests (
                    id, employee_id, rollout_job_id, status, mode, summary
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    f"smoke-{employee['id']}",
                    employee["id"],
                    rollout.get("job_id") or f"rollout-{employee['id']}",
                    smoke_status,
                    "manual",
                    rollout.get("summary"),
                ),
            )


def _load_employee_service_tokens(connection: psycopg.Connection) -> dict[str, str]:
    rows = connection.execute("SELECT token, employee_id FROM employee_service_tokens").fetchall()
    return {row["token"]: row["employee_id"] for row in rows}


def _save_employee_service_tokens(connection: psycopg.Connection, tokens: dict[str, str]) -> None:
    for token, employee_id in tokens.items():
        connection.execute(
            """
            INSERT INTO employee_service_tokens (token, employee_id)
            VALUES (%s, %s)
            """,
            (token, employee_id),
        )


def _load_goal_runs(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, title, description, root_owner_id, job_template_version_id, status,
               risk_level, budget_tokens, token_used
        FROM goal_runs
        ORDER BY created_at DESC
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "title": row["title"],
            "goal_type": "业务目标",
            "description": row["description"],
            "owner": row["root_owner_id"],
            "root_responsible": row["root_owner_id"],
            "budget_tokens": row["budget_tokens"],
            "policy": {"job_template_version_id": row["job_template_version_id"], "risk_level": row["risk_level"]},
            "status": row["status"],
            "used_tokens": row["token_used"],
        }
        for row in rows
    }


def _save_goal_runs(connection: psycopg.Connection, goals: dict[str, dict[str, Any]]) -> None:
    for goal in goals.values():
        employee_id = goal.get("owner")
        template_id = (goal.get("policy") or {}).get("job_template_version_id") or (goal.get("policy") or {}).get("template_id")
        if not employee_id or not template_id:
            continue
        connection.execute(
            """
            INSERT INTO goal_runs (
                id, title, description, root_owner_id, job_template_version_id, status,
                risk_level, budget_tokens, token_used, budget_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                goal["id"],
                goal["title"],
                goal["description"],
                employee_id,
                template_id,
                goal.get("status", "running"),
                (goal.get("policy") or {}).get("risk_level", "L2"),
                goal["budget_tokens"],
                goal.get("used_tokens", 0),
                "normal",
            ),
        )


def _load_work_items(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, goal_run_id, parent_work_item_id, owner_employee_id, title,
               input_payload, status, trace_context
        FROM work_items
        ORDER BY id
        """
    ).fetchall()
    items: dict[str, dict[str, Any]] = {}
    for row in rows:
        trace_context = row["trace_context"] or {}
        items[row["id"]] = {
            "id": row["id"],
            "goal_run_id": row["goal_run_id"],
            "assignee_employee_id": row["owner_employee_id"],
            "title": row["title"],
            "input_payload": row["input_payload"] or {},
            "parent_work_item_id": row["parent_work_item_id"],
            "budget_tokens": trace_context.get("budget_tokens"),
            "status": row["status"],
            "depth": 1 if row["parent_work_item_id"] else 0,
            "trace_ref": trace_context.get("trace_ref"),
        }
    return items


def _save_work_items(connection: psycopg.Connection, items: dict[str, dict[str, Any]]) -> None:
    for item in items.values():
        connection.execute(
            """
            INSERT INTO work_items (
                id, goal_run_id, parent_work_item_id, owner_employee_id, title,
                input_payload, status, trace_context
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                item["id"],
                item["goal_run_id"],
                item.get("parent_work_item_id"),
                item["assignee_employee_id"],
                item["title"],
                Jsonb(item.get("input_payload") or {}),
                item.get("status", "pending"),
                Jsonb({
                    "trace_ref": item.get("trace_ref"),
                    "budget_tokens": item.get("budget_tokens"),
                    "depth": item.get("depth", 0),
                }),
            ),
        )


def _load_execution_edges(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, goal_run_id, from_work_item_id, to_work_item_id, edge_type
        FROM execution_graph_edges
        ORDER BY id
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "goal_run_id": row["goal_run_id"],
            "parent_work_item_id": row["from_work_item_id"],
            "child_work_item_id": row["to_work_item_id"],
            "relation": "delegated_to",
        }
        for row in rows
    }


def _save_execution_edges(connection: psycopg.Connection, edges: dict[str, dict[str, Any]]) -> None:
    for edge in edges.values():
        connection.execute(
            """
            INSERT INTO execution_graph_edges (
                id, goal_run_id, from_work_item_id, to_work_item_id, edge_type
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                edge["id"],
                edge["goal_run_id"],
                edge["parent_work_item_id"],
                edge["child_work_item_id"],
                edge.get("relation", "delegated_to"),
            ),
        )


def _load_approvals(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, type, status, risk_level, approver, goal_run_id, work_item_id,
               artifact_id, summary, proposed_action, evidence_refs, decision_reason
        FROM approval_requests
        ORDER BY created_at DESC
        """
    ).fetchall()
    approvals: dict[str, dict[str, Any]] = {}
    for row in rows:
        context = _decode_json_text(row["summary"], {})
        evidence_refs = row["evidence_refs"] or []
        approvals[row["id"]] = {
            "id": row["id"],
            "approval_type": row["type"],
            "status": row["status"],
            "risk_level": row["risk_level"],
            "goal_run_id": row["goal_run_id"],
            "work_item_id": row["work_item_id"],
            "tool_id": evidence_refs[0] if evidence_refs else None,
            "artifact_id": row["artifact_id"],
            "assignee": row["approver"],
            "context": context,
            "decision_by": row["proposed_action"] if row["status"] in {"approved", "rejected"} else None,
            "decision_reason": row["decision_reason"],
        }
    return approvals


def _save_approvals(connection: psycopg.Connection, approvals: dict[str, dict[str, Any]]) -> None:
    for approval in approvals.values():
        tool_id = approval.get("tool_id")
        connection.execute(
            """
            INSERT INTO approval_requests (
                id, type, status, risk_level, requester, approver, goal_run_id,
                work_item_id, artifact_id, summary, proposed_action, evidence_refs,
                decision_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                approval["id"],
                approval["approval_type"],
                approval.get("status", "pending"),
                approval.get("risk_level", "medium"),
                "platform",
                approval["assignee"],
                approval.get("goal_run_id"),
                approval.get("work_item_id"),
                approval.get("artifact_id"),
                json.dumps(approval.get("context") or {}, ensure_ascii=False),
                approval.get("decision_by") or "待审批",
                Jsonb([tool_id] if tool_id else []),
                approval.get("decision_reason"),
            ),
        )


def _load_artifacts(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, goal_run_id, produced_by_work_item_id, name, object_key, version,
               validation_status, requires_acceptance
        FROM artifacts
        ORDER BY id
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "goal_run_id": row["goal_run_id"],
            "work_item_id": row["produced_by_work_item_id"],
            "name": row["name"],
            "artifact_type": "document",
            "uri": row["object_key"] or "",
            "requires_acceptance": row["requires_acceptance"],
            "metadata": {},
            "status": row["validation_status"],
            "version": _safe_int(row["version"], 1),
        }
        for row in rows
    }


def _save_artifacts(connection: psycopg.Connection, artifacts: dict[str, dict[str, Any]]) -> None:
    for artifact in artifacts.values():
        connection.execute(
            """
            INSERT INTO artifacts (
                id, goal_run_id, produced_by_work_item_id, name, object_key, version,
                validation_status, requires_acceptance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                artifact["id"],
                artifact["goal_run_id"],
                artifact["work_item_id"],
                artifact["name"],
                artifact.get("uri"),
                str(artifact.get("version", 1)),
                artifact.get("status", "draft"),
                bool(artifact.get("requires_acceptance", True)),
            ),
        )


def _load_artifact_acceptances(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, artifact_id, status, reviewer, business_result_ref, note
        FROM artifact_acceptances
        ORDER BY decided_at DESC
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "artifact_id": row["artifact_id"],
            "status": row["status"],
            "reviewer": row["reviewer"],
            "business_result": row["business_result_ref"],
            "reason": row["note"],
        }
        for row in rows
    }


def _save_artifact_acceptances(connection: psycopg.Connection, acceptances: dict[str, dict[str, Any]]) -> None:
    for acceptance in acceptances.values():
        connection.execute(
            """
            INSERT INTO artifact_acceptances (
                id, artifact_id, status, reviewer, business_result_ref, note
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                acceptance["id"],
                acceptance["artifact_id"],
                acceptance["status"],
                acceptance["reviewer"],
                acceptance.get("business_result"),
                acceptance.get("reason"),
            ),
        )


def _load_token_ledger(connection: psycopg.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, department_id, employee_id, model_config_id, job_template_version_id,
               goal_run_id, work_item_id, purpose, prompt_tokens, completion_tokens,
               total_tokens, request_id
        FROM token_ledger_entries
        ORDER BY occurred_at DESC
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "organization_id": DEFAULT_ORGANIZATION_ID,
            "department_id": row["department_id"],
            "employee_id": row["employee_id"],
            "model_id": row["model_config_id"],
            "job_template_version_id": row["job_template_version_id"],
            "goal_run_id": row["goal_run_id"],
            "work_item_id": row["work_item_id"],
            "usage": row["purpose"],
            "input_tokens": row["prompt_tokens"],
            "output_tokens": row["completion_tokens"],
            "total_tokens": row["total_tokens"],
            "trace_ref": row["request_id"],
        }
        for row in rows
    ]


def _save_token_ledger(connection: psycopg.Connection, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        if not entry.get("model_id"):
            continue
        connection.execute(
            """
            INSERT INTO token_ledger_entries (
                id, goal_run_id, work_item_id, employee_id, department_id,
                model_config_id, job_template_version_id, purpose, prompt_tokens,
                completion_tokens, total_tokens, estimated, request_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry["id"],
                entry.get("goal_run_id"),
                entry.get("work_item_id"),
                entry["employee_id"],
                entry.get("department_id"),
                entry["model_id"],
                entry.get("job_template_version_id"),
                entry["usage"],
                entry.get("input_tokens", 0),
                entry.get("output_tokens", 0),
                entry["total_tokens"],
                True,
                entry.get("trace_ref") or entry["id"],
            ),
        )


def _load_metric_measurements(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, metric_definition_id, measured_value, evidence_refs, collected_by
        FROM business_outcome_metric_measurements
        ORDER BY collected_at DESC
        """
    ).fetchall()
    measurements: dict[str, dict[str, Any]] = {}
    for row in rows:
        evidence = row["evidence_refs"] or []
        measurements[row["id"]] = {
            "id": row["id"],
            "metric_definition_id": row["metric_definition_id"],
            "value": row["measured_value"],
            "period": "",
            "evidence_uri": evidence[0] if evidence else None,
            "reviewer": row["collected_by"],
            "source_trace": evidence[1] if len(evidence) > 1 else None,
        }
    return measurements


def _save_metric_measurements(connection: psycopg.Connection, measurements: dict[str, dict[str, Any]]) -> None:
    for measurement in measurements.values():
        evidence_refs = [
            value for value in (measurement.get("evidence_uri"), measurement.get("source_trace")) if value
        ]
        connection.execute(
            """
            INSERT INTO business_outcome_metric_measurements (
                id, metric_definition_id, measured_value, evidence_refs, collected_by
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                measurement["id"],
                measurement["metric_definition_id"],
                measurement["value"],
                Jsonb(evidence_refs),
                measurement.get("reviewer"),
            ),
        )


def _load_audit_events(connection: psycopg.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, event_type, payload, occurred_at
        FROM audit_events
        ORDER BY occurred_at DESC
        """
    ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        payload = row["payload"] or {}
        dispositions = payload.pop("_dispositions", []) if isinstance(payload, dict) else []
        events.append({
            "id": row["id"],
            "event_type": row["event_type"],
            "payload": payload,
            "dispositions": dispositions,
            "occurred_at": row["occurred_at"],
        })
    return events


def _save_audit_events(connection: psycopg.Connection, events: list[dict[str, Any]]) -> None:
    for event in events:
        payload = dict(event.get("payload") or {})
        if event.get("dispositions"):
            payload["_dispositions"] = event["dispositions"]
        occurred_at = event.get("occurred_at") or datetime.now(timezone.utc)
        connection.execute(
            """
            INSERT INTO audit_events (
                id, event_type, severity, actor_type, actor_id, payload, evidence_refs, occurred_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event["id"],
                event["event_type"],
                "info",
                "platform",
                "platform",
                Jsonb(payload),
                Jsonb([]),
                occurred_at,
            ),
        )


def _load_audit_rule_evaluations(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT are.id, are.audit_event_id, are.audit_rule_id, are.matched, are.actions,
               rt.id AS review_task_id
        FROM audit_rule_evaluations are
        LEFT JOIN review_tasks rt ON rt.audit_event_id = are.audit_event_id
        ORDER BY are.evaluated_at DESC
        """
    ).fetchall()
    return {
        row["id"]: {
            "id": row["id"],
            "audit_event_id": row["audit_event_id"],
            "audit_rule_id": row["audit_rule_id"],
            "matched": row["matched"],
            "notifications": row["actions"] or [],
            "review_task_id": row["review_task_id"],
        }
        for row in rows
    }


def _save_audit_rule_evaluations(connection: psycopg.Connection, evaluations: dict[str, dict[str, Any]]) -> None:
    for evaluation in evaluations.values():
        connection.execute(
            """
            INSERT INTO audit_rule_evaluations (
                id, audit_event_id, audit_rule_id, matched, actions
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                evaluation["id"],
                evaluation["audit_event_id"],
                evaluation["audit_rule_id"],
                evaluation["matched"],
                Jsonb(evaluation.get("notifications") or []),
            ),
        )


def _load_review_tasks(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT id, audit_event_id, owner, status, note
        FROM review_tasks
        ORDER BY created_at DESC
        """
    ).fetchall()
    tasks: dict[str, dict[str, Any]] = {}
    for row in rows:
        note = _decode_json_text(row["note"], {})
        tasks[row["id"]] = {
            "id": row["id"],
            "audit_event_id": row["audit_event_id"] or "",
            "audit_rule_id": note.get("audit_rule_id", ""),
            "assignee": row["owner"],
            "status": "closed" if row["status"] in {"closed", "completed"} else "open",
        }
    return tasks


def _save_review_tasks(connection: psycopg.Connection, tasks: dict[str, dict[str, Any]]) -> None:
    for task in tasks.values():
        connection.execute(
            """
            INSERT INTO review_tasks (id, audit_event_id, owner, status, note)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                task["id"],
                task["audit_event_id"],
                task["assignee"],
                "closed" if task.get("status") == "closed" else "pending",
                json.dumps({"audit_rule_id": task["audit_rule_id"]}, ensure_ascii=False),
            ),
        )


def _load_tool_idempotency_results(connection: psycopg.Connection) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        "SELECT idempotency_key, result_json FROM tool_idempotency_results ORDER BY created_at DESC"
    ).fetchall()
    return {row["idempotency_key"]: row["result_json"] for row in rows}


def _save_tool_idempotency_results(connection: psycopg.Connection, results: dict[str, dict[str, Any]]) -> None:
    for key, result in results.items():
        connection.execute(
            """
            INSERT INTO tool_idempotency_results (idempotency_key, tool_id, result_json)
            VALUES (%s, %s, %s)
            """,
            (key, result.get("tool_id"), Jsonb(result)),
        )


def _decode_json_text(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
