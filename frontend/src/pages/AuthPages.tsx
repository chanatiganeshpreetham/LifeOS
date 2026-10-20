import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../auth/context'

function AuthEntryPage({ isSignUp }: { isSignUp: boolean }) {
  const { error: sessionError, isLoading, signIn, signUp, user } = useAuth()
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const title = isSignUp ? 'Make space for what matters.' : 'Good to see you.'
  const action = isSignUp ? signUp : signIn

  if (isLoading) {
    return <main className="page-content"><p>Preparing your LifeOS…</p></main>
  }
  if (user) {
    return <Navigate replace to="/today" />
  }

  async function beginAuthentication() {
    setError('')
    setIsSubmitting(true)
    try {
      await action()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not connect to Auth0.')
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-layout">
      <section aria-labelledby="auth-heading" className="auth-card">
        <Link className="auth-back-link" to="/">
          <span aria-hidden="true">←</span> LifeOS
        </Link>
        <p className="eyebrow">{isSignUp ? 'Get started' : 'Your personal space'}</p>
        <h1 className="auth-heading" id="auth-heading">{title}</h1>
        <p className="auth-description">
          {isSignUp
            ? 'Create your LifeOS account securely with Auth0.'
            : 'Sign in securely to continue to LifeOS.'}
        </p>
        {(error || sessionError) && (
          <div className="form-message form-message-error" role="alert">
            {error || sessionError}
          </div>
        )}
        <button
          className="primary-button"
          disabled={isSubmitting}
          onClick={() => void beginAuthentication()}
          type="button"
        >
          {isSubmitting
            ? 'Connecting…'
            : isSignUp
              ? 'Continue to create account'
              : 'Continue to sign in'}
        </button>
        <p className="auth-footer">
          {isSignUp ? 'Already have an account? ' : 'New to LifeOS? '}
          <Link className="text-link" to={isSignUp ? '/login' : '/register'}>
            {isSignUp ? 'Sign in' : 'Create an account'}
          </Link>
        </p>
        {!isSignUp && (
          <p className="auth-footer">
            Forgot your password? Auth0 will provide account recovery during sign-in.
          </p>
        )}
      </section>
    </main>
  )
}

export function LoginPage() {
  return <AuthEntryPage isSignUp={false} />
}

export function RegisterPage() {
  return <AuthEntryPage isSignUp />
}
