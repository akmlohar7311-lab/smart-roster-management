
import { supabase } from './supabase'

// Production backend URL comes from Render environment variables.
// Local development falls back to the Vite proxy.
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ''
).replace(/\/+$/, '')

function getApiUrl(path) {
  // Support absolute URLs too.
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  // Normalize the API path.
  let apiPath = path.startsWith('/') ? path : `/${path}`

  // Remove an existing /api prefix to prevent duplicate paths.
  apiPath = apiPath.replace(/^\/api(?=\/|$)/, '') || '/'

  // Production: call Render backend directly.
  if (API_BASE_URL) {
    return `${API_BASE_URL}${apiPath}`
  }

  // Local development: use Vite proxy.
  return `/api${apiPath}`
}

export async function apiFetch(path, options = {}) {
  const {
    data: { session },
    error
  } = await supabase.auth.getSession()

  if (error) {
    throw error
  }

  const headers = new Headers(options.headers || {})

  if (session?.access_token) {
    headers.set(
      'Authorization',
      `Bearer ${session.access_token}`
    )
  }

  return fetch(getApiUrl(path), {
    ...options,
    headers
  })
}
