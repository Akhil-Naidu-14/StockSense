import { useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import { TypeBadge } from '../components/ui/TypeBadge'
import EmptyState from '../components/ui/EmptyState'
import { mockProducts, getStockLedger, formatDate } from '../data/mockData'

// Default to Steel Rods (P001) to showcase the demo workflow
const DEFAULT_PRODUCT = 'P001'

export default function StockLedger() {
  const [productId, setProductId] = useState(DEFAULT_PRODUCT)
  const [warehouseFilter, setWarehouseFilter] = useState('All')

  const ledger = getStockLedger(productId)
  const selectedProduct = mockProducts.find((p) => p.id === productId)

  const warehouses = ['All', ...new Set(ledger.map((e) => e.warehouseName))]

  const filtered = warehouseFilter === 'All'
    ? ledger
    : ledger.filter((e) => e.warehouseName === warehouseFilter)

  return (
    <div>
      <PageHeader
        title="Stock Ledger"
        subtitle="Running balance ledger – shows every stock movement with cumulative balance"
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <select
          value={productId}
          onChange={(e) => { setProductId(e.target.value); setWarehouseFilter('All') }}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {mockProducts.map((p) => (
            <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
          ))}
        </select>
        <select
          value={warehouseFilter}
          onChange={(e) => setWarehouseFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {warehouses.map((w) => <option key={w}>{w === 'All' ? 'All Warehouses' : w}</option>)}
        </select>
      </div>

      {/* Product Summary */}
      {selectedProduct && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
          {[
            { label: 'Current Stock', value: `${selectedProduct.totalStock} ${selectedProduct.unit}`, color: 'text-gray-900' },
            { label: 'Reorder Point', value: `${selectedProduct.reorderPoint} ${selectedProduct.unit}`, color: 'text-yellow-700' },
            { label: 'Min Stock', value: `${selectedProduct.minStock} ${selectedProduct.unit}`, color: 'text-red-700' },
            { label: 'Max Stock', value: `${selectedProduct.maxStock} ${selectedProduct.unit}`, color: 'text-blue-700' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className={`text-lg font-bold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Steel Rods demo callout */}
      {productId === 'P001' && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800">
          <strong>📋 Demo Workflow – Steel Rods:</strong> Received 100 kg → Transferred to Production Rack → Delivered 20 kg → Adjusted to 77 kg (damage write-off)
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState title="No ledger entries" description="No ledger data available for this product/warehouse combination." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Date', 'Time', 'Transaction Type', 'Reference', 'Warehouse', 'Stock In', 'Stock Out', 'Balance', 'Performed By', 'Notes'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((entry, idx) => (
                  <tr key={entry.id} className={`hover:bg-gray-50 ${idx === filtered.length - 1 ? 'bg-blue-50' : ''}`}>
                    <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{formatDate(entry.date)}</td>
                    <td className="px-4 py-3 text-gray-500">{entry.time}</td>
                    <td className="px-4 py-3"><TypeBadge type={entry.transactionType} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{entry.referenceId}</td>
                    <td className="px-4 py-3 text-gray-700">{entry.warehouseName}</td>
                    <td className="px-4 py-3">
                      {entry.inQty > 0
                        ? <span className="font-semibold text-green-600">+{entry.inQty} {selectedProduct?.unit}</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      {entry.outQty > 0
                        ? <span className="font-semibold text-red-600">-{entry.outQty} {selectedProduct?.unit}</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-bold text-gray-900 text-base">{entry.balance}</span>
                      <span className="text-gray-400 text-xs ml-1">{selectedProduct?.unit}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{entry.performedBy}</td>
                    <td className="px-4 py-3 text-gray-500 max-w-xs truncate" title={entry.notes}>{entry.notes}</td>
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
