// StatusBadge – for receipt/delivery/transfer/adjustment status
const STATUS_STYLES = {
  completed: 'bg-green-100 text-green-700',
  active:    'bg-green-100 text-green-700',
  pending:   'bg-yellow-100 text-yellow-700',
  cancelled: 'bg-red-100 text-red-700',
  failed:    'bg-red-100 text-red-700',
  in_transit:'bg-blue-100 text-blue-700',
  processing:'bg-blue-100 text-blue-700',
}

const STATUS_LABELS = {
  completed:  'Completed',
  active:     'Active',
  pending:    'Pending',
  cancelled:  'Cancelled',
  failed:     'Failed',
  in_transit: 'In Transit',
  processing: 'Processing',
}

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || 'bg-gray-100 text-gray-600'
  const label = STATUS_LABELS[status] || status
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}>
      {label}
    </span>
  )
}
