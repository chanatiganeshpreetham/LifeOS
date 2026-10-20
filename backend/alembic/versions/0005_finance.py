"""Add expense tracking, budgets, monthly plans, and cards.

Revision ID: 0005_finance
Revises: 0004_reminders_push
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_finance"
down_revision: str | None = "0004_reminders_push"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SYSTEM_CATEGORIES = (
    ("00000000-0000-4000-8000-000000000001", "Food", "food", "#EF8354"),
    ("00000000-0000-4000-8000-000000000002", "Transport", "transport", "#5B8DEF"),
    ("00000000-0000-4000-8000-000000000003", "Bills", "bills", "#9B6DCC"),
    ("00000000-0000-4000-8000-000000000004", "Shopping", "shopping", "#E06C9F"),
    ("00000000-0000-4000-8000-000000000005", "Health", "health", "#39A879"),
    ("00000000-0000-4000-8000-000000000006", "Entertainment", "entertainment", "#D4A72C"),
    ("00000000-0000-4000-8000-000000000007", "Education", "education", "#4F9BA8"),
    ("00000000-0000-4000-8000-000000000008", "Home", "home", "#8A817C"),
    ("00000000-0000-4000-8000-000000000009", "Personal care", "personal-care", "#C2785C"),
    ("00000000-0000-4000-8000-000000000010", "Travel", "travel", "#4F77B5"),
    ("00000000-0000-4000-8000-000000000011", "Groceries", "groceries", "#64A45C"),
    ("00000000-0000-4000-8000-000000000012", "Other", "other", "#6B7280"),
)


def upgrade() -> None:
    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("colour_hex", sa.String(length=7), server_default="#6B7280", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_expense_categories_system_name",
        "expense_categories",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_expense_categories_user_name",
        "expense_categories",
        ["user_id", sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.bulk_insert(
        sa.table(
            "expense_categories",
            sa.column("id", sa.Uuid()),
            sa.column("user_id", sa.Uuid()),
            sa.column("name", sa.String()),
            sa.column("icon", sa.String()),
            sa.column("colour_hex", sa.String()),
            sa.column("is_system", sa.Boolean()),
        ),
        [
            {
                "id": category_id,
                "user_id": None,
                "name": name,
                "icon": icon,
                "colour_hex": colour,
                "is_system": True,
            }
            for category_id, name, icon, colour in _SYSTEM_CATEGORIES
        ],
    )

    op.create_table(
        "credit_cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("card_name", sa.String(length=100), nullable=False),
        sa.Column("bank_name", sa.String(length=80), nullable=False),
        sa.Column("last_four_digits", sa.String(length=4), nullable=True),
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_date", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Integer(), nullable=False),
        sa.Column("current_balance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("alert_3day_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("alert_0day_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("alert_cycle", sa.String(length=7), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("credit_limit > 0", name="ck_credit_cards_limit_positive"),
        sa.CheckConstraint("current_balance >= 0", name="ck_credit_cards_balance_nonnegative"),
        sa.CheckConstraint("billing_date BETWEEN 1 AND 31", name="ck_credit_cards_billing_date"),
        sa.CheckConstraint("due_date BETWEEN 1 AND 31", name="ck_credit_cards_due_date"),
        sa.CheckConstraint(
            "last_four_digits IS NULL OR last_four_digits ~ '^[0-9]{4}$'",
            name="ck_credit_cards_last_four_digits",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_credit_cards_user_active",
        "credit_cards",
        ["user_id", "is_active", "deleted_at"],
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("credit_card_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("merchant", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.CheckConstraint("currency = 'INR'", name="ck_expenses_currency_inr"),
        sa.CheckConstraint("source IN ('manual')", name="ck_expenses_source"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"]),
        sa.ForeignKeyConstraint(["credit_card_id"], ["credit_cards.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_user_date", "expenses", ["user_id", "expense_date"])
    op.create_index("ix_expenses_user_category", "expenses", ["user_id", "category_id"])
    op.create_index("ix_expenses_user_card", "expenses", ["user_id", "credit_card_id"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("monthly_limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("budget_month", sa.Integer(), nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("alert_80_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("alert_100_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("monthly_limit > 0", name="ck_budgets_limit_positive"),
        sa.CheckConstraint("budget_month BETWEEN 1 AND 12", name="ck_budgets_month"),
        sa.CheckConstraint("budget_year BETWEEN 2000 AND 2200", name="ck_budgets_year"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "budget_year",
            "budget_month",
            name="uq_budgets_user_category_period",
        ),
    )
    op.create_index("ix_budgets_user_period", "budgets", ["user_id", "budget_year", "budget_month"])

    op.create_table(
        "finance_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "entry_type IN ('income', 'saving', 'investment', 'loan_borrowed', 'loan_repayment')",
            name="ck_finance_entries_type",
        ),
        sa.CheckConstraint("amount > 0", name="ck_finance_entries_amount_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finance_entries_user_date", "finance_entries", ["user_id", "entry_date"])
    op.create_index(
        "ix_finance_entries_user_type_date",
        "finance_entries",
        ["user_id", "entry_type", "entry_date"],
    )

    op.create_table(
        "monthly_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("budget_month", sa.Integer(), nullable=False),
        sa.Column("budget_year", sa.Integer(), nullable=False),
        sa.Column("planned_income", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("spending_limit", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("savings_target", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("investment_target", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("loan_repayment_target", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("budget_month BETWEEN 1 AND 12", name="ck_monthly_plans_month"),
        sa.CheckConstraint("budget_year BETWEEN 2000 AND 2200", name="ck_monthly_plans_year"),
        sa.CheckConstraint("planned_income >= 0", name="ck_monthly_plans_income_nonnegative"),
        sa.CheckConstraint("spending_limit >= 0", name="ck_monthly_plans_spending_nonnegative"),
        sa.CheckConstraint("savings_target >= 0", name="ck_monthly_plans_savings_nonnegative"),
        sa.CheckConstraint(
            "investment_target >= 0", name="ck_monthly_plans_investment_nonnegative"
        ),
        sa.CheckConstraint(
            "loan_repayment_target >= 0",
            name="ck_monthly_plans_loan_repayment_nonnegative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "budget_year", "budget_month", name="uq_monthly_plans_period"
        ),
    )

    op.drop_constraint("ck_notification_log_type", "notification_log", type_="check")
    op.create_check_constraint(
        "ck_notification_log_type",
        "notification_log",
        "type IN ('push', 'in_app', 'budget_alert', 'cc_due')",
    )
    op.add_column("notification_log", sa.Column("event_key", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_notification_log_event_key", "notification_log", ["event_key"])
    op.alter_column(
        "notification_log",
        "status",
        existing_type=sa.String(length=20),
        server_default="pending",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("DELETE FROM notification_log WHERE type IN ('budget_alert', 'cc_due')")
    op.drop_constraint("uq_notification_log_event_key", "notification_log", type_="unique")
    op.drop_column("notification_log", "event_key")
    op.drop_constraint("ck_notification_log_type", "notification_log", type_="check")
    op.create_check_constraint(
        "ck_notification_log_type",
        "notification_log",
        "type IN ('push', 'in_app')",
    )
    op.drop_table("monthly_plans")
    op.drop_index("ix_finance_entries_user_type_date", table_name="finance_entries")
    op.drop_index("ix_finance_entries_user_date", table_name="finance_entries")
    op.drop_table("finance_entries")
    op.drop_index("ix_budgets_user_period", table_name="budgets")
    op.drop_table("budgets")
    op.drop_index("ix_expenses_user_card", table_name="expenses")
    op.drop_index("ix_expenses_user_category", table_name="expenses")
    op.drop_index("ix_expenses_user_date", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_credit_cards_user_active", table_name="credit_cards")
    op.drop_table("credit_cards")
    op.drop_index("uq_expense_categories_user_name", table_name="expense_categories")
    op.drop_index("uq_expense_categories_system_name", table_name="expense_categories")
    op.drop_table("expense_categories")
