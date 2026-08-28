import Icon from '@/components/ui/Icon'

export interface ActivityEntry {
  id: string
  title: string
  description: string
  time: string
  icon: string
  tone: 'primary' | 'secondary' | 'error' | 'success'
}

const toneIconClasses: Record<ActivityEntry['tone'], string> = {
  primary: 'bg-primary-fixed text-on-primary-fixed',
  secondary: 'bg-secondary-fixed text-on-secondary-fixed',
  error: 'bg-error-container text-on-error-container',
  success: 'bg-green-100 text-green-700',
}

interface ActivityFeedProps {
  items: ActivityEntry[]
}

export default function ActivityFeed({ items }: ActivityFeedProps) {
  return (
    <ul className="flex flex-col">
      {items.map((item, index) => (
        <li
          key={item.id}
          className={`flex gap-3 py-3 ${index > 0 ? 'border-t border-outline-variant/60' : ''}`}
        >
          <span
            className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${toneIconClasses[item.tone]}`}
          >
            <Icon name={item.icon} size="18px" />
          </span>
          <div className="min-w-0">
            <p className="font-body-md text-body-md text-on-surface font-medium">{item.title}</p>
            <p className="font-label-sm text-label-sm text-on-surface-variant">{item.description}</p>
          </div>
          <span className="ml-auto shrink-0 font-label-sm text-label-sm text-on-surface-variant/70 whitespace-nowrap">
            {item.time}
          </span>
        </li>
      ))}
    </ul>
  )
}
