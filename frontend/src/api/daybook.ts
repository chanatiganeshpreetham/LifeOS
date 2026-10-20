import { apiRequest } from './client'

export interface DaybookEntry {
  id: string
  entry_date: string
  title: string
  content: string
  created_at: string
  updated_at: string
}

export interface DaybookActivity {
  id: string
  activity_date: string
  title: string
  description: string | null
  source: 'tasks' | 'reminders' | 'finance' | 'health' | 'notes'
  status: string | null
  url: string
  occurred_at: string | null
}

export interface DaybookData {
  entries: DaybookEntry[]
  activities: DaybookActivity[]
}

export function fetchDaybook(
  token: string,
  startDate: string,
  endDate: string,
): Promise<DaybookData> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate })
  return apiRequest(`/daybook?${params}`, {}, token)
}

export function createDaybookEntry(
  token: string,
  input: { entry_date: string; title: string; content: string },
): Promise<DaybookEntry> {
  return apiRequest('/daybook/entries', {
    method: 'POST',
    body: JSON.stringify(input),
  }, token)
}

export function updateDaybookEntry(
  token: string,
  entryId: string,
  input: { title: string; content: string },
): Promise<DaybookEntry> {
  return apiRequest(`/daybook/entries/${entryId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  }, token)
}

export function deleteDaybookEntry(token: string, entryId: string): Promise<void> {
  return apiRequest(`/daybook/entries/${entryId}`, { method: 'DELETE' }, token)
}
