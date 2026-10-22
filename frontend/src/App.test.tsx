import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppNavigation } from './App'
import { AuthContext, type AuthContextValue } from './auth/context'

const authenticatedContext: AuthContextValue = {
  accessToken: 'test-token',
  user: {
    id: 'user-1',
    email: 'person@example.com',
    full_name: 'Test Person',
    avatar_url: null,
    timezone: 'Asia/Kolkata',
    is_verified: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  isLoading: false,
  error: null,
  signIn: async () => {},
  signUp: async () => {},
  signOut: async () => {},
}

describe('AppNavigation', () => {
  it('opens a module menu and closes it on Escape or navigation', () => {
    render(
      <AuthContext.Provider value={authenticatedContext}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={['/today']}
        >
          <AppNavigation />
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    const trigger = screen.getByRole('button', { name: 'Open LifeOS menu' })
    fireEvent.click(trigger)

    const mobileNavigation = screen.getByRole('navigation', { name: 'Mobile navigation' })
    for (const label of ['Today', 'Tasks', 'Reminders', 'Finance', 'Health', 'Notes', 'Daybook']) {
      expect(mobileNavigation).toHaveTextContent(label)
    }

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument()
    expect(trigger).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(trigger)
    const reopenedNavigation = screen.getByRole('navigation', { name: 'Mobile navigation' })
    fireEvent.click(within(reopenedNavigation).getByRole('link', { name: /finance/i }))
    expect(screen.queryByRole('navigation', { name: 'Mobile navigation' })).not.toBeInTheDocument()
  })
})
