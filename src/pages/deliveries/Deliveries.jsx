import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import SearchBar from '../../components/ui/SearchBar'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { mockDeliveries, formatDate } from '../../data/mockData'

const STATUSES = ['All', 'completed', 'pending', 'cancelled']

export default function Deliveries() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('All')

  const filtered = mockDeliveries.filter((d) => {
    const matchSearch =
      d.id.toLowerCase().includes(search.toLowerCase()) ||
      d.productName.toLowerCase().includes(search.toLowerCase()) ||
      d.customer.toLowerCase().includes(search.toLowerCase())
    const matchStatus = status === 'All' || d.status === status
    return matchSearch && matchStatus
  })

  return (
    <div>
      <PageHeader
        title="Deliveries"
        subtitle={`${mockDeliveries.length} total deliveries`}
        action={{ label: 'Create Delivery', onClick: () => navigate('/deliveries/create') }}
      />

      <div className="flex flex-wrap gap-3 mb-4">
        <SearchBar value={search} onChange={setSearch} placeholder="Search deliveries…" className="w-full sm:w-64" />
        <select
          value={status} onChange={(e) => setStatus(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
          {STATUSES.map((s) => <option key={s}>{s === 'All' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState title="No deliveries found" description="Try a different search or create a new delivery." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Delivery #', 'Date', 'Product', 'Qty', 'From Warehouse', 'Customer', 'Order No', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((d) => (
                  <tr key={d.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-gray-700">{d.id}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(d.date)}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900">{d.productName}</p>
                      <p className="text-xs text-gray-400">{d.productSku}</p>
                    </td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{d.quantity} <span className="text-gray-400 font-normal">{d.unit}</span></td>
                    <td className="px-4 py-3 text-gray-600">{d.warehouseName}</td>
                    <td className="px-4 py-3 text-gray-700">{d.customer}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{d.orderNo}</td>
                    <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                    <td className="px-4 py-3">
                      <button onClick={() => navigate(`/deliveries/${d.id}`)} className="text-blue-600 hover:underline text-xs font-medium">View</button>
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
