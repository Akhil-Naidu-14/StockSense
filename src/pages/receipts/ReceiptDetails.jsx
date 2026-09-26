import { useParams } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { getReceiptById, formatDate, formatCurrency } from '../../data/mockData'

export default function ReceiptDetails() {
  const { id } = useParams()
  const receipt = getReceiptById(id)

  if (!receipt) {
    return (
      <div>
        <PageHeader title="Receipt Not Found" backTo="/receipts" />
        <EmptyState title="Receipt not found" description="This receipt does not exist." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={receipt.id}
        subtitle={`Created ${formatDate(receipt.createdAt)}`}
        backTo="/receipts"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main details */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Receipt Details</h3>
            <StatusBadge status={receipt.status} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {[
              ['Product', `${receipt.productName} (${receipt.productSku})`],
              ['Supplier', receipt.supplier],
              ['Invoice No', receipt.invoiceNo],
              ['Date', formatDate(receipt.date)],
              ['Warehouse', receipt.warehouseName],
              ['Received By', receipt.receivedBy || '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
          {receipt.notes && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</p>
              <p className="text-sm text-gray-700">{receipt.notes}</p>
            </div>
          )}
        </div>

        {/* Financial summary */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Financial Summary</h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Quantity</span>
              <span className="font-medium text-gray-900">{receipt.quantity} {receipt.unit}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Cost / Unit</span>
              <span className="font-medium text-gray-900">{formatCurrency(receipt.costPerUnit)}</span>
            </div>
            <div className="flex justify-between border-t border-gray-100 pt-3">
              <span className="font-semibold text-gray-800">Total Cost</span>
              <span className="font-bold text-gray-900 text-base">{formatCurrency(receipt.totalCost)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
