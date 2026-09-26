import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import { mockProducts, mockWarehouses } from '../../data/mockData'

const REASONS = ['Damage', 'Recount', 'Expiry', 'Theft', 'Return', 'Other']

export default function CreateAdjustment() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    productId: '', warehouseId: '', newQty: '', reason: '',
    description: '', date: new Date().toISOString().split('T')[0],
  })
  const [saved, setSaved] = useState(false)
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const selectedProduct = mockProducts.find((p) => p.id === form.productId)

  const handleSubmit = (e) => {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => navigate('/adjustments'), 1200)
  }

  if (saved) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-3xl">✓</div>
        <h3 className="text-lg font-semibold text-gray-900">Adjustment created!</h3>
        <p className="text-sm text-gray-500">Redirecting to adjustments…</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      <PageHeader title="Create Adjustment" backTo="/adjustments" />
      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-5">

        {/* Warning banner */}
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800 font-medium">⚠️ Adjustments directly modify stock levels. Use with caution.</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Product *</label>
            <select required value={form.productId} onChange={set('productId')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select product</option>
              {mockProducts.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Warehouse *</label>
            <select required value={form.warehouseId} onChange={set('warehouseId')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select warehouse</option>
              {mockWarehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
          </div>
        </div>

        {/* Current stock display */}
        {selectedProduct && (
          <div className="flex items-center gap-4 p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm">
            <span className="text-blue-700 font-medium">Current total stock:</span>
            <span className="font-bold text-blue-900">{selectedProduct.totalStock} {selectedProduct.unit}</span>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Quantity *</label>
            <input required type="number" min="0" value={form.newQty} onChange={set('newQty')}
              placeholder="e.g. 77"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason *</label>
            <select required value={form.reason} onChange={set('reason')}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="">Select reason</option>
              {REASONS.map((r) => <option key={r}>{r}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
          <input required type="date" value={form.date} onChange={set('date')}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea rows={3} value={form.description} onChange={set('description')}
            placeholder="Explain the reason for this adjustment in detail…"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
        </div>

        <div className="flex gap-3 pt-2">
          <button type="submit" className="px-6 py-2.5 bg-yellow-500 text-white text-sm font-semibold rounded-lg hover:bg-yellow-600">Create Adjustment</button>
          <button type="button" onClick={() => navigate('/adjustments')} className="px-6 py-2.5 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50">Cancel</button>
        </div>
      </form>
    </div>
  )
}
