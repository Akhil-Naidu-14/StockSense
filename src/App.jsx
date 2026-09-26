import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Login from './pages/auth/Login'
import Signup from './pages/auth/Signup'
import ForgotPassword from './pages/auth/ForgotPassword'
import VerifyOTP from './pages/auth/VerifyOTP'
import ResetPassword from './pages/auth/ResetPassword'
import Dashboard from './pages/Dashboard'
import Products from './pages/products/Products'
import CreateProduct from './pages/products/CreateProduct'
import ProductDetails from './pages/products/ProductDetails'
import Receipts from './pages/receipts/Receipts'
import CreateReceipt from './pages/receipts/CreateReceipt'
import ReceiptDetails from './pages/receipts/ReceiptDetails'
import Deliveries from './pages/deliveries/Deliveries'
import CreateDelivery from './pages/deliveries/CreateDelivery'
import DeliveryDetails from './pages/deliveries/DeliveryDetails'
import Transfers from './pages/transfers/Transfers'
import CreateTransfer from './pages/transfers/CreateTransfer'
import TransferDetails from './pages/transfers/TransferDetails'
import Adjustments from './pages/adjustments/Adjustments'
import CreateAdjustment from './pages/adjustments/CreateAdjustment'
import MoveHistory from './pages/MoveHistory'
import StockLedger from './pages/StockLedger'
import Warehouses from './pages/Warehouses'
import CreateWarehouse from './pages/warehouses/CreateWarehouse'
import Profile from './pages/Profile'
import { getToken } from './services/api'

// ── Guard: redirects to /login if no JWT is stored ──────────
function PrivateRoute({ children }) {
  const token = getToken()
  return token ? children : <Navigate to="/login" replace />
}

// ── Guard: redirects authenticated users away from auth pages
function PublicRoute({ children }) {
  const token = getToken()
  return token ? <Navigate to="/dashboard" replace /> : children
}

export default function App() {
  return (
    <Routes>
      {/* ── Public / Auth pages ── */}
      <Route path="/login"           element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/signup"          element={<PublicRoute><Signup /></PublicRoute>} />
      <Route path="/forgot-password" element={<PublicRoute><ForgotPassword /></PublicRoute>} />
      <Route path="/verify-otp"      element={<PublicRoute><VerifyOTP /></PublicRoute>} />
      <Route path="/reset-password"  element={<PublicRoute><ResetPassword /></PublicRoute>} />

      {/* ── Private / App pages ── */}
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard"          element={<Dashboard />} />
        <Route path="products"           element={<Products />} />
        <Route path="products/create"    element={<CreateProduct />} />
        <Route path="products/:id"       element={<ProductDetails />} />
        <Route path="receipts"           element={<Receipts />} />
        <Route path="receipts/create"    element={<CreateReceipt />} />
        <Route path="receipts/:id"       element={<ReceiptDetails />} />
        <Route path="deliveries"         element={<Deliveries />} />
        <Route path="deliveries/create"  element={<CreateDelivery />} />
        <Route path="deliveries/:id"     element={<DeliveryDetails />} />
        <Route path="transfers"          element={<Transfers />} />
        <Route path="transfers/create"   element={<CreateTransfer />} />
        <Route path="transfers/:id"      element={<TransferDetails />} />
        <Route path="adjustments"        element={<Adjustments />} />
        <Route path="adjustments/create" element={<CreateAdjustment />} />
        <Route path="move-history"       element={<MoveHistory />} />
        <Route path="stock-ledger"       element={<StockLedger />} />
        <Route path="warehouses"         element={<Warehouses />} />
        <Route path="warehouses/create"  element={<CreateWarehouse />} />
        <Route path="profile"            element={<Profile />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
