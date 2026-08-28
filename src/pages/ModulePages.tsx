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

export function PerfilPage() {
  return <Module title="Perfil" icon="account_circle" />
}
