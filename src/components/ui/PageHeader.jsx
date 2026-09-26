import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus } from 'lucide-react'

export default function PageHeader({ title, subtitle, backTo, action }) {
  const navigate = useNavigate()
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
      <div className="flex items-center gap-3">
        {backTo && (
          <button
            onClick={() => navigate(backTo)}
            className="p-2 rounded-lg hover:bg-gray-200 text-gray-500"
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
        )}
        <div>
          <h2 className="text-xl font-bold text-gray-900">{title}</h2>
          {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action && (
        <button
          onClick={action.onClick}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 shrink-0"
        >
          {action.icon || <Plus className="w-4 h-4" />}
          {action.label}
        </button>
      )}
    </div>
  )
}
