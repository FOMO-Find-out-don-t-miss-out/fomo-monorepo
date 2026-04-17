'use client'

import { useState, useMemo } from 'react'
import { DashboardLayout } from '@/components/dashboard/dashboard-layout'
import { VenueList } from '@/components/dashboard/venue-list'
import { VenueInspector } from '@/components/dashboard/venue-inspector'
import { moderationApi } from '@/lib/api'
import type { Venue } from '@/types/api'
import { useQuery } from '@tanstack/react-query'

export default function VenuesPage() {
  const [selectedVenue, setSelectedVenue] = useState<Venue | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<'all' | 'verified' | 'unverified'>('all')

  // Queries
  const { data: venues = [], isLoading: venuesLoading } = useQuery({
    queryKey: ['venues', searchQuery],
    queryFn: () => moderationApi.getVenues(searchQuery || undefined),
  })

  const filteredVenues = useMemo(() => {
    return venues.filter((venue) => {
      if (filterStatus === 'verified') return venue.is_manually_verified
      if (filterStatus === 'unverified') return !venue.is_manually_verified
      return true
    })
  }, [venues, filterStatus])

  const handleSelectVenue = (venue: Venue) => {
    setSelectedVenue(venue)
    setInspectorOpen(true)
  }

  const totalCount = venues.length
  const unverifiedCount = useMemo(() => venues.filter(v => !v.is_manually_verified).length, [venues])

  return (
    <DashboardLayout>
      <div className="h-full flex min-h-0">
        <VenueList
          venues={filteredVenues}
          selectedVenue={selectedVenue}
          searchQuery={searchQuery}
          filterStatus={filterStatus}
          onSearchChange={setSearchQuery}
          onFilterStatusChange={setFilterStatus}
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
