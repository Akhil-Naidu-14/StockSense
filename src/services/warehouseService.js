// ============================================================
//  src/services/warehouseService.js
//  Warehouse API service layer connected to FastAPI backend.
// ============================================================
import api from './api'

// GET /api/warehouses
export async function getWarehouses(params = {}) {
  const { data } = await api.get('/warehouses', { params })
  return data
}

// POST /api/warehouses
// Schema: WarehouseCreate { name, code, address?, manager_id? }
export async function createWarehouse(warehouseData) {
  const { data } = await api.post('/warehouses', warehouseData)
  return data
}
