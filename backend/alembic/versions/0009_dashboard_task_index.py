"""Add task update index for Daybook and dashboard queries.

Revision ID: 0009_dashboard_task_index
Revises: 0008_daybook
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_dashboard_task_index"
down_revision: str | None = "0008_daybook"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("tasks")}
    if "ix_tasks_user_updated" not in existing_indexes:
        op.create_index("ix_tasks_user_updated", "tasks", ["user_id", "updated_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index["name"] for index in inspector.get_indexes("tasks")}
    if "ix_tasks_user_updated" in existing_indexes:
        op.drop_index("ix_tasks_user_updated", table_name="tasks")
