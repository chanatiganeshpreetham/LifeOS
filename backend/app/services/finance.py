import calendar
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.models.finance import (
    Budget,
    CreditCard,
    Expense,
    ExpenseCategory,
    FinanceEntry,
    MonthlyPlan,
)
from app.schemas.finance import (
    BudgetCreate,
    CategoryCreate,
    CreditCardCreate,
    ExpenseCreate,
    ExpenseUpdate,
    FinanceEntryCreate,
    MonthlyPlanInput,
)
from app.services.notifications import create_user_notification, enqueue_push_notification

ZERO = Decimal("0.00")
logger = logging.getLogger(__name__)


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def _owned_category(session: Session, user: User, category_id: UUID) -> ExpenseCategory:
    category = session.scalar(
        select(ExpenseCategory).where(
            ExpenseCategory.id == category_id,
            (ExpenseCategory.user_id == user.id) | ExpenseCategory.is_system.is_(True),
        )
    )
    if category is None:
        raise _not_found("Expense category not found.")
    return category


def _owned_card(session: Session, user: User, card_id: UUID) -> CreditCard:
    card = session.scalar(
        select(CreditCard).where(
            CreditCard.id == card_id,
            CreditCard.user_id == user.id,
            CreditCard.deleted_at.is_(None),
        )
    )
    if card is None:
        raise _not_found("Credit card not found.")
    return card


def list_categories(session: Session, user: User) -> list[ExpenseCategory]:
    return list(
        session.scalars(
            select(ExpenseCategory)
            .where((ExpenseCategory.user_id == user.id) | ExpenseCategory.is_system.is_(True))
            .order_by(ExpenseCategory.is_system.desc(), ExpenseCategory.name.asc())
        )
    )


def create_category(session: Session, user: User, payload: CategoryCreate) -> ExpenseCategory:
    category = ExpenseCategory(
        user_id=user.id,
        name=payload.name,
        icon=payload.icon,
        colour_hex=payload.colour_hex,
    )
    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists.",
        ) from None
    session.refresh(category)
    return category


def _budget_spent(session: Session, user_id: UUID, budget: Budget) -> Decimal:
    return (
        session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user_id,
                Expense.category_id == budget.category_id,
                Expense.expense_date >= date(budget.budget_year, budget.budget_month, 1),
                Expense.expense_date
                < date(
                    budget.budget_year + (budget.budget_month == 12),
                    budget.budget_month % 12 + 1,
                    1,
                ),
                Expense.deleted_at.is_(None),
            )
        )
        or ZERO
    )


def _check_budget_notifications(session: Session, user_id: UUID, expense: Expense) -> list[UUID]:
    budgets = list(
        session.scalars(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.category_id == expense.category_id,
                Budget.budget_month == expense.expense_date.month,
                Budget.budget_year == expense.expense_date.year,
            )
        )
    )
    return _check_budget_thresholds(session, user_id, budgets)


def _check_budget_thresholds(session: Session, user_id: UUID, budgets: list[Budget]) -> list[UUID]:
    push_ids = []
    for budget in budgets:
        spent = _budget_spent(session, user_id, budget)
        for threshold, field in (
            (Decimal("0.8"), "alert_80_sent"),
            (Decimal("1"), "alert_100_sent"),
        ):
            if spent >= budget.monthly_limit * threshold and not getattr(budget, field):
                percent = int(threshold * 100)
                notification_id = create_user_notification(
                    session,
                    user_id,
                    "budget_alert",
                    (
                        f"Your category budget has reached {percent}% "
                        f"({spent:.2f} of {budget.monthly_limit:.2f})."
                    ),
                    f"budget:{budget.id}:{percent}",
                )
                if notification_id:
                    push_ids.append(notification_id)
                setattr(budget, field, True)
    return push_ids


def _save_and_enqueue(session: Session, push_ids: list[UUID]) -> None:
    session.commit()
    for notification_id in push_ids:
        enqueue_push_notification(notification_id)


def create_expense(session: Session, user: User, payload: ExpenseCreate) -> Expense:
    _owned_category(session, user, payload.category_id)
    if payload.credit_card_id:
        _owned_card(session, user, payload.credit_card_id)
    expense = Expense(user_id=user.id, **payload.model_dump())
    session.add(expense)
    session.flush()
    push_ids = _check_budget_notifications(session, user.id, expense)
    _save_and_enqueue(session, push_ids)
    session.refresh(expense)
    return expense


def update_expense(
    session: Session, user: User, expense_id: UUID, payload: ExpenseUpdate
) -> Expense:
    expense = session.scalar(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.user_id == user.id,
            Expense.deleted_at.is_(None),
        )
    )
    if expense is None:
        raise _not_found("Expense not found.")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and changes["category_id"] is not None:
        _owned_category(session, user, changes["category_id"])
    if "credit_card_id" in changes and changes["credit_card_id"] is not None:
        _owned_card(session, user, changes["credit_card_id"])
    for key, value in changes.items():
        setattr(expense, key, value)
    session.flush()
    push_ids = _check_budget_notifications(session, user.id, expense)
    _save_and_enqueue(session, push_ids)
    session.refresh(expense)
    return expense


def delete_expense(session: Session, user: User, expense_id: UUID) -> None:
    expense = session.scalar(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.user_id == user.id,
            Expense.deleted_at.is_(None),
        )
    )
    if expense is None:
        raise _not_found("Expense not found.")
    expense.deleted_at = datetime.now(UTC)
    session.commit()


def list_expenses(
    session: Session,
    user: User,
    date_from: date | None,
    date_to: date | None,
    category_id: UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Expense], int]:
    query = select(Expense).where(Expense.user_id == user.id, Expense.deleted_at.is_(None))
    count_query = (
        select(func.count())
        .select_from(Expense)
        .where(Expense.user_id == user.id, Expense.deleted_at.is_(None))
    )
    if date_from:
        query = query.where(Expense.expense_date >= date_from)
        count_query = count_query.where(Expense.expense_date >= date_from)
    if date_to:
        query = query.where(Expense.expense_date <= date_to)
        count_query = count_query.where(Expense.expense_date <= date_to)
    if category_id:
        query = query.where(Expense.category_id == category_id)
        count_query = count_query.where(Expense.category_id == category_id)
    items = list(
        session.scalars(
            query.order_by(Expense.expense_date.desc(), Expense.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return items, int(session.scalar(count_query) or 0)


def upsert_budget(session: Session, user: User, payload: BudgetCreate) -> Budget:
    _owned_category(session, user, payload.category_id)
    budget = session.scalar(
        select(Budget).where(
            Budget.user_id == user.id,
            Budget.category_id == payload.category_id,
            Budget.budget_month == payload.budget_month,
            Budget.budget_year == payload.budget_year,
        )
    )
    if budget is None:
        budget = Budget(user_id=user.id, **payload.model_dump())
        session.add(budget)
    else:
        budget.monthly_limit = payload.monthly_limit
    session.flush()
    push_ids = _check_budget_thresholds(session, user.id, [budget])
    _save_and_enqueue(session, push_ids)
    session.refresh(budget)
    return budget


def list_budgets(session: Session, user: User, year: int, month: int) -> list[dict]:
    budgets = list(
        session.scalars(
            select(Budget).where(
                Budget.user_id == user.id,
                Budget.budget_year == year,
                Budget.budget_month == month,
            )
        )
    )
    return [
        {"budget": budget, "spent": _budget_spent(session, user.id, budget)} for budget in budgets
    ]


def save_monthly_plan(session: Session, user: User, payload: MonthlyPlanInput) -> MonthlyPlan:
    plan = session.scalar(
        select(MonthlyPlan).where(
            MonthlyPlan.user_id == user.id,
            MonthlyPlan.budget_year == payload.budget_year,
            MonthlyPlan.budget_month == payload.budget_month,
        )
    )
    if plan is None:
        plan = MonthlyPlan(user_id=user.id, **payload.model_dump())
        session.add(plan)
    else:
        for key, value in payload.model_dump().items():
            setattr(plan, key, value)
    session.commit()
    session.refresh(plan)
    return plan


def get_monthly_plan(session: Session, user: User, year: int, month: int) -> MonthlyPlan | None:
    return session.scalar(
        select(MonthlyPlan).where(
            MonthlyPlan.user_id == user.id,
            MonthlyPlan.budget_year == year,
            MonthlyPlan.budget_month == month,
        )
    )


def get_dashboard_summary(session: Session, user: User) -> dict:
    try:
        timezone = ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your profile timezone is invalid. Update it before viewing finance summaries.",
        ) from None

    today = datetime.now(UTC).astimezone(timezone).date()
    month_start = date(today.year, today.month, 1)
    next_month = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    today_spent = (
        session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user.id,
                Expense.expense_date == today,
                Expense.deleted_at.is_(None),
            )
        )
        or ZERO
    )
    month_spent = (
        session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user.id,
                Expense.expense_date >= month_start,
                Expense.expense_date < next_month,
                Expense.deleted_at.is_(None),
            )
        )
        or ZERO
    )

    plan = get_monthly_plan(session, user, today.year, today.month)
    budget_source = None
    spending_limit = None
    if plan is not None and plan.spending_limit > ZERO:
        spending_limit = plan.spending_limit
        budget_source = "monthly_plan"
    else:
        category_limit = session.scalar(
            select(func.sum(Budget.monthly_limit)).where(
                Budget.user_id == user.id,
                Budget.budget_year == today.year,
                Budget.budget_month == today.month,
            )
        )
        if category_limit is not None:
            spending_limit = category_limit
            budget_source = "category_budgets"

    cards_due = []
    for card in list_cards(session, user):
        due_month = today.month
        due_year = today.year
        due_day = min(card.due_date, calendar.monthrange(due_year, due_month)[1])
        due = date(due_year, due_month, due_day)
        if due < today:
            due_month += 1
            if due_month > 12:
                due_month = 1
                due_year += 1
            due = date(
                due_year,
                due_month,
                min(card.due_date, calendar.monthrange(due_year, due_month)[1]),
            )
        days_until_due = (due - today).days
        if days_until_due <= 30 and card.current_balance > ZERO:
            cards_due.append(
                {
                    "id": card.id,
                    "card_name": card.card_name,
                    "bank_name": card.bank_name,
                    "last_four_digits": card.last_four_digits,
                    "current_balance": card.current_balance,
                    "due_date": due,
                    "days_until_due": days_until_due,
                }
            )

    return {
        "date": today,
        "today_spent": today_spent,
        "month_spent": month_spent,
        "monthly_spending_limit": spending_limit,
        "budget_source": budget_source,
        "cards_due": sorted(cards_due, key=lambda item: item["due_date"]),
    }


def create_finance_entry(session: Session, user: User, payload: FinanceEntryCreate) -> FinanceEntry:
    entry = FinanceEntry(user_id=user.id, **payload.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def list_finance_entries(session: Session, user: User, year: int, month: int) -> list[FinanceEntry]:
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return list(
        session.scalars(
            select(FinanceEntry)
            .where(
                FinanceEntry.user_id == user.id,
                FinanceEntry.deleted_at.is_(None),
                FinanceEntry.entry_date >= start,
                FinanceEntry.entry_date < end,
            )
            .order_by(FinanceEntry.entry_date.desc(), FinanceEntry.created_at.desc())
        )
    )


def list_cards(session: Session, user: User) -> list[CreditCard]:
    return list(
        session.scalars(
            select(CreditCard)
            .where(
                CreditCard.user_id == user.id,
                CreditCard.is_active.is_(True),
                CreditCard.deleted_at.is_(None),
            )
            .order_by(CreditCard.due_date.asc())
        )
    )


def create_card(session: Session, user: User, payload: CreditCardCreate) -> CreditCard:
    card = CreditCard(user_id=user.id, **payload.model_dump())
    session.add(card)
    session.commit()
    session.refresh(card)
    return card


def delete_card(session: Session, user: User, card_id: UUID) -> None:
    card = _owned_card(session, user, card_id)
    card.is_active = False
    card.deleted_at = datetime.now(UTC)
    session.commit()


def get_summary(session: Session, user: User, year: int, month: int) -> dict:
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    plan = session.scalar(
        select(MonthlyPlan).where(
            MonthlyPlan.user_id == user.id,
            MonthlyPlan.budget_year == year,
            MonthlyPlan.budget_month == month,
        )
    )
    totals = {
        entry_type: session.scalar(
            select(func.coalesce(func.sum(FinanceEntry.amount), 0)).where(
                FinanceEntry.user_id == user.id,
                FinanceEntry.entry_type == entry_type,
                FinanceEntry.entry_date >= start,
                FinanceEntry.entry_date < end,
                FinanceEntry.deleted_at.is_(None),
            )
        )
        or ZERO
        for entry_type in ("income", "saving", "investment", "loan_borrowed", "loan_repayment")
    }
    spent = (
        session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user.id,
                Expense.expense_date >= start,
                Expense.expense_date < end,
                Expense.deleted_at.is_(None),
            )
        )
        or ZERO
    )
    category_rows = session.execute(
        select(ExpenseCategory.name, func.sum(Expense.amount))
        .join(Expense, Expense.category_id == ExpenseCategory.id)
        .where(
            Expense.user_id == user.id,
            Expense.expense_date >= start,
            Expense.expense_date < end,
            Expense.deleted_at.is_(None),
        )
        .group_by(ExpenseCategory.name)
    )
    category_spending = {name: amount for name, amount in category_rows}
    spending_limit = plan.spending_limit if plan else ZERO
    return {
        "budget_month": month,
        "budget_year": year,
        "planned_income": plan.planned_income if plan else ZERO,
        "actual_income": totals["income"],
        "spending_limit": spending_limit,
        "actual_spent": spent,
        "remaining": spending_limit - spent,
        "savings_target": plan.savings_target if plan else ZERO,
        "actual_saved": totals["saving"],
        "investment_target": plan.investment_target if plan else ZERO,
        "actual_invested": totals["investment"],
        "loan_repayment_target": plan.loan_repayment_target if plan else ZERO,
        "actual_repaid": totals["loan_repayment"],
        "actual_borrowed": totals["loan_borrowed"],
        "category_spending": category_spending,
    }


def get_year_summary(session: Session, user: User, year: int) -> dict:
    start, end = date(year, 1, 1), date(year + 1, 1, 1)
    plans = list(
        session.scalars(
            select(MonthlyPlan).where(
                MonthlyPlan.user_id == user.id,
                MonthlyPlan.budget_year == year,
            )
        )
    )
    totals = {
        entry_type: session.scalar(
            select(func.coalesce(func.sum(FinanceEntry.amount), 0)).where(
                FinanceEntry.user_id == user.id,
                FinanceEntry.entry_type == entry_type,
                FinanceEntry.entry_date >= start,
                FinanceEntry.entry_date < end,
                FinanceEntry.deleted_at.is_(None),
            )
        )
        or ZERO
        for entry_type in ("income", "saving", "investment", "loan_borrowed", "loan_repayment")
    }
    spent = (
        session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user.id,
                Expense.expense_date >= start,
                Expense.expense_date < end,
                Expense.deleted_at.is_(None),
            )
        )
        or ZERO
    )
    category_rows = session.execute(
        select(ExpenseCategory.name, func.sum(Expense.amount))
        .join(Expense, Expense.category_id == ExpenseCategory.id)
        .where(
            Expense.user_id == user.id,
            Expense.expense_date >= start,
            Expense.expense_date < end,
            Expense.deleted_at.is_(None),
        )
        .group_by(ExpenseCategory.name)
    )
    spending_limit = sum((plan.spending_limit for plan in plans), ZERO)
    return {
        "budget_year": year,
        "planned_income": sum((plan.planned_income for plan in plans), ZERO),
        "actual_income": totals["income"],
        "spending_limit": spending_limit,
        "actual_spent": spent,
        "remaining": spending_limit - spent,
        "savings_target": sum((plan.savings_target for plan in plans), ZERO),
        "actual_saved": totals["saving"],
        "investment_target": sum((plan.investment_target for plan in plans), ZERO),
        "actual_invested": totals["investment"],
        "loan_repayment_target": sum((plan.loan_repayment_target for plan in plans), ZERO),
        "actual_repaid": totals["loan_repayment"],
        "actual_borrowed": totals["loan_borrowed"],
        "category_spending": {name: amount for name, amount in category_rows},
    }


def dispatch_finance_alerts(session: Session, now: datetime) -> int:
    cards = list(
        session.scalars(
            select(CreditCard).where(
                CreditCard.is_active.is_(True),
                CreditCard.deleted_at.is_(None),
            )
        )
    )
    pushed: list[UUID] = []
    notified = 0
    for card in cards:
        user = session.get(User, card.user_id)
        if user is None or not user.is_active:
            continue
        try:
            local_today = now.astimezone(ZoneInfo(user.timezone)).date()
        except ZoneInfoNotFoundError:
            logger.error(
                "Skipped due-date notifications for user %s because timezone %r is invalid",
                user.id,
                user.timezone,
            )
            continue
        due_year, due_month = local_today.year, local_today.month
        due_day = min(card.due_date, calendar.monthrange(due_year, due_month)[1])
        due = date(due_year, due_month, due_day)
        if due < local_today:
            due_month += 1
            if due_month > 12:
                due_month = 1
                due_year += 1
            due = date(
                due_year, due_month, min(card.due_date, calendar.monthrange(due_year, due_month)[1])
            )
        days_left = (due - local_today).days
        if days_left not in (0, 3):
            continue
        threshold = "due" if days_left == 0 else "3day"
        cycle = f"{due_year:04d}-{due_month:02d}"
        if card.alert_cycle != cycle:
            card.alert_cycle = cycle
            card.alert_3day_sent = False
            card.alert_0day_sent = False
        alert_field = "alert_0day_sent" if days_left == 0 else "alert_3day_sent"
        if getattr(card, alert_field):
            continue
        notification_id = create_user_notification(
            session,
            user.id,
            "cc_due",
            f"{card.card_name} payment is due {'today' if days_left == 0 else 'in 3 days'}.",
            f"card:{card.id}:{due:%Y-%m}:{threshold}",
        )
        if notification_id:
            pushed.append(notification_id)
            notified += 1
        setattr(card, alert_field, True)
    session.commit()
    for notification_id in pushed:
        enqueue_push_notification(notification_id)
    return notified
