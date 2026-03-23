'use client'

import Image from 'next/image'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PendingEvent } from '@/types/moderation'
import { MapPin, Calendar, CheckCircle2, AlertCircle, XCircle, ImageOff } from 'lucide-react'
import { format } from 'date-fns'

interface EventCardProps {
  event: PendingEvent
  isSelected: boolean
  isChecked: boolean
  onSelect: () => void
  onToggleCheck: () => void
}

const statusConfig: Record<string, any> = {
  verified: {
    icon: CheckCircle2,
    color: 'bg-green-500',
    label: 'Verified'
  },
  ambiguous: {
    icon: AlertCircle,
    color: 'bg-yellow-500',
    label: 'Ambiguous'
  },
  failed: {
    icon: XCircle,
    color: 'bg-red-500',
    label: 'Failed'
  }
}

export function EventCard({ event, isSelected, isChecked, onSelect, onToggleCheck }: EventCardProps) {
  const status = statusConfig[event.geocoding_status] || statusConfig.failed
  const StatusIcon = status.icon

  return (
    <div
      className={cn(
        'group relative rounded-lg border bg-card transition-all cursor-pointer',
        isSelected
          ? 'border-primary ring-1 ring-primary/50'
          : 'border-border hover:border-muted-foreground/50'
      )}
      onClick={onSelect}
    >
      <div className="flex gap-3 p-3">
        {/* Checkbox */}
        <div
          className="flex-shrink-0 pt-0.5"
          onClick={(e) => {
            e.stopPropagation()
            onToggleCheck()
          }}
        >
          <Checkbox
            checked={isChecked}
            className="data-[state=checked]:bg-primary data-[state=checked]:border-primary"
          />
        </div>

        {/* Thumbnail */}
        <div className="relative w-20 h-20 flex-shrink-0 rounded-md overflow-hidden bg-muted">
          {event.photo_url ? (
            <Image
              src={event.photo_url}
              alt={event.title}
              fill
              className="object-cover"
              sizes="80px"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <ImageOff className="w-6 h-6 text-muted-foreground" />
            </div>
          )}
          {/* Status Badge Overlay */}
          <div className="absolute top-1 right-1">
            <div
              className={cn(
                'w-2.5 h-2.5 rounded-full',
                status.color
              )}
              title={status.label}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium text-sm text-foreground truncate">
              {event.title}
            </h3>
            <Badge variant="secondary" className="text-xs flex-shrink-0">
              {event.category}
            </Badge>
          </div>
          
          <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{event.location_name}</span>
          </div>

          <div className="flex items-center gap-1 mt-0.5 text-xs text-muted-foreground">
            <Calendar className="w-3 h-3 flex-shrink-0" />
            <span>{format(new Date(event.start_time), 'MMM d, yyyy h:mm a')}</span>
          </div>

          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-muted-foreground">
              {event.country_code}
            </span>
            <div className="flex items-center gap-1">
              <StatusIcon className={cn(
                'w-3.5 h-3.5',
                event.geocoding_status === 'verified' && 'text-green-500',
                event.geocoding_status === 'ambiguous' && 'text-yellow-500',
                event.geocoding_status === 'failed' && 'text-red-500'
              )} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
