import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/context'
import {
  createTask,
  deleteTask,
  fetchTasks,
  type Task,
  type TaskFilter,
  type TaskInput,
  type TaskPriority,
  updateTask,
} from '../api/tasks'
import { dateTimeLocalInZone, dateTimeLocalToIso, formatTaskDue, overdueDays } from '../utils/taskTime'

const filters: { value: TaskFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'today', label: 'Today' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'completed', label: 'Completed' },
]
const priorities: TaskPriority[] = ['high', 'medium', 'low']
const sessionFilterKey = 'lifeos.tasks.filter'

function getInitialFilter(): TaskFilter {
  const saved = window.sessionStorage.getItem(sessionFilterKey)
  return filters.some((filter) => filter.value === saved) ? (saved as TaskFilter) : 'all'
}

function taskDueInput(task: Task, timeZone: string): string {
  return task.due_at ? dateTimeLocalInZone(new Date(task.due_at), timeZone) : ''
}

function toTaskInput(
  form: HTMLFormElement,
  timeZone: string,
  overrideTitle?: string,
): TaskInput {
  const formData = new FormData(form)
  const dueValue = String(formData.get('due_at') ?? '')
  return {
    title: (overrideTitle ?? String(formData.get('title') ?? '')).trim(),
    notes: String(formData.get('notes') ?? '').trim() || null,
    priority: String(formData.get('priority') ?? 'medium') as TaskPriority,
    due_at: dueValue ? dateTimeLocalToIso(dueValue, timeZone) : null,
  }
}

export function TasksPage() {
  const { accessToken, user } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [filter, setFilter] = useState<TaskFilter>(getInitialFilter)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [title, setTitle] = useState('')
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null)
  const titleInput = useRef<HTMLInputElement>(null)
  const timeZone = user?.timezone ?? 'Asia/Kolkata'

  const reloadTasks = useCallback(async () => {
    if (!accessToken) return
    const response = await fetchTasks(accessToken, filter, search)
    setTasks(response.items)
  }, [accessToken, filter, search])

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 250)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError('')
    if (!accessToken) {
      setIsLoading(false)
      return
    }
    fetchTasks(accessToken, filter, search)
      .then((response) => {
        if (active) setTasks(response.items)
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load tasks.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [accessToken, filter, search])

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      const target = event.target
      const isTyping =
        target instanceof HTMLElement &&
        (target.isContentEditable ||
          ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
      if (!isTyping && !event.altKey && !event.ctrlKey && !event.metaKey && event.key.toLowerCase() === 'n') {
        event.preventDefault()
        titleInput.current?.focus()
      }
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!accessToken) return
    const form = event.currentTarget
    setError('')
    setIsCreating(true)
    try {
      await createTask(accessToken, toTaskInput(form, timeZone, title))
      setTitle('')
      form.reset()
      await reloadTasks()
      titleInput.current?.focus()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create this task.')
    } finally {
      setIsCreating(false)
    }
  }

  async function handleUpdate(taskId: string, input: Partial<TaskInput> & { is_completed?: boolean }) {
    if (!accessToken) return
    setError('')
    setBusyTaskId(taskId)
    try {
      await updateTask(accessToken, taskId, input)
      if (input.title !== undefined) setEditingTaskId(null)
      await reloadTasks()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update this task.')
    } finally {
      setBusyTaskId(null)
    }
  }

  async function handleEdit(event: FormEvent<HTMLFormElement>, task: Task) {
    event.preventDefault()
    try {
      const input = toTaskInput(event.currentTarget, timeZone)
      await handleUpdate(task.id, input)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Check the task details and try again.')
    }
  }

  async function handleDelete(task: Task) {
    if (!accessToken || !window.confirm(`Delete "${task.title}"? This task will be moved to trash.`)) {
      return
    }
    setError('')
    setBusyTaskId(task.id)
    try {
      await deleteTask(accessToken, task.id)
      await reloadTasks()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not delete this task.')
    } finally {
      setBusyTaskId(null)
    }
  }

  function chooseFilter(nextFilter: TaskFilter) {
    window.sessionStorage.setItem(sessionFilterKey, nextFilter)
    setFilter(nextFilter)
  }

  return (
    <main className="page-content task-page">
      <div className="task-heading-row">
        <div>
          <p className="eyebrow">Make space for what matters</p>
          <h1 className="task-page-heading">Your tasks</h1>
          <p className="task-subtitle">A clear list for everything you want to get done.</p>
        </div>
        <span className="task-timezone">Times shown in {timeZone}</span>
      </div>

      <section aria-label="Quick add task" className="quick-capture">
        <form className="quick-capture-form" onSubmit={(event) => void handleCreate(event)}>
          <label className="sr-only" htmlFor="quick-task-title">Task title</label>
          <input
            ref={titleInput}
            autoComplete="off"
            className="text-input quick-task-title"
            id="quick-task-title"
            maxLength={500}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="What needs to get done?"
            required
            value={title}
          />
          <details className="task-extra-details">
            <summary>Details</summary>
            <div className="task-extra-fields">
              <label className="field-label">
                Priority
                <select className="text-input" defaultValue="medium" name="priority">
                  {priorities.map((priority) => (
                    <option key={priority} value={priority}>{priority[0].toUpperCase() + priority.slice(1)}</option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                Due date and time
                <input className="text-input" name="due_at" type="datetime-local" />
              </label>
              <label className="field-label task-notes-field">
                Notes
                <textarea className="text-input task-notes-input" maxLength={10000} name="notes" rows={2} />
              </label>
            </div>
          </details>
          <div className="quick-capture-actions">
            <span className="shortcut-hint">Press <kbd>N</kbd> to capture</span>
            <button className="primary-button add-task-button" disabled={isCreating || !title.trim()} type="submit">
              {isCreating ? 'Adding…' : 'Add task'}
            </button>
          </div>
        </form>
      </section>

      <section aria-label="Task list" className="task-list-section">
        <div className="task-list-toolbar">
          <div aria-label="Filter tasks" className="task-filters" role="tablist">
            {filters.map((item) => (
              <button
                aria-selected={filter === item.value}
                className={`task-filter${filter === item.value ? ' is-active' : ''}`}
                key={item.value}
                onClick={() => chooseFilter(item.value)}
                role="tab"
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
          <label className="search-field">
            <span className="sr-only">Search tasks</span>
            <input
              className="text-input task-search"
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search tasks"
              type="search"
              value={searchInput}
            />
          </label>
        </div>

        {error && <div className="form-message form-message-error task-error" role="alert">{error}</div>}
        {isLoading ? (
          <p className="task-state">Loading your tasks…</p>
        ) : tasks.length === 0 ? (
          <div className="task-state task-empty">
            <span aria-hidden="true" className="task-empty-icon">✓</span>
            <h2>{search ? 'No matching tasks' : filter === 'completed' ? 'No completed tasks yet' : 'You’re all caught up'}</h2>
            <p>{search ? 'Try a different search phrase.' : 'Add a task above to get started.'}</p>
          </div>
        ) : (
          <ul className="task-list">
            {tasks.map((task) => {
              const isOverdue = !task.is_completed && task.due_at !== null && new Date(task.due_at) < new Date()
              const daysLate = isOverdue && task.due_at ? overdueDays(task.due_at, timeZone) : 0
              return (
                <li className={`task-card${task.is_completed ? ' is-completed' : ''}${isOverdue ? ' is-overdue' : ''}`} key={task.id}>
                  <div className="task-main-row">
                    <input
                      aria-label={`${task.is_completed ? 'Reopen' : 'Complete'} ${task.title}`}
                      checked={task.is_completed}
                      className="task-checkbox"
                      disabled={busyTaskId === task.id}
                      onChange={(event) => void handleUpdate(task.id, { is_completed: event.target.checked })}
                      type="checkbox"
                    />
                    <div className="task-content">
                      <button
                        className="task-title-button"
                        onClick={() => setEditingTaskId(editingTaskId === task.id ? null : task.id)}
                        type="button"
                      >
                        {task.title}
                      </button>
                      <div className="task-meta">
                        <span className={`priority-badge priority-${task.priority}`}>{task.priority}</span>
                        {task.due_at && (
                          <span className="task-due">
                            {isOverdue ? (
                              <strong>{daysLate > 0 ? `Overdue by ${daysLate} ${daysLate === 1 ? 'day' : 'days'}` : 'Overdue today'}</strong>
                            ) : 'Due'} {!task.is_completed && formatTaskDue(task.due_at, timeZone)}
                            {task.is_completed && formatTaskDue(task.due_at, timeZone)}
                          </span>
                        )}
                      </div>
                      {task.notes && editingTaskId !== task.id && <p className="task-notes-preview">{task.notes}</p>}
                    </div>
                    <button
                      aria-label={`Delete ${task.title}`}
                      className="task-delete-button"
                      disabled={busyTaskId === task.id}
                      onClick={() => void handleDelete(task)}
                      type="button"
                    >
                      Delete
                    </button>
                  </div>
                  {editingTaskId === task.id && (
                    <form className="task-edit-form" onSubmit={(event) => void handleEdit(event, task)}>
                      <label className="field-label">
                        Title
                        <input className="text-input" defaultValue={task.title} maxLength={500} name="title" required />
                      </label>
                      <div className="task-edit-fields">
                        <label className="field-label">
                          Priority
                          <select className="text-input" defaultValue={task.priority} name="priority">
                            {priorities.map((priority) => (
                              <option key={priority} value={priority}>{priority[0].toUpperCase() + priority.slice(1)}</option>
                            ))}
                          </select>
                        </label>
                        <label className="field-label">
                          Due date and time
                          <input className="text-input" defaultValue={taskDueInput(task, timeZone)} name="due_at" type="datetime-local" />
                        </label>
                      </div>
                      <label className="field-label">
                        Notes
                        <textarea className="text-input task-notes-input" defaultValue={task.notes ?? ''} maxLength={10000} name="notes" rows={2} />
                      </label>
                      <div className="task-edit-actions">
                        <button className="secondary-button" onClick={() => setEditingTaskId(null)} type="button">Cancel</button>
                        <button className="primary-button add-task-button" disabled={busyTaskId === task.id} type="submit">Save changes</button>
                      </div>
                    </form>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </main>
  )
}
