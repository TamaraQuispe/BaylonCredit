import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import ProtectedRoute from '@/routes/ProtectedRoute'
import LoginPage from '@/pages/LoginPage'
import HomePage from '@/pages/HomePage'
import {
  VentasPage,
  FiadosPage,
  NuevoFiadoPage,
  DetalleFiadoPage,
  ClientesPage,
  NuevoClientePage,
  DetalleClientePage,
  ProductosPage,
  InventarioPage,
  PagosPage,
  NuevoPagoPage,
  EvaluacionCrediticiaPage,
  ReportesPage,
  UsuariosPage,
  ConfiguracionPage,
  PerfilPage,
} from '@/pages/ModulePages'

export default function App() {
  return (
    <Routes>
      <Route path="/iniciar-sesion" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/inicio" element={<HomePage />} />
          <Route path="/ventas" element={<VentasPage />} />
          <Route path="/fiados" element={<FiadosPage />} />
          <Route path="/fiados/nuevo" element={<NuevoFiadoPage />} />
          <Route path="/fiados/:id" element={<DetalleFiadoPage />} />
          <Route path="/clientes" element={<ClientesPage />} />
          <Route path="/clientes/nuevo" element={<NuevoClientePage />} />
          <Route path="/clientes/:id" element={<DetalleClientePage />} />
          <Route path="/productos" element={<ProductosPage />} />
          <Route path="/inventario" element={<InventarioPage />} />
          <Route path="/pagos" element={<PagosPage />} />
          <Route path="/pagos/nuevo" element={<NuevoPagoPage />} />
          <Route path="/evaluacion-crediticia" element={<EvaluacionCrediticiaPage />} />
          <Route path="/reportes" element={<ReportesPage />} />
          <Route path="/usuarios" element={<UsuariosPage />} />
          <Route path="/configuracion" element={<ConfiguracionPage />} />
          <Route path="/perfil" element={<PerfilPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/inicio" replace />} />
      <Route path="*" element={<Navigate to="/inicio" replace />} />
    </Routes>
  )
}
