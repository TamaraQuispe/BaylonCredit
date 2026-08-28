import PageHeader from '@/components/layout/PageHeader'
import Button from '@/components/ui/Button'
import StatCard from '@/components/ui/StatCard'
import { homeStats } from '@/data/home'

export default function HomePage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Buenos días, Administrador"
        subtitle="Aquí tienes un resumen de la actividad de hoy."
        actions={
          <Button variant="primary-container" size="md">
            <span className="material-symbols-outlined text-[18px]">add</span>
            Nuevo Fiado
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {homeStats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <div className="bg-surface-container-lowest rounded-lg border border-surface-container-high shadow-card overflow-hidden">
        <div className="p-6 text-center">
          <p className="font-h3-title text-h3-title text-on-surface">
            Panel principal en preparación
          </p>
          <p className="font-body-md text-body-md text-on-surface-variant mt-2 max-w-md mx-auto">
            Esta página se completará con el módulo de tablero, tablas y gráficos en una
            siguiente etapa. Por ahora se muestran los componentes base del sistema de diseño.
          </p>
        </div>
      </div>
    </div>
  )
}
