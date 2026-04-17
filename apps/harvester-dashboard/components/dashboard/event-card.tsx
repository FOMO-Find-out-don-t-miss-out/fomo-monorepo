'use client'

import Image from 'next/image'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PendingEvent } from '@/types/api'
import { MapPin, Calendar, CheckCircle2, AlertCircle, XCircle, ImageOff, Code, Sparkles, Database } from 'lucide-react'
import { format } from 'date-fns'

interface EventCardProps {
  event: PendingEvent
  isSelected: boolean
  isChecked: boolean
  onSelect: () => void
  onToggleCheck: () => void
}

const statusConfig: Record<string, { icon: React.ElementType, color: string, neonColor: string, label: string }> = {
  verified: {
    icon: CheckCircle2,
    color: 'bg-neon-green',
    neonColor: 'text-neon-green',
    label: 'Verified'
  },
  ambiguous: {
    icon: AlertCircle,
    color: 'bg-warning',
    neonColor: 'text-warning',
    label: 'Ambiguous'
  },
  failed: {
    icon: XCircle,
    color: 'bg-destructive',
    neonColor: 'text-destructive',
    label: 'Failed'
  }
}

const ingestionConfig: Record<string, { icon: React.ElementType, label: string, color: string }> = {
  json_ld: {
    icon: Code,
    label: 'JSON-LD',
    color: 'text-neon-blue'
  },
  html_fallback: {
    icon: Sparkles,
    label: 'AI Fallback',
    color: 'text-neon-purple'
  },
  registry: {
    icon: Database,
    label: 'Registry',
    color: 'text-warning'
  },
  manual: {
    icon: Database,
    label: 'Manual',
    color: 'text-muted-foreground'
  }
}

export function EventCard({ event, isSelected, isChecked, onSelect, onToggleCheck }: EventCardProps) {
  const status = statusConfig[event.geocoding_status] || statusConfig.failed
  const StatusIcon = status.icon
  const Ingestion = ingestionConfig[event.ingestion_method] || ingestionConfig.manual
  const IngestionIcon = Ingestion.icon

  return (
    <div
      className={cn(
        'group relative rounded-xl border bg-card/40 backdrop-blur-sm transition-all duration-300 cursor-pointer overflow-hidden',
        isSelected
          ? 'card-neon-selected border-neon-blue'
          : 'card-neon border-border hover:border-neon-purple/50'
      )}
      onClick={onSelect}
    >
      <div className="flex gap-4 p-4">
        {/* Checkbox */}
        <div
          className="flex-shrink-0 pt-1"
          onClick={(e) => {
            e.stopPropagation()
            onToggleCheck()
          }}
        >
          <Checkbox
            checked={isChecked}
            className="checkbox-neon"
          />
        </div>

        {/* Thumbnail */}
        <div className="relative w-24 h-24 flex-shrink-0 rounded-lg overflow-hidden bg-muted/30 border border-border/50 group-hover:border-neon-blue/30 transition-colors">
          {event.photo_url ? (
            <Image
              src={event.photo_url}
              alt={event.title}
              fill
              className="object-cover transition-transform duration-500 group-hover:scale-110"
              sizes="96px"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <ImageOff className="w-8 h-8 text-muted-foreground/50" />
            </div>
          )}
          
          {/* Status Glow Overlay */}
          <div className="absolute top-1.5 right-1.5">
            <div
              className={cn(
                'w-3 h-3 rounded-full border border-white/20',
                status.color,
                event.geocoding_status === 'verified' && 'shadow-[0_0_8px_var(--neon-green)]',
                event.geocoding_status === 'ambiguous' && 'shadow-[0_0_8px_var(--warning)]',
                event.geocoding_status === 'failed' && 'shadow-[0_0_8px_var(--destructive)]'
              )}
              title={status.label}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 flex flex-col justify-between">
          <div>
            <div className="flex items-start justify-between gap-2">
              <h3 className={cn(
                "font-bold text-base truncate transition-colors",
                isSelected ? "text-neon-blue" : "text-foreground group-hover:text-neon-blue/80"
              )}>
                {event.title}
              </h3>
              <Badge variant="outline" className="badge-neon-purple text-[10px] uppercase tracking-wider h-5 px-2 flex-shrink-0">
                {event.category}
              </Badge>
            </div>
            
            <div className="flex items-center gap-2 mt-1.5 text-xs text-muted-foreground">
              <MapPin className="w-3.5 h-3.5 text-neon-blue/60" />
              <span className="truncate group-hover:text-foreground/80 transition-colors">{event.location_name}</span>
            </div>

            <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
              <Calendar className="w-3.5 h-3.5 text-neon-purple/60" />
              <span className="group-hover:text-foreground/80 transition-colors">
                {format(new Date(event.start_time), 'MMM d, HH:mm')}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-muted-foreground/60 uppercase tracking-tighter">
                {event.country_code}
              </span>
              {event.source_provider && (
                <Badge 
                  variant="outline" 
                  className="badge-neon text-[9px] h-4.5 px-2 border-neon-blue/20 bg-neon-blue/5 font-bold uppercase tracking-tighter"
                >
                  {event.source_provider}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-muted/20 border border-border/30">
                <IngestionIcon className={cn('w-3 h-3', Ingestion.color)} />
                <span className="text-[9px] font-bold uppercase text-muted-foreground tracking-widest">
                  {Ingestion.label}
                </span>
              </div>
              <StatusIcon className={cn(
                'w-4 h-4 transition-all duration-300',
                status.neonColor,
                isSelected && 'scale-110 drop-shadow-[0_0_5px_currentColor]'
              )} />
            </div>
          </div>
        </div>
      </div>
      
      {/* Selection Accent Line */}
      {isSelected && (
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-neon-blue animate-neon-pulse shadow-[0_0_10px_var(--neon-blue)]" />
      )}
    </div>
  )
}
