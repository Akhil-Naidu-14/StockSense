import { useParams } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { getTransferById, formatDate } from '../../data/mockData'

export default function TransferDetails() {
  const { id } = useParams()
  const transfer = getTransferById(id)

  if (!transfer) {
    return (
      <div>
        <PageHeader title="Transfer Not Found" backTo="/transfers" />
        <EmptyState title="Transfer not found" description="This transfer does not exist." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title={transfer.id} subtitle={`Created ${formatDate(transfer.createdAt)}`} backTo="/transfers" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Transfer Details</h3>
            <StatusBadge status={transfer.status} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {[
              ['Product', `${transfer.productName} (${transfer.productSku})`],
              ['Quantity', `${transfer.quantity} ${transfer.unit}`],
              ['Date', formatDate(transfer.date)],
              ['Requested By', transfer.requestedBy],
              ['Approved By', transfer.approvedBy || '—'],
              ['Completed At', transfer.completedAt ? formatDate(transfer.completedAt) : '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Transfer Route</h3>
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="w-full p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <p className="text-xs text-gray-500 mb-1">FROM</p>
              <p className="font-semibold text-gray-900">{transfer.fromWarehouseName}</p>
            </div>
            <div className="flex items-center gap-2 text-blue-500">
              <div className="flex-1 h-px bg-blue-200" />
              <ArrowRight className="w-5 h-5" />
              <div className="flex-1 h-px bg-blue-200" />
            </div>
            <div className="w-full p-3 bg-blue-50 rounded-lg border border-blue-200 text-center">
              <p className="text-xs text-blue-500 mb-1">TO</p>
              <p className="font-semibold text-blue-900">{transfer.toWarehouseName}</p>
            </div>
          </div>

          {transfer.reason && (
            <div className="mt-2 pt-4 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Reason</p>
              <p className="text-sm text-gray-700">{transfer.reason}</p>
            </div>
          )}
          {transfer.notes && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</p>
              <p className="text-sm text-gray-700">{transfer.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
