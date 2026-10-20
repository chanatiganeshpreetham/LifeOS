import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiHealthStatus } from './ApiHealthStatus'

const healthyResponse = {
  status: 'ok',
  checks: {
    backend: { status: 'ok' },
    database: { status: 'ok' },
    auth0: { status: 'ok' },
  },
}

function renderStatus() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ApiHealthStatus />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ApiHealthStatus', () => {
  it('shows a loading state while checking the API', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    renderStatus()

    expect(screen.getByRole('status')).toHaveTextContent('Checking LifeOS services')
  })

  it('reports a successful API response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => healthyResponse,
      }),
    )

    renderStatus()

    expect(await screen.findByText('Frontend → API: Connected')).toBeInTheDocument()
    expect(await screen.findByText('Backend API: Connected')).toBeInTheDocument()
    expect(await screen.findByText('Database: Connected')).toBeInTheDocument()
    expect(await screen.findByText('Auth0: Connected')).toBeInTheDocument()
  })

  it('reports unavailable dependencies when a health check is degraded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ...healthyResponse,
          status: 'degraded',
          checks: {
            ...healthyResponse.checks,
            database: { status: 'error' },
          },
        }),
      }),
    )

    renderStatus()

    expect(await screen.findByText('Database: Unavailable')).toBeInTheDocument()
    expect(screen.getByText('One or more backend services are unavailable.')).toBeInTheDocument()
  })

  it('shows a clear message when the API request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network unavailable')))

    renderStatus()

    await waitFor(() => {
      expect(
        screen.getByText('Backend API: Unavailable'),
      ).toBeInTheDocument()
    })
    expect(screen.getByText('Frontend → API: Unavailable')).toBeInTheDocument()
    expect(screen.getByText('The frontend could not reach the health endpoint.')).toBeInTheDocument()
  })
})
