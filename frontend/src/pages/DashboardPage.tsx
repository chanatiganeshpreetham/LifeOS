import { useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/context'
import { fetchFinanceDashboardSummary } from '../api/finance'
import { fetchHealthToday, fetchSleepLogs } from '../api/healthTracking'
import { fetchDashboardReminders } from '../api/reminders'
import { createTask, fetchTaskDashboard } from '../api/tasks'
import { ApiHealthStatus } from '../components/ApiHealthStatus'

interface DashboardPageProps {
  onSignOut: () => void
  signOutError: string
}

function money(value: number | string): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value))
}

function localDateKey(date: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en', {
    day: '2-digit',
    month: '2-digit',
    timeZone,
    year: 'numeric',
  }).formatToParts(date)
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''
  return `${value('year')}-${value('month')}-${value('day')}`
}

function displayDate(value: string, timeZone: string): string {
  const isCalendarDate = /^\d{4}-\d{2}-\d{2}$/.test(value)
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    timeZone: isCalendarDate ? 'UTC' : timeZone,
  }).format(new Date(isCalendarDate ? `${value}T12:00:00Z` : value))
}

function Widget({
  title,
  description,
  href,
  isPending,
  error,
  retry,
  children,
}: {
  title: string
  description: string
  href: string
  isPending: boolean
  error: Error | null
  retry: () => void
  children: ReactNode
}) {
  return (
    <section aria-label={title} className="dashboard-widget">
      <header className="dashboard-widget-header">
        <div>
          <p className="dashboard-widget-description">{description}</p>
          <h2>{title}</h2>
        </div>
        <Link className="dashboard-widget-link" to={href}>Open <span aria-hidden="true">↗</span></Link>
      </header>
      {isPending ? (
        <div aria-label={`Loading ${title.toLowerCase()}`} className="dashboard-widget-skeleton" role="status">
          <span /><span /><span />
        </div>
      ) : error ? (
        <div className="dashboard-widget-error" role="alert">
          <p>{error.message}</p>
          <button className="secondary-button" onClick={retry} type="button">Try again</button>
        </div>
      ) : children}
    </section>
  )
}

export function DashboardPage({ onSignOut, signOutError }: DashboardPageProps) {
  const { accessToken, user } = useAuth()
  const queryClient = useQueryClient()
  const [taskTitle, setTaskTitle] = useState('')
  const [taskError, setTaskError] = useState('')
  const [isCreatingTask, setIsCreatingTask] = useState(false)
  const timeZone = user?.timezone ?? 'Asia/Kolkata'
  const today = new Date()
  const todayKey = localDateKey(today, timeZone)
  const localHour = Number(new Intl.DateTimeFormat('en', {
    hour: 'numeric',
    hourCycle: 'h23',
    timeZone,
  }).format(today))
  const greeting = localHour < 12 ? 'Good morning' : localHour < 18 ? 'Good afternoon' : 'Good evening'

  const tasks = useQuery({
    queryKey: ['dashboard-tasks', accessToken],
    queryFn: () => fetchTaskDashboard(accessToken!),
    enabled: Boolean(accessToken),
    refetchInterval: 60_000,
  })
  const reminders = useQuery({
    queryKey: ['dashboard-reminders', accessToken],
    queryFn: () => fetchDashboardReminders(accessToken!),
    enabled: Boolean(accessToken),
    refetchInterval: 60_000,
  })
  const finance = useQuery({
    queryKey: ['dashboard-finance', accessToken],
    queryFn: () => fetchFinanceDashboardSummary(accessToken!),
    enabled: Boolean(accessToken),
    refetchInterval: 60_000,
  })
  const health = useQuery({
    queryKey: ['dashboard-health', accessToken],
    queryFn: async () => {
      const [summary, sleep] = await Promise.all([
        fetchHealthToday(accessToken!),
        fetchSleepLogs(accessToken!, 7),
      ])
      return { summary, sleep: sleep.items[0] ?? null }
    },
    enabled: Boolean(accessToken),
    refetchInterval: 60_000,
  })

  const upcomingTasks = tasks.data?.upcoming ?? []
  const upcomingReminders = (reminders.data?.items ?? [])
    .filter((reminder) => reminder.is_active && new Date(reminder.remind_at).getTime() >= Date.now())
    .sort((left, right) => left.remind_at.localeCompare(right.remind_at))
    .slice(0, 4)
  const waterPercent = health.data?.summary.water_goal_ml
    ? Math.min(100, Math.round(health.data.summary.water_total_ml / health.data.summary.water_goal_ml * 100))
    : 0

  async function quickAddTask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken || !taskTitle.trim()) return
    setIsCreatingTask(true)
    setTaskError('')
    try {
      await createTask(accessToken, {
        title: taskTitle.trim(),
        notes: null,
        priority: 'medium',
        due_at: null,
      })
      setTaskTitle('')
      await queryClient.invalidateQueries({ queryKey: ['dashboard-tasks', accessToken] })
    } catch (cause) {
      setTaskError(cause instanceof Error ? cause.message : 'Could not create the task.')
    } finally {
      setIsCreatingTask(false)
    }
  }

  return (
    <main className="page-content dashboard-page">
      <header className="dashboard-welcome">
        <div>
          <p className="eyebrow">{displayDate(todayKey, timeZone)}</p>
          <h1>{greeting}, {user?.full_name.split(' ')[0] ?? 'there'}.</h1>
          <p className="welcome-copy">Here’s your day at a glance.</p>
        </div>
        <button className="secondary-button dashboard-signout" onClick={onSignOut} type="button">Sign out</button>
      </header>

      {signOutError && <p className="form-message form-message-error" role="alert">{signOutError}</p>}
      <div className="dashboard-grid">
        <Widget
          description="Stay focused"
          error={tasks.error}
          href="/tasks"
          isPending={tasks.isPending}
          retry={() => void tasks.refetch()}
          title="Tasks"
        >
          <div className="dashboard-widget-body">
            <p className="dashboard-stat"><strong>{tasks.data?.open_count ?? 0}</strong><span>open tasks</span></p>
            {(tasks.data?.overdue_count ?? 0) > 0 && (
              <p className="dashboard-overdue">{tasks.data?.overdue_count} overdue</p>
            )}
            {upcomingTasks.length ? (
              <ul className="dashboard-list">
                {upcomingTasks.map((task) => (
                  <li key={task.id}>
                    <span>{task.title}</span>
                    {task.due_at && <time dateTime={task.due_at}>{displayDate(task.due_at, timeZone)}</time>}
                  </li>
                ))}
              </ul>
            ) : <p className="dashboard-empty-copy">{tasks.data?.open_count ? 'No upcoming dated tasks.' : 'You’re all caught up.'}</p>}
            <form className="dashboard-quick-add" onSubmit={(event) => void quickAddTask(event)}>
              <label className="sr-only" htmlFor="dashboard-quick-task">Add a task</label>
              <input
                id="dashboard-quick-task"
                maxLength={500}
                onChange={(event) => setTaskTitle(event.target.value)}
                placeholder="Add a task…"
                value={taskTitle}
              />
              <button aria-label="Create task" disabled={!taskTitle.trim() || isCreatingTask} type="submit">＋</button>
            </form>
            {taskError && <p className="dashboard-inline-error" role="alert">{taskError}</p>}
          </div>
        </Widget>

        <Widget
          description="Coming up"
          error={reminders.error}
          href="/reminders"
          isPending={reminders.isPending}
          retry={() => void reminders.refetch()}
          title="Reminders"
        >
          <div className="dashboard-widget-body">
            {upcomingReminders.length ? (
              <ul className="dashboard-list">
                {upcomingReminders.map((reminder) => (
                  <li key={reminder.id}>
                    <span>{reminder.title}</span>
                    <time dateTime={reminder.remind_at}>
                      {new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone }).format(new Date(reminder.remind_at))}
                    </time>
                  </li>
                ))}
              </ul>
            ) : <p className="dashboard-empty-copy">No upcoming reminders.</p>}
          </div>
        </Widget>

        <Widget
          description="Today and this month"
          error={finance.error}
          href="/finance"
          isPending={finance.isPending}
          retry={() => void finance.refetch()}
          title="Finance"
        >
          <div className="dashboard-widget-body">
            <div className="dashboard-finance-summary">
              <span><small>Spent this month</small><strong>{money(finance.data?.month_spent ?? 0)}</strong></span>
              <span>
                <small>{finance.data?.budget_source === 'category_budgets' ? 'Category budget' : 'Monthly budget'}</small>
                <strong>{finance.data?.monthly_spending_limit == null ? 'Not set' : money(finance.data.monthly_spending_limit)}</strong>
              </span>
              <span><small>Spent today</small><strong>{money(finance.data?.today_spent ?? 0)}</strong></span>
            </div>
            {finance.data?.monthly_spending_limit != null && (
              <p className="dashboard-empty-copy">
                {Number(finance.data.monthly_spending_limit) - Number(finance.data.month_spent) >= 0
                  ? `${money(Number(finance.data.monthly_spending_limit) - Number(finance.data.month_spent))} left in your monthly budget.`
                  : `${money(Number(finance.data.month_spent) - Number(finance.data.monthly_spending_limit))} over your monthly budget.`}
              </p>
            )}
          </div>
        </Widget>

        <Widget
          description="Mood, movement, rest"
          error={health.error}
          href="/health"
          isPending={health.isPending}
          retry={() => void health.refetch()}
          title="Health"
        >
          <div className="dashboard-widget-body">
            <div className="dashboard-health-grid">
              <span><small>Mood</small><strong>{health.data?.summary.mood_score == null ? 'Not logged' : `${health.data.summary.mood_score} / 5`}</strong></span>
              <span><small>Water</small><strong>{(health.data?.summary.water_total_ml ?? 0).toLocaleString()} / {(health.data?.summary.water_goal_ml ?? 0).toLocaleString()} ml</strong></span>
              <span><small>Habits</small><strong>{health.data?.summary.habits_completed ?? 0} / {health.data?.summary.habits_total ?? 0} complete</strong></span>
              <span><small>Latest sleep</small><strong>{health.data?.sleep ? `${health.data.sleep.duration_hours.toFixed(1)} hrs` : 'No sleep log'}</strong></span>
            </div>
            <div aria-label={`Water goal ${waterPercent}% complete`} className="dashboard-water-progress" role="progressbar" aria-valuemax={100} aria-valuemin={0} aria-valuenow={waterPercent}>
              <span style={{ width: `${waterPercent}%` }} />
            </div>
          </div>
        </Widget>
      </div>

      <section aria-label="More from LifeOS" className="dashboard-shortcuts">
        <Link to="/daybook"><span aria-hidden="true">▦</span><strong>Daybook</strong><small>Journal and daily activity</small></Link>
        <Link to="/notes"><span aria-hidden="true">✎</span><strong>Notes</strong><small>Ideas and things to remember</small></Link>
      </section>

      <footer className="dashboard-footer">
        <ApiHealthStatus />
      </footer>
    </main>
  )
}
