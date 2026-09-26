import { useLocation, useNavigate } from 'react-router-dom'
import { Menu, Bell } from 'lucide-react'
import { getStoredUser } from '../../services/api'

const ROUTE_LABELS = {
  '/dashboard':          'Dashboard',
  '/products':           'Products',
  '/warehouses':         'Warehouses',
  '/receipts':           'Receipts',
  '/receipts/create':    'Create Receipt',
  '/deliveries':         'Deliveries',
  '/deliveries/create':  'Create Delivery',
  '/transfers':          'Transfers',
  '/transfers/create':   'Create Transfer',
  '/adjustments':        'Adjustments',
  '/adjustments/create': 'Create Adjustment',
  '/move-history':       'Move History',
  '/stock-ledger':       'Stock Ledger',
  '/profile':            'Profile',
}

function getPageTitle(pathname) {
  if (ROUTE_LABELS[pathname]) return ROUTE_LABELS[pathname]
  const parts = pathname.split('/')
  const base = '/' + parts[1]
  const segment = parts[2]
  if (base === '/products'   && segment && segment !== 'create') return 'Product Details'
  if (base === '/receipts'   && segment && segment !== 'create') return 'Receipt Details'
  if (base === '/deliveries' && segment && segment !== 'create') return 'Delivery Details'
  if (base === '/transfers'  && segment && segment !== 'create') return 'Transfer Details'
  return 'StockSense'
}

export default function Topbar({ onMenuToggle }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const title = getPageTitle(pathname)

  // Read user from localStorage cache (set during login / GET /auth/me)
  const user = getStoredUser()
  const displayName = user?.name || user?.full_name || user?.email || 'User'
  const displayRole = user?.role || 'Staff'
  const initial = displayName.charAt(0).toUpperCase()

  return (
    <header className="flex items-center h-16 px-6 bg-white border-b border-gray-200 shrink-0 gap-4">
      <button
        onClick={onMenuToggle}
        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 lg:hidden"
        aria-label="Toggle menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      <h1 className="text-lg font-semibold text-gray-900 truncate">{title}</h1>

      <div className="ml-auto flex items-center gap-3">
        {/* Notification bell */}
        <button className="relative p-2 rounded-lg hover:bg-gray-100 text-gray-500">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
        </button>

        {/* User avatar — clicking opens Profile */}
        <button
          onClick={() => navigate('/profile')}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100"
        >
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-semibold shrink-0">
            {initial}
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-sm font-medium text-gray-900 leading-tight truncate max-w-[120px]">
              {displayName}
            </p>
            <p className="text-xs text-gray-500 leading-tight">{displayRole}</p>
          </div>
        </button>
      </div>
    </header>
  )
}
