import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Boxes, ArrowLeft, Mail } from 'lucide-react'
import { forgotPassword, getApiError } from '../../services/authService'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!email) { setError('Please enter your email address.'); return }
    setLoading(true)
    try {
      await forgotPassword(email)
      setSuccess(true)
      // Navigate to OTP page after a short delay, passing email via state
      setTimeout(() => navigate('/verify-otp', { state: { email } }), 1500)
    } catch (err) {
      setError(getApiError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center gap-3 mb-8">
          <Boxes className="w-10 h-10 text-blue-400" />
          <span className="text-3xl font-bold text-white tracking-tight">StockSense</span>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8">
          <Link to="/login" className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-6">
            <ArrowLeft className="w-4 h-4" /> Back to Sign In
          </Link>

          <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-4">
            <Mail className="w-6 h-6 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">Forgot your password?</h2>
          <p className="text-sm text-gray-500 mb-6">
            Enter your registered email and we&apos;ll send you a one-time code to reset your password.
          </p>

          {success ? (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium">
              ✓ OTP sent! Redirecting to verification…
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

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
                {loading ? 'Sending OTP…' : 'Send OTP'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
