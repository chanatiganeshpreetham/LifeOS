"""Create user-scoped tasks with PostgreSQL full-text search.

Revision ID: 0003_tasks
Revises: 0002_auth_tables
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_tasks"
down_revision: str | None = "0002_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=10), server_default="medium", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "priority IN ('high', 'medium', 'low')",
            name="ck_tasks_priority",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_user_due", "tasks", ["user_id", "due_at"])
    op.create_index("ix_tasks_user_completed", "tasks", ["user_id", "is_completed"])
    op.create_index("ix_tasks_user_deleted", "tasks", ["user_id", "deleted_at"])
    op.create_index(
        "ix_tasks_search_vector",
        "tasks",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.execute(
        """
        CREATE FUNCTION update_task_search_vector() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector := to_tsvector(
            'simple',
            coalesce(NEW.title, '') || ' ' || coalesce(NEW.notes, '')
          );
          RETURN NEW;
        END
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER tasks_search_vector_update
        BEFORE INSERT OR UPDATE OF title, notes ON tasks
        FOR EACH ROW EXECUTE FUNCTION update_task_search_vector()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tasks_search_vector_update ON tasks")
    op.execute("DROP FUNCTION IF EXISTS update_task_search_vector()")
    op.drop_index("ix_tasks_search_vector", table_name="tasks")
    op.drop_index("ix_tasks_user_deleted", table_name="tasks")
    op.drop_index("ix_tasks_user_completed", table_name="tasks")
    op.drop_index("ix_tasks_user_due", table_name="tasks")
    op.drop_table("tasks")
