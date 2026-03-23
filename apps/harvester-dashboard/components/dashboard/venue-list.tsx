'use client'

import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { VenueCard } from './venue-card'
import type { Venue } from '@/types/moderation'
import { Search, Building2, ShieldCheck, ShieldAlert, Filter } from 'lucide-react'

interface VenueListProps {
  venues: Venue[]
  selectedVenue: Venue | null
  searchQuery: string
  filterStatus: 'all' | 'verified' | 'unverified'
  onSearchChange: (query: string) => void
  onFilterStatusChange: (status: 'all' | 'verified' | 'unverified') => void
  onSelectVenue: (venue: Venue) => void
  isLoading?: boolean
  totalCount: number
  unverifiedCount: number
}

export function VenueList({
  venues,
  selectedVenue,
  searchQuery,
  filterStatus,
  onSearchChange,
  onFilterStatusChange,
  onSelectVenue,
  isLoading,
  totalCount,
  unverifiedCount
}: VenueListProps) {
  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background">
      {/* Header */}
      <div className="p-4 border-b border-border bg-card/30">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-foreground">Venues</h1>
            <Badge variant="secondary" className="text-xs">
              {totalCount} total
            </Badge>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search venues..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-9 bg-input/50"
            />
          </div>

          <div className="flex items-center gap-2 border-l border-border pl-4">
             <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-muted-foreground" />
                <Select
                    value={filterStatus}
                    onValueChange={(value) => onFilterStatusChange(value as any)}
                >
                    <SelectTrigger className="h-9 w-[160px] bg-input/50 text-xs border-border/50">
                        <SelectValue placeholder="Filter by status" />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all" className="text-xs">
                            All Venues
                        </SelectItem>
                        <SelectItem value="verified" className="text-xs">
                            <div className="flex items-center gap-2">
                                <ShieldCheck className="w-3 h-3 text-green-500" />
                                Verified
                            </div>
                        </SelectItem>
                        <SelectItem value="unverified" className="text-xs">
                            <div className="flex items-center gap-2">
                                <ShieldAlert className="w-3 h-3 text-yellow-500" />
                                Unverified
                            </div>
                        </SelectItem>
                    </SelectContent>
                </Select>
             </div>
             {unverifiedCount > 0 && filterStatus !== 'unverified' && (
                <Badge variant="outline" className="text-[10px] bg-yellow-500/10 text-yellow-600 border-yellow-500/20">
                    {unverifiedCount} unverified
                </Badge>
             )}
          </div>
        </div>
      </div>

      {/* Venue Cards */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-2 relative">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
               <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : venues.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
                <Building2 className="w-8 h-8 text-muted-foreground" />
              </div>
              <p className="text-muted-foreground">No venues found</p>
              <p className="text-sm text-muted-foreground mt-1">Try adjusting your search</p>
            </div>
          ) : (
            venues.map((venue) => (
              <VenueCard
                key={venue.id}
                venue={venue}
                isSelected={selectedVenue?.id === venue.id}
                onSelect={() => onSelectVenue(venue)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
