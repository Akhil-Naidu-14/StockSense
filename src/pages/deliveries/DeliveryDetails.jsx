import { useParams } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import StatusBadge from '../../components/ui/StatusBadge'
import EmptyState from '../../components/ui/EmptyState'
import { getDeliveryById, formatDate } from '../../data/mockData'

export default function DeliveryDetails() {
  const { id } = useParams()
  const delivery = getDeliveryById(id)

  if (!delivery) {
    return (
      <div>
        <PageHeader title="Delivery Not Found" backTo="/deliveries" />
        <EmptyState title="Delivery not found" description="This delivery does not exist." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title={delivery.id} subtitle={`Created ${formatDate(delivery.createdAt)}`} backTo="/deliveries" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-800">Delivery Details</h3>
            <StatusBadge status={delivery.status} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {[
              ['Product', `${delivery.productName} (${delivery.productSku})`],
              ['Quantity', `${delivery.quantity} ${delivery.unit}`],
              ['Source Warehouse', delivery.warehouseName],
              ['Date', formatDate(delivery.date)],
              ['Delivered By', delivery.deliveredBy || '—'],
              ['Delivered At', delivery.deliveredAt ? formatDate(delivery.deliveredAt) : '—'],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Customer Information</h3>
          <dl className="space-y-3 text-sm">
            {[
              ['Customer', delivery.customer],
              ['Order No', delivery.orderNo],
              ['Delivery Address', delivery.deliveryAddress],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900 mt-0.5">{value}</dd>
              </div>
            ))}
          </dl>
          {delivery.notes && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Notes</p>
              <p className="text-sm text-gray-700">{delivery.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
