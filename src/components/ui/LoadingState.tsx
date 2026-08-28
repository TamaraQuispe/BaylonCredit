interface LoadingStateProps {
  label?: string
}

export default function LoadingState({ label = 'Cargando...' }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center gap-3">
      <span className="material-symbols-outlined text-primary animate-spin">progress_activity</span>
      <p className="font-body-md text-body-md text-on-surface-variant">{label}</p>
    </div>
  )
}
