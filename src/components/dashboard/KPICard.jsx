export default function KPICard({ title, value, subtitle, icon: Icon, color = 'blue' }) {
  const colors = {
    blue:   { bg: 'bg-blue-50',   icon: 'bg-blue-100 text-blue-600' },
    green:  { bg: 'bg-green-50',  icon: 'bg-green-100 text-green-600' },
    yellow: { bg: 'bg-yellow-50', icon: 'bg-yellow-100 text-yellow-600' },
    red:    { bg: 'bg-red-50',    icon: 'bg-red-100 text-red-600' },
    purple: { bg: 'bg-purple-50', icon: 'bg-purple-100 text-purple-600' },
  }
  const c = colors[color] || colors.blue

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${c.icon}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-gray-500 truncate">{title}</p>
        <p className="text-2xl font-bold text-gray-900 leading-tight">{value}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5 truncate">{subtitle}</p>}
      </div>
    </div>
  )
}
