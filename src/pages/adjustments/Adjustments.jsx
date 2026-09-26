import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import SearchBar from '../../components/ui/SearchBar'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { mockAdjustments, formatDate } from '../../data/mockData'
import { TrendingUp, TrendingDown } from 'lucide-react'

const STATUSES = ['All', 'completed', 'pending']

export default function Adjustments() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')

  const filtered = mockAdjustments.filter((a) => {
    const matchSearch =
      a.id.toLowerCase().includes(search.toLowerCase()) ||
      a.productName.toLowerCase().includes(search.toLowerCase()) ||
      a.reason.toLowerCase().includes(search.toLowerCase())
    const matchStatus = status === 'All' || a.status === status
    return matchSearch && matchStatus
  })

  return (
    <div>
      <PageHeader
        title="Adjustments"
        subtitle={`${mockAdjustments.length} total adjustments`}
        action={{ label: 'Create Adjustment', onClick: () => navigate('/adjustments/create') }}
      />

      <div className="flex flex-wrap gap-3 mb-4">
        <SearchBar value={search} onChange={setSearch} placeholder="Search adjustments…" className="w-full sm:w-64" />
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
          {STATUSES.map((s) => <option key={s}>{s === 'All' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState title="No adjustments found" description="Try a different search or create a new adjustment." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Adj #', 'Date', 'Product', 'Warehouse', 'Before', 'After', 'Change', 'Reason', 'By', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-gray-700">{a.id}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(a.date)}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{a.productName}</p>
                      <p className="text-xs text-gray-400">{a.productSku}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{a.warehouseName}</td>
                    <td className="px-4 py-3 text-gray-500">{a.previousQty} {a.unit}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{a.newQty} {a.unit}</td>
                    <td className="px-4 py-3">
                      <div className={`flex items-center gap-1 text-xs font-semibold ${a.adjustedQty >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {a.adjustedQty >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                        {a.adjustedQty > 0 ? '+' : ''}{a.adjustedQty} {a.unit}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{a.reason}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{a.adjustedBy}</td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3">
                      <button className="text-blue-600 hover:underline text-xs font-medium" onClick={() => {}}>View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
