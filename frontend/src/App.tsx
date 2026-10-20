import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useState } from 'react'
import { ApiHealthStatus } from './components/ApiHealthStatus'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/context'
import { NotificationsBell } from './components/NotificationsBell'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { TasksPage } from './pages/TasksPage'
import { RemindersPage } from './pages/RemindersPage'
import { FinancePage } from './pages/FinancePage'
import { HealthPage } from './pages/HealthPage'
import { NotesPage } from './pages/NotesPage'
import { DaybookPage } from './pages/DaybookPage'
import { DashboardPage } from './pages/DashboardPage'

function HomePage() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <main className="page-content mx-auto w-full px-4 sm:px-6">
        <p className="welcome-copy">Preparing your LifeOS…</p>
      </main>
    )
  }
  if (user) {
    return <Navigate replace to="/today" />
  }

  return (
    <main className="page-content mx-auto w-full px-4 sm:px-6">
      <section className="welcome-panel" aria-labelledby="welcome-heading">
        <p className="eyebrow">A calmer way to manage your day</p>
        <h1 id="welcome-heading">Make room for what matters.</h1>
        <p className="welcome-copy">
          LifeOS brings the important parts of everyday life together in one
          thoughtful space.
        </p>
        <div className="home-actions">
          <Link className="primary-button primary-button-link" to="/register">
            Get started
          </Link>
          <Link className="secondary-button" to="/login">
            Sign in
          </Link>
        </div>
        <ApiHealthStatus />
      </section>
    </main>
  )
}

function TodayPage() {
  const { user, isLoading, signOut } = useAuth()
  const [signOutError, setSignOutError] = useState('')
  if (isLoading) {
    return (
      <main className="page-content mx-auto w-full px-4 sm:px-6">
        <p className="welcome-copy">Preparing your LifeOS…</p>
      </main>
    )
  }
  if (!user) {
    return <Navigate replace to="/login" />
  }

  async function handleSignOut() {
    setSignOutError('')
    try {
      await signOut()
    } catch (cause) {
      setSignOutError(cause instanceof Error ? cause.message : 'Could not sign out. Try again.')
    }
  }

  return <DashboardPage onSignOut={() => void handleSignOut()} signOutError={signOutError} />
}

function AuthenticatedTasksPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return (
      <main className="page-content mx-auto w-full px-4 sm:px-6">
        <p className="welcome-copy">Preparing your LifeOS…</p>
      </main>
    )
  }
  if (!user) return <Navigate replace to="/login" />
  return <TasksPage />
}

function AuthenticatedRemindersPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return (
      <main className="page-content mx-auto w-full px-4 sm:px-6">
        <p className="welcome-copy">Preparing your LifeOS…</p>
      </main>
    )
  }
  if (!user) return <Navigate replace to="/login" />
  return <RemindersPage />
}

function AuthenticatedFinancePage() {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return (
      <main className="page-content mx-auto w-full px-4 sm:px-6">
        <p className="welcome-copy">Preparing your LifeOS…</p>
      </main>
    )
  }
  if (!user) return <Navigate replace to="/login" />
  return <FinancePage />
}

function AuthenticatedHealthPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return <main className="page-content"><p className="welcome-copy">Preparing your LifeOS…</p></main>
  }
  if (!user) return <Navigate replace to="/login" />
  return <HealthPage />
}

function AuthenticatedNotesPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return <main className="page-content"><p className="welcome-copy">Preparing your LifeOS…</p></main>
  }
  if (!user) return <Navigate replace to="/login" />
  return <NotesPage />
}

function AuthenticatedDaybookPage() {
  const { user, isLoading } = useAuth()
  if (isLoading) {
    return <main className="page-content"><p className="welcome-copy">Preparing your LifeOS…</p></main>
  }
  if (!user) return <Navigate replace to="/login" />
  return <DaybookPage />
}

function NotFoundPage() {
  return (
    <main className="page-content mx-auto w-full px-4 sm:px-6">
      <section className="welcome-panel">
        <p className="eyebrow">Page not found</p>
        <h1>We couldn&apos;t find that page.</h1>
        <Link className="text-link" to="/">
          Return to LifeOS
        </Link>
      </section>
    </main>
  )
}

function AppRoutes() {
  const { user } = useAuth()
  return (
    <div className="app-shell min-h-screen">
      <header className="topbar">
        <Link aria-label="LifeOS home" className="brand" to="/">
          <img alt="" aria-hidden="true" className="brand-mark" src="/lifeos-mark.png" />
          <span>LifeOS</span>
        </Link>
        {user && (
          <nav aria-label="Main navigation" className="topbar-nav">
            <Link className="topbar-link" to="/today">Today</Link>
            <Link className="topbar-link" to="/tasks">Tasks</Link>
            <Link className="topbar-link" to="/reminders">Reminders</Link>
            <Link className="topbar-link" to="/finance">Finance</Link>
            <Link className="topbar-link" to="/health">Health</Link>
            <Link className="topbar-link" to="/notes">Notes</Link>
            <Link className="topbar-link" to="/daybook">Daybook</Link>
            <NotificationsBell />
          </nav>
        )}
        <span className="topbar-label">Your personal space</span>
      </header>
      <Routes>
        <Route element={<HomePage />} path="/" />
        <Route element={<LoginPage />} path="/login" />
        <Route element={<RegisterPage />} path="/register" />
        <Route element={<TodayPage />} path="/today" />
        <Route element={<AuthenticatedTasksPage />} path="/tasks" />
        <Route element={<AuthenticatedRemindersPage />} path="/reminders" />
        <Route element={<AuthenticatedFinancePage />} path="/finance" />
        <Route element={<AuthenticatedHealthPage />} path="/health" />
        <Route element={<AuthenticatedNotesPage />} path="/notes" />
        <Route element={<AuthenticatedDaybookPage />} path="/daybook" />
        <Route element={<NotFoundPage />} path="*" />
      </Routes>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
