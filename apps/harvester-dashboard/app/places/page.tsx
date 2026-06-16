'use client'

import { useState, useMemo, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { VenueList, type PlaceVerificationFilter, type PlaceSort } from '@/components/dashboard/venue-list'
import { VenueInspector } from '@/components/dashboard/venue-inspector'
import { moderationApi } from '@/lib/api'
import type { Venue } from '@/types/api'
import { isPlaceVerified } from '@/lib/utils'
import { useQuery } from '@tanstack/react-query'

function PlacesDashboard() {
  const searchParams = useSearchParams()
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

  // Deep-link support from event cards/inspectors: /places?placeId=<id> opens that
  // place directly; /places?search=<name> falls back to a name search when no id
  // is available (e.g. a pending event's place candidate hasn't resolved yet).
  useEffect(() => {
    const search = searchParams.get('search')
    if (search) {
      setSearchQuery(search)
    }
  }, [searchParams])

  useEffect(() => {
    const placeId = searchParams.get('placeId')
    if (placeId && venues.length > 0) {
      const venue = venues.find((v) => v.id === placeId)
      if (venue) {
        setSelectedVenue(venue)
        setInspectorOpen(true)
      }
    }
  }, [searchParams, venues])

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

export default function PlacesPage() {
  return (
    <Suspense fallback={
      <div className="h-screen w-full flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    }>
      <PlacesDashboard />
    </Suspense>
  )
}
