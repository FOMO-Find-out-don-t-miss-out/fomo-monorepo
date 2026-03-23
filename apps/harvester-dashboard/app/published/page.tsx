'use client'

import { useState, useMemo } from 'react'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { FilterSidebar } from '@/components/dashboard/filter-sidebar'
import { EventList } from '@/components/dashboard/event-list'
import { EventInspector } from '@/components/dashboard/event-inspector'
import { moderationApi } from '@/lib/api'
import type { PendingEvent, GeocodeSuggestion } from '@/types/moderation'
import { toast } from 'sonner'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

export default function PublishedEventsPage() {
  const queryClient = useQueryClient()
  
  // Selection State
  const [selectedEvent, setSelectedEvent] = useState<PendingEvent | null>(null)
  const [selectedEventIds, setSelectedEventIds] = useState<string[]>([])
  
  // UI State
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Filters
  const [selectedLocation, setSelectedLocation] = useState('All Locations')
  const [selectedCategory, setSelectedCategory] = useState('All Categories')
  const [selectedStatus, setSelectedStatus] = useState<string | 'all'>('all')

  // Queries
  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ['published-events', selectedLocation],
    queryFn: () => moderationApi.getPublishedEvents(
      selectedLocation === 'All Locations' ? undefined : selectedLocation
    )
  })

  // Mutations
  const unpublishMutation = useMutation({
    mutationFn: (eventId: string) => moderationApi.unpublishEvent(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['published-events'] })
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Event moved to pending')
      setInspectorOpen(false)
      setSelectedEvent(null)
    }
  })

  // Handlers
  const handleSelectEvent = (event: PendingEvent) => {
    setSelectedEvent(event)
    setInspectorOpen(true)
  }

  // Memoized data
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (!event.title.toLowerCase().includes(query) && !(event.location_name || '').toLowerCase().includes(query)) {
          return false
        }
      }
      if (selectedCategory !== 'All Categories' && event.category !== selectedCategory) return false
      return true
    })
  }, [events, searchQuery, selectedCategory])

  const dynamicLocations = useMemo(() => {
    const locs = new Set(events.map(e => e.location_name).filter(Boolean))
    return ['All Locations', ...Array.from(locs).sort()] as string[]
  }, [events])

  // Stats for published events (they don't have geocoding_status in the same way usually, but let's keep the object shape)
  const eventCounts = useMemo(() => ({
    verified: events.length,
    ambiguous: 0,
    failed: 0,
    total: events.length
  }), [events])

  return (
    <DashboardLayout>
      <div className="h-full flex min-h-0">
        <FilterSidebar
          selectedLocation={selectedLocation}
          setSelectedLocation={setSelectedLocation}
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          selectedStatus={selectedStatus}
          setSelectedStatus={setSelectedStatus}
          eventCounts={eventCounts}
          locations={dynamicLocations}
        />

        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex-1 flex flex-col overflow-hidden relative min-h-0">
            {eventsLoading && events.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <EventList
                events={filteredEvents}
                selectedEvent={selectedEvent}
                selectedEventIds={selectedEventIds}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSelectEvent={handleSelectEvent}
                onToggleEventCheck={(id) => setSelectedEventIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])}
                onSelectAll={() => setSelectedEventIds(selectedEventIds.length === filteredEvents.length ? [] : filteredEvents.map(e => e.id))}
                onBulkApprove={() => {}} // Not applicable here
                onBulkReject={() => {}} // Not applicable here
              />
            )}
          </div>
        </div>

        <EventInspector
          event={selectedEvent}
          open={inspectorOpen && !!selectedEvent}
          onOpenChange={setInspectorOpen}
          onApprove={() => {}} // Not applicable for published
          onReject={(e) => unpublishMutation.mutate(e.id)} // "Reject" here means unpublish
        />
      </div>
    </DashboardLayout>
  )
}
