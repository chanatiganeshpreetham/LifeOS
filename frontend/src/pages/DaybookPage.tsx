import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/context'
import {
  createDaybookEntry,
  deleteDaybookEntry,
  fetchDaybook,
  updateDaybookEntry,
  type DaybookActivity,
  type DaybookData,
  type DaybookEntry,
} from '../api/daybook'

const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const sourceNames: Record<DaybookActivity['source'], string> = {
  tasks: 'Task',
  reminders: 'Reminder',
  finance: 'Finance',
  health: 'Health',
  notes: 'Note',
}

function dateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function dateKeyInTimezone(date: Date, timeZone: string): string {
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

function addDays(date: Date, amount: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + amount)
  return next
}

function formatDay(date: Date): string {
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

function getCalendarDays(month: Date): Date[] {
  const first = new Date(month.getFullYear(), month.getMonth(), 1)
  const mondayOffset = (first.getDay() + 6) % 7
  return Array.from({ length: 42 }, (_, index) => addDays(first, index - mondayOffset))
}

function monthRequestRange(month: Date): { start: string; end: string } {
  const days = getCalendarDays(month)
  return { start: dateKey(days[0]), end: dateKey(addDays(days[41], 1)) }
}

export function DaybookPage() {
  const { accessToken, user } = useAuth()
  const userTimezone = user?.timezone ?? 'Asia/Kolkata'
  const currentDate = dateKeyInTimezone(new Date(), userTimezone)
  const [month, setMonth] = useState(() => {
    const initialDate = new Date(`${currentDate}T12:00:00`)
    return new Date(initialDate.getFullYear(), initialDate.getMonth(), 1)
  })
  const [selectedDate, setSelectedDate] = useState(currentDate)
  const [data, setData] = useState<DaybookData>({ entries: [], activities: [] })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')
  const [editingEntry, setEditingEntry] = useState<DaybookEntry | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const calendarDays = useMemo(() => getCalendarDays(month), [month])
  const requestRange = useMemo(() => monthRequestRange(month), [month])
  const hasUnsavedChanges = useCallback((): boolean => {
    if (isCreating) return Boolean(title.trim() || content.trim())
    if (!editingEntry) return false
    return editingEntry.title !== (title.trim() || 'Untitled entry') ||
      editingEntry.content !== content
  }, [content, editingEntry, isCreating, title])

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError('')
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    fetchDaybook(accessToken, requestRange.start, requestRange.end)
      .then((response) => {
        if (active) {
          setData(response)
          setError('')
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load Daybook.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    const refreshTimer = window.setInterval(() => {
      void fetchDaybook(accessToken, requestRange.start, requestRange.end)
        .then((response) => {
          if (active) {
            setData(response)
            setError('')
          }
        })
        .catch((cause: unknown) => {
          if (active) setError(cause instanceof Error ? cause.message : 'Could not refresh Daybook.')
        })
    }, 60000)
    return () => {
      active = false
      window.clearInterval(refreshTimer)
    }
  }, [accessToken, requestRange.end, requestRange.start])

  useEffect(() => {
    if (!hasUnsavedChanges()) return

    function warnBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault()
      event.returnValue = ''
    }

    function confirmInternalNavigation(event: MouseEvent) {
      const target = event.target
      if (
        !(target instanceof Element) ||
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) return
      const link = target.closest('a[href]')
      if (!(link instanceof HTMLAnchorElement) || link.target || link.href === window.location.href) return
      const destination = new URL(link.href, window.location.href)
      if (
        destination.origin === window.location.origin &&
        !window.confirm('Discard your unsaved Daybook changes?')
      ) {
        event.preventDefault()
        event.stopPropagation()
      }
    }

    window.addEventListener('beforeunload', warnBeforeUnload)
    document.addEventListener('click', confirmInternalNavigation, true)
    return () => {
      window.removeEventListener('beforeunload', warnBeforeUnload)
      document.removeEventListener('click', confirmInternalNavigation, true)
    }
  }, [hasUnsavedChanges])

  const entriesForDay = data.entries.filter((entry) => entry.entry_date === selectedDate)
  const activitiesForDay = data.activities.filter((item) => item.activity_date === selectedDate)
  const counts = new Map<string, number>()
  for (const entry of data.entries) {
    counts.set(entry.entry_date, (counts.get(entry.entry_date) ?? 0) + 1)
  }
  for (const activity of data.activities) {
    counts.set(activity.activity_date, (counts.get(activity.activity_date) ?? 0) + 1)
  }

  function allowNavigation(): boolean {
    return !isSaving && (!hasUnsavedChanges() ||
      window.confirm('Discard your unsaved Daybook changes?')
    )
  }

  function selectDay(nextDate: string) {
    if (!allowNavigation()) return
    setSelectedDate(nextDate)
    setEditingEntry(null)
    setIsCreating(false)
    setTitle('')
    setContent('')
    setSaveMessage('')
    const date = new Date(`${nextDate}T12:00:00`)
    setMonth(new Date(date.getFullYear(), date.getMonth(), 1))
  }

  function changeMonth(offset: number) {
    if (!allowNavigation()) return
    const nextMonth = new Date(month.getFullYear(), month.getMonth() + offset, 1)
    setMonth(nextMonth)
    setSelectedDate(dateKey(nextMonth))
    setEditingEntry(null)
    setIsCreating(false)
    setTitle('')
    setContent('')
    setSaveMessage('')
  }

  function goToToday() {
    if (!allowNavigation()) return
    const today = new Date(`${currentDate}T12:00:00`)
    setSelectedDate(currentDate)
    setMonth(new Date(today.getFullYear(), today.getMonth(), 1))
    setEditingEntry(null)
    setIsCreating(false)
    setTitle('')
    setContent('')
    setSaveMessage('')
  }

  function startNewEntry() {
    if (!allowNavigation()) return
    setEditingEntry(null)
    setIsCreating(true)
    setTitle('')
    setContent('')
    setSaveMessage('')
    setError('')
  }

  function startEditing(entry: DaybookEntry) {
    if (!allowNavigation()) return
    setEditingEntry(entry)
    setIsCreating(false)
    setTitle(entry.title)
    setContent(entry.content)
    setSaveMessage('')
    setError('')
  }

  async function saveEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    setError('')
    setIsSaving(true)
    setSaveMessage('Saving…')
    try {
      let savedEntry: DaybookEntry
      if (editingEntry) {
        savedEntry = await updateDaybookEntry(accessToken, editingEntry.id, {
          title: title.trim() || 'Untitled entry',
          content,
        })
      } else {
        savedEntry = await createDaybookEntry(accessToken, {
          entry_date: selectedDate,
          title: title.trim() || 'Untitled entry',
          content,
        })
      }
      setData((current) => ({
        ...current,
        entries: [...current.entries.filter((entry) => entry.id !== savedEntry.id), savedEntry]
          .sort((left, right) =>
            left.entry_date.localeCompare(right.entry_date) ||
            left.created_at.localeCompare(right.created_at),
          ),
      }))
      setEditingEntry(null)
      setIsCreating(false)
      setTitle('')
      setContent('')
      setSaveMessage('Saved')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this entry.')
      setSaveMessage('Save failed')
    } finally {
      setIsSaving(false)
    }
  }

  async function removeEntry(entry: DaybookEntry) {
    if (!accessToken || !window.confirm(`Delete "${entry.title}"? This cannot be undone.`)) return
    setIsSaving(true)
    setError('')
    try {
      await deleteDaybookEntry(accessToken, entry.id)
      setData((current) => ({
        ...current,
        entries: current.entries.filter((item) => item.id !== entry.id),
      }))
      if (editingEntry?.id === entry.id) {
        setEditingEntry(null)
        setTitle('')
        setContent('')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not delete this entry.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <main className="page-content daybook-page">
      <header className="daybook-heading">
        <div>
          <p className="eyebrow">Your days, gathered in one place</p>
          <h1>Daybook</h1>
          <p className="welcome-copy">A personal journal alongside the moments and plans in LifeOS.</p>
        </div>
        <div className="daybook-controls">
          <button aria-label="Previous month" className="secondary-button" onClick={() => changeMonth(-1)} type="button">‹</button>
          <h2 aria-live="polite">{month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</h2>
          <button aria-label="Next month" className="secondary-button" onClick={() => changeMonth(1)} type="button">›</button>
          <button className="secondary-button daybook-today-button" onClick={goToToday} type="button">Today</button>
        </div>
      </header>

      {error && <p className="form-message form-message-error" role="alert">{error}</p>}
      <div className="daybook-layout">
        <section aria-label="Monthly calendar" className="daybook-calendar-panel">
          <div className="daybook-calendar-grid daybook-weekdays" aria-hidden="true">
            {dayLabels.map((day) => <span key={day}>{day}</span>)}
          </div>
          <div aria-label={month.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })} className="daybook-calendar-grid">
            {calendarDays.map((date) => {
              const key = dateKey(date)
              const count = counts.get(key) ?? 0
              const isCurrentMonth = date.getMonth() === month.getMonth()
              const isToday = key === currentDate
              return (
                <button
                  aria-current={isToday ? 'date' : undefined}
                  aria-label={`${formatDay(date)}${count ? `, ${count} items` : ''}`}
                  aria-pressed={key === selectedDate}
                  className={`daybook-date${isCurrentMonth ? '' : ' is-outside'}${isToday ? ' is-today' : ''}${key === selectedDate ? ' is-selected' : ''}`}
                  key={key}
                  onClick={() => selectDay(key)}
                  type="button"
                >
                  <span>{date.getDate()}</span>
                  {count > 0 && <small aria-hidden="true">{count > 9 ? '9+' : count}<i /></small>}
                </button>
              )
            })}
          </div>
          <p className="daybook-calendar-key"><span /> Days with notes or activities</p>
        </section>

        <section aria-label={`Details for ${formatDay(new Date(`${selectedDate}T12:00:00`))}`} className="daybook-details">
          <header className="daybook-day-heading">
            <div>
              <p className="eyebrow">Selected day</p>
              <h2>{formatDay(new Date(`${selectedDate}T12:00:00`))}</h2>
            </div>
            <button className="primary-button" onClick={startNewEntry} type="button">＋ Add note</button>
            {saveMessage && !isCreating && !editingEntry && (
              <span aria-live="polite" className="daybook-save-feedback" role="status">{saveMessage}</span>
            )}
          </header>

          {isLoading && <p className="daybook-empty" role="status">Loading your day…</p>}
          {!isLoading && !entriesForDay.length && !activitiesForDay.length && !isCreating && (
            <div className="daybook-empty">
              <span aria-hidden="true">✦</span>
              <h3>A fresh page</h3>
              <p>Nothing is recorded for this day yet. Add a note to remember it or plan ahead.</p>
              <button className="secondary-button" onClick={startNewEntry} type="button">Write a note</button>
            </div>
          )}

          {(isCreating || editingEntry) && (
            <form className="daybook-editor" onSubmit={(event) => void saveEntry(event)}>
              <div className="daybook-editor-header">
                <span className="daybook-type-label">Personal note</span>
                <span aria-live="polite" className="note-save-state">{isSaving ? 'Saving…' : saveMessage}</span>
              </div>
              <label className="sr-only" htmlFor="daybook-entry-title">Entry title</label>
              <input
                autoFocus
                className="daybook-entry-title"
                id="daybook-entry-title"
                maxLength={300}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Give this note a title"
                value={title}
              />
              <label className="sr-only" htmlFor="daybook-entry-content">Entry content</label>
              <textarea
                className="daybook-entry-content"
                id="daybook-entry-content"
                maxLength={100000}
                onChange={(event) => setContent(event.target.value)}
                placeholder="Write freely… paragraphs and lists are welcome."
                rows={7}
                value={content}
              />
              <div className="daybook-editor-actions">
                {editingEntry && <button className="finance-delete-button" disabled={isSaving} onClick={() => void removeEntry(editingEntry)} type="button">Delete note</button>}
                <button className="secondary-button" disabled={isSaving} onClick={() => {
                  setIsCreating(false)
                  setEditingEntry(null)
                  setTitle('')
                  setContent('')
                  setSaveMessage('')
                }} type="button">Cancel</button>
                <button className="primary-button" disabled={isSaving || !(title.trim() || content.trim())} type="submit">
                  {isSaving ? 'Saving…' : 'Save note'}
                </button>
              </div>
            </form>
          )}

          {!isLoading && entriesForDay.length > 0 && (
            <section aria-label="Daily notes" className="daybook-section">
              <h3>Daily notes <span>{entriesForDay.length}</span></h3>
              <div className="daybook-entry-list">
                {entriesForDay.map((entry) => (
                  <article className="daybook-entry-card" key={entry.id}>
                    <button className="daybook-entry-open" onClick={() => startEditing(entry)} type="button">
                      <span className="daybook-type-label">Personal note</span>
                      <strong>{entry.title}</strong>
                      {entry.content && <span className="daybook-entry-preview">{entry.content}</span>}
                    </button>
                    <time dateTime={entry.updated_at}>Updated {new Date(entry.updated_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}</time>
                  </article>
                ))}
              </div>
            </section>
          )}

          {!isLoading && activitiesForDay.length > 0 && (
            <section aria-label="Synchronized activities" className="daybook-section">
              <h3>Activities <span>{activitiesForDay.length}</span></h3>
              <div className="daybook-activity-list">
                {activitiesForDay.map((activity) => (
                  <Link className="daybook-activity-card" key={activity.id} to={activity.url}>
                    <span aria-hidden="true" className="daybook-activity-icon">{activity.source === 'finance' ? '$' : activity.source === 'health' ? '+' : activity.source === 'tasks' ? '✓' : activity.source === 'notes' ? '✎' : '◷'}</span>
                    <span className="daybook-activity-copy">
                      <span className="daybook-activity-meta">{sourceNames[activity.source]}{activity.status ? ` · ${activity.status}` : ''}</span>
                      <strong>{activity.title}</strong>
                      {activity.description && <span>{activity.description}</span>}
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </section>
      </div>
    </main>
  )
}
