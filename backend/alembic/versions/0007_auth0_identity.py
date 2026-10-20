"""Use Auth0 identities for LifeOS users.

Revision ID: 0007_auth0_identity
Revises: 0006_health_notes
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_auth0_identity"
down_revision: str | None = "0006_health_notes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth0_subject", sa.String(length=255), nullable=True))
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.create_index("ix_users_auth0_subject", "users", ["auth0_subject"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_auth0_subject", table_name="users")
    op.drop_column("users", "auth0_subject")
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(length=255),
        nullable=False,
    )
