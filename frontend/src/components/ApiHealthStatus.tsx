import { useQuery } from '@tanstack/react-query'
import { fetchApiHealth } from '../api/health'

export function ApiHealthStatus() {
  const { data, error, isPending } = useQuery({
    queryKey: ['api-health'],
    queryFn: fetchApiHealth,
    refetchInterval: 30_000,
  })

  const checks: { name: string; status: 'ok' | 'error' | 'loading' | 'unknown' }[] = [
    { name: 'Frontend → API', status: data ? 'ok' : error ? 'error' : 'loading' },
    { name: 'Backend API', status: data?.checks.backend.status ?? (error ? 'error' : 'loading') },
    { name: 'Database', status: data?.checks.database.status ?? (error ? 'unknown' : 'loading') },
    { name: 'Auth0', status: data?.checks.auth0.status ?? (error ? 'unknown' : 'loading') },
  ]

  return (
    <div aria-live="polite" className="health-card" role="status">
      <div className="health-checks">
        {checks.map((check) => (
          <div className="health-check" key={check.name}>
            <span
              aria-hidden="true"
              className="health-indicator"
              data-status={check.status}
            />
            <span>
              {check.name}:{' '}
              {check.status === 'loading'
                ? 'Checking…'
                : check.status === 'ok'
                  ? 'Connected'
                  : check.status === 'error'
                    ? 'Unavailable'
                    : 'Unknown'}
            </span>
          </div>
        ))}
      </div>
      {isPending && <span>Checking LifeOS services…</span>}
      {error && <span>The frontend could not reach the health endpoint.</span>}
      {data?.status === 'degraded' && <span>One or more backend services are unavailable.</span>}
    </div>
  )
}
