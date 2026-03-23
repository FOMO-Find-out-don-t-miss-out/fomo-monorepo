'use client'

import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { EventCard } from './event-card'
import type { PendingEvent } from '@/types/moderation'
import { Search, Check, X, Trash2 } from 'lucide-react'

interface EventListProps {
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
    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card/30">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-foreground">Events</h1>
            <Badge variant="secondary" className="text-xs">
              {events.length} pending
            </Badge>
          </div>
        </div>

        {/* Search and Bulk Actions */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search events..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-9 bg-input/50"
            />
          </div>

          {/* Select All */}
          <div className="flex items-center gap-2 border-l border-border pl-3">
            <Checkbox
              checked={allSelected}
              onCheckedChange={onSelectAll}
              className="data-[state=checked]:bg-primary"
            />
            <span className="text-sm text-muted-foreground">Select all</span>
          </div>

          {/* Bulk Actions */}
          {someSelected && (
            <div className="flex items-center gap-2 border-l border-border pl-3">
              <Badge variant="outline" className="text-xs">
                {selectedEventIds.length} selected
              </Badge>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-success border-success/30 hover:bg-success/10"
                onClick={onBulkApprove}
              >
                <Check className="w-3.5 h-3.5 mr-1" />
                Approve
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-destructive border-destructive/30 hover:bg-destructive/10"
                onClick={onBulkReject}
              >
                <X className="w-3.5 h-3.5 mr-1" />
                Reject
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Event Cards */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-2">
          {events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Search className="w-8 h-8 text-muted-foreground" />
              </div>
              <p className="text-muted-foreground">No events found</p>
              <p className="text-sm text-muted-foreground mt-1">Try adjusting your filters</p>
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
