import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthContext } from '../auth/context'

const {
  addWater,
  completeHabit,
  createHabit,
  createSleepLog,
  fetchHabits,
  fetchMoodHistory,
  fetchSleepLogs,
  fetchTodayMood,
  fetchWaterToday,
  saveMood,
} = vi.hoisted(() => ({
  addWater: vi.fn(),
  completeHabit: vi.fn(),
  createHabit: vi.fn(),
  createSleepLog: vi.fn(),
  fetchHabits: vi.fn(),
  fetchMoodHistory: vi.fn(),
  fetchSleepLogs: vi.fn(),
  fetchTodayMood: vi.fn(),
  fetchWaterToday: vi.fn(),
  saveMood: vi.fn(),
}))

vi.mock('../api/healthTracking', () => ({
  addWater,
  completeHabit,
  createHabit,
  createSleepLog,
  fetchHabits,
  fetchMoodHistory,
  fetchSleepLogs,
  fetchTodayMood,
  fetchWaterToday,
  saveMood,
}))

import { HealthPage } from './HealthPage'

function renderHealthPage() {
  return render(
    <AuthContext.Provider value={{
      accessToken: 'health-token',
      user: {
        id: 'user-1',
        email: 'person@example.com',
        full_name: 'Taylor Person',
        avatar_url: null,
        timezone: 'Asia/Kolkata',
        is_verified: true,
        created_at: new Date().toISOString(),
      },
      isLoading: false,
      error: null,
      signIn: async () => {},
      signUp: async () => {},
      signOut: async () => {},
    }}>
      <HealthPage />
    </AuthContext.Provider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  fetchTodayMood.mockResolvedValue(null)
  fetchMoodHistory.mockResolvedValue({ items: [], days: 7 })
  fetchSleepLogs.mockResolvedValue({ items: [] })
  fetchHabits.mockResolvedValue({ items: [], total: 0 })
  fetchWaterToday.mockResolvedValue({
    log_date: '2026-10-20',
    total_ml: 0,
    goal_ml: 2000,
    items: [],
  })
})

afterEach(() => cleanup())

describe('HealthPage', () => {
  it('uses a 250 ml default and lets the user log a custom water amount', async () => {
    addWater.mockResolvedValue({ id: 'water-1', amount_ml: 425 })
    renderHealthPage()

    const amount = await screen.findByLabelText('Amount (ml)')
    expect(amount).toHaveValue(250)
    fireEvent.change(amount, { target: { value: '425' } })
    fireEvent.click(screen.getByRole('button', { name: '＋ Add 425 ml' }))

    await waitFor(() => expect(addWater).toHaveBeenCalledWith('health-token', 425))
    expect(await screen.findByRole('status')).toHaveTextContent('425 ml added.')
  })

  it('switches sleep time inputs between 24-hour and AM/PM formats', async () => {
    renderHealthPage()

    const hour = await screen.findByLabelText('Bedtime hour')
    expect(hour.querySelectorAll('option')).toHaveLength(24)
    fireEvent.click(screen.getByLabelText('12-hour (AM/PM)'))
    fireEvent.change(hour, { target: { value: '11' } })
    fireEvent.change(screen.getByLabelText('Bedtime AM or PM'), { target: { value: 'pm' } })

    expect(hour).toHaveValue('11')
    fireEvent.click(screen.getByLabelText('24-hour'))
    expect(hour).toHaveValue('23')
    expect(hour.querySelectorAll('option')).toHaveLength(24)
  })
})
