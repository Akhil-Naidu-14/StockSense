import { useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import SearchBar from '../components/ui/SearchBar'
import StatusBadge from '../components/ui/StatusBadge'
import { TypeBadge } from '../components/ui/TypeBadge'
import EmptyState from '../components/ui/EmptyState'
import { mockMoveHistory, formatDate } from '../data/mockData'

const TYPES = ['All', 'Receipt', 'Delivery', 'Transfer', 'Adjustment']

export default function MoveHistory() {
  const [search, setSearch] = useState('')
  const [type, setType] = useState('All')
  const [status, setStatus] = useState('All')

  const filtered = mockMoveHistory.filter((m) => {
    const matchSearch =
      m.productName.toLowerCase().includes(search.toLowerCase()) ||
      m.productSku.toLowerCase().includes(search.toLowerCase()) ||
      m.referenceId.toLowerCase().includes(search.toLowerCase()) ||
      m.performedBy.toLowerCase().includes(search.toLowerCase())
    const matchType = type === 'All' || m.type === type
    const matchStatus = status === 'All' || m.status === status
    return matchSearch && matchType && matchStatus
  })

  return (
    <div>
      <PageHeader title="Move History" subtitle="All stock movements across all products and warehouses" />

      <div className="flex flex-wrap gap-3 mb-4">
        <SearchBar value={search} onChange={setSearch} placeholder="Search by product, ref, or person…" className="w-full sm:w-64" />
        <select value={type} onChange={(e) => setType(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
          {TYPES.map((t) => <option key={t}>{t === 'All' ? 'All Types' : t}</option>)}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option value="All">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
          <span className="text-sm text-gray-500">{filtered.length} record{filtered.length !== 1 ? 's' : ''}</span>
        </div>
        {filtered.length === 0 ? (
          <EmptyState title="No movements found" description="Try adjusting your filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Date & Time', 'Type', 'Product', 'From', 'To', 'Qty', 'Reference', 'Performed By', 'Status'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap">
                      <p className="text-gray-700 font-medium">{formatDate(m.date)}</p>
                      <p className="text-xs text-gray-400">{m.time}</p>
                    </td>
                    <td className="px-4 py-3"><TypeBadge type={m.type} /></td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{m.productName}</p>
                      <p className="text-xs text-gray-400">{m.productSku}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{m.fromLocation}</td>
                    <td className="px-4 py-3 text-gray-600">{m.toLocation}</td>
                    <td className="px-4 py-3">
                      <span className={`font-semibold ${m.quantity < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                        {m.quantity > 0 ? '+' : ''}{m.quantity} {m.unit}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{m.referenceId}</td>
                    <td className="px-4 py-3 text-gray-600">{m.performedBy}</td>
                    <td className="px-4 py-3"><StatusBadge status={m.status} /></td>
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
