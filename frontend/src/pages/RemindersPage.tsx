import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/context'
import {
  acknowledgeReminder,
  createReminder,
  deleteReminder,
  fetchPushConfig,
  fetchReminders,
  registerPushSubscription,
  removePushSubscription,
  updateReminder,
  type Reminder,
  type ReminderFrequency,
  type ReminderInput,
  type ReminderWeekday,
} from '../api/reminders'
import { dateTimeLocalInZone, dateTimeLocalToIso, formatTaskDue } from '../utils/taskTime'

const weekdays: { value: ReminderWeekday; label: string }[] = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' },
]

function toReminderInput(form: HTMLFormElement, timeZone: string): ReminderInput {
  const data = new FormData(form)
  const isRecurring = data.get('is_recurring') === 'on'
  const rawFrequency = String(data.get('frequency') ?? '')
  const frequency = isRecurring ? (rawFrequency as ReminderFrequency) : null
  const intervalValue = Number(data.get('interval_days'))
  return {
    title: String(data.get('title') ?? '').trim(),
    notes: String(data.get('notes') ?? '').trim() || null,
    remind_at: dateTimeLocalToIso(String(data.get('remind_at') ?? ''), timeZone),
    is_recurring: isRecurring,
    frequency,
    interval_days: frequency === 'custom' ? intervalValue : null,
    weekdays:
      frequency === 'weekly'
        ? data.getAll('weekdays').map((day) => String(day) as ReminderWeekday)
        : null,
  }
}

function reminderDateInput(reminder: Reminder, timeZone: string): string {
  return dateTimeLocalInZone(new Date(reminder.remind_at), timeZone)
}

function urlBase64ToUint8Array(value: string): Uint8Array {
  const padding = '='.repeat((4 - (value.length % 4)) % 4)
  const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  const bytes = new Uint8Array(raw.length)
  for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index)
  return bytes
}

export function RemindersPage() {
  const { accessToken, user } = useAuth()
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [editingReminder, setEditingReminder] = useState<Reminder | null>(null)
  const [isRecurring, setIsRecurring] = useState(false)
  const [frequency, setFrequency] = useState<ReminderFrequency>('daily')
  const [pushEnabled, setPushEnabled] = useState(false)
  const [pushSupported, setPushSupported] = useState(true)
  const [pushPermission, setPushPermission] = useState<NotificationPermission | 'unsupported'>('default')
  const [pushStatus, setPushStatus] = useState('')
  const [pushBusy, setPushBusy] = useState(false)
  const [pushReady, setPushReady] = useState(false)
  const timeZone = user?.timezone ?? 'Asia/Kolkata'
  const editingId = editingReminder?.id ?? null

  const reload = useCallback(async () => {
    if (!accessToken) return
    const response = await fetchReminders(accessToken)
    setReminders(response.items)
  }, [accessToken])

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError('')
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    Promise.all([fetchReminders(accessToken), fetchPushConfig(accessToken)])
      .then(([reminderResponse, pushConfig]) => {
        if (active) {
          setReminders(reminderResponse.items)
          setPushEnabled(pushConfig.enabled && Boolean(pushConfig.public_key))
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load reminders.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [accessToken])

  useEffect(() => {
    const supported =
      typeof window !== 'undefined' &&
      'Notification' in window &&
      'serviceWorker' in navigator &&
      'PushManager' in window
    setPushSupported(supported)
    if (!supported) {
      setPushPermission('unsupported')
      return
    }
    setPushPermission(window.Notification.permission)
    navigator.serviceWorker
      .register('/service-worker.js')
      .then(async (registration) => {
        const subscription = await registration.pushManager.getSubscription()
        setPushReady(Boolean(subscription))
      })
      .catch(() => {
        setPushStatus('This browser could not enable the notification service worker.')
      })
  }, [])

  function clearForm(form: HTMLFormElement) {
    form.reset()
    setIsRecurring(false)
    setFrequency('daily')
    setEditingReminder(null)
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    setError('')
    setIsSaving(true)
    try {
      const input = toReminderInput(form, timeZone)
      if (editingReminder) {
        await updateReminder(accessToken, editingReminder.id, input)
      } else {
        await createReminder(accessToken, input)
      }
      clearForm(form)
      await reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this reminder.')
    } finally {
      setIsSaving(false)
    }
  }

  function startEdit(reminder: Reminder) {
    setEditingReminder(reminder)
    setIsRecurring(reminder.is_recurring)
    setFrequency(reminder.frequency ?? 'daily')
    setError('')
  }

  async function handleAcknowledge(reminder: Reminder) {
    if (!accessToken) return
    setBusyId(reminder.id)
    setError('')
    try {
      await acknowledgeReminder(accessToken, reminder.id)
      await reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not acknowledge this reminder.')
    } finally {
      setBusyId(null)
    }
  }

  async function handleToggleActive(reminder: Reminder) {
    if (!accessToken) return
    setBusyId(reminder.id)
    setError('')
    try {
      await updateReminder(accessToken, reminder.id, { is_active: !reminder.is_active })
      await reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update this reminder.')
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(reminder: Reminder) {
    if (!accessToken || !window.confirm(`Delete "${reminder.title}"?`)) return
    setBusyId(reminder.id)
    setError('')
    try {
      await deleteReminder(accessToken, reminder.id)
      if (editingId === reminder.id) setEditingReminder(null)
      await reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not delete this reminder.')
    } finally {
      setBusyId(null)
    }
  }

  async function enablePush() {
    if (!accessToken || !pushSupported) return
    setPushBusy(true)
    setPushStatus('')
    try {
      if (Notification.permission === 'denied') {
        setPushPermission('denied')
        setPushStatus('Notifications are blocked in your browser settings. Allow them there, or keep using in-app reminders.')
        return
      }
      const permission = await Notification.requestPermission()
      setPushPermission(permission)
      if (permission !== 'granted') {
        setPushStatus('Push permission was not granted. In-app reminders remain available.')
        return
      }
      const config = await fetchPushConfig(accessToken)
      if (!config.enabled || !config.public_key) {
        setPushStatus('Browser push is not configured on this server. In-app reminders remain available.')
        return
      }
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(config.public_key),
      })
      const keys = subscription.toJSON().keys
      if (!keys?.p256dh || !keys.auth) {
        await subscription.unsubscribe()
        throw new Error('The browser returned an incomplete push subscription.')
      }
      await registerPushSubscription(accessToken, {
        endpoint: subscription.endpoint,
        p256dh_key: keys.p256dh,
        auth_key: keys.auth,
        device_label: navigator.userAgent.slice(0, 100),
      })
      setPushReady(true)
      setPushStatus('Browser push is enabled on this device.')
    } catch (cause) {
      setPushStatus(cause instanceof Error ? cause.message : 'Could not enable browser push.')
    } finally {
      setPushBusy(false)
    }
  }

  async function disablePush() {
    if (!accessToken) return
    setPushBusy(true)
    setPushStatus('')
    try {
      const registration = await navigator.serviceWorker.getRegistration('/service-worker.js')
      const subscription = await registration?.pushManager.getSubscription()
      if (subscription) {
        await removePushSubscription(accessToken, subscription.endpoint)
        await subscription.unsubscribe()
      }
      setPushReady(false)
      setPushStatus('Browser push has been disabled on this device.')
    } catch (cause) {
      setPushStatus(cause instanceof Error ? cause.message : 'Could not disable browser push.')
    } finally {
      setPushBusy(false)
    }
  }

  return (
    <main className="page-content reminder-page">
      <div className="task-heading-row">
        <div>
          <p className="eyebrow">A gentle nudge at the right time</p>
          <h1 className="task-page-heading">Reminders</h1>
          <p className="task-subtitle">Schedule the things you don’t want to forget.</p>
        </div>
        <span className="task-timezone">Times shown in {timeZone}</span>
      </div>

      <section aria-labelledby="push-heading" className="push-settings-card">
        <div>
          <p className="progress-card-title" id="push-heading">Browser notifications</p>
          <p className="push-description">
            {pushReady
              ? 'This browser can receive reminders even when the tab is closed.'
              : !pushSupported
                ? 'This browser does not support web push. In-app reminders are still available.'
                : pushPermission === 'denied'
                  ? 'Permission is blocked in browser settings. In-app reminders are still available.'
                  : !pushEnabled
                    ? 'Push delivery is not configured on this server. In-app reminders are still available.'
                    : 'Enable browser push to receive reminders outside the app.'}
          </p>
        </div>
        {pushSupported && pushEnabled && (
          <button
            className={pushReady ? 'secondary-button' : 'primary-button add-task-button'}
            disabled={pushBusy}
            onClick={() => void (pushReady ? disablePush() : enablePush())}
            type="button"
          >
            {pushBusy ? 'Please wait…' : pushReady ? 'Disable push' : 'Enable push'}
          </button>
        )}
        {pushStatus && <p className="push-status" role="status">{pushStatus}</p>}
      </section>

      <section aria-label={editingId ? 'Edit reminder' : 'Create reminder'} className="quick-capture reminder-form-card">
        <form key={editingId ?? 'new-reminder'} className="reminder-form" onSubmit={(event) => void handleSave(event)}>
          <h2 className="reminder-form-heading">{editingId ? 'Edit reminder' : 'Quick reminder'}</h2>
          <label className="field-label" htmlFor="reminder-title">
            Reminder
            <input autoComplete="off" className="text-input" defaultValue={editingReminder?.title ?? ''} id="reminder-title" maxLength={300} name="title" placeholder="What should we remind you about?" required />
          </label>
          <div className="reminder-form-row">
            <label className="field-label" htmlFor="reminder-datetime">
              Date and time
              <input className="text-input" defaultValue={editingReminder ? reminderDateInput(editingReminder, timeZone) : ''} id="reminder-datetime" name="remind_at" required type="datetime-local" />
            </label>
            <label className="field-label reminder-repeat-toggle">
              <span>Repeat</span>
              <span className="repeat-checkbox-label">
                <input checked={isRecurring} name="is_recurring" onChange={(event) => setIsRecurring(event.target.checked)} type="checkbox" />
                Repeat this reminder
              </span>
            </label>
          </div>
          {isRecurring && (
            <div className="reminder-repeat-options">
              <label className="field-label" htmlFor="reminder-frequency">
                Repeat
                <select className="text-input" id="reminder-frequency" name="frequency" onChange={(event) => setFrequency(event.target.value as ReminderFrequency)} value={frequency}>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="custom">Every few days</option>
                </select>
              </label>
              {frequency === 'custom' && (
                <label className="field-label" htmlFor="reminder-interval">
                  Interval in days
                  <input className="text-input" defaultValue={editingReminder?.interval_days ?? 2} id="reminder-interval" max="365" min="1" name="interval_days" required type="number" />
                </label>
              )}
              {frequency === 'weekly' && (
                <fieldset className="weekday-fieldset">
                  <legend>Repeat on</legend>
                  <div className="weekday-options">
                    {weekdays.map((day) => (
                      <label className="weekday-option" key={day.value}>
                        <input defaultChecked={editingReminder?.weekdays?.includes(day.value) ?? false} name="weekdays" type="checkbox" value={day.value} />
                        {day.label}
                      </label>
                    ))}
                  </div>
                </fieldset>
              )}
            </div>
          )}
          <label className="field-label">
            Notes <span className="field-hint">Optional</span>
            <textarea className="text-input task-notes-input" defaultValue={editingReminder?.notes ?? ''} maxLength={10000} name="notes" rows={2} />
          </label>
          {error && <div className="form-message form-message-error" role="alert">{error}</div>}
          <div className="reminder-form-actions">
            {editingId && <button className="secondary-button" onClick={() => setEditingReminder(null)} type="button">Cancel</button>}
            <button className="primary-button add-task-button" disabled={isSaving} type="submit">{isSaving ? 'Saving…' : editingId ? 'Save changes' : 'Add reminder'}</button>
          </div>
        </form>
      </section>

      <section aria-label="Scheduled reminders" className="task-list-section reminder-list-section">
        <div className="reminder-list-heading">
          <h2>Scheduled reminders</h2>
          <span>{reminders.filter((reminder) => reminder.is_active).length} active</span>
        </div>
        {isLoading ? (
          <p className="task-state">Loading your reminders…</p>
        ) : reminders.length === 0 ? (
          <div className="task-state task-empty">
            <span aria-hidden="true" className="task-empty-icon">◷</span>
            <h2>No reminders yet</h2>
            <p>Add a reminder above to get started.</p>
          </div>
        ) : (
          <ul className="task-list">
            {reminders.map((reminder) => (
              <li className={`task-card${!reminder.is_active ? ' reminder-inactive' : ''}`} key={reminder.id}>
                <div className="task-main-row">
                  <span aria-hidden="true" className="reminder-clock">◷</span>
                  <div className="task-content">
                    <strong className="reminder-title">{reminder.title}</strong>
                    <div className="task-meta">
                      <span className="task-due">{formatTaskDue(reminder.remind_at, timeZone)}</span>
                      {reminder.is_recurring && <span className="recurrence-badge">{reminder.frequency === 'custom' ? `Every ${reminder.interval_days} days` : reminder.frequency}</span>}
                      {!reminder.is_active && <span className="reminder-status-badge">Completed / paused</span>}
                    </div>
                    {reminder.notes && <p className="task-notes-preview">{reminder.notes}</p>}
                  </div>
                  <div className="reminder-actions">
                    {reminder.is_active && (
                      <button className="text-button" disabled={busyId === reminder.id} onClick={() => void handleAcknowledge(reminder)} type="button">Complete</button>
                    )}
                    <button className="text-button" disabled={busyId === reminder.id} onClick={() => void handleToggleActive(reminder)} type="button">
                      {reminder.is_active ? 'Pause' : 'Resume'}
                    </button>
                    <button className="text-button" disabled={busyId === reminder.id} onClick={() => startEdit(reminder)} type="button">Edit</button>
                    <button className="task-delete-button" disabled={busyId === reminder.id} onClick={() => void handleDelete(reminder)} type="button">Delete</button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
