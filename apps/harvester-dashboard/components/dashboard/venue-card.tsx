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
        'group relative rounded-xl border bg-card/40 backdrop-blur-sm transition-all duration-300 cursor-pointer overflow-hidden p-4',
        isSelected
          ? 'card-neon-selected border-neon-blue'
          : 'card-neon border-border hover:border-neon-purple/50'
      )}
      onClick={onSelect}
    >
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={cn(
          "w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-300 border border-border/50",
          isSelected ? "bg-neon-blue/20 border-neon-blue/30 neon-glow-sm" : "bg-muted/30 group-hover:bg-neon-purple/10 group-hover:border-neon-purple/20"
        )}>
          <Building2 className={cn(
            "w-7 h-7 transition-colors duration-300",
            isSelected ? "text-neon-blue" : "text-muted-foreground group-hover:text-neon-purple"
          )} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 flex flex-col justify-between h-14">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <h3 className={cn(
                "font-bold text-base truncate transition-colors",
                isSelected ? "text-neon-blue text-neon-glow-blue" : "text-foreground group-hover:text-neon-purple"
              )}>
                {venue.name}
              </h3>
              {venue.is_manually_verified && (
                <CheckCircle2 className="w-4 h-4 text-neon-green flex-shrink-0 drop-shadow-[0_0_3px_var(--neon-green)]" />
              )}
            </div>
            <Badge
              variant="outline"
              className={cn(
                'text-[10px] uppercase tracking-widest font-black h-5 px-2 flex-shrink-0 transition-all',
                venue.is_manually_verified 
                  ? 'badge-neon-green border-neon-green/30' 
                  : 'badge-neon-purple border-neon-purple/30 opacity-70'
              )}
            >
              {venue.is_manually_verified ? 'Verified' : 'Unverified'}
            </Badge>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-muted-foreground group-hover:text-foreground/80 transition-colors">
            <MapPin className="w-3.5 h-3.5 text-neon-blue/60" />
            <span className="truncate font-medium">{venue.city || 'Unknown City'}</span>
            <span className="mx-1 text-muted-foreground/30">•</span>
            <span className="truncate text-[11px] opacity-70">{venue.full_address}</span>
          </div>
        </div>
      </div>

      {/* Relevance Bar at bottom */}
      <div className="mt-4 flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden border border-white/5">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-1000 ease-out",
              isSelected ? "bg-neon-blue neon-glow-sm" : "bg-neon-purple/60"
            )}
            style={{ width: `${venue.relevance * 100}%` }}
          />
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-bold uppercase tracking-tighter text-muted-foreground">Match</span>
          <span className={cn(
            "text-xs font-black tabular-nums",
            isSelected ? "text-neon-blue" : "text-neon-purple/80"
          )}>
            {Math.round(venue.relevance * 100)}%
          </span>
        </div>
      </div>

      {/* Selection Accent Line */}
      {isSelected && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-neon-blue animate-neon-pulse shadow-[0_0_10px_var(--neon-blue)]" />
      )}
    </div>
  )
}
