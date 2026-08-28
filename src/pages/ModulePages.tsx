import ModulePlaceholder from '@/components/common/ModulePlaceholder'

interface ModuleProps {
  title: string
  icon: string
}

function Module({ title, icon }: ModuleProps) {
  return <ModulePlaceholder title={title} icon={icon} />
}

export function NuevoFiadoPage() {
  return <Module title="Registrar Fiado" icon="receipt_long" />
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
