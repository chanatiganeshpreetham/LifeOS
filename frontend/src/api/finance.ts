import { apiDownload, apiRequest } from './client'

export type Amount = number | string
export type FinanceEntryType =
  | 'income'
  | 'saving'
  | 'investment'
  | 'loan_borrowed'
  | 'loan_repayment'

export interface FinanceCategory {
  id: string
  name: string
  icon: string | null
  colour_hex: string
  is_system: boolean
}

export interface FinanceExpense {
  id: string
  category_id: string
  credit_card_id: string | null
  amount: Amount
  currency: string
  merchant: string | null
  notes: string | null
  expense_date: string
  created_at: string
}

export interface FinanceBudget {
  id: string
  category_id: string
  monthly_limit: Amount
  budget_month: number
  budget_year: number
  spent: Amount
}

export interface FinancePlan {
  id?: string
  budget_month: number
  budget_year: number
  planned_income: Amount
  spending_limit: Amount
  savings_target: Amount
  investment_target: Amount
  loan_repayment_target: Amount
}

export interface FinanceEntry {
  id: string
  entry_type: FinanceEntryType
  amount: Amount
  source: string
  notes: string | null
  entry_date: string
}

export interface FinanceCard {
  id: string
  card_name: string
  bank_name: string
  last_four_digits: string | null
  credit_limit: Amount
  billing_date: number
  due_date: number
  current_balance: Amount
}

export interface FinanceSummary {
  budget_month?: number
  budget_year: number
  planned_income: Amount
  actual_income: Amount
  spending_limit: Amount
  actual_spent: Amount
  remaining: Amount
  savings_target: Amount
  actual_saved: Amount
  investment_target: Amount
  actual_invested: Amount
  loan_repayment_target: Amount
  actual_repaid: Amount
  actual_borrowed: Amount
  category_spending: Record<string, Amount>
}

export interface FinanceDashboardSummary {
  date: string
  today_spent: Amount
  month_spent: Amount
  monthly_spending_limit: Amount | null
  budget_source: 'monthly_plan' | 'category_budgets' | null
  cards_due: {
    id: string
    card_name: string
    bank_name: string
    last_four_digits: string | null
    current_balance: Amount
    due_date: string
    days_until_due: number
  }[]
}

export interface FinanceExpenseList {
  items: FinanceExpense[]
  total: number
}

export function fetchFinanceSummary(
  token: string,
  year: number,
  month: number,
): Promise<FinanceSummary> {
  return apiRequest(`/finance/summary?year=${year}&month=${month}`, {}, token)
}

export function fetchFinanceDashboardSummary(token: string): Promise<FinanceDashboardSummary> {
  return apiRequest('/finance/dashboard-summary', {}, token)
}

export function fetchFinanceYearSummary(token: string, year: number): Promise<FinanceSummary> {
  return apiRequest(`/finance/summary/yearly?year=${year}`, {}, token)
}

export function fetchFinanceCategories(token: string): Promise<FinanceCategory[]> {
  return apiRequest('/finance/categories', {}, token)
}

export function createFinanceCategory(
  token: string,
  input: { name: string; icon: string | null; colour_hex: string },
): Promise<FinanceCategory> {
  return apiRequest('/finance/categories', { method: 'POST', body: JSON.stringify(input) }, token)
}

export function fetchFinanceExpenses(
  token: string,
  year: number,
  month: number,
): Promise<FinanceExpenseList> {
  const endOfMonth = new Date(year, month, 0).getDate()
  const start = `${year}-${String(month).padStart(2, '0')}-01`
  const end = `${year}-${String(month).padStart(2, '0')}-${String(endOfMonth).padStart(2, '0')}`
  const query = new URLSearchParams({ date_from: start, date_to: end, limit: '500' })
  return apiRequest(`/finance/expenses?${query}`, {}, token)
}

export function createFinanceExpense(
  token: string,
  input: {
    category_id: string
    credit_card_id: string | null
    amount: string
    merchant: string | null
    notes: string | null
    expense_date: string
  },
): Promise<FinanceExpense> {
  return apiRequest('/finance/expenses', { method: 'POST', body: JSON.stringify(input) }, token)
}

export function deleteFinanceExpense(token: string, expenseId: string): Promise<void> {
  return apiRequest(`/finance/expenses/${expenseId}`, { method: 'DELETE' }, token)
}

export function exportFinanceExpenses(token: string): Promise<Blob> {
  return apiDownload('/finance/expenses/export.csv', token)
}

export function fetchFinanceBudgets(
  token: string,
  year: number,
  month: number,
): Promise<FinanceBudget[]> {
  return apiRequest(`/finance/budgets?year=${year}&month=${month}`, {}, token)
}

export function saveFinanceBudget(
  token: string,
  input: { category_id: string; monthly_limit: string; budget_month: number; budget_year: number },
): Promise<FinanceBudget> {
  return apiRequest('/finance/budgets', { method: 'PUT', body: JSON.stringify(input) }, token)
}

export function fetchFinancePlan(
  token: string,
  year: number,
  month: number,
): Promise<FinancePlan | null> {
  return apiRequest(`/finance/plan?year=${year}&month=${month}`, {}, token)
}

export function saveFinancePlan(token: string, input: FinancePlan): Promise<FinancePlan> {
  return apiRequest('/finance/plan', { method: 'PUT', body: JSON.stringify(input) }, token)
}

export function fetchFinanceEntries(
  token: string,
  year: number,
  month: number,
): Promise<FinanceEntry[]> {
  return apiRequest(`/finance/entries?year=${year}&month=${month}`, {}, token)
}

export function createFinanceEntry(
  token: string,
  input: {
    entry_type: FinanceEntryType
    amount: string
    source: string
    notes: string | null
    entry_date: string
  },
): Promise<FinanceEntry> {
  return apiRequest('/finance/entries', { method: 'POST', body: JSON.stringify(input) }, token)
}

export function fetchFinanceCards(token: string): Promise<FinanceCard[]> {
  return apiRequest('/finance/cards', {}, token)
}

export function createFinanceCard(
  token: string,
  input: {
    card_name: string
    bank_name: string
    last_four_digits: string | null
    credit_limit: string
    billing_date: number
    due_date: number
    current_balance: string
  },
): Promise<FinanceCard> {
  return apiRequest('/finance/cards', { method: 'POST', body: JSON.stringify(input) }, token)
}

export function deleteFinanceCard(token: string, cardId: string): Promise<void> {
  return apiRequest(`/finance/cards/${cardId}`, { method: 'DELETE' }, token)
}
