import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/context'
import {
  createFinanceCard,
  createFinanceCategory,
  createFinanceEntry,
  createFinanceExpense,
  deleteFinanceCard,
  deleteFinanceExpense,
  exportFinanceExpenses,
  fetchFinanceBudgets,
  fetchFinanceCards,
  fetchFinanceCategories,
  fetchFinanceEntries,
  fetchFinanceExpenses,
  fetchFinancePlan,
  fetchFinanceSummary,
  fetchFinanceYearSummary,
  saveFinanceBudget,
  saveFinancePlan,
  type FinanceBudget,
  type FinanceCard,
  type FinanceCategory,
  type FinanceEntry,
  type FinanceEntryType,
  type FinanceExpense,
  type FinancePlan,
  type FinanceSummary,
} from '../api/finance'

const entryTypes: { value: FinanceEntryType; label: string }[] = [
  { value: 'income', label: 'Income received' },
  { value: 'saving', label: 'Money saved' },
  { value: 'investment', label: 'Investment made' },
  { value: 'loan_borrowed', label: 'Money borrowed' },
  { value: 'loan_repayment', label: 'Loan repaid' },
]

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
const currentDate = today.toLocaleDateString('en-CA')
const emptyPlan = (year: number, month: number): FinancePlan => ({
  budget_month: month,
  budget_year: year,
  planned_income: '0',
  spending_limit: '0',
  savings_target: '0',
  investment_target: '0',
  loan_repayment_target: '0',
})

function amount(value: string | number | undefined): number {
  return Number(value ?? 0)
}

function money(value: string | number | undefined): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount(value))
}

function formValue(form: HTMLFormElement, name: string): string {
  return String(new FormData(form).get(name) ?? '').trim()
}

function ErrorMessage({ message }: { message: string }) {
  if (!message) return null
  return <p className="form-message form-message-error" role="alert">{message}</p>
}

export function FinancePage() {
  const { accessToken } = useAuth()
  const [selectedMonth, setSelectedMonth] = useState(currentMonth)
  const [summary, setSummary] = useState<FinanceSummary | null>(null)
  const [yearSummary, setYearSummary] = useState<FinanceSummary | null>(null)
  const [categories, setCategories] = useState<FinanceCategory[]>([])
  const [expenses, setExpenses] = useState<FinanceExpense[]>([])
  const [budgets, setBudgets] = useState<FinanceBudget[]>([])
  const [entries, setEntries] = useState<FinanceEntry[]>([])
  const [cards, setCards] = useState<FinanceCard[]>([])
  const [plan, setPlan] = useState<FinancePlan>(emptyPlan(today.getFullYear(), today.getMonth() + 1))
  const [isLoading, setIsLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [expenseSearch, setExpenseSearch] = useState('')
  const [year, month] = selectedMonth.split('-').map(Number)

  const reload = useCallback(async () => {
    if (!accessToken) return
    const [
      monthData,
      annualData,
      categoryData,
      expenseData,
      budgetData,
      entryData,
      cardData,
      savedPlan,
    ] = await Promise.all([
      fetchFinanceSummary(accessToken, year, month),
      fetchFinanceYearSummary(accessToken, year),
      fetchFinanceCategories(accessToken),
      fetchFinanceExpenses(accessToken, year, month),
      fetchFinanceBudgets(accessToken, year, month),
      fetchFinanceEntries(accessToken, year, month),
      fetchFinanceCards(accessToken),
      fetchFinancePlan(accessToken, year, month),
    ])
    setSummary(monthData)
    setYearSummary(annualData)
    setCategories(categoryData)
    setExpenses(expenseData.items)
    setBudgets(budgetData)
    setEntries(entryData)
    setCards(cardData)
    setPlan(savedPlan ?? emptyPlan(year, month))
  }, [accessToken, month, year])

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError('')
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    reload()
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load finances.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [accessToken, reload])

  const categoryNames = useMemo(
    () => new Map(categories.map((category) => [category.id, category.name])),
    [categories],
  )
  const visibleExpenses = useMemo(() => expenses.filter((expense) => {
    const matchesCategory = !categoryFilter || expense.category_id === categoryFilter
    const needle = expenseSearch.trim().toLowerCase()
    const matchesSearch = !needle || `${expense.merchant ?? ''} ${expense.notes ?? ''}`.toLowerCase().includes(needle)
    return matchesCategory && matchesSearch
  }), [categoryFilter, expenseSearch, expenses])
  const topCategories = useMemo(
    () => Object.entries(summary?.category_spending ?? {}).sort((a, b) => amount(b[1]) - amount(a[1])),
    [summary],
  )

  async function perform(action: () => Promise<unknown>, successMessage: string) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await action()
      await reload()
      setNotice(successMessage)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save your finance changes.')
    } finally {
      setBusy(false)
    }
  }

  function handleExpenseSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceExpense(accessToken, {
      category_id: formValue(form, 'category_id'),
      credit_card_id: formValue(form, 'credit_card_id') || null,
      amount: formValue(form, 'amount'),
      merchant: formValue(form, 'merchant') || null,
      notes: formValue(form, 'notes') || null,
      expense_date: formValue(form, 'expense_date'),
    }), 'Expense recorded.')
    form.reset()
  }

  function handlePlanSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    const updated = { ...plan }
    for (const field of ['planned_income', 'spending_limit', 'savings_target', 'investment_target', 'loan_repayment_target'] as const) {
      updated[field] = formValue(form, field) || '0'
    }
    void perform(() => saveFinancePlan(accessToken, updated), 'Monthly plan saved.')
  }

  function handleEntrySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceEntry(accessToken, {
      entry_type: formValue(form, 'entry_type') as FinanceEntryType,
      amount: formValue(form, 'amount'),
      source: formValue(form, 'source'),
      notes: formValue(form, 'notes') || null,
      entry_date: formValue(form, 'entry_date'),
    }), 'Finance entry saved.')
    form.reset()
  }

  function handleBudgetSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    void perform(() => saveFinanceBudget(accessToken, {
      category_id: formValue(form, 'category_id'),
      monthly_limit: formValue(form, 'monthly_limit'),
      budget_month: month,
      budget_year: year,
    }), 'Category budget saved.')
    form.reset()
  }

  function handleCategorySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceCategory(accessToken, {
      name: formValue(form, 'name'),
      icon: null,
      colour_hex: '#6B7280',
    }), 'Category added.')
    form.reset()
  }

  function handleCardSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceCard(accessToken, {
      card_name: formValue(form, 'card_name'),
      bank_name: formValue(form, 'bank_name'),
      last_four_digits: formValue(form, 'last_four_digits') || null,
      credit_limit: formValue(form, 'credit_limit'),
      billing_date: Number(formValue(form, 'billing_date')),
      due_date: Number(formValue(form, 'due_date')),
      current_balance: formValue(form, 'current_balance') || '0',
    }), 'Credit card added.')
    form.reset()
  }

  async function removeExpense(expenseId: string) {
    if (!accessToken || !window.confirm('Delete this expense?')) return
    await perform(() => deleteFinanceExpense(accessToken, expenseId), 'Expense deleted.')
  }

  async function removeCard(cardId: string) {
    if (!accessToken || !window.confirm('Remove this credit card?')) return
    await perform(() => deleteFinanceCard(accessToken, cardId), 'Credit card removed.')
  }

  async function downloadCsv() {
    if (!accessToken) return
    try {
      const blob = await exportFinanceExpenses(accessToken)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'lifeos-expenses.csv'
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not export expenses.')
    }
  }

  function setPlanAmount(field: keyof Omit<FinancePlan, 'id' | 'budget_month' | 'budget_year'>, value: string) {
    setPlan((previous) => ({ ...previous, [field]: value }))
  }

  if (isLoading) {
    return <main className="page-content"><p className="welcome-copy">Loading your finances…</p></main>
  }

  return (
    <main className="page-content finance-page">
      <header className="finance-heading">
        <div>
          <p className="eyebrow">Your money, in one clear view</p>
          <h1>Finance</h1>
          <p className="welcome-copy">Plan your spending, track what matters, and see how your goals are progressing.</p>
        </div>
        <label className="finance-month-picker">
          <span>Reporting month</span>
          <input type="month" value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)} />
        </label>
      </header>
      <ErrorMessage message={error} />
      {notice && <p className="form-message form-message-success" role="status">{notice}</p>}
      {!categories.length && !error ? <p className="welcome-copy">Finance categories will appear after the database migration is applied.</p> : null}

      {summary && yearSummary && (
        <>
          <section aria-label="Monthly overview" className="finance-section">
            <div className="finance-section-heading">
              <div><p className="eyebrow">Monthly snapshot</p><h2>{new Date(year, month - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2></div>
            </div>
            <div className="finance-metrics">
              <Metric label="Spent" actual={summary.actual_spent} target={summary.spending_limit} />
              <Metric label="Income" actual={summary.actual_income} target={summary.planned_income} />
              <Metric label="Saved" actual={summary.actual_saved} target={summary.savings_target} />
              <Metric label="Invested" actual={summary.actual_invested} target={summary.investment_target} />
              <Metric label="Loan repayments" actual={summary.actual_repaid} target={summary.loan_repayment_target} />
              <Metric label="Borrowed" actual={summary.actual_borrowed} />
              <article className="finance-metric"><span>Budget remaining</span><strong>{money(summary.remaining)}</strong><small>Monthly spending limit less expenses</small></article>
            </div>
          </section>

          <section aria-label="Yearly overview" className="finance-section finance-yearly">
            <div className="finance-section-heading"><div><p className="eyebrow">Year to date</p><h2>{year} plan vs actual</h2></div></div>
            <div className="finance-metrics finance-metrics-compact">
              <Metric label="Spent" actual={yearSummary.actual_spent} target={yearSummary.spending_limit} />
              <Metric label="Income" actual={yearSummary.actual_income} target={yearSummary.planned_income} />
              <Metric label="Saved" actual={yearSummary.actual_saved} target={yearSummary.savings_target} />
              <Metric label="Invested" actual={yearSummary.actual_invested} target={yearSummary.investment_target} />
              <Metric label="Repaid" actual={yearSummary.actual_repaid} target={yearSummary.loan_repayment_target} />
            </div>
          </section>

          <div className="finance-columns">
            <section className="finance-panel">
              <div className="finance-section-heading"><div><p className="eyebrow">Stay intentional</p><h2>Monthly plan</h2></div></div>
              <form className="finance-form" onSubmit={handlePlanSubmit}>
                <label>Planned income<input min="0" name="planned_income" onChange={(event) => setPlanAmount('planned_income', event.target.value)} step="0.01" type="number" value={plan.planned_income} /></label>
                <label>Spending limit<input min="0" name="spending_limit" onChange={(event) => setPlanAmount('spending_limit', event.target.value)} step="0.01" type="number" value={plan.spending_limit} /></label>
                <label>Savings target<input min="0" name="savings_target" onChange={(event) => setPlanAmount('savings_target', event.target.value)} step="0.01" type="number" value={plan.savings_target} /></label>
                <label>Investment target<input min="0" name="investment_target" onChange={(event) => setPlanAmount('investment_target', event.target.value)} step="0.01" type="number" value={plan.investment_target} /></label>
                <label>Loan repayment target<input min="0" name="loan_repayment_target" onChange={(event) => setPlanAmount('loan_repayment_target', event.target.value)} step="0.01" type="number" value={plan.loan_repayment_target} /></label>
                <button className="primary-button" disabled={busy} type="submit">Save monthly plan</button>
              </form>
            </section>
            <section className="finance-panel">
              <div className="finance-section-heading"><div><p className="eyebrow">Category limits</p><h2>Budgets</h2></div></div>
              <form className="finance-form finance-inline-form" onSubmit={handleBudgetSubmit}>
                <label>Category<select name="category_id" required>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
                <label>Monthly limit<input min="0.01" name="monthly_limit" required step="0.01" type="number" /></label>
                <button className="secondary-button" disabled={busy} type="submit">Set budget</button>
              </form>
              <div className="finance-budget-list">
                {budgets.map((budget) => {
                  const spent = amount(budget.spent)
                  const limit = amount(budget.monthly_limit)
                  const percent = limit > 0 ? Math.min(100, (spent / limit) * 100) : 0
                  return <article className="finance-budget-item" key={budget.id}>
                    <div><strong>{categoryNames.get(budget.category_id) ?? 'Category'}</strong><span>{money(spent)} / {money(limit)}</span></div>
                    <div aria-label={`${Math.round(percent)}% used`} className="finance-progress"><span style={{ width: `${percent}%` }} /></div>
                  </article>
                })}
                {!budgets.length && <p className="finance-empty">No budgets set for this month yet.</p>}
              </div>
            </section>
          </div>

          <section className="finance-panel">
            <div className="finance-section-heading"><div><p className="eyebrow">Understand your habits</p><h2>Spending by category</h2></div></div>
            <div className="finance-category-chart">
              {topCategories.map(([name, total]) => {
                const max = Math.max(...topCategories.map(([, value]) => amount(value)), 1)
                return <div className="finance-chart-row" key={name}><span>{name}</span><div><i style={{ width: `${Math.max(2, amount(total) / max * 100)}%` }} /></div><strong>{money(total)}</strong></div>
              })}
              {!topCategories.length && <p className="finance-empty">Record expenses to see category spending.</p>}
            </div>
          </section>

          <section className="finance-columns">
            <div className="finance-panel">
              <div className="finance-section-heading"><div><p className="eyebrow">Log a purchase</p><h2>Add expense</h2></div></div>
              <form className="finance-form" onSubmit={handleExpenseSubmit}>
                <label>Amount (INR)<input min="0.01" name="amount" required step="0.01" type="number" /></label>
                <label>Category<select name="category_id" required>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
                <label>Merchant<input maxLength={200} name="merchant" placeholder="Store or service" /></label>
                <label>Payment card<select defaultValue="" name="credit_card_id"><option value="">Not a card / unspecified</option>{cards.map((card) => <option key={card.id} value={card.id}>{card.card_name} ···· {card.last_four_digits ?? '----'}</option>)}</select></label>
                <label>Date<input defaultValue={currentDate} name="expense_date" required type="date" /></label>
                <label>Notes<input maxLength={10000} name="notes" /></label>
                <button className="primary-button" disabled={busy || !categories.length} type="submit">Record expense</button>
              </form>
            </div>
            <div className="finance-panel">
              <div className="finance-section-heading"><div><p className="eyebrow">Plan and actual</p><h2>Income, saving & loans</h2></div></div>
              <form className="finance-form" onSubmit={handleEntrySubmit}>
                <label>Entry type<select name="entry_type">{entryTypes.map((entryType) => <option key={entryType.value} value={entryType.value}>{entryType.label}</option>)}</select></label>
                <label>Amount (INR)<input min="0.01" name="amount" required step="0.01" type="number" /></label>
                <label>Source<input maxLength={200} name="source" placeholder="Employer, bank, loan…" required /></label>
                <label>Date<input defaultValue={currentDate} name="entry_date" required type="date" /></label>
                <label>Notes<input maxLength={10000} name="notes" /></label>
                <button className="primary-button" disabled={busy} type="submit">Save entry</button>
              </form>
              <EntryList entries={entries} />
            </div>
          </section>

          <section className="finance-panel">
            <div className="finance-section-heading"><div><p className="eyebrow">Recent activity</p><h2>Expenses</h2></div><button className="secondary-button" onClick={() => void downloadCsv()} type="button">Export CSV</button></div>
            <div className="finance-filters">
              <label>Filter category<select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
              <label>Search merchant or notes<input onChange={(event) => setExpenseSearch(event.target.value)} placeholder="Search expenses" value={expenseSearch} /></label>
            </div>
            <ExpenseList expenses={visibleExpenses} categoryNames={categoryNames} onDelete={(id) => void removeExpense(id)} />
          </section>

          <section className="finance-columns">
            <div className="finance-panel">
              <div className="finance-section-heading"><div><p className="eyebrow">Due-date reminders</p><h2>Credit cards</h2></div></div>
              <form className="finance-form" onSubmit={handleCardSubmit}>
                <label>Card name<input maxLength={100} name="card_name" required /></label>
                <label>Bank<input maxLength={80} name="bank_name" required /></label>
                <label>Last four digits<input maxLength={4} name="last_four_digits" pattern="[0-9]{4}" /></label>
                <label>Credit limit<input min="0.01" name="credit_limit" required step="0.01" type="number" /></label>
                <label>Current balance<input min="0" name="current_balance" step="0.01" type="number" defaultValue="0" /></label>
                <div className="finance-form-row"><label>Billing day<input max="31" min="1" name="billing_date" required type="number" /></label><label>Due day<input max="31" min="1" name="due_date" required type="number" /></label></div>
                <button className="primary-button" disabled={busy} type="submit">Add card</button>
              </form>
              <CardList cards={cards} onDelete={(id) => void removeCard(id)} />
            </div>
            <div className="finance-panel">
              <div className="finance-section-heading"><div><p className="eyebrow">Personal categories</p><h2>Manage categories</h2></div></div>
              <form className="finance-form finance-inline-form" onSubmit={handleCategorySubmit}>
                <label>New category<input maxLength={80} name="name" placeholder="e.g. Pet care" required /></label>
                <button className="secondary-button" disabled={busy} type="submit">Add category</button>
              </form>
              <ul className="finance-category-tags">{categories.map((category) => <li key={category.id}>{category.name}{category.is_system && <small>Default</small>}</li>)}</ul>
              <p className="finance-footnote">Amounts are stored in INR. Budget alerts appear in your LifeOS notification centre when you reach 80% and 100% of a category limit.</p>
            </div>
          </section>
        </>
      )}
    </main>
  )
}

function Metric({ label, actual, target }: { label: string; actual: string | number; target?: string | number }) {
  return <article className="finance-metric"><span>{label}</span><strong>{money(actual)}</strong><small>{target === undefined ? 'Actual recorded' : `Target ${money(target)}`}</small></article>
}

function ExpenseList({
  expenses,
  categoryNames,
  onDelete,
}: {
  expenses: FinanceExpense[]
  categoryNames: Map<string, string>
  onDelete: (id: string) => void
}) {
  if (!expenses.length) return <p className="finance-empty">No expenses match this month and filter.</p>
  return <div className="finance-activity-list">{expenses.map((expense) => <article className="finance-activity-row" key={expense.id}>
    <div><strong>{expense.merchant || categoryNames.get(expense.category_id) || 'Expense'}</strong><span>{categoryNames.get(expense.category_id) ?? 'Category'} · {expense.expense_date}</span></div>
    <strong>{money(expense.amount)}</strong>
    <button aria-label={`Delete expense at ${expense.merchant || 'merchant'}`} className="finance-delete-button" onClick={() => onDelete(expense.id)} type="button">Delete</button>
  </article>)}</div>
}

function EntryList({ entries }: { entries: FinanceEntry[] }) {
  if (!entries.length) return <p className="finance-empty">No income, savings, investments or loan entries this month.</p>
  return <div className="finance-activity-list">{entries.map((entry) => <article className="finance-activity-row" key={entry.id}>
    <div><strong>{entryTypes.find(({ value }) => value === entry.entry_type)?.label ?? entry.entry_type}</strong><span>{entry.source} · {entry.entry_date}</span></div>
    <strong>{money(entry.amount)}</strong>
  </article>)}</div>
}

function CardList({ cards, onDelete }: { cards: FinanceCard[]; onDelete: (id: string) => void }) {
  if (!cards.length) return <p className="finance-empty">Add a card to keep its basic billing and due dates together.</p>
  return <div className="finance-activity-list">{cards.map((card) => <article className="finance-activity-row" key={card.id}>
    <div><strong>{card.card_name} · {card.bank_name}</strong><span>Due in {cardDueDays(card.due_date)} days · Balance {money(card.current_balance)} of {money(card.credit_limit)}</span></div>
    <button aria-label={`Remove ${card.card_name}`} className="finance-delete-button" onClick={() => onDelete(card.id)} type="button">Remove</button>
  </article>)}</div>
}

function cardDueDays(dueDay: number): number {
  const now = new Date()
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  let dueDate = new Date(now.getFullYear(), now.getMonth(), Math.min(dueDay, lastDay))
  if (dueDate < new Date(now.getFullYear(), now.getMonth(), now.getDate())) {
    const nextMonthLastDay = new Date(now.getFullYear(), now.getMonth() + 2, 0).getDate()
    dueDate = new Date(now.getFullYear(), now.getMonth() + 1, Math.min(dueDay, nextMonthLastDay))
  }
  return Math.round((dueDate.getTime() - new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()) / 86_400_000)
}
