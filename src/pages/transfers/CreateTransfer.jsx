import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import { mockProducts, mockWarehouses } from '../../data/mockData'

export default function CreateTransfer() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    productId: '', fromWarehouseId: '', toWarehouseId: '',
    quantity: '', reason: '', notes: '',
    date: new Date().toISOString().split('T')[0],
  })
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (form.fromWarehouseId === form.toWarehouseId) {
      setError('Source and destination warehouses must be different.')
      return
    }
    setError('')
    setSaved(true)
    setTimeout(() => navigate('/transfers'), 1200)
  }

  if (saved) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-3xl">✓</div>
        <h3 className="text-lg font-semibold text-gray-900">Transfer created!</h3>
        <p className="text-sm text-gray-500">Redirecting to transfers…</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <PageHeader title="Create Transfer" backTo="/transfers" />
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Product *</label>
          <select required value={form.productId} onChange={set('productId')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">Select product</option>
            {mockProducts.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku}) – {p.totalStock} {p.unit} available</option>)}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Warehouse *</label>
            <select required value={form.fromWarehouseId} onChange={set('fromWarehouseId')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select source</option>
              {mockWarehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Warehouse *</label>
            <select required value={form.toWarehouseId} onChange={set('toWarehouseId')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select destination</option>
              {mockWarehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Quantity *</label>
            <input required type="number" min="1" value={form.quantity} onChange={set('quantity')} placeholder="e.g. 100"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
            <input required type="date" value={form.date} onChange={set('date')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
          <input type="text" value={form.reason} onChange={set('reason')} placeholder="Reason for transfer"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea rows={3} value={form.notes} onChange={set('notes')} placeholder="Optional notes…"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>

        {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700">Create Transfer</button>
          <button type="button" onClick={() => navigate('/transfers')} className="px-6 py-2.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">Cancel</button>
        </div>
      </form>
    </div>
  )
}
