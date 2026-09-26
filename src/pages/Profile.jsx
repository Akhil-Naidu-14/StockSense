import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import { mockUser } from '../data/mockData'
import { User, Building2, Phone, Mail, Shield, LogOut } from 'lucide-react'

export default function Profile() {
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ ...mockUser })
  const [saved, setSaved] = useState(false)
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const handleSave = () => {
    setSaved(true)
    setEditing(false)
    setTimeout(() => setSaved(false), 2500)
  }

  const handleLogout = () => {
    localStorage.removeItem('stocksense_auth')
    navigate('/login')
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Profile" subtitle="Manage your account details" />

      {saved && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium">
          ✓ Profile updated successfully.
        </div>
      )}

      {/* Avatar + Name */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-5 mb-6">
          <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold">
            {form.name.charAt(0)}
          </div>
          <div>
            <h3 className="text-xl font-bold text-gray-900">{form.name}</h3>
            <p className="text-sm text-gray-500">{form.role} · {form.company}</p>
          </div>
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="ml-auto px-4 py-2 border border-gray-300 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50"
            >
              Edit Profile
            </button>
          )}
        </div>

        {/* Info fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {[
            { label: 'Full Name', field: 'name', icon: User },
            { label: 'Email', field: 'email', icon: Mail, type: 'email' },
            { label: 'Phone', field: 'phone', icon: Phone },
            { label: 'Department', field: 'department', icon: Building2 },
            { label: 'Company', field: 'company', icon: Building2 },
            { label: 'Role', field: 'role', icon: Shield, readOnly: true },
          ].map(({ label, field, icon: Icon, type = 'text', readOnly }) => (
            <div key={field}>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{label}</label>
              <div className="relative">
                <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type={type}
                  value={form[field]}
                  onChange={set(field)}
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
            <button onClick={handleSave} className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700">
              Save Changes
            </button>
            <button onClick={() => { setEditing(false); setForm({ ...mockUser }) }} className="px-5 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Security */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <Shield className="w-4 h-4" /> Security
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Current Password</label>
            <input type="password" placeholder="••••••••"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
              <input type="password" placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirm Password</label>
              <input type="password" placeholder="••••••••"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <button className="px-5 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">
            Update Password
          </button>
        </div>
      </div>

      {/* Danger zone */}
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6">
        <h3 className="font-semibold text-red-700 mb-2 flex items-center gap-2">
          <LogOut className="w-4 h-4" /> Session
        </h3>
        <p className="text-sm text-gray-500 mb-3">Signed in as <strong>{form.email}</strong></p>
        <button
          onClick={handleLogout}
          className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700"
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}
