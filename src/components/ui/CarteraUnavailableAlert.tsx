import type { ReactNode } from 'react'
import Icon from './Icon'

interface CarteraUnavailableAlertProps {
  children: ReactNode
  className?: string
}

/**
 * Aviso unico para cuando falla la carga de la cartera: el saldo no es cero,
 * es desconocido, y ninguna pantalla debe operar como si lo fuera.
 */
export default function CarteraUnavailableAlert({
  children,
  className,
}: CarteraUnavailableAlertProps) {
  return (
    <div
      role="alert"
      className={`p-4 bg-error-container text-on-error-container border border-error/20 rounded-lg flex items-start gap-2${className ? ` ${className}` : ''}`}
    >
      <Icon name="error" size="20px" />
      <div>
        <p className="font-medium">No se pudo cargar la cartera</p>
        <p className="font-body-md text-body-md">{children}</p>
      </div>
    </div>
  )
}
