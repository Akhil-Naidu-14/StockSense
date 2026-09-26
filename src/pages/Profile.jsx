import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import ErrorState from '../components/ui/ErrorState'
import { User, Building2, Phone, Mail, Shield, LogOut } from 'lucide-react'
import { getMe, logout, getApiError } from '../services/authService'
import { getStoredUser } from '../services/api'

export default function Profile() {
  const navigate = useNavigate()

  // Local UI state
  const [user, setUser] = useState(getStoredUser)   // seed with cache for instant display
  const [loading, setLoading] = useState(!getStoredUser())
  const [fetchError, setFetchError] = useState('')
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [logoutLoading, setLogoutLoading] = useState(false)

  // Fetch fresh user data from GET /auth/me on mount
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const fresh = await getMe()
        if (!cancelled) {
          setUser(fresh)
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          // 401 is handled globally by the interceptor (redirects to /login)
          // Show error only for other failures
          if (err?.response?.status !== 401) {
            setFetchError(getApiError(err))
          }
          setLoading(false)
        }
      }
    })()
    return () => { cancelled = true }
  }, [])

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const startEditing = () => {
    setForm({ ...(user || {}) })
    setEditing(true)
    setSaveSuccess(false)
  }

  const cancelEditing = () => {
    setEditing(false)
    setForm(null)
  }

  // Profile editing is UI-only for now (no PATCH /auth/me endpoint exists yet)
  const handleSave = async () => {
    setSaving(true)
    await new Promise((r) => setTimeout(r, 600))   // simulate save
    setUser(form)
    setSaving(false)
    setEditing(false)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  const handleLogout = async () => {
    setLogoutLoading(true)
    try {
      await logout()
    } catch {
      // clearAuth already ran inside authService.logout
    }
    navigate('/login', { replace: true })
  }

  // ── Resolve display values (backend field names may vary) ──
  const displayName = user?.name || user?.full_name || '—'
  const displayEmail = user?.email || '—'
  const displayRole  = user?.role  || 'Staff'
  const displayPhone = user?.phone || user?.phone_number || ''
  const displayDept  = user?.department || ''
  const displayCompany = user?.company || user?.company_name || ''
  const initial = displayName.charAt(0).toUpperCase()

  if (loading) return <LoadingSpinner message="Loading profile…" />
  if (fetchError && !user) return <ErrorState message={fetchError} onRetry={() => window.location.reload()} />

  const current = editing ? form : {
    name: displayName, email: displayEmail, role: displayRole,
    phone: displayPhone, department: displayDept, company: displayCompany,
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Profile" subtitle="Your account information" />

      {fetchError && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          ⚠️ Showing cached data. Could not refresh: {fetchError}
        </div>
      )}

      {saveSuccess && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium">
          ✓ Profile updated successfully.
        </div>
      )}

      {/* Avatar + Name card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-5 mb-6">
          <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold shrink-0">
            {initial}
          </div>
          <div className="min-w-0">
            <h3 className="text-xl font-bold text-gray-900 truncate">{displayName}</h3>
            <p className="text-sm text-gray-500">{displayRole}</p>
          </div>
          {!editing && (
            <button
              onClick={startEditing}
              className="ml-auto px-4 py-2 border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50 shrink-0"
            >
              Edit Profile
            </button>
          )}
        </div>

        {/* Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {[
            { label: 'Full Name',   field: 'name',       icon: User,      type: 'text'  },
            { label: 'Email',       field: 'email',      icon: Mail,      type: 'email' },
            { label: 'Phone',       field: 'phone',      icon: Phone,     type: 'tel'   },
            { label: 'Department',  field: 'department', icon: Building2, type: 'text'  },
            { label: 'Company',     field: 'company',    icon: Building2, type: 'text'  },
            { label: 'Role',        field: 'role',       icon: Shield,    type: 'text', readOnly: true },
          ].map(({ label, field, icon: Icon, type, readOnly }) => (
            <div key={field}>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                {label}
              </label>
              <div className="relative">
                <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={type}
                  value={current[field] || ''}
                  onChange={editing && !readOnly ? set(field) : undefined}
                  readOnly={!editing || readOnly}
                  className={`w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm
                    ${editing && !readOnly
                      ? 'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
                      : 'bg-gray-50 cursor-default text-gray-700'
                    }`}
                />
              </div>
            </div>
          ))}
        </div>

        {editing && (
          <div className="flex gap-3 mt-5">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 flex items-center gap-2"
            >
              {saving && <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              {saving ? 'Saving…' : 'Save Changes'}
            </button>
            <button
              onClick={cancelEditing}
              className="px-5 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Security section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Shield className="w-4 h-4" /> Security
        </h3>
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
              <input type="password" placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
              <input type="password" placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <p className="text-xs text-gray-400">
            To change your password, use the{' '}
            <button
              onClick={() => navigate('/forgot-password')}
              className="text-blue-600 hover:underline font-medium"
            >
              Forgot Password
            </button>{' '}
            flow.
          </p>
        </div>
      </div>

      {/* Danger zone */}
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6">
        <h3 className="font-semibold text-red-700 mb-2 flex items-center gap-2">
          <LogOut className="w-4 h-4" /> Session
        </h3>
        <p className="text-sm text-gray-500 mb-3">
          Signed in as <strong>{displayEmail}</strong>
        </p>
        <button
          onClick={handleLogout}
          disabled={logoutLoading}
          className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-60 flex items-center gap-2"
        >
          {logoutLoading && (
            <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
          )}
          {logoutLoading ? 'Signing out…' : 'Sign Out'}
        </button>
      </div>
    </div>
  )
}
