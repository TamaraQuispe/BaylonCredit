import { useState } from 'react'
import Icon from '@/components/ui/Icon'

interface ProductThumbnailProps {
  name: string
  icon: string
  imageUrl?: string | null
  className?: string
  imageClassName?: string
  iconClassName?: string
  iconSize?: string
}

export default function ProductThumbnail({
  name,
  icon,
  imageUrl,
  className = '',
  imageClassName = '',
  iconClassName = 'text-primary',
  iconSize = '22px',
}: ProductThumbnailProps) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null)
  const showImage = Boolean(imageUrl && failedUrl !== imageUrl)

  return (
    <div className={`overflow-hidden flex items-center justify-center ${className}`}>
      {showImage ? (
        <img
          src={imageUrl ?? undefined}
          alt={name}
          loading="lazy"
          className={`w-full h-full object-cover ${imageClassName}`}
          onError={() => setFailedUrl(imageUrl ?? null)}
        />
      ) : (
        <Icon name={icon || 'inventory_2'} size={iconSize} className={iconClassName} />
      )}
    </div>
  )
}
