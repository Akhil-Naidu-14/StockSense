import PageHeader from '../components/ui/PageHeader'
import { mockWarehouses } from '../data/mockData'
import { Warehouse, Users, MapPin } from 'lucide-react'

export default function Warehouses() {
  return (
    <div>
      <PageHeader
        title="Warehouses"
        subtitle={`${mockWarehouses.length} active locations`}
        action={{ label: 'Add Warehouse', onClick: () => {} }}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {mockWarehouses.map((w) => {
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
