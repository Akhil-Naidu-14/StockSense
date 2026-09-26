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
// Expected body: { name, email, password }
// Expected response: { access_token, token_type, user? }
export async function signup({ name, email, password }) {
  const { data } = await api.post('/auth/signup', { name, email, password })
  // Store token + user if the backend returns them immediately
  if (data.access_token) {
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
  if (data.access_token) {
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
// Expected body: { email }
// Expected response: { message } or { detail }
export async function forgotPassword(email) {
  const { data } = await api.post('/auth/forgot-password', { email })
  return data
}

// ── Verify OTP ───────────────────────────────────────────────
// Expected body: { email, otp }
// Expected response: { message, reset_token? }
export async function verifyOtp({ email, otp }) {
  const { data } = await api.post('/auth/verify-otp', { email, otp })
  return data
}

// ── Reset password ───────────────────────────────────────────
// Expected body: { email, otp, new_password }
//   (adjust fields to match your backend if it uses a reset_token instead)
export async function resetPassword({ email, otp, newPassword }) {
  const { data } = await api.post('/auth/reset-password', {
    email,
    otp,
    new_password: newPassword,
  })
  return data
}

// ── Convenience: extract a readable error message ────────────
export function getApiError(error) {
  return (
    error?.response?.data?.detail ||
    error?.response?.data?.message ||
    error?.response?.data?.error ||
    error?.message ||
    'An unexpected error occurred.'
  )
}
