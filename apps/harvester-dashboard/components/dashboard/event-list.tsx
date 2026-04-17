'use client'

import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { EventCard } from './event-card'
import type { PendingEvent } from '@/types/api'
import { Search, Check, X, Sparkles, Activity } from 'lucide-react'

interface EventListProps {
  mode: 'pending' | 'published'
  events: PendingEvent[]
  selectedEvent: PendingEvent | null
  selectedEventIds: string[]
  searchQuery: string
  onSearchChange: (query: string) => void
  onSelectEvent: (event: PendingEvent) => void
  onToggleEventCheck: (eventId: string) => void
  onSelectAll: () => void
  onBulkApprove: () => void
  onBulkReject: () => void
}

export function EventList({
  mode,
  events,
  selectedEvent,
  selectedEventIds,
  searchQuery,
  onSearchChange,
  onSelectEvent,
  onToggleEventCheck,
  onSelectAll,
  onBulkApprove,
  onBulkReject
}: EventListProps) {
  const allSelected = events.length > 0 && selectedEventIds.length === events.length
  const someSelected = selectedEventIds.length > 0

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background/50">
      {/* Header */}
      <div className="p-6 border-b border-neon-blue/10 bg-card/40 backdrop-blur-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center border animate-neon-pulse",
                mode === 'pending' ? "bg-neon-purple/10 border-neon-purple/30 shadow-[0_0_10px_var(--neon-purple)]" : "bg-neon-green/10 border-neon-green/30 shadow-[0_0_10px_var(--neon-green)]"
            )}>
                {mode === 'pending' ? <Activity className="w-5 h-5 text-neon-purple" /> : <Sparkles className="w-5 h-5 text-neon-green" />}
            </div>
            <div>
                <h1 className="text-2xl font-black text-foreground uppercase tracking-tighter italic leading-none mb-1">
                {mode} Signals
                </h1>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em]">
                    Synchronized Stream protocol v2.4
                </p>
            </div>
          </div>
          <Badge 
            variant="outline" 
            className={cn(
              "h-7 px-4 text-[10px] font-black uppercase tracking-[0.2em] animate-pulse",
              mode === 'pending' ? "badge-neon-purple" : "badge-neon-green"
            )}
          >
            {events.length} ACTIVE
          </Badge>
        </div>

        {/* Search and Bulk Actions */}
        <div className="flex items-center gap-6">
          <div className="relative flex-1 max-w-md group">
            <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-neon-blue transition-colors" />
            <Input
              placeholder="Filter stream by title or location..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-11 bg-card/60 input-neon h-11 text-sm font-medium"
            />
          </div>

          <div className="flex items-center gap-4">
              {/* Select All */}
              <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-card/40 border border-border/50 hover:border-neon-blue/30 transition-all cursor-pointer group" onClick={onSelectAll}>
                <Checkbox
                  checked={allSelected}
                  onCheckedChange={onSelectAll}
                  className="checkbox-neon"
                />
                <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest group-hover:text-neon-blue">Sync Selection</span>
              </div>

              {/* Bulk Actions */}
              {someSelected && (
                <div className="flex items-center gap-3 border-l border-neon-blue/20 pl-6 animate-in fade-in slide-in-from-right-4 duration-300">
                  <div className="flex items-center gap-2">
                    <Button
                        variant="neon-green"
                        size="sm"
                        className="h-9 px-4 font-black uppercase tracking-widest text-[10px]"
                        onClick={onBulkApprove}
                    >
                        <Check className="w-4 h-4 mr-2" />
                        Execute ({selectedEventIds.length})
                    </Button>
                    <Button
                        variant="neon-red"
                        size="sm"
                        className="h-9 px-4 font-black uppercase tracking-widest text-[10px]"
                        onClick={onBulkReject}
                    >
                        <X className="w-4 h-4 mr-2" />
                        Abort
                    </Button>
                  </div>
                </div>
              )}
          </div>
        </div>
      </div>

      {/* Event Cards */}
      <ScrollArea className="flex-1 min-h-0 scrollbar-neon">
        <div className="p-6 space-y-3 relative">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="w-20 h-20 rounded-2xl bg-muted/10 border border-dashed border-border flex items-center justify-center mb-6">
                <Search className="w-10 h-10 text-muted-foreground/30" />
              </div>
              <p className="text-xl font-bold text-foreground/50 uppercase tracking-widest">No signals detected</p>
              <p className="text-xs text-muted-foreground/60 mt-2 uppercase tracking-tight">Try recalibrating your frequency filters</p>
            </div>
          ) : (
            events.map((event) => (
              <EventCard
                key={event.id}
                event={event}
                isSelected={selectedEvent?.id === event.id}
                isChecked={selectedEventIds.includes(event.id)}
                onSelect={() => onSelectEvent(event)}
                onToggleCheck={() => onToggleEventCheck(event.id)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
