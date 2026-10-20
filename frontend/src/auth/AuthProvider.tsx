import { useAuth0 } from '@auth0/auth0-react'
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { fetchCurrentUser, type AuthUser } from '../api/auth'
import { AuthContext } from './context'

const tokenRefreshIntervalMs = 10 * 60 * 1000

export function AuthProvider({ children }: { children: ReactNode }) {
  const {
    error: auth0Error,
    getAccessTokenSilently,
    getIdTokenClaims,
    isAuthenticated,
    isLoading: isAuth0Loading,
    loginWithRedirect,
    logout,
  } = useAuth0()
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [sessionError, setSessionError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true
    let refreshTimer: number | undefined

    async function loadSession() {
      if (isAuth0Loading) return
      if (!isAuthenticated) {
        setAccessToken(null)
        setUser(null)
        setSessionError(auth0Error?.message ?? null)
        setIsLoading(false)
        return
      }

      setIsLoading(true)
      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
        })
        if (!token) {
          throw new Error('Auth0 did not return a LifeOS API access token.')
        }
        if (!isMounted) return
        setAccessToken(token)
        const idTokenClaims = await getIdTokenClaims()
        if (!idTokenClaims?.__raw) {
          throw new Error('Auth0 did not provide an identity token for LifeOS.')
        }
        const currentUser = await fetchCurrentUser(token, idTokenClaims.__raw)
        if (!isMounted) return
        setUser(currentUser)
        setSessionError(null)
      } catch (cause) {
        if (isMounted) {
          setAccessToken(null)
          setUser(null)
          setSessionError(
            cause instanceof Error ? cause.message : 'Could not restore your LifeOS session.',
          )
        }
      } finally {
        if (isMounted) setIsLoading(false)
      }
    }

    void loadSession()

    if (!isAuth0Loading && isAuthenticated) {
      const refreshAccessToken = async () => {
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE },
          })
          if (!token) {
            throw new Error('Auth0 did not return a LifeOS API access token.')
          }
          if (isMounted) {
            setAccessToken(token)
            setSessionError(null)
          }
        } catch (cause) {
          if (isMounted) {
            setSessionError(
              cause instanceof Error ? cause.message : 'Could not refresh your session.',
            )
          }
        } finally {
          if (isMounted) {
            refreshTimer = window.setTimeout(refreshAccessToken, tokenRefreshIntervalMs)
          }
        }
      }
      refreshTimer = window.setTimeout(refreshAccessToken, tokenRefreshIntervalMs)
    }

    return () => {
      isMounted = false
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer)
    }
  }, [auth0Error, getAccessTokenSilently, getIdTokenClaims, isAuthenticated, isAuth0Loading])

  const signIn = useCallback(
    () => loginWithRedirect({ appState: { returnTo: '/today' } }),
    [loginWithRedirect],
  )
  const signUp = useCallback(
    () =>
      loginWithRedirect({
        authorizationParams: { screen_hint: 'signup' },
        appState: { returnTo: '/today' },
      }),
    [loginWithRedirect],
  )
  const signOut = useCallback(
    () => logout({ logoutParams: { returnTo: `${window.location.origin}/` } }),
    [logout],
  )

  const value = useMemo(
    () => ({
      accessToken,
      user,
      isLoading: isLoading || isAuth0Loading,
      error: sessionError,
      signIn,
      signUp,
      signOut,
    }),
    [accessToken, user, isLoading, isAuth0Loading, sessionError, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
