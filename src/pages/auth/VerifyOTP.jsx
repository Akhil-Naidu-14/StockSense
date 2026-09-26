import { useState, useRef } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Boxes, ArrowLeft, ShieldCheck } from 'lucide-react'
import { verifyOtp, getApiError } from '../../services/authService'

export default function VerifyOTP() {
  const navigate = useNavigate()
  const location = useLocation()
  // email is passed via navigate state from ForgotPassword
  const email = location.state?.email || ''

  const [otp, setOtp] = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const inputsRef = useRef([])

  // Handle individual digit input
  const handleChange = (idx, val) => {
    if (!/^\d?$/.test(val)) return
    const next = [...otp]
    next[idx] = val
    setOtp(next)
    if (val && idx < 5) inputsRef.current[idx + 1]?.focus()
  }

  const handleKeyDown = (idx, e) => {
    if (e.key === 'Backspace' && !otp[idx] && idx > 0) {
      inputsRef.current[idx - 1]?.focus()
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    const next = Array.from({ length: 6 }, (_, i) => text[i] || '')
    setOtp(next)
    inputsRef.current[Math.min(text.length, 5)]?.focus()
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const code = otp.join('')
    if (code.length < 6) { setError('Please enter the full 6-digit OTP.'); return }
    setError('')
    setLoading(true)
    try {
      const data = await verifyOtp({ email, otp: code })
      setSuccess(true)
      setTimeout(() =>
        navigate('/reset-password', {
          state: { email, otp: code, resetToken: data?.reset_token },
        }), 1200)
    } catch (err) {
      setError(getApiError(err))
      setOtp(['', '', '', '', '', ''])
      inputsRef.current[0]?.focus()
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
          <Link to="/forgot-password" className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-6">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>

          <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-4">
            <ShieldCheck className="w-6 h-6 text-blue-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">Verify OTP</h2>
          <p className="text-sm text-gray-500 mb-2">
            We sent a 6-digit code to
          </p>
          <p className="text-sm font-semibold text-gray-800 mb-6">{email}</p>

          {success ? (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium">
              ✓ OTP verified! Redirecting…
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* OTP boxes */}
              <div className="flex gap-2 justify-center" onPaste={handlePaste}>
                {otp.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => (inputsRef.current[idx] = el)}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleChange(idx, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(idx, e)}
                    className="w-12 h-12 text-center text-xl font-bold border-2 border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
                  />
                ))}
              </div>

              {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-2 rounded-lg text-center">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || otp.join('').length < 6}
                className="w-full py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading && (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {loading ? 'Verifying…' : 'Verify OTP'}
              </button>

              <p className="text-center text-xs text-gray-500">
                Didn&apos;t receive the code?{' '}
                <button
                  type="button"
                  onClick={() => navigate('/forgot-password')}
                  className="text-blue-600 hover:underline font-medium"
                >
                  Resend OTP
                </button>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
