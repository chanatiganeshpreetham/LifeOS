import csv
import io
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.models.finance import Budget
from app.schemas.finance import (
    BudgetCreate,
    BudgetResponse,
    CategoryCreate,
    CategoryResponse,
    CreditCardCreate,
    CreditCardResponse,
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseResponse,
    ExpenseUpdate,
    FinanceDashboardSummary,
    FinanceEntryCreate,
    FinanceEntryResponse,
    FinanceSummary,
    FinanceYearSummary,
    MonthlyPlanInput,
    MonthlyPlanResponse,
)
from app.services import finance as finance_service

router = APIRouter(prefix="/finance", tags=["finance"])
SessionDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/dashboard-summary", response_model=FinanceDashboardSummary)
def get_dashboard_summary(session: SessionDependency, user: CurrentUser) -> FinanceDashboardSummary:
    return FinanceDashboardSummary(**finance_service.get_dashboard_summary(session, user))


def _budget_response(budget: Budget, spent: Decimal) -> BudgetResponse:
    return BudgetResponse.model_validate(
        {
            "id": budget.id,
            "category_id": budget.category_id,
            "monthly_limit": budget.monthly_limit,
            "budget_month": budget.budget_month,
            "budget_year": budget.budget_year,
            "spent": spent,
        }
    )


@router.get("/summary", response_model=FinanceSummary)
def get_summary(
    session: SessionDependency,
    user: CurrentUser,
    year: Annotated[int, Query(ge=2000, le=2200)] = date.today().year,
    month: Annotated[int, Query(ge=1, le=12)] = date.today().month,
) -> FinanceSummary:
    return FinanceSummary(**finance_service.get_summary(session, user, year, month))


@router.get("/summary/yearly", response_model=FinanceYearSummary)
def get_year_summary(
    session: SessionDependency,
    user: CurrentUser,
    year: Annotated[int, Query(ge=2000, le=2200)] = date.today().year,
) -> FinanceYearSummary:
    return FinanceYearSummary(**finance_service.get_year_summary(session, user, year))


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(session: SessionDependency, user: CurrentUser) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(item)
        for item in finance_service.list_categories(session, user)
    ]


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate, session: SessionDependency, user: CurrentUser
) -> CategoryResponse:
    return CategoryResponse.model_validate(finance_service.create_category(session, user, payload))


@router.get("/expenses/export.csv")
def export_expenses(
    session: SessionDependency,
    user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: UUID | None = None,
) -> StreamingResponse:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from cannot be after date_to.",
        )
    expenses, _ = finance_service.list_expenses(
        session, user, date_from, date_to, category_id, limit=1000000, offset=0
    )
    categories = {item.id: item.name for item in finance_service.list_categories(session, user)}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("Date", "Category", "Merchant", "Amount (INR)", "Notes"))
    for expense in expenses:
        row = [
            expense.expense_date.isoformat(),
            categories.get(expense.category_id, "Unknown"),
            expense.merchant or "",
            str(expense.amount),
            expense.notes or "",
        ]
        writer.writerow(
            [
                f"'{value}"
                if isinstance(value, str)
                and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
                for value in row
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="lifeos-expenses.csv"'},
    )


@router.get("/expenses", response_model=ExpenseListResponse)
def list_expenses(
    session: SessionDependency,
    user: CurrentUser,
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExpenseListResponse:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from cannot be after date_to.",
        )
    expenses, total = finance_service.list_expenses(
        session, user, date_from, date_to, category_id, limit, offset
    )
    return ExpenseListResponse(items=expenses, total=total)


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseCreate, session: SessionDependency, user: CurrentUser
) -> ExpenseResponse:
    return ExpenseResponse.model_validate(finance_service.create_expense(session, user, payload))


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: UUID,
    payload: ExpenseUpdate,
    session: SessionDependency,
    user: CurrentUser,
) -> ExpenseResponse:
    return ExpenseResponse.model_validate(
        finance_service.update_expense(session, user, expense_id, payload)
    )


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: UUID, session: SessionDependency, user: CurrentUser) -> Response:
    finance_service.delete_expense(session, user, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/budgets", response_model=list[BudgetResponse])
def list_budgets(
    session: SessionDependency,
    user: CurrentUser,
    year: Annotated[int, Query(ge=2000, le=2200)] = date.today().year,
    month: Annotated[int, Query(ge=1, le=12)] = date.today().month,
) -> list[BudgetResponse]:
    return [
        _budget_response(item["budget"], item["spent"])
        for item in finance_service.list_budgets(session, user, year, month)
    ]


@router.put("/budgets", response_model=BudgetResponse)
def save_budget(
    payload: BudgetCreate, session: SessionDependency, user: CurrentUser
) -> BudgetResponse:
    budget = finance_service.upsert_budget(session, user, payload)
    item = next(
        item
        for item in finance_service.list_budgets(
            session, user, payload.budget_year, payload.budget_month
        )
        if item["budget"].id == budget.id
    )
    return _budget_response(budget, item["spent"])


@router.put("/plan", response_model=MonthlyPlanResponse)
def save_monthly_plan(
    payload: MonthlyPlanInput, session: SessionDependency, user: CurrentUser
) -> MonthlyPlanResponse:
    return MonthlyPlanResponse.model_validate(
        finance_service.save_monthly_plan(session, user, payload)
    )


@router.get("/plan", response_model=MonthlyPlanResponse | None)
def get_monthly_plan(
    session: SessionDependency,
    user: CurrentUser,
    year: Annotated[int, Query(ge=2000, le=2200)] = date.today().year,
    month: Annotated[int, Query(ge=1, le=12)] = date.today().month,
) -> MonthlyPlanResponse | None:
    plan = finance_service.get_monthly_plan(session, user, year, month)
    return MonthlyPlanResponse.model_validate(plan) if plan else None


@router.get("/entries", response_model=list[FinanceEntryResponse])
def list_entries(
    session: SessionDependency,
    user: CurrentUser,
    year: Annotated[int, Query(ge=2000, le=2200)] = date.today().year,
    month: Annotated[int, Query(ge=1, le=12)] = date.today().month,
) -> list[FinanceEntryResponse]:
    return [
        FinanceEntryResponse.model_validate(item)
        for item in finance_service.list_finance_entries(session, user, year, month)
    ]


@router.post("/entries", response_model=FinanceEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: FinanceEntryCreate, session: SessionDependency, user: CurrentUser
) -> FinanceEntryResponse:
    return FinanceEntryResponse.model_validate(
        finance_service.create_finance_entry(session, user, payload)
    )


@router.get("/cards", response_model=list[CreditCardResponse])
def list_cards(session: SessionDependency, user: CurrentUser) -> list[CreditCardResponse]:
    return [
        CreditCardResponse.model_validate(item)
        for item in finance_service.list_cards(session, user)
    ]


@router.post("/cards", response_model=CreditCardResponse, status_code=status.HTTP_201_CREATED)
def create_card(
    payload: CreditCardCreate, session: SessionDependency, user: CurrentUser
) -> CreditCardResponse:
    return CreditCardResponse.model_validate(finance_service.create_card(session, user, payload))


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(card_id: UUID, session: SessionDependency, user: CurrentUser) -> Response:
    finance_service.delete_card(session, user, card_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
