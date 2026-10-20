import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/context'

const {
  createTask,
  fetchFinanceDashboardSummary,
  fetchHealthToday,
  fetchDashboardReminders,
  fetchSleepLogs,
  fetchTaskDashboard,
} = vi.hoisted(() => ({
  createTask: vi.fn(),
  fetchFinanceDashboardSummary: vi.fn(),
  fetchHealthToday: vi.fn(),
  fetchDashboardReminders: vi.fn(),
  fetchSleepLogs: vi.fn(),
  fetchTaskDashboard: vi.fn(),
}))

vi.mock('../api/finance', () => ({ fetchFinanceDashboardSummary }))
vi.mock('../api/healthTracking', () => ({ fetchHealthToday, fetchSleepLogs }))
vi.mock('../api/reminders', () => ({ fetchDashboardReminders }))
vi.mock('../api/tasks', () => ({ createTask, fetchTaskDashboard }))
vi.mock('../components/ApiHealthStatus', () => ({
  ApiHealthStatus: () => <div>API status</div>,
}))

import { DashboardPage } from './DashboardPage'

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <AuthContext.Provider value={{
      accessToken: 'dashboard-token',
      user: {
        id: 'user-1',
        email: 'person@example.com',
        full_name: 'Taylor Person',
        avatar_url: null,
        timezone: 'Asia/Kolkata',
        is_verified: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
      signIn: async () => {},
      signUp: async () => {},
      signOut: async () => {},
    }}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <DashboardPage onSignOut={() => {}} signOutError="" />
        </MemoryRouter>
      </QueryClientProvider>
    </AuthContext.Provider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  fetchTaskDashboard.mockResolvedValue({ open_count: 2, overdue_count: 1, upcoming: [] })
  fetchDashboardReminders.mockResolvedValue({ items: [], total: 0 })
  fetchFinanceDashboardSummary.mockResolvedValue({
    date: '2026-10-20',
    today_spent: '120',
    month_spent: '4500',
    monthly_spending_limit: '10000',
    budget_source: 'monthly_plan',
    cards_due: [],
  })
  fetchHealthToday.mockResolvedValue({
    date: '2026-10-20',
    mood_score: 4,
    water_total_ml: 1000,
    water_goal_ml: 2000,
    habits_completed: 1,
    habits_total: 2,
  })
  fetchSleepLogs.mockResolvedValue({
    items: [{
      id: 'sleep-1',
      bedtime: '2026-10-19T22:00:00Z',
      wake_time: '2026-10-20T06:00:00Z',
      duration_hours: 8,
      quality_rating: 4,
      sleep_date: '2026-10-20',
      created_at: new Date().toISOString(),
    }],
  })
})

afterEach(() => cleanup())

describe('DashboardPage', () => {
  it('renders real module summaries and links into each feature', async () => {
    renderDashboard()

    expect(await screen.findByText('2')).toBeInTheDocument()
    expect(screen.getByText('1 overdue')).toBeInTheDocument()
    expect(screen.getByText('Spent today')).toBeInTheDocument()
    expect(screen.getByText('1,000 / 2,000 ml')).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Tasks' })).getByRole('link')).toHaveAttribute('href', '/tasks')
    expect(within(screen.getByRole('region', { name: 'Reminders' })).getByRole('link')).toHaveAttribute('href', '/reminders')
    expect(within(screen.getByRole('region', { name: 'Finance' })).getByRole('link')).toHaveAttribute('href', '/finance')
    expect(within(screen.getByRole('region', { name: 'Health' })).getByRole('link')).toHaveAttribute('href', '/health')
    expect(screen.getByRole('link', { name: /daybook/i })).toHaveAttribute('href', '/daybook')
  })

  it('allows retrying a failed widget independently', async () => {
    fetchTaskDashboard
      .mockRejectedValueOnce(new Error('Tasks are temporarily unavailable.'))
      .mockResolvedValueOnce({ open_count: 0, overdue_count: 0, upcoming: [] })
    renderDashboard()

    expect(await screen.findByText('Tasks are temporarily unavailable.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    await waitFor(() => expect(fetchTaskDashboard).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('You’re all caught up.')).toBeInTheDocument()
  })

  it('creates a task from the dashboard and refreshes only the task widget', async () => {
    createTask.mockResolvedValue({ id: 'task-1' })
    renderDashboard()

    const input = await screen.findByLabelText('Add a task')
    fireEvent.change(input, { target: { value: 'Call the dentist' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create task' }))

    await waitFor(() => {
      expect(createTask).toHaveBeenCalledWith('dashboard-token', {
        title: 'Call the dentist',
        notes: null,
        priority: 'medium',
        due_at: null,
      })
    })
    await waitFor(() => expect(fetchTaskDashboard).toHaveBeenCalledTimes(2))
  })
})
