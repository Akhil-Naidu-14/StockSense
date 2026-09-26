import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import SearchBar from '../../components/ui/SearchBar'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { mockTransfers, formatDate } from '../../data/mockData'
import { ArrowRight } from 'lucide-react'

const STATUSES = ['All', 'completed', 'pending', 'cancelled']

export default function Transfers() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')

  const filtered = mockTransfers.filter((t) => {
    const matchSearch =
      t.id.toLowerCase().includes(search.toLowerCase()) ||
      t.productName.toLowerCase().includes(search.toLowerCase()) ||
      t.fromWarehouseName.toLowerCase().includes(search.toLowerCase()) ||
      t.toWarehouseName.toLowerCase().includes(search.toLowerCase())
    const matchStatus = status === 'All' || t.status === status
    return matchSearch && matchStatus
  })

  return (
    <div>
      <PageHeader
        title="Transfers"
        subtitle={`${mockTransfers.length} total transfers`}
        action={{ label: 'Create Transfer', onClick: () => navigate('/transfers/create') }}
      />

      <div className="flex flex-wrap gap-3 mb-4">
        <SearchBar value={search} onChange={setSearch} placeholder="Search transfers…" className="w-full sm:w-64" />
        <select value={status} onChange={(e) => setStatus(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
          {STATUSES.map((s) => <option key={s}>{s === 'All' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState title="No transfers found" description="Try a different search or create a new transfer." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Transfer #', 'Date', 'Product', 'Qty', 'Route', 'Requested By', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((t) => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-gray-700">{t.id}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(t.date)}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{t.productName}</p>
                      <p className="text-xs text-gray-400">{t.productSku}</p>
                    </td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{t.quantity} <span className="text-gray-400 font-normal">{t.unit}</span></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-xs text-gray-700">
                        <span className="bg-gray-100 px-2 py-0.5 rounded">{t.fromWarehouseName}</span>
                        <ArrowRight className="w-3 h-3 text-gray-400 shrink-0" />
                        <span className="bg-gray-100 px-2 py-0.5 rounded">{t.toWarehouseName}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{t.requestedBy}</td>
                    <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                    <td className="px-4 py-3">
                      <button onClick={() => navigate(`/transfers/${t.id}`)} className="text-blue-600 hover:underline text-xs font-medium">View</button>
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
