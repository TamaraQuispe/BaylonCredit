import ModulePlaceholder from '@/components/common/ModulePlaceholder'

interface ModuleProps {
  title: string
  icon: string
}

function Module({ title, icon }: ModuleProps) {
  return <ModulePlaceholder title={title} icon={icon} />
}

export function FiadosPage() {
  return <Module title="Fiados" icon="receipt_long" />
}

export function NuevoFiadoPage() {
  return <Module title="Registrar Fiado" icon="receipt_long" />
}

export function DetalleFiadoPage() {
  return <Module title="Detalle del Fiado" icon="receipt_long" />
}

export function ClientesPage() {
  return <Module title="Clientes" icon="group" />
}

export function NuevoClientePage() {
  return <Module title="Registrar Cliente" icon="group" />
}

export function DetalleClientePage() {
  return <Module title="Perfil del Cliente" icon="group" />
}

export function ProductosPage() {
  return <Module title="Productos" icon="inventory_2" />
}

export function InventarioPage() {
  return <Module title="Inventario" icon="inventory" />
}

export function PagosPage() {
  return <Module title="Pagos" icon="payments" />
}

export function NuevoPagoPage() {
  return <Module title="Registrar Pago" icon="payments" />
}

export function EvaluacionCrediticiaPage() {
  return <Module title="Evaluación crediticia" icon="psychology_alt" />
}

export function ReportesPage() {
  return <Module title="Reportes" icon="analytics" />
}

export function UsuariosPage() {
  return <Module title="Usuarios" icon="person" />
}

export function ConfiguracionPage() {
  return <Module title="Configuración" icon="settings" />
}

export function PerfilPage() {
  return <Module title="Perfil" icon="account_circle" />
}
