import { apiRequest } from './client'

export interface AuthUser {
  id: string
  email: string
  full_name: string
  avatar_url: string | null
  timezone: string
  is_verified: boolean
  created_at: string
}

export async function fetchCurrentUser(
  accessToken: string,
  idToken: string,
): Promise<AuthUser> {
  return apiRequest(
    '/auth/session',
    { method: 'POST', headers: { 'X-LifeOS-ID-Token': idToken } },
    accessToken,
  )
}
