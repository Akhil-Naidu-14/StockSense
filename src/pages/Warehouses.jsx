import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import { mockWarehouses } from '../data/mockData'
import { Warehouse, Users, MapPin } from 'lucide-react'
import { getWarehouses } from '../services/warehouseService'

export default function Warehouses() {
  const navigate = useNavigate()
  const location = useLocation()
  const [backendWarehouses, setBackendWarehouses] = useState([])
  const [infoMsg, setInfoMsg] = useState(location.state?.message || '')

  // Fetch warehouse list from backend API
  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const data = await getWarehouses()
        if (active && Array.isArray(data)) {
          setBackendWarehouses(data)
        }
      } catch {
        // Quiet fallback to mock warehouses if endpoint errors or returns empty
      }
    })()
    return () => { active = false }
  }, [location.state])

  // Combine backend warehouses with mock data (avoiding duplicate codes)
  const backendCodes = new Set(backendWarehouses.map((bw) => bw.code.toUpperCase()))
  const mockFiltered = mockWarehouses.filter((mw) => !backendCodes.has(mw.code.toUpperCase()))

  const formattedBackendWarehouses = backendWarehouses.map((bw) => ({
    id: String(bw.id),
    name: bw.name,
    code: bw.code,
    location: bw.address || 'Location Not Specified',
    capacity: 5000,
    unit: 'kg',
    usedCapacity: 0,
    manager: bw.manager_name || 'Unassigned',
    status: bw.is_active ? 'active' : 'inactive',
    productCount: 0,
  }))

  const allWarehouses = [...formattedBackendWarehouses, ...mockFiltered]

  return (
    <div>
      <PageHeader
        title="Warehouses"
        subtitle={`${allWarehouses.length} active locations`}
        action={{ label: 'Add Warehouse', onClick: () => navigate('/warehouses/create') }}
      />

      {infoMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium flex justify-between items-center">
          <span>✓ {infoMsg}</span>
          <button onClick={() => setInfoMsg('')} className="text-green-700 hover:text-green-900 text-xs">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {allWarehouses.map((w) => {
          const pct = Math.round((w.usedCapacity / w.capacity) * 100)
          const barColor = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-400' : 'bg-blue-500'

          return (
            <div key={w.id} className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">
                    <Warehouse className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{w.name}</h3>
                    <p className="text-xs font-mono text-gray-400">{w.code}</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                  {w.status}
                </span>
              </div>

              {/* Details */}
              <div className="space-y-2 mb-4 text-sm">
                <div className="flex items-center gap-2 text-gray-600">
                  <MapPin className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="truncate">{w.location}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-600">
                  <Users className="w-4 h-4 text-gray-400 shrink-0" />
                  <span>{w.manager}</span>
                </div>
              </div>

              {/* Capacity */}
              <div className="mb-2">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-500">Capacity used</span>
                  <span className="font-semibold text-gray-700">{pct}%</span>
                </div>
                <div className="w-full h-2 bg-gray-100 rounded-full">
                  <div className={`h-2 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
                </div>
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>{w.usedCapacity.toLocaleString()} {w.unit} used</span>
                  <span>{w.capacity.toLocaleString()} {w.unit} total</span>
                </div>
              </div>

              {/* Footer */}
              <div className="pt-3 border-t border-gray-100 flex items-center justify-between text-sm">
                <span className="text-gray-500">Products stored</span>
                <span className="font-semibold text-gray-900">{w.productCount}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
