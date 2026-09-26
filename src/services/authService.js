// ============================================================
//  src/services/authService.js
//  Thin wrapper around the real backend auth endpoints.
//  Only calls the 7 endpoints that currently exist:
//    POST /auth/signup
//    POST /auth/login
//    GET  /auth/me
//    POST /auth/logout
//    POST /auth/forgot-password
//    POST /auth/verify-otp
//    POST /auth/reset-password
// ============================================================
import api, { setToken, setStoredUser, clearAuth } from './api'

// ── Sign up ──────────────────────────────────────────────────
// Expected body: { name, email, password, role?, phone? }
// Expected response: 201 Created with user object or access_token
export async function signup({ name, email, password, role, phone }) {
  const payload = { name, email, password }
  if (role) payload.role = role
  if (phone) payload.phone = phone
  const { data } = await api.post('/auth/signup', payload)
  // Store token + user if the backend returns them immediately
  if (data?.access_token) {
    setToken(data.access_token)
    if (data.user) setStoredUser(data.user)
  }
  return data
}

// ── Login ────────────────────────────────────────────────────
// Expected body: { email, password }
// Expected response: { access_token, token_type, user? }
export async function login({ email, password }) {
  const { data } = await api.post('/auth/login', { email, password })
  if (data?.access_token) {
    setToken(data.access_token)
    if (data.user) setStoredUser(data.user)
  }
  return data
}

// ── Get current user ─────────────────────────────────────────
// Expected response: { id, name, email, role, ... }
export async function getMe() {
  const { data } = await api.get('/auth/me')
  if (data) setStoredUser(data)
  return data
}

// ── Logout ───────────────────────────────────────────────────
export async function logout() {
  try {
    await api.post('/auth/logout')
  } finally {
    // Always clear local state even if the server call fails
    clearAuth()
  }
}

// ── Forgot password ──────────────────────────────────────────
export async function forgotPassword(email) {
  const { data } = await api.post('/auth/forgot-password', { email })
  return data
}

// ── Verify OTP ───────────────────────────────────────────────
export async function verifyOtp({ email, otp }) {
  const { data } = await api.post('/auth/verify-otp', { email, otp })
  return data
}

// ── Reset password ───────────────────────────────────────────
export async function resetPassword({ email, otp, newPassword }) {
  const { data } = await api.post('/auth/reset-password', {
    email,
    otp,
    new_password: newPassword,
  })
  return data
}

// ── Convenience: extract a readable error message ────────────
// Guaranteed to ALWAYS return a primitive string to prevent JSX render crashes
export function getApiError(error) {
  if (!error) return 'An unexpected error occurred.'

  const status = error.response?.status
  const data = error.response?.data

  if (data) {
    // 1. FastAPI 422 validation error: detail is an array of objects [{ loc, msg, type }]
    if (Array.isArray(data.detail)) {
      const messages = data.detail.map((err) => {
        if (typeof err === 'string') return err
        if (err && typeof err === 'object') {
          const locStr = Array.isArray(err.loc) ? err.loc.filter((l) => l !== 'body').join(' → ') : ''
          const msg = err.msg || 'Invalid value'
          return locStr ? `${locStr}: ${msg}` : msg
        }
        return String(err)
      })
      return messages.join('. ')
    }

    // 2. detail is a string
    if (typeof data.detail === 'string' && data.detail.trim()) {
      return data.detail
    }

    // 3. detail is an object
    if (data.detail && typeof data.detail === 'object') {
      if (typeof data.detail.message === 'string') return data.detail.message
      if (typeof data.detail.error === 'string') return data.detail.error
    }

    // 4. message or error top-level fields
    if (typeof data.message === 'string' && data.message.trim()) {
      return data.message
    }
    if (typeof data.error === 'string' && data.error.trim()) {
      return data.error
    }
  }

  // Fallback by HTTP status codes
  if (status === 409) {
    return 'An account with this email address already exists.'
  }
  if (status === 422) {
    return 'Validation failed. Please check your input fields.'
  }
  if (status === 400) {
    return 'Bad request. Please check your information and try again.'
  }
  if (status === 401) {
    return 'Invalid credentials or unauthorized.'
  }
  if (status === 403) {
    return 'Access denied.'
  }
  if (status === 404) {
    return 'Requested resource not found.'
  }
  if (status && status >= 500) {
    return 'Server error. Please try again later.'
  }

  // Network Error / Timeout / Generic Error
  if (typeof error.message === 'string' && error.message) {
    if (error.message.includes('Network Error')) {
      return 'Unable to connect to the server. Please check your network connection.'
    }
    return error.message
  }

  return 'An unexpected error occurred.'
}
