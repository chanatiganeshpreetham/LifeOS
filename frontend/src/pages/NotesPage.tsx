import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useAuth } from '../auth/context'
import { createNote, deleteNote, fetchNotes, updateNote, type Note } from '../api/notes'

export function NotesPage() {
  const { accessToken } = useAuth()
  const [notes, setNotes] = useState<Note[]>([])
  const [activeNote, setActiveNote] = useState<Note | null>(null)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveStatus, setSaveStatus] = useState('')
  const saveTimer = useRef<number | null>(null)
  const initializedForToken = useRef<string | null>(null)

  const refreshNotes = useCallback(async (searchTerm = '') => {
    if (!accessToken) return
    const response = await fetchNotes(accessToken, searchTerm)
    setNotes(response.items)
    return response.items
  }, [accessToken])

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(searchInput), 250)
    return () => window.clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    let active = true
    setIsLoading(true)
    setError('')
    refreshNotes(query)
      .then((items) => {
        if (active && accessToken && initializedForToken.current !== accessToken) {
          initializedForToken.current = accessToken
          if (items?.length) {
            setActiveNote(items[0])
            setTitle(items[0].title)
            setBody(items[0].body ?? '')
          }
        }
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Could not load notes.')
      })
      .finally(() => {
        if (active) setIsLoading(false)
      })
    return () => {
      active = false
    }
  }, [accessToken, query, refreshNotes])

  const saveDraft = useCallback(async (note: Note, nextTitle: string, nextBody: string) => {
    if (!accessToken) return
    const normalizedTitle = nextTitle.trim() || 'Untitled note'
    if (note.title === normalizedTitle && (note.body ?? '') === nextBody) {
      setSaveStatus('All changes saved')
      return
    }
    setIsSaving(true)
    setError('')
    setSaveStatus('Saving…')
    try {
      const updated = await updateNote(accessToken, note.id, {
        title: normalizedTitle,
        body: nextBody,
      })
      setNotes((current) => current.map((item) => item.id === updated.id ? updated : item))
      setActiveNote((current) => current?.id === updated.id ? updated : current)
      setTitle((current) => current.trim() ? current : normalizedTitle)
      setSaveStatus('All changes saved')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this note.')
      setSaveStatus('Save failed')
    } finally {
      setIsSaving(false)
    }
  }, [accessToken])

  useEffect(() => {
    if (!activeNote) return
    if (activeNote.title === (title.trim() || 'Untitled note') && (activeNote.body ?? '') === body) {
      return
    }
    setSaveStatus('Unsaved changes')
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current)
    saveTimer.current = window.setTimeout(() => {
      void saveDraft(activeNote, title, body)
    }, 1500)
    return () => {
      if (saveTimer.current !== null) window.clearTimeout(saveTimer.current)
    }
  }, [activeNote, body, saveDraft, title])

  function flushSave() {
    if (saveTimer.current !== null) {
      window.clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    if (activeNote) void saveDraft(activeNote, title, body)
  }

  function chooseNote(note: Note) {
    flushSave()
    setActiveNote(note)
    setTitle(note.title)
    setBody(note.body ?? '')
    setSaveStatus('All changes saved')
    setError('')
  }

  async function addNote() {
    if (!accessToken) return
    flushSave()
    setIsSaving(true)
    setError('')
    try {
      const note = await createNote(accessToken)
      setSearchInput('')
      setQuery('')
      setNotes((current) => [note, ...current])
      setActiveNote(note)
      setTitle(note.title)
      setBody(note.body ?? '')
      setSaveStatus('All changes saved')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not create a note.')
    } finally {
      setIsSaving(false)
    }
  }

  async function removeActiveNote() {
    if (!accessToken || !activeNote || !window.confirm('Move this note to the deleted items?')) return
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current)
    setIsSaving(true)
    setError('')
    try {
      await deleteNote(accessToken, activeNote.id)
      const remaining = notes.filter((note) => note.id !== activeNote.id)
      setNotes(remaining)
      setActiveNote(remaining[0] ?? null)
      setTitle(remaining[0]?.title ?? '')
      setBody(remaining[0]?.body ?? '')
      setSaveStatus('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not delete this note.')
    } finally {
      setIsSaving(false)
    }
  }

  function updateSearch(event: FormEvent<HTMLInputElement>) {
    const value = event.currentTarget.value
    setSearchInput(value)
  }

  return (
    <main className="page-content notes-page">
      <header className="notes-heading">
        <div><p className="eyebrow">A quiet place for your thoughts</p><h1>Notes</h1><p className="welcome-copy">Capture ideas and find them again with full-text search.</p></div>
        <button className="primary-button notes-new-button" disabled={isSaving} onMouseDown={(event) => event.preventDefault()} onClick={() => void addNote()} type="button">＋ New note</button>
      </header>
      {error && <p className="form-message form-message-error" role="alert">{error}</p>}
      <section aria-label="Notes workspace" className="notes-workspace">
        <aside aria-label="Your notes" className="notes-sidebar">
          <label className="notes-search">Search notes<input onChange={updateSearch} placeholder="Search title and body" type="search" value={searchInput} /></label>
          <div aria-live="polite" className="notes-list">
            {isLoading && <p className="notes-empty">Loading notes…</p>}
            {!isLoading && notes.map((note) => <button
              aria-current={activeNote?.id === note.id ? 'page' : undefined}
              className={`notes-list-item${activeNote?.id === note.id ? ' is-active' : ''}`}
              key={note.id}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => chooseNote(note)}
              type="button"
            ><strong>{note.title || 'Untitled note'}</strong><span>{(note.body ?? '').trim().slice(0, 90) || 'No content yet'}</span><time dateTime={note.updated_at}>{new Date(note.updated_at).toLocaleDateString()}</time></button>)}
            {!isLoading && !notes.length && <p className="notes-empty">{query ? 'No notes match your search.' : 'Your notes will appear here.'}</p>}
          </div>
        </aside>
        <section aria-label="Note editor" className="note-editor">
          {activeNote ? <>
            <div className="note-editor-toolbar">
              <span aria-live="polite" className="note-save-state">{isSaving ? 'Saving…' : saveStatus}</span>
              <button className="finance-delete-button" disabled={isSaving} onMouseDown={(event) => event.preventDefault()} onClick={() => void removeActiveNote()} type="button">Delete note</button>
            </div>
            <label className="sr-only" htmlFor="note-title">Note title</label>
            <input
              autoComplete="off"
              className="note-title-input"
              id="note-title"
              maxLength={300}
              onBlur={flushSave}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Untitled note"
              value={title}
            />
            <label className="sr-only" htmlFor="note-body">Note content</label>
            <textarea
              className="note-body-input"
              id="note-body"
              maxLength={100000}
              onBlur={flushSave}
              onChange={(event) => setBody(event.target.value)}
              placeholder="Start writing…"
              value={body}
            />
            <p className="notes-autosave-hint">Your changes save automatically after you pause typing.</p>
          </> :           <div className="notes-first-run"><p className="eyebrow">Ready when you are</p><h2>Create your first note</h2><p>Notes are private to your account and searchable by title and text.</p><button className="primary-button" disabled={isSaving} onMouseDown={(event) => event.preventDefault()} onClick={() => void addNote()} type="button">Create a note</button></div>}
        </section>
      </section>
    </main>
  )
}
