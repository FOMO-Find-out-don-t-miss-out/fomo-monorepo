'use client'

import { useState, useMemo, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { FilterSidebar } from '@/components/dashboard/filter-sidebar'
import { EventList } from '@/components/dashboard/event-list'
import { EventInspector } from '@/components/dashboard/event-inspector'
import { moderationApi } from '@/lib/api'
import type { PendingEvent, GeocodeSuggestion } from '@/types/api'
import { toast } from 'sonner'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

function EventsDashboard() {
  const queryClient = useQueryClient()
  const searchParams = useSearchParams()
  
  // Selection State
  const [selectedEvent, setSelectedEvent] = useState<PendingEvent | null>(null)
  const [selectedEventIds, setSelectedEventIds] = useState<string[]>([])
  
  // UI State
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Filters
  const [selectedLocation] = useState('All Locations')
  const [selectedCategory, setSelectedCategory] = useState('All Categories')
  const [selectedStatus, setSelectedStatus] = useState<string | 'all'>('all')
  const [selectedSource, setSelectedSource] = useState<string | 'all'>('all')

  // Queries
  const { data: events = [], isLoading: eventsLoading } = useQuery({
    queryKey: ['pending-events', selectedLocation, selectedStatus],
    queryFn: () => moderationApi.getPendingEvents(
      selectedLocation === 'All Locations' ? undefined : selectedLocation,
      selectedStatus === 'all' ? undefined : [selectedStatus]
    )
  })

  // Handle URL Params
  useEffect(() => {
    const search = searchParams.get('search')
    if (search) {
      setSearchQuery(search)
    }

    const id = searchParams.get('id')
    if (id && events.length > 0) {
      const event = events.find(e => e.id === id)
      if (event) {
        setSelectedEvent(event)
        setInspectorOpen(true)
      }
    }
  }, [searchParams, events])

  // Mutations
  const approveMutation = useMutation({
    mutationFn: (eventId: string) => moderationApi.approveEvent(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      queryClient.invalidateQueries({ queryKey: ['published-events'] })
      toast.success('Event approved and published')
      setInspectorOpen(false)
      setSelectedEvent(null)
    }
  })

  const rejectMutation = useMutation({
    mutationFn: (eventId: string) => moderationApi.rejectEvent(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Event rejected and deleted')
      setInspectorOpen(false)
      setSelectedEvent(null)
    }
  })

  const bulkApproveMutation = useMutation({
    mutationFn: (ids: string[]) => moderationApi.approveBatch(ids),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      queryClient.invalidateQueries({ queryKey: ['published-events'] })
      toast.success(`Successfully approved ${data.approved_count} events`)
      setSelectedEventIds([])
    }
  })

  const bulkRejectMutation = useMutation({
    mutationFn: (ids: string[]) => moderationApi.rejectBatch(ids),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success(`Successfully rejected ${data.rejected_count} events`)
      setSelectedEventIds([])
    }
  })

  // Handlers
  const handleSelectEvent = (event: PendingEvent) => {
    setSelectedEvent(event)
    setInspectorOpen(true)
  }

  const handleSuggestionSelect = (_suggestion: GeocodeSuggestion) => {
    void _suggestion
    if (selectedEvent) {
        // Find & Sync logic here if needed
        toast.info("Select an event first to apply this location");
    }
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
      if (selectedSource !== 'all' && event.source_provider !== selectedSource) return false
      return true
    })
  }, [events, searchQuery, selectedCategory, selectedSource])

  const eventCounts = useMemo(() => ({
    verified: events.filter((e) => e.geocoding_status === 'verified').length,
    ambiguous: events.filter((e) => e.geocoding_status === 'ambiguous').length,
    failed: events.filter((e) => e.geocoding_status === 'failed').length,
    total: events.length
  }), [events])

  return (
    <DashboardLayout>
      <div className="h-full flex">
        <FilterSidebar
          mode="pending"
          selectedCategory={selectedCategory}
          setSelectedCategory={setSelectedCategory}
          selectedStatus={selectedStatus}
          setSelectedStatus={setSelectedStatus}
          selectedSource={selectedSource}
          setSelectedSource={setSelectedSource}
          eventCounts={eventCounts}
          onSuggestionSelect={handleSuggestionSelect}
        />

        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          <div className="flex-1 flex flex-col overflow-hidden relative min-h-0">
            {eventsLoading && events.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <EventList
                mode="pending"
                events={filteredEvents}
                selectedEvent={selectedEvent}
                selectedEventIds={selectedEventIds}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                onSelectEvent={handleSelectEvent}
                onToggleEventCheck={(id) => setSelectedEventIds(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id])}
                onSelectAll={() => setSelectedEventIds(selectedEventIds.length === filteredEvents.length ? [] : filteredEvents.map(e => e.id))}
                onBulkApprove={() => bulkApproveMutation.mutate(selectedEventIds)}
                onBulkReject={() => bulkRejectMutation.mutate(selectedEventIds)}
              />
            )}
          </div>
        </div>

        <EventInspector
          event={selectedEvent}
          open={inspectorOpen && !!selectedEvent}
          onOpenChange={setInspectorOpen}
          onApprove={(e) => approveMutation.mutate(e.id)}
          onReject={(e) => rejectMutation.mutate(e.id)}
        />
      </div>
    </DashboardLayout>
  )
}

export default function EventsPage() {
  return (
    <Suspense fallback={
      <div className="h-screen w-full flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    }>
      <EventsDashboard />
    </Suspense>
  )
}
