import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Package, Warehouse, PackagePlus, Truck,
  ArrowLeftRight, SlidersHorizontal, History, BookOpen, User,
  LogOut, Boxes, ChevronLeft, ChevronRight,
} from 'lucide-react'

const NAV_GROUPS = [
  {
    label: 'Overview',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    ],
  },
  {
    label: 'Inventory',
    items: [
      { to: '/products', icon: Package, label: 'Products' },
      { to: '/warehouses', icon: Warehouse, label: 'Warehouses' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/receipts', icon: PackagePlus, label: 'Receipts' },
      { to: '/deliveries', icon: Truck, label: 'Deliveries' },
      { to: '/transfers', icon: ArrowLeftRight, label: 'Transfers' },
      { to: '/adjustments', icon: SlidersHorizontal, label: 'Adjustments' },
    ],
  },
  {
    label: 'Reports',
    items: [
      { to: '/move-history', icon: History, label: 'Move History' },
      { to: '/stock-ledger', icon: BookOpen, label: 'Stock Ledger' },
    ],
  },
  {
    label: 'Account',
    items: [
      { to: '/profile', icon: User, label: 'Profile' },
    ],
  },
]

export default function Sidebar({ open, setOpen }) {
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('stocksense_auth')
    navigate('/login')
  }

  return (
    <aside
      className={`
        flex flex-col bg-slate-900 text-white h-screen shrink-0
        transition-all duration-200
        ${open ? 'w-60' : 'w-16'}
      `}
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-4 border-b border-slate-700 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Boxes className="w-7 h-7 text-blue-400 shrink-0" />
          {open && (
            <span className="font-bold text-lg tracking-tight truncate">
              StockSense
            </span>
          )}
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="ml-auto p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white shrink-0"
          aria-label="Toggle sidebar"
        >
          {open ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto scrollbar-hide py-3 space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {open && (
              <p className="px-4 mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                {group.label}
              </p>
            )}
            {group.items.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 mx-2 px-3 py-2 rounded-lg text-sm font-medium
                  ${isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <Icon className="w-5 h-5 shrink-0" />
                {open && <span className="truncate">{label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Logout */}
      <div className="shrink-0 border-t border-slate-700 p-3">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <LogOut className="w-5 h-5 shrink-0" />
          {open && <span>Logout</span>}
        </button>
      </div>
    </aside>
  )
}
