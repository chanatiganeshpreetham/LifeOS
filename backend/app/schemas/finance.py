from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    condecimal,
    model_validator,
)

Money = condecimal(max_digits=12, decimal_places=2, ge=0)
PositiveMoney = condecimal(max_digits=12, decimal_places=2, gt=0)
FinanceEntryType = Literal["income", "saving", "investment", "loan_borrowed", "loan_repayment"]
FinanceSource = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
CardName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
BankName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    icon: str | None
    colour_hex: str
    is_system: bool


class CategoryCreate(BaseModel):
    name: CategoryName
    icon: Annotated[str | None, StringConstraints(max_length=50)] = None
    colour_hex: Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")] = "#6B7280"


class ExpenseCreate(BaseModel):
    category_id: UUID
    credit_card_id: UUID | None = None
    amount: PositiveMoney
    merchant: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=200)] = None
    notes: Annotated[str | None, StringConstraints(max_length=10000)] = None
    expense_date: date


class ExpenseUpdate(BaseModel):
    category_id: UUID | None = None
    credit_card_id: UUID | None = None
    amount: PositiveMoney | None = None
    merchant: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=200)] = None
    notes: Annotated[str | None, StringConstraints(max_length=10000)] = None
    expense_date: date | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "ExpenseUpdate":
        for field in ("category_id", "amount", "expense_date"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    credit_card_id: UUID | None
    amount: Decimal
    currency: str
    merchant: str | None
    notes: str | None
    expense_date: date
    created_at: datetime


class ExpenseListResponse(BaseModel):
    items: list[ExpenseResponse]
    total: int


class BudgetCreate(BaseModel):
    category_id: UUID
    monthly_limit: PositiveMoney
    budget_month: int = Field(ge=1, le=12)
    budget_year: int = Field(ge=2000, le=2200)


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    monthly_limit: Decimal
    budget_month: int
    budget_year: int
    spent: Decimal


class MonthlyPlanInput(BaseModel):
    budget_month: int = Field(ge=1, le=12)
    budget_year: int = Field(ge=2000, le=2200)
    planned_income: Money = Decimal("0")
    spending_limit: Money = Decimal("0")
    savings_target: Money = Decimal("0")
    investment_target: Money = Decimal("0")
    loan_repayment_target: Money = Decimal("0")


class MonthlyPlanResponse(MonthlyPlanInput):
    id: UUID


class FinanceEntryCreate(BaseModel):
    entry_type: FinanceEntryType
    amount: PositiveMoney
    source: FinanceSource
    notes: Annotated[str | None, StringConstraints(max_length=10000)] = None
    entry_date: date


class FinanceEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entry_type: FinanceEntryType
    amount: Decimal
    source: str
    notes: str | None
    entry_date: date


class CreditCardCreate(BaseModel):
    card_name: CardName
    bank_name: BankName
    last_four_digits: Annotated[str | None, StringConstraints(pattern=r"^[0-9]{4}$")] = None
    credit_limit: PositiveMoney
    billing_date: int = Field(ge=1, le=31)
    due_date: int = Field(ge=1, le=31)
    current_balance: Money = Decimal("0")

    @model_validator(mode="after")
    def balance_within_limit(self) -> "CreditCardCreate":
        if self.current_balance > self.credit_limit:
            raise ValueError("Current balance cannot exceed the credit limit.")
        return self


class CreditCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    card_name: str
    bank_name: str
    last_four_digits: str | None
    credit_limit: Decimal
    billing_date: int
    due_date: int
    current_balance: Decimal


class FinanceSummary(BaseModel):
    budget_month: int
    budget_year: int
    planned_income: Decimal
    actual_income: Decimal
    spending_limit: Decimal
    actual_spent: Decimal
    remaining: Decimal
    savings_target: Decimal
    actual_saved: Decimal
    investment_target: Decimal
    actual_invested: Decimal
    loan_repayment_target: Decimal
    actual_repaid: Decimal
    actual_borrowed: Decimal
    category_spending: dict[str, Decimal]


class FinanceYearSummary(BaseModel):
    budget_year: int
    planned_income: Decimal
    actual_income: Decimal
    spending_limit: Decimal
    actual_spent: Decimal
    remaining: Decimal
    savings_target: Decimal
    actual_saved: Decimal
    investment_target: Decimal
    actual_invested: Decimal
    loan_repayment_target: Decimal
    actual_repaid: Decimal
    actual_borrowed: Decimal
    category_spending: dict[str, Decimal]


class DashboardCardDue(BaseModel):
    id: UUID
    card_name: str
    bank_name: str
    last_four_digits: str | None
    current_balance: Decimal
    due_date: date
    days_until_due: int


class FinanceDashboardSummary(BaseModel):
    date: date
    today_spent: Decimal
    month_spent: Decimal
    monthly_spending_limit: Decimal | None
    budget_source: Literal["monthly_plan", "category_budgets"] | None
    cards_due: list[DashboardCardDue]
