interface DonutSlice {
  label: string
  value: string
  color: string
  percent: number
}

interface DonutChartProps {
  segments: DonutSlice[]
  centerLabel?: string
  centerValue?: string
}

export default function DonutChart({
  segments,
  centerLabel,
  centerValue,
}: DonutChartProps) {
  let accumulated = 0
  const stops = segments
    .map((segment) => {
      const start = accumulated
      const end = accumulated + segment.percent
      accumulated = end
      return `${segment.color} ${start}% ${end}%`
    })
    .join(', ')

  return (
    <div className="flex items-center gap-6">
      <div className="relative shrink-0 w-40 h-40 rounded-full" style={{ background: `conic-gradient(${stops})` }}>
        <div className="absolute inset-3 rounded-full bg-white flex flex-col items-center justify-center">
          {centerValue && (
            <span className="font-h2-headline text-h2-headline text-on-surface">
              {centerValue}
            </span>
          )}
          {centerLabel && (
            <span className="font-label-sm text-label-sm text-on-surface-variant text-center">
              {centerLabel}
            </span>
          )}
        </div>
      </div>

      <ul className="flex flex-col gap-3 flex-1">
        {segments.map((segment) => (
          <li key={segment.label} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex items-center gap-2 text-on-surface-variant">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: segment.color }}
              />
              {segment.label}
            </span>
            <span className="font-medium text-on-surface">{segment.value}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
