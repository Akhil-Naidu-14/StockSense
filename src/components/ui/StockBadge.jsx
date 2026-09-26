// StockBadge – shows stock level relative to reorder/min/max
import { getStockStatus } from '../../data/mockData'

const STOCK_STYLES = {
  ok:   'bg-green-100 text-green-700',
  low:  'bg-yellow-100 text-yellow-700',
  out:  'bg-red-100 text-red-700',
  over: 'bg-blue-100 text-blue-700',
}

const STOCK_LABELS = {
  ok:   'In Stock',
  low:  'Low Stock',
  out:  'Out of Stock',
  over: 'Overstocked',
}

export default function StockBadge({ product }) {
  const status = getStockStatus(product)
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STOCK_STYLES[status]}`}>
      {STOCK_LABELS[status]}
    </span>
  )
}
