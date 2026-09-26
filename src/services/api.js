// ============================================================
//  src/services/api.js
//  Axios instance – single source for all HTTP calls.
//  - Reads base URL from VITE_API_BASE_URL env variable
//  - Attaches Authorization: Bearer <token> automatically
//  - On 401: clears stored credentials and redirects to /login
// ============================================================
import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// ── Request interceptor: attach JWT ─────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('stocksense_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response interceptor: handle 401 ────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear credentials
      localStorage.removeItem('stocksense_token')
      localStorage.removeItem('stocksense_user')
      // Redirect to login only if not already on an auth page
      const authPaths = ['/login', '/signup', '/forgot-password', '/verify-otp', '/reset-password']
      const isOnAuthPage = authPaths.some((p) => window.location.pathname.startsWith(p))
      if (!isOnAuthPage) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api

// ── Token helpers ────────────────────────────────────────────
export const setToken = (token) => localStorage.setItem('stocksense_token', token)
export const getToken = () => localStorage.getItem('stocksense_token')
export const clearToken = () => localStorage.removeItem('stocksense_token')

// ── User cache helpers (quick display without re-fetching) ───
export const setStoredUser = (user) =>
  localStorage.setItem('stocksense_user', JSON.stringify(user))
export const getStoredUser = () => {
  try {
    return JSON.parse(localStorage.getItem('stocksense_user') || 'null')
  } catch {
    return null
  }
}
export const clearStoredUser = () => localStorage.removeItem('stocksense_user')

// ── Full sign-out helper ─────────────────────────────────────
export const clearAuth = () => {
  clearToken()
  clearStoredUser()
  // Legacy key from the mock phase – clear it too
  localStorage.removeItem('stocksense_auth')
}
