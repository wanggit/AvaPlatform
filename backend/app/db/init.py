from __future__ import annotations

"""初始化运行期数据库表与平台默认组织数据。"""

import psycopg
from sqlalchemy import select

from app.config import settings
from app.db import Base
from app.db.session import engine, session_scope
from app.models import Organization

DEFAULT_ORGANIZATION_ID = "org-default"
DEFAULT_ORGANIZATION_NAME = "默认组织"


def init_database() -> None:
    # Import app.models before create_all so SQLAlchemy sees every mapped class.
    Base.metadata.create_all(bind=engine)
    create_runtime_support_tables()
    ensure_default_organization()
    drop_legacy_platform_state()


def ensure_default_organization() -> None:
    with session_scope() as session:
        existing = session.execute(
            select(Organization).where(Organization.id == DEFAULT_ORGANIZATION_ID)
        ).scalar_one_or_none()
        if existing:
            return
        session.add(Organization(id=DEFAULT_ORGANIZATION_ID, name=DEFAULT_ORGANIZATION_NAME))


def drop_legacy_platform_state() -> None:
    with psycopg.connect(settings.database_url) as connection:
        connection.execute("DROP TABLE IF EXISTS platform_state")
        connection.commit()


def create_runtime_support_tables() -> None:
    Base.metadata.create_all(bind=engine)
    with psycopg.connect(settings.database_url) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS employee_service_tokens (
                token text PRIMARY KEY,
                employee_id varchar(36) NOT NULL REFERENCES digital_employees(id) ON DELETE CASCADE,
                created_at timestamp NOT NULL DEFAULT now()
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_idempotency_results (
                idempotency_key text PRIMARY KEY,
                employee_id varchar(36) REFERENCES digital_employees(id) ON DELETE SET NULL,
                tool_id varchar(36),
                result_json jsonb NOT NULL,
                created_at timestamp NOT NULL DEFAULT now()
            )
            """
        )
        # Backfill columns that may be missing from tables created before the ORM model was updated.
        connection.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'model_configurations' AND column_name = 'api_key'
                ) THEN
                    ALTER TABLE model_configurations ADD COLUMN api_key varchar(500) NOT NULL DEFAULT '';
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'model_configurations' AND column_name = 'max_output_tokens'
                ) THEN
                    ALTER TABLE model_configurations ADD COLUMN max_output_tokens integer;
                END IF;
            END $$;
            """
        )
        connection.commit()
