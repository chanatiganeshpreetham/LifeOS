"""Store a simple payment method on expenses.

Revision ID: 0010_expense_payment_method
Revises: 0009_dashboard_task_index
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_expense_payment_method"
down_revision: str | None = "0009_dashboard_task_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("payment_method", sa.String(length=30), nullable=True))
    op.add_column("expenses", sa.Column("is_monthly_emi", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("expenses", sa.Column("emi_end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("expenses", "emi_end_date")
    op.drop_column("expenses", "is_monthly_emi")
    op.drop_column("expenses", "payment_method")
