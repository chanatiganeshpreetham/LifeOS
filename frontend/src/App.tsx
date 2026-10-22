import { Link, Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
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

export function AppNavigation() {
  const { user } = useAuth()
  const location = useLocation()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const menuTriggerRef = useRef<HTMLButtonElement>(null)
  const menuCloseRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!isMobileMenuOpen) return

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsMobileMenuOpen(false)
        menuTriggerRef.current?.focus()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    menuCloseRef.current?.focus()
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMobileMenuOpen])

  function closeMobileMenu() {
    setIsMobileMenuOpen(false)
    menuTriggerRef.current?.focus()
  }

  return (
    <>
      <header className="topbar">
        <Link aria-label="LifeOS home" className="brand brand-desktop" to="/">
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
          </nav>
        )}
        {user ? (
          <button
            aria-controls="mobile-navigation"
            aria-expanded={isMobileMenuOpen}
            aria-label="Open LifeOS menu"
            className="brand brand-menu-trigger"
            onClick={() => setIsMobileMenuOpen(true)}
            ref={menuTriggerRef}
            type="button"
          >
            <img alt="" aria-hidden="true" className="brand-mark" src="/lifeos-mark.png" />
            <span>LifeOS</span>
            <span aria-hidden="true" className="menu-chevron">⌄</span>
          </button>
        ) : (
          <Link aria-label="LifeOS home" className="brand brand-mobile-home" to="/">
            <img alt="" aria-hidden="true" className="brand-mark" src="/lifeos-mark.png" />
            <span>LifeOS</span>
          </Link>
        )}
        {user && <NotificationsBell />}
        <span className="topbar-label">Your personal space</span>
      </header>
      {user && isMobileMenuOpen && (
        <div className="mobile-nav-overlay">
          <button
            aria-label="Close navigation"
            className="mobile-nav-backdrop"
            onClick={closeMobileMenu}
            tabIndex={-1}
            type="button"
          />
          <aside
            aria-modal="true"
            className="mobile-nav-panel"
            id="mobile-navigation"
            aria-labelledby="mobile-nav-title"
            role="dialog"
          >
            <div className="mobile-nav-heading">
              <div>
                <p className="eyebrow">Your personal space</p>
                <h2 id="mobile-nav-title">Explore LifeOS</h2>
              </div>
              <button
                aria-label="Close navigation"
                className="mobile-nav-close"
                onClick={closeMobileMenu}
                ref={menuCloseRef}
                type="button"
              >
                ×
              </button>
            </div>
            <nav aria-label="Mobile navigation" className="mobile-nav-links">
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/today">
                <span aria-hidden="true">⌂</span><span>Today</span>
              </NavLink>
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/tasks">
                <span aria-hidden="true">✓</span><span>Tasks</span>
              </NavLink>
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/reminders">
                <span aria-hidden="true">◷</span><span>Reminders</span>
              </NavLink>
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/finance">
                <span aria-hidden="true">₹</span><span>Finance</span>
              </NavLink>
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/health">
                <span aria-hidden="true">♡</span><span>Health</span>
              </NavLink>
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/notes">
                <span aria-hidden="true">✎</span><span>Notes</span>
              </NavLink>
              <NavLink className="mobile-nav-link" onClick={closeMobileMenu} to="/daybook">
                <span aria-hidden="true">▦</span><span>Daybook</span>
              </NavLink>
            </nav>
          </aside>
        </div>
      )}
    </>
  )
}

function AppRoutes() {
  return (
    <div className="app-shell min-h-screen">
      <AppNavigation />
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
