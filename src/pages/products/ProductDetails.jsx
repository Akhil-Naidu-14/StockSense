import { useParams } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import StockBadge from '../../components/ui/StockBadge'
import { TypeBadge } from '../../components/ui/TypeBadge'
import EmptyState from '../../components/ui/EmptyState'
import {
  getProductById, mockMoveHistory, formatCurrency, formatDate,
} from '../../data/mockData'

export default function ProductDetails() {
  const { id } = useParams()
  const product = getProductById(id)

  if (!product) {
    return (
      <div>
        <PageHeader title="Product Not Found" backTo="/products" />
        <EmptyState title="Product not found" description="This product does not exist." />
      </div>
    )
  }

  const movements = mockMoveHistory.filter((m) => m.productId === id).slice(0, 8)

  return (
    <div className="space-y-6">
      <PageHeader title={product.name} subtitle={product.sku} backTo="/products" />

      {/* Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Product Info */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Product Information</h3>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {[
              ['SKU', product.sku],
              ['Category', product.category],
              ['Unit', product.unit],
              ['Supplier', product.supplier],
              ['Cost Price', formatCurrency(product.costPrice)],
              ['Selling Price', formatCurrency(product.sellingPrice)],
              ['Min Stock', `${product.minStock} ${product.unit}`],
              ['Max Stock', `${product.maxStock} ${product.unit}`],
              ['Reorder Point', `${product.reorderPoint} ${product.unit}`],
              ['Created', formatDate(product.createdAt)],
              ['Last Updated', formatDate(product.updatedAt)],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
          {product.description && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-gray-500 text-sm">{product.description}</p>
            </div>
          )}
        </div>

        {/* Stock Summary */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Stock Summary</h3>
            <StockBadge product={product} />
          </div>
          <div className="text-center mb-4">
            <p className="text-4xl font-bold text-gray-900">{product.totalStock}</p>
            <p className="text-sm text-gray-500 mt-1">{product.unit} total</p>
          </div>

          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>0</span>
              <span>Max: {product.maxStock}</span>
            </div>
            <div className="w-full h-2 bg-gray-100 rounded-full">
              <div
                className="h-2 rounded-full bg-blue-500"
                style={{ width: `${Math.min((product.totalStock / product.maxStock) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* By warehouse */}
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">By Warehouse</h4>
          <div className="space-y-2">
            {product.stockByWarehouse.map((w) => (
              <div key={w.warehouseId} className="flex items-center justify-between text-sm">
                <span className="text-gray-700">{w.warehouseName}</span>
                <span className="font-semibold text-gray-900">{w.quantity} {product.unit}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Movements */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800">Recent Movements</h3>
        </div>
        {movements.length === 0 ? (
          <EmptyState title="No movements yet" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Date', 'Type', 'Reference', 'From', 'To', 'Qty', 'By'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {movements.map((m) => (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(m.date)}</td>
                    <td className="px-4 py-3"><TypeBadge type={m.type} /></td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{m.referenceId}</td>
                    <td className="px-4 py-3 text-gray-700">{m.fromLocation}</td>
                    <td className="px-4 py-3 text-gray-700">{m.toLocation}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{Math.abs(m.quantity)} {m.unit}</td>
                    <td className="px-4 py-3 text-gray-600">{m.performedBy}</td>
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
