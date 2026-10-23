import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/context'
import {
  createFinanceCategory, createFinanceEntry, createFinanceExpense, deleteFinanceExpense,
  exportFinanceExpenses, fetchFinanceBudgets, fetchFinanceCategories, fetchFinanceEntries,
  fetchFinanceExpenses, fetchFinancePlan, fetchFinanceSummary, saveFinanceBudget, saveFinancePlan,
  type FinanceBudget, type FinanceCategory, type FinanceEntry, type FinanceEntryType,
  type FinanceExpense, type FinancePlan, type FinanceSummary,
} from '../api/finance'

const today = new Date()
const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`
const currentDate = today.toLocaleDateString('en-CA')
const entryTypes: { value: FinanceEntryType; label: string }[] = [
  { value: 'income', label: 'Income' }, { value: 'saving', label: 'Savings' }, { value: 'investment', label: 'Investment' },
]
const emptyPlan = (year: number, month: number): FinancePlan => ({ budget_month: month, budget_year: year, planned_income: '0', spending_limit: '0', savings_target: '0', investment_target: '0', loan_repayment_target: '0' })
const amount = (value: string | number | undefined) => Number(value ?? 0)
const money = (value: string | number | undefined) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount(value))
const field = (form: HTMLFormElement, name: string) => String(new FormData(form).get(name) ?? '').trim()

export function FinancePage() {
  const { accessToken } = useAuth()
  const [selectedMonth, setSelectedMonth] = useState(currentMonth)
  const [summary, setSummary] = useState<FinanceSummary | null>(null)
  const [categories, setCategories] = useState<FinanceCategory[]>([])
  const [expenses, setExpenses] = useState<FinanceExpense[]>([])
  const [budgets, setBudgets] = useState<FinanceBudget[]>([])
  const [entries, setEntries] = useState<FinanceEntry[]>([])
  const [plan, setPlan] = useState<FinancePlan>(emptyPlan(today.getFullYear(), today.getMonth() + 1))
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')
  const [isEmi, setIsEmi] = useState(false)
  const [year, month] = selectedMonth.split('-').map(Number)

  const reload = useCallback(async () => {
    if (!accessToken) return
    const [summaryData, categoryData, expenseData, budgetData, entryData, savedPlan] = await Promise.all([
      fetchFinanceSummary(accessToken, year, month), fetchFinanceCategories(accessToken), fetchFinanceExpenses(accessToken, year, month),
      fetchFinanceBudgets(accessToken, year, month), fetchFinanceEntries(accessToken, year, month), fetchFinancePlan(accessToken, year, month),
    ])
    setSummary(summaryData); setCategories(categoryData); setExpenses(expenseData.items); setBudgets(budgetData); setEntries(entryData)
    setPlan(savedPlan ?? emptyPlan(year, month))
  }, [accessToken, month, year])

  useEffect(() => {
    let active = true
    setLoading(true); setError('')
    reload().catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : 'Could not load your money overview.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [reload])

  const categoryNames = useMemo(() => new Map(categories.map((item) => [item.id, item.name])), [categories])
  const visibleExpenses = useMemo(() => expenses.filter((item) => (!filter || item.category_id === filter) && (!search || `${item.merchant ?? ''} ${item.notes ?? ''}`.toLowerCase().includes(search.toLowerCase()))), [expenses, filter, search])

  async function perform(action: () => Promise<unknown>, message: string) {
    setBusy(true); setError(''); setNotice('')
    try { await action(); await reload(); setNotice(message) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save that change.') }
    finally { setBusy(false) }
  }

  function saveExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceExpense(accessToken, { category_id: field(form, 'category_id'), credit_card_id: null, amount: field(form, 'amount'), merchant: field(form, 'merchant') || null, payment_method: field(form, 'payment_method') as 'debit_card' | 'credit_card' | 'cash' | 'bank_transfer' | 'upi' | 'other', is_monthly_emi: form.elements.namedItem('is_monthly_emi') instanceof HTMLInputElement && (form.elements.namedItem('is_monthly_emi') as HTMLInputElement).checked, emi_end_date: field(form, 'emi_end_date') || null, notes: field(form, 'notes') || null, expense_date: field(form, 'expense_date') }), 'Expense added.')
    form.reset()
    setIsEmi(false)
  }

  function saveEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceEntry(accessToken, { entry_type: field(form, 'entry_type') as FinanceEntryType, amount: field(form, 'amount'), source: field(form, 'source') || (field(form, 'entry_type') === 'income' ? 'Other income' : field(form, 'entry_type')), notes: field(form, 'notes') || null, entry_date: field(form, 'entry_date') }), 'Entry added.')
    form.reset()
  }

  function savePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!accessToken) return
    const form = event.currentTarget
    const updated = { ...plan, planned_income: field(form, 'planned_income') || '0', spending_limit: field(form, 'spending_limit') || '0', savings_target: field(form, 'savings_target') || '0', investment_target: field(form, 'investment_target') || '0' }
    void perform(() => saveFinancePlan(accessToken, updated), 'Monthly budget saved.')
  }

  function saveBudget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!accessToken) return
    const form = event.currentTarget
    void perform(() => saveFinanceBudget(accessToken, { category_id: field(form, 'category_id'), monthly_limit: field(form, 'monthly_limit'), budget_month: month, budget_year: year }), 'Category budget saved.')
    form.reset()
  }

  function saveCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!accessToken) return
    const form = event.currentTarget
    void perform(() => createFinanceCategory(accessToken, { name: field(form, 'name'), icon: null, colour_hex: '#6B7280' }), 'Category added.')
    form.reset()
  }

  async function deleteExpense(id: string) {
    if (!accessToken || !window.confirm('Delete this expense?')) return
    await perform(() => deleteFinanceExpense(accessToken, id), 'Expense removed.')
  }

  async function downloadCsv() {
    if (!accessToken) return
    try { const blob = await exportFinanceExpenses(accessToken); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'lifeos-expenses.csv'; a.click(); URL.revokeObjectURL(url) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not export expenses.') }
  }

  if (loading) return <main className="page-content"><p className="welcome-copy">Loading your money overview…</p></main>
  const monthLabel = new Date(year, month - 1).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
  const remaining = amount(summary?.remaining)
  const limit = amount(summary?.spending_limit)
  const spentPercent = limit > 0 ? Math.min(100, amount(summary?.actual_spent) / limit * 100) : 0

  return <main className="page-content finance-page">
    <header className="finance-heading"><div><p className="eyebrow">A clear picture of your money</p><h1>Finance</h1><p className="welcome-copy">See what came in, what went out, and what you have left this month.</p></div><label className="finance-month-picker"><span>Month</span><input type="month" value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)} /></label></header>
    {error && <p className="form-message form-message-error" role="alert">{error}</p>}{notice && <p className="form-message form-message-success" role="status">{notice}</p>}
    {!categories.length && <p className="welcome-copy">Your expense categories are being set up. Refresh after the database migration is applied.</p>}
    {summary && <>
      <section className="finance-panel finance-overview" aria-label="Monthly money overview">
        <div className="finance-section-heading"><div><p className="eyebrow">Your month</p><h2>{monthLabel}</h2></div></div>
        <div className="finance-metrics">
          <Metric label="Expected income" actual={summary.planned_income} actualLabel="planned" />
          <Metric label="Income received" actual={summary.actual_income} />
          <Metric label="Spent" actual={summary.actual_spent} />
          <Metric label="Budget left" actual={summary.remaining} actualLabel={remaining < 0 ? 'over budget' : 'remaining'} />
        </div>
        <div className="finance-budget-status"><div><strong>{money(summary.actual_spent)}</strong><span> spent of {money(summary.spending_limit)} budget</span></div><strong>{Math.round(spentPercent)}%</strong><div className="finance-progress" aria-label={`${Math.round(spentPercent)}% of budget used`}><span style={{ width: `${spentPercent}%` }} /></div></div>
        <div className="finance-goal-row"><span>Savings target <strong>{money(summary.savings_target)}</strong></span><span>Saved <strong>{money(summary.actual_saved)}</strong></span><span>Investment target <strong>{money(summary.investment_target)}</strong></span><span>Invested <strong>{money(summary.actual_invested)}</strong></span></div>
      </section>

      <section className="finance-columns">
        <section className="finance-panel"><div className="finance-section-heading"><div><p className="eyebrow">Quick add</p><h2>Record an expense</h2></div></div>
          <form className="finance-form" onSubmit={saveExpense}>
            <label>Amount (₹)<input min="0.01" name="amount" required step="0.01" type="number" /></label>
            <label>What was it for?<select name="category_id" required>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <label>Paid with<select name="payment_method" defaultValue="upi"><option value="upi">UPI</option><option value="debit_card">Debit card</option><option value="credit_card">Credit card</option><option value="cash">Cash</option><option value="bank_transfer">Bank transfer</option><option value="other">Other</option></select></label>
            <label>Place or note<input maxLength={200} name="merchant" placeholder="Optional" /></label>
            <label>Date<input defaultValue={currentDate} name="expense_date" required type="date" /></label>
            <label className="finance-checkbox"><input checked={isEmi} name="is_monthly_emi" onChange={(event) => setIsEmi(event.target.checked)} type="checkbox" /> This is a monthly EMI</label>
            {isEmi && <label>Expected EMI end date<input min={currentDate} name="emi_end_date" required type="date" /></label>}
            <button className="primary-button" disabled={busy || !categories.length} type="submit">Add expense</button>
          </form>
        </section>
        <section className="finance-panel"><div className="finance-section-heading"><div><p className="eyebrow">Money in and goals</p><h2>Record income or progress</h2></div></div>
          <form className="finance-form" onSubmit={saveEntry}>
            <label>Record<select name="entry_type">{entryTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            <label>Amount (₹)<input min="0.01" name="amount" required step="0.01" type="number" /></label>
            <label>Source or where it went<input maxLength={100} name="source" placeholder="Salary, freelance, emergency fund…" /></label>
            <label>Date<input defaultValue={currentDate} name="entry_date" required type="date" /></label>
            <button className="primary-button" disabled={busy} type="submit">Save entry</button>
          </form>
        </section>
      </section>

      <section className="finance-panel"><div className="finance-section-heading"><div><p className="eyebrow">This month</p><h2>Recent expenses</h2></div><button className="secondary-button" onClick={() => void downloadCsv()} type="button">Export CSV</button></div>
        <div className="finance-filters"><label>Category<select value={filter} onChange={(event) => setFilter(event.target.value)}><option value="">All categories</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Find an expense<input onChange={(event) => setSearch(event.target.value)} placeholder="Search" value={search} /></label></div>
        {!visibleExpenses.length ? <p className="finance-empty">No expenses recorded for this month yet.</p> : <div className="finance-activity-list">{visibleExpenses.map((item) => <article className="finance-activity-row" key={item.id}><div><strong>{item.merchant || categoryNames.get(item.category_id) || 'Expense'}</strong><span>{categoryNames.get(item.category_id)} · {item.expense_date}{item.payment_method ? ` · ${paymentLabel(item.payment_method)}` : ''}{item.is_monthly_emi ? ` · Monthly EMI${item.emi_end_date ? ` until ${item.emi_end_date}` : ''}` : ''}</span></div><strong>{money(item.amount)}</strong><button className="finance-delete-button" onClick={() => void deleteExpense(item.id)} type="button">Delete</button></article>)}</div>}
      </section>
      <details className="finance-advanced"><summary>Monthly plan and category budgets</summary><div className="finance-columns">
        <section className="finance-panel"><p className="finance-empty">Set expected income, your total spending budget, and monthly savings and investment goals.</p><form className="finance-form" onSubmit={savePlan}><label>Expected income<input min="0" name="planned_income" type="number" value={plan.planned_income} onChange={(event) => setPlan({ ...plan, planned_income: event.target.value })} /></label><label>Monthly spending budget<input min="0" name="spending_limit" type="number" value={plan.spending_limit} onChange={(event) => setPlan({ ...plan, spending_limit: event.target.value })} /></label><label>Savings target<input min="0" name="savings_target" type="number" value={plan.savings_target} onChange={(event) => setPlan({ ...plan, savings_target: event.target.value })} /></label><label>Investment target<input min="0" name="investment_target" type="number" value={plan.investment_target} onChange={(event) => setPlan({ ...plan, investment_target: event.target.value })} /></label><button className="primary-button" disabled={busy} type="submit">Save monthly plan</button></form></section>
        <section className="finance-panel"><h2>Optional category budgets</h2><form className="finance-form finance-inline-form" onSubmit={saveBudget}><label>Category<select name="category_id" required>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Monthly limit<input min="0.01" name="monthly_limit" required step="0.01" type="number" /></label><button className="secondary-button" disabled={busy} type="submit">Add limit</button></form>{budgets.map((item) => <p className="finance-budget-item" key={item.id}><strong>{categoryNames.get(item.category_id)}</strong><span>{money(item.spent)} / {money(item.monthly_limit)}</span></p>)}<form className="finance-form finance-inline-form" onSubmit={saveCategory}><label>Add your own category<input maxLength={80} name="name" placeholder="e.g. Pet care" required /></label><button className="secondary-button" disabled={busy} type="submit">Add category</button></form></section>
      </div><h3>Income, savings and investment activity</h3>{entries.length ? <div className="finance-activity-list">{entries.map((entry) => <article className="finance-activity-row" key={entry.id}><div><strong>{entryTypes.find((item) => item.value === entry.entry_type)?.label ?? entry.entry_type}</strong><span>{entry.source} · {entry.entry_date}</span></div><strong>{money(entry.amount)}</strong></article>)}</div> : <p className="finance-empty">No income or goal entries recorded this month.</p>}</details>
    </>}
  </main>
}

function Metric({ label, actual, actualLabel }: { label: string; actual: string | number; actualLabel?: string }) {
  return <article className="finance-metric"><span>{label}</span><strong>{money(actual)}</strong><small>{actualLabel ?? 'recorded this month'}</small></article>
}

function paymentLabel(value: string) {
  return ({ debit_card: 'Debit card', credit_card: 'Credit card', cash: 'Cash', bank_transfer: 'Bank transfer', upi: 'UPI', other: 'Other' } as Record<string, string>)[value] ?? value
}
