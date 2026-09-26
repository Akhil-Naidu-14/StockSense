import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import SearchBar from '../../components/ui/SearchBar'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { mockReceipts, formatDate, formatCurrency } from '../../data/mockData'

const STATUSES = ['All', 'completed', 'pending', 'cancelled']

export default function Receipts() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')

  const filtered = mockReceipts.filter((r) => {
    const matchSearch =
      r.id.toLowerCase().includes(search.toLowerCase()) ||
      r.productName.toLowerCase().includes(search.toLowerCase()) ||
      r.supplier.toLowerCase().includes(search.toLowerCase())
    const matchStatus = status === 'All' || r.status === status
    return matchSearch && matchStatus
  })

  return (
    <div>
      <PageHeader
        title="Receipts"
        subtitle={`${mockReceipts.length} total receipts`}
        action={{ label: 'Create Receipt', onClick: () => navigate('/receipts/create') }}
      />

      <div className="flex flex-wrap gap-3 mb-4">
        <SearchBar value={search} onChange={setSearch} placeholder="Search receipts…" className="w-full sm:w-64" />
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {STATUSES.map((s) => <option key={s}>{s === 'All' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState title="No receipts found" description="Try a different search or create a new receipt." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Receipt #', 'Date', 'Product', 'Qty', 'Warehouse', 'Supplier', 'Total Cost', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-gray-700">{r.id}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(r.date)}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{r.productName}</p>
                      <p className="text-xs text-gray-400">{r.productSku}</p>
                    </td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{r.quantity} <span className="text-gray-400 font-normal">{r.unit}</span></td>
                    <td className="px-4 py-3 text-gray-600">{r.warehouseName}</td>
                    <td className="px-4 py-3 text-gray-600">{r.supplier}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{formatCurrency(r.totalCost)}</td>
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3">
                      <button onClick={() => navigate(`/receipts/${r.id}`)} className="text-blue-600 hover:underline text-xs font-medium">View</button>
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
