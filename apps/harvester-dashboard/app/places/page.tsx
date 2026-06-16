'use client'

import { useState, useMemo } from 'react'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { VenueList, type PlaceVerificationFilter, type PlaceSort } from '@/components/dashboard/venue-list'
import { VenueInspector } from '@/components/dashboard/venue-inspector'
import { moderationApi } from '@/lib/api'
import type { Venue } from '@/types/api'
import { isPlaceVerified } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'

export default function PlacesPage() {
  const [selectedVenue, setSelectedVenue] = useState<Venue | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<PlaceVerificationFilter>('all')
  const [missingCoordsOnly, setMissingCoordsOnly] = useState(false)
  const [sortBy, setSortBy] = useState<PlaceSort>('relevance')

  // Queries
  const { data: venues = [], isLoading: venuesLoading } = useQuery({
    queryKey: ['venues', searchQuery],
    queryFn: () => moderationApi.getVenues(searchQuery || undefined),
  })

  const filteredVenues = useMemo(() => {
    const filtered = venues.filter((venue) => {
      if (filterStatus !== 'all' && venue.verification_status !== filterStatus) return false
      if (missingCoordsOnly && venue.lat != null && venue.lng != null) return false
      return true
    })

    return [...filtered].sort((a, b) => {
      if (sortBy === 'relevance') return b.relevance - a.relevance
      const aTime = new Date(a.updated_at ?? a.created_at ?? 0).getTime()
      const bTime = new Date(b.updated_at ?? b.created_at ?? 0).getTime()
      return bTime - aTime
    })
  }, [venues, filterStatus, missingCoordsOnly, sortBy])

  const handleSelectVenue = (venue: Venue) => {
    setSelectedVenue(venue)
    setInspectorOpen(true)
  }

  const totalCount = venues.length
  const unverifiedCount = useMemo(() => venues.filter(v => !isPlaceVerified(v)).length, [venues])

  return (
    <DashboardLayout>
      <div className="h-full flex min-h-0">
        <VenueList
          venues={filteredVenues}
          selectedVenue={selectedVenue}
          searchQuery={searchQuery}
          filterStatus={filterStatus}
          missingCoordsOnly={missingCoordsOnly}
          sortBy={sortBy}
          onSearchChange={setSearchQuery}
          onFilterStatusChange={setFilterStatus}
          onMissingCoordsOnlyChange={setMissingCoordsOnly}
          onSortByChange={setSortBy}
          onSelectVenue={handleSelectVenue}
          isLoading={venuesLoading}
          totalCount={totalCount}
          unverifiedCount={unverifiedCount}
        />

        <VenueInspector
          venue={selectedVenue}
          open={inspectorOpen && !!selectedVenue}
          onOpenChange={setInspectorOpen}
        />
      </div>
    </DashboardLayout>
  )
}
