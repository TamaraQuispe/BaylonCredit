import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  icon?: string
}

export default function Input({ label, icon, className = '', id, ...rest }: InputProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="font-label-sm text-label-sm text-on-surface" htmlFor={inputId}>
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-outline pointer-events-none">
            <span className="material-symbols-outlined text-[20px]">{icon}</span>
          </span>
        )}
        <input
          id={inputId}
          className={`w-full bg-surface text-on-surface font-body-md text-body-md border border-outline-variant rounded-lg py-2.5 pr-4 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-sm ${
            icon ? 'pl-10' : 'pl-4'
          } ${className}`}
          {...rest}
        />
      </div>
    </div>
  )
}
