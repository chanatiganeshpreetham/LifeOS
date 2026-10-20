export interface HealthResponse {
  status: 'ok' | 'degraded'
  checks: {
    backend: HealthComponent
    database: HealthComponent
    auth0: HealthComponent
  }
}

export interface HealthComponent {
  status: 'ok' | 'error'
}

function isHealthComponent(value: unknown): value is HealthComponent {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    (value.status === 'ok' || value.status === 'error')
  )
}

function isHealthResponse(payload: unknown): payload is HealthResponse {
  if (
    typeof payload !== 'object' ||
    payload === null ||
    !('status' in payload) ||
    (payload.status !== 'ok' && payload.status !== 'degraded') ||
    !('checks' in payload) ||
    typeof payload.checks !== 'object' ||
    payload.checks === null ||
    !('backend' in payload.checks) ||
    !('database' in payload.checks) ||
    !('auth0' in payload.checks)
  ) {
    return false
  }
  return (
    isHealthComponent(payload.checks.backend) &&
    isHealthComponent(payload.checks.database) &&
    isHealthComponent(payload.checks.auth0)
  )
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/+$/, '')

export async function fetchApiHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`)
  if (!response.ok) {
    throw new Error(`API health check failed with status ${response.status}.`)
  }
  const payload: unknown = await response.json()
  if (!isHealthResponse(payload)) {
    throw new Error('The API returned an invalid health response.')
  }
  return payload
}
