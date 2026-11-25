export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN',
    minimumFractionDigits: 2,
  }).format(value)
}

export const UNAVAILABLE_LABEL = 'No disponible'

/** Valor formateado, o '—' si la fuente no permite conocerlo. */
export function orDash(value: string, unavailable: boolean): string {
  return unavailable ? '—' : value
}

/** Texto de apoyo, o la etiqueta de no disponible si falta la fuente. */
export function orUnavailable(value: string, unavailable: boolean): string {
  return unavailable ? UNAVAILABLE_LABEL : value
}

const dateFormatter = new Intl.DateTimeFormat('es-PE', {
  day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'America/Lima',
})
const dateTimeFormatter = new Intl.DateTimeFormat('es-PE', {
  day: '2-digit', month: '2-digit', year: 'numeric',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'America/Lima',
})

function civilDate(value: string): Date | null {
  const iso = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  const display = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(value)
  if (!iso && !display) return null
  const [year, month, day] = iso
    ? [Number(iso[1]), Number(iso[2]), Number(iso[3])]
    : [Number(display![3]), Number(display![2]), Number(display![1])]
  // Noon UTC keeps a civil date on the same calendar day in Lima.
  const date = new Date(0)
  date.setUTCFullYear(year, month - 1, day)
  date.setUTCHours(12, 0, 0, 0)
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
    ? date : null
}

function timestamp(value: string): Date | null {
  // Display timestamps from the repository use the business timezone (Lima).
  const display = /^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4}),?\s+(\d{1,2}):(\d{2})(?:\s*([ap])\.?\s*m\.?)?$/i.exec(value)
  if (display) {
    const [, day, month, year, hour, minute, period] = display
    let hours = Number(hour)
    if (Number(minute) > 59 || hours > (period ? 12 : 23) || (period && hours < 1)) return null
    if (period) hours = hours % 12 + (period.toLowerCase() === 'p' ? 12 : 0)
    const fullYear = year.length === 2 ? 2000 + Number(year) : Number(year)
    if (!civilDate(`${day}/${month}/${fullYear}`)) return null
    return new Date(`${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${String(hours).padStart(2, '0')}:${minute}:00-05:00`)
  }
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return null
  // An ISO timestamp without an offset is treated as Lima wall time.
  const date = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}-05:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value: string): string {
  const date = civilDate(value) ?? timestamp(value)
  return date ? dateFormatter.format(date) : value
}

export function formatDateTime(value: string): string {
  const date = timestamp(value)
  return date ? dateTimeFormatter.format(date) : formatDate(value)
}

export function daysUntil(value: string, now = new Date()): number | null {
  const target = civilDate(value) ?? civilDate(formatDate(value))
  const today = civilDate(dateFormatter.format(now))
  return target && today ? Math.round((target.getTime() - today.getTime()) / 86_400_000) : null
}

export function formatDays(value: number): string {
  return `${value} ${value === 1 ? 'día' : 'días'}`
}
