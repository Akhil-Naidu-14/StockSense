// ============================================================
//  src/services/productService.js
//  Product API service layer connected to FastAPI backend.
// ============================================================
import api from './api'

// GET /api/products
export async function getProducts(params = {}) {
  const { data } = await api.get('/products', { params })
  return data
}

// POST /api/products
// Schema: ProductCreate { name, sku, category_id?, unit_of_measure?, reorder_level?, reorder_quantity? }
export async function createProduct(productData) {
  const { data } = await api.post('/products', productData)
  return data
}

// GET /api/categories
export async function getCategories(params = {}) {
  const { data } = await api.get('/categories', { params })
  return data
}
