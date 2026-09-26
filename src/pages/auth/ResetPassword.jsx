import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Boxes, ArrowLeft, Eye, EyeOff, KeyRound } from 'lucide-react'
import { resetPassword, getApiError } from '../../services/authService'

export default function ResetPassword() {
  const navigate = useNavigate()
  const location = useLocation()
  // Passed from VerifyOTP via navigate state
  const { email = '', otp = '', resetToken = '' } = location.state || {}

  const [form, setForm] = useState({ password: '', confirm: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.password || !form.confirm) { setError('Please fill in all fields.'); return }
    if (form.password !== form.confirm) { setError('Passwords do not match.'); return }
    if (form.password.length < 8) { setError('Password must be at least 8 characters.'); return }
    setLoading(true)
    try {
      await resetPassword({ email, otp, newPassword: form.password })
      setSuccess(true)
      setTimeout(() => navigate('/login', { replace: true }), 2000)
    } catch (err) {
      setError(getApiError(err))
    } finally {
      setLoading(false)
    }
  }

  if (!email) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center max-w-sm w-full">
          <p className="text-gray-600 mb-4">Session expired. Please start again.</p>
          <Link to="/forgot-password" className="text-blue-600 hover:underline text-sm font-medium">
            Go to Forgot Password
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-3 mb-8">
          <Boxes className="w-10 h-10 text-blue-400" />
          <span className="text-3xl font-bold text-white tracking-tight">StockSense</span>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-4">
            <KeyRound className="w-6 h-6 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">Set new password</h2>
          <p className="text-sm text-gray-500 mb-6">
            Create a strong password for <strong>{email}</strong>
          </p>

          {success ? (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium">
              ✓ Password reset successfully! Redirecting to sign in…
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <div className="relative">
                  <input
                    type={showPwd ? 'text' : 'password'}
                    value={form.password}
                    onChange={set('password')}
                    placeholder="Min 8 characters"
                    autoComplete="new-password"
                    className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPwd((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                  >
                    {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
                <input
                  type="password"
                  value={form.confirm}
                  onChange={set('confirm')}
                  placeholder="Repeat password"
                  autoComplete="new-password"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Password strength hint */}
              {form.password && (
                <div className="flex gap-1">
                  {[8, 12, 16].map((threshold, i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full ${
                        form.password.length >= threshold ? 'bg-blue-500' : 'bg-gray-200'
                      }`}
                    />
                  ))}
                  <span className="text-xs text-gray-400 ml-1">
                    {form.password.length < 8 ? 'Too short' : form.password.length < 12 ? 'Fair' : 'Strong'}
                  </span>
                </div>
              )}

              {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading && (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {loading ? 'Resetting…' : 'Reset Password'}
              </button>

              <p className="text-center text-xs text-gray-500">
                Remembered it?{' '}
                <Link to="/login" className="text-blue-600 hover:underline font-medium">
                  Sign in
                </Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
