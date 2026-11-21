
import { useState } from 'react'
import App from './App'
import { useAuth } from './context/AuthContext'

export default function AuthGate() {
  const { user, loading, login, logout } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleLogin(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      await login(email.trim(), password)
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleLogout() {
    try {
      await logout()
    } catch (err) {
      setError(err.message || 'Logout failed')
    }
  }

  if (loading) {
    return <div style={styles.center}>Loading Datastraw...</div>
  }

  if (!user) {
    return (
      <div style={styles.page}>
        <form onSubmit={handleLogin} style={styles.card}>
          <div style={styles.logo}>D</div>
          <h1 style={styles.title}>Datastraw</h1>
          <p style={styles.subtitle}>
            Smart Roster Management System
          </p>

          <label style={styles.label}>Email address</label>
          <input
            style={styles.input}
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="Enter your email"
            autoComplete="username"
            required
          />

          <label style={styles.label}>Password</label>
          <input
            style={styles.input}
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Enter your password"
            autoComplete="current-password"
            required
          />

          {error && <p style={styles.error}>{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            style={styles.button}
          >
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>

          <p style={styles.footer}>
            Secure access to Datastraw
          </p>
        </form>
      </div>
    )
  }

  return (
    <>
      <div style={styles.accountBar}>
        <span>{user.email}</span>
        <button onClick={handleLogout} style={styles.logout}>
          Logout
        </button>
      </div>
      <App />
    </>
  )
}

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: '#0b1120',
    padding: 20,
    fontFamily: 'Arial, sans-serif'
  },
  card: {
    width: '100%',
    maxWidth: 390,
    padding: 36,
    borderRadius: 16,
    background: '#172033',
    color: '#ffffff',
    boxSizing: 'border-box'
  },
  logo: {
    width: 48,
    height: 48,
    borderRadius: 12,
    display: 'grid',
    placeItems: 'center',
    background: '#2563eb',
    fontSize: 25,
    fontWeight: 'bold'
  },
  title: { marginBottom: 5 },
  subtitle: { color: '#9ca3af', marginBottom: 30 },
  label: {
    display: 'block',
    marginBottom: 8,
    marginTop: 18,
    fontSize: 14
  },
  input: {
    width: '100%',
    boxSizing: 'border-box',
    padding: 13,
    borderRadius: 8,
    border: '1px solid #374151',
    background: '#0f172a',
    color: 'white'
  },
  button: {
    width: '100%',
    marginTop: 24,
    padding: 14,
    border: 0,
    borderRadius: 8,
    background: '#2563eb',
    color: 'white',
    fontWeight: 'bold',
    cursor: 'pointer'
  },
  error: { color: '#f87171', fontSize: 13 },
  footer: {
    textAlign: 'center',
    color: '#9ca3af',
    fontSize: 12,
    marginTop: 24
  },
  center: {
    minHeight: '100vh',
    display: 'grid',
    placeItems: 'center'
  },
  accountBar: {
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 15,
    padding: '10px 20px',
    background: '#111827',
    color: 'white',
    fontSize: 13
  },
  logout: {
    padding: '8px 16px',
    border: 0,
    borderRadius: 6,
    background: '#dc2626',
    color: 'white',
    cursor: 'pointer'
  }
}
