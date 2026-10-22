export interface HealthResponse {
  status: 'ok' | 'degraded'
  checks: {
    backend: HealthComponent
    database: DatabaseHealthComponent
    auth0: HealthComponent
    background_tasks: BackgroundTasksHealth
  }
}

export interface HealthComponent {
  status: 'ok' | 'error'
}

export interface DatabaseHealthComponent extends HealthComponent {
  provider: 'prisma_postgres' | 'other'
}

export interface BackgroundTasksHealth {
  status: 'ok' | 'error'
  scheduler: HealthComponent
}

function isHealthComponent(value: unknown): value is HealthComponent {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    (value.status === 'ok' || value.status === 'error')
  )
}

function isDatabaseHealthComponent(value: unknown): value is DatabaseHealthComponent {
  return (
    isHealthComponent(value) &&
    'provider' in value &&
    (value.provider === 'prisma_postgres' || value.provider === 'other')
  )
}

function isBackgroundTasksHealth(value: unknown): value is BackgroundTasksHealth {
  return (
    typeof value === 'object' &&
    value !== null &&
    'status' in value &&
    (value.status === 'ok' || value.status === 'error') &&
    'scheduler' in value &&
    isHealthComponent(value.scheduler)
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
    !('auth0' in payload.checks) ||
    !('background_tasks' in payload.checks)
  ) {
    return false
  }
  return (
    isHealthComponent(payload.checks.backend) &&
    isDatabaseHealthComponent(payload.checks.database) &&
    isHealthComponent(payload.checks.auth0) &&
    isBackgroundTasksHealth(payload.checks.background_tasks)
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
