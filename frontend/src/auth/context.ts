import { createContext, useContext } from 'react'
import type { AuthUser } from '../api/auth'

export interface AuthContextValue {
  accessToken: string | null
  user: AuthUser | null
  isLoading: boolean
  error: string | null
  signIn: () => Promise<void>
  signUp: () => Promise<void>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.')
  }
  return context
}
