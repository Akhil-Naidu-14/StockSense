// Type badge for move history / ledger transaction types
const TYPE_STYLES = {
  Receipt:     'bg-green-100 text-green-700',
  Delivery:    'bg-red-100 text-red-700',
  Transfer:    'bg-blue-100 text-blue-700',
  'Transfer In':  'bg-blue-100 text-blue-700',
  'Transfer Out': 'bg-purple-100 text-purple-700',
  Adjustment:  'bg-yellow-100 text-yellow-700',
}

export function TypeBadge({ type }) {
  const style = TYPE_STYLES[type] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style}`}>
      {type}
    </span>
  )
}

export default TypeBadge
