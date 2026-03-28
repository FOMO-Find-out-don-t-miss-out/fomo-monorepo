'use client'

import { useState, useEffect } from 'react'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { CheckCircle2, AlertCircle, XCircle, Filter, Search, MapPin, Database } from 'lucide-react'
import { moderationApi } from '@/lib/api'
import type { GeocodeSuggestion } from '@/types/moderation'

interface FilterSidebarProps {
  selectedCategory: string
  setSelectedCategory: (category: string) => void
  selectedStatus: string | 'all'
  setSelectedStatus: (status: string | 'all') => void
  selectedSource: string | 'all'
  setSelectedSource: (source: string | 'all') => void
  eventCounts: {
    verified: number
    ambiguous: number
    failed: number
    total: number
  }
  onSuggestionSelect?: (suggestion: GeocodeSuggestion) => void
}

const categories = ['All Categories', 'Live Music', 'Theater', 'Art', 'Food & Drink', 'Nightlife', 'Sports', 'Other']
const sources = ['all', 'more.com', 'ticketmaster.com', 'manual', 'unknown']

export function FilterSidebar({
  selectedCategory,
  setSelectedCategory,
  selectedStatus,
  setSelectedStatus,
  selectedSource,
  setSelectedSource,
  eventCounts,
  onSuggestionSelect
}: FilterSidebarProps) {
  const [locationSearch, setLocationSearch] = useState('')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (locationSearch.length > 2) {
        try {
          const res = await moderationApi.getMapboxSuggestions(locationSearch)
          setSuggestions(res)
        } catch (err) {
          console.error('Failed to fetch suggestions', err)
        }
      } else {
        setSuggestions([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [locationSearch])

  return (
    <aside className="w-64 flex-shrink-0 border-r border-border bg-card/50 flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <h2 className="font-semibold text-foreground">Filters</h2>
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {eventCounts.total} pending events
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {/* Quick Location Search */}
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              Quick Location Find
            </Label>
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <Input
                placeholder="Search addresses..."
                value={locationSearch}
                onChange={(e) => setLocationSearch(e.target.value)}
                className="pl-8 h-8 text-xs bg-input/30"
              />
            </div>
            {suggestions.length > 0 && (
              <div className="mt-1 border border-border rounded-md overflow-hidden bg-card shadow-lg z-50 max-h-48 overflow-y-auto">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    className="w-full p-2 text-left text-[10px] hover:bg-accent transition-colors border-b border-border last:border-b-0"
                    onClick={() => {
                      onSuggestionSelect?.(s)
                      setLocationSearch('')
                      setSuggestions([])
                    }}
                  >
                    <div className="font-medium text-foreground truncate">{s.full_address}</div>
                    <div className="text-muted-foreground truncate">{s.city}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Category Filter */}
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Category
            </Label>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-full bg-input/50">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((category) => (
                  <SelectItem key={category} value={category}>
                    {category}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Source Filter */}
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
              <Database className="w-3 h-3" />
              Source Provider
            </Label>
            <Select value={selectedSource} onValueChange={setSelectedSource}>
              <SelectTrigger className="w-full bg-input/50">
                <SelectValue placeholder="All Sources" />
              </SelectTrigger>
              <SelectContent>
                {sources.map((source) => (
                  <SelectItem key={source} value={source}>
                    {source === 'all' ? 'All Sources' : source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Separator className="bg-border" />

          {/* Geocoding Status Filter */}
          <div className="space-y-3">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Geocoding Status
            </Label>
            <RadioGroup
              value={selectedStatus}
              onValueChange={(value) => setSelectedStatus(value)}
              className="space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="all" id="all" />
                  <Label htmlFor="all" className="text-sm font-normal cursor-pointer">
                    All Status
                  </Label>
                </div>
                <Badge variant="secondary" className="text-xs">
                  {eventCounts.total}
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="verified" id="verified" />
                  <Label htmlFor="verified" className="text-sm font-normal cursor-pointer flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                    Verified
                  </Label>
                </div>
                <Badge variant="secondary" className="text-xs bg-green-500/10 text-green-500 border-green-500/20">
                  {eventCounts.verified}
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="ambiguous" id="ambiguous" />
                  <Label htmlFor="ambiguous" className="text-sm font-normal cursor-pointer flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-yellow-500" />
                    Ambiguous
                  </Label>
                </div>
                <Badge variant="secondary" className="text-xs bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
                  {eventCounts.ambiguous}
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="failed" id="failed" />
                  <Label htmlFor="failed" className="text-sm font-normal cursor-pointer flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 text-red-500" />
                    Failed
                  </Label>
                </div>
                <Badge variant="secondary" className="text-xs bg-red-500/10 text-red-500 border-red-500/20">
                  {eventCounts.failed}
                </Badge>
              </div>
            </RadioGroup>
          </div>
        </div>
      </ScrollArea>
    </aside>
  )
}
