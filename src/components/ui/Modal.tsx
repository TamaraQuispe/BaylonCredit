import { useEffect, type ReactNode } from 'react'
import Icon from './Icon'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  icon?: string
  iconClassName?: string
  children: ReactNode
  maxWidth?: string
}

export default function Modal({
  open,
  onClose,
  title,
  icon,
  iconClassName = '',
  children,
  maxWidth = 'max-w-md',
}: ModalProps) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    if (open) {
      document.addEventListener('keydown', handleKey)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 bg-on-surface/50 backdrop-blur-sm flex items-center justify-center">
      <div className={`bg-surface-container-lowest rounded-xl p-6 w-full mx-4 shadow-lg border border-outline-variant ${maxWidth}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {icon && <Icon name={icon} size="30px" className={iconClassName} />}
            <h3 className="font-h3-title text-h3-title text-on-surface">{title}</h3>
          </div>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface transition-colors p-1 rounded hover:bg-surface-container-high"
            aria-label="Cerrar"
          >
            <Icon name="close" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
