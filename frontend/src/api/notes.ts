import { apiRequest } from './client'

export interface Note {
  id: string
  title: string
  body: string | null
  created_at: string
  updated_at: string
}

export interface NoteList {
  items: Note[]
  total: number
}

export function fetchNotes(token: string, query = ''): Promise<NoteList> {
  const params = new URLSearchParams({ limit: '100' })
  if (query.trim()) params.set('query', query.trim())
  return apiRequest(`/notes?${params}`, {}, token)
}

export function createNote(token: string): Promise<Note> {
  return apiRequest('/notes', {
    method: 'POST',
    body: JSON.stringify({ title: 'Untitled note', body: '' }),
  }, token)
}

export function updateNote(
  token: string,
  noteId: string,
  input: { title: string; body: string },
): Promise<Note> {
  return apiRequest(`/notes/${noteId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  }, token)
}

export function deleteNote(token: string, noteId: string): Promise<void> {
  return apiRequest(`/notes/${noteId}`, { method: 'DELETE' }, token)
}
