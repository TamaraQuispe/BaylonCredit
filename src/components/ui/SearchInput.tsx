interface SearchInputProps {
  placeholder?: string
  className?: string
}

export default function SearchInput({ placeholder = 'Buscar...', className = '' }: SearchInputProps) {
  return (
    <div className={`relative ${className}`}>
      <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-on-surface-variant">
        <span className="material-symbols-outlined text-[18px]">search</span>
      </span>
      <input
        type="text"
        placeholder={placeholder}
        className="w-full h-10 pl-10 pr-4 bg-surface-container-lowest border border-outline-variant rounded-full font-body-md text-body-md text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
      />
    </div>
  )
}
