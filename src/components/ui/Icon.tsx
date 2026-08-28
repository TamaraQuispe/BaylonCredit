interface IconProps {
  name: string
  className?: string
  filled?: boolean
  size?: string
}

export default function Icon({ name, className = '', filled = false, size }: IconProps) {
  return (
    <span
      className={`material-symbols-outlined select-none ${filled ? 'fill-icon' : ''} ${className}`}
      style={size ? { fontSize: size } : undefined}
      aria-hidden="true"
    >
      {name}
    </span>
  )
}
