import { useNavigate } from 'react-router-dom'
import {
  Package, Warehouse, PackagePlus, Truck,
  ArrowLeftRight, SlidersHorizontal, TrendingDown, AlertTriangle,
} from 'lucide-react'
import KPICard from '../components/dashboard/KPICard'
import StatusBadge from '../components/ui/StatusBadge'
import {
  mockDashboardStats, mockMoveHistory, mockProducts,
  formatCurrency, formatDate,
} from '../data/mockData'

export default function Dashboard() {
  const navigate = useNavigate()
  const recentActivity = mockMoveHistory.slice(0, 6)
  const lowStockProducts = mockProducts.filter(
    (p) => p.totalStock <= p.reorderPoint
  )

  const typeIcon = {
    Receipt:    <PackagePlus className="w-4 h-4 text-green-600" />,
    Delivery:   <Truck className="w-4 h-4 text-red-500" />,
    Transfer:   <ArrowLeftRight className="w-4 h-4 text-blue-600" />,
    Adjustment: <SlidersHorizontal className="w-4 h-4 text-yellow-600" />,
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard
          title="Total Products"
          value={mockDashboardStats.totalProducts}
          subtitle="5 active SKUs"
          icon={Package}
          color="blue"
        />
        <KPICard
          title="Stock Value"
          value={formatCurrency(mockDashboardStats.totalStockValue)}
          subtitle="Across all warehouses"
          icon={Warehouse}
          color="green"
        />
        <KPICard
          title="Low Stock Items"
          value={mockDashboardStats.lowStockItems}
          subtitle="Need reordering"
          icon={AlertTriangle}
          color="yellow"
        />
        <KPICard
          title="Pending Operations"
          value={mockDashboardStats.totalPendingOps}
          subtitle={`${mockDashboardStats.pendingReceipts} receipt · ${mockDashboardStats.pendingTransfers} transfer · ${mockDashboardStats.pendingDeliveries} delivery`}
          icon={TrendingDown}
          color="red"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="xl:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Recent Activity</h3>
            <button
              onClick={() => navigate('/move-history')}
              className="text-xs font-medium text-blue-600 hover:underline"
            >
              View all
            </button>
          </div>
          <div className="divide-y divide-gray-50">
            {recentActivity.map((item) => (
              <div key={item.id} className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50">
                <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center shrink-0">
                  {typeIcon[item.type]}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {item.type} – {item.productName}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {item.fromLocation} → {item.toLocation} · {Math.abs(item.quantity)} {item.unit}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <StatusBadge status={item.status} />
                  <p className="text-xs text-gray-400 mt-0.5">{formatDate(item.date)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Low Stock Alerts */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-gray-800">Stock Alerts</h3>
            <button
              onClick={() => navigate('/products')}
              className="text-xs font-medium text-blue-600 hover:underline"
            >
              View all
            </button>
          </div>
          {lowStockProducts.length === 0 ? (
            <p className="text-sm text-gray-500 px-5 py-8 text-center">All stock levels are healthy.</p>
          ) : (
            <div className="divide-y divide-gray-50">
              {lowStockProducts.map((p) => (
                <div key={p.id} className="px-5 py-4">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-900">{p.name}</p>
                    <span className="text-xs font-semibold text-yellow-600">{p.totalStock} {p.unit}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
                    <span>{p.sku}</span>
                    <span>Reorder @ {p.reorderPoint} {p.unit}</span>
                  </div>
                  {/* Mini progress bar */}
                  <div className="w-full h-1.5 bg-gray-100 rounded-full">
                    <div
                      className="h-1.5 rounded-full bg-yellow-400"
                      style={{ width: `${Math.min((p.totalStock / p.maxStock) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Quick links */}
          <div className="px-5 py-4 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Quick Actions</p>
            <div className="space-y-2">
              {[
                { label: 'Create Receipt', to: '/receipts/create', color: 'text-green-600' },
                { label: 'Create Transfer', to: '/transfers/create', color: 'text-blue-600' },
                { label: 'Create Delivery', to: '/deliveries/create', color: 'text-red-500' },
              ].map(({ label, to, color }) => (
                <button
                  key={to}
                  onClick={() => navigate(to)}
                  className={`block w-full text-left text-sm font-medium ${color} hover:underline`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
