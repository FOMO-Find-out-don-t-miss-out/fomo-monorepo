'use client'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Venue } from '@/types/moderation'
import { MapPin, CheckCircle2, Building2 } from 'lucide-react'

interface VenueCardProps {
  venue: Venue
  isSelected: boolean
  onSelect: () => void
}

export function VenueCard({ venue, isSelected, onSelect }: VenueCardProps) {
  return (
    <div
      className={cn(
        'group relative rounded-lg border bg-card transition-all cursor-pointer p-4',
        isSelected
          ? 'border-primary ring-1 ring-primary/50'
          : 'border-border hover:border-muted-foreground/50'
      )}
      onClick={onSelect}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
          <Building2 className="w-6 h-6 text-muted-foreground" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-sm text-foreground">
                {venue.name}
              </h3>
              {venue.is_manually_verified && (
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
              )}
            </div>
            <Badge
              variant={venue.is_manually_verified ? 'default' : 'secondary'}
              className={cn(
                'text-xs flex-shrink-0',
                venue.is_manually_verified && 'bg-green-600/10 text-green-600 border-green-600/20'
              )}
            >
              {venue.is_manually_verified ? 'Verified' : 'Unverified'}
            </Badge>
          </div>

          <div className="flex items-center gap-1 mt-1 text-xs text-muted-foreground">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{venue.city || 'Unknown City'}</span>
          </div>

          <p className="text-xs text-muted-foreground mt-1 truncate">
            {venue.full_address}
          </p>

          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center gap-1.5 flex-1">
              <span className="text-xs text-muted-foreground whitespace-nowrap">Relevance:</span>
              <div className="w-full max-w-[80px] h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${venue.relevance * 100}%` }}
                />
              </div>
              <span className="text-xs text-foreground font-medium">{Math.round(venue.relevance * 100)}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
