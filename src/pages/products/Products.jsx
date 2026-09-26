import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import PageHeader from '../../components/ui/PageHeader'
import SearchBar from '../../components/ui/SearchBar'
import StockBadge from '../../components/ui/StockBadge'
import EmptyState from '../../components/ui/EmptyState'
import { mockProducts, formatDate } from '../../data/mockData'
import { getProducts } from '../../services/productService'

const CATEGORIES = ['All', 'Raw Materials', 'Electrical', 'Plumbing', 'Fasteners']

export default function Products() {
  const navigate = useNavigate()
  const location = useLocation()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [backendProducts, setBackendProducts] = useState([])
  const [infoMsg, setInfoMsg] = useState(location.state?.message || '')

  // Fetch product list from backend API
  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const data = await getProducts()
        if (active && Array.isArray(data)) {
          setBackendProducts(data)
        }
      } catch {
        // Quiet fallback to mock products if endpoint errors or returns empty
      }
    })()
    return () => { active = false }
  }, [location.state])

  // Combine backend products with mock data (avoiding duplicate SKUs)
  const backendSkus = new Set(backendProducts.map((bp) => bp.sku.toUpperCase()))
  const mockFiltered = mockProducts.filter((mp) => !backendSkus.has(mp.sku.toUpperCase()))

  const formattedBackendProducts = backendProducts.map((bp) => ({
    id: String(bp.id),
    sku: bp.sku,
    name: bp.name,
    category: bp.category_name || (bp.category_id ? `Category #${bp.category_id}` : 'General'),
    unit: bp.unit_of_measure || 'pcs',
    totalStock: 0,
    reorderPoint: Number(bp.reorder_level || 0),
    maxStock: 500,
    minStock: 10,
    status: bp.is_active ? 'active' : 'inactive',
    updatedAt: bp.updated_at || bp.created_at || new Date().toISOString(),
  }))

  const allProducts = [...formattedBackendProducts, ...mockFiltered]

  const filtered = allProducts.filter((p) => {
    const matchSearch =
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.sku.toLowerCase().includes(search.toLowerCase())
    const matchCat = category === 'All' || p.category === category
    return matchSearch && matchCat
  })

  return (
    <div>
      <PageHeader
        title="Products"
        subtitle={`${allProducts.length} total products`}
        action={{ label: 'Add Product', onClick: () => navigate('/products/create') }}
      />

      {infoMsg && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 font-medium flex justify-between items-center">
          <span>✓ {infoMsg}</span>
          <button onClick={() => setInfoMsg('')} className="text-green-700 hover:text-green-900 text-xs">✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search by name or SKU…"
          className="w-full sm:w-64"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {CATEGORIES.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState title="No products found" description="Try a different search or filter." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['SKU', 'Name', 'Category', 'Total Stock', 'Reorder Point', 'Stock Status', 'Updated', 'Actions'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{p.sku}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                    <td className="px-4 py-3 text-gray-600">{p.category}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">
                      {p.totalStock} <span className="text-gray-400 font-normal">{p.unit}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{p.reorderPoint} {p.unit}</td>
                    <td className="px-4 py-3"><StockBadge product={p} /></td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{formatDate(p.updatedAt)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/products/${p.id}`)}
                        className="text-blue-600 hover:underline text-xs font-medium"
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
