import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/context'

const { createDaybookEntry, deleteDaybookEntry, fetchDaybook, updateDaybookEntry } = vi.hoisted(() => ({
  createDaybookEntry: vi.fn(),
  deleteDaybookEntry: vi.fn(),
  fetchDaybook: vi.fn(),
  updateDaybookEntry: vi.fn(),
}))

vi.mock('../api/daybook', () => ({
  createDaybookEntry,
  deleteDaybookEntry,
  fetchDaybook,
  updateDaybookEntry,
}))

import { DaybookPage } from './DaybookPage'

function renderDaybook() {
  return render(
    <AuthContext.Provider value={{
      accessToken: 'test-token',
      user: null,
      isLoading: false,
      error: null,
      signIn: async () => {},
      signUp: async () => {},
      signOut: async () => {},
    }}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DaybookPage />
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

function localDateKey(date: Date): string {
  const parts = new Intl.DateTimeFormat('en', {
    day: '2-digit',
    month: '2-digit',
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
  }).formatToParts(date)
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''
  return [
    value('year'),
    value('month'),
    value('day'),
  ].join('-')
}

afterEach(() => {
  cleanup()
})

beforeEach(() => {
  vi.clearAllMocks()
  fetchDaybook.mockResolvedValue({ entries: [], activities: [] })
})

describe('DaybookPage', () => {
  it('creates a private diary note for the selected day', async () => {
    const todayKey = localDateKey(new Date())
    const savedEntry = {
      id: 'entry-1',
      entry_date: todayKey,
      title: 'A good day',
      content: 'A few lines to remember.',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    createDaybookEntry.mockResolvedValue(savedEntry)

    renderDaybook()
    await screen.findByText('A fresh page')
    fireEvent.click(screen.getByRole('button', { name: /add note/i }))
    fireEvent.change(screen.getByLabelText('Entry title'), { target: { value: savedEntry.title } })
    fireEvent.change(screen.getByLabelText('Entry content'), { target: { value: savedEntry.content } })
    fireEvent.click(screen.getByRole('button', { name: 'Save note' }))

    await waitFor(() => {
      expect(createDaybookEntry).toHaveBeenCalledWith('test-token', {
        entry_date: todayKey,
        title: savedEntry.title,
        content: savedEntry.content,
      })
    })
    expect(await screen.findByRole('heading', { name: 'Daily notes 1' })).toBeInTheDocument()
    expect(screen.getByText(savedEntry.title)).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Saved')
  })

  it('shows synchronized activities as links to their source feature', async () => {
    const todayKey = localDateKey(new Date())
    fetchDaybook.mockResolvedValue({
      entries: [],
      activities: [{
        id: 'task:task-1',
        activity_date: todayKey,
        title: 'Finish the draft',
        description: 'Review the final section',
        source: 'tasks',
        status: 'Open',
        url: '/tasks',
        occurred_at: null,
      }],
    })

    renderDaybook()

    const activityLink = await screen.findByRole('link', { name: /finish the draft/i })
    expect(activityLink).toHaveAttribute('href', '/tasks')
    expect(screen.getByText('Review the final section')).toBeInTheDocument()
  })
})
