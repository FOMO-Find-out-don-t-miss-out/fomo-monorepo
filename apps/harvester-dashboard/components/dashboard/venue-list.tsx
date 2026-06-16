'use client'

import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { VenueCard } from './venue-card'
import type { Venue } from '@/types/api'
import { Search, Building2, ShieldCheck, ShieldQuestion, ShieldAlert, Filter, MapPinOff, ArrowDownWideNarrow } from 'lucide-react'

export type PlaceVerificationFilter = 'all' | 'unverified' | 'system_matched' | 'manually_verified'
export type PlaceSort = 'relevance' | 'recent'

interface VenueListProps {
  venues: Venue[]
  selectedVenue: Venue | null
  searchQuery: string
  filterStatus: PlaceVerificationFilter
  missingCoordsOnly: boolean
  sortBy: PlaceSort
  onSearchChange: (query: string) => void
  onFilterStatusChange: (status: PlaceVerificationFilter) => void
  onMissingCoordsOnlyChange: (value: boolean) => void
  onSortByChange: (sort: PlaceSort) => void
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
  missingCoordsOnly,
  sortBy,
  onSearchChange,
  onFilterStatusChange,
  onMissingCoordsOnlyChange,
  onSortByChange,
  onSelectVenue,
  isLoading,
  totalCount,
  unverifiedCount
}: VenueListProps) {
  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-0 bg-background/50">
      {/* Header */}
      <div className="p-6 border-b border-neon-blue/10 bg-card/40 backdrop-blur-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-black text-foreground text-neon-glow-blue uppercase tracking-tighter italic">Places Registry</h1>
            <Badge variant="outline" className="badge-neon h-6 px-3 text-[10px] font-bold tracking-[0.2em] uppercase">
              {totalCount} Nodes
            </Badge>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[220px] max-w-md group">
            <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-neon-blue transition-colors" />
            <Input
              placeholder="Search registry by name or city..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-11 bg-card/60 input-neon h-11 text-sm font-medium"
            />
          </div>

          <div className="flex items-center gap-3">
            <Filter className="w-4 h-4 text-neon-purple/60" />
            <Select
                value={filterStatus}
                onValueChange={(value) => onFilterStatusChange(value as PlaceVerificationFilter)}
            >
                <SelectTrigger className="h-11 w-[180px] bg-card/60 input-neon text-xs font-bold uppercase tracking-widest">
                    <SelectValue placeholder="STATUS FILTER" />
                </SelectTrigger>
                <SelectContent className="bg-card border-neon-purple/20">
                    <SelectItem value="all" className="text-[10px] font-bold uppercase tracking-widest">
                        All Statuses
                    </SelectItem>
                    <SelectItem value="manually_verified" className="text-[10px] font-bold uppercase tracking-widest">
                        <div className="flex items-center gap-2">
                            <ShieldCheck className="w-3.5 h-3.5 text-neon-green" />
                            Verified
                        </div>
                    </SelectItem>
                    <SelectItem value="system_matched" className="text-[10px] font-bold uppercase tracking-widest">
                        <div className="flex items-center gap-2">
                            <ShieldQuestion className="w-3.5 h-3.5 text-neon-blue" />
                            System Matched
                        </div>
                    </SelectItem>
                    <SelectItem value="unverified" className="text-[10px] font-bold uppercase tracking-widest">
                        <div className="flex items-center gap-2">
                            <ShieldAlert className="w-3.5 h-3.5 text-neon-yellow" />
                            Unverified
                        </div>
                    </SelectItem>
                </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-3">
            <ArrowDownWideNarrow className="w-4 h-4 text-neon-purple/60" />
            <Select
                value={sortBy}
                onValueChange={(value) => onSortByChange(value as PlaceSort)}
            >
                <SelectTrigger className="h-11 w-[170px] bg-card/60 input-neon text-xs font-bold uppercase tracking-widest">
                    <SelectValue placeholder="SORT BY" />
                </SelectTrigger>
                <SelectContent className="bg-card border-neon-purple/20">
                    <SelectItem value="relevance" className="text-[10px] font-bold uppercase tracking-widest">
                        Match Confidence
                    </SelectItem>
                    <SelectItem value="recent" className="text-[10px] font-bold uppercase tracking-widest">
                        Recently Updated
                    </SelectItem>
                </SelectContent>
            </Select>
          </div>

          <label className="flex items-center gap-2 h-11 px-3 rounded-md border border-border/50 bg-card/60 cursor-pointer">
            <Checkbox
              checked={missingCoordsOnly}
              onCheckedChange={(checked) => onMissingCoordsOnlyChange(checked === true)}
              className="checkbox-neon"
            />
            <MapPinOff className="w-3.5 h-3.5 text-neon-yellow/80" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground whitespace-nowrap">
              Missing Coordinates
            </span>
          </label>

          {unverifiedCount > 0 && filterStatus === 'all' && (
            <Badge variant="outline" className="badge-neon-purple animate-neon-pulse h-6 px-3 text-[9px] font-black tracking-widest uppercase">
                {unverifiedCount} Not Verified
            </Badge>
          )}
        </div>
      </div>

      {/* Place Cards */}
      <ScrollArea className="flex-1 min-h-0 scrollbar-neon">
        <div className="p-6 space-y-3 relative">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
               <div className="w-12 h-12 rounded-full border-t-2 border-r-2 border-neon-blue animate-spin shadow-[0_0_15px_var(--neon-blue)]"></div>
               <p className="mt-4 text-[10px] font-bold uppercase tracking-[0.3em] text-neon-blue animate-pulse">Scanning Registry...</p>
            </div>
          ) : venues.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="w-20 h-20 rounded-2xl bg-muted/10 border border-dashed border-border flex items-center justify-center mb-6">
                <Building2 className="w-10 h-10 text-muted-foreground/30" />
              </div>
              <p className="text-xl font-bold text-foreground/50 uppercase tracking-widest">No nodes found</p>
              <p className="text-xs text-muted-foreground/60 mt-2 uppercase tracking-tight">Adjust search parameters or sync protocol</p>
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
