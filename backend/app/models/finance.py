from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    __table_args__ = (
        Index(
            "uq_expense_categories_system_name",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("user_id IS NULL"),
        ),
        Index(
            "uq_expense_categories_user_name",
            "user_id",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(50), nullable=True)
    colour_hex: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#6B7280")
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CreditCard(Base):
    __tablename__ = "credit_cards"
    __table_args__ = (
        CheckConstraint("credit_limit > 0", name="ck_credit_cards_limit_positive"),
        CheckConstraint("current_balance >= 0", name="ck_credit_cards_balance_nonnegative"),
        CheckConstraint("billing_date BETWEEN 1 AND 31", name="ck_credit_cards_billing_date"),
        CheckConstraint("due_date BETWEEN 1 AND 31", name="ck_credit_cards_due_date"),
        CheckConstraint(
            "last_four_digits IS NULL OR last_four_digits ~ '^[0-9]{4}$'",
            name="ck_credit_cards_last_four_digits",
        ),
        Index("ix_credit_cards_user_active", "user_id", "is_active", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    card_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_four_digits: Mapped[str | None] = mapped_column(String(4), nullable=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_date: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[int] = mapped_column(Integer, nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    alert_3day_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    alert_0day_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    alert_cycle: Mapped[str | None] = mapped_column(String(7), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        CheckConstraint("currency = 'INR'", name="ck_expenses_currency_inr"),
        CheckConstraint("source IN ('manual')", name="ck_expenses_source"),
        Index("ix_expenses_user_date", "user_id", "expense_date"),
        Index("ix_expenses_user_category", "user_id", "category_id"),
        Index("ix_expenses_user_card", "user_id", "credit_card_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_categories.id"), nullable=False
    )
    credit_card_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("credit_cards.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR")
    merchant: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_monthly_emi: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    emi_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, server_default="manual")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("monthly_limit > 0", name="ck_budgets_limit_positive"),
        CheckConstraint("budget_month BETWEEN 1 AND 12", name="ck_budgets_month"),
        CheckConstraint("budget_year BETWEEN 2000 AND 2200", name="ck_budgets_year"),
        UniqueConstraint(
            "user_id",
            "category_id",
            "budget_year",
            "budget_month",
            name="uq_budgets_user_category_period",
        ),
        Index("ix_budgets_user_period", "user_id", "budget_year", "budget_month"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("expense_categories.id"), nullable=False
    )
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    budget_month: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    alert_80_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    alert_100_sent: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class FinanceEntry(Base):
    __tablename__ = "finance_entries"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('income', 'saving', 'investment', 'loan_borrowed', 'loan_repayment')",
            name="ck_finance_entries_type",
        ),
        CheckConstraint("amount > 0", name="ck_finance_entries_amount_positive"),
        Index("ix_finance_entries_user_date", "user_id", "entry_date"),
        Index("ix_finance_entries_user_type_date", "user_id", "entry_type", "entry_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class MonthlyPlan(Base):
    __tablename__ = "monthly_plans"
    __table_args__ = (
        CheckConstraint("budget_month BETWEEN 1 AND 12", name="ck_monthly_plans_month"),
        CheckConstraint("budget_year BETWEEN 2000 AND 2200", name="ck_monthly_plans_year"),
        CheckConstraint("planned_income >= 0", name="ck_monthly_plans_income_nonnegative"),
        CheckConstraint("spending_limit >= 0", name="ck_monthly_plans_spending_nonnegative"),
        CheckConstraint("savings_target >= 0", name="ck_monthly_plans_savings_nonnegative"),
        CheckConstraint("investment_target >= 0", name="ck_monthly_plans_investment_nonnegative"),
        CheckConstraint(
            "loan_repayment_target >= 0",
            name="ck_monthly_plans_loan_repayment_nonnegative",
        ),
        UniqueConstraint("user_id", "budget_year", "budget_month", name="uq_monthly_plans_period"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    budget_month: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    spending_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    savings_target: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    investment_target: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    loan_repayment_target: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
